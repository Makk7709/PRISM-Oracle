"""
Tests T05-T16: User workspace isolation, file operations scoping, audit.

TDD RED phase — these tests define the contract for user_workspace.py
All MUST fail before implementation, all MUST pass after.

Spec: docs/SPEC_MULTI_USER_WORKSPACE.md
Rules: R3 (isolation), R4 (traversal), R5 (file_writer), R6 (code_exec),
       R7 (admin), R8 (audit)
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
def shared_root(tmp_path):
    """Create a temporary shared root directory."""
    root = tmp_path / "shared"
    root.mkdir()
    return root


@pytest.fixture
def workspace_manager(shared_root):
    """Create a WorkspaceManager with a temp shared root."""
    from python.helpers.user_workspace import WorkspaceManager

    return WorkspaceManager(str(shared_root))


@pytest.fixture
def marie_workspace(workspace_manager):
    """Ensure Marie's workspace exists and return its path."""
    return workspace_manager.ensure_workspace("marie")


@pytest.fixture
def jean_workspace(workspace_manager):
    """Ensure Jean's workspace exists and return its path."""
    return workspace_manager.ensure_workspace("jean")


@pytest.fixture
def admin_workspace(workspace_manager):
    """Ensure admin workspace exists and return its path."""
    return workspace_manager.ensure_workspace("admin")


# ============================================================================
# T05 — Workspace created on first login
# Rule: R3
# ============================================================================

class TestT05_WorkspaceCreation:
    """T05: Workspace is created when user first accesses it."""

    def test_ensure_workspace_creates_directory(self, workspace_manager, shared_root):
        """Calling ensure_workspace creates the user directory."""
        path = workspace_manager.ensure_workspace("marie")

        assert Path(path).exists()
        assert Path(path).is_dir()
        assert "marie" in path

    def test_ensure_workspace_idempotent(self, workspace_manager):
        """Calling ensure_workspace twice returns the same path."""
        path1 = workspace_manager.ensure_workspace("marie")
        path2 = workspace_manager.ensure_workspace("marie")

        assert path1 == path2

    def test_commun_folder_created(self, workspace_manager, shared_root):
        """The 'commun' shared folder is created on init."""
        commun = shared_root / "commun"
        # WorkspaceManager should create commun/ on init
        assert commun.exists()
        assert commun.is_dir()


# ============================================================================
# T06 — Workspace contains documents/ rapports/ tmp/
# Rule: R3
# ============================================================================

class TestT06_WorkspaceStructure:
    """T06: Workspace has the correct subdirectory structure."""

    def test_workspace_has_documents(self, marie_workspace):
        """Workspace contains documents/ subdirectory."""
        assert (Path(marie_workspace) / "documents").exists()
        assert (Path(marie_workspace) / "documents").is_dir()

    def test_workspace_has_rapports(self, marie_workspace):
        """Workspace contains rapports/ subdirectory."""
        assert (Path(marie_workspace) / "rapports").exists()
        assert (Path(marie_workspace) / "rapports").is_dir()

    def test_workspace_has_tmp(self, marie_workspace):
        """Workspace contains tmp/ subdirectory."""
        assert (Path(marie_workspace) / "tmp").exists()
        assert (Path(marie_workspace) / "tmp").is_dir()


# ============================================================================
# T07 — User cannot READ outside workspace
# Rule: R4
# ============================================================================

class TestT07_ReadIsolation:
    """T07: User cannot read files outside their workspace."""

    def test_cannot_read_other_user_file(
        self, workspace_manager, marie_workspace, jean_workspace
    ):
        """Marie cannot read a file in Jean's workspace."""
        # Create a file in Jean's workspace
        jean_file = Path(jean_workspace) / "documents" / "secret.txt"
        jean_file.write_text("Jean's secret")

        # Marie tries to read it
        with pytest.raises(PermissionError):
            workspace_manager.read_file("marie", str(jean_file))

    def test_cannot_read_parent_directory(self, workspace_manager, marie_workspace):
        """Marie cannot read /etc/passwd via path traversal."""
        with pytest.raises(PermissionError):
            workspace_manager.read_file("marie", "/etc/passwd")

    def test_can_read_own_file(self, workspace_manager, marie_workspace):
        """Marie CAN read her own file."""
        my_file = Path(marie_workspace) / "documents" / "myfile.txt"
        my_file.write_text("Marie's file")

        content = workspace_manager.read_file("marie", str(my_file))
        assert content == "Marie's file"

    def test_can_read_commun(self, workspace_manager, marie_workspace, shared_root):
        """Marie CAN read files in commun/."""
        commun_file = shared_root / "commun" / "template.txt"
        commun_file.write_text("Shared template")

        content = workspace_manager.read_file("marie", str(commun_file))
        assert content == "Shared template"


