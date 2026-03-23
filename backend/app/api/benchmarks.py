"""Benchmark endpoints — trigger and retrieve accuracy benchmarks for a run."""

import asyncio
from typing import Literal

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.benchmark import BenchmarkResult
from app.models.run import Run

router = APIRouter()

SUPPORTED_TASKS = {"perplexity", "hellaswag", "mmlu"}


class BenchmarkRequest(BaseModel):
    tasks: list[Literal["perplexity", "hellaswag", "mmlu"]] = ["perplexity"]


@router.post("/{run_id}/benchmark", status_code=202)
async def trigger_benchmark(
    run_id: int,
    payload: BenchmarkRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    run = db.get(Run, run_id)
    if run is None:
        raise HTTPException(status_code=404, detail=f"Run {run_id} not found")
    if run.status != "COMPLETED":
        raise HTTPException(status_code=400, detail="Run must be COMPLETED before benchmarking")

    background_tasks.add_task(run_benchmarks_background, run_id, payload.tasks)
    return {"run_id": run_id, "tasks": payload.tasks, "status": "queued"}


@router.get("/{run_id}/benchmark")
def get_benchmarks(run_id: int, db: Session = Depends(get_db)):
    results = db.query(BenchmarkResult).filter(BenchmarkResult.run_id == run_id).all()
    return [{"task": r.task, "score": r.score, "metadata": r.metadata_} for r in results]


async def run_benchmarks_background(run_id: int, tasks: list[str]) -> None:
    await asyncio.to_thread(_run_benchmarks_sync, run_id, tasks)


def _run_benchmarks_sync(run_id: int, tasks: list[str]) -> None:
    from app.database import SessionLocal
    from app.workers.inference_task import _get_cached_backend

    db = SessionLocal()
    try:
        run = db.get(Run, run_id)
        if run is None:
            return

        cfg = run.config
        backend = _get_cached_backend(
            backend_type=cfg.get("backend_type", "huggingface"),
            model_id=cfg["model_id"],
            device=cfg["device"],
        )
        model = backend._model
        tokenizer = backend._tokenizer
        device = cfg["device"]

        for task in tasks:
            score = None

            if task == "perplexity":
                from app.benchmarks.perplexity import compute_perplexity
                score = compute_perplexity(model, tokenizer, device)
                db.add(BenchmarkResult(run_id=run_id, task="perplexity", score=score))

            elif task in ("hellaswag", "mmlu"):
                from app.benchmarks.lm_eval_runner import run_lm_eval
                scores = run_lm_eval(cfg["model_id"], device, [task])
                if task in scores:
                    db.add(BenchmarkResult(run_id=run_id, task=task, score=scores[task]))

        db.commit()

    finally:
        db.close()
