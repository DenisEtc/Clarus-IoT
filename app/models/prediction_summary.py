import uuid
from sqlalchemy import Integer, Float, String, DateTime, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base

class PredictionSummary(Base):
    __tablename__ = "prediction_summaries"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    job_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("inference_jobs.id"), nullable=False, unique=True, index=True)

    rows_scored: Mapped[int] = mapped_column(Integer, nullable=False)
    attack_share: Mapped[float] = mapped_column(Float, nullable=False)

    top_class: Mapped[str | None] = mapped_column(String(64), nullable=True)
    top_class_share: Mapped[float | None] = mapped_column(Float, nullable=True)

    created_at: Mapped["DateTime"] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    job = relationship("InferenceJob", back_populates="summary")
