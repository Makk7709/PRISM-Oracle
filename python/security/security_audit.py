from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any


_SECURITY_AUDIT_LOGGER = logging.getLogger("security_audit")
if not _SECURITY_AUDIT_LOGGER.handlers:
    _handler = logging.StreamHandler()
    _handler.setLevel(logging.INFO)
    _SECURITY_AUDIT_LOGGER.addHandler(_handler)
_SECURITY_AUDIT_LOGGER.setLevel(logging.INFO)
_SECURITY_AUDIT_LOGGER.propagate = False


def log_security_event(
    *,
    action: str,
    decision: str,
    user: str | None,
    organization: str | None,
    resource_type: str,
    resource_id: str | None = None,
    reason: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> None:
    """
    Emit a structured security audit event in JSON.

    Never include sensitive chat content in this payload.
    """
    payload: dict[str, Any] = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "action": action,
        "decision": decision,
        "user": user,
        "organization": organization,
        "resource_type": resource_type,
        "resource_id": resource_id,
        "reason": reason,
    }
    if metadata:
        payload["metadata"] = metadata
    _SECURITY_AUDIT_LOGGER.info(json.dumps(payload, ensure_ascii=False))
