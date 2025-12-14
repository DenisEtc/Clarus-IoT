import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from app.core.db import SessionLocal
from app.models import User, Plan, Payment, Subscription


def main() -> None:
    db = SessionLocal()
    try:
        # 1) Проверяем наличие "базовых моделей" (Plan)
        plan = db.scalar(select(Plan).where(Plan.code == "MONTHLY_1M"))
        if not plan:
            raise RuntimeError("Plan MONTHLY_1M not found. Run `alembic upgrade head` first.")
        print(f"[OK] Plan found: {plan.code} ({plan.duration_days}d, {plan.price_cents} {plan.currency})")

        # 2) "Создание пользователей": создадим нового пользователя, если его нет
        email = "test_user@clarus.local"
        user = db.scalar(select(User).where(User.email == email))
        if not user:
            user = User(
                email=email,
                password_hash="demo_hash_placeholder",
                role="user",
                is_active=True,
            )
            db.add(user)
            db.commit()
            db.refresh(user)
            print(f"[OK] User created: {user.email} (id={user.id})")
        else:
            print(f"[OK] User exists: {user.email} (id={user.id})")

        # 3) "Пополнение / транзакция": создаём mock payment
        payment = Payment(
            user_id=user.id,
            plan_id=plan.id,
            amount_cents=plan.price_cents,
            currency=plan.currency,
            provider="mock",
            status="succeeded",
            external_id=str(uuid.uuid4()),
            paid_at=datetime.now(timezone.utc),
        )
        db.add(payment)
        db.commit()
        db.refresh(payment)
        print(f"[OK] Payment created: {payment.id} status={payment.status} amount={payment.amount_cents} {payment.currency}")

        # 4) "Списание/использование" в твоём кейсе = выдача доступа через подписку
        now = datetime.now(timezone.utc)
        sub = Subscription(
            user_id=user.id,
            plan_id=plan.id,
            payment_id=payment.id,
            status="active",
            start_at=now,
            end_at=now + timedelta(days=plan.duration_days),
        )
        db.add(sub)
        db.commit()
        db.refresh(sub)
        print(f"[OK] Subscription created: {sub.status} {sub.start_at} -> {sub.end_at}")

        # 5) "История транзакций": список платежей пользователя
        payments = db.scalars(
            select(Payment).where(Payment.user_id == user.id).order_by(Payment.created_at.desc())
        ).all()

        print("\n=== Payment history (transactions) ===")
        for p in payments:
            print(f"- {p.created_at} | {p.status} | {p.amount_cents} {p.currency} | {p.external_id}")

        print("\n[ALL OK] DB scenario completed successfully.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
