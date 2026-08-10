from datetime import datetime

from flask import Blueprint, request, jsonify
from flask_login import current_user

from extensions import db, cache
from decorators import roles_required
from caching import DEFAULT_TIMEOUT, scoped_cache_key, bump_cache_version
from models.user import Role
from models.company import Company, ApprovalStatus
from models.drive import PlacementDrive, DriveStatus
from models.application import Application, ApplicationStatus
from validation import is_valid_cgpa, is_valid_grad_year

company_bp = Blueprint("company", __name__)


def _error(message, status=400):
    return jsonify({"error": message}), status


def _current_company():
    return current_user.company


def _serialize_company(company):
    return {
        "id": company.id,
        "company_name": company.company_name,
        "hr_contact_name": company.hr_contact_name,
        "hr_contact_phone": company.hr_contact_phone,
        "website": company.website,
        "description": company.description,
        "approval_status": company.approval_status,
        "email": company.user.email,
    }


def _serialize_drive(drive, include_applicant_count=True):
    payload = {
        "id": drive.id,
        "job_title": drive.job_title,
        "job_description": drive.job_description,
        "package_ctc": drive.package_ctc,
        "eligible_branches": drive.eligible_branches_list(),
        "min_cgpa": drive.min_cgpa,
        "eligible_grad_year": drive.eligible_grad_year,
        "application_deadline": drive.application_deadline.isoformat() if drive.application_deadline else None,
        "status": drive.status,
        "created_at": drive.created_at.isoformat() if drive.created_at else None,
    }
    if include_applicant_count:
        payload["applicant_count"] = len(drive.applications)
    return payload


def _serialize_application(app_):
    student = app_.student
    return {
        "id": app_.id,
        "drive_id": app_.drive_id,
        "job_title": app_.drive.job_title,
        "student_id": student.id,
        "student_name": student.user.name,
        "student_email": student.user.email,
        "branch": student.branch,
        "cgpa": student.cgpa,
        "grad_year": student.grad_year,
        "resume_path": student.resume_path,
        "status": app_.status,
        "application_date": app_.application_date.isoformat() if app_.application_date else None,
        "interview_date": app_.interview_date.isoformat() if app_.interview_date else None,
        "remarks": app_.remarks,
    }


def _parse_deadline(value):
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        return None


@company_bp.route("/profile", methods=["GET"])
@roles_required(Role.COMPANY)
def get_profile():
    return jsonify(_serialize_company(_current_company()))


@company_bp.route("/profile", methods=["PUT"])
@roles_required(Role.COMPANY)
def update_profile():
    company = _current_company()
    data = request.get_json(silent=True) or {}

    company_name = (data.get("company_name") or "").strip()
    hr_contact_name = (data.get("hr_contact_name") or "").strip()
    if not company_name:
        return _error("Company name is required", 400)
    if not hr_contact_name:
        return _error("HR contact name is required", 400)

    company.company_name = company_name
    company.hr_contact_name = hr_contact_name
    company.hr_contact_phone = (data.get("hr_contact_phone") or "").strip() or None
    company.website = (data.get("website") or "").strip() or None
    company.description = (data.get("description") or "").strip() or None
    db.session.commit()
    bump_cache_version()
    return jsonify(_serialize_company(company))


@company_bp.route("/dashboard", methods=["GET"])
@roles_required(Role.COMPANY)
@cache.cached(timeout=DEFAULT_TIMEOUT, key_prefix=scoped_cache_key)
def dashboard():
    company = _current_company()
    drives = PlacementDrive.query.filter_by(company_id=company.id).order_by(PlacementDrive.created_at.desc()).all()
    total_applicants = sum(len(d.applications) for d in drives)
    return jsonify(
        {
            "company": _serialize_company(company),
            "drive_count": len(drives),
            "total_applicants": total_applicants,
            "drives": [_serialize_drive(d) for d in drives],
        }
    )


