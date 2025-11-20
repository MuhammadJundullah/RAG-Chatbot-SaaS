from celery import Celery
from celery.schedules import crontab
from app.core.config import settings

# Initialize Celery
celery_app = Celery(
    "tasks",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=[
        "app.tasks.document_tasks",
        "app.tasks.subscription_tasks"
    ]
)

celery_app.conf.update(
    task_track_started=True,
    beat_schedule={
        'check-expired-subscriptions-daily': {
            'task': 'tasks.check_expired_subscriptions',
            'schedule': crontab(hour=0, minute=5),  # Runs daily at 00:05
        },
    },
)
