from python.helpers.api import ApiHandler, Request, Response
from python.helpers.file_browser import FileBrowser
from python.helpers import runtime, files

class GetWorkDirFiles(ApiHandler):

    @classmethod
    def get_methods(cls):
        return ["GET"]
    
    @classmethod
    def requires_csrf(cls) -> bool:
        # Read-only file listing, no CSRF needed
        return False

    async def process(self, input: dict, request: Request) -> dict | Response:
        current_path = request.args.get("path", "")
        if current_path == "$WORK_DIR":
            current_path = ""

        _, workspace = self._session_user_info()
        result = await runtime.call_development_function(get_files, current_path, workspace)

        return {"data": result}


async def get_files(path, workspace=None):
    browser = FileBrowser(base_dir=workspace or files.get_base_dir())
    return browser.get_files(path)
