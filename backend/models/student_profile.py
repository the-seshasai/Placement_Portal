from datetime import datetime, timezone

from extensions import db


class StudentProfile(db.Model):
    """Student-specific data, 1:1 with a User row (role == 'student')."""

    __tablename__ = "student_profiles"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False
    )

    branch = db.Column(db.String(100), nullable=False)
    cgpa = db.Column(db.Float, nullable=False)
    grad_year = db.Column(db.Integer, nullable=False)
    phone = db.Column(db.String(30))
    resume_path = db.Column(db.String(255))

    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    user = db.relationship("User", back_populates="student_profile")
    applications = db.relationship(
        "Application", back_populates="student", cascade="all, delete-orphan"
    )

    __table_args__ = (
        db.CheckConstraint("cgpa >= 0 AND cgpa <= 10", name="ck_student_profiles_cgpa_range"),
    )

    def __repr__(self):
        return f"<StudentProfile {self.branch} {self.grad_year}>"
