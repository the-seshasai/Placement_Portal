"""Lightweight Celery producer.

Importable from the Flask web server process to *enqueue* tasks
(`celery.send_task(...)`) without ever creating a Flask app in that
process. The worker/beat processes load `tasks.py` instead (via
`celery -A tasks worker` / `celery -A tasks beat`), which imports this
`celery` instance, registers the actual task implementations, and binds
them to a Flask app context.

Run (from `backend/`, venv active):
    celery -A tasks worker --loglevel=info
    celery -A tasks beat --loglevel=info
"""

from celery import Celery
from celery.schedules import crontab

from config import Config

celery = Celery("ppa", broker=Config.CELERY_BROKER_URL, backend=Config.CELERY_RESULT_BACKEND)
celery.conf.timezone = "UTC"
celery.conf.beat_schedule = {
    "daily-deadline-reminders": {
        "task": "tasks.send_deadline_reminders",
        "schedule": crontab(hour=9, minute=0),
    },
    "monthly-activity-report": {
        "task": "tasks.send_monthly_activity_report",
        "schedule": crontab(day_of_month=1, hour=8, minute=0),
    },
}
