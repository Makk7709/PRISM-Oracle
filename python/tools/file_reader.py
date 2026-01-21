"""
File Reader Tool — Direct file reading for Excel, CSV, PDF, and text files.

This tool provides a simple interface for reading common file formats
without requiring the agent to write Python code.
"""

import os
from dataclasses import dataclass
from python.helpers.tool import Tool, Response
from python.helpers import files
from python.helpers.print_style import PrintStyle


class FileReader(Tool):
    """
    Simple file reader for common formats.
    Supports: Excel (.xlsx, .xls), CSV, PDF, TXT, JSON
    """

    async def execute(self, **kwargs) -> Response:
        file_path = self.args.get("path", "")
        format_hint = self.args.get("format", "auto")
        max_rows = int(self.args.get("max_rows", 100))
        
        if not file_path:
            return Response(
                message="Error: 'path' argument is required. Provide the file path.",
                break_loop=False
            )
        
        # Resolve path
        abs_path = self._resolve_path(file_path)
        
        if not os.path.exists(abs_path):
            # Try in uploads folder
            uploads_path = files.get_abs_path("tmp/uploads", os.path.basename(file_path))
            if os.path.exists(uploads_path):
                abs_path = uploads_path
            else:
                return Response(
                    message=f"Error: File not found: {file_path}\n"
                            f"Checked:\n- {abs_path}\n- {uploads_path}\n"
                            f"Available files in uploads:\n{self._list_uploads()}",
                    break_loop=False
                )
        
        # Detect format
        ext = os.path.splitext(abs_path)[1].lower()
        
        try:
            if ext in ['.xlsx', '.xls']:
                content = self._read_excel(abs_path, max_rows)
            elif ext == '.csv':
                content = self._read_csv(abs_path, max_rows)
            elif ext == '.pdf':
                content = self._read_pdf(abs_path)
            elif ext in ['.txt', '.md', '.json', '.xml', '.html']:
                content = self._read_text(abs_path)
            else:
                content = self._read_text(abs_path)
            
            PrintStyle(font_color="green").print(f"[FileReader] Read: {abs_path}")
            
            return Response(
                message=f"File: {os.path.basename(abs_path)}\nPath: {abs_path}\n\n{content}",
                break_loop=False
            )
            
        except Exception as e:
            return Response(
                message=f"Error reading file: {e}",
                break_loop=False
            )
    
    def _resolve_path(self, path: str) -> str:
        """Resolve file path to absolute."""
        if os.path.isabs(path):
            return path
        
        # Check relative to work dir
        work_dir = files.get_abs_path("")
        candidate = os.path.join(work_dir, path)
        if os.path.exists(candidate):
            return candidate
        
        # Check in uploads
        uploads = files.get_abs_path("tmp/uploads")
        candidate = os.path.join(uploads, path)
        if os.path.exists(candidate):
            return candidate
        
        return files.get_abs_path(path)
    
    def _list_uploads(self) -> str:
        """List files in uploads folder."""
        uploads = files.get_abs_path("tmp/uploads")
        if not os.path.exists(uploads):
            return "(uploads folder empty)"
        
        files_list = os.listdir(uploads)
        if not files_list:
            return "(no files)"
        
        return "\n".join(f"- {f}" for f in sorted(files_list)[:20])
    
    def _read_excel(self, path: str, max_rows: int) -> str:
        """Read Excel file using pandas."""
        import pandas as pd
        
        df = pd.read_excel(path, nrows=max_rows)
        
        info = f"Rows: {len(df)} (showing up to {max_rows})\n"
        info += f"Columns: {list(df.columns)}\n\n"
        info += "Data:\n"
        info += df.to_string(index=False)
        
        return info
    
    def _read_csv(self, path: str, max_rows: int) -> str:
        """Read CSV file using pandas."""
        import pandas as pd
        
        df = pd.read_csv(path, nrows=max_rows)
        
        info = f"Rows: {len(df)} (showing up to {max_rows})\n"
        info += f"Columns: {list(df.columns)}\n\n"
        info += "Data:\n"
        info += df.to_string(index=False)
        
        return info
    
    def _read_pdf(self, path: str) -> str:
        """Read PDF file using PyMuPDF."""
        try:
            import fitz  # PyMuPDF
            
            doc = fitz.open(path)
            text_parts = []
            
            for page_num, page in enumerate(doc, 1):
                text = page.get_text()
                if text.strip():
                    text_parts.append(f"--- Page {page_num} ---\n{text}")
            
            doc.close()
            
            if not text_parts:
                return "(PDF contains no extractable text - may be scanned/image-based)"
            
            return f"Pages: {len(text_parts)}\n\n" + "\n\n".join(text_parts[:10])
            
        except ImportError:
            return "Error: PyMuPDF not installed. Install with: pip install PyMuPDF"
    
    def _read_text(self, path: str) -> str:
        """Read text file."""
        with open(path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        
        # Truncate if too long
        if len(content) > 10000:
            content = content[:10000] + "\n\n... (truncated)"
        
        return content
