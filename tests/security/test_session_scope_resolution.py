import json
import os
import threading
from types import SimpleNamespace

from flask import session

from python.api.notification_create import NotificationCreate
from python.helpers.api import ApiHandler
from python.security.auth import hash_password


class _DummyHandler(ApiHandler):
    async def process(self, input, request):
        return {}


def _build_app(tmp_path):
    users = {
        "users": {
            "jeremie": {
                "password_hash": hash_password("JeremiePass123!"),
                "role": "user",
                "organization": "dica",
                "org_role": "MEMBER",
            },
            "legacy-no-org": {
                "password_hash": hash_password("Legacy123!"),
                "role": "user",
            },
        }
    }
    users_file = tmp_path / "users.json"
    users_file.write_text(json.dumps(users), encoding="utf-8")

    shared = tmp_path / "shared"
    shared.mkdir()

    os.environ["EVIDENCE_USERS_JSON"] = str(users_file)
    os.environ["EVIDENCE_SHARED_DIR"] = str(shared)
    os.environ["AUTH_LOGIN"] = "admin"
    os.environ["AUTH_PASSWORD"] = "fallback"
    try:
        from run_ui import create_app

        return create_app(testing=True, secret_key="scope-test")
    finally:
        os.environ.pop("EVIDENCE_USERS_JSON", None)
        os.environ.pop("EVIDENCE_SHARED_DIR", None)


def test_resolve_session_scope_hydrates_org_and_workspace(tmp_path):
    app = _build_app(tmp_path)
    handler = _DummyHandler(app, threading.Lock())

    with app.test_request_context("/x", method="POST"):
        session["authentication"] = "ok"
        session["username"] = "jeremie"
        session["role"] = "user"
        scope = handler._resolve_session_scope()

    assert scope["organization"] == "dica"
    assert scope["org_role"] == "MEMBER"
    assert isinstance(scope["workspace"], str)
    assert "jeremie" in scope["workspace"]


def test_notification_create_denied_for_user_without_organization(tmp_path):
    app = _build_app(tmp_path)
    handler = NotificationCreate(app, threading.Lock())

    with app.test_request_context("/notification_create", method="POST"):
        session["authentication"] = "ok"
        session["username"] = "legacy-no-org"
        session["role"] = "user"
        # No organization in session, and none in user manager.
        result = __import__("asyncio").run(
            handler.process(
                {"type": "info", "message": "test"},
                SimpleNamespace(),
            )
        )

    assert result["success"] is False
    assert "Missing notification scope" in result["error"]
