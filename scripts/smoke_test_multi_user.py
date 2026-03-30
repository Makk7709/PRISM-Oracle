#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import sys
import time
import uuid
from concurrent.futures import ThreadPoolExecutor

import requests


def _login(base_url: str, username: str, password: str) -> tuple[requests.Session, str]:
    s = requests.Session()
    s.get(f"{base_url}/login", timeout=20)
    r = s.post(
        f"{base_url}/login",
        data={"username": username, "password": password},
        allow_redirects=False,
        timeout=20,
    )
    if r.status_code not in (301, 302, 303):
        raise RuntimeError(f"login failed for {username}: status={r.status_code}")
    csrf = s.get(f"{base_url}/csrf_token", timeout=20).json().get("token")
    if not csrf:
        raise RuntimeError(f"csrf token missing for {username}")
    return s, csrf


def run_smoke(base_url: str, user_a: str, pass_a: str, user_b: str, pass_b: str) -> dict[str, object]:
    report: dict[str, object] = {"checks": [], "ok": True}
    s_a, csrf_a = _login(base_url, user_a, pass_a)
    s_b, csrf_b = _login(base_url, user_b, pass_b)

    task_name = f"smoke_task_{uuid.uuid4().hex[:8]}"
    create = s_a.post(
        f"{base_url}/scheduler_task_create",
        json={
            "name": task_name,
            "system_prompt": "You are concise.",
            "prompt": "Reply exactly: SMOKE_OK",
        },
        headers={"X-CSRF-Token": csrf_a},
        timeout=25,
    ).json()
    task = (create.get("task") or {}) if isinstance(create, dict) else {}
    task_uuid = task.get("uuid")
    if not create.get("ok") or not task_uuid:
        raise RuntimeError(f"task create failed: {create}")

    run_resp = s_a.post(
        f"{base_url}/scheduler_task_run",
        json={"task_id": task_uuid},
        headers={"X-CSRF-Token": csrf_a},
        timeout=25,
    ).json()
    if not run_resp.get("success"):
        raise RuntimeError(f"task run failed: {run_resp}")

    notif_group = f"task-{task_uuid}"
    found_a = []
    found_b = []
    for _ in range(10):
        time.sleep(3)
        h_a = s_a.post(
            f"{base_url}/notifications_history",
            json={},
            headers={"X-CSRF-Token": csrf_a},
            timeout=25,
        ).json().get("notifications", [])
        h_b = s_b.post(
            f"{base_url}/notifications_history",
            json={},
            headers={"X-CSRF-Token": csrf_b},
            timeout=25,
        ).json().get("notifications", [])
        found_a = [n for n in h_a if n.get("group") == notif_group]
        found_b = [n for n in h_b if n.get("group") == notif_group]
        if found_a:
            break

    if not found_a:
        raise RuntimeError("no scheduler notification for user A")
    if found_b:
        raise RuntimeError("cross-tenant notification leak detected")

    notif_id = found_a[0].get("id")
    mark_cross = s_b.post(
        f"{base_url}/notifications_mark_read",
        json={"notification_ids": [notif_id]},
        headers={"X-CSRF-Token": csrf_b},
        timeout=25,
    ).json()
    mark_owner = s_a.post(
        f"{base_url}/notifications_mark_read",
        json={"notification_ids": [notif_id]},
        headers={"X-CSRF-Token": csrf_a},
        timeout=25,
    ).json()

    if int(mark_cross.get("marked_count", 0)) != 0:
        raise RuntimeError(f"cross-user mark-read should be denied: {mark_cross}")
    if int(mark_owner.get("marked_count", 0)) <= 0:
        raise RuntimeError(f"owner mark-read expected >0: {mark_owner}")

    # Concurrency scenario: two run requests on same task -> one winner
    cc_name = f"smoke_claim_task_{uuid.uuid4().hex[:8]}"
    cc_create = s_a.post(
        f"{base_url}/scheduler_task_create",
        json={
            "name": cc_name,
            "system_prompt": "You are concise.",
            "prompt": "Reply exactly: CLAIM_SMOKE_OK",
        },
        headers={"X-CSRF-Token": csrf_a},
        timeout=25,
    ).json()
    cc_task_uuid = (cc_create.get("task") or {}).get("uuid")
    if not cc_create.get("ok") or not cc_task_uuid:
        raise RuntimeError(f"concurrency task create failed: {cc_create}")

    def _run_once() -> dict:
        return s_a.post(
            f"{base_url}/scheduler_task_run",
            json={"task_id": cc_task_uuid},
            headers={"X-CSRF-Token": csrf_a},
            timeout=25,
        ).json()

    with ThreadPoolExecutor(max_workers=2) as ex:
        run_results = list(ex.map(lambda _: _run_once(), [0, 1]))
    success_count = sum(1 for r in run_results if r.get("success"))
    if success_count < 1:
        raise RuntimeError(f"concurrency run: no started run, run_results={run_results}")
    cc_group = f"task-{cc_task_uuid}"
    cc_notifs = []
    for _ in range(12):
        time.sleep(2)
        h_a_cc = s_a.post(
            f"{base_url}/notifications_history",
            json={},
            headers={"X-CSRF-Token": csrf_a},
            timeout=25,
        ).json().get("notifications", [])
        cc_notifs = [n for n in h_a_cc if n.get("group") == cc_group]
        if cc_notifs:
            break
    if len(cc_notifs) > 1:
        raise RuntimeError(f"duplicate completion notifications detected: count={len(cc_notifs)}")

    # cleanup
    s_a.post(
        f"{base_url}/scheduler_task_delete",
        json={"task_id": task_uuid},
        headers={"X-CSRF-Token": csrf_a},
        timeout=25,
    )
    s_a.post(
        f"{base_url}/scheduler_task_delete",
        json={"task_id": cc_task_uuid},
        headers={"X-CSRF-Token": csrf_a},
        timeout=25,
    )

    report["checks"] = [
        {"name": "task_create", "ok": True, "task_uuid": task_uuid},
        {"name": "notification_scope", "ok": True, "owner_count": len(found_a), "other_count": len(found_b)},
        {"name": "cross_mark_read_denied", "ok": True, "response": mark_cross},
        {
            "name": "claim_concurrency",
            "ok": True,
            "details": {
                "success_count": success_count,
                "run_results": run_results,
                "completion_notification_count": len(cc_notifs),
            },
        },
    ]
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default=os.environ.get("EVIDENCE_BASE_URL", "https://www.korev-evidence.com"))
    parser.add_argument("--user-a", default=os.environ.get("SMOKE_USER_A", ""))
    parser.add_argument("--pass-a", default=os.environ.get("SMOKE_PASS_A", ""))
    parser.add_argument("--user-b", default=os.environ.get("SMOKE_USER_B", ""))
    parser.add_argument("--pass-b", default=os.environ.get("SMOKE_PASS_B", ""))
    args = parser.parse_args()
    if not (args.user_a and args.pass_a and args.user_b and args.pass_b):
        print(
            json.dumps(
                {
                    "verdict": "SMOKE TEST FAILED",
                    "error": "Missing credentials. Provide --user-a/--pass-a/--user-b/--pass-b or env SMOKE_USER_*/SMOKE_PASS_*.",
                },
                indent=2,
                ensure_ascii=False,
            )
        )
        return 1

    try:
        report = run_smoke(args.base_url.rstrip("/"), args.user_a, args.pass_a, args.user_b, args.pass_b)
        print(json.dumps({"verdict": "SMOKE TEST PASSED", "report": report}, indent=2, ensure_ascii=False))
        return 0
    except Exception as exc:
        print(json.dumps({"verdict": "SMOKE TEST FAILED", "error": str(exc)}, indent=2, ensure_ascii=False))
        return 1


if __name__ == "__main__":
    sys.exit(main())
