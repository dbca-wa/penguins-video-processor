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


def get_unprocessed_videos(dirname='unprocessed'):
    """Check the contents of the ./storage/unprocessed directory and return a list
    source video file paths.
    """
    # Assume video storage is mounted at ./storage
    cwd = pathlib.Path().resolve()
    unprocessed_path = os.path.join(cwd, 'storage', dirname)
    unprocessed_videos = os.listdir(unprocessed_path)
    LOGGER.info('Checking for unprocessed videos')
    source_paths = []

    for filename in unprocessed_videos:
        name, ext = os.path.splitext(filename)
        # Accepted source video file formats.
        if ext not in ['.mkv', '.mp4', '.m4v', '.mov', '.mpg', '.avi', '.wmv']:
            continue
        output = f'{name}.mp4'  # Output container format is MP4, optimised for HTTP streaming.
        source_paths.append(os.path.join(unprocessed_path, filename))

    return source_paths


def transcode_video(source_path, preset=None, dirname='processed'):
    """Transcode a single video at the source_path, then move it to
    the processed directory at `dirname`.
    """
    name, ext = os.path.splitext(filename)
    # Accepted source video file formats.
    if ext not in ['.mkv', '.mp4', '.m4v', '.mov', '.mpg', '.avi', '.wmv']:
        return
    output = f'{name}.mp4'  # Output container format is MP4, optimised for HTTP streaming.
    source = os.path.join(unprocessed_path, filename)
    dest = os.path.join(encoded_path, output)
    processed = os.path.join(processed_path, filename)

    try:
        hb_cmd = f'HandBrakeCLI --preset "{preset}" --optimize --input {source} --output {dest}'
        subprocess.run(hb_cmd, shell=True, stderr=subprocess.STDOUT)
    except subprocess.CalledProcessError:
        LOGGER.exception(f'HandBrake encode failed for {source}')

    LOGGER.info('Moving encoded video to the processed directory')
    shutil.move(source, processed)


def transcode_videos(preset=None):
    """Check the content of the ./storage/unprocessed directory, transcode any videos present,
    then move each video to the ./storage./processed directory.
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
    unprocessed_path = os.path.join(cwd, 'storage', 'unprocessed')
    encoded_path = os.path.join(cwd, 'storage', 'encoded')
    processed_path = os.path.join(cwd, 'storage', 'processed')
    unprocessed_videos = os.listdir(unprocessed_path)
    LOGGER.info('Checking for unprocessed videos')

    for filename in unprocessed_videos:
        name, ext = os.path.splitext(filename)
        # Accepted source video file formats.
        if ext not in ['.mkv', '.mp4', '.m4v', '.mov', '.mpg', '.avi', '.wmv']:
            continue
        output = f'{name}.mp4'  # Output container format is MP4, optimised for HTTP streaming.
        source = os.path.join(unprocessed_path, filename)
        dest = os.path.join(encoded_path, output)
        processed = os.path.join(processed_path, filename)

        try:
            hb_cmd = f'HandBrakeCLI --preset "{preset}" --optimize --input {source} --output {dest}'
            subprocess.run(hb_cmd, shell=True, stderr=subprocess.STDOUT)
        except subprocess.CalledProcessError:
            LOGGER.exception(f'HandBrake encode failed for {source}')

        LOGGER.info('Moving encoded video to the processed directory')
        shutil.move(source, processed)


def upload_transcoded(container_name='beach-return-cams', blob_prefix='beach_return_cams_2', overwrite_existing=True):
    """Check the content of the ./storage/encoded directory, check the Azure blob storage destination,
    then upload any local videos (by default, overwriting any files already in blob storage).
    On successful upload, delete the local encoded video (assumed to have been archived elsewhere).
    """
    connect_str = os.getenv('AZURE_CONNECTION_STRING')
    blob_service_client = BlobServiceClient.from_connection_string(connect_str)
    container_client = blob_service_client.get_container_client(container=container_name)
    blob_list = container_client.list_blobs(name_starts_with=blob_prefix)

    cwd = pathlib.Path().resolve()
    encoded_path = os.path.join(cwd, 'storage', 'encoded')
    encoded_videos = os.listdir(encoded_path)

    if not encoded_videos:
        LOGGER.info('No encoded videos, exiting')
        return  # Exit

    LOGGER.info('Checking existing uploaded videos')
    remote_blobs = [blob.name for blob in blob_list]
    remote_filenames = []
    for b in remote_blobs:
        remote_filenames.append(b.split('/')[-1])

    for video in encoded_videos:
        if overwrite_existing or video not in remote_filenames:
            filepath = os.path.join(encoded_path, video)
            name = f'{blob_prefix}/{video}'

            LOGGER.info(f'Uploading {name}')
            blob_client = blob_service_client.get_blob_client(container=container_name, blob=name)
            with open(file=filepath, mode='rb') as data:
                blob_client.upload_blob(data)

    # Repeat the listing of remote encoded videos before removing any local encoded files.
    blob_list = container_client.list_blobs(name_starts_with=blob_prefix)
    LOGGER.info('Checking if local videos can be removed')
    remote_blobs = [blob.name for blob in blob_list]
    remote_filenames = []
    for b in remote_blobs:
        remote_filenames.append(b.split('/')[-1])

    for video in encoded_videos:
        if video in remote_filenames:
            filepath = os.path.join(encoded_path, video)
            LOGGER.info(f'Deleting {filepath} (present in Azure)')
            os.remove(filepath)

    LOGGER.info('Completed')


if __name__ == '__main__':
    transcode_videos()
    upload_transcoded()
