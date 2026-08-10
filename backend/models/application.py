from datetime import datetime, timezone

from extensions import db


class ApplicationStatus:
    APPLIED = "applied"
    SHORTLISTED = "shortlisted"
    SELECTED = "selected"
    REJECTED = "rejected"
    ALL = (APPLIED, SHORTLISTED, SELECTED, REJECTED)


class Application(db.Model):
    __tablename__ = "applications"

    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(
        db.Integer, db.ForeignKey("student_profiles.id", ondelete="CASCADE"), nullable=False
    )
    drive_id = db.Column(
        db.Integer, db.ForeignKey("placement_drives.id", ondelete="CASCADE"), nullable=False
    )

    status = db.Column(db.String(20), nullable=False, default=ApplicationStatus.APPLIED)
    application_date = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    interview_date = db.Column(db.DateTime)
    remarks = db.Column(db.Text)

    updated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    student = db.relationship("StudentProfile", back_populates="applications")
    drive = db.relationship("PlacementDrive", back_populates="applications")

    __table_args__ = (
        db.UniqueConstraint("student_id", "drive_id", name="uq_applications_student_drive"),
        db.CheckConstraint(f"status IN {ApplicationStatus.ALL}", name="ck_applications_status_valid"),
    )

    def __repr__(self):
        return f"<Application student={self.student_id} drive={self.drive_id} ({self.status})>"
