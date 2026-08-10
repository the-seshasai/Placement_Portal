import os
from datetime import timedelta

BASE_DIR = os.path.abspath(os.path.dirname(__file__))


class Config:
    """Base config. Values are overridable via environment variables so the
    whole stack stays configurable for the demo machine (port 8001, etc.)."""

    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-change-me")

    # --- Server ---
    PORT = int(os.environ.get("PORT", 8001))
    HOST = os.environ.get("HOST", "0.0.0.0")

    # --- Database (SQLite, created programmatically via SQLAlchemy) ---
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL", f"sqlite:///{os.path.join(BASE_DIR, 'instance', 'ppa.db')}"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # --- Redis / Caching ---
    REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
    CACHE_TYPE = "RedisCache"
    CACHE_REDIS_URL = REDIS_URL
    CACHE_DEFAULT_TIMEOUT = 60

    # --- Celery ---
    CELERY_BROKER_URL = os.environ.get("CELERY_BROKER_URL", REDIS_URL)
    CELERY_RESULT_BACKEND = os.environ.get("CELERY_RESULT_BACKEND", REDIS_URL)

    # --- Uploads ---
    UPLOAD_FOLDER = os.environ.get(
        "UPLOAD_FOLDER", os.path.join(BASE_DIR, "uploads", "resumes")
    )
    REPORTS_FOLDER = os.environ.get(
        "REPORTS_FOLDER", os.path.join(BASE_DIR, "reports")
    )
    MAX_CONTENT_LENGTH = 5 * 1024 * 1024  # 5 MB resume upload cap
    ALLOWED_RESUME_EXTENSIONS = {"pdf", "doc", "docx"}

    # --- Session / Auth ---
    PERMANENT_SESSION_LIFETIME = timedelta(hours=8)
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"

    # --- Mail (Flask-Mail, local SMTP debug server for demo) ---
    MAIL_SERVER = os.environ.get("MAIL_SERVER", "localhost")
    MAIL_PORT = int(os.environ.get("MAIL_PORT", 1025))
    MAIL_USE_TLS = os.environ.get("MAIL_USE_TLS", "false").lower() == "true"
    MAIL_USERNAME = os.environ.get("MAIL_USERNAME")
    MAIL_PASSWORD = os.environ.get("MAIL_PASSWORD")
    MAIL_DEFAULT_SENDER = os.environ.get("MAIL_DEFAULT_SENDER", "ppa-noreply@localhost")
    ADMIN_NOTIFICATION_EMAIL = os.environ.get("ADMIN_NOTIFICATION_EMAIL", "admin@localhost")

    # --- Notifications (Google Chat webhook for reminders) ---
    GOOGLE_CHAT_WEBHOOK_URL = os.environ.get("GOOGLE_CHAT_WEBHOOK_URL", "")
    REMINDER_WINDOW_HOURS = int(os.environ.get("REMINDER_WINDOW_HOURS", 24))

    # --- Seed admin (used only by `flask create-admin` / seed.py) ---
    ADMIN_EMAIL = os.environ.get("ADMIN_EMAIL", "admin@ppa.local")
    ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "ChangeMe123!")
    ADMIN_NAME = os.environ.get("ADMIN_NAME", "Placement Admin")


class DevelopmentConfig(Config):
    DEBUG = True


class ProductionConfig(Config):
    DEBUG = False


config_by_name = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
}
