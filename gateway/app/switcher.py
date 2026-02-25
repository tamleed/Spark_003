from __future__ import annotations

import asyncio
import os
import subprocess
import time
from typing import Any, Dict, Optional

import httpx

from .locks import file_switch_lock, switch_lock


class ModelSwitcher:
    def __init__(self, cfg):
        self.cfg = cfg
        self.active_model: Optional[str] = None
        self.switching = False
        self.backend_state = "idle"

    def get_active_model(self) -> Optional[str]:
        return self.active_model

    def _container_name(self) -> str:
        prefix = os.getenv("BACKEND_CONTAINER_NAME_PREFIX", "llm-backend")
        return f"{prefix}-active"

    def _docker(self, args: list[str], check: bool = True) -> subprocess.CompletedProcess:
        return subprocess.run(["docker", *args], capture_output=True, text=True, check=check)

    def stop_current_model(self):
        cname = self._container_name()
        graceful = int(self.cfg.gateway.get("timeouts", {}).get("GRACEFUL_STOP_TIMEOUT_SEC", 20))
        self._docker(["rm", "-f", cname], check=False)
        stop = self._docker(["stop", "--time", str(graceful), cname], check=False)
        if stop.returncode != 0:
            self._docker(["kill", cname], check=False)
        self._docker(["rm", "-f", cname], check=False)
        self.active_model = None
        self.backend_state = "stopped"

    def start_model(self, model_name: str):
        model_cfg = self.cfg.models["models"][model_name]
        image = model_cfg.get("backend", {}).get("image", "nvcr.io/nvidia/vllm:25.11-py3")
        port = int(model_cfg.get("backend", {}).get("port", 8001))
        args = model_cfg.get("backend", {}).get("vllm_args", [])
        source = model_cfg["source"]["value"]
        hf_home = self.cfg.gateway.get("paths", {}).get("hf_home", "/var/lib/huggingface")

        cmd = [
            "run", "-d", "--name", self._container_name(), "--network", os.getenv("DOCKER_NETWORK_MODE", "host"),
            "-e", f"HF_TOKEN={os.getenv('HF_TOKEN', '')}",
            "-e", f"HF_HOME={hf_home}",
            "-e", f"TRANSFORMERS_CACHE={hf_home}",
            "-v", "/mnt/models:/mnt/models",
            "-v", f"{hf_home}:{hf_home}",
            image,
            "python", "-m", "vllm.entrypoints.openai.api_server",
            "--model", source,
            "--port", str(port),
            *args,
        ]
        self._docker(cmd)
        self.active_model = model_name
        self.backend_state = "starting"

    async def wait_backend_ready(self, model_name: str):
        model_cfg = self.cfg.models["models"][model_name]
        port = int(model_cfg.get("backend", {}).get("port", 8001))
        timeout = int(self.cfg.gateway.get("timeouts", {}).get("BACKEND_READY_TIMEOUT_SEC", 600))
        start = time.time()
        async with httpx.AsyncClient(timeout=5.0) as client:
            while time.time() - start < timeout:
                try:
                    r = await client.get(f"http://127.0.0.1:{port}/v1/models")
                    if r.status_code == 200:
                        self.backend_state = "ready"
                        return
                except Exception:
                    pass
                await asyncio.sleep(2)

        logs = self._docker(["logs", "--tail", "200", self._container_name()], check=False)
        self.backend_state = "failed"
        raise RuntimeError(f"Backend readiness timeout for {model_name}. Logs:\n{logs.stdout}\n{logs.stderr}")

    async def ensure_model_active(self, model_name: str):
        model_cfg = self.cfg.models.get("models", {})
        if model_name not in model_cfg:
            raise ValueError(f"Unknown model: {model_name}")

        if self.active_model == model_name and self.backend_state == "ready":
            return

        lock_path = self.cfg.gateway.get("locks", {}).get("file_lock_path", "/var/lock/llm-switch.lock")
        async with switch_lock:
            with file_switch_lock(lock_path, timeout=int(self.cfg.gateway.get("timeouts", {}).get("SWITCH_TIMEOUT_SEC", 900))):
                if self.active_model == model_name and self.backend_state == "ready":
                    return
                self.switching = True
                try:
                    if self.active_model:
                        self.stop_current_model()
                    self.start_model(model_name)
                    await self.wait_backend_ready(model_name)
                finally:
                    self.switching = False
