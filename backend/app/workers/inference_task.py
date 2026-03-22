"""Celery task: run LLM inference and persist results to the database."""

from datetime import datetime, timezone

from celery import Task
from celery.utils.log import get_task_logger

from app.database import SessionLocal
from app.inference.backend_factory import create_backend
from app.inference.base import GenerationConfig
from app.models.metric import Metric
from app.models.run import Run
from app.models.tensor_artifact import TensorArtifact
from app.workers.celery_app import celery_app

logger = get_task_logger(__name__)


class InferenceTask(Task):
    """Base task class that holds a long-lived backend to avoid repeated model loads."""
    abstract = True
    _backend = None
    _loaded_model_id = None
    _loaded_device = None

    def get_backend(self, backend_type: str, model_id: str, device: str):
        """Return a cached backend, reloading only if model or device changed."""
        if (
            self._backend is None
            or self._loaded_model_id != model_id
            or self._loaded_device != device
        ):
            if self._backend is not None:
                self._backend.unload_model()
            self._backend = create_backend(backend_type)
            self._backend.load_model(model_id, device)
            self._loaded_model_id = model_id
            self._loaded_device = device
        return self._backend


@celery_app.task(bind=True, base=InferenceTask, name="inference.run")
def run_inference(self: InferenceTask, run_id: int) -> dict:
    db = SessionLocal()
    try:
        run = db.get(Run, run_id)
        if run is None:
            raise ValueError(f"Run {run_id} not found")

        cfg = run.config
        run.status = "RUNNING"
        db.commit()
        logger.info("Starting inference for run %d: model=%s device=%s", run_id, cfg["model_id"], cfg["device"])

        backend = self.get_backend(
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

        result = backend.generate(gen_config)

        # Persist aggregate metrics
        aggregate_metrics = [
            Metric(run_id=run_id, metric_type="ttft_ms", value=result.time_to_first_token_ms),
            Metric(run_id=run_id, metric_type="total_latency_ms", value=result.total_latency_ms),
            Metric(run_id=run_id, metric_type="throughput_tps", value=result.throughput_tps),
            Metric(run_id=run_id, metric_type="peak_memory_mb", value=result.peak_memory_mb),
            Metric(run_id=run_id, metric_type="num_tokens", value=result.num_tokens),
        ]
        db.add_all(aggregate_metrics)

        # Persist tensor artifacts
        for layer_name, file_path in result.tensor_artifacts.items():
            db.add(TensorArtifact(
                run_id=run_id,
                layer_name=layer_name,
                file_path=file_path,
            ))

        run.status = "COMPLETED"
        run.finished_at = datetime.now(timezone.utc)
        run.config = {**run.config, "output_text": result.text}
        db.commit()

        logger.info(
            "Run %d completed: %d tokens, %.1f tps, %.1f ms latency",
            run_id, result.num_tokens, result.throughput_tps, result.total_latency_ms,
        )
        return {"run_id": run_id, "status": "COMPLETED", "num_tokens": result.num_tokens}

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
