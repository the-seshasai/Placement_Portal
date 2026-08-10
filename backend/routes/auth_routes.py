from flask import Blueprint, request, jsonify
from flask_login import login_user, logout_user, login_required, current_user

from extensions import db
from models.user import User, Role
from models.company import Company, ApprovalStatus
from models.student_profile import StudentProfile
from validation import is_valid_email, is_valid_password, is_valid_cgpa, is_valid_grad_year

auth_bp = Blueprint("auth", __name__)


def _error(message, status=400, field=None):
    body = {"error": message}
    if field:
        body["field"] = field
    return jsonify(body), status


def _serialize_user(user):
    payload = {"id": user.id, "name": user.name, "email": user.email, "role": user.role}
    if user.role == Role.COMPANY and user.company:
        payload["company_name"] = user.company.company_name
        payload["approval_status"] = user.company.approval_status
    if user.role == Role.STUDENT and user.student_profile:
        payload["branch"] = user.student_profile.branch
        payload["cgpa"] = user.student_profile.cgpa
        payload["grad_year"] = user.student_profile.grad_year
    return payload


@auth_bp.route("/register/student", methods=["POST"])
def register_student():
    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""
    branch = (data.get("branch") or "").strip()
    cgpa = data.get("cgpa")
    grad_year = data.get("grad_year")
    phone = (data.get("phone") or "").strip() or None

    if not name:
        return _error("Name is required", field="name")
    if not is_valid_email(email):
        return _error("A valid email is required", field="email")
    if not is_valid_password(password):
        return _error("Password must be at least 8 characters", field="password")
    if not branch:
        return _error("Branch is required", field="branch")
    if not is_valid_cgpa(cgpa):
        return _error("CGPA must be a number between 0 and 10", field="cgpa")
    if not is_valid_grad_year(grad_year):
        return _error("Graduation year is invalid", field="grad_year")

    if User.query.filter_by(email=email).first():
        return _error("An account with this email already exists", field="email")

    user = User(name=name, email=email, role=Role.STUDENT)
    user.set_password(password)
    db.session.add(user)
    db.session.flush()  # get user.id before creating the profile

    profile = StudentProfile(
        user_id=user.id,
        branch=branch,
        cgpa=float(cgpa),
        grad_year=int(grad_year),
        phone=phone,
    )
    db.session.add(profile)
    db.session.commit()

    login_user(user)
    return jsonify(_serialize_user(user)), 201


@auth_bp.route("/register/company", methods=["POST"])
def register_company():
    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""
    company_name = (data.get("company_name") or "").strip()
    hr_contact_name = (data.get("hr_contact_name") or "").strip()
    hr_contact_phone = (data.get("hr_contact_phone") or "").strip() or None
    website = (data.get("website") or "").strip() or None
    description = (data.get("description") or "").strip() or None

    if not name:
        return _error("Name is required", field="name")
    if not is_valid_email(email):
        return _error("A valid email is required", field="email")
    if not is_valid_password(password):
        return _error("Password must be at least 8 characters", field="password")
    if not company_name:
        return _error("Company name is required", field="company_name")
    if not hr_contact_name:
        return _error("HR contact name is required", field="hr_contact_name")

    if User.query.filter_by(email=email).first():
        return _error("An account with this email already exists", field="email")

    user = User(name=name, email=email, role=Role.COMPANY)
    user.set_password(password)
    db.session.add(user)
    db.session.flush()

    company = Company(
        user_id=user.id,
        company_name=company_name,
        hr_contact_name=hr_contact_name,
        hr_contact_phone=hr_contact_phone,
        website=website,
        description=description,
        approval_status=ApprovalStatus.PENDING,
    )
    db.session.add(company)
    db.session.commit()

    # Registration is not auto-approved: the company can log in immediately
    # but drive creation stays gated until the admin approves it (step 4/5).
    login_user(user)
    return jsonify(_serialize_user(user)), 201


@auth_bp.route("/login", methods=["POST"])
def login():
    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""

    if not email or not password:
        return _error("Email and password are required")

    user = User.query.filter_by(email=email).first()
    if not user or not user.check_password(password):
        return _error("Invalid email or password", status=401)

    if not user.is_active:
        return _error("This account has been deactivated or blacklisted. Contact the admin.", status=403)

    login_user(user)
    return jsonify(_serialize_user(user)), 200


@auth_bp.route("/logout", methods=["POST"])
@login_required
def logout():
    logout_user()
    return jsonify({"message": "Logged out"}), 200


@auth_bp.route("/me", methods=["GET"])
def me():
    if not current_user.is_authenticated:
        return jsonify({"authenticated": False}), 200
    return jsonify({"authenticated": True, "user": _serialize_user(current_user)}), 200
