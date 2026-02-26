"""
E2E Tests T17-T20: Multi-user workspace end-to-end.

These tests simulate complete user scenarios:
- T17: Docker volume structure validation (mocked)
- T18: Two simultaneous users with isolated workspaces
- T19: User uploads file → Evidence reads it → generates report
- T20: Retro-compatibility: mono-user mode works unchanged

Spec: docs/SPEC_MULTI_USER_WORKSPACE.md
"""

import json
import os
import pytest
import tempfile
from pathlib import Path


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def e2e_shared_root(tmp_path):
    """Create a full shared root structure for E2E testing."""
    root = tmp_path / "shared"
    root.mkdir()
    return root


@pytest.fixture
def e2e_users_json(tmp_path):
    """Create users.json for E2E tests."""
    from python.security.auth import hash_password

    users_data = {
        "users": {
            "marie": {
                "password_hash": hash_password("MarieE2E!"),
                "role": "user"
            },
            "jean": {
                "password_hash": hash_password("JeanE2E!"),
                "role": "user"
            },
            "admin": {
                "password_hash": hash_password("AdminE2E!"),
                "role": "admin"
            }
        }
    }
    users_file = tmp_path / "users.json"
    users_file.write_text(json.dumps(users_data, indent=2))
    return str(users_file)


@pytest.fixture
def e2e_app(e2e_users_json, e2e_shared_root):
    """Flask app fully configured for E2E testing."""
    os.environ["EVIDENCE_USERS_JSON"] = e2e_users_json
    os.environ["EVIDENCE_SHARED_DIR"] = str(e2e_shared_root)
    os.environ["AUTH_LOGIN"] = "admin"
    os.environ["AUTH_PASSWORD"] = "fallback"

    from run_ui import create_app
    app = create_app(testing=True, secret_key="e2e-secret")

    yield app

    os.environ.pop("EVIDENCE_USERS_JSON", None)
    os.environ.pop("EVIDENCE_SHARED_DIR", None)


@pytest.fixture
def e2e_client(e2e_app):
    return e2e_app.test_client()


def _login(client, username, password):
    """Helper to login a user."""
    return client.post(
        "/login",
        data={"username": username, "password": password},
        follow_redirects=False,
    )


# ============================================================================
# T17 — Docker volume structure validation
# Rule: R9
# ============================================================================

@pytest.mark.e2e
class TestT17_DockerVolume:
    """T17: Shared directory has correct structure after multi-user usage."""

    def test_shared_root_structure_after_logins(
        self, e2e_app, e2e_shared_root
    ):
        """After multiple users login, the shared root has correct structure."""
        client1 = e2e_app.test_client()
        client2 = e2e_app.test_client()

        _login(client1, "marie", "MarieE2E!")
        _login(client2, "jean", "JeanE2E!")

        root = e2e_shared_root

        # Top-level structure
        assert (root / "users").is_dir()
        assert (root / "commun").is_dir()
        assert (root / "audit").is_dir()

        # Per-user structure
        for user in ["marie", "jean"]:
            user_dir = root / "users" / user
            assert user_dir.is_dir()
            assert (user_dir / "documents").is_dir()
            assert (user_dir / "rapports").is_dir()
            assert (user_dir / "tmp").is_dir()

    def test_audit_directory_exists(self, e2e_app, e2e_shared_root):
        """Audit directory is created during app initialization."""
        # The WorkspaceManager creates audit/ on init
        assert (e2e_shared_root / "audit").is_dir()


# ============================================================================
# T18 — Two simultaneous users, isolated workspaces
# Rules: R3, R4
# ============================================================================

@pytest.mark.e2e
class TestT18_SimultaneousUsers:
    """T18: Two users logged in simultaneously have isolated workspaces."""

    def test_two_users_different_sessions(self, e2e_app):
        """Marie and Jean get different session data."""
        client_marie = e2e_app.test_client()
        client_jean = e2e_app.test_client()

        _login(client_marie, "marie", "MarieE2E!")
        _login(client_jean, "jean", "JeanE2E!")

        with client_marie.session_transaction() as s:
            assert s["username"] == "marie"
            marie_ws = s["workspace"]

        with client_jean.session_transaction() as s:
            assert s["username"] == "jean"
            jean_ws = s["workspace"]

        assert marie_ws != jean_ws
        assert "marie" in marie_ws
        assert "jean" in jean_ws

    def test_marie_file_invisible_to_jean(self, e2e_app, e2e_shared_root):
        """A file in Marie's workspace is NOT accessible to Jean."""
        from python.helpers.user_workspace import WorkspaceManager

        ws_mgr = e2e_app.config["WORKSPACE_MANAGER"]

        # Marie creates a file
        marie_ws = ws_mgr.ensure_workspace("marie")
        secret_file = Path(marie_ws) / "documents" / "secret_client.txt"
        ws_mgr.write_file("marie", str(secret_file), "Confidentiel Marie")

        # Jean tries to read it
        with pytest.raises(PermissionError):
            ws_mgr.read_file("jean", str(secret_file))

    def test_both_users_share_commun(self, e2e_app, e2e_shared_root):
        """Both users can read/write in commun/."""
        ws_mgr = e2e_app.config["WORKSPACE_MANAGER"]

        # Marie writes
        commun_file = e2e_shared_root / "commun" / "shared_template.txt"
        ws_mgr.write_file("marie", str(commun_file), "Template partagé")

        # Jean reads
        content = ws_mgr.read_file("jean", str(commun_file))
        assert content == "Template partagé"

    def test_cross_user_write_rejected(self, e2e_app, e2e_shared_root):
        """Jean cannot write into Marie's workspace."""
        ws_mgr = e2e_app.config["WORKSPACE_MANAGER"]

        marie_ws = ws_mgr.ensure_workspace("marie")
        target = Path(marie_ws) / "documents" / "injected_by_jean.txt"

        with pytest.raises(PermissionError):
            ws_mgr.write_file("jean", str(target), "Tentative d'injection")


