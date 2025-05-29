import pandas as pd
import numpy as np
from fastapi import APIRouter, Depends
import logging


from app.pipeline import run_similarity_pipeline
from fastapi.responses import JSONResponse
from app.loc_access import LocDataAccess



from app.schemas import CombinedRequest

router = APIRouter()

logging.basicConfig(
    level=logging.INFO,  # <-- show info-level logs
    format="%(asctime)s [%(levelname)s] %(message)s",
)


@router.post("/combined_operation")
async def combined_operation(request: CombinedRequest):
    data = request.dict()
    data["shards"] = [
        "2019-01-01_2019-02-28",
        "2019-03-01_2019-04-30",
        "2019-05-01_2019-06-30",
        "2019-07-01_2019-08-31",
        "2019-09-01_2019-10-31",
        "2019-11-01_2019-12-31",
    ]
    result = run_similarity_pipeline(data)
    return result

