#!/usr/bin/env bash
set -euo pipefail

echo "=== tailscale status ==="
tailscale status --json | jq '{Self: .Self.DNSName, Online: .Self.Online}'

echo "=== tailscale serve status ==="
tailscale serve status || true

echo "=== tailscale funnel status ==="
tailscale funnel status || true
