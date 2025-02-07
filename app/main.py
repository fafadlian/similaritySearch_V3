from fastapi import APIRouter, HTTPException, Request, Depends
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.responses import StreamingResponse

from sqlalchemy.orm import Session
from sqlalchemy.sql import text
from app.tasks import process_task, perform_similarity_search_task, retrieveng_from_new_API
from app.models import Task
from app.database import get_db, SessionLocal
from app.schemas import FlightSearchRequest, SimilaritySearchRequest, CombinedRequest
from app.local_storage import delete_from_local_storage, list_files_in_directory
from fastapi.templating import Jinja2Templates
from dotenv import load_dotenv
import os
import uuid
import shutil
import logging
import asyncio

# Load environment variables
load_dotenv("environment.env")

logging.basicConfig(level=logging.INFO)
router = APIRouter()

# Constants
AZURE_STORAGE_CONNECTION_STRING = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
CONTAINER_NAME = "taskfiles"

# Helper Functions
def create_task_folder(folder_name: str):
    """Ensure the task folder exists."""
    os.makedirs(folder_name, exist_ok=True)

def get_task_by_id(task_id: str, db: Session) -> Task:
    """Retrieve a task by ID or raise a 404 error."""
    task = db.query(Task).get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task

# Routes


templates = Jinja2Templates(directory="app/templates")

@router.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


from fastapi import Query

@router.post("/submit_param")
async def submit_param(
    flight_search: FlightSearchRequest,
    db: Session = Depends(get_db),
):
    try:
        data = flight_search.dict()
        task_id = str(uuid.uuid4())
        folder_name = f"task_{task_id}"
        create_task_folder(folder_name)

        task = Task(id=task_id, folder_path=folder_name, status="pending")
        db.add(task)
        db.commit()

        logging.info(f"Task {task_id} created with folder {folder_name}")

        process_task.delay(task_id, data["arrival_date_from"], data["arrival_date_to"], data["flight_nbr"], folder_name)
        return {"status": "processing", "task_id": task_id}
    except Exception as e:
        logging.error(f"Error creating task: {e}")
        raise HTTPException(status_code=500, detail={"status": "error", "message": str(e)})

@router.post("/submit_param_sync")
async def submit_param_sync(
    flight_search: FlightSearchRequest,
    db: Session = Depends(get_db),
):
    data = flight_search.dict()
    task_id = str(uuid.uuid4())
    folder_name = f"task_{task_id}"
    create_task_folder(folder_name)

    # Create and store the task
    task = Task(id=task_id, folder_path=folder_name, status="pending")
    db.add(task)
    db.commit()

    logging.info(f"Task {task_id} created with folder {folder_name}")

    process_task.delay(task_id, data["arrival_date_from"], data["arrival_date_to"], data["flight_nbr"], folder_name)

    # Synchronous wait logic
    max_wait_time = 300  # 5 minutes
    elapsed_time = 0
    polling_interval = 2  # Check every 2 seconds

    while elapsed_time < max_wait_time:
        db.refresh(task)  # Refresh the task state from the database
        if task.status in ["completed", "failed"]:
            return {
                "status": task.status,
                "message": task.status,
                "folder": task.folder_path if task.status == "completed" else None,
            }
        await asyncio.sleep(polling_interval)
        elapsed_time += polling_interval

    # Timeout
    raise HTTPException(status_code=408, detail="Task timed out. Please check the status later.")

