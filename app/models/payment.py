import uuid
from sqlalchemy import String, Integer, DateTime, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base

class Payment(Base):
    __tablename__ = "payments"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    plan_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("plans.id"), nullable=False, index=True)

    amount_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    currency: Mapped[str] = mapped_column(String(8), nullable=False)

    provider: Mapped[str] = mapped_column(String(32), nullable=False, default="mock")
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="pending")
    external_id: Mapped[str | None] = mapped_column(String(64), nullable=True)

    created_at: Mapped["DateTime"] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    paid_at: Mapped["DateTime | None"] = mapped_column(DateTime(timezone=True), nullable=True)

    user = relationship("User", back_populates="payments")
    plan = relationship("Plan", back_populates="payments")
    subscription = relationship("Subscription", back_populates="payment", uselist=False)
