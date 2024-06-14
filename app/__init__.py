from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from dotenv import load_dotenv
from app.database import engine
from app.models import Base
from app.celery_init import make_celery
# from starlette.staticfiles import StaticFiles

import os

load_dotenv('environment.env')

templates = Jinja2Templates(directory="app/templates")


def create_app():
    app = FastAPI()

    # Mount the static directory to serve static files
    app.mount("/static", StaticFiles(directory="app/static"), name="static")

    # Set up the Jinja2 templates
    # templates = Jinja2Templates(directory="app/templates")

    from . import main  # Import the routes from main
    app.include_router(main.router)
    
    return app


app = create_app()
celery = make_celery()

