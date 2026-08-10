from datetime import datetime, timezone

from extensions import db


class ApprovalStatus:
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    ALL = (PENDING, APPROVED, REJECTED)


class Company(db.Model):
    """Company profile, 1:1 with a User row (role == 'company')."""

    __tablename__ = "companies"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False
    )

    company_name = db.Column(db.String(150), nullable=False)
    hr_contact_name = db.Column(db.String(120), nullable=False)
    hr_contact_phone = db.Column(db.String(30))
    website = db.Column(db.String(255))
    description = db.Column(db.Text)

    approval_status = db.Column(db.String(20), nullable=False, default=ApprovalStatus.PENDING)

    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    user = db.relationship("User", back_populates="company")
    drives = db.relationship(
        "PlacementDrive", back_populates="company", cascade="all, delete-orphan"
    )

    __table_args__ = (
        db.CheckConstraint(
            f"approval_status IN {ApprovalStatus.ALL}", name="ck_companies_approval_status_valid"
        ),
    )

    def __repr__(self):
        return f"<Company {self.company_name} ({self.approval_status})>"
