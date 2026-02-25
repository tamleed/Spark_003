#!/usr/bin/env bash
set -euo pipefail
IMAGE="${1:-nvcr.io/nvidia/vllm:25.11-py3}"
docker pull "$IMAGE"
