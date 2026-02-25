from __future__ import annotations

import logging
import os

from fastapi import FastAPI
from fastapi.responses import ORJSONResponse

from .config import load_config
from .middleware import RequestContextMiddleware, SimpleRateLimitMiddleware
from .routes_admin import router as admin_router
from .routes_jobs import router as jobs_router
from .routes_openai import router as openai_router
from .switcher import ModelSwitcher


def create_app() -> FastAPI:
    cfg = load_config()
    app = FastAPI(title="LLM Switchboard", default_response_class=ORJSONResponse)
    app.state.cfg = cfg
    app.state.switcher = ModelSwitcher(cfg)

    app.add_middleware(RequestContextMiddleware)
    app.add_middleware(SimpleRateLimitMiddleware)

    app.include_router(openai_router)
    app.include_router(jobs_router)
    app.include_router(admin_router)
    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn

    logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=False)
