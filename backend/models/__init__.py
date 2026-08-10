"""SQLAlchemy models package.

Every model module is imported here so `db.create_all()` / seed.py sees all
tables and relationships resolve correctly.
"""

from models.user import User, Role
from models.company import Company, ApprovalStatus
from models.student_profile import StudentProfile
from models.drive import PlacementDrive, DriveStatus
from models.application import Application, ApplicationStatus

__all__ = [
    "User",
    "Role",
    "Company",
    "ApprovalStatus",
    "StudentProfile",
    "PlacementDrive",
    "DriveStatus",
    "Application",
    "ApplicationStatus",
]
