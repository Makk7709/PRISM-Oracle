#!/usr/bin/env python3
"""
Rollback helper: export identity DB records back to deploy/users.json format.
"""
import json
import sqlite3
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
USERS_JSON = ROOT / "deploy" / "users.json"
DB_PATH = ROOT / "data" / "security" / "identity.db"


def main() -> None:
    if not DB_PATH.exists():
        raise SystemExit(f"Missing DB: {DB_PATH}")
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(
            """
            SELECT u.username, u.password_hash, u.system_role, m.organization_id, m.org_role
            FROM users u
            LEFT JOIN memberships m ON m.user_id = u.id
            WHERE u.status = 'active'
            """
        ).fetchall()
    finally:
        conn.close()

    output = {"users": {}}
    for row in rows:
        username = row["username"]
        output["users"][username] = {
            "password_hash": row["password_hash"],
            "role": row["system_role"],
            "organization": row["organization_id"],
            "org_role": row["org_role"] or "MEMBER",
        }

    USERS_JSON.write_text(json.dumps(output, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Rollback export written to {USERS_JSON}")


if __name__ == "__main__":
    main()
