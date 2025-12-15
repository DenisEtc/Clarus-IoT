from __future__ import annotations

import uuid
from pydantic import BaseModel


class PredictionSummaryOut(BaseModel):
    total_rows: int
    attack_rows: int
    attack_ratio: float
    top_class: str | None = None
    top_class_share: float | None = None


class PredictionJobOut(BaseModel):
    job_id: uuid.UUID
    status: str
    summary: PredictionSummaryOut


class PredictionJobListItemOut(PredictionJobOut):
    """Extended shape for history screens."""

    created_at: str | None = None
    original_filename: str | None = None
