from fastapi import APIRouter, HTTPException

from app import models
from app.schemas import JobResponse, JobStatusResponse
from app.services import video_service

router = APIRouter(prefix="/jobs", tags=["Jobs"])      # one job per video: job_id == video_id


def _get(job_id: int) -> dict:
    info = models.video_info(job_id)
    if not info:
        raise HTTPException(404, "job not found")
    return info


def _response(info: dict) -> dict:
    return {"id": info["id"], "video_id": info["id"], "status": info["status"], "error": info["error"],
            "completed": info["done"], "total": info["total"]}


@router.get("/{job_id}", response_model=JobResponse)
def get_job(job_id: int):
    return _response(_get(job_id))


@router.get("/{job_id}/status", response_model=JobStatusResponse)
def job_status(job_id: int):
    return {"id": job_id, "status": _get(job_id)["status"]}


@router.post("/{job_id}/cancel", response_model=JobResponse)
def cancel_job(job_id: int):
    _get(job_id)
    video_service.cancel_job(job_id)
    return _response(_get(job_id))
