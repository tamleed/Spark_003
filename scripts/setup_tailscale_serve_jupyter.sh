#!/usr/bin/env bash
set -euo pipefail
TARGET="${1:-http://127.0.0.1:8888}"
PORT="${2:-8443}"

sudo tailscale serve --bg "$PORT" "$TARGET"
echo "[INFO] Tailnet-only Jupyter serve enabled"
tailscale serve status || true
