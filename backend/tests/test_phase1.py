"""Phase 1 integration tests.

Run with:
    pytest tests/test_phase1.py -v

Requires: pip install -r requirements.txt
The Celery task is executed eagerly (no broker needed).
"""

import pytest
from unittest.mock import patch


# ---------------------------------------------------------------------------
# Unit tests — HFBackend + collectors (no real model download)
# ---------------------------------------------------------------------------

class TestMemoryCollector:
    def test_cpu_returns_float(self):
        from app.collectors.memory import get_peak_memory_mb, reset_memory_stats
        reset_memory_stats("cpu")
        mb = get_peak_memory_mb("cpu")
        assert isinstance(mb, float)
        assert mb > 0  # process is using some RAM

    def test_cuda_returns_zero_when_unavailable(self):
        import torch
        if torch.cuda.is_available():
            pytest.skip("CUDA is available — skipping unavailability test")
        from app.collectors.memory import get_peak_memory_mb
        # Should not raise, returns 0 when no CUDA allocations
        mb = get_peak_memory_mb("cuda")
        assert mb == 0.0


class TestInferenceBackendBase:
    def test_generation_result_throughput(self):
        from app.inference.base import GenerationResult, TokenEvent
        result = GenerationResult(
            text="hello world",
            tokens=[
                TokenEvent(token="hello", token_id=1, step=0, elapsed_ms=100),
                TokenEvent(token=" world", token_id=2, step=1, elapsed_ms=200),
            ],
            tensor_artifacts={},
            time_to_first_token_ms=100.0,
            total_latency_ms=1000.0,
            peak_memory_mb=512.0,
            num_tokens=2,
        )
        assert result.throughput_tps == pytest.approx(2.0, rel=0.01)

    def test_throughput_zero_latency(self):
        from app.inference.base import GenerationResult
        result = GenerationResult(
            text="", tokens=[], tensor_artifacts={},
            time_to_first_token_ms=0, total_latency_ms=0,
            peak_memory_mb=0, num_tokens=0,
        )
        assert result.throughput_tps == 0.0


class TestBackendFactory:
    def test_hf_backend_created(self):
        from app.inference.backend_factory import create_backend
        from app.inference.hf_backend import HFBackend
        backend = create_backend("huggingface")
        assert isinstance(backend, HFBackend)

    def test_unknown_backend_raises(self):
        from app.inference.backend_factory import create_backend
        with pytest.raises(ValueError, match="Unknown backend"):
            create_backend("nonexistent")


# ---------------------------------------------------------------------------
# Integration test — POST /runs → DB (Celery task mocked)
# ---------------------------------------------------------------------------

class TestRunsAPI:
    def test_create_run_returns_202(self, client):
        with patch("app.api.runs.run_inference.delay") as mock_delay:
            resp = client.post("/runs", json={
                "model_id": "gpt2",
                "prompt": "Hello, world!",
                "device": "cpu",
                "max_new_tokens": 10,
            })
        assert resp.status_code == 202
        data = resp.json()
        assert data["status"] == "PENDING"
        assert data["id"] is not None
        mock_delay.assert_called_once_with(data["id"])

    def test_get_run_not_found(self, client):
        resp = client.get("/runs/99999")
        assert resp.status_code == 404

    def test_list_runs_empty(self, client):
        resp = client.get("/runs")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_system_gpus(self, client):
        resp = client.get("/system/gpus")
        assert resp.status_code == 200
        devices = resp.json()["devices"]
        assert any(d["device"] == "cpu" for d in devices)


# ---------------------------------------------------------------------------
# Integration test — Celery task run eagerly with gpt2 on CPU
# ---------------------------------------------------------------------------

class TestInferenceTaskEager:
    """Runs the actual Celery task synchronously using task.apply() (no broker).

    Downloads gpt2 (~500 MB) on first run; subsequent runs use HF cache.
    Skip with: pytest -m 'not slow'
    """

    @pytest.mark.slow
    def test_run_gpt2_cpu_metrics_written(self, db_session):
        from datetime import datetime, timezone

        from app.models.metric import Metric
        from app.models.run import Run
        from app.workers.inference_task import run_inference

        # Create a run record
        run = Run(
            name="test-gpt2-cpu",
            status="PENDING",
            config={
                "model_id": "gpt2",
                "prompt": "The capital of France is",
                "device": "cpu",
                "backend_type": "huggingface",
                "max_new_tokens": 20,
                "temperature": 1.0,
                "do_sample": False,
                "capture_layers": [],
            },
            created_at=datetime.now(timezone.utc),
        )
        db_session.add(run)
        db_session.commit()
        run_id = run.id

        # Patch SessionLocal to use the test DB session
        with patch("app.workers.inference_task.SessionLocal", return_value=db_session):
            # apply() runs the task synchronously in the same process
            result = run_inference.apply(args=[run_id])

        assert result.successful(), f"Task failed: {result.result}"

        db_session.expire_all()
        updated_run = db_session.get(Run, run_id)
        assert updated_run.status == "COMPLETED"
        assert updated_run.finished_at is not None

        metrics = db_session.query(Metric).filter(Metric.run_id == run_id).all()
        metric_types = {m.metric_type for m in metrics}

        assert "ttft_ms" in metric_types
        assert "total_latency_ms" in metric_types
        assert "throughput_tps" in metric_types
        assert "peak_memory_mb" in metric_types
        assert "num_tokens" in metric_types

        throughput = next(m.value for m in metrics if m.metric_type == "throughput_tps")
        assert throughput > 0, "Expected positive throughput"

        latency = next(m.value for m in metrics if m.metric_type == "total_latency_ms")
        assert latency > 0, "Expected positive latency"
