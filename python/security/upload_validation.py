"""
Upload Validation Module - File Upload Security

Security Requirements:
- File extensions MUST be validated against allowlist
- File size MUST be limited
- MIME type MUST be verified (not just trusted from header)
- Executable files MUST be rejected
- Path traversal in filenames MUST be prevented
"""

import os
import mimetypes
from pathlib import Path
from typing import BinaryIO, Optional, Set, Tuple, Union
from io import BytesIO

from python.security.path_safety import SecurityError, sanitize_filename


# Configurable via environment
MAX_UPLOAD_SIZE = int(os.environ.get("MAX_UPLOAD_SIZE", str(10 * 1024 * 1024)))  # 10MB default

# Allowlist of safe file extensions (lowercase, without dot)
ALLOWED_EXTENSIONS: Set[str] = {
    # Documents
    "txt", "md", "pdf", "doc", "docx", "odt", "rtf",
    # Data
    "csv", "json", "xml", "yaml", "yml",
    # Images
    "png", "jpg", "jpeg", "gif", "webp", "svg", "ico",
    # Archives (if needed)
    "zip", "tar", "gz",
    # Code (read-only, for analysis)
    "py", "rs", "go", "java", "kt", "swift", "c", "cpp", "h",
    "ts", "tsx", "jsx", "vue", "svelte",
    "html", "css", "scss", "less",
    "sql", "sh", "bash", "zsh",
    "toml", "ini", "cfg", "conf",
}

# Explicitly blocked extensions (even if someone adds to allowlist)
BLOCKED_EXTENSIONS: Set[str] = {
    # Executables
    "exe", "dll", "so", "dylib", "bin", "com", "bat", "cmd", "msi",
    # Scripts that could be executed server-side
    "php", "php3", "php4", "php5", "phtml", "phar",
    "asp", "aspx", "jsp", "jspx",
    "cgi", "pl", "rb",
    # Other dangerous
    "htaccess", "htpasswd",
    "scr", "pif", "application", "gadget",
    "hta", "cpl", "msc", "jar",
}

# Magic bytes for common file types (for MIME sniffing)
MAGIC_BYTES = {
    b"\x89PNG\r\n\x1a\n": "image/png",
    b"\xff\xd8\xff": "image/jpeg",
    b"GIF87a": "image/gif",
    b"GIF89a": "image/gif",
    b"%PDF": "application/pdf",
    b"PK\x03\x04": "application/zip",
    b"\x1f\x8b": "application/gzip",
    b"RIFF": "audio/wav",  # or video/avi - need more bytes
    b"\x00\x00\x00": "video/mp4",  # ftyp box follows
}


class UploadValidationError(SecurityError):
    """Raised when file upload validation fails."""
    pass


def validate_upload(
    file: Union[BinaryIO, BytesIO],
    filename: str,
    *,
    allowed_extensions: Optional[Set[str]] = None,
    max_size: Optional[int] = None,
    check_mime: bool = True,
) -> Tuple[str, str, int]:
    """
    Validate an uploaded file for security.
    
    Args:
        file: File-like object to validate
        filename: Original filename from client
        allowed_extensions: Set of allowed extensions (default: ALLOWED_EXTENSIONS)
        max_size: Maximum file size in bytes (default: MAX_UPLOAD_SIZE)
        check_mime: Whether to verify MIME type matches extension
        
    Returns:
        Tuple of (safe_filename, detected_mime_type, file_size)
        
    Raises:
        UploadValidationError: If any validation fails
    """
    if allowed_extensions is None:
        allowed_extensions = ALLOWED_EXTENSIONS
    if max_size is None:
        max_size = MAX_UPLOAD_SIZE
    
    # 1. Validate and sanitize filename
    try:
        safe_name = sanitize_filename(filename)
    except SecurityError as e:
        raise UploadValidationError(f"Invalid filename: {e}")
    
    # 2. Check extension
    ext = _get_extension(safe_name)
    
    if ext in BLOCKED_EXTENSIONS:
        raise UploadValidationError(
            f"File type '{ext}' is explicitly blocked for security"
        )
    
    if ext not in allowed_extensions:
        raise UploadValidationError(
            f"File type '{ext}' is not in the allowed list"
        )
    
    # 3. Check file size
    file_size = _get_file_size(file)
    if file_size > max_size:
        raise UploadValidationError(
            f"File size ({file_size} bytes) exceeds maximum ({max_size} bytes)"
        )
    
    # 4. Verify MIME type if requested
    detected_mime = None
    if check_mime:
        detected_mime = _detect_mime_type(file, safe_name)
        expected_mime = _get_expected_mime(ext)
        
        if detected_mime and expected_mime:
            # Allow some flexibility (e.g., text/plain for various text files)
            if not _mime_types_compatible(detected_mime, expected_mime, ext):
                raise UploadValidationError(
                    f"MIME type mismatch: detected '{detected_mime}', "
                    f"expected '{expected_mime}' for extension '{ext}'"
                )
    
    return safe_name, detected_mime or "application/octet-stream", file_size


def _get_extension(filename: str) -> str:
    """Extract lowercase extension from filename."""
    if "." not in filename:
        return ""
    return filename.rsplit(".", 1)[1].lower()


def _get_file_size(file: Union[BinaryIO, BytesIO]) -> int:
    """Get file size without consuming the file."""
    current_pos = file.tell()
    file.seek(0, os.SEEK_END)
    size = file.tell()
    file.seek(current_pos)  # Reset to original position
    return size


def _detect_mime_type(file: Union[BinaryIO, BytesIO], filename: str) -> Optional[str]:
    """Detect MIME type from file content (magic bytes)."""
    current_pos = file.tell()
    file.seek(0)
    header = file.read(16)
    file.seek(current_pos)
    
    # Check magic bytes
    for magic, mime in MAGIC_BYTES.items():
        if header.startswith(magic):
            return mime
    
    # Fall back to extension-based detection
    mime_type, _ = mimetypes.guess_type(filename)
    return mime_type


def _get_expected_mime(ext: str) -> Optional[str]:
    """Get expected MIME type for an extension."""
    mime_type, _ = mimetypes.guess_type(f"file.{ext}")
    return mime_type


def _mime_types_compatible(detected: str, expected: str, ext: str) -> bool:
    """Check if detected MIME type is compatible with expected."""
    # Exact match
    if detected == expected:
        return True
    
    # Text files are flexible
    text_extensions = {"txt", "md", "csv", "json", "xml", "yaml", "yml", "html", "css"}
    if ext in text_extensions and detected.startswith("text/"):
        return True
    
    # Same major type (e.g., image/png vs image/jpeg for damaged files)
    # This is intentionally NOT allowed - we want strict matching
    
    return False


def is_extension_allowed(filename: str) -> bool:
    """Quick check if a filename has an allowed extension."""
    ext = _get_extension(filename)
    return ext in ALLOWED_EXTENSIONS and ext not in BLOCKED_EXTENSIONS


def get_blocked_extensions() -> Set[str]:
    """Return the set of blocked extensions."""
    return BLOCKED_EXTENSIONS.copy()
