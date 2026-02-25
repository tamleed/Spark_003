from __future__ import annotations

import os
from redis import Redis
from rq import Queue


def get_redis_conn():
    url = os.getenv("REDIS_URL", "redis://127.0.0.1:6379/0")
    return Redis.from_url(url)


def get_queue() -> Queue:
    return Queue("llm_jobs", connection=get_redis_conn(), default_timeout=7200)
