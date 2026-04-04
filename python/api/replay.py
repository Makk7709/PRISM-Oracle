"""
API /replay — declenchement de replay et consultation des snapshots.

GET  (action=snapshot) : recupere le snapshot d'une session
POST (action=verify)   : verifie l'integrite d'un snapshot
POST (action=compare)  : compare deux reponses

Acces : auth + role OWNER ou DPO/RSSI/COMPLIANCE_OFFICER.
"""

from __future__ import annotations

from flask import Request, Response

from python.helpers.api import ApiHandler
from python.helpers.replay_engine import (
    compare_responses,
    load_snapshot,
    verify_snapshot_integrity,
)
from python.security.authorization import can_access_audit_reports

try:
    from python.security.security_audit import log_security_event
except Exception:
    def log_security_event(**kwargs):  # type: ignore[misc]
        pass


class Replay(ApiHandler):
    @classmethod
    def requires_auth(cls) -> bool:
        return True

    @classmethod
    def requires_admin(cls) -> bool:
        return False

    @classmethod
    def get_methods(cls) -> list[str]:
        return ["GET", "POST"]

    async def process(self, input: dict, request: Request) -> dict | Response:
        principal = self._principal()
        org, _ = self._session_org_info()

        allowed, reason = can_access_audit_reports(principal, target_org=org)
        if not allowed:
            log_security_event(
                action="replay_access_denied",
                decision="denied",
                user=principal.username,
                organization=principal.organization,
                resource_type="replay_snapshot",
                reason=reason,
            )
            return Response(
                '{"error":"Access denied","reason":"' + reason + '"}',
                status=403,
                mimetype="application/json",
            )

        action = input.get("action", "snapshot")

        if action == "snapshot":
            return self._get_snapshot(input.get("context_id", ""))

        if action == "verify":
            return self._verify_integrity(input.get("context_id", ""))

        if action == "compare":
            return self._compare(
                input.get("original", ""),
                input.get("replayed", ""),
            )

        return {
            "error": "Unknown action",
            "valid_actions": ["snapshot", "verify", "compare"],
        }

    def _get_snapshot(self, context_id: str) -> dict | Response:
        if not context_id:
            return Response(
                '{"error":"context_id required"}',
                status=400,
                mimetype="application/json",
            )

        snap = load_snapshot(context_id)
        if snap is None:
            return Response(
                '{"error":"Snapshot not found"}',
                status=404,
                mimetype="application/json",
            )

        return {"ok": True, "snapshot": snap.to_dict()}

    def _verify_integrity(self, context_id: str) -> dict | Response:
        if not context_id:
            return Response(
                '{"error":"context_id required"}',
                status=400,
                mimetype="application/json",
            )

        snap = load_snapshot(context_id)
        if snap is None:
            return Response(
                '{"error":"Snapshot not found"}',
                status=404,
                mimetype="application/json",
            )

        valid = verify_snapshot_integrity(snap)

        log_security_event(
            action="replay_integrity_check",
            decision="valid" if valid else "tampered",
            user=None,
            organization=None,
            resource_type="replay_snapshot",
            resource_id=context_id,
            reason=f"integrity={'PASS' if valid else 'FAIL'}",
        )

        return {
            "ok": True,
            "context_id": context_id,
            "integrity_valid": valid,
            "stored_hash": snap.integrity_hash,
            "computed_hash": snap.compute_integrity(),
        }

    def _compare(self, original: str, replayed: str) -> dict | Response:
        if not original or not replayed:
            return Response(
                '{"error":"original and replayed fields required"}',
                status=400,
                mimetype="application/json",
            )

        report = compare_responses(original, replayed)
        return {"ok": True, "divergence": report.to_dict()}
