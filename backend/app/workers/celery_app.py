from celery import Celery

from app.config import settings

celery_app = Celery(
    "spp1",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=["app.workers.inference_task"],
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    worker_prefetch_multiplier=1,   # one task at a time per worker (GPU is exclusive)
)

# DEV_EAGER=true — run tasks synchronously in the API process (no Redis/worker needed)
if settings.dev_eager:
    celery_app.conf.update(
        task_always_eager=True,
        task_eager_propagates=True,
    )
