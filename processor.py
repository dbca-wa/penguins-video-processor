from azure.storage.blob import BlobServiceClient
import logging
import os
import pathlib
import shutil
import subprocess
import sys


# Development environment: define variables in .env
dot_env = os.path.join(os.getcwd(), '.env')
if os.path.exists(dot_env):
    from dotenv import load_dotenv
    load_dotenv()

# Configure logging
LOGGER = logging.getLogger()
LOGGER.setLevel(logging.INFO)
handler = logging.StreamHandler(sys.stdout)
handler.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s | %(levelname)s | %(message)s')
handler.setFormatter(formatter)
LOGGER.addHandler(handler)
# Set the logging level for all azure-* libraries (the azure-storage-blob library uses this one).
# Reference: https://learn.microsoft.com/en-us/azure/developer/python/sdk/azure-sdk-logging
azure_logger = logging.getLogger('azure')
azure_logger.setLevel(logging.ERROR)


def encode_video(source_path, encoded_path, preset):
    """Transcode a single video at the source_path, then move it to
    the `processed` directory. If processed_path is not supplied, infer it.
    """
    hb_cmd = f'HandBrakeCLI --preset "{preset}" --optimize --input {source_path} --output {encoded_path}'
    subprocess.run(hb_cmd, shell=True, stderr=subprocess.STDOUT)
    return


def get_remote_videos(container_name='beach-return-cams', blob_prefix='beach_return_cams_2'):
    """Check Azure blob storage for the list of uploaded videos, returns a
    list of filenames (minus any prefix).
    """
    connect_str = os.getenv('AZURE_CONNECTION_STRING')
    blob_service_client = BlobServiceClient.from_connection_string(connect_str)
    LOGGER.info('Checking existing uploaded videos')
    container_client = blob_service_client.get_container_client(container=container_name)
    blob_list = container_client.list_blobs(name_starts_with=blob_prefix)
    remote_blobs = [blob.name for blob in blob_list]
    remote_filenames = []
    for b in remote_blobs:
        remote_filenames.append(b.split('/')[-1])
    return remote_filenames


def upload_video(source_path, container_name='beach-return-cams', blob_prefix='beach_return_cams_2', overwrite=True):
    """Upload a single video at `source_path` to Azure blob storage.
    """
    filename = os.path.basename(source_path)
    connect_str = os.getenv('AZURE_CONNECTION_STRING')
    blob_service_client = BlobServiceClient.from_connection_string(connect_str)
    remote_name = f'{blob_prefix}/{filename}'
    blob_client = blob_service_client.get_blob_client(container=container_name, blob=remote_name)
    with open(file=source_path, mode='rb') as data:
        blob_client.upload_blob(data, overwrite=overwrite)


def transcode_videos(preset=None, overwrite=True, container_name='beach-return-cams', blob_prefix='beach_return_cams_2'):
    """Check the content of the ./storage/unprocessed directory, transcode any videos present,
    then move each video to the ./storage./processed directory.
    Upload encoded videos to Azure blob storage.
    On successful upload, delete the local encoded video (assumed to have been archived elsewhere).
    """
    if not preset:
        # Check if the encoding preset has been set via environment variable.
        if os.getenv('VIDEO_PRESET'):
            preset = os.getenv('VIDEO_PRESET')
        else:
            # Fall back to a basic video encoding preset.
            preset = 'Very Fast 480p30'
    LOGGER.info(f'Using HandBrake video preset {preset}')

    # Assume video storage is mounted at ./storage
    cwd = pathlib.Path().resolve()
    unprocessed_dir = os.path.join(cwd, 'storage', 'unprocessed')
    encoded_dir = os.path.join(cwd, 'storage', 'encoded')
    processed_dir = os.path.join(cwd, 'storage', 'processed')
    unprocessed_videos = os.listdir(unprocessed_dir)
    LOGGER.info('Checking for unprocessed videos')

    for filename in unprocessed_videos:
        name, ext = os.path.splitext(filename)
        # Accepted source video file formats.
        if ext not in ['.mkv', '.mp4', '.m4v', '.mov', '.mpg', '.avi', '.wmv']:
            continue
        output = f'{name}.mp4'  # Output container format is MP4, optimised for HTTP streaming.
        source_path = os.path.join(unprocessed_dir, filename)
        encoded_path = os.path.join(encoded_dir, output)

        try:
            encode_video(source_path, encoded_path, preset)
        except subprocess.CalledProcessError:
            LOGGER.exception(f'HandBrake encode failed for {source_path}')

        LOGGER.info(f'Moving encoded video {filename} to the processed directory')
        processed_path = os.path.join(processed_dir, filename)
        shutil.move(source_path, processed_path)

        if not overwrite:
            LOGGER.info('Checking existing uploaded videos')
            remote_filenames = get_remote_videos()
            if output in remote_filenames:
                LOGGER.info('Video already uploaded, skipping.')
                continue

        LOGGER.info(f'Uploading encoded video {output} to Azure blob store')
        upload_video(encoded_path, container_name, blob_prefix, overwrite)

        # Repeat the listing of remote encoded videos before removing any local encoded files.
        LOGGER.info(f'Checking if encoded video {output} can be removed locally')
        remote_filenames = get_remote_videos()
        if output in remote_filenames:
            LOGGER.info(f'Deleting {output} locally (present in Azure)')
            os.remove(encoded_path)

    LOGGER.info('Completed')


if __name__ == '__main__':
    transcode_videos()
