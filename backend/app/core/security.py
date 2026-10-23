from datetime import UTC, datetime, timedelta
from uuid import uuid4

import jwt
from pwdlib import PasswordHash

from app.core.config import settings

password_hash = PasswordHash.recommended()


def hash_password(password: str) -> str:
    return password_hash.hash(password)


def verify_password(password: str, hashed_password: str) -> bool:
    return password_hash.verify(password, hashed_password)


def create_access_token(subject: str, role: str, session_version: int = 0) -> str:
    expires_at = datetime.now(UTC) + timedelta(minutes=settings.jwt_expire_minutes)
    return jwt.encode(
        {
            "sub": subject,
            "role": role,
            "sv": session_version,
            "exp": expires_at,
            "jti": str(uuid4()),
        },
        settings.jwt_secret,
        algorithm=settings.jwt_algorithm,
    )
