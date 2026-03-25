"""
File Reader Tool — Direct file reading for Excel, CSV, PDF, and text files.

This tool provides a simple interface for reading common file formats
without requiring the agent to write Python code.
"""

import os
from typing import Optional
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
        max_rows = int(self.args.get("max_rows", 100))
        max_chars = int(self.args.get("max_chars", 300000))
        max_pages_arg = int(self.args.get("max_pages", 0)) if str(self.args.get("max_pages", "")).strip() else 0
        max_pages = max_pages_arg if max_pages_arg > 0 else None
        
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
                # Try in knowledge folders
                knowledge_path = self._find_in_knowledge(file_path)
                if knowledge_path:
                    abs_path = knowledge_path
                else:
                    return Response(
                        message=f"Error: File not found: {file_path}\n"
                                f"Checked:\n- {abs_path}\n- {uploads_path}\n"
                                f"Available files:\n{self._list_all_user_files()}",
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
                content = self._read_pdf(abs_path, max_pages=max_pages, max_chars=max_chars)
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
        """Resolve file path to absolute, checking uploads and knowledge folders."""
        # Normalize Docker/container paths to local equivalents
        if path.startswith(("/korev/", "/app/", "/a0/")):
            from python.helpers.files import fix_dev_path
            fixed = fix_dev_path(path)
            if os.path.exists(fixed):
                return fixed

        if os.path.isabs(path):
            if os.path.exists(path):
                return path
            # Absolute path doesn't exist — try basename fallback below

        basename = os.path.basename(path)

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
        candidate = os.path.join(uploads, basename)
        if os.path.exists(candidate):
            return candidate

        # Check in knowledge folders
        knowledge_hit = self._find_in_knowledge(path)
        if knowledge_hit:
            return knowledge_hit
        
        return files.get_abs_path(path)

    def _get_knowledge_dirs(self) -> list[str]:
        """Return all knowledge directories accessible to the current agent."""
        dirs = []
        try:
            from python.helpers import memory, projects
            agent = self.agent

            # Project-specific knowledge
            project_name = projects.get_context_project_name(agent.context)
            if project_name:
                proj_kn = projects.get_project_meta_folder(project_name, "knowledge")
                if os.path.isdir(proj_kn):
                    dirs.append(proj_kn)

            # Custom knowledge (knowledge/custom/main/)
            try:
                custom_dir = memory.get_custom_knowledge_subdir_abs(agent)
                main_dir = os.path.join(custom_dir, "main")
                if os.path.isdir(main_dir):
                    dirs.append(main_dir)
                if os.path.isdir(custom_dir) and custom_dir not in dirs:
                    dirs.append(custom_dir)
            except Exception:
                pass

            # Default knowledge
            default_kn = files.get_abs_path("knowledge", "default")
            if os.path.isdir(default_kn):
                dirs.append(default_kn)

            # Top-level knowledge (catches any subdirectory structure)
            top_kn = files.get_abs_path("knowledge")
            if os.path.isdir(top_kn):
                dirs.append(top_kn)

        except Exception:
            pass
        return dirs

    def _find_in_knowledge(self, path: str) -> Optional[str]:
        """Search for a file by name or relative path in knowledge directories."""
        basename = os.path.basename(path)
        for kn_dir in self._get_knowledge_dirs():
            # Direct match
            candidate = os.path.join(kn_dir, path)
            if os.path.isfile(candidate):
                return candidate
            candidate = os.path.join(kn_dir, basename)
            if os.path.isfile(candidate):
                return candidate
            # Recursive search by basename
            for root, _dirs, fnames in os.walk(kn_dir):
                if basename in fnames:
                    return os.path.join(root, basename)
        return None

    def _list_all_user_files(self) -> str:
        """List files in uploads and knowledge folders."""
        sections = []

        # Uploads
        uploads = files.get_abs_path("tmp/uploads")
        if os.path.isdir(uploads):
            upload_files = [f for f in os.listdir(uploads) if os.path.isfile(os.path.join(uploads, f))]
            if upload_files:
                sections.append("📎 Uploads (tmp/uploads/):")
                for f in sorted(upload_files)[:20]:
                    sections.append(f"  - {f}")

        # Knowledge
        for kn_dir in self._get_knowledge_dirs():
            kn_files = []
            for root, _dirs, fnames in os.walk(kn_dir):
                for f in fnames:
                    if not f.startswith('.'):
                        rel = os.path.relpath(os.path.join(root, f), kn_dir)
                        kn_files.append(rel)
            if kn_files:
                label = os.path.relpath(kn_dir, files.get_abs_path(""))
                sections.append(f"📚 Knowledge ({label}/):")
                for f in sorted(kn_files)[:20]:
                    sections.append(f"  - {f}")

        if not sections:
            return "(no files found)"
        return "\n".join(sections)
    
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
    
    def _read_pdf(self, path: str, max_pages: Optional[int] = None, max_chars: int = 300000) -> str:
        """Read PDF file using pypdf (BSD license)."""
        try:
            from pypdf import PdfReader

            reader = PdfReader(path)
            total_pages = len(reader.pages)
            pages_to_process = total_pages if max_pages is None else min(max_pages, total_pages)
            text_parts = []

            for page_num in range(pages_to_process):
                page = reader.pages[page_num]
                text = page.extract_text() or ""
                if text.strip():
                    text_parts.append(f"--- Page {page_num + 1} ---\n{text}")

            if not text_parts:
                return "(PDF contains no extractable text - may be scanned/image-based)"

            output = (
                f"Pages: {pages_to_process}/{total_pages}\n"
                f"Non-empty pages: {len(text_parts)}\n\n"
                + "\n\n".join(text_parts)
            )
            if len(output) > max_chars:
                output = (
                    output[:max_chars]
                    + f"\n\n... (truncated to {max_chars} chars; increase `max_chars` to read full document)"
                )
            return output

        except ImportError:
            return "Error: pypdf not installed. Install with: pip install pypdf"
    
    def _read_text(self, path: str) -> str:
        """Read text file."""
        with open(path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        
        # Truncate if too long
        if len(content) > 10000:
            content = content[:10000] + "\n\n... (truncated)"
        
        return content
