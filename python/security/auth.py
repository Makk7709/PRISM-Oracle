"""
Password Hashing Module - Argon2-based

Security Requirements:
- Passwords MUST be hashed with Argon2id (memory-hard)
- Verification MUST be timing-safe
- Plaintext passwords MUST NEVER be stored
- Hash parameters: time_cost=3, memory_cost=65536, parallelism=4
"""

import os
import hmac
from typing import Optional

# Use argon2-cffi library
try:
    from argon2 import PasswordHasher, Type
    from argon2.exceptions import VerifyMismatchError, InvalidHashError
    ARGON2_AVAILABLE = True
except ImportError:
    ARGON2_AVAILABLE = False


# Argon2 configuration - OWASP recommended parameters
ARGON2_TIME_COST = int(os.environ.get("ARGON2_TIME_COST", "3"))
ARGON2_MEMORY_COST = int(os.environ.get("ARGON2_MEMORY_COST", "65536"))  # 64MB
ARGON2_PARALLELISM = int(os.environ.get("ARGON2_PARALLELISM", "4"))


def _get_hasher() -> "PasswordHasher":
    """Get configured Argon2 hasher instance."""
    if not ARGON2_AVAILABLE:
        raise RuntimeError(
            "argon2-cffi not installed. Run: pip install argon2-cffi"
        )
    return PasswordHasher(
        time_cost=ARGON2_TIME_COST,
        memory_cost=ARGON2_MEMORY_COST,
        parallelism=ARGON2_PARALLELISM,
        type=Type.ID,  # Argon2id - recommended variant
    )


def hash_password(password: str) -> str:
    """
    Hash a password using Argon2id.
    
    Args:
        password: Plaintext password to hash
        
    Returns:
        Argon2 hash string (contains salt, parameters, and hash)
        
    Raises:
        ValueError: If password is empty or None
        RuntimeError: If argon2-cffi is not installed
    """
    if not password:
        raise ValueError("Password cannot be empty")
    
    hasher = _get_hasher()
    return hasher.hash(password)


def verify_password(stored_hash: str, password: str) -> bool:
    """
    Verify a password against a stored hash (timing-safe).
    
    Args:
        stored_hash: The Argon2 hash from storage
        password: The plaintext password to verify
        
    Returns:
        True if password matches, False otherwise
        
    Note:
        This function is designed to be timing-safe to prevent
        timing attacks. It will take approximately the same time
        whether the password is correct or not.
    """
    if not stored_hash or not password:
        # Still do a dummy hash to maintain constant time
        _dummy_verify()
        return False
    
    if not is_password_hashed(stored_hash):
        # Password stored in plaintext - SECURITY VIOLATION
        # Still verify in constant time but log warning
        _dummy_verify()
        return False
    
    hasher = _get_hasher()
    try:
        hasher.verify(stored_hash, password)
        return True
    except (VerifyMismatchError, InvalidHashError):
        return False


def is_password_hashed(value: str) -> bool:
    """
    Check if a value appears to be an Argon2 hash.
    
    Args:
        value: String to check
        
    Returns:
        True if value looks like an Argon2 hash
    """
    if not value or not isinstance(value, str):
        return False
    # Argon2 hashes start with $argon2id$, $argon2i$, or $argon2d$
    return value.startswith(("$argon2id$", "$argon2i$", "$argon2d$"))


def _dummy_verify() -> None:
    """
    Perform a dummy hash operation to maintain constant time
    even when early-returning from verify_password.
    """
    if ARGON2_AVAILABLE:
        try:
            hasher = _get_hasher()
            # Hash a dummy password to consume time
            hasher.hash("dummy_password_for_timing")
        except Exception:
            pass


def needs_rehash(stored_hash: str) -> bool:
    """
    Check if a hash needs to be rehashed (parameters changed).
    
    Args:
        stored_hash: The stored Argon2 hash
        
    Returns:
        True if hash should be regenerated with new parameters
    """
    if not is_password_hashed(stored_hash):
        return True
    
    hasher = _get_hasher()
    try:
        return hasher.check_needs_rehash(stored_hash)
    except Exception:
        return True
