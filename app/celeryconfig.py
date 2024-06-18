# app/celeryconfig.py

import os
from dotenv import load_dotenv
from celery.schedules import crontab

load_dotenv('environment.env')

broker_url = os.getenv('CELERY_BROKER_URL')
result_backend = os.getenv('CELERY_RESULT_BACKEND')
worker_concurrency = os.cpu_count()

task_serializer = 'json'
result_serializer = 'json'
accept_content = ['json']
timezone = 'UTC'
enable_utc = True

beat_schedule = {
    'delete-old-tasks': {
        'task': 'app.tasks.delete_old_tasks',
        'schedule': crontab(hour='*/2'),  # Run every hour
    },
}
