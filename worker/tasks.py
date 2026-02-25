from __future__ import annotations

import asyncio
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

import yaml
from rq import get_current_job

import sys

sys.path.append(str(Path(__file__).resolve().parents[1] / "gateway"))

from app.proxy import call_backend_chat
from app.switcher import ModelSwitcher
from app.config import AppConfig


CFG_CACHE: AppConfig | None = None
SWITCHER: ModelSwitcher | None = None


def _load_cfg() -> AppConfig:
    global CFG_CACHE
    if CFG_CACHE:
        return CFG_CACHE
    gateway_path = os.getenv("GATEWAY_YAML_PATH", "/opt/llm-switchboard/configs/gateway.yaml")
    models_path = os.getenv("MODELS_YAML_PATH", "/opt/llm-switchboard/configs/models.yaml")
    with open(gateway_path, "r", encoding="utf-8") as f:
        gateway = yaml.safe_load(f) or {}
    with open(models_path, "r", encoding="utf-8") as f:
        models = yaml.safe_load(f) or {}
    CFG_CACHE = AppConfig(gateway=gateway, models=models)
    return CFG_CACHE


def _switcher() -> ModelSwitcher:
    global SWITCHER
    if SWITCHER:
        return SWITCHER
    SWITCHER = ModelSwitcher(_load_cfg())
    return SWITCHER


def process_chat_job(payload: Dict[str, Any], request_id: str | None = None):
    job = get_current_job()
    sw = _switcher()
    model = payload["model"]
    job.meta["requested_model"] = model
    job.meta["started_at"] = datetime.now(timezone.utc).isoformat()
    job.save_meta()

    async def _run():
        await sw.ensure_model_active(model)
        model_cfg = _load_cfg().models["models"][model]
        timeout = int(_load_cfg().gateway.get("timeouts", {}).get("INFERENCE_TIMEOUT_SEC", 1200))
        return await call_backend_chat(model_cfg, payload, timeout_sec=timeout)

    try:
        result = asyncio.run(_run())
    except Exception as exc:
        job.meta["error"] = str(exc)
        job.meta["finished_at"] = datetime.now(timezone.utc).isoformat()
        job.save_meta()
        raise

    job.meta["finished_at"] = datetime.now(timezone.utc).isoformat()
    job.meta["progress"] = 1.0
    job.save_meta()
    return result


def admin_switch_job(model: str):
    async def _run():
        await _switcher().ensure_model_active(model)

    asyncio.run(_run())
    return {"status": "switched", "active_model": model}
