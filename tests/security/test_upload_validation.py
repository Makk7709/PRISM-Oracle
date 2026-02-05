"""
Upload Validation Tests - File Upload Security

Tests verify:
1. Dangerous extensions are blocked
2. File size limits are enforced
3. MIME type sniffing works
4. Path traversal in filenames blocked
"""

import io
import pytest

from python.security.upload_validation import (
    validate_upload,
    is_extension_allowed,
    ALLOWED_EXTENSIONS,
    BLOCKED_EXTENSIONS,
    MAX_UPLOAD_SIZE,
    UploadValidationError,
)


class TestExtensionValidation:
    """Tests for file extension validation."""
    
    @pytest.mark.parametrize("ext", ["exe", "dll", "php", "jsp", "bat", "cmd", "msi"])
    def test_executable_extensions_blocked(self, ext):
        """Executable file extensions are blocked."""
        file = io.BytesIO(b"fake content")
        filename = f"malicious.{ext}"
        
        with pytest.raises(UploadValidationError, match="blocked"):
            validate_upload(file, filename)
    
    @pytest.mark.parametrize("ext", ["php3", "php4", "php5", "phtml", "phar"])
    def test_php_variants_blocked(self, ext):
        """All PHP variants are blocked."""
        file = io.BytesIO(b"<?php evil(); ?>")
        filename = f"backdoor.{ext}"
        
        with pytest.raises(UploadValidationError, match="blocked"):
            validate_upload(file, filename)
    
    @pytest.mark.parametrize("ext", ["txt", "pdf", "png", "jpg", "json", "md"])
    def test_safe_extensions_allowed(self, ext):
        """Safe file extensions are allowed."""
        file = io.BytesIO(b"safe content")
        filename = f"document.{ext}"
        
        # Should not raise
        safe_name, mime, size = validate_upload(file, filename, check_mime=False)
        assert safe_name == filename
    
    def test_double_extension_checked(self):
        """Double extensions like .php.txt are handled."""
        file = io.BytesIO(b"content")
        # The final extension is what matters
        safe_name, _, _ = validate_upload(file, "file.php.txt", check_mime=False)
        assert safe_name == "file.php.txt"  # .txt is the extension
    
    def test_is_extension_allowed_helper(self):
        """is_extension_allowed helper function works."""
        assert is_extension_allowed("document.pdf") is True
        assert is_extension_allowed("script.exe") is False
        assert is_extension_allowed("no_extension") is False


class TestFileSizeValidation:
    """Tests for file size limits."""
    
    def test_file_under_limit_allowed(self):
        """Files under the size limit are allowed."""
        small_file = io.BytesIO(b"x" * 1000)  # 1KB
        
        safe_name, _, size = validate_upload(small_file, "small.txt", check_mime=False)
        assert size == 1000
    
    def test_file_over_limit_blocked(self):
        """Files over the size limit are blocked."""
        large_file = io.BytesIO(b"x" * (MAX_UPLOAD_SIZE + 1))
        
        with pytest.raises(UploadValidationError, match="exceeds maximum"):
            validate_upload(large_file, "large.txt")
    
    def test_custom_size_limit(self):
        """Custom size limit can be specified."""
        file = io.BytesIO(b"x" * 1000)
        
        with pytest.raises(UploadValidationError, match="exceeds maximum"):
            validate_upload(file, "file.txt", max_size=500)
    
    def test_file_exactly_at_limit(self):
        """File exactly at limit is allowed."""
        file = io.BytesIO(b"x" * 1000)
        
        # Should not raise with exact limit
        validate_upload(file, "exact.txt", max_size=1000, check_mime=False)


