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

TARMAC_USER = {
    "password_hash": "$argon2id$v=19$m=65536,t=3,p=4$3+ZCWqfPXQU7oHuWVBC5bA$Jqe4rKaK6A8BEFRk8OyhXQX09yKc7/zysZOvEabOU6A",
    "role": "user",
    "organization": "TARMAC",
    "org_role": "OWNER",
    "profile": "TARMAC — Utilisateur",
}


def main():
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

    users["tarmac"] = TARMAC_USER
    data["users"] = users

    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")

    print(f"OK — user 'tarmac' (org: TARMAC, role: user) added to {path}")
    print("Restart the backend container to apply: docker restart evidence-backend")


if __name__ == "__main__":
    main()
