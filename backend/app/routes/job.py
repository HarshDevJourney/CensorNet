from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Job
from app.schemas import JobResponse, JobStatusResponse
from app.services import video_service

router = APIRouter(prefix="/jobs", tags=["Jobs"])


def _get(db: Session, job_id: int) -> Job:
    job = db.get(Job, job_id)
    if not job:
        raise HTTPException(404, "job not found")
    return job


@router.get("/{job_id}", response_model=JobResponse)
def get_job(job_id: int, db: Session = Depends(get_db)):
    return _get(db, job_id)


@router.get("/{job_id}/status", response_model=JobStatusResponse)
def job_status(job_id: int, db: Session = Depends(get_db)):
    return _get(db, job_id)


@router.post("/{job_id}/cancel", response_model=JobResponse)
def cancel_job(job_id: int, db: Session = Depends(get_db)):
    return video_service.cancel_job(db, _get(db, job_id))
