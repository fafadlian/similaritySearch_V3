import os
from dotenv import load_dotenv

load_dotenv()

CELERY_BROKER_URL = os.getenv('CELERY_BROKER_URL')
CELERY_RESULT_BACKEND = os.getenv('CELERY_RESULT_BACKEND')

CATEGORICAL_FEATURES = ["gender", "nationality"]
NUMERIC_FEATURES = ["relative_age", "dep_lat", "dep_lon", "arr_lat", "arr_lon"]
TEXT_FEATURES = ["surname", "address", "city", "given_name"]
