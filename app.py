import os

from flask import Flask
from flask_login import LoginManager
from database.db_connection import configure_db, close_db
from config import Config, DevelopmentConfig, ProductionConfig, TestingConfig

# Import blueprints
from routes.dashboard import dashboard_bp
from routes.leads import leads_bp
from routes.interactions import interactions_bp
from routes.institutions import institutions_bp
from routes.auth import auth_bp


def _resolve_config(config_object=None, config_name=None):
    """Return the requested config class, defaulting safely to production."""
    if config_object:
        return config_object

    if config_name:
        return {
            "development": DevelopmentConfig,
            "testing": TestingConfig,
            "production": ProductionConfig,
        }.get(str(config_name).lower(), ProductionConfig)

    env_name = (os.getenv("FLASK_ENV") or os.getenv("APP_ENV") or "production").lower()
    return {
        "development": DevelopmentConfig,
        "testing": TestingConfig,
        "production": ProductionConfig,
    }.get(env_name, ProductionConfig)


def create_app(config_object=None, config_name=None):
    """Create the Flask app and apply a concrete config class.

    If no config object/class is supplied, choose one from the environment,
    defaulting to the safe production config.
    """
    app = Flask(__name__)
    selected_config = _resolve_config(config_object=config_object, config_name=config_name)

    # Pull the config object shape into the app safely.
    app.config.from_object(selected_config)

    # Keep runtime URI selection outside the import-time class attribute freeze.
    if selected_config is TestingConfig:
        app.config["TESTING"] = True
        app.config["DEBUG"] = False
        app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv(
            "TEST_DATABASE_URL",
            os.getenv("DATABASE_URL", "sqlite:///:memory:"),
        )
    elif selected_config is DevelopmentConfig:
        app.config["DEBUG"] = True
        app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv(
            "DATABASE_URL",
            Config.SQLALCHEMY_DATABASE_URI,
        )
    else:
        app.config["DEBUG"] = False
        app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv(
            "DATABASE_URL",
            Config.SQLALCHEMY_DATABASE_URI,
        )

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


app = create_app(config_name=os.getenv("FLASK_ENV", "production"))


if __name__ == "__main__":
    app.run(debug=app.config.get("DEBUG", False), host="0.0.0.0")