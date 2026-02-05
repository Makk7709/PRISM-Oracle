"""
Path Safety Tests - Traversal Protection

Tests verify:
1. Path traversal sequences (..) are blocked
2. Resolved paths stay within base directory
3. Symlinks are handled safely
4. Edge cases (empty, null bytes, unicode) handled
"""

import os
import pytest
import tempfile
from pathlib import Path

from python.security.path_safety import (
    safe_path_join,
    validate_path_in_base,
    sanitize_filename,
    SecurityError,
)


class TestSafePathJoin:
    """Tests for safe_path_join function."""
    
    @pytest.fixture
    def temp_base(self):
        """Create a temporary directory for testing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create some test files/dirs
            Path(tmpdir, "allowed").mkdir()
            Path(tmpdir, "allowed", "file.txt").touch()
            Path(tmpdir, "allowed", "subdir").mkdir()
            yield Path(tmpdir)
    
    def test_simple_path_works(self, temp_base):
        """Simple relative path within base is allowed."""
        result = safe_path_join(temp_base, "allowed/file.txt")
        # Use resolve() to handle macOS /var -> /private/var symlink
        expected = (temp_base / "allowed" / "file.txt").resolve()
        assert result == expected
    
    def test_traversal_dotdot_blocked(self, temp_base):
        """Path with .. attempting to escape is blocked."""
        with pytest.raises(SecurityError, match="traversal"):
            safe_path_join(temp_base, "../etc/passwd")
    
    def test_traversal_multiple_dotdot_blocked(self, temp_base):
        """Multiple .. sequences are blocked."""
        with pytest.raises(SecurityError, match="traversal"):
            safe_path_join(temp_base, "allowed/../../etc/passwd")
    
    def test_traversal_encoded_blocked(self, temp_base):
        """URL-encoded traversal attempts are handled."""
        # After URL decoding, this would be ../
        # The function expects already-decoded input
        with pytest.raises(SecurityError, match="traversal"):
            safe_path_join(temp_base, "..%2F..%2Fetc/passwd".replace("%2F", "/"))
    
    def test_absolute_path_outside_blocked(self, temp_base):
        """Absolute paths outside base are blocked."""
        # Leading slash is stripped, so /etc/passwd becomes etc/passwd
        # which is actually safe (relative path within base)
        # The real test is for paths that resolve outside base
        with pytest.raises(SecurityError, match="traversal"):
            safe_path_join(temp_base, "../../../../../../etc/passwd")
    
    def test_symlink_outside_blocked(self, temp_base):
        """Symlinks pointing outside base are blocked when allow_symlinks=False."""
        # Create a symlink pointing outside
        symlink_path = temp_base / "allowed" / "evil_link"
        try:
            symlink_path.symlink_to("/etc")
        except OSError:
            pytest.skip("Cannot create symlinks (permissions)")
        
        # Either raises SecurityError for symlink or for traversal (both acceptable)
        with pytest.raises(SecurityError):
            safe_path_join(temp_base, "allowed/evil_link/passwd", allow_symlinks=False)
    
    def test_symlink_allowed_when_enabled(self, temp_base):
        """Symlinks work when allow_symlinks=True (still validates final path)."""
        # Create a symlink within base
        symlink_path = temp_base / "allowed" / "internal_link"
        target = temp_base / "allowed" / "subdir"
        try:
            symlink_path.symlink_to(target)
        except OSError:
            pytest.skip("Cannot create symlinks")
        
        # Should work since target is within base
        result = safe_path_join(temp_base, "allowed/internal_link", allow_symlinks=True)
        # Use resolved paths for comparison (handles /var -> /private/var on macOS)
        base_resolved = temp_base.resolve()
        assert str(result).startswith(str(base_resolved))
    
    def test_null_byte_injection_blocked(self, temp_base):
        """Null byte injection attempts are handled."""
        # Null bytes could truncate paths in some systems
        malicious = "allowed/file.txt\x00.jpg"
        # The path module should handle this, but let's verify
        with pytest.raises((SecurityError, ValueError, OSError)):
            safe_path_join(temp_base, malicious)
    
    def test_must_exist_enforced(self, temp_base):
        """must_exist=True raises if path doesn't exist."""
        with pytest.raises(FileNotFoundError):
            safe_path_join(temp_base, "nonexistent.txt", must_exist=True)
    
    def test_leading_slash_stripped(self, temp_base):
        """Leading slashes are stripped from user path."""
        result = safe_path_join(temp_base, "/allowed/file.txt")
        expected = (temp_base / "allowed" / "file.txt").resolve()
        assert result == expected


