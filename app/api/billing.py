from datetime import datetime, timedelta, timezone
import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.api.deps import get_db, get_current_user
from app.schemas.billing import SubscriptionStatusOut, RenewIn, RenewOut
from app.models import User, Plan, Payment, Subscription

router = APIRouter()


@router.get("/subscription", response_model=SubscriptionStatusOut)
def get_subscription_status(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    now = datetime.now(timezone.utc)
    sub = db.scalar(
        select(Subscription)
        .where(Subscription.user_id == user.id)
        .where(Subscription.status == "active")
        .order_by(Subscription.end_at.desc())
    )

    if not sub:
        return SubscriptionStatusOut(
            has_active=False,
            ends_at=None,
            remaining_days=0,
        )

    remaining = max(0, int((sub.end_at - now).total_seconds() // 86400))
    has_active = sub.end_at > now and sub.status == "active"
    return SubscriptionStatusOut(
        has_active=has_active,
        ends_at=sub.end_at,
        remaining_days=remaining,
    )


@router.post("/renew", response_model=RenewOut)
def renew_subscription(payload: RenewIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """
    Mock-продление:
    - создаём Payment со статусом succeeded
    - продлеваем/создаём Subscription на duration_days плана
    """
    plan = db.scalar(select(Plan).where(Plan.code == payload.plan_code).where(Plan.is_active == True))  # noqa: E712
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found or inactive")

    now = datetime.now(timezone.utc)

    payment = Payment(
        user_id=user.id,
        plan_id=plan.id,
        amount_cents=plan.price_cents,
        currency=plan.currency,
        provider="mock",
        status="succeeded",
        external_id=str(uuid.uuid4()),
        paid_at=now,
    )
    db.add(payment)
    db.commit()
    db.refresh(payment)

    # найдём текущую активную подписку
    current = db.scalar(
        select(Subscription)
        .where(Subscription.user_id == user.id)
        .where(Subscription.status == "active")
        .order_by(Subscription.end_at.desc())
    )

    start_at = now
    if current and current.end_at > now:
        start_at = current.end_at

    end_at = start_at + timedelta(days=plan.duration_days)

    sub = Subscription(
        user_id=user.id,
        plan_id=plan.id,
        payment_id=payment.id,
        status="active",
        start_at=start_at,
        end_at=end_at,
    )
    db.add(sub)
    db.commit()
    db.refresh(sub)

    return RenewOut(
        payment_id=payment.id,
        subscription_id=sub.id,
        ends_at=sub.end_at,
    )
