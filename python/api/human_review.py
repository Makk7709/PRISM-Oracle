"""
API /human_review — gestion des reviews humains bloquants.

GET  : liste les reviews en attente (filtre par org)
POST : soumet une decision (APPROVED / REJECTED)

Acces : auth + role OWNER ou DPO/RSSI/COMPLIANCE_OFFICER.
"""

from __future__ import annotations

from flask import Request, Response

from python.helpers.api import ApiHandler
from python.helpers.human_review import (
    ReviewStatus,
    create_review,
    list_pending_reviews,
    load_review,
    submit_review,
)
from python.security.authorization import can_access_audit_reports

try:
    from python.security.security_audit import log_security_event
except Exception:
    def log_security_event(**kwargs):  # type: ignore[misc]
        pass


class HumanReview(ApiHandler):
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
                action="human_review_access_denied",
                decision="denied",
                user=principal.username,
                organization=principal.organization,
                resource_type="human_review",
                reason=reason,
            )
            return Response(
                '{"error":"Access denied","reason":"' + reason + '"}',
                status=403,
                mimetype="application/json",
            )

        action = input.get("action", "list")

        if action == "list":
            return self._list_pending(org)

        if action == "get":
            return self._get_review(input.get("review_id", ""))

        if action == "decide":
            return self._decide(input, principal.username or "unknown")

        return {"error": "Unknown action", "valid_actions": ["list", "get", "decide"]}

    def _list_pending(self, org: str | None) -> dict:
        reviews = list_pending_reviews(organization=org)
        return {
            "ok": True,
            "reviews": [r.to_dict() for r in reviews],
            "total": len(reviews),
        }

    def _get_review(self, review_id: str) -> dict | Response:
        if not review_id:
            return Response(
                '{"error":"review_id required"}',
                status=400,
                mimetype="application/json",
            )
        rev = load_review(review_id)
        if rev is None:
            return Response(
                '{"error":"Review not found"}',
                status=404,
                mimetype="application/json",
            )
        return {"ok": True, "review": rev.to_dict()}

    def _decide(self, input: dict, username: str) -> dict | Response:
        review_id = input.get("review_id", "")
        status_str = input.get("status", "")
        justification = input.get("justification", "")

        if not review_id:
            return Response(
                '{"error":"review_id required"}',
                status=400,
                mimetype="application/json",
            )

        if status_str not in ("APPROVED", "REJECTED"):
            return Response(
                '{"error":"status must be APPROVED or REJECTED"}',
                status=400,
                mimetype="application/json",
            )

        if not justification:
            return Response(
                '{"error":"justification required for audit trail"}',
                status=400,
                mimetype="application/json",
            )

        try:
            status = ReviewStatus(status_str)
            rev = submit_review(
                review_id,
                reviewer_id=username,
                reviewer_name=input.get("reviewer_name", username),
                status=status,
                justification=justification,
                override_response=input.get("override_response", ""),
            )
            return {"ok": True, "review": rev.to_dict()}
        except ValueError as e:
            return Response(
                f'{{"error":"{str(e)}"}}',
                status=404,
                mimetype="application/json",
            )
