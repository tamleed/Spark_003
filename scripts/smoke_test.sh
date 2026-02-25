#!/usr/bin/env bash
set -euo pipefail

API="${API_BASE:-http://127.0.0.1:8000}"
KEY="${GATEWAY_API_KEY:-change_me}"
MODEL1="${MODEL1:-gpt-oss120}"
MODEL2="${MODEL2:-qwen3-30b}"

pass() { echo "PASS: $1"; }
fail() { echo "FAIL: $1"; exit 1; }

curl -fsS "$API/health" >/dev/null && pass "/health" || fail "/health"
curl -fsS -H "X-API-Key: $KEY" "$API/v1/models" >/dev/null && pass "/v1/models" || fail "/v1/models"

JOB1=$(curl -fsS -H "X-API-Key: $KEY" -H 'Content-Type: application/json' \
  -d "{\"model\":\"$MODEL1\",\"messages\":[{\"role\":\"user\",\"content\":\"Say ping\"}],\"async\":true}" \
  "$API/v1/chat/completions" | python3 -c 'import sys,json;print(json.load(sys.stdin)["id"])')
pass "job1 queued: $JOB1"

for _ in $(seq 1 120); do
  S=$(curl -fsS -H "X-API-Key: $KEY" "$API/jobs/$JOB1" | python3 -c 'import sys,json;print(json.load(sys.stdin)["status"])')
  [[ "$S" == "succeeded" ]] && break
  [[ "$S" == "failed" ]] && fail "job1 failed"
  sleep 2
done
curl -fsS -H "X-API-Key: $KEY" "$API/jobs/$JOB1/result" >/dev/null && pass "job1 result"

JOB2=$(curl -fsS -H "X-API-Key: $KEY" -H 'Content-Type: application/json' \
  -d "{\"model\":\"$MODEL2\",\"messages\":[{\"role\":\"user\",\"content\":\"Say pong\"}],\"async\":true}" \
  "$API/v1/chat/completions" | python3 -c 'import sys,json;print(json.load(sys.stdin)["id"])')
pass "job2 queued: $JOB2"

CANCEL_JOB=$(curl -fsS -H "X-API-Key: $KEY" -H 'Content-Type: application/json' \
  -d "{\"model\":\"$MODEL1\",\"messages\":[{\"role\":\"user\",\"content\":\"Long generation\"}],\"max_tokens\":4096,\"async\":true}" \
  "$API/v1/chat/completions" | python3 -c 'import sys,json;print(json.load(sys.stdin)["id"])')
curl -fsS -X POST -H "X-API-Key: $KEY" "$API/jobs/$CANCEL_JOB/cancel" >/dev/null && pass "cancel endpoint"
