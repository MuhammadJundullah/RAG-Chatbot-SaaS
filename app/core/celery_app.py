from celery import Celery
from app.core.config import settings

# Initialize Celery
celery_app = Celery(
    "tasks",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=["app.tasks.document_tasks"]
)

celery_app.conf.update(
    task_track_started=True,
)
