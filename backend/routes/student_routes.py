import os
from datetime import datetime, timezone

from flask import Blueprint, request, jsonify, current_app, send_from_directory
from flask_login import current_user
from werkzeug.utils import secure_filename

from extensions import db, cache
from decorators import roles_required
from caching import DEFAULT_TIMEOUT, scoped_cache_key, bump_cache_version
from celery_app import celery
from exports import export_cache_key
from models.user import User, Role
from models.student_profile import StudentProfile
from models.drive import PlacementDrive, DriveStatus
from models.company import Company
from models.application import Application, ApplicationStatus
from validation import is_valid_cgpa, is_valid_grad_year

student_bp = Blueprint("student", __name__)


def _error(message, status=400):
    return jsonify({"error": message}), status


def _current_profile():
    return current_user.student_profile


def _serialize_profile(profile):
    return {
        "id": profile.id,
        "name": profile.user.name,
        "email": profile.user.email,
        "branch": profile.branch,
        "cgpa": profile.cgpa,
        "grad_year": profile.grad_year,
        "phone": profile.phone,
        "resume_path": profile.resume_path,
    }


def _is_eligible(profile, drive):
    return (
        profile.branch in drive.eligible_branches_list()
        and profile.cgpa >= drive.min_cgpa
        and profile.grad_year == drive.eligible_grad_year
    )


def _serialize_drive(drive, profile=None, applied_status=None):
    payload = {
        "id": drive.id,
        "company_name": drive.company.company_name,
        "job_title": drive.job_title,
        "job_description": drive.job_description,
        "package_ctc": drive.package_ctc,
        "eligible_branches": drive.eligible_branches_list(),
        "min_cgpa": drive.min_cgpa,
        "eligible_grad_year": drive.eligible_grad_year,
        "application_deadline": drive.application_deadline.isoformat() if drive.application_deadline else None,
        "status": drive.status,
    }
    if profile is not None:
        payload["eligible"] = _is_eligible(profile, drive)
    payload["already_applied"] = applied_status is not None
    payload["application_status"] = applied_status
    return payload


def _serialize_application(app_):
    drive = app_.drive
    return {
        "id": app_.id,
        "drive_id": drive.id,
        "job_title": drive.job_title,
        "company_name": drive.company.company_name,
        "package_ctc": drive.package_ctc,
        "status": app_.status,
        "application_date": app_.application_date.isoformat() if app_.application_date else None,
        "interview_date": app_.interview_date.isoformat() if app_.interview_date else None,
        "remarks": app_.remarks,
    }


@student_bp.route("/profile", methods=["GET"])
@roles_required(Role.STUDENT)
def get_profile():
    return jsonify(_serialize_profile(_current_profile()))


@student_bp.route("/profile", methods=["PUT"])
@roles_required(Role.STUDENT)
def update_profile():
    profile = _current_profile()
    data = request.get_json(silent=True) or {}

    branch = (data.get("branch") or "").strip()
    cgpa = data.get("cgpa")
    grad_year = data.get("grad_year")
    phone = (data.get("phone") or "").strip() or None

    if not branch:
        return _error("Branch is required")
    if not is_valid_cgpa(cgpa):
        return _error("CGPA must be a number between 0 and 10")
    if not is_valid_grad_year(grad_year):
        return _error("Graduation year is invalid")

    profile.branch = branch
    profile.cgpa = float(cgpa)
    profile.grad_year = int(grad_year)
    profile.phone = phone
    db.session.commit()
    bump_cache_version()
    return jsonify(_serialize_profile(profile))


@student_bp.route("/resume", methods=["POST"])
@roles_required(Role.STUDENT)
def upload_resume():
    profile = _current_profile()
    if "resume" not in request.files:
        return _error("No file uploaded (expected field name `resume`)")

    file = request.files["resume"]
    if not file.filename:
        return _error("No file selected")

    ext = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
    if ext not in current_app.config["ALLOWED_RESUME_EXTENSIONS"]:
        allowed = ", ".join(sorted(current_app.config["ALLOWED_RESUME_EXTENSIONS"]))
        return _error(f"Unsupported file type. Allowed: {allowed}")

    filename = secure_filename(f"student_{profile.id}.{ext}")
    filepath = os.path.join(current_app.config["UPLOAD_FOLDER"], filename)
    file.save(filepath)

    profile.resume_path = filename
    db.session.commit()
    return jsonify(_serialize_profile(profile))


@student_bp.route("/resume/<int:student_id>", methods=["GET"])
def get_resume(student_id):
    if not current_user.is_authenticated:
        return _error("Authentication required", 401)

    profile = db.session.get(StudentProfile, student_id)
    if not profile or not profile.resume_path:
        return _error("Resume not found", 404)

    allowed = False
    if current_user.role == Role.ADMIN:
        allowed = True
    elif current_user.role == Role.STUDENT and current_user.id == profile.user_id:
        allowed = True
    elif current_user.role == Role.COMPANY:
        company = current_user.company
        allowed = (
            db.session.query(Application.id)
            .join(PlacementDrive, PlacementDrive.id == Application.drive_id)
            .filter(Application.student_id == profile.id, PlacementDrive.company_id == company.id)
            .first()
            is not None
        )

    if not allowed:
        return _error("Forbidden", 403)

    return send_from_directory(current_app.config["UPLOAD_FOLDER"], profile.resume_path)


