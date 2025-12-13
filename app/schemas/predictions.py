from pydantic import BaseModel
import uuid


class PredictionSummaryOut(BaseModel):
    total_rows: int
    attack_rows: int
    attack_ratio: float


class PredictionJobOut(BaseModel):
    job_id: uuid.UUID
    status: str
    summary: PredictionSummaryOut


class PredictionHistoryOut(BaseModel):
    items: list[PredictionJobOut]
