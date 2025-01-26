import os
from dotenv import load_dotenv

load_dotenv('environment.env')

DATABASE_URL = os.getenv("DATABASE_URL")
CELERY_BROKER_URL = os.getenv('CELERY_BROKER_URL')
CELERY_RESULT_BACKEND = os.getenv('CELERY_RESULT_BACKEND')
TOKEN_URL = os.getenv("TOKEN_URL")
FLIGHT_URL = os.getenv("FLIGHT_URL")
USERNAME = os.getenv("USERNAME")
ACCESS_TOKEN = os.getenv("ACCESS_TOKEN")
REFRESH_TOKEN = os.getenv("REFRESH_TOKEN")
