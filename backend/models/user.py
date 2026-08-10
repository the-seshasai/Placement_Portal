from datetime import datetime, timezone

from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

from extensions import db


class Role:
    ADMIN = "admin"
    COMPANY = "company"
    STUDENT = "student"
    ALL = (ADMIN, COMPANY, STUDENT)


class User(db.Model, UserMixin):
    """Unified auth identity for all three roles. Role-specific data lives in
    Company / StudentProfile, each linked 1:1 back to a User row."""

    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False)

    is_active_flag = db.Column("is_active", db.Boolean, nullable=False, default=True)
    blacklisted = db.Column(db.Boolean, nullable=False, default=False)

    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    company = db.relationship(
        "Company", back_populates="user", uselist=False, cascade="all, delete-orphan"
    )
    student_profile = db.relationship(
        "StudentProfile", back_populates="user", uselist=False, cascade="all, delete-orphan"
    )

    __table_args__ = (
        db.CheckConstraint(f"role IN {Role.ALL}", name="ck_users_role_valid"),
    )

    def set_password(self, raw_password):
        self.password_hash = generate_password_hash(raw_password)

    def check_password(self, raw_password):
        return check_password_hash(self.password_hash, raw_password)

    # Flask-Login uses is_active to gate login; blacklisted/deactivated
    # accounts (by the admin) should not be able to authenticate.
    @property
    def is_active(self):
        return self.is_active_flag and not self.blacklisted

    def __repr__(self):
        return f"<User {self.email} ({self.role})>"
