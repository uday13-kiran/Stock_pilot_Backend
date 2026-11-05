"""Create the first administrator in a trusted environment.

Run from the project root after database migrations:
    python -m scripts.create_admin
"""
from getpass import getpass

from sqlalchemy import select

from app.core.database import SessionLocal
from app.core.security import hash_password
from app.models.roles import Role
from app.core.role_policy import ROLE_DESCRIPTIONS
from app.models.user import User


def main() -> None:
    name = input("Administrator name: ").strip()
    email = input("Administrator email: ").strip().lower()
    password = getpass("Password (minimum 8 characters): ")
    confirm = getpass("Confirm password: ")
    if not name or not email:
        raise SystemExit("Name and email are required.")
    if len(password) < 8:
        raise SystemExit("Password must be at least 8 characters.")
    if password != confirm:
        raise SystemExit("Passwords do not match.")

    db = SessionLocal()
    try:
        if db.scalar(select(User.id).where(User.email == email)):
            raise SystemExit("A user with that email already exists.")
        roles = {}
        for role_name, description in ROLE_DESCRIPTIONS.items():
            role = db.scalar(select(Role).where(Role.name == role_name))
            if role is None:
                role = Role(name=role_name, description=description)
                db.add(role)
                db.flush()
            roles[role_name] = role
        user = User(name=name, email=email, password_hash=hash_password(password), role_id=roles["admin"].id, is_active=True)
        db.add(user)
        db.commit()
        print(f"Administrator created: {email}")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
