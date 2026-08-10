from flask import Blueprint, request, jsonify
from sqlalchemy import func

from extensions import db, cache
from decorators import roles_required
from caching import DEFAULT_TIMEOUT, scoped_cache_key, bump_cache_version
from models.user import User, Role
from models.company import Company, ApprovalStatus
from models.student_profile import StudentProfile
from models.drive import PlacementDrive, DriveStatus
from models.application import Application, ApplicationStatus

admin_bp = Blueprint("admin", __name__)


def _error(message, status=400):
    return jsonify({"error": message}), status


def _serialize_company(company):
    return {
        "id": company.id,
        "user_id": company.user_id,
        "company_name": company.company_name,
        "hr_contact_name": company.hr_contact_name,
        "hr_contact_phone": company.hr_contact_phone,
        "website": company.website,
        "description": company.description,
        "approval_status": company.approval_status,
        "email": company.user.email,
        "blacklisted": company.user.blacklisted,
        "created_at": company.created_at.isoformat() if company.created_at else None,
    }


def _serialize_student(profile):
    return {
        "id": profile.id,
        "user_id": profile.user_id,
        "name": profile.user.name,
        "email": profile.user.email,
        "branch": profile.branch,
        "cgpa": profile.cgpa,
        "grad_year": profile.grad_year,
        "phone": profile.phone,
        "resume_path": profile.resume_path,
        "blacklisted": profile.user.blacklisted,
        "created_at": profile.created_at.isoformat() if profile.created_at else None,
    }


def _serialize_drive(drive):
    return {
        "id": drive.id,
        "company_id": drive.company_id,
        "company_name": drive.company.company_name,
        "job_title": drive.job_title,
        "job_description": drive.job_description,
        "package_ctc": drive.package_ctc,
        "eligible_branches": drive.eligible_branches_list(),
        "min_cgpa": drive.min_cgpa,
        "eligible_grad_year": drive.eligible_grad_year,
        "application_deadline": drive.application_deadline.isoformat() if drive.application_deadline else None,
        "status": drive.status,
        "applicant_count": len(drive.applications),
        "created_at": drive.created_at.isoformat() if drive.created_at else None,
    }


def _serialize_application(app_):
    return {
        "id": app_.id,
        "student_id": app_.student_id,
        "student_name": app_.student.user.name,
        "student_email": app_.student.user.email,
        "drive_id": app_.drive_id,
        "job_title": app_.drive.job_title,
        "company_name": app_.drive.company.company_name,
        "status": app_.status,
        "application_date": app_.application_date.isoformat() if app_.application_date else None,
        "interview_date": app_.interview_date.isoformat() if app_.interview_date else None,
    }


@admin_bp.route("/dashboard", methods=["GET"])
@roles_required(Role.ADMIN)
@cache.cached(timeout=DEFAULT_TIMEOUT, key_prefix=scoped_cache_key)
def dashboard():
    total_students = StudentProfile.query.count()
    total_companies = Company.query.count()

    def counts_by(model, column, values):
        rows = db.session.query(column, func.count(model.id)).group_by(column).all()
        counts = {v: 0 for v in values}
        for value, count in rows:
            counts[value] = count
        counts["total"] = sum(counts[v] for v in values)
        return counts

    company_counts = counts_by(Company, Company.approval_status, ApprovalStatus.ALL)
    drive_counts = counts_by(PlacementDrive, PlacementDrive.status, DriveStatus.ALL)
    application_counts = counts_by(Application, Application.status, ApplicationStatus.ALL)

    return jsonify(
        {
            "total_students": total_students,
            "total_companies": total_companies,
            "companies": company_counts,
            "drives": drive_counts,
            "applications": application_counts,
        }
    )


@admin_bp.route("/companies", methods=["GET"])
@roles_required(Role.ADMIN)
def list_companies():
    query = Company.query.join(User)
    status = request.args.get("status")
    if status:
        query = query.filter(Company.approval_status == status)
    q = request.args.get("q")
    if q:
        like = f"%{q}%"
        query = query.filter(db.or_(Company.company_name.ilike(like), User.email.ilike(like)))
    companies = query.order_by(Company.created_at.desc()).all()
    return jsonify([_serialize_company(c) for c in companies])


@admin_bp.route("/companies/<int:company_id>/approve", methods=["POST"])
@roles_required(Role.ADMIN)
def approve_company(company_id):
    company = db.session.get(Company, company_id)
    if not company:
        return _error("Company not found", 404)
    company.approval_status = ApprovalStatus.APPROVED
    db.session.commit()
    bump_cache_version()
    return jsonify(_serialize_company(company))


@admin_bp.route("/companies/<int:company_id>/reject", methods=["POST"])
@roles_required(Role.ADMIN)
def reject_company(company_id):
    company = db.session.get(Company, company_id)
    if not company:
        return _error("Company not found", 404)
    company.approval_status = ApprovalStatus.REJECTED
    db.session.commit()
    bump_cache_version()
    return jsonify(_serialize_company(company))


