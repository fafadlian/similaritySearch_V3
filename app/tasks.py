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
logging.basicConfig(level=logging.INFO)


# AZURE_STORAGE_CONNECTION_STRING = os.getenv('AZURE_STORAGE_CONNECTION_STRING')
# CONTAINER_NAME = 'taskfiles'

# container_client = ContainerClient.from_connection_string(AZURE_STORAGE_CONNECTION_STRING, CONTAINER_NAME)
# Helper Functions
def run_async(func, *args, **kwargs):
    """Run an asynchronous function in a new event loop."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(func(*args, **kwargs))
    finally:
        loop.close()

def get_db_session():
    """Provide a database session."""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
        logging.info("Database session closed.")

# Celery Tasks
@celery.task
def process_task(task_id, arrival_date_from, arrival_date_to, flight_number, folder_name):
    """Fetch PNR data for a specific flight and save it to the specified folder."""
    session = SessionLocal()
    try:
        logging.info(f"[Task {task_id}] Fetching PNR data for flight {flight_number} from {arrival_date_from} to {arrival_date_to}...")

        api_url = 'https://tenacity-rmt.eurodyn.com/api/datalist/flights'
        access_token = os.getenv("ACCESS_TOKEN")
        params = {
            'ft_flight_leg_arrival_date_time_from': arrival_date_from.isoformat(),
            'ft_flight_leg_arrival_date_time_to': arrival_date_to.isoformat(),
            'ft_flight_leg_flight_number': flight_number
        }

        # Use asyncio.run to handle asynchronous calls cleanly
        start_time = time.time()
        pnr_data, total_pages = asyncio.run(fetch_all_pages(api_url, access_token, params))
        if pnr_data:
            print(f"Fetched data from {total_pages} pages")
        else:
            print("Failed to fetch data")
        end_time = time.time()
        time_first_approach = end_time - start_time
        logging.info(f"Time for fetching PNR data (first approach): {time_first_approach:.2f} seconds")

        task = session.query(Task).get(task_id)
        if not task:
            logging.error(f"[Task {task_id}] Task not found in database.")
            return

        flight_ids = [flight['flight_id'] for flight in pnr_data]
        task.flight_ids = ",".join(flight_ids)
        task.flight_count = len(set(flight_ids))

        start_time = time.time()

        # Use asyncio.run again for the second asynchronous call
        run_async(fetch_all_pnr_data, flight_ids, folder_name, access_token)
        end_time = time.time()
        time_second_approach = end_time - start_time
        logging.info(f"Time for fetching PNR data concurrently: {time_second_approach:.2f} seconds")

        task.status = 'completed'
        logging.info(f"Task {task_id} completed")

        session.commit()

        time_comparison_content = (
            f"Time for fetching PNR data (first approach): {time_first_approach:.2f} seconds\n"
            f"Time for fetching PNR data concurrently: {time_second_approach:.2f} seconds\n"
        )

        blob_name = f"{folder_name}/time_comparison.txt"
        upload_to_local_storage_txt(blob_name, time_comparison_content)
        logging.info(f"blob_name: {blob_name}")

    except Exception as e:
        logging.error(f"[Task {task_id}] Error processing task: {e}", exc_info=True)
        if task:
            task.status = "failed"
            session.commit()
    finally:
        session.close()
        logging.info("Database session closed.")


# Task to delete old folders
@celery.task
def delete_old_tasks():
    """Delete tasks older than a certain time threshold."""
    session = SessionLocal()
    try:
        cutoff_time = datetime.utcnow() - timedelta(hours=7)
        logging.info(f"Cutoff time for old tasks: {cutoff_time}")

        old_tasks = session.query(Task).filter(Task.created_at < cutoff_time).all()
        logging.info(f"Found {len(old_tasks)} old tasks to delete.")

        for task in old_tasks:
            logging.info(f"Deleting task {task.id} created at {task.created_at}")
            folder_path = task.folder_path

            if os.path.exists(folder_path):
                shutil.rmtree(folder_path, ignore_errors=True)
                logging.info(f"Deleted folder: {folder_path}")
            else:
                logging.warning(f"Folder not found: {folder_path}")

            session.delete(task)

        session.commit()
        logging.info("Old tasks deleted successfully.")
    except Exception as e:
        logging.error(f"Error deleting old tasks: {e}", exc_info=True)
    finally:
        session.close()

@celery.task
def perform_similarity_search_task(task_id, firstname, surname, dob, iata_o, iata_d, city_name, address, sex, nationality, folder_path, nameThreshold, ageThreshold, locationThreshold):
    """Perform a similarity search for passengers."""
    logging.info(f"[Task {task_id}] Starting similarity search...")
    try:
        airport_data_access = LocDataAccess.get_instance()
        similar_passengers = find_similar_passengers(
            airport_data_access, firstname, surname, f"{firstname} {surname}", dob, iata_o, iata_d,
            city_name, address, sex, nationality, folder_path, nameThreshold, ageThreshold, locationThreshold
        )

        # Replace invalid values
        similar_passengers.replace([np.inf, -np.inf, np.nan], None, inplace=True)

        # Check for empty DataFrame
        if similar_passengers.empty:
            logging.warning(f"[Task {task_id}] No similar passengers found.")
            return {"status": "success", "data": []}

        # Convert DataFrame to JSON-serializable format
        similar_passengers_json = similar_passengers.to_dict(orient="records")
        logging.info(f"[Task {task_id}] Similarity search completed successfully.")
        return {"status": "success", "data": similar_passengers_json}
    except Exception as e:
        logging.error(f"[Task {task_id}] Error during similarity search: {e}", exc_info=True)
        return {"status": "error", "message": str(e)}


