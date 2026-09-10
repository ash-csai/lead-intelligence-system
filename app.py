import os

from flask import Flask
from flask_login import LoginManager
from database.db_connection import configure_db, close_db

# Import blueprints
from routes.dashboard import dashboard_bp
from routes.leads import leads_bp
from routes.interactions import interactions_bp
from routes.institutions import institutions_bp
from routes.auth import auth_bp


def create_app():
    app = Flask(__name__)
    app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-secret-key")

    # Configure SQLAlchemy
    configure_db(app)

    # Configure Flask-Login
    login_manager = LoginManager()
    login_manager.login_view = "auth.login"
    login_manager.login_message = "Please log in to access this page."
    login_manager.id_attribute = "get_id"
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(user_id):
        from database.models import User
        return User.query.get(int(user_id))

    app.teardown_appcontext(close_db)

    # Register blueprints (keep original URLs)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(leads_bp)
    app.register_blueprint(interactions_bp)
    app.register_blueprint(institutions_bp)
    app.register_blueprint(auth_bp)

    return app


if __name__ == "__main__":
    create_app().run(debug=True)