@admin_bp.route("/drives", methods=["GET"])
@roles_required(Role.ADMIN)
def list_drives():
    query = PlacementDrive.query.join(Company)
    status = request.args.get("status")
    if status:
        query = query.filter(PlacementDrive.status == status)
    q = request.args.get("q")
    if q:
        like = f"%{q}%"
        query = query.filter(db.or_(PlacementDrive.job_title.ilike(like), Company.company_name.ilike(like)))
    drives = query.order_by(PlacementDrive.created_at.desc()).all()
    return jsonify([_serialize_drive(d) for d in drives])


@admin_bp.route("/drives/<int:drive_id>/approve", methods=["POST"])
@roles_required(Role.ADMIN)
def approve_drive(drive_id):
    drive = db.session.get(PlacementDrive, drive_id)
    if not drive:
        return _error("Drive not found", 404)
    drive.status = DriveStatus.APPROVED
    db.session.commit()
    bump_cache_version()
    return jsonify(_serialize_drive(drive))


@admin_bp.route("/drives/<int:drive_id>/reject", methods=["POST"])
@roles_required(Role.ADMIN)
def reject_drive(drive_id):
    drive = db.session.get(PlacementDrive, drive_id)
    if not drive:
        return _error("Drive not found", 404)
    drive.status = DriveStatus.REJECTED
    db.session.commit()
    bump_cache_version()
    return jsonify(_serialize_drive(drive))


@admin_bp.route("/students", methods=["GET"])
@roles_required(Role.ADMIN)
def list_students():
    query = StudentProfile.query.join(User)
    q = request.args.get("q")
    if q:
        like = f"%{q}%"
        query = query.filter(
            db.or_(User.name.ilike(like), User.email.ilike(like), StudentProfile.branch.ilike(like))
        )
    students = query.order_by(StudentProfile.created_at.desc()).all()
    return jsonify([_serialize_student(s) for s in students])


@admin_bp.route("/applications", methods=["GET"])
@roles_required(Role.ADMIN)
def list_applications():
    query = Application.query
    status = request.args.get("status")
    if status:
        query = query.filter(Application.status == status)
    drive_id = request.args.get("drive_id", type=int)
    if drive_id:
        query = query.filter(Application.drive_id == drive_id)
    applications = query.order_by(Application.application_date.desc()).all()
    return jsonify([_serialize_application(a) for a in applications])


@admin_bp.route("/users/<int:user_id>/blacklist", methods=["POST"])
@roles_required(Role.ADMIN)
def set_blacklist(user_id):
    user = db.session.get(User, user_id)
    if not user:
        return _error("User not found", 404)
    if user.role == Role.ADMIN:
        return _error("Cannot blacklist an admin account", 403)

    data = request.get_json(silent=True) or {}
    blacklisted = data.get("blacklisted")
    if not isinstance(blacklisted, bool):
        return _error("`blacklisted` (boolean) is required")

    user.blacklisted = blacklisted
    db.session.commit()
    bump_cache_version()
    return jsonify({"id": user.id, "email": user.email, "blacklisted": user.blacklisted})


@admin_bp.route("/stats", methods=["GET"])
@roles_required(Role.ADMIN)
@cache.cached(timeout=DEFAULT_TIMEOUT, key_prefix=scoped_cache_key)
def stats():
    total_applications = Application.query.count()
    selected = Application.query.filter_by(status=ApplicationStatus.SELECTED).count()
    placed_student_ids = {
        row[0]
        for row in db.session.query(Application.student_id)
        .filter(Application.status == ApplicationStatus.SELECTED)
        .distinct()
    }
    total_students = StudentProfile.query.count()

    branch_rows = (
        db.session.query(StudentProfile.branch, func.count(func.distinct(Application.student_id)))
        .join(Application, Application.student_id == StudentProfile.id)
        .filter(Application.status == ApplicationStatus.SELECTED)
        .group_by(StudentProfile.branch)
        .all()
    )

    company_rows = (
        db.session.query(Company.company_name, func.count(Application.id))
        .join(PlacementDrive, PlacementDrive.company_id == Company.id)
        .join(Application, Application.drive_id == PlacementDrive.id)
        .filter(Application.status == ApplicationStatus.SELECTED)
        .group_by(Company.company_name)
        .all()
    )

    return jsonify(
        {
            "total_students": total_students,
            "students_placed": len(placed_student_ids),
            "placement_rate": (len(placed_student_ids) / total_students) if total_students else 0,
            "total_applications": total_applications,
            "total_selected": selected,
            "selected_by_branch": {branch: count for branch, count in branch_rows},
            "selected_by_company": {name: count for name, count in company_rows},
        }
    )
