#!/usr/bin/env bash
set -euo pipefail

MODELS_YAML="${MODELS_YAML_PATH:-/opt/llm-switchboard/configs/models.yaml}"
HF_HOME="${HF_HOME:-/var/lib/huggingface}"
mkdir -p "$HF_HOME"

python3 - <<'PY'
import os, yaml, subprocess, sys
from pathlib import Path

p = Path(os.getenv("MODELS_YAML_PATH", "/opt/llm-switchboard/configs/models.yaml"))
cfg = yaml.safe_load(p.read_text()) or {}
models = cfg.get("models", {})
ok, fail = [], []
for name, m in models.items():
    src = m.get("source", {})
    if src.get("type") != "huggingface_repo":
        print(f"[SKIP] {name}: source.type={src.get('type')}")
        continue
    repo = src.get("value")
    if not repo or repo.startswith("TODO/"):
        print(f"[SKIP] {name}: placeholder repo {repo}")
        continue
    print(f"[INFO] Downloading {name} from {repo}")
    cmd = ["huggingface-cli", "download", repo, "--local-dir", f"/mnt/models/{name}"]
    env = os.environ.copy()
    try:
        subprocess.run(cmd, env=env, check=True)
        ok.append(name)
    except Exception as e:
        print(f"[ERROR] {name}: {e}")
        fail.append(name)
print("\nSummary")
print("  OK:", ok)
print("  FAIL:", fail)
if fail:
    sys.exit(1)
PY
