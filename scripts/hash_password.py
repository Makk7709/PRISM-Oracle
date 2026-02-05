#!/usr/bin/env python3
"""
Password Hashing Utility - Argon2id

Usage:
    python scripts/hash_password.py
    python scripts/hash_password.py "mypassword"
    
The output can be used directly in .env as AUTH_PASSWORD.

Example:
    $ python scripts/hash_password.py "my_secure_password"
    $argon2id$v=19$m=65536,t=3,p=4$randomsalt$hash...

Then in .env:
    AUTH_PASSWORD=$argon2id$v=19$m=65536,t=3,p=4$randomsalt$hash...
"""

import sys
import getpass
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from python.security.auth import hash_password, verify_password, is_password_hashed


def main():
    if len(sys.argv) > 1:
        password = sys.argv[1]
    else:
        print("Password Hashing Utility (Argon2id)")
        print("=" * 40)
        password = getpass.getpass("Enter password to hash: ")
        confirm = getpass.getpass("Confirm password: ")
        
        if password != confirm:
            print("ERROR: Passwords do not match")
            sys.exit(1)
    
    if not password:
        print("ERROR: Password cannot be empty")
        sys.exit(1)
    
    # Generate hash
    hashed = hash_password(password)
    
    print("\n" + "=" * 60)
    print("ARGON2ID HASH (copy this to AUTH_PASSWORD in .env):")
    print("=" * 60)
    print(hashed)
    print("=" * 60)
    
    # Verify it works
    if verify_password(hashed, password):
        print("\n✓ Verification: PASS")
    else:
        print("\n✗ Verification: FAIL (this should not happen)")
        sys.exit(1)
    
    print("\nUsage in .env:")
    print(f"AUTH_PASSWORD={hashed}")


if __name__ == "__main__":
    main()
