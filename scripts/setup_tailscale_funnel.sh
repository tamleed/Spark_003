#!/usr/bin/env bash
set -euo pipefail
TARGET="${1:-http://127.0.0.1:8000}"
PORT="${2:-443}"

sudo tailscale funnel --bg "$PORT" "$TARGET"
echo "[INFO] Funnel enabled"
tailscale funnel status || true
echo "[INFO] Disable with: sudo tailscale funnel reset"