# ============================================================================
# T08 — User cannot WRITE outside workspace
# Rule: R4
# ============================================================================

class TestT08_WriteIsolation:
    """T08: User cannot write files outside their workspace."""

    def test_cannot_write_other_user_workspace(
        self, workspace_manager, marie_workspace, jean_workspace
    ):
        """Marie cannot write into Jean's workspace."""
        target = Path(jean_workspace) / "documents" / "injected.txt"

        with pytest.raises(PermissionError):
            workspace_manager.write_file("marie", str(target), "hacked!")

    def test_cannot_write_system_path(self, workspace_manager, marie_workspace):
        """Marie cannot write to /tmp/evil.txt."""
        with pytest.raises(PermissionError):
            workspace_manager.write_file("marie", "/tmp/evil.txt", "evil")

    def test_can_write_own_workspace(self, workspace_manager, marie_workspace):
        """Marie CAN write to her own workspace."""
        target = Path(marie_workspace) / "documents" / "myreport.txt"

        workspace_manager.write_file("marie", str(target), "My report content")

        assert target.exists()
        assert target.read_text() == "My report content"

    def test_can_write_commun(self, workspace_manager, marie_workspace, shared_root):
        """Marie CAN write to commun/."""
        target = shared_root / "commun" / "shared_note.txt"

        workspace_manager.write_file("marie", str(target), "Shared note")

        assert target.exists()


# ============================================================================
# T09 — Path traversal rejected
# Rule: R4
# ============================================================================

class TestT09_PathTraversal:
    """T09: Path traversal attacks are blocked."""

    def test_dotdot_read_rejected(self, workspace_manager, marie_workspace):
        """../../../etc/passwd in read → PermissionError."""
        evil_path = os.path.join(marie_workspace, "..", "..", "..", "etc", "passwd")

        with pytest.raises(PermissionError):
            workspace_manager.read_file("marie", evil_path)

    def test_dotdot_write_rejected(self, workspace_manager, marie_workspace):
        """../../../tmp/evil in write → PermissionError."""
        evil_path = os.path.join(marie_workspace, "..", "..", "..", "tmp", "evil")

        with pytest.raises(PermissionError):
            workspace_manager.write_file("marie", evil_path, "evil")

    def test_relative_path_normalized(self, workspace_manager, marie_workspace):
        """Relative paths like documents/../documents/file.txt are OK if resolved in workspace."""
        target = os.path.join(marie_workspace, "documents", "..", "documents", "ok.txt")

        # This should succeed (resolves to workspace/documents/ok.txt)
        workspace_manager.write_file("marie", target, "OK")

        resolved = Path(marie_workspace) / "documents" / "ok.txt"
        assert resolved.exists()


# ============================================================================
# T10 — Symlink attacks rejected
# Rule: R4
# ============================================================================

class TestT10_SymlinkAttack:
    """T10: Symlinks pointing outside workspace are rejected."""

    def test_symlink_to_external_dir_rejected(
        self, workspace_manager, marie_workspace, tmp_path
    ):
        """Symlink in workspace pointing to /tmp → rejected."""
        external_dir = tmp_path / "external_secret"
        external_dir.mkdir()
        (external_dir / "secret.txt").write_text("TOP SECRET")

        # Create a symlink inside Marie's workspace pointing outside
        symlink = Path(marie_workspace) / "documents" / "evil_link"
        symlink.symlink_to(external_dir)

        with pytest.raises(PermissionError):
            workspace_manager.read_file(
                "marie",
                str(symlink / "secret.txt")
            )


# ============================================================================
# T11 — User can read/write in commun/
# Rule: R3, R4
# ============================================================================

class TestT11_CommunAccess:
    """T11: All users can read/write in the commun/ folder."""

    def test_marie_writes_jean_reads(
        self, workspace_manager, marie_workspace, jean_workspace, shared_root
    ):
        """Marie writes to commun → Jean can read it."""
        target = shared_root / "commun" / "collaboration.txt"

        workspace_manager.write_file("marie", str(target), "Hello from Marie")

        content = workspace_manager.read_file("jean", str(target))
        assert content == "Hello from Marie"


# ============================================================================
# T12 — file_writer writes to {workspace}/rapports/
# Rule: R5
# ============================================================================

class TestT12_FileWriterScoped:
    """T12: file_writer outputs to user's rapports/ directory."""

    def test_get_output_dir_returns_rapports(self, workspace_manager, marie_workspace):
        """Output dir for file_writer = {workspace}/rapports/."""
        output_dir = workspace_manager.get_output_dir("marie")

        assert output_dir == str(Path(marie_workspace) / "rapports")
        assert Path(output_dir).exists()


