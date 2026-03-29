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
    try:
        abs_path = str(safe_path_join(root, path.lstrip("/"), allow_symlinks=False))
    except SecurityError:
        abs_path = files.get_abs_path("__invalid__path__")
    exists = os.path.exists(abs_path)
    message = ""

    if not exists:
        message = f"File {path} not found."

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