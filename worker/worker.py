from __future__ import annotations

import os

from redis import Redis
from rq import Connection, Worker


def main():
    redis_url = os.getenv("REDIS_URL", "redis://127.0.0.1:6379/0")
    conn = Redis.from_url(redis_url)
    with Connection(conn):
        worker = Worker(["llm_jobs"], name="llm-worker-1")
        worker.work(with_scheduler=False, logging_level=os.getenv("LOG_LEVEL", "INFO"))


if __name__ == "__main__":
    main()
