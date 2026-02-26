"""
Tests T01-T04: Multi-user authentication.

TDD RED phase — these tests define the contract for user_manager.py
All MUST fail before implementation, all MUST pass after.

Spec: docs/SPEC_MULTI_USER_WORKSPACE.md
Rules: R1 (multi-auth), R2 (session), R10 (retro-compat)
"""

import json
import os
import pytest
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def users_json_path(tmp_path):
    """Create a valid users.json with test users."""
    from python.security.auth import hash_password

    users_data = {
        "users": {
            "marie": {
                "password_hash": hash_password("MariePass123!"),
                "role": "user"
            },
            "jean": {
                "password_hash": hash_password("JeanPass456!"),
                "role": "user"
            },
            "admin": {
                "password_hash": hash_password("AdminPass789!"),
                "role": "admin"
            }
        }
    }
    users_file = tmp_path / "users.json"
    users_file.write_text(json.dumps(users_data, indent=2))
    return str(users_file)


@pytest.fixture
def plaintext_users_json(tmp_path):
    """Create a users.json with plaintext passwords (INVALID in production)."""
    users_data = {
        "users": {
            "baduser": {
                "password_hash": "plaintext_not_hashed",
                "role": "user"
            }
        }
    }
    users_file = tmp_path / "users.json"
    users_file.write_text(json.dumps(users_data, indent=2))
    return str(users_file)


@pytest.fixture
def empty_users_dir(tmp_path):
    """A directory WITHOUT users.json (mono-user fallback)."""
    return str(tmp_path)


# ============================================================================
# T01 — Login with valid user → session contains username
# Rule: R1 (multi-auth), R2 (session)
# ============================================================================

class TestT01_ValidLogin:
    """T01: Login with valid multi-user credentials."""

    def test_authenticate_valid_user_marie(self, users_json_path):
        """Marie logs in with correct password → returns user info."""
        from python.helpers.user_manager import UserManager

        mgr = UserManager(users_json_path)
        result = mgr.authenticate("marie", "MariePass123!")

        assert result is not None
        assert result["username"] == "marie"
        assert result["role"] == "user"

    def test_authenticate_valid_user_admin(self, users_json_path):
        """Admin logs in with correct password → returns admin info."""
        from python.helpers.user_manager import UserManager

        mgr = UserManager(users_json_path)
        result = mgr.authenticate("admin", "AdminPass789!")

        assert result is not None
        assert result["username"] == "admin"
        assert result["role"] == "admin"

    def test_authenticate_returns_no_password_hash(self, users_json_path):
        """Authentication result MUST NOT contain the password hash."""
        from python.helpers.user_manager import UserManager

        mgr = UserManager(users_json_path)
        result = mgr.authenticate("marie", "MariePass123!")

        assert "password_hash" not in result
        assert "password" not in result

    def test_list_users(self, users_json_path):
        """List all usernames without exposing password hashes."""
        from python.helpers.user_manager import UserManager

        mgr = UserManager(users_json_path)
        users = mgr.list_users()

        assert set(users) == {"marie", "jean", "admin"}

    def test_get_user_role(self, users_json_path):
        """Get the role for a specific user."""
        from python.helpers.user_manager import UserManager

        mgr = UserManager(users_json_path)
        assert mgr.get_role("marie") == "user"
        assert mgr.get_role("admin") == "admin"


# ============================================================================
# T02 — Login with invalid user → rejected
# Rule: R1
# ============================================================================

