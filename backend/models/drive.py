from datetime import datetime, timezone

from extensions import db


class DriveStatus:
    PENDING = "pending"    # awaiting admin approval
    APPROVED = "approved"  # visible to eligible students
    REJECTED = "rejected"
    CLOSED = "closed"      # past deadline / manually closed
    ALL = (PENDING, APPROVED, REJECTED, CLOSED)


class PlacementDrive(db.Model):
    __tablename__ = "placement_drives"

    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(
        db.Integer, db.ForeignKey("companies.id", ondelete="CASCADE"), nullable=False
    )

    job_title = db.Column(db.String(150), nullable=False)
    job_description = db.Column(db.Text, nullable=False)
    package_ctc = db.Column(db.String(60))

    # Eligibility
    eligible_branches = db.Column(db.String(255), nullable=False)  # comma-separated, e.g. "CSE,ECE"
    min_cgpa = db.Column(db.Float, nullable=False, default=0)
    eligible_grad_year = db.Column(db.Integer, nullable=False)

    application_deadline = db.Column(db.DateTime, nullable=False)
    status = db.Column(db.String(20), nullable=False, default=DriveStatus.PENDING)

    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    company = db.relationship("Company", back_populates="drives")
    applications = db.relationship(
        "Application", back_populates="drive", cascade="all, delete-orphan"
    )

    __table_args__ = (
        db.CheckConstraint(f"status IN {DriveStatus.ALL}", name="ck_drives_status_valid"),
    )

    def eligible_branches_list(self):
        return [b.strip() for b in self.eligible_branches.split(",") if b.strip()]

    def __repr__(self):
        return f"<PlacementDrive {self.job_title} ({self.status})>"
