from celery import Celery
from app.config import CELERY_BROKER_URL, CELERY_RESULT_BACKEND

celery_app = Celery(
    "faiss_similarity_service",
    broker=CELERY_BROKER_URL,
    backend=CELERY_RESULT_BACKEND
)

celery_app.conf.task_track_started = True
celery_app.conf.result_expires = 3600  # 1 hour
