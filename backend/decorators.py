"""Role-based route protection, layered on top of Flask-Login."""

from functools import wraps

from flask import jsonify
from flask_login import current_user


def roles_required(*roles):
    """Restrict a view to authenticated users whose `role` is in `roles`.

    401 if not logged in, 403 if logged in but the wrong role.
    """

    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            if not current_user.is_authenticated:
                return jsonify({"error": "Authentication required"}), 401
            if current_user.role not in roles:
                return jsonify({"error": "Forbidden for this role"}), 403
            return fn(*args, **kwargs)

        return wrapper

    return decorator
