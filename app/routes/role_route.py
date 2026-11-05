"""Read-only list of the six roles seeded by the trusted admin bootstrap script."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.roles import Role

router = APIRouter(prefix="/roles", tags=["Roles"])


@router.get("/")
def list_roles(db: Session = Depends(get_db)):
    return db.scalars(select(Role).order_by(Role.id)).all()


@router.get("/{role_id}")
def get_role(role_id: int, db: Session = Depends(get_db)):
    role = db.get(Role, role_id)
    if role is None:
        raise HTTPException(status_code=404, detail="Role not found")
    return role
