from __future__ import annotations

import time

from fastapi import APIRouter, Depends, HTTPException, Request

from .auth import require_admin_api_key
from .config import get_admin_api_key
from .models import HealthResponse, QueueInfoResponse, StatusResponse, SwitchRequest
from .queue import get_queue, get_redis_conn

router = APIRouter(tags=["admin"])
START_TS = time.time()
DRAIN_MODE = False


@router.get("/health", response_model=HealthResponse)
async def health(request: Request):
    cfg = request.app.state.cfg.gateway
    open_health = cfg.get("security", {}).get("health_without_api_key", True)
    if not open_health:
        key = request.headers.get("x-api-key")
        if key != get_admin_api_key():
            raise HTTPException(status_code=401, detail="Invalid or missing admin API key")
    redis_ok = True
    try:
        get_redis_conn().ping()
    except Exception:
        redis_ok = False
    return HealthResponse(status="ok" if redis_ok else "degraded", redis_ok=redis_ok)


@router.get("/status", response_model=StatusResponse)
async def status(request: Request, _: None = Depends(require_admin_api_key)):
    q = get_queue()
    sw = request.app.state.switcher
    return StatusResponse(
        active_model=sw.active_model,
        switching=sw.switching,
        backend_state=sw.backend_state,
        queue_length=len(q),
        uptime_sec=int(time.time() - START_TS),
    )


@router.get("/queue", response_model=QueueInfoResponse)
async def queue_info(request: Request, _: None = Depends(require_admin_api_key)):
    q = get_queue()
    current_job = get_redis_conn().get("rq:worker:current_job")
    sw = request.app.state.switcher
    return QueueInfoResponse(
        queue_length=len(q),
        current_job_id=current_job.decode() if current_job else None,
        active_model=sw.active_model,
        switching=sw.switching,
        drain_mode=DRAIN_MODE,
    )


@router.post("/admin/switch")
async def admin_switch(req: SwitchRequest, request: Request, _: None = Depends(require_admin_api_key)):
    if DRAIN_MODE:
        raise HTTPException(status_code=409, detail="Drain mode enabled")
    q = get_queue()
    sw = request.app.state.switcher
    if len(q) == 0 and not sw.switching:
        await sw.ensure_model_active(req.model)
        return {"status": "switched", "active_model": sw.active_model}

    job = q.enqueue("worker.tasks.admin_switch_job", kwargs={"model": req.model}, at_front=True)
    return {"status": "queued", "job_id": job.id}


@router.post("/admin/drain")
async def admin_drain(_: None = Depends(require_admin_api_key)):
    global DRAIN_MODE
    DRAIN_MODE = True
    return {"drain_mode": DRAIN_MODE}
