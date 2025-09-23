# app/response_utils.py
from fastapi.responses import JSONResponse

def success_response(message: str, data=None):
    return JSONResponse(
        status_code=200,
        content={
            "status": "success",
            "message": message,
            "data": data if data is not None else []
        }
    )

def error_response(message: str, status_code: int = 400):
    return JSONResponse(
        status_code=status_code,
        content={
            "status": "error",
            "message": message,
            "data": []
        }
    )
