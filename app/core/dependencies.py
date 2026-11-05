from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import decode_access_token
from app.models.user import User

bearer = HTTPBearer(auto_error=False)

def get_current_user(credentials: HTTPAuthorizationCredentials | None = Depends(bearer), db: Session = Depends(get_db)) -> User:
    if credentials is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Bearer token required", headers={"WWW-Authenticate":"Bearer"})
    try:
        payload = decode_access_token(credentials.credentials)
        user_id = int(payload.get("sub", ""))
    except Exception as exc:
        raise HTTPException(status_code=401, detail="Invalid or expired token", headers={"WWW-Authenticate":"Bearer"}) from exc
    user = db.get(User, user_id)
    if user is None or not user.is_active:
        raise HTTPException(status_code=401, detail="User is inactive or no longer exists")
    return user

def require_roles(*roles: str):
    """Require one of the database-assigned roles; admins can access all business routes."""
    allowed = {role.strip().lower() for role in roles}

    def dependency(user: User = Depends(get_current_user)) -> User:
        role_name = (user.role.name if user.role else "").strip().lower()
        if role_name == "admin":
            return user
        if role_name not in allowed:
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        return user

    return dependency
