from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy.orm import Session, selectinload

import app.streaming as streaming
from app.database import get_db
from app.models.run import Run
from app.schemas.run import RunCreate, RunOut
from app.workers.inference_task import run_inference_background

router = APIRouter()


@router.post("", response_model=RunOut, status_code=202)
async def create_run(
    payload: RunCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    run = Run(name=payload.name, status="PENDING", config=payload.model_dump())
    db.add(run)
    db.commit()
    db.refresh(run)

    # Create queue before starting task so WebSocket can connect immediately
    streaming.create_queue(run.id)
    background_tasks.add_task(run_inference_background, run.id)

    return run


@router.get("", response_model=list[RunOut])
def list_runs(db: Session = Depends(get_db)):
    return db.query(Run).options(selectinload(Run.metrics)).order_by(Run.id.desc()).all()


@router.get("/{run_id}", response_model=RunOut)
def get_run(run_id: int, db: Session = Depends(get_db)):
    run = db.query(Run).options(selectinload(Run.metrics)).filter(Run.id == run_id).first()
    if run is None:
        raise HTTPException(status_code=404, detail=f"Run {run_id} not found")
    return run
