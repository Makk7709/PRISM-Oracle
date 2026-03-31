"""
Multi-user authentication manager.

Supports two modes:
1. Multi-user: users defined in a users.json file
2. Mono-user (fallback): single user via AUTH_LOGIN/AUTH_PASSWORD env vars

Spec: docs/SPEC_MULTI_USER_WORKSPACE.md — Rules R1, R2, R10
"""

import json
import hmac
import os
import warnings
import logging
from pathlib import Path
from typing import Optional

from python.security.auth import (
    verify_password,
    is_password_hashed,
    hash_password,
)
from python.helpers.organization import (
    normalize_org_id,
    get_registry,
    initialize_registry_from_users,
)

logger = logging.getLogger("user_manager")


class UserManager:
    """Manages user authentication for KOREV Evidence.

    Parameters
    ----------
    users_json_path : str
        Path to the users.json file. If the file doesn't exist,
        falls back to mono-user mode using AUTH_LOGIN/AUTH_PASSWORD.
    strict : bool
        If True, reject plaintext passwords with ValueError.
        If False, emit a warning but allow (dev mode only).
    """

    def __init__(self, users_json_path: str, strict: bool = False):
        self._users: dict = {}
        self._is_mono_user: bool = False
        self._is_auth_required: bool = True
        self._strict = strict

        path = Path(users_json_path)

        if path.exists():
            self._load_users_json(path)
        else:
            self._fallback_mono_user()

    # ── Loading ──────────────────────────────────────────────────────────

    def _load_users_json(self, path: Path) -> None:
        """Load and validate users from a JSON file."""
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as e:
            logger.error(f"Failed to load users.json: {e}")
            self._fallback_mono_user()
            return

        users_dict = data.get("users", {})
        if not users_dict:
            logger.warning("users.json has no users, falling back to mono-user")
            self._fallback_mono_user()
            return

        # Validate password hashes
        for username, info in users_dict.items():
            pw_hash = info.get("password_hash", "")
            if not is_password_hashed(pw_hash):
                msg = (
                    f"User '{username}' has a plaintext password in users.json. "
                    f"Hash it with: python -c \"from python.security.auth import "
                    f"hash_password; print(hash_password('YOUR_PASSWORD'))\""
                )
                if self._strict:
                    raise ValueError(msg)
                else:
                    warnings.warn(msg, UserWarning)

        self._users = users_dict
        self._is_mono_user = False
        self._is_auth_required = True
        initialize_registry_from_users(users_dict)
        logger.info(f"Loaded {len(self._users)} users from users.json")

    def _fallback_mono_user(self) -> None:
        """Fall back to single-user mode using environment variables."""
        login = os.environ.get("AUTH_LOGIN", "").strip()
        password = os.environ.get("AUTH_PASSWORD", "").strip()

        if not login:
            # No auth configured at all
            self._is_mono_user = True
            self._is_auth_required = False
            self._users = {}
            logger.info("No authentication configured (no users.json, no AUTH_LOGIN)")
            return

        # Build a single-user entry
        self._users = {
            login: {
                "password_hash": password,  # May be plaintext or Argon2
                "role": "admin",  # Mono-user is always admin
            }
        }
        self._is_mono_user = True
        self._is_auth_required = True
        logger.info(f"Mono-user mode: user='{login}'")

    # ── Properties ───────────────────────────────────────────────────────

    @property
    def is_mono_user(self) -> bool:
        """True if running in single-user fallback mode."""
        return self._is_mono_user

    @property
    def is_auth_required(self) -> bool:
        """True if authentication is required (at least one user configured)."""
        return self._is_auth_required

    # ── Authentication ───────────────────────────────────────────────────

    def authenticate(
        self, username: Optional[str], password: Optional[str]
    ) -> Optional[dict]:
        """Authenticate a user.

        Parameters
        ----------
        username : str or None
        password : str or None

        Returns
        -------
        dict or None
            On success: {"username": str, "role": str}
            On failure: None
        """
        if not username or not password:
            return None

        user_info = self._users.get(username)
        if user_info is None:
            # Timing-safe: still do a dummy check
            _dummy_verify()
            return None

        stored_hash = user_info.get("password_hash", "")

        if is_password_hashed(stored_hash):
            if verify_password(stored_hash, password):
                return {
                    "username": username,
                    "role": user_info.get("role", "user"),
                    "organization": user_info.get("organization"),
                    "org_role": user_info.get("org_role", "MEMBER"),
                }
            return None
        else:
            if hmac.compare_digest(
                password.encode("utf-8"), stored_hash.encode("utf-8")
            ):
                return {
                    "username": username,
                    "role": user_info.get("role", "user"),
                    "organization": user_info.get("organization"),
                    "org_role": user_info.get("org_role", "MEMBER"),
                }
            return None

    # ── User listing ─────────────────────────────────────────────────────

    def list_users(self) -> list[str]:
        """List all usernames (without sensitive data)."""
        return list(self._users.keys())

    def get_role(self, username: str) -> Optional[str]:
        """Get the role for a user, or None if not found."""
        info = self._users.get(username)
        if info is None:
            return None
        return info.get("role", "user")

    def get_organization(self, username: str) -> Optional[str]:
        """Get the display organization name for a user, or None if not found."""
        info = self._users.get(username)
        if info is None:
            return None
        return info.get("organization")

    def get_organization_id(self, username: str) -> str:
        """Get the canonical normalized org slug for a user."""
        raw = self.get_organization(username)
        return normalize_org_id(raw)

    def get_org_role(self, username: str) -> Optional[str]:
        """Get the org_role for a user, or None if not found."""
        info = self._users.get(username)
        if info is None:
            return None
        return info.get("org_role", "MEMBER")

    def get_user_profile(self, username: str) -> str:
        """Get the display profile for a user.

        Returns the explicit `profile` field if set, otherwise falls back
        to the capitalised `role` (e.g. "Admin", "User").
        Never raises — returns "User" on any failure.
        """
        info = self._users.get(username)
        if info is None:
            return "User"
        profile = info.get("profile")
        if profile:
            return profile
        role = info.get("role", "user")
        return role.capitalize()

    def get_org_members(self, organization: str) -> list[str]:
        """Get all usernames belonging to an organization (matches by normalized slug)."""
        target_id = normalize_org_id(organization)
        return [
            uname for uname, info in self._users.items()
            if normalize_org_id(info.get("organization")) == target_id
        ]


def _dummy_verify() -> None:
    """Constant-time dummy to prevent timing attacks on username enumeration."""
    try:
        from python.security.auth import _dummy_verify as _dv
        _dv()
    except ImportError:
        pass
