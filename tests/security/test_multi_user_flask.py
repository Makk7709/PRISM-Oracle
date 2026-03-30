"""
Flask integration tests for multi-user authentication.

Tests the actual HTTP login flow through the Flask app with
multi-user (users.json) and mono-user (fallback) modes.

Spec: docs/SPEC_MULTI_USER_WORKSPACE.md — Rules R1, R2, R10
"""

import json
import os
import pytest
import tempfile
from pathlib import Path
from unittest.mock import patch


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def users_json_dir(tmp_path):
    """Create a temp dir with a valid users.json."""
    from python.security.auth import hash_password

    users_data = {
        "users": {
            "marie": {
                "password_hash": hash_password("MariePass123!"),
                "role": "user",
                "organization": "dica",
                "org_role": "MEMBER",
            },
            "admin": {
                "password_hash": hash_password("AdminPass789!"),
                "role": "admin",
                "organization": "korev-ai",
                "org_role": "OWNER",
            }
        }
    }
    users_file = tmp_path / "users.json"
    users_file.write_text(json.dumps(users_data, indent=2))
    return tmp_path


@pytest.fixture
def shared_dir(tmp_path):
    """Temp directory for workspace."""
    d = tmp_path / "shared"
    d.mkdir()
    return str(d)


@pytest.fixture
def multi_user_app(users_json_dir, shared_dir):
    """Flask app configured for multi-user mode."""
    os.environ["EVIDENCE_USERS_JSON"] = str(users_json_dir / "users.json")
    os.environ["EVIDENCE_SHARED_DIR"] = shared_dir
    # Ensure AUTH_LOGIN is set so login is required
    os.environ["AUTH_LOGIN"] = "admin"
    os.environ["AUTH_PASSWORD"] = "fallback"

    from run_ui import create_app
    app = create_app(testing=True, secret_key="test-secret")

    yield app

    os.environ.pop("EVIDENCE_USERS_JSON", None)
    os.environ.pop("EVIDENCE_SHARED_DIR", None)


@pytest.fixture
def multi_client(multi_user_app):
    """Test client for multi-user app."""
    return multi_user_app.test_client()


# ============================================================================
# T01-Flask — Multi-user login via HTTP
# ============================================================================

class TestMultiUserFlaskLogin:
    """Login through Flask with multi-user users.json."""

    def test_login_page_returns_200(self, multi_client):
        """GET /login → 200."""
        resp = multi_client.get("/login")
        assert resp.status_code == 200

    def test_valid_login_redirects(self, multi_client):
        """POST /login with valid creds → redirect to /."""
        resp = multi_client.post(
            "/login",
            data={"username": "marie", "password": "MariePass123!"},
            follow_redirects=False,
        )
        assert resp.status_code in (301, 302, 303)

    def test_session_contains_username(self, multi_client):
        """After login, session has username."""
        with multi_client.session_transaction() as sess:
            sess.clear()

        multi_client.post(
            "/login",
            data={"username": "marie", "password": "MariePass123!"},
        )

        with multi_client.session_transaction() as sess:
            assert sess.get("username") == "marie"
            assert sess.get("role") == "user"
            assert sess.get("organization") == "dica"
            assert sess.get("org_role") == "MEMBER"

    def test_session_contains_workspace(self, multi_client, shared_dir):
        """After login with EVIDENCE_SHARED_DIR, session has workspace path."""
        multi_client.post(
            "/login",
            data={"username": "marie", "password": "MariePass123!"},
        )

        with multi_client.session_transaction() as sess:
            ws = sess.get("workspace")
            assert ws is not None
            assert "marie" in ws
            assert Path(ws).exists()

    def test_invalid_login_stays_on_login(self, multi_client):
        """POST /login with bad creds → stays on login page."""
        resp = multi_client.post(
            "/login",
            data={"username": "marie", "password": "WrongPass!"},
            follow_redirects=True,
        )
        assert resp.status_code == 200
        assert b"Invalid Credentials" in resp.data or b"login" in resp.data.lower()

    def test_admin_login_gets_admin_role(self, multi_client):
        """Admin login → session role = admin."""
        multi_client.post(
            "/login",
            data={"username": "admin", "password": "AdminPass789!"},
        )

        with multi_client.session_transaction() as sess:
            assert sess.get("role") == "admin"

    def test_logout_clears_session(self, multi_client):
        """After logout, session is cleared."""
        multi_client.post(
            "/login",
            data={"username": "marie", "password": "MariePass123!"},
        )
        multi_client.get("/logout")

        with multi_client.session_transaction() as sess:
            assert "username" not in sess
            assert "role" not in sess
            assert "workspace" not in sess

    def test_protected_route_requires_login(self, multi_client):
        """GET / without login → redirect to /login."""
        resp = multi_client.get("/", follow_redirects=False)
        assert resp.status_code in (301, 302, 303)


# ============================================================================
# T04-Flask — Mono-user fallback via HTTP
# ============================================================================

class TestMonoUserFlaskFallback:
    """Mono-user fallback when no users.json exists."""

    @pytest.fixture
    def mono_app(self, tmp_path):
        """Flask app in mono-user mode (no users.json)."""
        # Point to non-existent users.json
        os.environ["EVIDENCE_USERS_JSON"] = str(tmp_path / "nope.json")
        os.environ.pop("EVIDENCE_SHARED_DIR", None)
        os.environ["AUTH_LOGIN"] = "admin"
        os.environ["AUTH_PASSWORD"] = "MonoPass123!"

        from run_ui import create_app
        app = create_app(testing=True, secret_key="test-secret-mono")

        yield app

        os.environ.pop("EVIDENCE_USERS_JSON", None)

    @pytest.fixture
    def mono_client(self, mono_app):
        return mono_app.test_client()

    def test_mono_user_login_works(self, mono_client):
        """Mono-user login with AUTH_LOGIN/AUTH_PASSWORD."""
        resp = mono_client.post(
            "/login",
            data={"username": "admin", "password": "MonoPass123!"},
            follow_redirects=False,
        )
        assert resp.status_code in (301, 302, 303)

    def test_mono_user_session_has_admin_role(self, mono_client):
        """Mono-user always gets admin role."""
        mono_client.post(
            "/login",
            data={"username": "admin", "password": "MonoPass123!"},
        )
        with mono_client.session_transaction() as sess:
            assert sess.get("username") == "admin"
            assert sess.get("role") == "admin"
