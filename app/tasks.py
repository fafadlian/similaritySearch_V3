from app.pipeline import run_similarity_pipeline
from celery import Celery

app = Celery("similarity_app")
app.config_from_object("app.config")  # optional, if you have config.py


@app.task(name="process_similarity_task")
def process_similarity_task(data: dict):
    return run_similarity_pipeline(data)
