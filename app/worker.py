from __future__ import annotations

import json
import os
import time
import traceback
from datetime import datetime, timezone

import pika
from pika.exceptions import AMQPConnectionError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.csv_utils import read_csv_robust
from app.core.db import SessionLocal
from app.core.model_seed import ensure_models_present
from app.ml.bundle import XGBBundle
from app.models.inference_job import InferenceJob
from app.models.prediction_summary import PredictionSummary
from app.models.traffic_file import TrafficFile


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _get_db() -> Session:
    return SessionLocal()


def _load_models() -> XGBBundle:
    ensure_models_present(
        model_dir=settings.model_dir,
        required_paths=[
            settings.xgb_bin_path,
            settings.xgb_multi_path,
            settings.xgb_class_mapping_path,
            settings.xgb_features_bin_path,
            settings.xgb_features_multi_path,
        ],
        source_dir="/app/models",
    )

    return XGBBundle.load(
        xgb_bin_path=settings.xgb_bin_path,
        xgb_multi_path=settings.xgb_multi_path,
        class_mapping_path=settings.xgb_class_mapping_path,
        features_bin_path=settings.xgb_features_bin_path,
        features_multi_path=settings.xgb_features_multi_path,
    )


def _connect_rabbitmq_with_retry(max_attempts: int = 30, sleep_seconds: float = 1.0):
    params = pika.URLParameters(settings.rabbitmq_url)
    last_exc: Exception | None = None
    for attempt in range(1, max_attempts + 1):
        try:
            return pika.BlockingConnection(params)
        except AMQPConnectionError as e:
            last_exc = e
            print(f"[worker] RabbitMQ connection failed (attempt {attempt}/{max_attempts}): {e}")
            time.sleep(sleep_seconds)
    raise last_exc  # type: ignore[misc]


def _process_job(db: Session, bundle: XGBBundle, job_id: str) -> None:
    job = db.query(InferenceJob).filter(InferenceJob.id == job_id).first()
    if not job:
        return

    tf = db.query(TrafficFile).filter(TrafficFile.id == job.file_id).first()
    if not tf:
        job.status = "failed"
        job.error_message = "TrafficFile not found"
        job.finished_at = _utcnow()
        db.commit()
        return

    job.status = "running"
    job.started_at = _utcnow()
    db.commit()

    stored_path = tf.stored_path
    if not stored_path or not os.path.exists(stored_path):
        job.status = "failed"
        job.error_message = f"CSV not found at stored_path='{stored_path}'. (uploads volume может быть пересоздан)"
        job.finished_at = _utcnow()
        db.commit()
        return

    # -------- Read CSV robustly (comma/semicolon/tab) --------
    try:
        df, sep = read_csv_robust(stored_path, expected_columns=bundle.features_bin)
    except Exception as e:
        job.status = "failed"
        job.error_message = f"Failed to read CSV: {e}"
        job.finished_at = _utcnow()
        db.commit()
        return

    # sanity check: ensure it looks like the model features at least a bit
    cols_in = set(df.columns)
    overlap = len(cols_in & set(bundle.features_bin))
    if overlap < max(3, int(0.1 * len(bundle.features_bin))):
        # If overlap too small, predictions will be garbage (mostly zeros).
        job.status = "failed"
        job.finished_at = _utcnow()
        job.error_message = (
            "CSV columns do not match trained feature set. "
            f"Detected sep='{sep}', parsed_cols={df.shape[1]}, overlap_with_features={overlap}. "
            "Most likely wrong separator or wrong dataset schema."
        )
        db.commit()
        return

    try:
        scored = bundle.predict_rows(df)

        total, attack_rows, attack_ratio, top_class, top_share = bundle.summary_from_scored(scored)

        os.makedirs(settings.uploads_dir, exist_ok=True)
        base = os.path.basename(stored_path)
        scored_name = base[:-4] + "_scored.csv" if base.lower().endswith(".csv") else base + "_scored.csv"
        scored_path = os.path.join(settings.uploads_dir, scored_name)
        scored.to_csv(scored_path, index=False)

        tf.rows_count = total
        db.add(tf)

        ps = db.query(PredictionSummary).filter(PredictionSummary.job_id == job.id).first()
        if not ps:
            ps = PredictionSummary(
                job_id=job.id,
                rows_scored=total,
                attack_rows=attack_rows,
                attack_share=attack_ratio,
                top_class=top_class,
                top_class_share=top_share,
                scored_path=scored_path,
                created_at=_utcnow(),
            )
        else:
            ps.rows_scored = total
            ps.attack_rows = attack_rows
            ps.attack_share = attack_ratio
            ps.top_class = top_class
            ps.top_class_share = top_share
            ps.scored_path = scored_path

        # --- Optional debug (won't break if columns don't exist) ---
        # If your PredictionSummary model has no such columns, this simply won't be stored.
        # If you want persistence, add columns via migration.
        if hasattr(ps, "detected_sep"):
            setattr(ps, "detected_sep", sep)
        if hasattr(ps, "parsed_columns"):
            setattr(ps, "parsed_columns", int(df.shape[1]))

        db.add(ps)

        job.status = "done"
        job.finished_at = _utcnow()
        job.error_message = None
        db.add(job)

        db.commit()

    except Exception as e:
        job.status = "failed"
        job.finished_at = _utcnow()
        job.error_message = f"{e}\n\n{traceback.format_exc()}"
        db.commit()


def main() -> None:
    bundle = _load_models()

    connection = _connect_rabbitmq_with_retry()
    channel = connection.channel()

    channel.queue_declare(queue=settings.ml_queue_name, durable=True)
    channel.basic_qos(prefetch_count=1)

    def callback(ch, method, properties, body: bytes):
        try:
            payload = json.loads(body.decode("utf-8"))
            job_id = payload["job_id"]
        except Exception:
            ch.basic_ack(delivery_tag=method.delivery_tag)
            return

        db = _get_db()
        try:
            _process_job(db, bundle, job_id)
        finally:
            db.close()

        ch.basic_ack(delivery_tag=method.delivery_tag)

    channel.basic_consume(queue=settings.ml_queue_name, on_message_callback=callback)
    print(f"[worker] consuming queue={settings.ml_queue_name} url={settings.rabbitmq_url}")
    channel.start_consuming()


if __name__ == "__main__":
    main()
