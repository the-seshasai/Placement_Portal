import os

from flask import Flask, render_template

from config import config_by_name
from extensions import db, login_manager, cache, mail


def create_app(config_name=None):
    config_name = config_name or os.environ.get("FLASK_ENV", "development")
    app = Flask(
        __name__,
        static_folder=os.path.join(os.path.dirname(__file__), "..", "frontend", "src"),
        static_url_path="/src",
        template_folder="templates",
    )
    app.config.from_object(config_by_name[config_name])

    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
    os.makedirs(app.config["REPORTS_FOLDER"], exist_ok=True)
    os.makedirs(os.path.join(os.path.dirname(__file__), "instance"), exist_ok=True)

    db.init_app(app)
    login_manager.init_app(app)
    cache.init_app(app)
    mail.init_app(app)

    import models  # noqa: F401  (registers all tables with SQLAlchemy metadata)
    from models.user import User

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))

    # Blueprints are registered here as each role's routes are built
    # (auth_routes, admin_routes, company_routes, student_routes).
    from routes import register_blueprints

    register_blueprints(app)

    @app.route("/")
    def index():
        return render_template("index.html")

    register_cli(app)

    return app


def register_cli(app):
    import click
    from models.user import User, Role

    @app.cli.command("create-admin")
    @click.option("--email", default=None, help="Defaults to config ADMIN_EMAIL")
    @click.option("--password", default=None, help="Defaults to config ADMIN_PASSWORD")
    @click.option("--name", default=None, help="Defaults to config ADMIN_NAME")
    def create_admin(email, password, name):
        """Create the single admin user (idempotent)."""
        email = email or app.config["ADMIN_EMAIL"]
        password = password or app.config["ADMIN_PASSWORD"]
        name = name or app.config["ADMIN_NAME"]

        if User.query.filter_by(email=email).first():
            click.echo(f"Admin user already exists ({email}), skipping.")
            return

        admin = User(name=name, email=email, role=Role.ADMIN)
        admin.set_password(password)
        db.session.add(admin)
        db.session.commit()
        click.echo(f"Admin user created: {email}")


if __name__ == "__main__":
    app = create_app()
    app.run(host=app.config["HOST"], port=app.config["PORT"], debug=app.config["DEBUG"])