# ============================================================================
# T19 — User uploads file → Evidence reads → generates report
# Rules: R3, R5
# ============================================================================

@pytest.mark.e2e
class TestT19_FileWorkflow:
    """T19: Complete file workflow: upload → read → report generation."""

    def test_full_workflow(self, e2e_app, e2e_shared_root):
        """Simulate a complete Evidence workflow for a user."""
        ws_mgr = e2e_app.config["WORKSPACE_MANAGER"]

        # 1. User uploads a document
        marie_ws = ws_mgr.ensure_workspace("marie")
        doc_path = Path(marie_ws) / "documents" / "contrat_client.txt"
        ws_mgr.write_file(
            "marie",
            str(doc_path),
            "Contrat de service - Client ABC Corp\n"
            "Date: 2026-02-08\n"
            "Montant: 150 000 EUR\n"
        )

        # 2. Evidence reads the document
        content = ws_mgr.read_file("marie", str(doc_path))
        assert "ABC Corp" in content

        # 3. Evidence generates a report in rapports/
        output_dir = ws_mgr.get_output_dir("marie")
        report_path = Path(output_dir) / "analyse_contrat.txt"
        ws_mgr.write_file(
            "marie",
            str(report_path),
            "RAPPORT D'ANALYSE\n"
            "Client: ABC Corp\n"
            "Risque: Faible\n"
            "Recommandation: Accepter\n"
        )

        # 4. Verify report exists in the right place
        assert report_path.exists()
        assert "rapports" in str(report_path)

        # 5. Verify audit trail
        audit_file = e2e_shared_root / "audit" / "file_operations.jsonl"
        assert audit_file.exists()
        lines = audit_file.read_text().strip().split("\n")
        assert len(lines) >= 3  # write + read + write

        # All audit entries are for marie
        for line in lines:
            entry = json.loads(line)
            assert entry["username"] == "marie"

    def test_report_output_dir_correct(self, e2e_app):
        """get_output_dir points to rapports/ subdirectory."""
        ws_mgr = e2e_app.config["WORKSPACE_MANAGER"]

        output_dir = ws_mgr.get_output_dir("marie")
        assert output_dir.endswith("/rapports")
        assert Path(output_dir).exists()


# ============================================================================
# T20 — Retro-compatibility: mono-user preserved
# Rule: R10
# ============================================================================

@pytest.mark.e2e
class TestT20_RetroCompatibility:
    """T20: Mono-user mode works exactly as before."""

    @pytest.fixture
    def mono_app(self, tmp_path):
        """App in mono-user mode (no users.json, no shared dir)."""
        os.environ["EVIDENCE_USERS_JSON"] = str(tmp_path / "nonexistent.json")
        os.environ.pop("EVIDENCE_SHARED_DIR", None)
        os.environ["AUTH_LOGIN"] = "admin"
        os.environ["AUTH_PASSWORD"] = "MonoPass123!"

        from run_ui import create_app
        app = create_app(testing=True, secret_key="mono-e2e")

        yield app

        os.environ.pop("EVIDENCE_USERS_JSON", None)

    @pytest.fixture
    def mono_client(self, mono_app):
        return mono_app.test_client()

    def test_mono_login_works(self, mono_client):
        """Mono-user login still works."""
        resp = _login(mono_client, "admin", "MonoPass123!")
        assert resp.status_code in (301, 302, 303)

    def test_mono_session_has_username(self, mono_client):
        """Mono-user session has username=admin, role=admin."""
        _login(mono_client, "admin", "MonoPass123!")

        with mono_client.session_transaction() as s:
            assert s["username"] == "admin"
            assert s["role"] == "admin"

    def test_mono_no_workspace(self, mono_client):
        """Mono-user mode has no workspace (EVIDENCE_SHARED_DIR not set)."""
        _login(mono_client, "admin", "MonoPass123!")

        with mono_client.session_transaction() as s:
            assert s.get("workspace") is None

    def test_healthz_still_works(self, mono_client):
        """/healthz endpoint works in mono-user mode."""
        resp = mono_client.get("/healthz")
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert data["status"] == "ok"

    def test_protected_routes_still_redirect(self, mono_app):
        """Without login, protected routes redirect to /login."""
        client = mono_app.test_client()
        resp = client.get("/", follow_redirects=False)
        assert resp.status_code in (301, 302, 303)
