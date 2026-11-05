from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user, require_roles
from app.core.role_policy import ROLE_DESCRIPTIONS
from app.core.security import hash_password
from app.models.roles import Role
from app.models.user import User
from app.schemas.user import UserCreate, UserUpdate

router = APIRouter(prefix="/users", tags=["Users"])


def _user_payload(user: User) -> dict:
    return {
        "id": user.id,
        "name": user.name,
        "email": user.email,
        "is_active": user.is_active,
        "created_at": user.created_at,
        "role_name": user.role.name if user.role else None,
    }


@router.get("/me")
def me(user: User = Depends(get_current_user)):
    return _user_payload(user)


@router.post("/", status_code=status.HTTP_201_CREATED)
def create_user(
    payload: UserCreate,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_roles("admin")),
):
    email = str(payload.email).lower()
    if db.scalar(select(User.id).where(User.email == email)):
        raise HTTPException(status_code=409, detail="Email is already registered")

    role_name = payload.role_name.strip().lower()
    if role_name not in ROLE_DESCRIPTIONS:
        raise HTTPException(status_code=422, detail="Choose one of the configured StockPilot roles")
    role = db.scalar(select(Role).where(Role.name == role_name))
    if role is None:
        role = Role(name=role_name, description=ROLE_DESCRIPTIONS[role_name])
        db.add(role)
        db.flush()

    user = User(
        name=payload.name.strip(),
        email=email,
        password_hash=hash_password(payload.password),
        role_id=role.id,
        is_active=payload.is_active,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return _user_payload(user)


@router.get("/")
def list_users(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_roles("admin")),
):
    if skip < 0 or not 1 <= limit <= 500:
        raise HTTPException(status_code=422, detail="Invalid pagination")
    return [_user_payload(user) for user in db.scalars(select(User).offset(skip).limit(limit)).all()]


@router.get("/{user_id}")
def get_user(
    user_id: int,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_roles("admin")),
):
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return _user_payload(user)


@router.patch("/{user_id}")
def update_user(
    user_id: int,
    payload: UserUpdate,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_roles("admin")),
):
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    data = payload.model_dump(exclude_unset=True)
    if "email" in data and data["email"] is not None:
        email = str(data["email"]).lower()
        duplicate = db.scalar(select(User.id).where(User.email == email, User.id != user_id))
        if duplicate:
            raise HTTPException(status_code=409, detail="Email is already registered")
        user.email = email
    if "name" in data and data["name"] is not None:
        user.name = data["name"].strip()
    if "is_active" in data and data["is_active"] is not None:
        user.is_active = data["is_active"]
    if "role_name" in data and data["role_name"] is not None:
        role_name = data["role_name"].strip().lower()
        if role_name not in ROLE_DESCRIPTIONS:
            raise HTTPException(status_code=422, detail="Invalid StockPilot role")
        role = db.scalar(select(Role).where(Role.name == role_name))
        if role is None:
            role = Role(name=role_name, description=ROLE_DESCRIPTIONS[role_name])
            db.add(role)
            db.flush()
        user.role_id = role.id

    db.commit()
    db.refresh(user)
    return _user_payload(user)
