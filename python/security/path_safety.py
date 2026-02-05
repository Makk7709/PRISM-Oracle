"""
Path Safety Module - Traversal Protection

Security Requirements:
- User-provided paths MUST be validated before use
- Path traversal sequences (..) MUST be neutralized
- Final resolved path MUST be within allowed base directory
- Symlinks MUST be handled safely (optionally rejected)
"""

import os
from pathlib import Path
from typing import Union, Optional


class SecurityError(Exception):
    """Raised when a security violation is detected."""
    pass


def safe_path_join(
    base_dir: Union[str, Path],
    user_path: Union[str, Path],
    *,
    allow_symlinks: bool = False,
    must_exist: bool = False,
) -> Path:
    """
    Safely join a base directory with a user-provided path.
    
    This function prevents path traversal attacks by ensuring
    the resulting path is within the base directory.
    
    Args:
        base_dir: The trusted base directory
        user_path: The untrusted user-provided path component
        allow_symlinks: If False, reject paths containing symlinks
        must_exist: If True, verify the path exists
        
    Returns:
        The resolved absolute path within base_dir
        
    Raises:
        SecurityError: If path would escape base_dir
        SecurityError: If symlink detected and allow_symlinks=False
        FileNotFoundError: If must_exist=True and path doesn't exist
        
    Examples:
        >>> safe_path_join("/app/data", "file.txt")
        PosixPath('/app/data/file.txt')
        
        >>> safe_path_join("/app/data", "../etc/passwd")
        SecurityError: Path traversal detected
    """
    # Normalize base directory
    base = Path(base_dir).resolve()
    
    # Clean user path - remove leading slashes and normalize
    user_path_str = str(user_path).lstrip("/\\")
    
    # Check for obvious traversal attempts before joining
    if ".." in user_path_str:
        # Could be legitimate (e.g., "foo/../bar"), so we still resolve
        # but we'll check the result
        pass
    
    # Join and resolve
    try:
        # Use os.path.normpath first to handle .. sequences
        joined = base / user_path_str
        resolved = joined.resolve()
    except (OSError, ValueError) as e:
        raise SecurityError(f"Invalid path: {e}")
    
    # CRITICAL: Verify resolved path is within base directory
    try:
        resolved.relative_to(base)
    except ValueError:
        raise SecurityError(
            f"Path traversal detected: '{user_path}' escapes base directory"
        )
    
    # Check for symlinks if not allowed
    if not allow_symlinks:
        # Check each component of the path for symlinks
        current = base
        for part in Path(user_path_str).parts:
            current = current / part
            if current.is_symlink():
                raise SecurityError(
                    f"Symlink detected in path: {current}"
                )
    
    # Check existence if required
    if must_exist and not resolved.exists():
        raise FileNotFoundError(f"Path does not exist: {resolved}")
    
    return resolved


def validate_path_in_base(
    path: Union[str, Path],
    base_dir: Union[str, Path],
) -> bool:
    """
    Validate that a path is within a base directory.
    
    Args:
        path: Path to validate (can be absolute or relative)
        base_dir: The allowed base directory
        
    Returns:
        True if path is within base_dir, False otherwise
    """
    try:
        base = Path(base_dir).resolve()
        target = Path(path).resolve()
        target.relative_to(base)
        return True
    except (ValueError, OSError):
        return False


def sanitize_filename(filename: str) -> str:
    """
    Sanitize a filename to prevent directory traversal and other issues.
    
    Args:
        filename: The untrusted filename
        
    Returns:
        A safe filename with dangerous characters removed
        
    Raises:
        SecurityError: If filename is empty after sanitization
    """
    if not filename:
        raise SecurityError("Filename cannot be empty")
    
    # Remove path separators
    filename = filename.replace("/", "_").replace("\\", "_")
    
    # Remove null bytes
    filename = filename.replace("\x00", "")
    
    # Remove leading dots (hidden files / parent dir)
    while filename.startswith("."):
        filename = filename[1:]
    
    # Remove trailing dots and spaces (Windows issues)
    filename = filename.rstrip(". ")
    
    # Reject if empty after sanitization
    if not filename:
        raise SecurityError("Filename is empty after sanitization")
    
    # Reject if still contains traversal patterns
    if ".." in filename:
        raise SecurityError("Filename contains traversal pattern")
    
    return filename


def get_safe_relative_path(
    full_path: Union[str, Path],
    base_dir: Union[str, Path],
) -> str:
    """
    Get the relative path from base_dir, safely.
    
    Args:
        full_path: The full path
        base_dir: The base directory
        
    Returns:
        The relative path as a string
        
    Raises:
        SecurityError: If full_path is not within base_dir
    """
    base = Path(base_dir).resolve()
    target = Path(full_path).resolve()
    
    try:
        return str(target.relative_to(base))
    except ValueError:
        raise SecurityError(
            f"Path {full_path} is not within base directory {base_dir}"
        )
