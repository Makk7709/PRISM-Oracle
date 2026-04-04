"""
API /risk_dashboard — consultation du registre de risque dynamique.

GET  : retourne le dashboard systeme agrege
POST (action=assess) : declenche une evaluation de risque manuelle

Acces : auth + role admin ou OWNER/DPO/RSSI/COMPLIANCE_OFFICER.
"""

from __future__ import annotations

from flask import Request, Response

from python.helpers.api import ApiHandler
from python.helpers.dynamic_risk_register import (
    assess_session_risk,
    get_system_dashboard,
)
from python.security.authorization import can_access_audit_reports

try:
    from python.security.security_audit import log_security_event
except Exception:
    def log_security_event(**kwargs):  # type: ignore[misc]
        pass


class RiskDashboard(ApiHandler):
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
                action="risk_dashboard_access_denied",
                decision="denied",
                user=principal.username,
                organization=principal.organization,
                resource_type="risk_dashboard",
                reason=reason,
            )
            return Response(
                '{"error":"Access denied","reason":"' + reason + '"}',
                status=403,
                mimetype="application/json",
            )

        action = input.get("action", "dashboard")

        if action == "dashboard":
            limit = int(input.get("limit", 50))
            dashboard = get_system_dashboard(limit=limit)
            return {"ok": True, "dashboard": dashboard.to_dict()}

        if action == "assess":
            return self._manual_assess(input)

        return {
            "error": "Unknown action",
            "valid_actions": ["dashboard", "assess"],
        }

    def _manual_assess(self, input: dict) -> dict | Response:
        context_id = input.get("context_id", "")
        if not context_id:
            return Response(
                '{"error":"context_id required"}',
                status=400,
                mimetype="application/json",
            )

        assessment = assess_session_risk(
            context_id=context_id,
            session_id=input.get("session_id", ""),
            consensus_achieved=input.get("consensus_achieved", True),
            consensus_rounds=int(input.get("consensus_rounds", 0)),
            confidence_score=input.get("confidence_score"),
            error_count=int(input.get("error_count", 0)),
            timeout_count=int(input.get("timeout_count", 0)),
            delegation_depth=int(input.get("delegation_depth", 0)),
            tool_call_count=int(input.get("tool_call_count", 0)),
            execution_time_ms=int(input.get("execution_time_ms", 0)),
        )

        return {"ok": True, "assessment": assessment.to_dict()}
