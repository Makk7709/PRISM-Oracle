import base64
import os
from python.helpers.api import ApiHandler, Request, Response
from python.helpers import files
from python.helpers.print_style import PrintStyle
from python.security.path_safety import safe_path_join, SecurityError
import json


class ApiFilesGet(ApiHandler):
    @classmethod
    def requires_auth(cls) -> bool:
        return False

    @classmethod
    def requires_csrf(cls) -> bool:
        return False

    @classmethod
    def requires_api_key(cls) -> bool:
        return True

    @classmethod
    def get_methods(cls) -> list[str]:
        return ["POST"]

    async def process(self, input: dict, request: Request) -> dict | Response:
        try:
            # Get paths from input
            paths = input.get("paths", [])

            if not paths:
                return Response(
                    '{"error": "paths array is required"}',
                    status=400,
                    mimetype="application/json"
                )

            if not isinstance(paths, list):
                return Response(
                    '{"error": "paths must be an array"}',
                    status=400,
                    mimetype="application/json"
                )

            result = {}

            for path in paths:
                try:
                    relative_path = path.lstrip("/")
                    for prefix in ("app/", "korev/", "a0/"):
                        if relative_path.startswith(prefix):
                            relative_path = relative_path[len(prefix):]
                            break

                    # API-key scope is restricted to temporary generated files.
                    if not (
                        relative_path.startswith("tmp/uploads/")
                        or relative_path.startswith("tmp/chats/")
                    ):
                        PrintStyle.warning(f"Denied file outside API scope: {path}")
                        continue

                    try:
                        resolved = safe_path_join(
                            files.get_base_dir(),
                            relative_path,
                            allow_symlinks=False,
                        )
                    except SecurityError:
                        PrintStyle.warning(f"Denied unsafe path: {path}")
                        continue

                    external_path = str(resolved)
                    filename = os.path.basename(external_path)

                    # Check if file exists
                    if not os.path.exists(external_path):
                        PrintStyle.warning(f"File not found: {path}")
                        continue

                    # Read and encode file
                    with open(external_path, "rb") as f:
                        file_content = f.read()
                        base64_content = base64.b64encode(file_content).decode('utf-8')
                        result[filename] = base64_content

                    PrintStyle().print(f"Retrieved file: {filename} ({len(file_content)} bytes)")

                except Exception as e:
                    PrintStyle.error(f"Failed to read file {path}: {str(e)}")
                    continue

            # Log the retrieval
            PrintStyle(
                background_color="#2ECC71", font_color="white", bold=True, padding=True
            ).print(f"API Files retrieved: {len(result)} files")

            return result

        except Exception as e:
            PrintStyle.error(f"API files get error: {str(e)}")
            return Response(
                json.dumps({"error": f"Internal server error: {str(e)}"}),
                status=500,
                mimetype="application/json"
            )
