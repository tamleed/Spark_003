from __future__ import annotations

import asyncio
from contextlib import contextmanager
from filelock import FileLock


switch_lock = asyncio.Lock()


@contextmanager
def file_switch_lock(lock_path: str, timeout: int = 120):
    lock = FileLock(lock_path, timeout=timeout)
    lock.acquire()
    try:
        yield
    finally:
        lock.release()
