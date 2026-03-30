import os
from python.helpers.api import ApiHandler, Input, Output, Request, Response
from python.helpers import files, runtime
from typing import TypedDict
from python.security.path_safety import safe_path_join, SecurityError

class FileInfoApi(ApiHandler):
    async def process(self, input: Input, request: Request) -> Output:
        path = input.get("path", "")
        _, workspace = self._session_user_info()
        allowed, _ = self._authorize_workspace_access(workspace, action="workspace_file_info")
        if not allowed:
            raise Exception("Access denied")
        info = await runtime.call_development_function(get_file_info, path, workspace)
        return info

class FileInfo(TypedDict):
    input_path: str
    abs_path: str
    exists: bool
    is_dir: bool
    is_file: bool
    is_link: bool
    size: int
    modified: float
    created: float
    permissions: int
    dir_path: str
    file_name: str
    file_ext: str
    message: str

async def get_file_info(path: str, base_dir: str | None = None) -> FileInfo:
    root = base_dir or files.get_base_dir()
    normalized = path.lstrip("/")
    if os.path.isabs(path):
        abs_input = os.path.abspath(path)
        root_abs = os.path.abspath(root)
        # Accept absolute paths only when they remain inside the authorized root.
        if abs_input == root_abs or abs_input.startswith(root_abs + os.sep):
            normalized = os.path.relpath(abs_input, root_abs)
        else:
            # Normalize known container prefixes to support legacy links.
            for prefix in ("/app/", "/korev/", "/a0/"):
                if path.startswith(prefix):
                    normalized = path[len(prefix):].lstrip("/")
                    break
    try:
        abs_path = str(safe_path_join(root, normalized, allow_symlinks=False))
    except SecurityError:
        abs_path = files.get_abs_path("__invalid__path__")
    exists = os.path.exists(abs_path)
    message = ""

    # Legacy compatibility: sometimes UI receives only the filename.
    # Search in expected workspace subfolders and resolve uniquely.
    if not exists and "/" not in normalized and base_dir:
        candidates: list[str] = []
        for subdir in ("reports", "generated", "tmp", "documents"):
            start = os.path.join(root, subdir)
            if not os.path.isdir(start):
                continue
            for dirpath, _, filenames in os.walk(start):
                if normalized in filenames:
                    candidates.append(os.path.join(dirpath, normalized))
        if len(candidates) == 1:
            abs_path = candidates[0]
            exists = True
        elif len(candidates) > 1:
            message = f"Multiple files named {normalized} found; use full relative path."

    if not exists:
        message = f"File {path} not found."

    # Backward compatibility for legacy download links generated as
    # /tmp/generated/<file> before strict workspace scoping.
    # Strategy:
    #   1. Try workspace-local generated/<filename>
    #   2. Try global /app/tmp/generated/<filename> (read-only legacy volume)
    if not exists and normalized.startswith("tmp/generated/"):
        legacy_name = os.path.basename(normalized)
        if legacy_name:
            # 1. workspace-local generated/
            if base_dir:
                try:
                    generated_abs = str(
                        safe_path_join(root, os.path.join("generated", legacy_name), allow_symlinks=False)
                    )
                    if os.path.exists(generated_abs):
                        abs_path = generated_abs
                        exists = True
                        message = ""
                except SecurityError:
                    pass
            # 2. global /app/tmp/generated/ (pre-scoping legacy files)
            if not exists:
                app_base = files.get_base_dir()
                try:
                    global_abs = str(
                        safe_path_join(app_base, os.path.join("tmp", "generated", legacy_name), allow_symlinks=False)
                    )
                    if os.path.exists(global_abs):
                        abs_path = global_abs
                        exists = True
                        message = ""
                except SecurityError:
                    pass

    # Filename-only fallback: search workspace + global generated dirs
    if not exists and "/" not in normalized:
        legacy_name = normalized
        search_dirs = []
        if base_dir:
            search_dirs.append(os.path.join(root, "generated"))
            search_dirs.append(os.path.join(root, "reports"))
        app_base = files.get_base_dir()
        search_dirs.append(os.path.join(app_base, "tmp", "generated"))
        for search_dir in search_dirs:
            if not os.path.isdir(search_dir):
                continue
            for dirpath, _, filenames in os.walk(search_dir):
                if legacy_name in filenames:
                    candidate = os.path.join(dirpath, legacy_name)
                    abs_path = candidate
                    exists = True
                    message = ""
                    break
            if exists:
                break

    return {
        "input_path": path,
        "abs_path": abs_path,
        "exists": exists,
        "is_dir": os.path.isdir(abs_path) if exists else False,
        "is_file": os.path.isfile(abs_path) if exists else False,
        "is_link": os.path.islink(abs_path) if exists else False,
        "size": os.path.getsize(abs_path) if exists else 0,
        "modified": os.path.getmtime(abs_path) if exists else 0,
        "created": os.path.getctime(abs_path) if exists else 0,
        "permissions": os.stat(abs_path).st_mode if exists else 0,
        "dir_path": os.path.dirname(abs_path),
        "file_name": os.path.basename(abs_path),
        "file_ext": os.path.splitext(abs_path)[1],
        "message": message
    }