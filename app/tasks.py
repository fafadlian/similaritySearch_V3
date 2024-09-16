from app.models import Task
from app.data_fetcher import save_json_data_for_flight_id, fetch_all_pnr_data, fetch_all_pages
# from app.azure_blob_storage import upload_to_blob_storage, download_from_blob_storage, delete_from_blob_storage, upload_to_blob_storage_txt
from app.local_storage import upload_to_local_storage, download_from_local_storage, delete_from_local_storage, upload_to_local_storage_txt, list_files_in_directory

from app.similarity_search import find_similar_passengers
from app.loc_access import LocDataAccess
from azure.storage.blob import ContainerClient
from app.database import SessionLocal
from app.celery_init import celery
import numpy as np
import os
import time
import asyncio
from datetime import datetime, timedelta
import shutil
import logging
from dotenv import load_dotenv

load_dotenv('environment.env')

# AZURE_STORAGE_CONNECTION_STRING = os.getenv('AZURE_STORAGE_CONNECTION_STRING')
# CONTAINER_NAME = 'taskfiles'

# container_client = ContainerClient.from_connection_string(AZURE_STORAGE_CONNECTION_STRING, CONTAINER_NAME)

@celery.task
def process_task(task_id, arrival_date_from, arrival_date_to, flight_number, folder_name):
    session = SessionLocal()
    task = None

    try:
        api_url = 'https://tenacity-rmt.eurodyn.com/api/datalist/flights'
        access_token = os.getenv("ACCESS_TOKEN")

        params = {
            'ft_flight_leg_arrival_date_time_from': arrival_date_from.isoformat(),
            'ft_flight_leg_arrival_date_time_to': arrival_date_to.isoformat(),
            'ft_flight_leg_flight_number': flight_number
        }

        start_time = time.time()
        loop = asyncio.get_event_loop()
        pnr_data, total_pages = loop.run_until_complete(fetch_all_pages(api_url, access_token, params))
        loop.close()

        if pnr_data:
            print(f"Fetched data from {total_pages} pages")
        else:
            print("Failed to fetch data")
        end_time = time.time()
        time_first_approach = end_time - start_time
        logging.info(f"Time for fetching PNR data (first approach): {time_first_approach:.2f} seconds")

        task = session.query(Task).get(task_id)

        if not task:
            logging.error(f"Task with ID {task_id} not found.")
            return

        if pnr_data:
            flight_ids = [flight['flight_id'] for flight in pnr_data]
            task.flight_ids = ",".join(flight_ids)
            task.flight_count = len(set(flight_ids))

            start_time = time.time()

            # Ensure a clean event loop for the second async call
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    loop.close()
            except RuntimeError:
                pass

            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(fetch_all_pnr_data(flight_ids, folder_name, access_token))
            loop.close()

            end_time = time.time()
            time_second_approach = end_time - start_time
            logging.info(f"Time for fetching PNR data concurrently: {time_second_approach:.2f} seconds")

            task.status = 'completed'
            logging.info(f"Task {task_id} completed")
        else:
            task.status = 'failed'
            logging.info(f"Task {task_id} failed")
            time_second_approach = None

        session.commit()

        time_comparison_content = (
            f"Time for fetching PNR data (first approach): {time_first_approach:.2f} seconds\n"
            f"Time for fetching PNR data concurrently: {time_second_approach:.2f} seconds\n"
        )

        blob_name = f"{folder_name}/time_comparison.txt"
        # upload_to_blob_storage_txt(blob_name, time_comparison_content)
        upload_to_local_storage_txt(blob_name, time_comparison_content)
        # logging.info(f"Uploaded time comparison results to Azure Blob Storage as {blob_name}")
        logging.info(f"blob_name: {blob_name}")

    except Exception as e:
        if task:
            task.status = 'failed'
            try:
                session.commit()
            except Exception as commit_err:
                logging.error(f"Failed to commit session after setting task status to failed: {commit_err}")
        logging.error(f"Error processing task {task_id}: {e}")
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
            blobs_to_delete = list_files_in_directory(name_starts_with=folder_path)
            session.delete(task)
        session.commit()
    except Exception as e:
        print(f"Error deleting old tasks: {e}")
    finally:
        session.close()


@celery.task
def perform_similarity_search_task(task_id, firstname, surname, dob, iata_o, iata_d, city_name, address, sex, nationality, folder_path, nameThreshold, ageThreshold, locationThreshold):
    airport_data_access = LocDataAccess.get_instance()
    similar_passengers = find_similar_passengers(
        airport_data_access, firstname, surname, f"{firstname} {surname}", dob, iata_o, iata_d, city_name, address, sex, nationality, folder_path, nameThreshold, ageThreshold, locationThreshold)
    
    similar_passengers.replace([np.inf, -np.inf, np.nan], None, inplace=True)
    # Convert DataFrame to JSON-serializable format
    similar_passengers_json = similar_passengers.to_dict(orient='records')
    
    # Here you could save the result to a database or a file
    return {"status": "success", "data": similar_passengers_json}

