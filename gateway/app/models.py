from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field


JobStatus = Literal["queued", "running", "succeeded", "failed", "cancelled"]


class ChatMessage(BaseModel):
    role: Literal["system", "user", "assistant", "tool"]
    content: str


class ChatCompletionRequest(BaseModel):
    model: str
    messages: List[ChatMessage]
    temperature: float = 0.7
    max_tokens: int = 512
    stream: bool = False
    async_mode: bool = Field(default=True, alias="async")


class JobCreateRequest(BaseModel):
    model: str
    messages: List[ChatMessage]
    temperature: float = 0.7
    max_tokens: int = 512
    stream: bool = False


class JobCreateResponse(BaseModel):
    id: str
    status: JobStatus
    status_url: str


class JobStatusResponse(BaseModel):
    id: str
    status: JobStatus
    requested_model: str
    created_at: Optional[str] = None
    started_at: Optional[str] = None
    finished_at: Optional[str] = None
    queue_position: Optional[int] = None
    progress: Optional[float] = None
    error: Optional[str] = None


class OpenAIModel(BaseModel):
    id: str
    object: str = "model"
    owned_by: str = "llm-switchboard"


class OpenAIModelsResponse(BaseModel):
    object: str = "list"
    data: List[OpenAIModel]
    active_model: Optional[str]
    backend_ready: bool


class SwitchRequest(BaseModel):
    model: str


class QueueInfoResponse(BaseModel):
    queue_length: int
    current_job_id: Optional[str]
    active_model: Optional[str]
    switching: bool
    drain_mode: bool


class ErrorResponse(BaseModel):
    detail: str


class JobResultResponse(BaseModel):
    id: str
    result: Dict[str, Any]


class HealthResponse(BaseModel):
    status: str
    redis_ok: bool


class StatusResponse(BaseModel):
    active_model: Optional[str]
    switching: bool
    backend_state: str
    queue_length: int
    uptime_sec: int
