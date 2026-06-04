#!/usr/bin/env python3
"""One-shot script: add TARMAC company + user to deploy/users.json.

Run on the server:
    cd PRISM-Oracle && python3 scripts/add_tarmac_user.py

This script is idempotent — safe to run multiple times.
"""

import json
import os
import sys

USERS_JSON = os.path.join(os.path.dirname(__file__), "..", "deploy", "users.json")

# Variable d'environnement portant le hash argon2id du compte (jamais en dur dans le
# code — SonarQube python:S2068). À générer hors dépôt, ex. :
#   python -c "from argon2 import PasswordHasher; print(PasswordHasher().hash('<pwd>'))"
PASSWORD_HASH_ENV = "TARMAC_PASSWORD_HASH"


def require_password_hash() -> str:
    """Retourne le hash depuis l'environnement, ou échoue (fail-closed)."""
    value = os.environ.get(PASSWORD_HASH_ENV, "").strip()
    if not value:
        print(
            f"ERROR: variable d'environnement {PASSWORD_HASH_ENV} absente.\n"
            f"Fournir le hash argon2id du compte, ex. :\n"
            f"  {PASSWORD_HASH_ENV}='$argon2id$...' python3 scripts/add_tarmac_user.py",
            file=sys.stderr,
        )
        sys.exit(2)
    if not value.startswith("$argon2"):
        print(
            f"ERROR: {PASSWORD_HASH_ENV} ne ressemble pas à un hash argon2 "
            f"(attendu un préfixe '$argon2...', pas un mot de passe en clair).",
            file=sys.stderr,
        )
        sys.exit(2)
    return value


def build_tarmac_user(password_hash: str) -> dict:
    return {
        "password_hash": password_hash,
        "role": "user",
        "organization": "TARMAC",
        "org_role": "OWNER",
        "profile": "TARMAC — Utilisateur",
    }


def main():
    tarmac_user = build_tarmac_user(require_password_hash())
    path = os.path.abspath(USERS_JSON)

    if not os.path.isfile(path):
        print(f"ERROR: {path} not found")
        sys.exit(1)

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    users = data.get("users", {})

    if "tarmac" in users:
        print("User 'tarmac' already exists — skipping")
        sys.exit(0)

    users["tarmac"] = tarmac_user
    data["users"] = users

    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")

    print(f"OK — user 'tarmac' (org: TARMAC, role: user) added to {path}")
    print("Restart the backend container to apply: docker restart evidence-backend")


if __name__ == "__main__":
    main()
