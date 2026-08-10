"""Shared Flask extension instances.

Kept in one module (rather than instantiated in app.py) so models,
blueprints, and celery tasks can all import `db`, `cache`, etc. without
circular imports.
"""

from flask import jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_caching import Cache
from flask_mail import Mail

db = SQLAlchemy()
login_manager = LoginManager()
cache = Cache()
mail = Mail()


@login_manager.unauthorized_handler
def _unauthorized():
    # This is a JSON API (Vue frontend), so unauthenticated access to a
    # @login_required view returns 401 instead of redirecting to a login page.
    return jsonify({"error": "Authentication required"}), 401
