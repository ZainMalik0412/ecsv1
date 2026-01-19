"""FastAPI dependencies for authentication and authorization."""

from typing import Annotated, List

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.auth import decode_access_token
from app.database import get_db
from app.models import Role, User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

DBSession = Annotated[Session, Depends(get_db)]


def get_current_user(db: DBSession, token: Annotated[str, Depends(oauth2_scheme)]) -> User:
    """Extract and validate the current user from the JWT token."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    payload = decode_access_token(token)
    if payload is None:
        raise credentials_exception
    username: str = payload.get("sub")
    if username is None:
        raise credentials_exception
    user = db.query(User).filter(User.username == username).first()
    if user is None or not user.is_active:
        raise credentials_exception
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def require_roles(allowed_roles: List[Role]):
    """Dependency factory that restricts access to specific roles."""

    def role_checker(current_user: CurrentUser) -> User:
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions",
            )
        return current_user

    return role_checker


RequireAdmin = Annotated[User, Depends(require_roles([Role.ADMIN]))]
RequireLecturer = Annotated[User, Depends(require_roles([Role.LECTURER, Role.ADMIN]))]
RequireStudent = Annotated[User, Depends(require_roles([Role.STUDENT, Role.LECTURER, Role.ADMIN]))]