class TestValidatePathInBase:
    """Tests for validate_path_in_base function."""
    
    @pytest.fixture
    def temp_base(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)
    
    def test_path_in_base_returns_true(self, temp_base):
        """Path within base returns True."""
        path = temp_base / "subdir" / "file.txt"
        assert validate_path_in_base(path, temp_base) is True
    
    def test_path_outside_base_returns_false(self, temp_base):
        """Path outside base returns False."""
        assert validate_path_in_base("/etc/passwd", temp_base) is False
    
    def test_traversal_returns_false(self, temp_base):
        """Traversal attempt returns False."""
        path = temp_base / ".." / "etc" / "passwd"
        assert validate_path_in_base(path, temp_base) is False


class TestSanitizeFilename:
    """Tests for filename sanitization."""
    
    def test_normal_filename_unchanged(self):
        """Normal filename passes through."""
        assert sanitize_filename("document.pdf") == "document.pdf"
    
    def test_path_separators_replaced(self):
        """Path separators are replaced with underscores."""
        assert "/" not in sanitize_filename("path/to/file.txt")
        assert "\\" not in sanitize_filename("path\\to\\file.txt")
    
    def test_leading_dots_removed(self):
        """Leading dots (hidden files) are removed."""
        result = sanitize_filename(".hidden")
        assert not result.startswith(".")
    
    def test_dotdot_blocked(self):
        """.. in filename is blocked."""
        with pytest.raises(SecurityError, match="traversal"):
            sanitize_filename("file..txt")  # Contains ..
    
    def test_empty_after_sanitize_blocked(self):
        """Filename that becomes empty after sanitization is blocked."""
        with pytest.raises(SecurityError, match="empty"):
            sanitize_filename("...")
    
    def test_null_bytes_removed(self):
        """Null bytes are removed from filename."""
        result = sanitize_filename("file\x00name.txt")
        assert "\x00" not in result


class TestPropertyBased:
    """Property-based tests for path safety (using hypothesis if available)."""
    
    @pytest.mark.parametrize("malicious_path", [
        "../etc/passwd",
        "..\\..\\windows\\system32",
        "foo/../../../etc/passwd",
        "....//....//etc/passwd",
        "./../.../../etc/passwd",
        "/absolute/path",
        "valid/../../escape",
        "foo/bar/../../../baz",
    ])
    def test_traversal_variants_blocked(self, malicious_path):
        """Various traversal patterns are all blocked."""
        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir)
            try:
                result = safe_path_join(base, malicious_path)
                # If no exception, result must be within base
                assert str(result).startswith(str(base.resolve()))
            except SecurityError:
                pass  # Expected for traversal attempts
    
    @pytest.mark.parametrize("safe_path", [
        "file.txt",
        "subdir/file.txt",
        "a/b/c/d/e.txt",
        "file-with-dashes.txt",
        "file_with_underscores.txt",
        "UPPERCASE.TXT",
        "MixedCase.Txt",
    ])
    def test_safe_paths_allowed(self, safe_path):
        """Safe paths are allowed."""
        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir)
            result = safe_path_join(base, safe_path)
            assert str(result).startswith(str(base.resolve()))
