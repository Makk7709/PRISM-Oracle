from python.helpers.api import ApiHandler, Input, Output, Request, Response
from python.helpers.file_browser import FileBrowser
from python.helpers import files, runtime
from python.api import get_work_dir_files
from typing import Optional

# Security imports - Phase 1 P0
from python.security.path_safety import (
    safe_path_join,
    validate_path_in_base,
    SecurityError,
)


class DeleteWorkDirFile(ApiHandler):
    """
    Secure file deletion handler - Phase 1 P0 Security.
    
    Validates:
    - Path is within work directory (no traversal)
    - Path does not contain .. sequences
    """
    
    async def process(self, input: Input, request: Request) -> Output:
        file_path = input.get("path", "")
        _, workspace = self._session_user_info()
        
        # Security validation - Phase 1 P0
        # Strip leading "/" to treat as relative path within project
        file_path = file_path.lstrip("/")
        
        # Reject obvious traversal attempts early
        if ".." in file_path:
            raise Exception("Invalid path: traversal not allowed")
        
        current_path = input.get("currentPath", "")

        # Perform deletion with path validation
        res = await runtime.call_development_function(delete_file_secure, file_path, workspace)

        if res:
            # Get updated file list
            result = await runtime.call_development_function(
                get_work_dir_files.get_files, current_path, workspace
            )
            return {"data": result}
        else:
            raise Exception("File not found or could not be deleted")


async def delete_file_secure(file_path: str, workspace: Optional[str] = None) -> bool:
    """
    Securely delete a file with path validation.
    
    Returns True if deleted, False if not found.
    Raises SecurityError if path validation fails.
    """
    browser = FileBrowser(base_dir=workspace or files.get_base_dir())
    
    # Additional validation: ensure path stays within base_dir
    # The FileBrowser.delete_file already does this, but we add belt-and-suspenders
    try:
        # Validate the path before passing to delete
        resolved_path = safe_path_join(
            browser.base_dir,
            file_path,
            allow_symlinks=False,  # Don't follow symlinks for delete
        )
        
        # Use relative path for FileBrowser
        relative_path = str(resolved_path.relative_to(browser.base_dir))
        return browser.delete_file(relative_path)
        
    except SecurityError:
        # Don't expose security errors as exceptions
        # Just return False (file not found/not deletable)
        return False
    except FileNotFoundError:
        return False
