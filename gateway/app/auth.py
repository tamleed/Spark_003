from __future__ import annotations

from fastapi import Header, HTTPException, Request

from .config import get_admin_api_key, get_api_key


def require_api_key(request: Request, x_api_key: str | None = Header(default=None)):
    cfg = request.app.state.cfg.gateway
    require_key = cfg.get("security", {}).get("require_api_key", True)
    if not require_key:
        return
    if not x_api_key or x_api_key != get_api_key():
        raise HTTPException(status_code=401, detail="Invalid or missing API key")


def require_admin_api_key(x_api_key: str | None = Header(default=None)):
    if not x_api_key or x_api_key != get_admin_api_key():
        raise HTTPException(status_code=401, detail="Invalid or missing admin API key")
