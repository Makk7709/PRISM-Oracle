#!/usr/bin/env bash
set -euo pipefail

echo "[post-deploy] Running multi-user scheduler/notification smoke test..."
python3 scripts/smoke_test_multi_user.py "$@"
echo "[post-deploy] Smoke test passed."
