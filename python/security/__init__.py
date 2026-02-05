"""
KOREV Evidence Security Module - Phase 1 P0

This module provides security primitives for:
- Password hashing (Argon2)
- Rate limiting
- Path validation (traversal protection)
- File upload validation
- Shell command sanitization

Security Specifications (Given/When/Then):

## 1. Password Hashing (AUTH)
Given: A plaintext password
When: hash_password() is called
Then: Returns an Argon2 hash that:
  - Is NOT equal to the original password
  - Contains the "$argon2" prefix
  - Can be verified with verify_password()

Given: A hash and correct password
When: verify_password() is called
Then: Returns True in constant time

Given: A hash and incorrect password  
When: verify_password() is called
Then: Returns False in constant time (timing-safe)

## 2. Rate Limiting
Given: An IP address making requests to /login
When: More than N requests are made within T seconds
Then: Returns 429 Too Many Requests
Invariant: Limit is configurable via ENV (RATE_LIMIT_LOGIN)

## 3. Path Validation (TRAVERSAL)
Given: A user-provided path containing ".."
When: safe_path_join(base, user_path) is called
Then: Raises SecurityError OR returns path within base
Invariant: Final resolved path MUST start with base directory

Given: A symlink pointing outside base directory
When: safe_path_join() with follow_symlinks=False
Then: Raises SecurityError

## 4. File Upload Validation
Given: A file with dangerous extension (.exe, .php, .js)
When: validate_upload() is called
Then: Returns False / raises SecurityError

Given: A file exceeding MAX_UPLOAD_SIZE
When: validate_upload() is called
Then: Returns False / raises SecurityError

Given: A file with mismatched MIME type and extension
When: validate_upload() is called
Then: Returns False / raises SecurityError

## 5. Shell Command Safety
Given: A command string with shell metacharacters (;|&$`")
When: validate_command() is called
Then: Raises SecurityError

Given: A command not in the allowlist
When: execute_safe_command() is called
Then: Raises SecurityError

Invariant: NEVER use create_subprocess_shell
Invariant: Commands passed as list, not string
"""

from python.security.auth import (
    hash_password,
    verify_password,
    is_password_hashed,
)
from python.security.path_safety import (
    safe_path_join,
    validate_path_in_base,
    SecurityError,
)
from python.security.upload_validation import (
    validate_upload,
    ALLOWED_EXTENSIONS,
    MAX_UPLOAD_SIZE,
)
from python.security.shell_safety import (
    validate_command,
    build_safe_command,
    COMMAND_ALLOWLIST,
)

__all__ = [
    # Auth
    "hash_password",
    "verify_password", 
    "is_password_hashed",
    # Path safety
    "safe_path_join",
    "validate_path_in_base",
    "SecurityError",
    # Upload
    "validate_upload",
    "ALLOWED_EXTENSIONS",
    "MAX_UPLOAD_SIZE",
    # Shell
    "validate_command",
    "build_safe_command",
    "COMMAND_ALLOWLIST",
]
