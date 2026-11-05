from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import verify_password, create_access_token
from app.models.user import User
from app.schemas.user import UserResponse
from app.schemas.auth import LoginRequest, TokenResponse
from app.core.dependencies import get_current_user

router = APIRouter(prefix="/auth", tags=["Authentication"])

@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register():
    # StockPilot is admin-provisioned: public registration must never create
    # unassigned users or let a caller choose their own role.
    raise HTTPException(status_code=403, detail="Public registration is disabled. Contact the StockPilot administrator.")

@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.email == str(payload.email).lower()))
    if user is None or not user.is_active or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password", headers={"WWW-Authenticate":"Bearer"})
    role = user.role.name if user.role else "user"
    return TokenResponse(access_token=create_access_token(user.id, role), user_id=user.id, role=role)


@router.get("/me", response_model=UserResponse)
def current_user(user: User = Depends(get_current_user)):
    """Return the authenticated account without exposing credential fields."""
    return {
        "id": user.id,
        "name": user.name,
        "email": user.email,
        "is_active": user.is_active,
        "created_at": user.created_at,
        "role_name": user.role.name if user.role else None,
    }
