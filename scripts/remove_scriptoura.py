#!/usr/bin/env python3
"""One-shot script: remove Scriptoura entity and affiliated accounts (mathias, louis).

Run on the server:
    cd PRISM-Oracle && python3 scripts/remove_scriptoura.py

This script is idempotent — safe to run multiple times.
"""

import json
import os
import sys

USERS_JSON = os.path.join(os.path.dirname(__file__), "..", "deploy", "users.json")

USERS_TO_REMOVE = ["mathias", "louis"]
ORG_TO_REMOVE = "Scriptoura"


def main():
    path = os.path.abspath(USERS_JSON)

    if not os.path.isfile(path):
        print(f"ERROR: {path} not found")
        sys.exit(1)

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    users = data.get("users", {})
    removed = []

    for username in USERS_TO_REMOVE:
        if username in users:
            org = users[username].get("organization", "N/A")
            del users[username]
            removed.append(f"{username} (org: {org})")

    for username in list(users.keys()):
        if users[username].get("organization", "").lower() == ORG_TO_REMOVE.lower():
            del users[username]
            removed.append(f"{username} (org: {ORG_TO_REMOVE})")

    if not removed:
        print("Nothing to remove — users mathias/louis not found")
        sys.exit(0)

    data["users"] = users

    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")

    print(f"OK — removed {len(removed)} account(s):")
    for r in removed:
        print(f"  - {r}")
    print(f"\nUpdated: {path}")
    print("Restart the backend container to apply: docker restart evidence-backend")


if __name__ == "__main__":
    main()
