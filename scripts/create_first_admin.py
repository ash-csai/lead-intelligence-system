"""Create the first admin user for a fresh lead_system.db.

Usage:
    python scripts/create_first_admin.py --email admin@example.com --password secret
"""

import argparse
from app import create_app
from database.db_connection import get_db
from database.models import User


def create_first_admin(email="admin@example.com", password="secret", name="Admin User"):
    app = create_app()
    with app.app_context():
        db = get_db()
        user = db.session.query(User).filter(User.email == email).first()
        if user is None:
            user = User(name=name, email=email, role="admin", organization_id=1)
            db.session.add(user)
        user.name = name
        user.email = email
        user.role = "admin"
        user.organization_id = 1
        user.set_password(password)
        db.session.commit()
        print(f"Created/updated admin user {email} in organization 1.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--email", default="admin@example.com")
    parser.add_argument("--password", default="secret")
    parser.add_argument("--name", default="Admin User")
    args = parser.parse_args()

    create_first_admin(email=args.email, password=args.password, name=args.name)
