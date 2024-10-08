from fastapi import APIRouter, HTTPException, Request, Depends
from fastapi.responses import HTMLResponse, JSONResponse
from app.tasks import process_task, perform_similarity_search_task
from app.models import Task
from app.loc_access import LocDataAccess
from app.database import get_db
from app.schemas import FlightSearchRequest, SimilaritySearchRequest  # Import the new schemas
# from azure.storage.blob import ContainerClient
from sqlalchemy.orm import Session
from sqlalchemy.sql import text
# from app.azure_blob_storage import delete_from_blob_storage
from app.local_storage import delete_from_local_storage, list_files_in_directory
from dotenv import load_dotenv
import numpy as np

load_dotenv('environment.env')

import os
import uuid
import shutil
from datetime import datetime
from . import templates
import pandas as pd
import logging
logging.basicConfig(level=logging.INFO)

router = APIRouter()

AZURE_STORAGE_CONNECTION_STRING = os.getenv('AZURE_STORAGE_CONNECTION_STRING')
CONTAINER_NAME = 'taskfiles'
# container_client = ContainerClient.from_connection_string(AZURE_STORAGE_CONNECTION_STRING, CONTAINER_NAME)
# container_client = None


@router.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@router.post("/submit_param")
async def submit_param(flight_search: FlightSearchRequest, db: Session = Depends(get_db)):
    data = flight_search.dict()
    arrival_date_from = data['arrival_date_from']
    arrival_date_to = data['arrival_date_to']
    flight_nbr = data['flight_nbr']

    try:
        task_id = str(uuid.uuid4())
        folder_name = f'task_{task_id}'
        # os.makedirs(folder_name, exist_ok=True)

        task = Task(id=task_id, folder_path=folder_name, status='pending')
        db.add(task)
        db.commit()

        logging.info(f"Task {task_id} created with folder {folder_name}")

        process_task.delay(task_id, arrival_date_from, arrival_date_to, flight_nbr, folder_name)

        return {"status": "processing", "task_id": task_id}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    

@router.get("/flight_ids/{task_id}")
async def get_flight_ids(task_id: str, db: Session = Depends(get_db)):
    task = db.query(Task).get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    flight_ids = task.flight_ids.split(',') if task.flight_ids else []
    unique_flight_id_count = len(set(flight_ids))
    unique_flight_id_count_check = task.flight_count
    return {"flight_ids": flight_ids, "unique_flight_id_count": unique_flight_id_count, "unique_flight_id_count_check": unique_flight_id_count_check}


@router.get("/result/{task_id}")
async def get_result(task_id: str, db: Session = Depends(get_db)):
    task = db.query(Task).get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    if task.status == 'completed':
        result = {"message": "Processing completed", "folder": task.folder_path}
        return result
    else:
        return {"status": task.status}
    

    
@router.post("/perform_similarity_search", response_class=JSONResponse)
async def handle_similarity_search(similarity_search: SimilaritySearchRequest, db: Session = Depends(get_db)):
    try:
        data = similarity_search.dict()
        task_id = data.get('task_id')

        logging.info(f"perform_similarity_search: task_id={task_id}, query_data={data}")

        firstname = data.get('firstname', '')
        surname = data.get('surname', '')
        dob = data.get('dob', None)
        iata_o = data.get('iata_o', '')
        iata_d = data.get('iata_d', '')
        city_name = data.get('city_name', '')
        name = data.get('name', f"{firstname} {surname}")
        address = data.get('address', '')
        sex = data.get('sex', '')
        nationality = data.get('nationality', '')
        nameThreshold = data.get('nameThreshold', 0.0)
        ageThreshold = data.get('ageThreshold', 0.0)
        locationThreshold = data.get('locationThreshold', 0.0)

        logging.info(f"perform_similarity_search: name={name}, dob={dob}, iata_o={iata_o}, iata_d={iata_d}, city_name={city_name}, address={address}, sex={sex})")

        # Retrieve the task from the database to get the folder path
        task = db.query(Task).get(task_id)
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")

        folder_path = task.folder_path  # Use the folder path associated with the task

        # Start Celery task
        celery_task = perform_similarity_search_task.delay(task_id, firstname, surname, dob, iata_o, iata_d, city_name, address, sex, nationality, folder_path, nameThreshold, ageThreshold, locationThreshold)

        # Wait for task completion
        result = celery_task.get(timeout=300)  # Timeout after 5 minutes
        if result["status"] != "success":
            raise HTTPException(status_code=500, detail="Error during similarity search")

        similar_passengers_json = result["data"]

        response_data = {
            'data': similar_passengers_json,
            'message': 'Similar passengers found successfully'
        }

        return response_data
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
    

@router.post("/delete_task", response_class=JSONResponse)
async def delete_task(request: Request, db: Session = Depends(get_db)):
    data = await request.json()
    task_id = data.get('task_id')
    if not task_id:
        return JSONResponse(status_code=400, content={"status": "error", "message": "Task ID is required"})

    task = db.query(Task).get(task_id)
    if not task:
        return JSONResponse(status_code=404, content={"status": "error", "message": "Task not found"})

    try:
        # shutil.rmtree(task.folder_path)
        blobs_to_delete = list_files_in_directory(task.folder_path)
        for blob in blobs_to_delete:
            # delete_from_blob_storage(blob.name)
            delete_from_local_storage(blob)

        db.delete(task)
        db.commit()
        return {"status": "success", "message": "Task deleted successfully"}
    except Exception as e:
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})


@router.get("/test-db/")
async def test_db_connection(db: Session = Depends(get_db)):
    try:
        db.execute(text('SELECT 1'))
        return {"status": "success", "message": "Database connection successful!"}
    except Exception as e:
        return {"status": "error", "message": str(e)}
