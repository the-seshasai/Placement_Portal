"""Blueprint registry.

Each role gets its own blueprint module (auth_routes.py, admin_routes.py,
company_routes.py, student_routes.py). They're added here as they're built
so app.py never needs to change again.
"""


def register_blueprints(app):
    from routes.auth_routes import auth_bp
    from routes.admin_routes import admin_bp
    from routes.company_routes import company_bp
    from routes.student_routes import student_bp

    app.register_blueprint(auth_bp, url_prefix="/api/auth")
    app.register_blueprint(admin_bp, url_prefix="/api/admin")
    app.register_blueprint(company_bp, url_prefix="/api/company")
    app.register_blueprint(student_bp, url_prefix="/api/student")
