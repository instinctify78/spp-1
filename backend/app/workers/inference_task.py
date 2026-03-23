"""Inference runner — used both by the Celery task and the async background runner."""

import asyncio
from datetime import datetime, timezone

from celery import Task
from celery.utils.log import get_task_logger

from app.database import SessionLocal
from app.inference.backend_factory import create_backend
from app.inference.base import GenerationConfig, TokenEvent
from app.models.metric import Metric
from app.models.run import Run
from app.models.tensor_artifact import TensorArtifact
from app.workers.celery_app import celery_app

logger = get_task_logger(__name__)

# ---------------------------------------------------------------------------
# Shared sync inference runner (used by both Celery task and async background)
# ---------------------------------------------------------------------------

# Module-level backend cache (shared across calls in the same process)
_inference_backend = None
_loaded_model_id = None
_loaded_device = None


def _get_cached_backend(backend_type: str, model_id: str, device: str):
    global _inference_backend, _loaded_model_id, _loaded_device
    if (
        _inference_backend is None
        or _loaded_model_id != model_id
        or _loaded_device != device
    ):
        if _inference_backend is not None:
            _inference_backend.unload_model()
        _inference_backend = create_backend(backend_type)
        _inference_backend.load_model(model_id, device)
        _loaded_model_id = model_id
        _loaded_device = device
    return _inference_backend


def run_inference_sync(run_id: int, token_callback=None) -> None:
    """Run inference synchronously. Safe to call from any thread."""
    db = SessionLocal()
    try:
        run = db.get(Run, run_id)
        if run is None:
            raise ValueError(f"Run {run_id} not found")

        cfg = run.config
        run.status = "RUNNING"
        db.commit()
        logger.info("Starting inference run %d: model=%s device=%s", run_id, cfg["model_id"], cfg["device"])

        backend = _get_cached_backend(
            backend_type=cfg.get("backend_type", "huggingface"),
            model_id=cfg["model_id"],
            device=cfg["device"],
        )

        gen_config = GenerationConfig(
            model_id=cfg["model_id"],
            prompt=cfg["prompt"],
            device=cfg["device"],
            max_new_tokens=cfg.get("max_new_tokens", 256),
            temperature=cfg.get("temperature", 1.0),
            do_sample=cfg.get("do_sample", False),
            capture_layers=cfg.get("capture_layers", []),
        )

        result = backend.generate(gen_config, token_callback=token_callback)

        db.add_all([
            Metric(run_id=run_id, metric_type="ttft_ms",          value=result.time_to_first_token_ms),
            Metric(run_id=run_id, metric_type="total_latency_ms", value=result.total_latency_ms),
            Metric(run_id=run_id, metric_type="throughput_tps",   value=result.throughput_tps),
            Metric(run_id=run_id, metric_type="peak_memory_mb",   value=result.peak_memory_mb),
            Metric(run_id=run_id, metric_type="num_tokens",       value=result.num_tokens),
        ])

        for layer_name, file_path in result.tensor_artifacts.items():
            db.add(TensorArtifact(run_id=run_id, layer_name=layer_name, file_path=file_path))

        run.status = "COMPLETED"
        run.finished_at = datetime.now(timezone.utc)
        run.config = {**run.config, "output_text": result.text}
        db.commit()

        logger.info(
            "Run %d completed: %d tokens, %.1f tps, %.1f ms",
            run_id, result.num_tokens, result.throughput_tps, result.total_latency_ms,
        )

    except Exception as exc:
        logger.exception("Run %d failed: %s", run_id, exc)
        run = db.get(Run, run_id)
        if run:
            run.status = "FAILED"
            run.error = str(exc)
            run.finished_at = datetime.now(timezone.utc)
            db.commit()
        raise

    finally:
        db.close()


# ---------------------------------------------------------------------------
# Async background runner (used by POST /runs for streaming)
# ---------------------------------------------------------------------------

async def run_inference_background(run_id: int) -> None:
    """Async wrapper: runs sync inference in a thread, streams tokens via queue."""
    import app.streaming as streaming

    loop = asyncio.get_event_loop()
    queue = streaming.get_queue(run_id)

    def token_callback(event: TokenEvent) -> None:
        if queue is not None:
            loop.call_soon_threadsafe(
                queue.put_nowait,
                {"type": "token", "token": event.token, "step": event.step, "elapsed_ms": event.elapsed_ms},
            )

    try:
        await asyncio.to_thread(run_inference_sync, run_id, token_callback)
    finally:
        if queue is not None:
            loop.call_soon_threadsafe(queue.put_nowait, {"type": "done"})


# ---------------------------------------------------------------------------
# Celery task (kept for future Redis/worker mode)
# ---------------------------------------------------------------------------

class InferenceTask(Task):
    abstract = True


@celery_app.task(bind=True, base=InferenceTask, name="inference.run")
def run_inference(self: InferenceTask, run_id: int) -> dict:
    run_inference_sync(run_id)
    return {"run_id": run_id, "status": "COMPLETED"}
