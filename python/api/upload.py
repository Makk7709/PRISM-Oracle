from python.helpers.api import ApiHandler, Request, Response
from python.helpers import files
from werkzeug.utils import secure_filename
from io import BytesIO

# Security imports - Phase 1 P0
from python.security.upload_validation import (
    validate_upload,
    is_extension_allowed,
    UploadValidationError,
    MAX_UPLOAD_SIZE,
)
from python.security.path_safety import safe_path_join, SecurityError


class UploadFile(ApiHandler):
    """
    Secure file upload handler - Phase 1 P0 Security.
    
    Validates:
    - File extension against allowlist
    - File size against MAX_UPLOAD_SIZE
    - MIME type matches extension
    - Filename sanitization (no path traversal)
    """
    
    async def process(self, input: dict, request: Request) -> dict | Response:
        if "file" not in request.files:
            raise ValueError("No file part")

        file_list = request.files.getlist("file")  # Handle multiple files
        saved_filenames = []
        errors = []
        
        # Get upload directory path safely
        upload_base = files.get_abs_path("tmp/uploads")

        for file in file_list:
            if not file or not file.filename:
                continue
                
            try:
                # Read file content into BytesIO for validation
                file_content = BytesIO(file.read())
                file.seek(0)  # Reset for saving
                
                # Validate file - Phase 1 P0 Security
                safe_filename, detected_mime, file_size = validate_upload(
                    file_content,
                    file.filename,
                    check_mime=True,
                )
                
                # Additional werkzeug sanitization
                safe_filename = secure_filename(safe_filename)
                if not safe_filename:
                    raise UploadValidationError("Invalid filename after sanitization")
                
                # Safe path join to prevent traversal
                target_path = safe_path_join(upload_base, safe_filename)
                
                # Save the file
                file.save(str(target_path))
                saved_filenames.append(safe_filename)
                
            except (UploadValidationError, SecurityError):
                # Log but don't expose internal details
                errors.append(f"File '{file.filename}': validation failed")
            except Exception:
                errors.append(f"File '{file.filename}': upload error")

        result = {"filenames": saved_filenames}
        if errors:
            result["errors"] = errors
            
        return result