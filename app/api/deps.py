from __future__ import annotations

from datetime import datetime, timezone
from typing import Generator
import uuid

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.db import SessionLocal
from app.models import User, Subscription
from app.services.auth import decode_token

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    credentials_exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid authentication credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = decode_token(token)
        sub = payload.get("sub")
        if not sub:
            raise credentials_exc
        user_id = uuid.UUID(sub)
    except (JWTError, ValueError):
        raise credentials_exc

    user = db.scalar(select(User).where(User.id == user_id))
    if not user or not user.is_active:
        raise credentials_exc
    return user


def require_active_subscription(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> User:
    """Dependency-guard: user must have active subscription."""
    now = datetime.now(timezone.utc)

    sub = db.scalar(
        select(Subscription)
        .where(Subscription.user_id == user.id)
        .where(Subscription.status == "active")
        .where(Subscription.end_at > now)
        .order_by(Subscription.end_at.desc())
    )

    if not sub:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail="Active subscription required",
        )
    return user