class TestT02_InvalidLogin:
    """T02: Invalid credentials are rejected."""

    def test_wrong_password(self, users_json_path):
        """Correct username, wrong password → None."""
        from python.helpers.user_manager import UserManager

        mgr = UserManager(users_json_path)
        result = mgr.authenticate("marie", "WrongPassword!")

        assert result is None

    def test_unknown_user(self, users_json_path):
        """Unknown username → None."""
        from python.helpers.user_manager import UserManager

        mgr = UserManager(users_json_path)
        result = mgr.authenticate("inconnu", "SomePassword!")

        assert result is None

    def test_empty_password(self, users_json_path):
        """Empty password → None."""
        from python.helpers.user_manager import UserManager

        mgr = UserManager(users_json_path)
        result = mgr.authenticate("marie", "")

        assert result is None

    def test_empty_username(self, users_json_path):
        """Empty username → None."""
        from python.helpers.user_manager import UserManager

        mgr = UserManager(users_json_path)
        result = mgr.authenticate("", "MariePass123!")

        assert result is None

    def test_none_credentials(self, users_json_path):
        """None credentials → None (no crash)."""
        from python.helpers.user_manager import UserManager

        mgr = UserManager(users_json_path)
        result = mgr.authenticate(None, None)

        assert result is None


# ============================================================================
# T03 — Plaintext password in production → error
# Rule: R1
# ============================================================================

class TestT03_PlaintextRejection:
    """T03: Plaintext passwords rejected in strict mode."""

    def test_plaintext_password_rejected_strict(self, plaintext_users_json):
        """Loading users.json with plaintext password in strict mode → raises."""
        from python.helpers.user_manager import UserManager

        with pytest.raises(ValueError, match="[Pp]laintext|[Hh]ash"):
            UserManager(plaintext_users_json, strict=True)

    def test_plaintext_password_warning_non_strict(self, plaintext_users_json):
        """Loading users.json with plaintext password in non-strict → warns."""
        import warnings
        from python.helpers.user_manager import UserManager

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            mgr = UserManager(plaintext_users_json, strict=False)
            assert any("plaintext" in str(warning.message).lower() for warning in w)


# ============================================================================
# T04 — Fallback to mono-user if no users.json
# Rule: R10
# ============================================================================

class TestT04_MonoUserFallback:
    """T04: If users.json doesn't exist, fallback to AUTH_LOGIN/AUTH_PASSWORD."""

    def test_no_users_json_uses_env(self, empty_users_dir):
        """No users.json → UserManager falls back to environment variables."""
        from python.helpers.user_manager import UserManager

        with patch.dict(os.environ, {
            "AUTH_LOGIN": "admin",
            "AUTH_PASSWORD": "TestPass123!"
        }):
            mgr = UserManager(
                os.path.join(empty_users_dir, "users.json")  # doesn't exist
            )
            assert mgr.is_mono_user is True

    def test_mono_user_authenticate(self, empty_users_dir):
        """Mono-user mode: authenticate with AUTH_LOGIN/AUTH_PASSWORD."""
        from python.helpers.user_manager import UserManager

        with patch.dict(os.environ, {
            "AUTH_LOGIN": "admin",
            "AUTH_PASSWORD": "TestPass123!"
        }):
            mgr = UserManager(
                os.path.join(empty_users_dir, "users.json")
            )
            result = mgr.authenticate("admin", "TestPass123!")

            assert result is not None
            assert result["username"] == "admin"
            assert result["role"] == "admin"  # mono-user is always admin

    def test_mono_user_wrong_password(self, empty_users_dir):
        """Mono-user mode: wrong password → None."""
        from python.helpers.user_manager import UserManager

        with patch.dict(os.environ, {
            "AUTH_LOGIN": "admin",
            "AUTH_PASSWORD": "TestPass123!"
        }):
            mgr = UserManager(
                os.path.join(empty_users_dir, "users.json")
            )
            result = mgr.authenticate("admin", "WrongPass!")

            assert result is None

    def test_no_auth_at_all(self, empty_users_dir):
        """No users.json AND no AUTH_LOGIN → no auth required."""
        from python.helpers.user_manager import UserManager

        env = os.environ.copy()
        env.pop("AUTH_LOGIN", None)
        env.pop("AUTH_PASSWORD", None)

        with patch.dict(os.environ, env, clear=True):
            mgr = UserManager(
                os.path.join(empty_users_dir, "users.json")
            )
            assert mgr.is_auth_required is False
