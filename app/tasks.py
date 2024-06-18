from app.models import Task
from app.data_fetcher import fetch_pnr_data, save_json_data_for_flight_id
from app.azure_blob_storage import upload_to_blob_storage, download_from_blob_storage, delete_from_blob_storage
from azure.storage.blob import ContainerClient
from app.database import SessionLocal
from app.celery_init import celery
import os
from datetime import datetime, timedelta
import shutil
import logging
from dotenv import load_dotenv

load_dotenv('environment.env')

AZURE_STORAGE_CONNECTION_STRING = os.getenv('AZURE_STORAGE_CONNECTION_STRING')
CONTAINER_NAME = 'taskfiles'

container_client = ContainerClient.from_connection_string(AZURE_STORAGE_CONNECTION_STRING, CONTAINER_NAME)

@celery.task
def process_task(task_id, arrival_date_from, arrival_date_to, flight_number, folder_name):
    # from app import celery  # Import here to avoid circular import issues
    session = SessionLocal()

    try:
        api_url = 'https://tenacity-rmt.eurodyn.com/api/datalist/flights'
        access_token = os.getenv("ACCESS_TOKEN")
        refresh_token_value = os.getenv("REFRESH_TOKEN")

        params = {
            'ft_flight_leg_arrival_date_time_from': arrival_date_from,
            'ft_flight_leg_arrival_date_time_to': arrival_date_to,
            'ft_flight_leg_flight_number': flight_number
        }

        print(f"Processing task {task_id}")
        pnr_data, total_pages = fetch_pnr_data(api_url, access_token, params)
        print(f"Total pages: {total_pages}")
        
        task = session.query(Task).get(task_id)

        if not task:
            logging.error(f"Task with ID {task_id} not found.")
            return
        
        if pnr_data:
            flight_ids = [flight['flight_id'] for flight in pnr_data]  # Extract flight IDs
            task.flight_ids = ",".join(flight_ids)  # Assuming Task model has a flight_ids field
            task.flight_count = len(set(flight_ids))
            print(f"Task {task_id} has {task.flight_count} unique flights")

            for flight in flight_ids:
                save_json_data_for_flight_id(flight, folder_name)

            task.status = 'completed'
            logging.info(f"Task {task_id} completed")
        else:
            task.status = 'failed'
            logging.info(f"Task {task_id} failed")

        session.commit()

    except Exception as e:
        task.status = 'failed'
        session.commit()
        print(f"Error processing task {task_id}: {e}")
    finally:
        session.close()

# Task to delete old folders
@celery.task
def delete_old_tasks():
    session = SessionLocal()
    try:
        cutoff_time = datetime.utcnow() - timedelta(hours=7)
        print(f"Cutoff time: {cutoff_time}")

        old_tasks = session.query(Task).filter(Task.created_at < cutoff_time).all()
        print(f"Found {len(old_tasks)} old tasks")

        for task in old_tasks:
            print(f"Deleting task {task.id} created at {task.created_at}")
            folder_path = task.folder_path
            blobs_to_delete = container_client.list_blobs(name_starts_with=folder_path)
            session.delete(task)
        session.commit()
    except Exception as e:
        print(f"Error deleting old tasks: {e}")
    finally:
        session.close()
