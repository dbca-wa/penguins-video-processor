from azure.storage.blob import BlobClient, ContainerClient
import logging
import os
import sys


def configure_logging(logfile=None, azure_logfile=None):
    """
    Configure logging (stdout and file) for the default logger and for the `azure` logger.
    """
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(asctime)s | %(levelname)s | %(message)s')
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(logging.INFO)
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    if logfile:
        file_handler = logging.FileHandler(logfile)
        file_handler.setLevel(logging.INFO)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    # Set the logging level for all azure-* libraries (the azure-storage-blob library uses this one).
    # Reference: https://learn.microsoft.com/en-us/azure/developer/python/sdk/azure-sdk-logging
    azure_logger = logging.getLogger('azure')
    azure_logger.setLevel(logging.WARNING)
    if azure_logfile:
        file_handler = logging.FileHandler(azure_logfile)
        file_handler.setLevel(logging.WARNING)
        file_handler.setFormatter(formatter)
        azure_logger.addHandler(file_handler)

    return logger


def get_remote_videos(conn_str, container_name, name_starts_with=None):
    """
    Check Azure blob storage for the list of uploaded videos, returns a
    list of filenames (minus any prefix).
    """
    container_client = ContainerClient.from_connection_string(conn_str, container_name)
    if name_starts_with:
        blob_list = container_client.list_blobs(name_starts_with)
    else:
        blob_list = container_client.list_blobs()
    remote_blobs = [blob.name.split('/')[-1] for blob in blob_list]

    return remote_blobs


def get_blob_client(conn_str, container_name, blob_name, max_put=16*1024*1024, timeout=120):
    """
    Return a BlobClient class having defaults to account for a slower internet connection.
    The parent class defaults are 64MB and 20s.
    https://learn.microsoft.com/en-us/python/api/azure-storage-blob/azure.storage.blob.blobclient?view=azure-python#azure-storage-blob-blobclient-from-connection-string
    """
    return BlobClient.from_connection_string(
        conn_str,
        container_name,
        blob_name,
        max_single_put_size=max_put,
        connection_timeout=timeout,
    )


def upload_video(conn_str, container_name, source_path, blob_prefix=None, overwrite=True):
    """
    Upload a single video at `source_path` to Azure blob storage, allowing an optional
    prefix value and/or overwriting any existing blob.
    """
    blob_name = os.path.basename(source_path)
    if blob_prefix:
        blob_name = f'{blob_prefix}/{blob_name}'
    blob_client = get_blob_client(conn_str, container_name, blob_name)

    with open(file=source_path, mode='rb') as data:
        blob_client.upload_blob(data, overwrite=overwrite)