@router.post("/combined_operation")
async def combined_operation(
    request: CombinedRequest, db: Session = Depends(get_db)
):
    # Step 1: Extract data from the request
    data = request.dict()
    arrival_date_from = data["arrival_date_from"]
    arrival_date_to = data["arrival_date_to"]
    flight_nbr = data["flight_nbr"]

    firstname = data.get("firstname", "")
    surname = data.get("surname", "")
    dob = data.get("dob", "")
    iata_o = data.get("iata_o", "")
    iata_d = data.get("iata_d", "")
    city_name = data.get("city_name", "")
    address = data.get("address", "")
    sex = data.get("sex", "")
    nationality = data.get("nationality", "")
    nameThreshold = data.get("nameThreshold", 0.0)
    ageThreshold = data.get("ageThreshold", 0.0)
    locationThreshold = data.get("locationThreshold", 0.0)

    # Step 2: Create and start the task
    task_id = str(uuid.uuid4())
    folder_name = f"task_{task_id}"
    create_task_folder(folder_name)

    task = Task(id=task_id, folder_path=folder_name, status="pending")
    db.add(task)
    db.commit()

    logging.info(f"Task {task_id} created with folder {folder_name}")

    process_task.delay(task_id, arrival_date_from, arrival_date_to, flight_nbr, folder_name)
    logging.info(f"Task {task_id} started for flight search.")

    # Step 3: Wait for the task to complete
    max_wait_time = 300  # 5 minutes
    elapsed_time = 0
    polling_interval = 2  # Check every 2 seconds

    while elapsed_time < max_wait_time:
        db.refresh(task)
        if task.status == "completed":
            break
        elif task.status == "failed":
            return {
                "status": "error",
                "message": "Task processing failed. No flights found."
            }
        await asyncio.sleep(polling_interval)
        elapsed_time += polling_interval

    if task.status != "completed":
        return {
            "status": "error",
            "message": "Task timed out while processing flights."
        }

    # Step 4: Check if any flight IDs were found
    if not task.flight_ids:
        return {
            "status": "error",
            "message": "No flights found within the specified parameters."
        }

    # Step 5: Perform similarity search
    logging.info(f"Starting similarity search for task {task_id}, folder {folder_name}, with parameters: {firstname}, {surname}, {dob}, {iata_o}, {iata_d}, {city_name}, {address}, {nameThreshold}, {ageThreshold}, {locationThreshold}")
    celery_task = perform_similarity_search_task.delay(
        task_id, firstname, surname, dob, iata_o, iata_d, city_name, address,
        sex, nationality, folder_name, nameThreshold, ageThreshold, locationThreshold
    )
    logging.info(f"Task {task_id} started for similarity search.")

    # Step 6: Wait for similarity search to complete
    try:
        result = celery_task.get(timeout=300)
    except Exception as e:
        logging.error(f"Error during similarity search: {e}")
        return {
            "status": "error",
            "message": "Error during similarity search."
        }

    if result["status"] != "success":
        return {
            "status": "error",
            "message": "Similarity search failed."
        }

    # Step 7: Check if any similar passengers were found
    if not result["data"]:
        return {
            "status": "success",
            "message": "No similar passengers found.",
            "task_id": task_id,
            "data": []
        }

    # Step 8: Return the final results
    return {
        "status": "success",
        "message": "Operation completed successfully.",
        "task_id": task_id,
        "data": result["data"]
    }

@router.post("/combined_operation_new")
async def combined_operation_new(request: CombinedRequest, db: Session = Depends(get_db)):
    # Step 1: Extract data from the request
    data = request.dict()
    arrival_date_from = data["arrival_date_from"]
    arrival_date_to = data["arrival_date_to"]
    flight_nbr = data["flight_nbr"]

    firstname = data.get("firstname", "")
    surname = data.get("surname", "")
    dob = data.get("dob", "")
    iata_o = data.get("iata_o", "")
    iata_d = data.get("iata_d", "")
    city_name = data.get("city_name", "")
    address = data.get("address", "")
    sex = data.get("sex", "")
    nationality = data.get("nationality", "")
    nameThreshold = data.get("nameThreshold", 0.0)
    ageThreshold = data.get("ageThreshold", 0.0)
    locationThreshold = data.get("locationThreshold", 0.0)

    # Step 2: Create and start the task
    task_id = str(uuid.uuid4())
    folder_name = f"task_{task_id}"
    # create_task_folder(folder_name)
    # logging.info(f"Task {task_id} created with folder {folder_name}")

    task = Task(id=task_id, folder_path=folder_name, status="pending")
    db.add(task)
    db.commit()

    logging.info(f"Task {task_id} created with folder {folder_name}")
    retrieveng_from_new_API.delay(arrival_date_from, arrival_date_to, task_id)
    logging.info(f"Starting similarity search for task {task_id}, folder {folder_name}, with parameters: {firstname}, {surname}, {dob}, {iata_o}, {iata_d}, {city_name}, {address}, {nameThreshold}, {ageThreshold}, {locationThreshold}")
    celery_task = perform_similarity_search_task.delay(
        task_id, firstname, surname, dob, iata_o, iata_d, city_name, address,
        sex, nationality, folder_name, nameThreshold, ageThreshold, locationThreshold
    )
    logging.info(f"task {task_id} done for similarity search. result: {celery_task}")
    # Step 6: Wait for similarity search to complete
    try:
        result = celery_task.get(timeout=300)
    except Exception as e:
        logging.error(f"Error during similarity search: {e}")
        return {
            "status": "error",
            "message": "Error during similarity search."
        }

    if result["status"] != "success":
        return {
            "status": "error",
            "message": "Similarity search failed."
        }

    # Step 7: Check if any similar passengers were found
    if not result["data"]:
        return {
            "status": "success",
            "message": "No similar passengers found.",
            "task_id": task_id,
            "data": []
        }

    # Step 8: Return the final results
    return {
        "status": "success",
        "message": "Operation completed successfully.",
        "task_id": task_id,
        "data": result["data"]
    }