class TestMimeValidation:
    """Tests for MIME type validation."""
    
    def test_png_magic_bytes_detected(self):
        """PNG files are detected by magic bytes."""
        # PNG magic bytes
        png_data = b"\x89PNG\r\n\x1a\n" + b"\x00" * 100
        file = io.BytesIO(png_data)
        
        _, mime, _ = validate_upload(file, "image.png")
        assert mime == "image/png"
    
    def test_jpeg_magic_bytes_detected(self):
        """JPEG files are detected by magic bytes."""
        # JPEG magic bytes
        jpeg_data = b"\xff\xd8\xff" + b"\x00" * 100
        file = io.BytesIO(jpeg_data)
        
        _, mime, _ = validate_upload(file, "image.jpg")
        assert mime == "image/jpeg"
    
    def test_mime_mismatch_blocked(self):
        """Files with mismatched MIME type and extension are blocked."""
        # PNG content but .jpg extension
        png_data = b"\x89PNG\r\n\x1a\n" + b"\x00" * 100
        file = io.BytesIO(png_data)
        
        with pytest.raises(UploadValidationError, match="[Mm][Ii][Mm][Ee]"):
            validate_upload(file, "fake.jpg", check_mime=True)
    
    def test_mime_check_can_be_disabled(self):
        """MIME checking can be disabled."""
        png_data = b"\x89PNG\r\n\x1a\n" + b"\x00" * 100
        file = io.BytesIO(png_data)
        
        # Should not raise even with wrong extension
        validate_upload(file, "fake.txt", check_mime=False)


class TestFilenameValidation:
    """Tests for filename sanitization in uploads."""
    
    def test_path_traversal_in_filename_blocked(self):
        """Path traversal in filename is blocked."""
        file = io.BytesIO(b"content")
        
        # Path traversal should be rejected entirely
        with pytest.raises(UploadValidationError, match="filename|traversal"):
            validate_upload(file, "../../../etc/passwd.txt", check_mime=False)
    
    def test_hidden_file_blocked(self):
        """Hidden files (starting with .) are blocked."""
        file = io.BytesIO(b"content")
        
        # .htaccess should be blocked (no valid extension after sanitization)
        with pytest.raises(UploadValidationError):
            validate_upload(file, ".htaccess", check_mime=False)
    
    def test_null_byte_injection_handled(self):
        """Null bytes in filename are handled."""
        file = io.BytesIO(b"content")
        
        # Either sanitizes or raises
        try:
            safe_name, _, _ = validate_upload(file, "file\x00.exe.txt", check_mime=False)
            assert "\x00" not in safe_name
        except UploadValidationError:
            pass  # Also acceptable


class TestBlockedExtensions:
    """Verify BLOCKED_EXTENSIONS contains dangerous types."""
    
    def test_executables_in_blocklist(self):
        """Common executable extensions are blocked."""
        dangerous = ["exe", "dll", "bat", "cmd", "com", "msi", "scr"]
        for ext in dangerous:
            assert ext in BLOCKED_EXTENSIONS, f"{ext} should be blocked"
    
    def test_server_scripts_in_blocklist(self):
        """Server-side script extensions are blocked."""
        scripts = ["php", "asp", "aspx", "jsp", "cgi"]
        for ext in scripts:
            assert ext in BLOCKED_EXTENSIONS, f"{ext} should be blocked"
    
    def test_blocklist_takes_precedence(self):
        """Blocked extensions are rejected even if in allowlist."""
        # Simulate someone accidentally adding exe to allowlist
        file = io.BytesIO(b"MZ" + b"\x00" * 100)  # PE header start
        
        # Create custom allowlist including exe
        custom_allow = ALLOWED_EXTENSIONS | {"exe"}
        
        # Should still be blocked because BLOCKED_EXTENSIONS takes precedence
        with pytest.raises(UploadValidationError, match="blocked"):
            validate_upload(file, "malware.exe", allowed_extensions=custom_allow)


class TestEdgeCases:
    """Edge case tests."""
    
    def test_empty_filename_rejected(self):
        """Empty filename is rejected."""
        file = io.BytesIO(b"content")
        
        with pytest.raises(UploadValidationError, match="[Ff]ilename"):
            validate_upload(file, "")
    
    def test_only_extension_filename_blocked(self):
        """Filename that is only an extension is blocked."""
        file = io.BytesIO(b"content")
        
        # ".txt" has no valid extension after leading dot removal
        with pytest.raises(UploadValidationError):
            validate_upload(file, ".txt", check_mime=False)
    
    def test_very_long_filename_handled(self):
        """Very long filenames are handled."""
        file = io.BytesIO(b"content")
        long_name = "a" * 300 + ".txt"
        
        # Should either truncate or accept (not crash)
        safe_name, _, _ = validate_upload(file, long_name, check_mime=False)
        assert safe_name.endswith(".txt")