# ============================================================================
# T13 — code_execution CWD = workspace
# Rule: R6
# ============================================================================

class TestT13_CodeExecCWD:
    """T13: Code execution working directory is the user's workspace."""

    def test_get_cwd_returns_workspace(self, workspace_manager, marie_workspace):
        """CWD for code execution = user's workspace root."""
        cwd = workspace_manager.get_exec_cwd("marie")

        assert cwd == marie_workspace

    def test_get_cwd_different_per_user(
        self, workspace_manager, marie_workspace, jean_workspace
    ):
        """Different users get different CWDs."""
        cwd_marie = workspace_manager.get_exec_cwd("marie")
        cwd_jean = workspace_manager.get_exec_cwd("jean")

        assert cwd_marie != cwd_jean


# ============================================================================
# T14 — code_execution cannot chdir outside workspace
# Rule: R6
# ============================================================================

class TestT14_ChdirBlocked:
    """T14: validate_exec_path blocks paths outside workspace."""

    def test_validate_path_in_workspace_ok(self, workspace_manager, marie_workspace):
        """Path inside workspace → valid."""
        path = os.path.join(marie_workspace, "documents", "script.py")
        assert workspace_manager.validate_exec_path("marie", path) is True

    def test_validate_path_outside_workspace_rejected(
        self, workspace_manager, marie_workspace
    ):
        """Path outside workspace → rejected."""
        assert workspace_manager.validate_exec_path("marie", "/etc/passwd") is False

    def test_validate_path_other_user_rejected(
        self, workspace_manager, marie_workspace, jean_workspace
    ):
        """Path in another user's workspace → rejected."""
        assert workspace_manager.validate_exec_path("marie", jean_workspace) is False


# ============================================================================
# T15 — Admin can access all workspaces
# Rule: R7
# ============================================================================

class TestT15_AdminAccess:
    """T15: Admin can access all user workspaces."""

    def test_admin_reads_marie_file(
        self, workspace_manager, admin_workspace, marie_workspace
    ):
        """Admin can read Marie's files."""
        marie_file = Path(marie_workspace) / "documents" / "report.txt"
        marie_file.write_text("Marie's report")

        content = workspace_manager.read_file(
            "admin", str(marie_file), role="admin"
        )
        assert content == "Marie's report"

    def test_admin_lists_all_workspaces(self, workspace_manager, marie_workspace, jean_workspace):
        """Admin can list all user workspaces."""
        workspaces = workspace_manager.list_workspaces()

        assert "marie" in workspaces
        assert "jean" in workspaces


# ============================================================================
# T16 — Audit trail for file operations
# Rule: R8
# ============================================================================

class TestT16_AuditTrail:
    """T16: File operations are logged in audit trail."""

    def test_write_operation_logged(
        self, workspace_manager, marie_workspace, shared_root
    ):
        """Writing a file creates an audit log entry."""
        target = Path(marie_workspace) / "documents" / "audited.txt"
        workspace_manager.write_file("marie", str(target), "Audited content")

        audit_file = shared_root / "audit" / "file_operations.jsonl"
        assert audit_file.exists()

        lines = audit_file.read_text().strip().split("\n")
        last_entry = json.loads(lines[-1])

        assert last_entry["username"] == "marie"
        assert last_entry["operation"] == "write"
        assert "audited.txt" in last_entry["path"]
        assert last_entry["success"] is True

    def test_read_operation_logged(
        self, workspace_manager, marie_workspace, shared_root
    ):
        """Reading a file creates an audit log entry."""
        target = Path(marie_workspace) / "documents" / "toread.txt"
        target.write_text("Read me")

        workspace_manager.read_file("marie", str(target))

        audit_file = shared_root / "audit" / "file_operations.jsonl"
        lines = audit_file.read_text().strip().split("\n")
        last_entry = json.loads(lines[-1])

        assert last_entry["username"] == "marie"
        assert last_entry["operation"] == "read"
        assert last_entry["success"] is True

    def test_denied_operation_logged(
        self, workspace_manager, marie_workspace, jean_workspace, shared_root
    ):
        """A denied operation is also logged."""
        jean_file = Path(jean_workspace) / "documents" / "secret.txt"
        jean_file.write_text("Secret")

        with pytest.raises(PermissionError):
            workspace_manager.read_file("marie", str(jean_file))

        audit_file = shared_root / "audit" / "file_operations.jsonl"
        lines = audit_file.read_text().strip().split("\n")
        last_entry = json.loads(lines[-1])

        assert last_entry["username"] == "marie"
        assert last_entry["operation"] == "read"
        assert last_entry["success"] is False
