from flask import Flask
from database.db_connection import close_db

# Import blueprints
from routes.dashboard import dashboard_bp
from routes.leads import leads_bp
from routes.interactions import interactions_bp
from routes.institutions import institutions_bp


def create_app():
    app = Flask(__name__)
    app.teardown_appcontext(close_db)

    # Register blueprints (keep original URLs)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(leads_bp)
    app.register_blueprint(interactions_bp)
    app.register_blueprint(institutions_bp)

    return app


if __name__ == "__main__":
    create_app().run(debug=True)