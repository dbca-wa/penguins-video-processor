import os
import shutil
import subprocess
import sys

from utils import configure_logging, get_remote_videos, upload_video

# Configure logging.
LOGGER = configure_logging(logfile='processor.log', azure_logfile='azure.log')


def transcode_video(source_path, transcoded_path, preset=None, preset_import_file=None):
    """
    Transcode a single video at `source_path` with the output at `transcoded_path`.
    Requires either `preset` (string) or `preset_import_file` (path) to be passed in.
    """
    if not preset and not preset_import_file:
        return

    if preset:
        hb_cmd = f'HandBrakeCLI --preset "{preset}" --optimize --input {source_path} --output {transcoded_path}'
    else:
        hb_cmd = f'HandBrakeCLI --preset-import-file "{preset_import_file}" --optimize --input {source_path} --output {transcoded_path}'
    LOGGER.info(hb_cmd)
    subprocess.run(hb_cmd, shell=True, stderr=subprocess.STDOUT)
    return


def transcode_videos(source_dir, transcoded_dir, processed_dir='processed', preset=None, preset_import_file=None, overwrite=False, container_name='beach-return-cams', blob_prefix='beach_return_cams_2'):
    """
    Convenience function to check the content of the `source_dir` directory,
    transcode any videos present using the HandBrake preset, then move each
    transcoded video to the `transcoded_dir` directory. Upload transcoded videos to
    Azure blob storage. On successful upload, delete the local transcoded video
    and move the original video to `processed_dir`.
    """
    if not preset:
        # Check if the encoding preset has been set via environment variable.
        if os.getenv('TRANSCODE_PRESET'):
            preset = os.getenv('TRANSCODE_PRESET')
        LOGGER.info(f'Using HandBrake video preset {preset}')

    if not preset and not preset_import_file:
        LOGGER.warning('No HandBrake video preset specified')
        return

    conn_str = os.getenv('AZURE_CONNECTION_STRING')
    unprocessed_videos = os.listdir(source_dir)
    LOGGER.info('Checking for unprocessed videos')

    for filename in unprocessed_videos:
        name, ext = os.path.splitext(filename)
        # Accepted source video file formats.
        if ext not in ['.mkv', '.mp4', '.m4v', '.mov', '.mpg', '.avi', '.wmv']:
            continue
        output = f'{name}.mp4'
        source_path = os.path.join(source_dir, filename)
        transcoded_path = os.path.join(transcoded_dir, output)

        try:
            if preset:
                transcode_video(source_path, transcoded_path, preset=preset)
            else:
                transcode_video(source_path, transcoded_path, preset_import_file=preset_import_file)

        except subprocess.CalledProcessError:
            LOGGER.exception(f'HandBrake encode failed for {source_path}')
            continue  # Skip further actions for this video.

        LOGGER.info(f'Moving source video {filename} to the processed directory')
        processed_path = os.path.join(processed_dir, filename)
        shutil.move(source_path, processed_path)

        name_starts_with = f'{blob_prefix}/{output}'
        LOGGER.info(f'Checking existing uploaded videos at {name_starts_with}')
        remote_filenames = get_remote_videos(conn_str, container_name, name_starts_with)
        
        if output in remote_filenames and not overwrite:
            LOGGER.info('Video already exists in Azure blob store, skipping upload')
        else:
            LOGGER.info(f'Uploading transcoded video to Azure at {name_starts_with}')
            upload_video(conn_str, container_name, transcoded_path, blob_prefix, overwrite)

        # Repeat the list of remote transcoded videos before removing any local transcoded files.
        LOGGER.info(f'Checking if transcoded video {output} can be removed locally')
        remote_filenames = get_remote_videos(conn_str, container_name, name_starts_with)
        if output in remote_filenames:
            LOGGER.info(f'Deleting {output} locally (present in Azure)')
            os.remove(transcoded_path)

    LOGGER.info('Completed')


if __name__ == '__main__':
    """
    Call script directly on the CLI like so:

        python processor.py source_dir=$source_dir transcoded_dir=$transcoded_dir processed_dir=$processed_dir preset_import_file=$preset_import_file
    """
    dot_env = os.path.join(os.getcwd(), '.env')
    if os.path.exists(dot_env):
        from dotenv import load_dotenv
        load_dotenv()

    kwargs = dict(arg.split('=') for arg in sys.argv[1:])
    transcode_videos(**kwargs)