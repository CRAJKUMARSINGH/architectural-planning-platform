"""RQ job queue dispatcher — E04 Async Jobs & Storage.

In dev mode (no REDIS_URL) jobs execute synchronously inline.
In production, jobs are dispatched to Redis and picked up by worker processes.
"""
from __future__ import annotations

import logging
import os

logger = logging.getLogger("advocate.worker.queue")

REDIS_URL: str | None = os.environ.get("REDIS_URL")


def dispatch_job(job_id: str, job_type: str, payload: dict) -> None:
    """Dispatch a job to the RQ queue, or run synchronously if no Redis."""
    if REDIS_URL:
        try:
            from redis import Redis  # type: ignore[import]
            from rq import Queue  # type: ignore[import]

            conn = Redis.from_url(REDIS_URL)
            q = Queue("advocate", connection=conn)
            q.enqueue(
                "services.worker.tasks.run_job",
                job_id=job_id,
                job_type=job_type,
                payload=payload,
                job_timeout=600,
            )
            logger.info("Dispatched job %s (type=%s) to RQ", job_id, job_type)
        except Exception as exc:
            logger.warning("RQ dispatch failed, running inline: %s", exc)
            _run_inline(job_id, job_type, payload)
    else:
        _run_inline(job_id, job_type, payload)


def _run_inline(job_id: str, job_type: str, payload: dict) -> None:
    """Run job synchronously — for local dev without Redis."""
    try:
        from services.worker.tasks import run_job  # noqa: PLC0415
        run_job(job_id=job_id, job_type=job_type, payload=payload)
    except Exception as exc:
        logger.error("Inline job %s failed: %s", job_id, exc)
