import base64
import os
from python.helpers.api import ApiHandler, Request, Response, send_file
from python.helpers import files, runtime
import io
from mimetypes import guess_type
from agent import AgentContext


class ImageGet(ApiHandler):

    @classmethod
    def requires_csrf(cls) -> bool:
        # Image serving is read-only, no CSRF protection needed
        return False

    @classmethod
    def get_methods(cls) -> list[str]:
        return ["GET"]

    async def process(self, input: dict, request: Request) -> dict | Response:
        # input data
        path = input.get("path", request.args.get("path", ""))
        metadata = (
            input.get("metadata", request.args.get("metadata", "false")).lower()
            == "true"
        )

        if not path:
            raise ValueError("No path provided")

        # ── Normalize the user-supplied path to a safe relative path ──
        # 1. Strip leading slashes
        path = path.lstrip("/")

        # 2. Strip Docker/container prefixes (korev/, app/, a0/)
        for prefix in ("korev/", "app/", "a0/"):
            if path.startswith(prefix):
                path = path[len(prefix):]
                break

        # 3. Handle absolute paths that lost their leading "/"
        #    (e.g., browser agent sends /Users/.../tmp/chats/... which
        #    becomes Users/.../tmp/chats/... after lstrip)
        base_dir = files.get_base_dir()
        base_stripped = base_dir.lstrip("/")
        if path.startswith(base_stripped):
            path = path[len(base_stripped):].lstrip("/")

        principal = self._principal()
        if principal.is_authenticated:
            allowed = False
            workspace = (principal.workspace or "").lstrip("/")
            if workspace and (path == workspace or path.startswith(f"{workspace}/")):
                allowed = True
            if path.startswith("tmp/uploads/") and principal.username:
                user_prefix = f"tmp/uploads/{principal.username}/"
                if path.startswith(user_prefix):
                    allowed = True
            if path.startswith("tmp/chats/"):
                parts = path.split("/")
                if len(parts) >= 3:
                    ctxid = parts[2]
                    ctx = AgentContext.get(ctxid)
                    if ctx:
                        ctx_allowed, _ = self._authorize_context_access(
                            ctx, action="image_get_chat_file"
                        )
                        if ctx_allowed:
                            allowed = True
            if not allowed:
                raise ValueError("Access denied")

        # 4. Validate path stays within the project via safe_path_join
        from python.security.path_safety import safe_path_join, SecurityError
        try:
            if runtime.is_development():
                resolved = safe_path_join(base_dir, path, allow_symlinks=True)
            else:
                resolved = safe_path_join(base_dir, path, allow_symlinks=False)
        except SecurityError:
            raise ValueError("Path is outside of allowed directory")

        # get file extension and info
        file_ext = os.path.splitext(path)[1].lower()
        filename = os.path.basename(path)

        # list of allowed image extensions
        image_extensions = [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".svg"]

        # # If metadata is requested, return file information
        # if metadata:
        #     return _get_file_metadata(path, filename, file_ext, image_extensions)
       
        # Downloadable document extensions (served as attachment instead of icon)
        downloadable_extensions = [
            ".pdf", ".doc", ".docx", ".xls", ".xlsx", ".csv", ".ppt", ".pptx",
            ".odt", ".odp", ".rtf", ".txt", ".md", ".zip", ".rar", ".7z",
            ".tar", ".gz", ".json", ".xml", ".yaml", ".yml",
        ]

        if file_ext in image_extensions:

            # in development environment, try to serve the image from local file system if exists, otherwise from docker
            if runtime.is_development():
                if files.exists(path):
                    response = send_file(path)
                elif await runtime.call_development_function(files.exists, path):
                    b64_content = await runtime.call_development_function(
                        files.read_file_base64, path
                    )
                    file_content = base64.b64decode(b64_content)
                    mime_type, _ = guess_type(filename)
                    if not mime_type:
                        mime_type = "application/octet-stream"
                    response = send_file(
                        io.BytesIO(file_content),
                        mimetype=mime_type,
                        as_attachment=False,
                        download_name=filename,
                    )
                else:
                    response = _send_fallback_icon("image")
            else:
                if files.exists(path):
                    response = send_file(path)
                else:
                    response = _send_fallback_icon("image")

            # Add cache headers for better device sync performance
            response.headers["Cache-Control"] = "public, max-age=3600"
            response.headers["X-File-Type"] = "image"
            response.headers["X-File-Name"] = filename
            return response

        elif file_ext in downloadable_extensions:
            # Serve the actual file as a download instead of an icon
            if runtime.is_development():
                if files.exists(path):
                    mime_type, _ = guess_type(filename)
                    if not mime_type:
                        mime_type = "application/octet-stream"
                    response = send_file(
                        path,
                        mimetype=mime_type,
                        as_attachment=True,
                        download_name=filename,
                    )
                elif await runtime.call_development_function(files.exists, path):
                    b64_content = await runtime.call_development_function(
                        files.read_file_base64, path
                    )
                    file_content = base64.b64decode(b64_content)
                    mime_type, _ = guess_type(filename)
                    if not mime_type:
                        mime_type = "application/octet-stream"
                    response = send_file(
                        io.BytesIO(file_content),
                        mimetype=mime_type,
                        as_attachment=True,
                        download_name=filename,
                    )
                else:
                    return _send_file_type_icon(file_ext, filename)
            else:
                if files.exists(path):
                    mime_type, _ = guess_type(filename)
                    if not mime_type:
                        mime_type = "application/octet-stream"
                    response = send_file(
                        path,
                        mimetype=mime_type,
                        as_attachment=True,
                        download_name=filename,
                    )
                else:
                    return _send_file_type_icon(file_ext, filename)

            response.headers["Cache-Control"] = "no-cache"
            response.headers["X-File-Type"] = "document"
            response.headers["X-File-Name"] = filename
            return response

        else:
            # Handle unknown file types with fallback icons
            return _send_file_type_icon(file_ext, filename)


