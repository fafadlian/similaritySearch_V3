# celery_init.py
from celery import Celery
import os
from dotenv import load_dotenv
import logging

load_dotenv('environment.env')

def make_celery(app_name=__name__):
    celery = Celery(app_name, include=['app.tasks'])
    celery.config_from_object('app.celeryconfig')

    # Configure logging
    handler = logging.StreamHandler()
    handler.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)

    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    logger.addHandler(handler)

    # Prevent Celery from hijacking the root logger
    celery.conf.update(
        worker_hijack_root_logger=False,
    )

    return celery

celery = make_celery()
