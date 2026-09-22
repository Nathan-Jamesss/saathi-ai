"""One-time admin account seed script.

Run from the backend/ directory:
    python -m scripts.create_admin
Reads ADMIN_EMAIL / ADMIN_PASSWORD from the environment (.env locally,
Cloud Run env vars in production).
"""
import os
import sys

from dotenv import load_dotenv

load_dotenv()

from auth import firestore_repo  # noqa: E402
from auth.models import Role, User  # noqa: E402
from auth.security import hash_password  # noqa: E402


def main():
    email = os.environ.get("ADMIN_EMAIL")
    password = os.environ.get("ADMIN_PASSWORD")
    if not email or not password:
        print("ADMIN_EMAIL and ADMIN_PASSWORD must be set in the environment.")
        sys.exit(1)

    existing = firestore_repo.get_user_by_email(email)
    if existing:
        print(f"Admin {email} already exists (id={existing.id}).")
        return

    admin = User(
        email=email,
        password_hash=hash_password(password),
        role=Role.admin,
        name="Admin",
    )
    admin = firestore_repo.create_user(admin)
    print(f"Created admin {email} (id={admin.id}).")


if __name__ == "__main__":
    main()
