from __future__ import annotations

import json
import pika

from app.core.config import settings


def publish_ml_job(job_id: str) -> None:
    params = pika.URLParameters(settings.rabbitmq_url)
    connection = pika.BlockingConnection(params)
    channel = connection.channel()

    channel.queue_declare(queue=settings.ml_queue_name, durable=True)

    body = json.dumps({"job_id": job_id}).encode("utf-8")
    channel.basic_publish(
        exchange="",
        routing_key=settings.ml_queue_name,
        body=body,
        properties=pika.BasicProperties(
            delivery_mode=2,  # persistent
            content_type="application/json",
        ),
    )

    connection.close()
