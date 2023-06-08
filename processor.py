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


def get_unprocessed_videos(source_dir='unprocessed'):
    """Check the contents of the ./storage/unprocessed directory and return a list
    source video file paths.
    """
    # Assume video storage is mounted at ./storage
    cwd = pathlib.Path().resolve()
    unprocessed_path = os.path.join(cwd, 'storage', source_dir)
    unprocessed_videos = os.listdir(unprocessed_path)
    source_paths = []

    for filename in unprocessed_videos:
        name, ext = os.path.splitext(filename)
        # Accepted source video file formats.
        if ext not in ['.mkv', '.mp4', '.m4v', '.mov', '.mpg', '.avi', '.wmv']:
            continue
        source_paths.append(os.path.join(unprocessed_path, filename))

    return source_paths


def transcode_video(source_path, preset=None, encode_dir='encoded', processed_dir='processed'):
    """Transcode a single video at `source_path` then move it to the processed directory at `processed_dir`.
    """
    if not preset:
        # Check if the encoding preset has been set via environment variable.
        if os.getenv('VIDEO_PRESET'):
            preset = os.getenv('VIDEO_PRESET')
        else:
            # Fall back to a basic video encoding preset.
            preset = 'Very Fast 480p30'

    filename = os.path.basename(source_path)
    name, ext = os.path.splitext(filename)
    encoded_filename = f'{name}.mp4'
    cwd = pathlib.Path().resolve()
    encode_dirpath = os.path.join(cwd, 'storage', encode_dir)
    encoded_path = os.path.join(encode_dirpath, encoded_filename)

    try:
        hb_cmd = f'HandBrakeCLI --preset "{preset}" --optimize --input {source_path} --output {encoded_path}'
        subprocess.run(hb_cmd, shell=True, stderr=subprocess.STDOUT)
    except subprocess.CalledProcessError:
        LOGGER.exception(f'HandBrake encode failed for {source_path}')
        return None

    LOGGER.info('Moving encoded video to the processed directory')
    processed_path = os.path.join(cwd, 'storage', processed_dir)
    processed = os.path.join(processed_path, filename)
    shutil.move(source_path, processed)

    return encoded_path


def upload_video(encoded_path, container_name='beach-return-cams', blob_prefix='beach_return_cams_2'):
    """Upload a single video at the source path to blob storage (overwrites any existing blob).
    """
    filename = os.path.basename(encoded_path)
    connect_str = os.getenv('AZURE_CONNECTION_STRING')
    blob_service_client = BlobServiceClient.from_connection_string(connect_str)
    blob_name = f'{blob_prefix}/{filename}'
    blob_client = blob_service_client.get_blob_client(container=container_name, blob=blob_name)

    LOGGER.info(f'Uploading {blob_name}')
    with open(file=encoded_path, mode='rb') as data:
        blob_client.upload_blob(data)

    LOGGER.info(f'Deleting {encoded_path}')
    os.remove(encoded_path)


if __name__ == '__main__':
    source_paths = get_unprocessed_videos()
    for source_path in source_paths:
        encoded_path = transcode_video(source_path)
        upload_video(encoded_path)
