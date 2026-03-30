#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import sys

import requests


def _login(base_url: str, username: str, password: str):
    s = requests.Session()
    s.get(f"{base_url}/login", timeout=20)
    r = s.post(
        f"{base_url}/login",
        data={"username": username, "password": password},
        allow_redirects=False,
        timeout=20,
    )
    if r.status_code not in (301, 302, 303):
        raise RuntimeError("admin login failed")
    csrf = s.get(f"{base_url}/csrf_token", timeout=20).json().get("token")
    return s, csrf


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default=os.environ.get("EVIDENCE_BASE_URL", "https://www.korev-evidence.com"))
    parser.add_argument("--admin-user", default=os.environ.get("SMOKE_USER_A", ""))
    parser.add_argument("--admin-pass", default=os.environ.get("SMOKE_PASS_A", ""))
    parser.add_argument("--max-cross-tenant-denied", type=int, default=50)
    parser.add_argument("--max-claim-conflict-rate", type=float, default=0.30)
    parser.add_argument("--max-task-fail-rate", type=float, default=0.25)
    parser.add_argument("--max-notification-read-gap", type=int, default=200)
    args = parser.parse_args()
    if not args.admin_user or not args.admin_pass:
        print(
            json.dumps(
                {
                    "verdict": "ALERT",
                    "alerts": ["missing admin credentials for observability check"],
                },
                indent=2,
                ensure_ascii=False,
            )
        )
        return 2

    s, csrf = _login(args.base_url.rstrip("/"), args.admin_user, args.admin_pass)
    metrics = s.post(
        f"{args.base_url.rstrip('/')}/observability_metrics",
        json={},
        headers={"X-CSRF-Token": csrf},
        timeout=20,
    )
    try:
        payload = metrics.json()
    except Exception:
        print(
            json.dumps(
                {
                    "verdict": "ALERT",
                    "alerts": ["observability_metrics endpoint returned non-JSON response"],
                    "status_code": metrics.status_code,
                    "body_prefix": metrics.text[:200],
                },
                indent=2,
                ensure_ascii=False,
            )
        )
        return 2
    metrics = payload.get("metrics", {})

    alerts = []
    if int(metrics.get("cross_tenant_denied_total", 0)) > args.max_cross_tenant_denied:
        alerts.append("cross_tenant_denied_total above threshold")
    if float(metrics.get("claim_conflict_rate", 0.0)) > args.max_claim_conflict_rate:
        alerts.append("claim_conflict_rate above threshold")
    if float(metrics.get("task_fail_rate", 0.0)) > args.max_task_fail_rate:
        alerts.append("task_fail_rate above threshold")
    if int(metrics.get("notification_read_gap", 0)) > args.max_notification_read_gap:
        alerts.append("notification_read_gap above threshold")

    payload = {"alerts": alerts, "metrics": metrics}
    if alerts:
        print(json.dumps({"verdict": "ALERT", **payload}, indent=2, ensure_ascii=False))
        return 2
    print(json.dumps({"verdict": "OK", **payload}, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
