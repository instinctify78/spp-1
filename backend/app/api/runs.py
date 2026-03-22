from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, selectinload

from app.database import get_db
from app.models.run import Run
from app.schemas.run import RunCreate, RunOut
from app.workers.inference_task import run_inference

router = APIRouter()


@router.post("", response_model=RunOut, status_code=202)
def create_run(payload: RunCreate, db: Session = Depends(get_db)):
    run = Run(
        name=payload.name,
        status="PENDING",
        config=payload.model_dump(),
    )
    db.add(run)
    db.commit()
    db.refresh(run)

    run_inference.delay(run.id)

    # In DEV_EAGER mode the task runs synchronously above — re-fetch to get final state
    db.expire_all()
    run = db.query(Run).options(selectinload(Run.metrics)).filter(Run.id == run.id).first()
    return run


@router.get("", response_model=list[RunOut])
def list_runs(db: Session = Depends(get_db)):
    runs = db.query(Run).options(selectinload(Run.metrics)).order_by(Run.id.desc()).all()
    return runs


@router.get("/{run_id}", response_model=RunOut)
def get_run(run_id: int, db: Session = Depends(get_db)):
    run = db.query(Run).options(selectinload(Run.metrics)).filter(Run.id == run_id).first()
    if run is None:
        raise HTTPException(status_code=404, detail=f"Run {run_id} not found")
    return run
