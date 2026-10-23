import hashlib
import uuid
from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import get_db
from app.models.session import RevokedSession
from app.models.user import User, UserRole

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")
Database = Annotated[Session, Depends(get_db)]


def get_current_user(token: Annotated[str, Depends(oauth2_scheme)], db: Database) -> User:
    credentials_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Credenciais inválidas",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
        user_id = uuid.UUID(payload.get("sub", ""))
    except (jwt.PyJWTError, ValueError, TypeError, AttributeError) as exc:
        raise credentials_error from exc
    if db.get(RevokedSession, hashlib.sha256(token.encode()).hexdigest()):
        raise credentials_error
    user = db.get(User, user_id)
    if (
        not user
        or not user.is_active
        or payload.get("sv", 0) != user.session_version
    ):
        raise credentials_error
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def require_roles(*roles: UserRole):
    def authorize(user: CurrentUser) -> User:
        if user.role not in roles:
            raise HTTPException(status_code=403, detail="Você não possui permissão para esta ação")
        return user

    return authorize
