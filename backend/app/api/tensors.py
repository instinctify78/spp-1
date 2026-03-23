"""Tensor artifact endpoints — list and fetch layer activations."""

from pathlib import Path

import numpy as np
from fastapi import APIRouter, HTTPException
from sqlalchemy.orm import Session
from fastapi import Depends

from app.database import get_db
from app.models.tensor_artifact import TensorArtifact

router = APIRouter()

MAX_COLS = 64   # truncate columns for heatmap display


@router.get("/{run_id}/tensors")
def list_tensors(run_id: int, db: Session = Depends(get_db)):
    artifacts = db.query(TensorArtifact).filter(TensorArtifact.run_id == run_id).all()
    return [{"layer_name": a.layer_name, "shape": a.shape, "dtype": a.dtype} for a in artifacts]


@router.get("/{run_id}/tensors/{layer_name:path}")
def get_tensor(run_id: int, layer_name: str, db: Session = Depends(get_db)):
    artifact = (
        db.query(TensorArtifact)
        .filter(TensorArtifact.run_id == run_id, TensorArtifact.layer_name == layer_name)
        .first()
    )
    if artifact is None:
        raise HTTPException(status_code=404, detail="Tensor artifact not found")

    path = Path(artifact.file_path)
    if not path.exists():
        raise HTTPException(status_code=404, detail="Tensor file missing on disk")

    arr = np.load(path)

    # Flatten to 2D: (rows, cols) — take first batch, first token position if needed
    if arr.ndim == 3:
        arr = arr[0]        # [seq_len, hidden] — take batch 0
    elif arr.ndim == 1:
        arr = arr[None, :]  # [1, hidden]

    # Truncate columns for browser transfer
    arr = arr[:, :MAX_COLS]

    # Normalize to [0, 1] for heatmap coloring
    vmin, vmax = float(arr.min()), float(arr.max())
    if vmax > vmin:
        normalized = ((arr - vmin) / (vmax - vmin)).tolist()
    else:
        normalized = arr.tolist()

    return {
        "layer_name": layer_name,
        "shape": list(arr.shape),
        "vmin": vmin,
        "vmax": vmax,
        "data": normalized,
    }
