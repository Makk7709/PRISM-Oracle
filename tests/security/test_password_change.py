"""
Tests du changement de mot de passe (testeurs multi-user).

Architecture testée :
- UserManager.change_password() : vérification ancien mot de passe (timing-safe),
  politique de robustesse, hash Argon2id, écriture atomique d'un fichier overlay.
- Overlay users.local.json : users.json est monté read-only en production
  (docker-compose `:ro`), les nouveaux hashes vivent dans un fichier overlay
  sur volume writable. L'overlay ne peut surcharger QUE password_hash
  (jamais role/organization — pas d'escalade de privilèges possible).
- Route Flask POST /change_password : session + CSRF + rate-limit.
"""

import json
import os
import stat

import pytest

from python.security.auth import hash_password, verify_password


# ============================================================================
# Fixtures
# ============================================================================

MARIE_PASSWORD = "MariePass123!"
NEW_PASSWORD = "NouveauPass2026!"


@pytest.fixture
def users_setup(tmp_path):
    """users.json (lecture seule logique) + chemin overlay writable."""
    users_data = {
        "users": {
            "marie": {
                "password_hash": hash_password(MARIE_PASSWORD),
                "role": "user",
                "organization": "dica",
                "org_role": "MEMBER",
            },
            "admin": {
                "password_hash": hash_password("AdminPass789!"),
                "role": "admin",
                "organization": "korev-ai",
                "org_role": "OWNER",
            },
        }
    }
    users_file = tmp_path / "users.json"
    users_file.write_text(json.dumps(users_data, indent=2), encoding="utf-8")
    overlay_file = tmp_path / "users.local.json"
    return users_file, overlay_file


@pytest.fixture
def manager(users_setup):
    from python.helpers.user_manager import UserManager

    users_file, overlay_file = users_setup
    return UserManager(str(users_file), strict=True, overlay_path=str(overlay_file))


# ============================================================================
# T1 — UserManager.change_password
# ============================================================================

class TestChangePassword:
    def test_success_returns_ok(self, manager):
        ok, msg = manager.change_password("marie", MARIE_PASSWORD, NEW_PASSWORD)
        assert ok is True, msg

    def test_new_password_authenticates(self, manager):
        manager.change_password("marie", MARIE_PASSWORD, NEW_PASSWORD)
        assert manager.authenticate("marie", NEW_PASSWORD) is not None

    def test_old_password_rejected_after_change(self, manager):
        manager.change_password("marie", MARIE_PASSWORD, NEW_PASSWORD)
        assert manager.authenticate("marie", MARIE_PASSWORD) is None

    def test_wrong_current_password_rejected(self, manager, users_setup):
        _, overlay_file = users_setup
        ok, msg = manager.change_password("marie", "MauvaisPass999!", NEW_PASSWORD)
        assert ok is False
        assert not overlay_file.exists()
        # L'ancien mot de passe reste valide
        assert manager.authenticate("marie", MARIE_PASSWORD) is not None

    def test_unknown_user_rejected(self, manager):
        ok, _ = manager.change_password("inconnu", "x" * 16 + "1a", NEW_PASSWORD)
        assert ok is False

    def test_short_password_rejected(self, manager):
        ok, msg = manager.change_password("marie", MARIE_PASSWORD, "Court1!")
        assert ok is False
        assert "12" in msg

    def test_password_without_digit_rejected(self, manager):
        ok, _ = manager.change_password("marie", MARIE_PASSWORD, "QueDesLettresIci!")
        assert ok is False

    def test_password_without_letter_rejected(self, manager):
        ok, _ = manager.change_password("marie", MARIE_PASSWORD, "1234567890123!")
        assert ok is False

    def test_same_password_rejected(self, manager):
        ok, _ = manager.change_password("marie", MARIE_PASSWORD, MARIE_PASSWORD)
        assert ok is False

    def test_other_users_unaffected(self, manager):
        manager.change_password("marie", MARIE_PASSWORD, NEW_PASSWORD)
        assert manager.authenticate("admin", "AdminPass789!") is not None


