from __future__ import annotations

import os
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, Response
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_current_user
from app.core.config import settings
from app.models.inference_job import InferenceJob
from app.models.prediction_summary import PredictionSummary
from app.models.traffic_file import TrafficFile
from app.schemas.predictions import PredictionJobOut, PredictionJobListItemOut, PredictionSummaryOut
from app.services.billing import require_active_subscription
from app.services.queue import publish_ml_job

router = APIRouter(tags=["predictions"])


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


@router.post("/upload", response_model=PredictionJobOut)
def upload_for_prediction(
    csv_file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    require_active_subscription(db, user.id)

    if not csv_file.filename or not csv_file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only CSV files are supported")

    raw = csv_file.file.read()
    if not raw:
        raise HTTPException(status_code=400, detail="Empty file")

    os.makedirs(settings.uploads_dir, exist_ok=True)
    safe_name = os.path.basename(csv_file.filename)
    stored_name = f"{uuid.uuid4()}_{safe_name}"
    stored_path = os.path.join(settings.uploads_dir, stored_name)

    try:
        with open(stored_path, "wb") as f:
            f.write(raw)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to store file: {e}")

    now = _utcnow()

    tf = TrafficFile(
        user_id=user.id,
        original_filename=safe_name,
        stored_path=stored_path,
        rows_count=None,
        created_at=now,
    )
    db.add(tf)
    db.commit()
    db.refresh(tf)

    job = InferenceJob(
        user_id=user.id,
        file_id=tf.id,
        status="queued",
        created_at=now,
        started_at=None,
        finished_at=None,
        error_message=None,
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    publish_ml_job(job_id=str(job.id))

    return PredictionJobOut(
        job_id=job.id,
        status=job.status,
        summary=PredictionSummaryOut(
            total_rows=0,
            attack_rows=0,
            attack_ratio=0.0,
            top_class=None,
            top_class_share=None,
        ),
    )


@router.get("/jobs", response_model=list[PredictionJobListItemOut])
def list_prediction_jobs(
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """Return user's jobs for the dashboard/history.

    Important: this route must be declared before /{job_id} to avoid "jobs" being
    captured by the UUID path parameter.
    """

    limit = max(1, min(int(limit), 200))
    offset = max(0, int(offset))

    rows = (
        db.query(InferenceJob, TrafficFile, PredictionSummary)
        .join(TrafficFile, TrafficFile.id == InferenceJob.file_id)
        .outerjoin(PredictionSummary, PredictionSummary.job_id == InferenceJob.id)
        .filter(InferenceJob.user_id == user.id)
        .order_by(InferenceJob.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )

    out: list[PredictionJobListItemOut] = []

    for job, tf, summary in rows:
        if summary:
            total = int(summary.rows_scored or 0)
            attack_rows = int(summary.attack_rows or 0)
            attack_ratio = float(summary.attack_share or 0.0)

            out_summary = PredictionSummaryOut(
                total_rows=total,
                attack_rows=attack_rows,
                attack_ratio=attack_ratio,
                top_class=summary.top_class,
                top_class_share=float(summary.top_class_share)
                if summary.top_class_share is not None
                else None,
            )
        else:
            out_summary = PredictionSummaryOut(
                total_rows=0,
                attack_rows=0,
                attack_ratio=0.0,
                top_class=None,
                top_class_share=None,
            )

        created_iso = job.created_at.isoformat() if getattr(job, "created_at", None) else None

        out.append(
            PredictionJobListItemOut(
                job_id=job.id,
                status=job.status,
                summary=out_summary,
                created_at=created_iso,
                original_filename=getattr(tf, "original_filename", None),
            )
        )

    return out


@router.get("/{job_id}", response_model=PredictionJobOut)
def get_prediction_job(
    job_id: uuid.UUID,
    response: Response,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    job = (
        db.query(InferenceJob)
        .filter(InferenceJob.id == job_id, InferenceJob.user_id == user.id)
        .first()
    )
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    # If failed, provide diagnostic in header (does not break response schema)
    if job.status == "failed" and job.error_message:
        # shorten header size a bit
        msg = job.error_message.replace("\n", " ")[:800]
        response.headers["X-Job-Error"] = msg

    summary = db.query(PredictionSummary).filter(PredictionSummary.job_id == job.id).first()

    if summary:
        total = int(summary.rows_scored or 0)
        attack_rows = int(summary.attack_rows or 0)
        attack_ratio = float(summary.attack_share or 0.0)

        out_summary = PredictionSummaryOut(
            total_rows=total,
            attack_rows=attack_rows,
            attack_ratio=attack_ratio,
            top_class=summary.top_class,
            top_class_share=float(summary.top_class_share) if summary.top_class_share is not None else None,
        )
    else:
        out_summary = PredictionSummaryOut(
            total_rows=0,
            attack_rows=0,
            attack_ratio=0.0,
            top_class=None,
            top_class_share=None,
        )

    return PredictionJobOut(job_id=job.id, status=job.status, summary=out_summary)


@router.get("/{job_id}/download")
def download_scored_csv(
    job_id: uuid.UUID,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    job = (
        db.query(InferenceJob)
        .filter(InferenceJob.id == job_id, InferenceJob.user_id == user.id)
        .first()
    )
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    if job.status != "done":
        raise HTTPException(status_code=409, detail=f"Job is not done (status={job.status})")

    summary = db.query(PredictionSummary).filter(PredictionSummary.job_id == job.id).first()
    if not summary or not summary.scored_path:
        raise HTTPException(status_code=404, detail="Scored file not found")

    if not os.path.exists(summary.scored_path):
        raise HTTPException(status_code=404, detail="Scored file missing on disk (uploads volume?)")

    filename = os.path.basename(summary.scored_path)
    return FileResponse(
        path=summary.scored_path,
        media_type="text/csv",
        filename=filename,
    )