@student_bp.route("/drives", methods=["GET"])
@roles_required(Role.STUDENT)
@cache.cached(timeout=DEFAULT_TIMEOUT, key_prefix=scoped_cache_key)
def list_drives():
    profile = _current_profile()
    query = PlacementDrive.query.filter_by(status=DriveStatus.APPROVED)

    q = request.args.get("q")
    if q:
        like = f"%{q}%"
        query = query.join(Company).filter(
            db.or_(PlacementDrive.job_title.ilike(like), Company.company_name.ilike(like))
        )

    branch = request.args.get("branch")
    if branch:
        query = query.filter(PlacementDrive.eligible_branches.ilike(f"%{branch}%"))

    min_cgpa = request.args.get("min_cgpa", type=float)
    if min_cgpa is not None:
        query = query.filter(PlacementDrive.min_cgpa <= min_cgpa)

    grad_year = request.args.get("grad_year", type=int)
    if grad_year is not None:
        query = query.filter(PlacementDrive.eligible_grad_year == grad_year)

    drives = query.order_by(PlacementDrive.application_deadline.asc()).all()

    applied_map = {
        a.drive_id: a.status
        for a in Application.query.filter_by(student_id=profile.id).all()
    }

    eligible_only = request.args.get("eligible_only") == "true"
    results = []
    for d in drives:
        serialized = _serialize_drive(d, profile=profile, applied_status=applied_map.get(d.id))
        if eligible_only and not serialized["eligible"]:
            continue
        results.append(serialized)
    return jsonify(results)


@student_bp.route("/drives/<int:drive_id>/apply", methods=["POST"])
@roles_required(Role.STUDENT)
def apply_to_drive(drive_id):
    profile = _current_profile()
    drive = db.session.get(PlacementDrive, drive_id)
    if not drive or drive.status != DriveStatus.APPROVED:
        return _error("Drive not found or not open for applications", 404)

    now = datetime.now(timezone.utc)
    deadline = drive.application_deadline
    if deadline and deadline.tzinfo is None:
        deadline = deadline.replace(tzinfo=timezone.utc)
    if deadline and deadline < now:
        return _error("The application deadline for this drive has passed", 400)

    if not _is_eligible(profile, drive):
        return _error("You are not eligible for this drive", 403)

    existing = Application.query.filter_by(student_id=profile.id, drive_id=drive.id).first()
    if existing:
        return _error("You have already applied to this drive", 409)

    application = Application(student_id=profile.id, drive_id=drive.id, status=ApplicationStatus.APPLIED)
    db.session.add(application)
    db.session.commit()
    bump_cache_version()
    return jsonify(_serialize_application(application)), 201


@student_bp.route("/applications", methods=["GET"])
@roles_required(Role.STUDENT)
def list_applications():
    profile = _current_profile()
    applications = (
        Application.query.filter_by(student_id=profile.id)
        .order_by(Application.application_date.desc())
        .all()
    )
    return jsonify([_serialize_application(a) for a in applications])


@student_bp.route("/applications/export", methods=["POST"])
@roles_required(Role.STUDENT)
def export_applications():
    """Enqueue an async CSV export of this student's applications."""
    profile = _current_profile()
    cache.set(export_cache_key(profile.id), {"status": "pending"}, timeout=3600)
    celery.send_task("tasks.export_student_applications_csv", args=[profile.id])
    return jsonify({"status": "pending"}), 202


@student_bp.route("/applications/export/status", methods=["GET"])
@roles_required(Role.STUDENT)
def export_status():
    profile = _current_profile()
    status = cache.get(export_cache_key(profile.id))
    return jsonify(status or {"status": "none"})


@student_bp.route("/applications/export/download", methods=["GET"])
@roles_required(Role.STUDENT)
def export_download():
    profile = _current_profile()
    status = cache.get(export_cache_key(profile.id))
    if not status or status.get("status") != "ready":
        return _error("Export not ready", 404)
    return send_from_directory(current_app.config["REPORTS_FOLDER"], status["filename"], as_attachment=True)


@student_bp.route("/history", methods=["GET"])
@roles_required(Role.STUDENT)
def placement_history():
    profile = _current_profile()
    applications = (
        Application.query.filter_by(student_id=profile.id)
        .filter(Application.status.in_([ApplicationStatus.SELECTED, ApplicationStatus.REJECTED]))
        .order_by(Application.application_date.desc())
        .all()
    )
    return jsonify([_serialize_application(a) for a in applications])