@company_bp.route("/drives", methods=["GET"])
@roles_required(Role.COMPANY)
def list_drives():
    company = _current_company()
    drives = PlacementDrive.query.filter_by(company_id=company.id).order_by(PlacementDrive.created_at.desc()).all()
    return jsonify([_serialize_drive(d) for d in drives])


@company_bp.route("/drives", methods=["POST"])
@roles_required(Role.COMPANY)
def create_drive():
    company = _current_company()
    if company.approval_status != ApprovalStatus.APPROVED:
        return _error("Your company must be approved by the admin before creating drives", 403)

    data = request.get_json(silent=True) or {}
    job_title = (data.get("job_title") or "").strip()
    job_description = (data.get("job_description") or "").strip()
    package_ctc = (data.get("package_ctc") or "").strip() or None
    eligible_branches = data.get("eligible_branches")
    min_cgpa = data.get("min_cgpa")
    eligible_grad_year = data.get("eligible_grad_year")
    deadline_raw = data.get("application_deadline")

    if not job_title:
        return _error("Job title is required", 400)
    if not job_description:
        return _error("Job description is required", 400)

    if isinstance(eligible_branches, list):
        eligible_branches = ",".join(b.strip() for b in eligible_branches if b.strip())
    eligible_branches = (eligible_branches or "").strip()
    if not eligible_branches:
        return _error("At least one eligible branch is required", 400)

    if not is_valid_cgpa(min_cgpa):
        return _error("Minimum CGPA must be a number between 0 and 10", 400)
    min_cgpa = float(min_cgpa)

    if not is_valid_grad_year(eligible_grad_year):
        return _error("Eligible graduation year is invalid", 400)
    eligible_grad_year = int(eligible_grad_year)

    deadline = _parse_deadline(deadline_raw)
    if not deadline:
        return _error("A valid application deadline (ISO date/time) is required", 400)

    drive = PlacementDrive(
        company_id=company.id,
        job_title=job_title,
        job_description=job_description,
        package_ctc=package_ctc,
        eligible_branches=eligible_branches,
        min_cgpa=min_cgpa,
        eligible_grad_year=eligible_grad_year,
        application_deadline=deadline,
        status=DriveStatus.PENDING,
    )
    db.session.add(drive)
    db.session.commit()
    bump_cache_version()
    return jsonify(_serialize_drive(drive)), 201


def _own_drive_or_404(drive_id):
    drive = db.session.get(PlacementDrive, drive_id)
    if not drive or drive.company_id != _current_company().id:
        return None
    return drive


@company_bp.route("/drives/<int:drive_id>/applications", methods=["GET"])
@roles_required(Role.COMPANY)
def drive_applications(drive_id):
    drive = _own_drive_or_404(drive_id)
    if not drive:
        return _error("Drive not found", 404)

    status = request.args.get("status")
    query = Application.query.filter_by(drive_id=drive.id)
    if status:
        query = query.filter_by(status=status)
    applications = query.order_by(Application.application_date.desc()).all()
    return jsonify([_serialize_application(a) for a in applications])


@company_bp.route("/applications/<int:application_id>", methods=["PUT"])
@roles_required(Role.COMPANY)
def update_application(application_id):
    app_ = db.session.get(Application, application_id)
    if not app_ or app_.drive.company_id != _current_company().id:
        return _error("Application not found", 404)

    data = request.get_json(silent=True) or {}
    status = data.get("status")
    if status is not None:
        if status not in ApplicationStatus.ALL:
            return _error(f"Status must be one of {ApplicationStatus.ALL}", 400)
        app_.status = status

    if "interview_date" in data:
        interview_date = _parse_deadline(data.get("interview_date")) if data.get("interview_date") else None
        app_.interview_date = interview_date

    if "remarks" in data:
        app_.remarks = (data.get("remarks") or "").strip() or None

    db.session.commit()
    bump_cache_version()
    return jsonify(_serialize_application(app_))
