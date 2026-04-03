"""
SESSION 10 — Endpoint /audit_reports (OWNER + DPO/RSSI).

GET : liste les rapports d'audit disponibles pour l'organisation.
POST (action=download) : telecharge un rapport specifique (MD ou PDF).

Acces : auth + verification OWNER ou role de conformite (via can_access_audit_reports).
"""

from __future__ import annotations

import os
from flask import Request, Response, send_file

from python.helpers.api import ApiHandler
from python.helpers.audit_report_storage import AUDIT_REPORT_MD, AUDIT_REPORT_PDF
from python.security.authorization import can_access_audit_reports

try:
    from python.security.security_audit import log_security_event
except Exception:
    def log_security_event(**kwargs):
        pass


class AuditReports(ApiHandler):
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
                action="audit_reports_access_denied",
                decision="denied",
                user=principal.username,
                organization=principal.organization,
                resource_type="audit_report",
                reason=reason,
            )
            return Response(
                '{"error":"Access denied","reason":"' + reason + '"}',
                status=403,
                mimetype="application/json",
            )

        action = input.get("action", "list")

        if action == "list":
            return self._list_reports()

        if action == "download":
            context_id = input.get("context_id", "")
            fmt = input.get("format", "md")
            return self._download_report(context_id, fmt)

        return {"error": "Unknown action", "valid_actions": ["list", "download"]}

    def _list_reports(self) -> dict:
        """List all available audit reports."""
        chats_dir = os.path.join("tmp", "chats")
        if not os.path.isdir(chats_dir):
            return {"ok": True, "reports": []}

        reports = []
        for entry in sorted(os.listdir(chats_dir)):
            folder = os.path.join(chats_dir, entry)
            if not os.path.isdir(folder):
                continue

            md_path = os.path.join(folder, AUDIT_REPORT_MD)
            if not os.path.isfile(md_path):
                continue

            stat = os.stat(md_path)
            has_pdf = os.path.isfile(os.path.join(folder, AUDIT_REPORT_PDF))

            reports.append({
                "context_id": entry,
                "size_bytes": stat.st_size,
                "modified_at": stat.st_mtime,
                "has_pdf": has_pdf,
            })

        return {"ok": True, "reports": reports, "total": len(reports)}

    def _download_report(self, context_id: str, fmt: str) -> Response:
        """Download a specific audit report."""
        if not context_id:
            return Response('{"error":"context_id required"}', status=400,
                            mimetype="application/json")

        if os.sep in context_id or "/" in context_id or ".." in context_id:
            return Response('{"error":"Invalid context_id"}', status=400,
                            mimetype="application/json")

        chats_dir = os.path.join("tmp", "chats")
        folder = os.path.join(chats_dir, context_id)

        if fmt == "pdf":
            path = os.path.join(folder, AUDIT_REPORT_PDF)
            mimetype = "application/pdf"
            filename = f"audit_report_{context_id}.pdf"
        else:
            path = os.path.join(folder, AUDIT_REPORT_MD)
            mimetype = "text/markdown"
            filename = f"audit_report_{context_id}.md"

        if not os.path.isfile(path):
            return Response('{"error":"Report not found"}', status=404,
                            mimetype="application/json")

        return send_file(
            path,
            mimetype=mimetype,
            as_attachment=True,
            download_name=filename,
        )
