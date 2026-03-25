"""
Path alias normalization helpers.

Purpose:
- Normalize legacy container paths (/korev, /a0) to current runtime path (/app).
- Keep one deterministic conversion logic shared by API and code execution.
"""

import re


def normalize_container_path(path: str) -> str:
    """Normalize legacy absolute container path prefixes to /app/."""
    if not isinstance(path, str):
        return path
    if path.startswith("/korev/"):
        return path.replace("/korev/", "/app/", 1)
    if path.startswith("/a0/"):
        return path.replace("/a0/", "/app/", 1)
    return path


def normalize_legacy_paths_in_code(code: str) -> str:
    """
    Rewrite legacy absolute paths in python code snippets.
    Conservative: only rewrites quoted absolute prefixes "/korev/" and "/a0/".
    """
    if not isinstance(code, str) or not code:
        return code
    code = re.sub(r'([\'"])\/korev\/', r"\1/app/", code)
    code = re.sub(r'([\'"])\/a0\/', r"\1/app/", code)
    return code

