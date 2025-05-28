from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from dotenv import load_dotenv
import os

load_dotenv("environment.env")

templates = Jinja2Templates(directory="app_new/templates")  # Adjust path if needed

def create_app():
    app = FastAPI()

    # Mount static files
    app.mount("/static", StaticFiles(directory="app_new/static"), name="static")

    # Include new router
    from .main import router  # make sure `main.py` has `router = APIRouter()`
    app.include_router(router)

    return app

app = create_app()
