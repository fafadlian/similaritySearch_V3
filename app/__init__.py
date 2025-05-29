from fastapi import FastAPI
from dotenv import load_dotenv

load_dotenv()

def create_app():
    app = FastAPI()
    from .main import router
    app.include_router(router)
    return app

