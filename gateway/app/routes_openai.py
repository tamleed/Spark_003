from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request

from .auth import require_api_key
from .models import ChatCompletionRequest, JobCreateResponse, OpenAIModel, OpenAIModelsResponse
from .queue import get_queue

router = APIRouter(prefix="/v1", tags=["openai"])


@router.get("/models", response_model=OpenAIModelsResponse)
async def list_models(request: Request, _: None = Depends(require_api_key)):
    model_names = list(request.app.state.cfg.models.get("models", {}).keys())
    data = [OpenAIModel(id=name) for name in model_names]
    switcher = request.app.state.switcher
    return OpenAIModelsResponse(data=data, active_model=switcher.active_model, backend_ready=switcher.backend_state == "ready")


@router.post("/chat/completions")
async def chat_completions(req: ChatCompletionRequest, request: Request, _: None = Depends(require_api_key)):
    cfg = request.app.state.cfg.gateway
    if req.stream and req.async_mode:
        raise HTTPException(status_code=400, detail="streaming not implemented in async mode yet")

    q = get_queue()
    if not req.async_mode:
        queue_empty = len(q) == 0
        switcher = request.app.state.switcher
        if not (queue_empty and switcher.active_model == req.model and not switcher.switching):
            raise HTTPException(status_code=409, detail="Queue not empty or model switch required; use async")

        from .proxy import call_backend_chat
        model_cfg = request.app.state.cfg.models["models"][req.model]
        payload = req.model_dump(by_alias=True)
        payload.pop("async", None)
        return await call_backend_chat(model_cfg, payload, timeout_sec=cfg.get("timeouts", {}).get("INFERENCE_TIMEOUT_SEC", 1200))

    job = q.enqueue(
        "worker.tasks.process_chat_job",
        kwargs={"payload": req.model_dump(by_alias=True), "request_id": request.state.request_id},
        result_ttl=cfg.get("jobs", {}).get("result_ttl_sec", 86400),
        failure_ttl=cfg.get("jobs", {}).get("failure_ttl_sec", 86400),
    )
    return JobCreateResponse(id=job.id, status="queued", status_url=f"/jobs/{job.id}")
