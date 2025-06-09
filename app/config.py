import os
from dotenv import load_dotenv

load_dotenv()

CELERY_BROKER_URL = os.getenv('CELERY_BROKER_URL')
result_backend= os.getenv('result_backend')

PREPROCESSOR_DIR = "model"
XML_FOLDER = "data/raw_xml"

CATEGORICAL_FEATURES = ["gender", "nationality"]
NUMERIC_FEATURES = ["relative_age", "dep_lat", "dep_lon", "arr_lat", "arr_lon"]
TEXT_FEATURES = ["surname", "address", "city", "firstname"]
