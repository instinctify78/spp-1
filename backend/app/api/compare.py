"""Compare endpoint — pivot metrics and benchmark scores across multiple runs."""

import csv
import io

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session, selectinload

from app.database import get_db
from app.models.benchmark import BenchmarkResult
from app.models.metric import Metric
from app.models.run import Run

router = APIRouter()

METRIC_LABELS = {
    "throughput_tps":   "Throughput (tok/s)",
    "total_latency_ms": "Latency (ms)",
    "ttft_ms":          "TTFT (ms)",
    "peak_memory_mb":   "Peak Memory (MB)",
    "num_tokens":       "Tokens Generated",
}

# For these metrics, lower is better
LOWER_IS_BETTER = {"total_latency_ms", "ttft_ms", "peak_memory_mb", "perplexity"}


def _build_comparison(run_ids: list[int], db: Session) -> dict:
    runs = (
        db.query(Run)
        .options(selectinload(Run.metrics))
        .filter(Run.id.in_(run_ids))
        .all()
    )
    if not runs:
        raise HTTPException(status_code=404, detail="No runs found")

    run_map = {r.id: r for r in runs}

    # Pivot metrics: {metric_type: {run_id: value}}
    metrics: dict[str, dict[int, float]] = {}
    for run in runs:
        for m in run.metrics:
            metrics.setdefault(m.metric_type, {})[run.id] = m.value

    # Pivot benchmarks
    benchmark_rows = (
        db.query(BenchmarkResult)
        .filter(BenchmarkResult.run_id.in_(run_ids))
        .all()
    )
    for b in benchmark_rows:
        metrics.setdefault(b.task, {})[b.run_id] = b.score

    # Annotate each metric row with best/worst run
    annotated: dict[str, dict] = {}
    for metric_type, values in metrics.items():
        if not values:
            continue
        lower_better = metric_type in LOWER_IS_BETTER
        best_id = min(values, key=values.__getitem__) if lower_better else max(values, key=values.__getitem__)
        worst_id = max(values, key=values.__getitem__) if lower_better else min(values, key=values.__getitem__)
        annotated[metric_type] = {
            "label": METRIC_LABELS.get(metric_type, metric_type),
            "lower_is_better": lower_better,
            "values": {str(rid): v for rid, v in values.items()},
            "best_run_id": best_id,
            "worst_run_id": worst_id,
        }

    return {
        "runs": [
            {
                "id": r.id,
                "name": r.name or f"Run #{r.id}",
                "model_id": r.config.get("model_id"),
                "device": r.config.get("device"),
                "status": r.status,
            }
            for r in runs
        ],
        "metrics": annotated,
    }


@router.get("/compare")
def compare_runs(
    run_ids: str = Query(..., description="Comma-separated run IDs e.g. 1,2,3"),
    format: str = Query("json", description="json or csv"),
    db: Session = Depends(get_db),
):
    ids = [int(x.strip()) for x in run_ids.split(",") if x.strip().isdigit()]
    if not ids:
        raise HTTPException(status_code=400, detail="Provide at least one valid run_id")

    data = _build_comparison(ids, db)

    if format == "csv":
        return _to_csv(data)

    return data


def _to_csv(data: dict) -> StreamingResponse:
    runs = data["runs"]
    metrics = data["metrics"]

    output = io.StringIO()
    writer = csv.writer(output)

    # Header: Metric, Run1 name, Run2 name, ...
    writer.writerow(["Metric"] + [f"{r['name']} ({r['device']})" for r in runs])

    for metric_type, row in metrics.items():
        values = [row["values"].get(str(r["id"]), "") for r in runs]
        writer.writerow([row["label"]] + values)

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=comparison.csv"},
    )
