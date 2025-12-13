from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Subscription


def require_active_subscription(db: Session, user_id: UUID) -> Subscription:
    """Guard for paid endpoints.

    Raises HTTPException(402) if user has no active subscription.
    Returns the latest active subscription otherwise.
    """
    now = datetime.now(timezone.utc)

    sub = db.scalar(
        select(Subscription)
        .where(Subscription.user_id == user_id)
        .where(Subscription.status == "active")
        .where(Subscription.end_at > now)
        .order_by(Subscription.end_at.desc())
    )

    if not sub:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail="Active subscription required",
        )
    return sub