@router.get("/flight_ids/{task_id}")
async def get_flight_ids(task_id: str, db: Session = Depends(get_db)):
    task = get_task_by_id(task_id, db)

    flight_ids = task.flight_ids.split(",") if task.flight_ids else []
    unique_flight_id_count = len(set(flight_ids))

    return {
        "flight_ids": flight_ids,
        "unique_flight_id_count": unique_flight_id_count,
        "unique_flight_id_count_check": task.flight_count,
        "task_id": task_id,
    }

@router.get("/result/{task_id}")
async def get_result(task_id: str, db: Session = Depends(get_db)):
    task = get_task_by_id(task_id, db)

    if task.status == "completed":
        return {"status": "completed", "message": "completed", "folder": task.folder_path}
    return {"status": task.status, "message": "Task is still in progress."}

@router.get("/sse/{task_id}", response_class=StreamingResponse)
async def sse_task_status(task_id: str, db: Session = Depends(get_db)):
    async def event_generator():
        while True:
            # Use a new session for each iteration to get the latest status
            with SessionLocal() as session:
                task = session.query(Task).get(task_id)
                if task.status == "completed":
                    yield f"data: {{\"status\": \"completed\", \"message\": \"Task completed\", \"folder\": \"{task.folder_path}\"}}\n\n"
                    break
                elif task.status == "failed":
                    yield f"data: {{\"status\": \"failed\", \"message\": \"Task failed\"}}\n\n"
                    break
                else:
                    yield f"data: {{\"status\": \"{task.status}\", \"message\": \"Task is still in progress.\"}}\n\n"
            await asyncio.sleep(1)  # Delay before the next status check

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@router.post("/perform_similarity_search", response_class=JSONResponse)
async def handle_similarity_search(similarity_search: SimilaritySearchRequest, db: Session = Depends(get_db)):
    try:
        data = similarity_search.dict()
        task = get_task_by_id(data["task_id"], db)

        folder_path = task.folder_path
        celery_task = perform_similarity_search_task.delay(
            data["task_id"],
            data.get("firstname", ""),
            data.get("surname", ""),
            data.get("dob"),
            data.get("iata_o", ""),
            data.get("iata_d", ""),
            data.get("city_name", ""),
            data.get("address", ""),
            data.get("sex", ""),
            data.get("nationality", ""),
            folder_path,
            data.get("nameThreshold", 0.0),
            data.get("ageThreshold", 0.0),
            data.get("locationThreshold", 0.0),
        )

        result = celery_task.get(timeout=300)  # Wait for task completion
        if result["status"] != "success":
            raise HTTPException(
                status_code=500, detail={"status": "error", "message": "Error during similarity search"}
            )

        return {
            "status": "success",
            "data": result["data"],
            "message": "Similar passengers found successfully",
        }
    except HTTPException as e:
        raise e
    except Exception as e:
        logging.error(f"Error during similarity search: {e}")
        raise HTTPException(status_code=500, detail={"status": "error", "message": str(e)})


@router.post("/delete_task", response_class=JSONResponse)
async def delete_task(request: Request, db: Session = Depends(get_db)):
    try:
        data = await request.json()
        task_id = data.get("task_id")
        if not task_id:
            raise HTTPException(status_code=400, detail={"status": "error", "message": "Task ID is required"})

        task = get_task_by_id(task_id, db)
        blobs_to_delete = list_files_in_directory(task.folder_path)
        for blob in blobs_to_delete:
            delete_from_local_storage(blob)

        shutil.rmtree(task.folder_path, ignore_errors=True)
        db.delete(task)
        db.commit()
        return {"status": "success", "message": "Task deleted successfully"}
    except HTTPException as e:
        raise e
    except Exception as e:
        logging.error(f"Error deleting task: {e}")
        return {"status": "error", "message": str(e)}


@router.get("/test-db/")
async def test_db_connection(db: Session = Depends(get_db)):
    try:
        db.execute(text("SELECT 1"))
        return {"status": "success", "message": "Database connection successful!"}
    except Exception as e:
        return {"status": "error", "message": str(e)}
