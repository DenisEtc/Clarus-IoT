from __future__ import annotations

import csv
import io
import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_current_user
from app.models.inference_job import InferenceJob
from app.models.prediction_summary import PredictionSummary
from app.models.traffic_file import TrafficFile
from app.schemas.predictions import PredictionJobOut, PredictionSummaryOut
from app.services.billing import require_active_subscription

router = APIRouter(tags=["predictions"])


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _compute_stub_summary(rows: list[dict]) -> tuple[int, int, float, str, float]:
    """MVP-заглушка сводки.

    Возвращает:
      - total_rows
      - attack_rows / attack_ratio (по 'label'/'attack', если есть)
      - top_class / top_share (по 'label'/'attack', если есть)
    """
    total = len(rows)
    if total == 0:
        return 0, 0, 0.0, "unknown", 0.0

    label_key: Optional[str] = None
    for k in ("label", "attack", "class"):
        if k in rows[0]:
            label_key = k
            break

    if not label_key:
        return total, 0, 0.0, "unknown", 0.0

    counts: dict[str, int] = {}
    for r in rows:
        v = str(r.get(label_key, "")).strip()
        if not v:
            continue
        counts[v] = counts.get(v, 0) + 1

    if not counts:
        return total, 0, 0.0, "unknown", 0.0

    top_class = max(counts, key=counts.get)
    top_count = counts[top_class]
    top_share = top_count / total

    attack_rows = 0
    for r in rows:
        v = str(r.get(label_key, "")).strip()
        lv = v.lower()
        if lv in ("0", "normal", "benign", "legit", ""):
            continue
        attack_rows += 1

    attack_ratio = attack_rows / total if total else 0.0
    return total, attack_rows, attack_ratio, top_class, top_share


@router.post("/upload", response_model=PredictionJobOut)
def upload_for_prediction(
    csv_file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    # Проверка подписки (иначе нельзя предсказывать)
    require_active_subscription(db, user.id)

    if not csv_file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only CSV files are supported")

    raw = csv_file.file.read()
    if not raw:
        raise HTTPException(status_code=400, detail="Empty file")

    # Читаем CSV максимально “толерантно”
    try:
        text = raw.decode("utf-8", errors="replace")
        reader = csv.DictReader(io.StringIO(text))
        rows = [r for r in reader]
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to parse CSV: {e}")

    total_rows, attack_rows, attack_ratio, top_class, top_share = _compute_stub_summary(rows)
    now = _utcnow()

    # 1) TrafficFile (под реальные колонки модели)
    tf = TrafficFile(
        user_id=user.id,
        original_filename=csv_file.filename,
        stored_path=f"uploads/{uuid.uuid4()}_{csv_file.filename}",
        rows_count=total_rows,
        created_at=now,
    )
    db.add(tf)
    db.commit()
    db.refresh(tf)

    # 2) InferenceJob (под реальные колонки модели)
    job = InferenceJob(
        user_id=user.id,
        file_id=tf.id,
        status="finished",
        created_at=now,
        started_at=now,
        finished_at=now,
        error_message=None,
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    # 3) PredictionSummary (под реальные колонки модели)
    ps = PredictionSummary(
        job_id=job.id,
        rows_scored=total_rows,
        attack_share=attack_ratio,
        top_class=top_class,
        top_class_share=top_share,
        created_at=now,
    )
    db.add(ps)
    db.commit()
    db.refresh(ps)

    return PredictionJobOut(
        job_id=job.id,
        status=job.status,
        summary=PredictionSummaryOut(
            total_rows=total_rows,
            attack_rows=attack_rows,
            attack_ratio=attack_ratio,
        ),
    )