# ============================================================================
# T2 — Persistance overlay
# ============================================================================

class TestOverlayPersistence:
    def test_overlay_file_created_with_argon2_hash(self, manager, users_setup):
        _, overlay_file = users_setup
        manager.change_password("marie", MARIE_PASSWORD, NEW_PASSWORD)
        assert overlay_file.exists()
        data = json.loads(overlay_file.read_text(encoding="utf-8"))
        stored = data["password_overrides"]["marie"]
        assert stored.startswith("$argon2")
        assert verify_password(stored, NEW_PASSWORD)

    def test_overlay_file_permissions_0600(self, manager, users_setup):
        _, overlay_file = users_setup
        manager.change_password("marie", MARIE_PASSWORD, NEW_PASSWORD)
        mode = stat.S_IMODE(os.stat(overlay_file).st_mode)
        assert mode == 0o600

    def test_new_manager_instance_loads_overlay(self, manager, users_setup):
        """Redémarrage du serveur → le nouveau mot de passe survit."""
        from python.helpers.user_manager import UserManager

        users_file, overlay_file = users_setup
        manager.change_password("marie", MARIE_PASSWORD, NEW_PASSWORD)

        fresh = UserManager(
            str(users_file), strict=True, overlay_path=str(overlay_file)
        )
        assert fresh.authenticate("marie", NEW_PASSWORD) is not None
        assert fresh.authenticate("marie", MARIE_PASSWORD) is None

    def test_overlay_cannot_escalate_role(self, users_setup):
        """Un overlay malveillant ne peut PAS changer role/organization."""
        from python.helpers.user_manager import UserManager

        users_file, overlay_file = users_setup
        overlay_file.write_text(
            json.dumps(
                {
                    "password_overrides": {
                        "marie": hash_password(NEW_PASSWORD),
                    },
                    # Tentative d'escalade — doit être ignorée
                    "users": {"marie": {"role": "admin"}},
                    "roles": {"marie": "admin"},
                }
            ),
            encoding="utf-8",
        )
        mgr = UserManager(
            str(users_file), strict=True, overlay_path=str(overlay_file)
        )
        result = mgr.authenticate("marie", NEW_PASSWORD)
        assert result is not None
        assert result["role"] == "user"
        assert result["organization"] == "dica"

    def test_overlay_non_argon2_hash_ignored(self, users_setup):
        """Un overlay avec une valeur non-Argon2 est ignoré (fail-closed)."""
        from python.helpers.user_manager import UserManager

        users_file, overlay_file = users_setup
        overlay_file.write_text(
            json.dumps({"password_overrides": {"marie": "plaintext-pass"}}),
            encoding="utf-8",
        )
        mgr = UserManager(
            str(users_file), strict=True, overlay_path=str(overlay_file)
        )
        # Le mot de passe d'origine reste le seul valide
        assert mgr.authenticate("marie", MARIE_PASSWORD) is not None
        assert mgr.authenticate("marie", "plaintext-pass") is None

    def test_overlay_unknown_user_ignored(self, users_setup):
        """L'overlay ne peut pas créer de nouveau compte."""
        from python.helpers.user_manager import UserManager

        users_file, overlay_file = users_setup
        overlay_file.write_text(
            json.dumps(
                {"password_overrides": {"intrus": hash_password(NEW_PASSWORD)}}
            ),
            encoding="utf-8",
        )
        mgr = UserManager(
            str(users_file), strict=True, overlay_path=str(overlay_file)
        )
        assert mgr.authenticate("intrus", NEW_PASSWORD) is None

    def test_corrupt_overlay_does_not_break_auth(self, users_setup):
        """Overlay JSON corrompu → ignoré, l'auth de base fonctionne."""
        from python.helpers.user_manager import UserManager

        users_file, overlay_file = users_setup
        overlay_file.write_text("{invalid json", encoding="utf-8")
        mgr = UserManager(
            str(users_file), strict=True, overlay_path=str(overlay_file)
        )
        assert mgr.authenticate("marie", MARIE_PASSWORD) is not None


# ============================================================================
# T3 — Mode mono-user : refus explicite
# ============================================================================

