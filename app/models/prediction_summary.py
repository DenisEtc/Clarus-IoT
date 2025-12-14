import uuid
from sqlalchemy import Integer, Float, String, DateTime, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base


class PredictionSummary(Base):
    __tablename__ = "prediction_summaries"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("inference_jobs.id"),
        nullable=False,
        unique=True,
        index=True,
    )

    rows_scored: Mapped[int] = mapped_column(Integer, nullable=False)

    # сколько строк модель посчитала атакой (важно, не вычислять задним числом через share)
    attack_rows: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # доля атакованных строк (attack_rows/rows_scored)
    attack_share: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)

    # самый частый класс среди атак (или benign если атак нет)
    top_class: Mapped[str | None] = mapped_column(String(64), nullable=True)
    top_class_share: Mapped[float | None] = mapped_column(Float, nullable=True)

    # путь к scored CSV
    scored_path: Mapped[str | None] = mapped_column(String(512), nullable=True)

    created_at: Mapped["DateTime"] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    job = relationship("InferenceJob", back_populates="summary")
