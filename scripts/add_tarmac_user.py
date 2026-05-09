#!/usr/bin/env python3
"""Demo/example script: add a sanitized example user to deploy/users.json.

Demo/example only. No real user, no real hash, no production data.
Not intended for deployment.

Historical note: this file's name (`add_tarmac_user.py`) reflects the original
provisioning use case. Its contents have been fully sanitized for the external
transmission branch `diag-grow/transmission-evidence`. All real client data
(organization name, real password hash, real username and profile) have been
replaced with explicit placeholders. The script remains operational structurally
(idempotent JSON merge) but will never produce a working authentication: the
hash placeholder below is not a valid Argon2id output.

To re-establish a working provisioning script for any real deployment:
    1. Generate a real Argon2id hash via `scripts/hash_password.py`.
    2. Replace the placeholder in `DEMO_USER` with the new hash.
    3. Replace `demo_user`, `ExampleOrg`, and the demo profile with the
       real values, ideally outside of git (e.g. via environment variables).

Run on the server (will not produce working auth as-is):
    cd KOREV_Oracle && python3 scripts/add_tarmac_user.py

This script is idempotent — safe to run multiple times.
"""

import json
import os
import sys

USERS_JSON = os.path.join(os.path.dirname(__file__), "..", "deploy", "users.json")

DEMO_USER = {
    "password_hash": "$argon2id$PLACEHOLDER_NOT_A_VALID_HASH",
    "role": "user",
    "organization": "ExampleOrg",
    "org_role": "OWNER",
    "profile": "Demo User — Example",
}


def main():
    path = os.path.abspath(USERS_JSON)

    if not os.path.isfile(path):
        print(f"ERROR: {path} not found")
        sys.exit(1)

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    users = data.get("users", {})

    if "demo_user" in users:
        print("User 'demo_user' already exists — skipping")
        sys.exit(0)

    users["demo_user"] = DEMO_USER
    data["users"] = users

    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")

    print(f"OK — example user 'demo_user' (org: ExampleOrg, role: user) added to {path}")
    print("WARNING: the password_hash is a placeholder. Authentication will fail.")
    print("Restart the backend container to apply: docker restart evidence-backend")


if __name__ == "__main__":
    main()