class TestMonoUserMode:
    def test_mono_user_change_rejected(self, tmp_path, monkeypatch):
        from python.helpers.user_manager import UserManager

        monkeypatch.setenv("AUTH_LOGIN", "solo")
        monkeypatch.setenv("AUTH_PASSWORD", hash_password("SoloPass12345!"))
        mgr = UserManager(
            str(tmp_path / "missing.json"),
            overlay_path=str(tmp_path / "overlay.json"),
        )
        assert mgr.is_mono_user
        ok, msg = mgr.change_password("solo", "SoloPass12345!", NEW_PASSWORD)
        assert ok is False
        assert "administrateur" in msg.lower() or "mono" in msg.lower()


# ============================================================================
# T4 — Route Flask /change_password
# ============================================================================

@pytest.fixture
def flask_app(users_setup, tmp_path):
    users_file, overlay_file = users_setup
    os.environ["EVIDENCE_USERS_JSON"] = str(users_file)
    os.environ["EVIDENCE_USERS_OVERLAY"] = str(overlay_file)
    os.environ["AUTH_LOGIN"] = "admin"
    os.environ["AUTH_PASSWORD"] = "fallback"

    from run_ui import create_app

    app = create_app(testing=True, secret_key="test-secret")
    yield app

    os.environ.pop("EVIDENCE_USERS_JSON", None)
    os.environ.pop("EVIDENCE_USERS_OVERLAY", None)


@pytest.fixture
def client(flask_app):
    return flask_app.test_client()


def _login(client, username=None, password=None):
    return client.post(
        "/login",
        data={
            "username": username or "marie",
            "password": password or MARIE_PASSWORD,
        },
    )


def _set_csrf(client, token="test-csrf-token"):
    with client.session_transaction() as sess:
        sess["csrf_token"] = token
    return {"X-CSRF-Token": token}


class TestChangePasswordRoute:
    def test_requires_authentication(self, client):
        resp = client.post(
            "/change_password",
            json={"current_password": "a", "new_password": "b"},
        )
        # Non authentifié → redirection login (302) ou 401
        assert resp.status_code in (301, 302, 303, 401)

    def test_requires_csrf(self, client):
        _login(client)
        resp = client.post(
            "/change_password",
            json={
                "current_password": MARIE_PASSWORD,
                "new_password": NEW_PASSWORD,
            },
        )
        assert resp.status_code == 403

    def test_success(self, client, users_setup):
        _, overlay_file = users_setup
        _login(client)
        headers = _set_csrf(client)
        resp = client.post(
            "/change_password",
            json={
                "current_password": MARIE_PASSWORD,
                "new_password": NEW_PASSWORD,
            },
            headers=headers,
        )
        assert resp.status_code == 200
        assert resp.get_json()["success"] is True
        assert overlay_file.exists()

    def test_wrong_current_password_400(self, client):
        _login(client)
        headers = _set_csrf(client)
        resp = client.post(
            "/change_password",
            json={
                "current_password": "MauvaisPass999!",
                "new_password": NEW_PASSWORD,
            },
            headers=headers,
        )
        assert resp.status_code == 400
        assert resp.get_json()["success"] is False

    def test_weak_password_400(self, client):
        _login(client)
        headers = _set_csrf(client)
        resp = client.post(
            "/change_password",
            json={
                "current_password": MARIE_PASSWORD,
                "new_password": "court",
            },
            headers=headers,
        )
        assert resp.status_code == 400

    def test_missing_fields_400(self, client):
        _login(client)
        headers = _set_csrf(client)
        resp = client.post("/change_password", json={}, headers=headers)
        assert resp.status_code == 400

    def test_login_works_with_new_password_after_change(self, client):
        _login(client)
        headers = _set_csrf(client)
        client.post(
            "/change_password",
            json={
                "current_password": MARIE_PASSWORD,
                "new_password": NEW_PASSWORD,
            },
            headers=headers,
        )
        client.get("/logout")
        resp = _login(client, "marie", NEW_PASSWORD)
        assert resp.status_code in (301, 302, 303)
