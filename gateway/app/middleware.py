from __future__ import annotations

import time
import uuid
from collections import defaultdict, deque
from typing import Deque, Dict

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse


class RequestContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id
        response = await call_next(request)
        response.headers["X-Request-Id"] = request_id
        return response


class SimpleRateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, rpm: int = 120):
        super().__init__(app)
        self.rpm = rpm
        self.reqs: Dict[str, Deque[float]] = defaultdict(deque)

    async def dispatch(self, request: Request, call_next):
        cfg = request.app.state.cfg.gateway
        limiter_cfg = cfg.get("security", {}).get("rate_limit", {})
        if not limiter_cfg.get("enabled", True):
            return await call_next(request)

        rpm = int(limiter_cfg.get("requests_per_minute", self.rpm))
        key = request.headers.get("x-api-key") or (request.client.host if request.client else "unknown")
        now = time.time()
        bucket = self.reqs[key]
        while bucket and bucket[0] < now - 60:
            bucket.popleft()
        if len(bucket) >= rpm:
            return JSONResponse(status_code=429, content={"detail": "Rate limit exceeded"})
        bucket.append(now)
        return await call_next(request)
