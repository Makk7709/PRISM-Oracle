#!/usr/bin/env python3
"""
Bootstrap identity DB from deploy/users.json.

This script is intentionally idempotent and safe to rerun.
"""
import json
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
USERS_JSON = ROOT / "deploy" / "users.json"
DB_PATH = ROOT / "data" / "security" / "identity.db"
SCHEMA_SQL = ROOT / "scripts" / "migrations" / "0001_identity_schema.sql"


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def ensure_schema(conn: sqlite3.Connection) -> None:
    sql = SCHEMA_SQL.read_text(encoding="utf-8")
    conn.executescript(sql)
    conn.commit()


def upsert_identity(conn: sqlite3.Connection, users: dict) -> None:
    for username, info in users.items():
        org_id = info.get("organization")
        org_name = org_id or "unassigned"
        org_role = info.get("org_role", "MEMBER")
        user_id = f"user:{username}"
        membership_id = f"membership:{username}:{org_name}"
        now = now_iso()

        conn.execute(
            """
            INSERT INTO organizations(id, name, created_at)
            VALUES(?, ?, ?)
            ON CONFLICT(id) DO NOTHING
            """,
            (org_name, org_name, now),
        )
        conn.execute(
            """
            INSERT INTO users(id, username, password_hash, system_role, status, created_at, updated_at)
            VALUES(?, ?, ?, ?, 'active', ?, ?)
            ON CONFLICT(username) DO UPDATE SET
                password_hash=excluded.password_hash,
                system_role=excluded.system_role,
                updated_at=excluded.updated_at
            """,
            (
                user_id,
                username,
                info.get("password_hash", ""),
                info.get("role", "user"),
                now,
                now,
            ),
        )
        conn.execute(
            """
            INSERT INTO memberships(id, user_id, organization_id, org_role, created_at)
            VALUES(?, ?, ?, ?, ?)
            ON CONFLICT(user_id, organization_id) DO UPDATE SET
                org_role=excluded.org_role
            """,
            (membership_id, user_id, org_name, org_role, now),
        )
    conn.commit()


def main() -> None:
    if not USERS_JSON.exists():
        raise SystemExit(f"Missing users.json: {USERS_JSON}")
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    data = json.loads(USERS_JSON.read_text(encoding="utf-8"))
    users = data.get("users", {})
    conn = sqlite3.connect(DB_PATH)
    try:
        ensure_schema(conn)
        upsert_identity(conn, users)
        print(f"Migrated {len(users)} users into {DB_PATH}")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
