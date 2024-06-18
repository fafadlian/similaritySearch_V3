# azure_blob_storage.py

from azure.storage.blob import BlobServiceClient, ContentSettings
import os
import logging

AZURE_STORAGE_CONNECTION_STRING = os.getenv('AZURE_STORAGE_CONNECTION_STRING')
CONTAINER_NAME = os.getenv('CONTAINER_NAME')

blob_service_client = BlobServiceClient.from_connection_string(AZURE_STORAGE_CONNECTION_STRING)

def upload_to_blob_storage(blob_name, data):
    try:
        # logging.info(f"Uploading {blob_name} to blob storage from {data}...")
        blob_client = blob_service_client.get_blob_client(container=CONTAINER_NAME, blob=blob_name)
        blob_client.upload_blob(data, overwrite=True, content_settings=ContentSettings(content_type='application/json'))

        print(f"Uploaded {blob_name} to blob storage.")
    except Exception as e:
        logging.error(f"Error uploading {blob_name} to blob storage: {str(e)}")

def download_from_blob_storage(blob_name):
    try:
        blob_client = blob_service_client.get_blob_client(container=CONTAINER_NAME, blob=blob_name)
        data = blob_client.download_blob().readall()
        print(f"Downloaded {blob_name} from blob storage.")
        return data
    except Exception as e:
        logging.error(f"Error downloading {blob_name} from blob storage: {str(e)}")

def delete_from_blob_storage(blob_name):
    try:
        blob_client = blob_service_client.get_blob_client(container=CONTAINER_NAME, blob=blob_name)
        blob_client.delete_blob()
        print(f"Deleted {blob_name} from blob storage.")
    except Exception as e:
        logging.error(f"Error deleting {blob_name} from blob storage: {str(e)}")


def delete_all_files_in_directory(directory):
    blobs = blob_service_client.get_container_client(CONTAINER_NAME).list_blobs(name_starts_with=directory)
    for blob in blobs:
        blob_client = blob_service_client.get_blob_client(container=CONTAINER_NAME, blob=blob.name)
        blob_client.delete_blob()
