"""
Per-user workspace isolation manager.

Manages the shared directory structure:
  {SHARED_ROOT}/
  ├── users/
  │   ├── {username}/
  │   │   ├── documents/
  │   │   ├── rapports/
  │   │   └── tmp/
  │   └── ...
  ├── commun/
  └── audit/
      └── file_operations.jsonl

Spec: docs/SPEC_MULTI_USER_WORKSPACE.md — Rules R3, R4, R5, R6, R7, R8
"""

import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

logger = logging.getLogger("user_workspace")

# Subdirectories created for each user
_USER_SUBDIRS = ("documents", "rapports", "tmp")


class WorkspaceManager:
    """Manages per-user workspaces with strict isolation.

    Parameters
    ----------
    shared_root : str
        Root path for all shared data (e.g. /app/shared).
    """

    def __init__(self, shared_root: str):
        self._root = Path(shared_root).resolve()
        self._users_dir = self._root / "users"
        self._commun_dir = self._root / "commun"
        self._audit_dir = self._root / "audit"

        # Create top-level directories
        self._users_dir.mkdir(parents=True, exist_ok=True)
        self._commun_dir.mkdir(parents=True, exist_ok=True)
        self._audit_dir.mkdir(parents=True, exist_ok=True)

    # ── Workspace lifecycle ──────────────────────────────────────────────

    def ensure_workspace(self, username: str) -> str:
        """Create and return the workspace directory for a user.

        Idempotent: safe to call multiple times.

        Returns
        -------
        str
            Absolute path to the user's workspace.
        """
        ws = self._users_dir / username
        for subdir in _USER_SUBDIRS:
            (ws / subdir).mkdir(parents=True, exist_ok=True)
        return str(ws.resolve())

    def list_workspaces(self) -> list[str]:
        """List all user workspace names."""
        if not self._users_dir.exists():
            return []
        return [
            d.name
            for d in self._users_dir.iterdir()
            if d.is_dir()
        ]

    # ── Path validation ──────────────────────────────────────────────────

    def _resolve_safe(self, path_str: str) -> Path:
        """Resolve a path, following symlinks, to get the real location."""
        p = Path(path_str)
        # Resolve symlinks to detect escape attempts
        try:
            return p.resolve(strict=False)
        except (OSError, ValueError):
            # On resolution failure, return the raw resolve
            return p.resolve()

    def _is_in_workspace(self, username: str, resolved: Path) -> bool:
        """Check if a resolved path is inside the user's workspace."""
        ws = (self._users_dir / username).resolve()
        try:
            resolved.relative_to(ws)
            return True
        except ValueError:
            return False

    def _is_in_commun(self, resolved: Path) -> bool:
        """Check if a resolved path is inside the commun/ directory."""
        commun = self._commun_dir.resolve()
        try:
            resolved.relative_to(commun)
            return True
        except ValueError:
            return False

    def _check_access(
        self,
        username: str,
        path_str: str,
        operation: str,
        role: str = "user",
    ) -> Path:
        """Validate and return the resolved path, or raise PermissionError.

        Admin (role='admin') can access any user's workspace.

        Parameters
        ----------
        username : str
        path_str : str
        operation : str
            'read' or 'write'
        role : str
            'user' or 'admin'

        Returns
        -------
        Path
            The resolved, validated path.

        Raises
        ------
        PermissionError
            If the path is outside allowed zones.
        """
        resolved = self._resolve_safe(path_str)

        # Admin can access everything under the shared root
        if role == "admin":
            try:
                resolved.relative_to(self._root.resolve())
                return resolved
            except ValueError:
                pass
            # Admin still cannot go outside shared root
            self._audit_log(username, operation, path_str, success=False)
            raise PermissionError(
                f"Admin access denied: '{path_str}' is outside shared root"
            )

        # Regular user: own workspace + commun
        if self._is_in_workspace(username, resolved):
            return resolved

        if self._is_in_commun(resolved):
            return resolved

        # Denied
        self._audit_log(username, operation, path_str, success=False)
        raise PermissionError(
            f"Access denied for user '{username}': "
            f"'{path_str}' is outside workspace and commun/"
        )

    # ── File operations (with audit) ─────────────────────────────────────

    def read_file(
        self, username: str, path_str: str, role: str = "user"
    ) -> str:
        """Read a file, enforcing workspace isolation.

        Parameters
        ----------
        username : str
        path_str : str
        role : str

        Returns
        -------
        str
            File content.

        Raises
        ------
        PermissionError
            If path is outside allowed zones.
        """
        resolved = self._check_access(username, path_str, "read", role)
        content = resolved.read_text(encoding="utf-8")
        self._audit_log(username, "read", path_str, success=True)
        return content

    def write_file(
        self, username: str, path_str: str, content: str, role: str = "user"
    ) -> str:
        """Write content to a file, enforcing workspace isolation.

        Creates parent directories if they don't exist.

        Returns
        -------
        str
            Absolute path of the written file.

        Raises
        ------
        PermissionError
            If path is outside allowed zones.
        """
        resolved = self._check_access(username, path_str, "write", role)
        resolved.parent.mkdir(parents=True, exist_ok=True)
        resolved.write_text(content, encoding="utf-8")
        self._audit_log(username, "write", str(resolved), success=True)
        return str(resolved)

    def delete_file(
        self, username: str, path_str: str, role: str = "user"
    ) -> None:
        """Delete a file, enforcing workspace isolation.

        Raises
        ------
        PermissionError
            If path is outside allowed zones.
        """
        resolved = self._check_access(username, path_str, "delete", role)
        resolved.unlink()
        self._audit_log(username, "delete", str(resolved), success=True)

    def list_files(
        self, username: str, path_str: str, role: str = "user"
    ) -> list[str]:
        """List files in a directory, enforcing workspace isolation.

        Returns
        -------
        list[str]
            List of filenames in the directory.
        """
        resolved = self._check_access(username, path_str, "list", role)
        if not resolved.is_dir():
            raise NotADirectoryError(f"'{path_str}' is not a directory")
        return [f.name for f in resolved.iterdir()]

    # ── Scoped paths for tools ───────────────────────────────────────────

    def get_output_dir(self, username: str) -> str:
        """Return the rapports/ directory for file_writer output.

        Rule R5: file_writer MUST write to {workspace}/rapports/.
        """
        ws = self.ensure_workspace(username)
        rapports = Path(ws) / "rapports"
        return str(rapports)

    def get_exec_cwd(self, username: str) -> str:
        """Return the workspace root as CWD for code_execution_tool.

        Rule R6: code_execution CWD = {workspace}/.
        """
        return self.ensure_workspace(username)

    def validate_exec_path(self, username: str, path_str: str) -> bool:
        """Validate a path for code execution (read access).

        Returns True if the path is in the user's workspace or commun/.
        Returns False otherwise.

        Rule R6: code_execution must not access paths outside workspace.
        """
        resolved = self._resolve_safe(path_str)
        return self._is_in_workspace(username, resolved) or self._is_in_commun(resolved)

    # ── Audit trail ──────────────────────────────────────────────────────

    def _audit_log(
        self,
        username: str,
        operation: str,
        path: str,
        success: bool,
    ) -> None:
        """Append a JSONL audit entry.

        Rule R8: every file operation is logged.
        """
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "username": username,
            "operation": operation,
            "path": path,
            "success": success,
        }
        audit_file = self._audit_dir / "file_operations.jsonl"
        try:
            with open(audit_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        except OSError as e:
            logger.error(f"Audit log write failed: {e}")
