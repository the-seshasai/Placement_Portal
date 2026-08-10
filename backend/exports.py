"""Shared key format for the async CSV export status, written by the Celery
task (tasks.py) and polled by the student routes — kept separate so
student_routes.py never has to import tasks.py (which binds a Flask app)."""

EXPORT_CACHE_PREFIX = "ppa:export:student:"


def export_cache_key(student_id):
    return f"{EXPORT_CACHE_PREFIX}{student_id}"
