from __future__ import annotations

from typing import Any, Dict
import httpx


async def call_backend_chat(model_cfg: Dict[str, Any], payload: Dict[str, Any], timeout_sec: int = 1200) -> Dict[str, Any]:
    port = int(model_cfg.get("backend", {}).get("port", 8001))
    url = f"http://127.0.0.1:{port}/v1/chat/completions"
    async with httpx.AsyncClient(timeout=timeout_sec) as client:
        resp = await client.post(url, json=payload)
        resp.raise_for_status()
        return resp.json()
