from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict

import yaml


@dataclass
class AppConfig:
    gateway: Dict[str, Any]
    models: Dict[str, Any]


def _read_yaml(path: str) -> Dict[str, Any]:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Config not found: {path}")
    with p.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def load_config() -> AppConfig:
    gateway_path = os.getenv("GATEWAY_YAML_PATH", "/opt/llm-switchboard/configs/gateway.yaml")
    models_path = os.getenv("MODELS_YAML_PATH", "/opt/llm-switchboard/configs/models.yaml")
    gateway = _read_yaml(gateway_path)
    models = _read_yaml(models_path)
    return AppConfig(gateway=gateway, models=models)


def get_api_key() -> str:
    return os.getenv("GATEWAY_API_KEY", "")


def get_admin_api_key() -> str:
    return os.getenv("GATEWAY_ADMIN_API_KEY", get_api_key())
