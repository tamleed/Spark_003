from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from rq.job import Job

from .auth import require_api_key
from .models import JobCreateRequest, JobCreateResponse, JobResultResponse, JobStatusResponse
from .queue import get_queue, get_redis_conn

router = APIRouter(prefix="/jobs", tags=["jobs"])


def _job_status(job: Job):
    if job.is_finished:
        return "succeeded"
    if job.is_failed:
        return "failed"
    if job.get_status() == "canceled":
        return "cancelled"
    if job.get_status() in {"queued", "deferred", "scheduled"}:
        return "queued"
    if job.get_status() == "started":
        return "running"
    return "queued"


def _iso(dt):
    if not dt:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.isoformat()


@router.post("", response_model=JobCreateResponse)
async def create_job(req: JobCreateRequest, _: None = Depends(require_api_key)):
    q = get_queue()
    payload = req.model_dump()
    payload["async"] = True
    job = q.enqueue("worker.tasks.process_chat_job", kwargs={"payload": payload})
    return JobCreateResponse(id=job.id, status="queued", status_url=f"/jobs/{job.id}")


@router.get("/{job_id}", response_model=JobStatusResponse)
async def get_job(job_id: str, _: None = Depends(require_api_key)):
    try:
        job = Job.fetch(job_id, connection=get_redis_conn())
    except Exception:
        raise HTTPException(status_code=404, detail="Job not found")

    status = _job_status(job)
    meta = job.meta or {}
    return JobStatusResponse(
        id=job.id,
        status=status,
        requested_model=meta.get("requested_model", "unknown"),
        created_at=_iso(job.created_at),
        started_at=meta.get("started_at"),
        finished_at=meta.get("finished_at"),
        queue_position=meta.get("queue_position"),
        progress=meta.get("progress"),
        error=str(job.exc_info)[:4000] if status == "failed" else meta.get("error"),
    )


@router.get("/{job_id}/result", response_model=JobResultResponse)
async def get_job_result(job_id: str, _: None = Depends(require_api_key)):
    try:
        job = Job.fetch(job_id, connection=get_redis_conn())
    except Exception:
        raise HTTPException(status_code=404, detail="Job not found")
    if not job.is_finished:
        raise HTTPException(status_code=409, detail="Job is not finished")
    return JobResultResponse(id=job.id, result=job.result)


@router.post("/{job_id}/cancel")
async def cancel_job(job_id: str, request: Request, _: None = Depends(require_api_key)):
    redis_conn = get_redis_conn()
    try:
        job = Job.fetch(job_id, connection=redis_conn)
    except Exception:
        raise HTTPException(status_code=404, detail="Job not found")

    status = _job_status(job)
    if status == "queued":
        q = get_queue()
        q.remove(job.id)
        job.meta["cancelled_at"] = datetime.now(timezone.utc).isoformat()
        job.set_status("canceled")
        job.save_meta()
        return {"id": job_id, "status": "cancelled", "mode": "queued-remove"}

    if status == "running":
        request.app.state.switcher.stop_current_model()
        job.meta["cancelled_at"] = datetime.now(timezone.utc).isoformat()
        job.meta["finished_at"] = datetime.now(timezone.utc).isoformat()
        job.set_status("canceled")
        job.save_meta()
        return {"id": job_id, "status": "cancelled", "mode": "hard-cancel"}

    return {"id": job_id, "status": status, "detail": "Job already terminal"}
