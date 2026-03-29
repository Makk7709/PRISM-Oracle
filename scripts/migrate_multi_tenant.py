#!/usr/bin/env python3
"""
Multi-tenant migration script.

Phase 3: Delete christopher account and all associated data.
Phase 4: Assign organization field to all existing chats and tasks.

Run inside Docker container:
  docker exec -it evidence-backend python scripts/migrate_multi_tenant.py
"""
import json
import os
import shutil
import sys

ORG_MAP: dict[str, str] = {
    "amine": "korev-ai",
    "aya": "korev-ai",
    "nicolas": "dica-france",
    "luc": "dica-france",
    "jeremie": "dica-france",
    "coralie": "dica-france",
    "dominique": "dica-france",
    "laurianne": "dica-france",
    "sarah": "dica-france",
    "louis": "scriptoura",
    "mathias": "scriptoura",
}

ORG_ROLE_MAP: dict[str, str] = {
    "amine": "OWNER",
    "aya": "MEMBER",
    "nicolas": "OWNER",
    "luc": "MEMBER",
    "jeremie": "MEMBER",
    "coralie": "MEMBER",
    "dominique": "MEMBER",
    "laurianne": "MEMBER",
    "sarah": "MEMBER",
    "louis": "OWNER",
    "mathias": "MEMBER",
}

DELETE_USERS = ["christopher"]

BASE_DIR = os.environ.get("EVIDENCE_BASE_DIR", "/app")
CHATS_DIR = os.path.join(BASE_DIR, "tmp", "chats")
TASKS_FILE = os.path.join(BASE_DIR, "tmp", "scheduler", "tasks.json")
USERS_FILE = os.path.join(BASE_DIR, "deploy", "users.json")
USERS_DIR = os.path.join(BASE_DIR, "shared", "users")


def migrate_users_json() -> None:
    """Add organization and org_role to users.json; remove deleted users."""
    if not os.path.exists(USERS_FILE):
        print(f"[SKIP] users.json not found at {USERS_FILE}")
        return

    with open(USERS_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    users = data.get("users", {})
    changed = False

    for username in DELETE_USERS:
        if username in users:
            del users[username]
            print(f"[DELETE] Removed user '{username}' from users.json")
            changed = True

    for username, info in users.items():
        org = ORG_MAP.get(username)
        org_role = ORG_ROLE_MAP.get(username, "MEMBER")
        if org and info.get("organization") != org:
            info["organization"] = org
            changed = True
        if org_role and info.get("org_role") != org_role:
            info["org_role"] = org_role
            changed = True
        if changed:
            print(f"[UPDATE] {username} -> org={org}, org_role={org_role}")

    if changed:
        data["users"] = users
        with open(USERS_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"[SAVED] {USERS_FILE}")
    else:
        print("[SKIP] users.json already up to date")


def delete_christopher_data() -> None:
    """Remove all data belonging to deleted users."""
    for username in DELETE_USERS:
        user_dir = os.path.join(USERS_DIR, username)
        if os.path.exists(user_dir):
            shutil.rmtree(user_dir)
            print(f"[DELETE] Removed workspace directory: {user_dir}")

        if os.path.exists(CHATS_DIR):
            for folder in os.listdir(CHATS_DIR):
                chat_file = os.path.join(CHATS_DIR, folder, "chat.json")
                if os.path.exists(chat_file):
                    try:
                        with open(chat_file, "r", encoding="utf-8") as f:
                            chat_data = json.load(f)
                        if chat_data.get("username") == username:
                            chat_path = os.path.join(CHATS_DIR, folder)
                            shutil.rmtree(chat_path)
                            print(f"[DELETE] Removed chat: {folder} (owner: {username})")
                    except (json.JSONDecodeError, OSError):
                        pass

        if os.path.exists(TASKS_FILE):
            try:
                with open(TASKS_FILE, "r", encoding="utf-8") as f:
                    raw = json.load(f)
                if isinstance(raw, dict) and "tasks" in raw:
                    tasks_list = raw["tasks"]
                elif isinstance(raw, list):
                    tasks_list = raw
                else:
                    tasks_list = []
                original_count = len(tasks_list)
                tasks_list = [
                    t for t in tasks_list
                    if not isinstance(t, dict) or t.get("username") != username
                ]
                removed = original_count - len(tasks_list)
                if removed > 0:
                    if isinstance(raw, dict) and "tasks" in raw:
                        raw["tasks"] = tasks_list
                    else:
                        raw = tasks_list
                    with open(TASKS_FILE, "w", encoding="utf-8") as f:
                        json.dump(raw, f, indent=2, ensure_ascii=False)
                    print(f"[DELETE] Removed {removed} tasks owned by '{username}'")
            except (json.JSONDecodeError, OSError):
                pass


def migrate_chats() -> None:
    """Add organization field to all persisted chats."""
    if not os.path.exists(CHATS_DIR):
        print(f"[SKIP] Chats directory not found: {CHATS_DIR}")
        return

    migrated = 0
    for folder in os.listdir(CHATS_DIR):
        chat_file = os.path.join(CHATS_DIR, folder, "chat.json")
        if not os.path.exists(chat_file):
            continue
        try:
            with open(chat_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            username = data.get("username")
            if not username:
                continue
            org = ORG_MAP.get(username)
            if org and data.get("organization") != org:
                data["organization"] = org
                with open(chat_file, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)
                migrated += 1
        except (json.JSONDecodeError, OSError) as e:
            print(f"[ERROR] Failed to migrate chat {folder}: {e}")

    print(f"[MIGRATE] Updated {migrated} chats with organization field")


def migrate_tasks() -> None:
    """Add organization field to all persisted tasks."""
    if not os.path.exists(TASKS_FILE):
        print(f"[SKIP] Tasks file not found: {TASKS_FILE}")
        return

    try:
        with open(TASKS_FILE, "r", encoding="utf-8") as f:
            raw = json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        print(f"[ERROR] Failed to read tasks file: {e}")
        return

    if isinstance(raw, dict) and "tasks" in raw:
        tasks_list = raw["tasks"]
    elif isinstance(raw, list):
        tasks_list = raw
    else:
        print("[SKIP] Unexpected tasks file format")
        return

    migrated = 0
    for task in tasks_list:
        if not isinstance(task, dict):
            continue
        username = task.get("username")
        if not username:
            continue
        org = ORG_MAP.get(username)
        if org and task.get("organization") != org:
            task["organization"] = org
            migrated += 1

    if migrated > 0:
        if isinstance(raw, dict) and "tasks" in raw:
            raw["tasks"] = tasks_list
        else:
            raw = tasks_list
        with open(TASKS_FILE, "w", encoding="utf-8") as f:
            json.dump(raw, f, indent=2, ensure_ascii=False)
    print(f"[MIGRATE] Updated {migrated} tasks with organization field")


def main() -> None:
    print("=" * 60)
    print("Multi-Tenant Migration Script")
    print("=" * 60)

    print("\n--- Phase 3: Delete christopher account ---")
    delete_christopher_data()
    migrate_users_json()

    print("\n--- Phase 4: Migrate organization data ---")
    migrate_chats()
    migrate_tasks()

    print("\n" + "=" * 60)
    print("Migration complete.")
    print("=" * 60)


if __name__ == "__main__":
    main()
