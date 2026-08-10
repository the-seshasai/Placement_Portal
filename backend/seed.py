"""Programmatic DB setup + seed script.

Run with:  python seed.py

Creates the SQLite schema from the SQLAlchemy models and the single admin
user (credentials from config/env: ADMIN_EMAIL / ADMIN_PASSWORD / ADMIN_NAME).
Safe to re-run — it only creates the admin if it doesn't already exist.
"""

from app import create_app
from extensions import db
from models.user import User, Role

app = create_app()

with app.app_context():
    db.create_all()
    print("Database schema created.")

    admin_email = app.config["ADMIN_EMAIL"]
    existing = User.query.filter_by(email=admin_email).first()
    if existing:
        print(f"Admin user already exists ({admin_email}), skipping.")
    else:
        admin = User(
            name=app.config["ADMIN_NAME"],
            email=admin_email,
            role=Role.ADMIN,
        )
        admin.set_password(app.config["ADMIN_PASSWORD"])
        db.session.add(admin)
        db.session.commit()
        print(f"Admin user created: {admin_email}")
