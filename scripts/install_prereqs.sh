#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="/opt/llm-switchboard"
PY_VENV="$ROOT_DIR/.venv"
JUP_VENV="/opt/jupyter-venv"
USER_NAME="${SUDO_USER:-$USER}"

sudo apt-get update
sudo apt-get install -y python3-venv python3-pip curl jq ca-certificates

if ! command -v docker >/dev/null 2>&1; then
  curl -fsSL https://get.docker.com | sh
fi

sudo usermod -aG docker "$USER_NAME" || true
echo "[INFO] Added $USER_NAME to docker group. Run 'newgrp docker' or relogin."

sudo mkdir -p "$ROOT_DIR" /var/lib/huggingface /mnt/models "/home/$USER_NAME/work"
sudo chown -R "$USER_NAME":"$USER_NAME" "$ROOT_DIR" "/home/$USER_NAME/work"

python3 -m venv "$PY_VENV"
"$PY_VENV/bin/pip" install --upgrade pip
"$PY_VENV/bin/pip" install -r "$ROOT_DIR/requirements.txt"

python3 -m venv "$JUP_VENV"
"$JUP_VENV/bin/pip" install --upgrade pip jupyterlab

echo "[INFO] Prereqs installation complete"
