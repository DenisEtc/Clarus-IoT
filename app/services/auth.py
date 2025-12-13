from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.db import get_db
from app.models.user import User

# Важно: bcrypt имеет лимит 72 байта, но мы ограничиваем пароли на уровне схем.
# Здесь используем bcrypt как стандарт.
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, password_hash: str) -> bool:
    return pwd_context.verify(plain_password, password_hash)


def create_access_token(*, subject: str, expires_minutes: Optional[int] = None) -> str:
    now = datetime.now(timezone.utc)
    exp_minutes = expires_minutes or settings.access_token_expire_minutes
    expire = now + timedelta(minutes=exp_minutes)

    payload = {
        "sub": subject,  # user_id как строка UUID
        "iat": int(now.timestamp()),
        "exp": int(expire.timestamp()),
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def decode_token(token: str) -> dict:
    return jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    credentials_exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Not authenticated",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = decode_token(token)
        sub = payload.get("sub")
        if not sub:
            raise credentials_exc
        user_id = UUID(sub)
    except (JWTError, ValueError):
        raise credentials_exc

    user = db.scalar(select(User).where(User.id == user_id))
    if not user or not user.is_active:
        raise credentials_exc
    return user


# Backward-compatible alias (older imports)
def decode_access_token(token: str):
    return decode_token(token)
