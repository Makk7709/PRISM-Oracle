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
import re
import tempfile
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
    initialize_registry_from_users,
)

logger = logging.getLogger("user_manager")

# Politique de robustesse des mots de passe (changement self-service)
PASSWORD_MIN_LENGTH = 12
PASSWORD_MAX_LENGTH = 128


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
    overlay_path : str, optional
        Path to a writable overlay file (users.local.json) holding
        password hashes changed at runtime. Needed because users.json
        is bind-mounted read-only in production (docker-compose `:ro`).
        The overlay can ONLY override `password_hash` for users that
        already exist in users.json — never role/organization (no
        privilege escalation), and never create new accounts.
    """

    def __init__(
        self,
        users_json_path: str,
        strict: bool = False,
        overlay_path: Optional[str] = None,
    ):
        self._users: dict = {}
        self._is_mono_user: bool = False
        self._is_auth_required: bool = True
        self._strict = strict
        self._overlay_path = Path(overlay_path) if overlay_path else None

        path = Path(users_json_path)

        if path.exists():
            self._load_users_json(path)
            self._apply_overlay()
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

    def _apply_overlay(self) -> None:
        """Apply password overrides from the writable overlay file.

        Fail-closed: invalid JSON, unknown users, or non-Argon2 values
        are ignored — base users.json remains the source of truth.
        Only `password_hash` can be overridden (never role/organization).
        """
        if self._overlay_path is None or not self._overlay_path.exists():
            return
        try:
            data = json.loads(self._overlay_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as e:
            logger.warning(f"Ignoring corrupt users overlay: {e}")
            return

        overrides = data.get("password_overrides", {})
        if not isinstance(overrides, dict):
            logger.warning("Ignoring users overlay: password_overrides is not a dict")
            return

        applied = 0
        for username, pw_hash in overrides.items():
            if username not in self._users:
                logger.warning(
                    f"Overlay override for unknown user '{username}' ignored"
                )
                continue
            if not isinstance(pw_hash, str) or not is_password_hashed(pw_hash):
                logger.warning(
                    f"Overlay override for '{username}' is not an Argon2 hash — ignored"
                )
                continue
            self._users[username]["password_hash"] = pw_hash
            applied += 1

        if applied:
            logger.info(f"Applied {applied} password override(s) from overlay")

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

    # ── Password change (self-service) ──────────────────────────────────

    def change_password(
        self,
        username: Optional[str],
        current_password: Optional[str],
        new_password: Optional[str],
    ) -> tuple[bool, str]:
        """Change a user's password after verifying the current one.

        The new Argon2id hash is persisted to the overlay file
        (users.json is read-only in production) and applied in memory
        so the change is effective immediately, without restart.

        Returns
        -------
        (ok, message) : tuple[bool, str]
            ok=True on success. `message` is a user-displayable reason
            (French) and never leaks sensitive details.
        """
        if self._is_mono_user:
            return (
                False,
                "Compte géré par l'administrateur (mode mono-utilisateur) : "
                "le changement de mot de passe n'est pas disponible ici.",
            )
        if not username or not current_password or not new_password:
            return False, "Champs requis manquants."

        policy_error = self._validate_password_policy(new_password)
        if policy_error:
            return False, policy_error

        if new_password == current_password:
            return False, "Le nouveau mot de passe doit être différent de l'actuel."

        # Vérification timing-safe de l'ancien mot de passe
        if self.authenticate(username, current_password) is None:
            return False, "Mot de passe actuel incorrect."

        new_hash = hash_password(new_password)
        try:
            self._persist_overlay(username, new_hash)
        except OSError as e:
            logger.error(f"Failed to persist password overlay: {e}")
            return (
                False,
                "Échec d'enregistrement du nouveau mot de passe. Réessayez "
                "ou contactez l'administrateur.",
            )

        # Application immédiate en mémoire (pas de redémarrage requis)
        self._users[username]["password_hash"] = new_hash
        logger.info(f"Password changed for user '{username}'")
        return True, "Mot de passe mis à jour avec succès."

    @staticmethod
    def _validate_password_policy(password: str) -> Optional[str]:
        """Return an error message if the password violates the policy."""
        if len(password) < PASSWORD_MIN_LENGTH:
            return (
                f"Le mot de passe doit contenir au moins "
                f"{PASSWORD_MIN_LENGTH} caractères."
            )
        if len(password) > PASSWORD_MAX_LENGTH:
            return (
                f"Le mot de passe ne peut pas dépasser "
                f"{PASSWORD_MAX_LENGTH} caractères."
            )
        if not re.search(r"[A-Za-z]", password):
            return "Le mot de passe doit contenir au moins une lettre."
        if not re.search(r"\d", password):
            return "Le mot de passe doit contenir au moins un chiffre."
        return None

    def _persist_overlay(self, username: str, new_hash: str) -> None:
        """Atomically persist a password override to the overlay file.

        Write to a temp file in the same directory then os.replace()
        (atomic on POSIX). Permissions are restricted to 0600.
        """
        if self._overlay_path is None:
            raise OSError("No overlay path configured for password persistence")

        data: dict = {"password_overrides": {}}
        if self._overlay_path.exists():
            try:
                existing = json.loads(
                    self._overlay_path.read_text(encoding="utf-8")
                )
                if isinstance(existing.get("password_overrides"), dict):
                    data["password_overrides"] = existing["password_overrides"]
            except (json.JSONDecodeError, OSError):
                logger.warning("Overwriting corrupt users overlay")

        data["password_overrides"][username] = new_hash

        self._overlay_path.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp_path = tempfile.mkstemp(
            dir=str(self._overlay_path.parent), suffix=".tmp"
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                json.dump(data, fh, indent=2)
                fh.flush()
                os.fsync(fh.fileno())
            os.chmod(tmp_path, 0o600)
            os.replace(tmp_path, self._overlay_path)
        except OSError:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
            raise

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

    def get_compliance_role(self, username: str) -> Optional[str]:
        """Get the compliance role (DPO, RSSI, COMPLIANCE_OFFICER) or None."""
        info = self._users.get(username)
        if info is None:
            return None
        return info.get("compliance_role")

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