def _send_file_type_icon(file_ext, filename=None):
    """Return appropriate icon for file type"""

    # Map file extensions to icon names
    icon_mapping = {
        # Archive files
        ".zip": "archive",
        ".rar": "archive",
        ".7z": "archive",
        ".tar": "archive",
        ".gz": "archive",
        # Document files
        ".pdf": "document",
        ".doc": "document",
        ".docx": "document",
        ".txt": "document",
        ".rtf": "document",
        ".odt": "document",
        # Code files
        ".py": "code",
        ".js": "code",
        ".html": "code",
        ".css": "code",
        ".json": "code",
        ".xml": "code",
        ".md": "code",
        ".yml": "code",
        ".yaml": "code",
        ".sql": "code",
        ".sh": "code",
        ".bat": "code",
        # Spreadsheet files
        ".xls": "document",
        ".xlsx": "document",
        ".csv": "document",
        # Presentation files
        ".ppt": "document",
        ".pptx": "document",
        ".odp": "document",
    }

    # Get icon name, default to 'file' if not found
    icon_name = icon_mapping.get(file_ext, "file")

    response = _send_fallback_icon(icon_name)

    # Add headers for device sync
    if hasattr(response, "headers"):
        response.headers["Cache-Control"] = (
            "public, max-age=86400"  # Cache icons for 24 hours
        )
        response.headers["X-File-Type"] = "icon"
        response.headers["X-Icon-Type"] = icon_name
        if filename:
            response.headers["X-File-Name"] = filename

    return response


def _send_fallback_icon(icon_name):
    """Return fallback icon from public directory"""

    # Path to public icons
    icon_path = files.get_abs_path(f"webui/public/{icon_name}.svg")

    # Check if specific icon exists, fallback to generic file icon
    if not os.path.exists(icon_path):
        icon_path = files.get_abs_path("webui/public/file.svg")

    # Final fallback if file.svg doesn't exist
    if not os.path.exists(icon_path):
        raise ValueError(f"Fallback icon not found: {icon_path}")

    return send_file(icon_path, mimetype="image/svg+xml")
