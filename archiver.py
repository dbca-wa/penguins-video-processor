import os
import sys

from utils import configure_logging, get_remote_videos, upload_video


# Local environment: define variables in .env file.
dot_env = os.path.join(os.getcwd(), '.env')
if os.path.exists(dot_env):
    from dotenv import load_dotenv
    load_dotenv()

# Configure logging.
LOGGER = configure_logging(logfile='archiver.log', azure_logfile='azure.log')


def archive_videos(source_dir, container_name='archive', overwrite=True):
    """
    Convenience function to upload all processed videos in `source_path` to Azure blob storage.
    Requires an Azure storage account connection string to be defined in the `AZURE_CONNECTION_STRING`
    environment variable.
    """
    conn_str = os.getenv('AZURE_CONNECTION_STRING')
    local_videos = os.listdir(source_dir)
    LOGGER.info('Checking for videos to archive')

    for filename in local_videos:
        name, ext = os.path.splitext(filename)
        # Accepted source video file formats.
        if ext not in ['.mkv', '.mp4', '.m4v', '.mov', '.mpg', '.avi', '.wmv']:
            continue  # Skip non-video files.
        source_path = os.path.join(source_dir, filename)
        
        # Only get the current list of remote videos if we're not overwriting.
        if overwrite:
            LOGGER.info(f'Uploading processed video {filename} to Azure blob store')
            blob_name = os.path.basename(source_path)
            upload_video(conn_str, container_name, source_path, overwrite=overwrite)
        else:
            LOGGER.info('Checking existing uploaded videos')
            remote_filenames = get_remote_videos(conn_str, container_name, name_starts_with=filename)
            if filename in remote_filenames:
                LOGGER.info('Video already exists in Azure blob store, skipping upload')
            else:
                LOGGER.info(f'Uploading processed video {filename} to Azure blob store')
                upload_video(conn_str, container_name, source_path, overwrite=overwrite)

        # Repeat the listing of remote processed videos before removing any local processed files.
        LOGGER.info(f'Checking if processed video {filename} can be removed locally')
        remote_filenames = get_remote_videos(conn_str, container_name, name_starts_with=filename)
        if filename in remote_filenames:
            LOGGER.info(f'Deleting {filename} locally (present in Azure)')
            os.remove(source_path)


if __name__ == '__main__':
    """
    Call script directly on the CLI like so:

        python archiver.py source_dir=$source_dir
    """
    kwargs = dict(arg.split('=') for arg in sys.argv[1:])
    archive_videos(**kwargs)