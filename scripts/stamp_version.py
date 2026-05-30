#!/usr/bin/env python3
"""Stamp build-time git metadata into VERSION.json during the Docker build.

The human-curated fields (``version``, ``tag``, ``short_tag``) are preserved as
the release label. The commit-level fields are overridden with the values of the
build that actually produced the image, so a running container reports the real
deployed commit instead of whatever was committed to VERSION.json.

Driven by environment variables (passed as Docker build-args):
    GIT_COMMIT  full commit sha of the build (required to stamp; no-op if empty)
    GIT_BRANCH  branch name of the build (optional)
    BUILD_DATE  ISO-8601 build timestamp (optional)

No-op when GIT_COMMIT is empty so a plain ``docker build`` without build-args
keeps the repo VERSION.json untouched.
"""
from __future__ import annotations

import json
import os
import sys


def main() -> int:
    path = sys.argv[1] if len(sys.argv) > 1 else "VERSION.json"

    commit = os.environ.get("GIT_COMMIT", "").strip()
    if not commit:
        print("[stamp_version] GIT_COMMIT empty -> VERSION.json left unchanged")
        return 0

    try:
        with open(path) as handle:
            data = json.load(handle)
    except (OSError, ValueError) as exc:
        print(f"[stamp_version] cannot read {path}: {exc}", file=sys.stderr)
        return 1

    data["commit_hash"] = commit[:8]
    data["build_commit"] = commit

    branch = os.environ.get("GIT_BRANCH", "").strip()
    if branch:
        data["branch"] = branch

    build_date = os.environ.get("BUILD_DATE", "").strip()
    if build_date:
        data["commit_time"] = build_date
        data["build_date"] = build_date

    with open(path, "w") as handle:
        json.dump(data, handle, indent=2)
        handle.write("\n")

    print(
        f"[stamp_version] stamped commit={commit[:8]} "
        f"branch={data.get('branch', '')} build_date={build_date or 'n/a'}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
