"""
File Writer Tool — Create files (PDF, CSV, Excel, text).

This tool provides a simple interface for creating common file formats
without requiring the agent to write Python code.

Integrity contract (cf. ADR-006 + plan de correction yENoyKIZ):
  - If the agent passes a §§include(...) directive whose target cannot be
    resolved (file not in ALLOWED_INCLUDE_DIRS, missing, etc.), the tool
    MUST fail hard before writing ANY artefact on disk.
  - The Response.message MUST reflect the actual filesystem state. A success
    message is a structural commitment that an artefact was correctly produced
    with the expected content; it must never be returned for a partial render.
"""

import os
from datetime import datetime
from pathlib import Path
from python.helpers.tool import Tool, Response
from python.helpers import files
from python.helpers.print_style import PrintStyle


class IncludeResolutionError(Exception):
    """
    Raised when one or more §§include(...) directives in the agent-supplied
    content cannot be resolved to readable files inside the allowed
    directories.

    The exception carries the list of failing paths (verbatim, as written by
    the agent) so the caller can build an actionable error message.
    """

    def __init__(self, unresolved_paths: list[str]):
        self.unresolved_paths = list(unresolved_paths)
        super().__init__(
            f"{len(self.unresolved_paths)} include directive(s) could not "
            f"be resolved: {self.unresolved_paths}"
        )


class FileWriter(Tool):
    """
    Simple file writer for common formats.
    Supports: PDF, CSV, Excel, TXT, JSON, Markdown
    """

    def _resolve_workspace(self) -> str | None:
        """
        Resolve a scoped workspace for file generation.

        Priority:
        1. Explicit context.workspace
        2. Derive from context.username -> shared/users/<username>
        3. None (legacy/system context)
        """
        ctx = getattr(self.agent, "context", None)
        workspace = getattr(ctx, "workspace", None)
        username = (getattr(ctx, "username", None) or "").strip().lower()

        PrintStyle(font_color="cyan").print(
            f"[FileWriter] _resolve_workspace: ctx={ctx is not None}, "
            f"workspace={workspace!r}, username={username!r}"
        )

        if workspace:
            return workspace

        if username and username != "anonymous":
            derived = files.get_abs_path("shared/users", username)
            os.makedirs(derived, exist_ok=True)
            PrintStyle(font_color="cyan").print(
                f"[FileWriter] Derived workspace from username: {derived}"
            )
            return derived

        PrintStyle(font_color="yellow").print(
            "[FileWriter] WARNING: No workspace resolved — falling back to global tmp"
        )
        return None

    async def execute(self, **kwargs) -> Response:
        filename = self.args.get("filename", "")
        content = self.args.get("content", "")
        format_type = self.args.get("format", "auto")
        title = self.args.get("title", "")
        template = self.args.get("template", "")  # PDF template name
        
        if not filename:
            return Response(
                message="Error: 'filename' argument is required.",
                break_loop=False
            )
        
        if not content:
            return Response(
                message="Error: 'content' argument is required.",
                break_loop=False
            )
        
        # ── Guard: resolve §§include() directives ──────────────────────────
        # Some models (e.g. GPT-5.2) try to use fictional include directives
        # instead of providing the full content. Detect and resolve them.
        # CRITICAL: if any directive cannot be resolved we abort BEFORE any
        # filesystem write — see ADR-006 (tool I/O integrity contract).
        try:
            content = self._resolve_includes(content)
        except IncludeResolutionError as exc:
            return Response(
                message=self._format_include_error(exc),
                break_loop=False,
            )

        # Ensure output directory exists (workspace-local if available)
        workspace = self._resolve_workspace()
        if workspace:
            output_dir = os.path.join(workspace, "generated")
            try:
                os.makedirs(output_dir, exist_ok=True)
                # Verify we can actually write to the directory
                test_file = os.path.join(output_dir, ".write_test")
                with open(test_file, "w") as f:
                    f.write("")
                os.remove(test_file)
            except PermissionError:
                PrintStyle(font_color="yellow").print(
                    f"[FileWriter] Permission denied on {output_dir} — falling back to global tmp"
                )
                workspace = None
                output_dir = files.get_abs_path("tmp/generated")
                os.makedirs(output_dir, exist_ok=True)
        else:
            output_dir = files.get_abs_path("tmp/generated")
            os.makedirs(output_dir, exist_ok=True)
        
        # Add timestamp to avoid overwrites
        base, ext = os.path.splitext(filename)
        if not ext:
            ext = self._detect_extension(format_type)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        final_filename = f"{base}_{timestamp}{ext}"
        output_path = os.path.join(output_dir, final_filename)
        
        try:
            # Log content info for debugging
            content_lines = content.count('\n') + 1 if content else 0
            content_chars = len(content) if content else 0
            PrintStyle(font_color="cyan").print(
                f"[FileWriter] Processing: {content_chars} chars, {content_lines} lines, template={template or 'default'}"
            )
            
            if ext == '.pdf':
                self._write_pdf(output_path, content, title, template)
            elif ext == '.csv':
                self._write_csv(output_path, content)
            elif ext in ['.xlsx', '.xls']:
                self._write_excel(output_path, content)
            else:
                self._write_text(output_path, content)
            
            PrintStyle(font_color="green").print(f"[FileWriter] Created: {output_path}")
            
            # Build workspace-relative download URL to stay inside authorization scope.
            if workspace:
                rel = "/" + str(Path(output_path).relative_to(Path(workspace))).replace("\\", "/")
            else:
                rel = f"/tmp/generated/{final_filename}"
            download_url = f"/download_work_dir_file?path={rel}"
            
            return Response(
                message=f"✅ File created successfully!\n\n"
                        f"**Filename:** {final_filename}\n"
                        f"**Path:** {output_path}\n"
                        f"**Size:** {os.path.getsize(output_path)} bytes\n\n"
                        f"**Download link (use this in your response):**\n"
                        f"[📄 Télécharger {final_filename}]({download_url})",
                break_loop=False
            )
            
        except Exception as e:
            return Response(
                message=f"Error creating file: {e}",
                break_loop=False
            )
    
    def _resolve_includes(self, content: str) -> str:
        """
        Resolve §§include() directives that some models generate instead of
        providing full content. Also handles similar patterns like
        {{include()}}, <<include()>>, @include(), etc.

        Contract (ADR-006):
          - If the content has no directives, return it unchanged.
          - If every directive can be resolved, return the content with all
            directives replaced inline.
          - If ANY directive cannot be resolved, raise IncludeResolutionError
            carrying the list of unresolved paths. NO partial substitution
            ever leaks to the caller (all-or-nothing atomicity).
        """
        import re

        # Pattern: §§include(path), {{include(path)}}, <<include(path)>>, @include(path)
        include_pattern = re.compile(
            r'(?:§§|@@|<<|{{|@)?\s*include\s*\(\s*([^\)]+?)\s*\)\s*(?:>>|}})?',
            re.IGNORECASE,
        )

        matches = list(include_pattern.finditer(content))
        if not matches:
            return content

        PrintStyle(font_color="yellow").print(
            f"[FileWriter] WARNING: Detected {len(matches)} include directive(s) — "
            f"model sent reference instead of content. Resolving..."
        )

        # ── Phase 1: pre-resolve every directive without touching content ──
        # We collect the result for each match and the list of unresolved
        # paths. This guarantees that we either succeed for ALL directives or
        # we raise BEFORE any substitution takes place.
        resolutions: dict[int, str] = {}
        unresolved: list[str] = []
        for idx, match in enumerate(matches):
            file_path = match.group(1).strip().strip("'\"")
            resolved = self._read_include_file(file_path)
            if resolved is None:
                unresolved.append(file_path)
            else:
                resolutions[idx] = resolved
                PrintStyle(font_color="green").print(
                    f"[FileWriter] Resolved include: {len(resolved)} chars from {file_path}"
                )

        if unresolved:
            # Atomicity: no partial render. Caller turns this into a
            # Response error and refrains from writing any artefact.
            raise IncludeResolutionError(unresolved)

        # ── Phase 2: substitute in reverse order (preserves indices) ──
        result = content
        for idx in range(len(matches) - 1, -1, -1):
            match = matches[idx]
            result = result[: match.start()] + resolutions[idx] + result[match.end():]

        return result

    def _format_include_error(self, exc: IncludeResolutionError) -> str:
        """
        Build an agent-actionable error message for an unresolved include.

        Contract (cf. plan de correction §3.2 / invariant I-5):
          - Cite each requested path verbatim so the model can self-correct.
          - List the allowed directories explicitly.
          - State a corrective action (move file or inline content).
          - No Python traceback, no internal filesystem details beyond the
            allowed directory names.
        """
        bullets = "\n".join(f"  • {p}" for p in exc.unresolved_paths)
        allowed = "\n".join(f"  • {d}" for d in self.ALLOWED_INCLUDE_DIRS)
        return (
            "❌ FileWriter aborted: include directive(s) could not be resolved.\n"
            "\n"
            f"Failed paths ({len(exc.unresolved_paths)}):\n"
            f"{bullets}\n"
            "\n"
            "Allowed include directories (relative to project root):\n"
            f"{allowed}\n"
            "\n"
            "Corrective action:\n"
            "  - Move the referenced file(s) into one of the allowed "
            "directories above, OR\n"
            "  - Pass the full file content inline as the `content` argument "
            "instead of using a §§include(...) directive.\n"
            "\n"
            "No artefact was written. Please retry with a corrected payload."
        )
    
    # Directories from which include directives are allowed to read files.
    # All paths are relative to the project root (files.get_base_dir()).
    ALLOWED_INCLUDE_DIRS = (
        "tmp/uploads",
        "tmp/generated",
        "docs",
        "work_dir",
    )

    def _read_include_file(self, file_path: str) -> str | None:
        """
        Try to read a file referenced by an include directive.
        
        Security: Only files within ALLOWED_INCLUDE_DIRS (relative to the
        project root) can be read.  Absolute paths outside the project,
        traversal sequences, and symlinks escaping the base are all blocked.
        """
        from python.security.path_safety import safe_path_join, SecurityError
        from pathlib import Path
        import os

        if not file_path or not file_path.strip():
            return None

        file_path = file_path.strip()
        base_dir = files.get_base_dir()

        # ------------------------------------------------------------------
        # 1. If the path is absolute and inside the project, convert to
        #    relative so it can be validated against allowed dirs.
        # ------------------------------------------------------------------
        if os.path.isabs(file_path):
            try:
                rel = os.path.relpath(file_path, base_dir)
            except ValueError:
                # Different drive on Windows
                PrintStyle(font_color="red").print(
                    f"[FileWriter] BLOCKED include (absolute path outside project): {file_path}"
                )
                return None

            # If relpath starts with "..", the file is outside the project
            if rel.startswith(".."):
                PrintStyle(font_color="red").print(
                    f"[FileWriter] BLOCKED include (path escapes project): {file_path}"
                )
                return None
            file_path = rel

        # ------------------------------------------------------------------
        # 2. Try to resolve the path within each allowed directory.
        # ------------------------------------------------------------------
        for allowed_dir in self.ALLOWED_INCLUDE_DIRS:
            # If file_path already starts with the allowed prefix, try it
            # directly; otherwise try basename-only lookup.
            candidates = []

            if file_path.startswith(allowed_dir + "/") or file_path.startswith(allowed_dir + os.sep):
                candidates.append(file_path)
            else:
                # Basename lookup: look for the filename in the allowed dir
                basename = os.path.basename(file_path)
                if basename:
                    candidates.append(os.path.join(allowed_dir, basename))

                # Also try the full relative path under the allowed dir
                candidates.append(os.path.join(allowed_dir, file_path))

            # Resolve the allowed directory to an absolute path for
            # post-resolution containment check.
            allowed_abs = (Path(base_dir) / allowed_dir).resolve()

            for candidate_rel in candidates:
                try:
                    safe_abs = safe_path_join(
                        base_dir,
                        candidate_rel,
                        allow_symlinks=False,
                        must_exist=True,
                    )

                    # CRITICAL: the resolved path must land inside the
                    # specific allowed sub-directory, not just the base dir.
                    # This blocks traversal like tmp/uploads/../../.env
                    try:
                        safe_abs.relative_to(allowed_abs)
                    except ValueError:
                        continue

                    # Must be a regular file
                    if not safe_abs.is_file():
                        continue

                    with open(safe_abs, 'r', encoding='utf-8') as f:
                        content = f.read()
                    PrintStyle(font_color="cyan").print(
                        f"[FileWriter] Resolved include: {safe_abs}"
                    )
                    return content

                except (SecurityError, FileNotFoundError, OSError, UnicodeDecodeError):
                    # UnicodeDecodeError: file is binary or non-UTF-8.
                    # Treat as unresolved so the caller fails hard via
                    # IncludeResolutionError rather than silently producing
                    # a corrupted document.
                    continue

        # ------------------------------------------------------------------
        # 3. Nothing matched.
        # ------------------------------------------------------------------
        PrintStyle(font_color="red").print(
            f"[FileWriter] WARNING: Could not resolve include file "
            f"(not found in allowed dirs): {file_path}"
        )
        return None
    
    def _detect_extension(self, format_type: str) -> str:
        """Detect file extension from format type."""
        formats = {
            'pdf': '.pdf',
            'csv': '.csv',
            'excel': '.xlsx',
            'xlsx': '.xlsx',
            'text': '.txt',
            'txt': '.txt',
            'json': '.json',
            'markdown': '.md',
            'md': '.md',
        }
        return formats.get(format_type.lower(), '.txt')
    
    def _write_pdf(self, path: str, content: str, title: str = "", template: str = ""):
        """
        Create professional PDF file using Evidence Document System.
        
        Templates disponibles (sans marques):
        - consulting_premium: Rapport stratégique haut de gamme
        - legal_formal: Document juridique (tribunal/greffe)
        - scientific_academic: Publication scientifique
        - patent_ip: Brevet / Propriété intellectuelle
        - financial_audit: Rapport financier/audit
        - executive_brief: Note de synthèse executive
        - medical_clinical: Rapport médical/clinique
        - technical_doc: Documentation technique
        - standard: Document professionnel polyvalent
        
        Templates KOREV Evidence:
        - consulting_premium: Rapport stratégique premium
        - legal_formal: Document juridique
        - scientific_academic: Publication académique
        - patent -> patent_ip
        - financial -> financial_audit
        - executive -> executive_brief
        - medical -> medical_clinical
        - technical -> technical_doc
        """
        # Template mapping for backwards compatibility (legacy names)
        template_map = {
            "strategy": "consulting_premium",
            "strategic": "consulting_premium",
            "consulting": "consulting_premium",
            "legal": "legal_formal",
            "scientific": "scientific_academic",
            "patent": "patent_ip",
            "financial": "financial_audit",
            "executive": "executive_brief",
            "medical": "medical_clinical",
            "technical": "technical_doc",
        }
        
        # Normalize template name
        normalized_template = template_map.get(template, template) if template else ""
        
        # ═══════════════════════════════════════════════════════════════════
        # PRIMARY: WeasyPrint engine (PRISM branded, Playfair Display)
        # ═══════════════════════════════════════════════════════════════════
        try:
            from python.helpers.evidence_pdf_engine import markdown_to_pdf
            
            PrintStyle(font_color="cyan").print(
                f"[FileWriter] PDF via PRISM engine: {len(content)} chars, template={normalized_template or 'auto'}"
            )
            
            # Detect header_right from template
            header_map = {
                "consulting_premium": "Rapport Stratégique",
                "legal_formal": "Document Juridique",
                "scientific_academic": "Publication Scientifique",
                "patent_ip": "Brevet / PI",
                "financial_audit": "Rapport Financier",
                "executive_brief": "Note Executive",
                "medical_clinical": "Document Médical",
                "technical_doc": "Documentation Technique",
            }
            header_right = header_map.get(normalized_template, "Document")
            
            markdown_to_pdf(
                content=content,
                output_path=path,
                title=title if title else None,
                header_right=header_right,
            )
            
            PrintStyle(font_color="green").print(
                f"[FileWriter] PDF generated (PRISM/WeasyPrint)"
            )
            
        except Exception as e:
            PrintStyle(font_color="yellow").print(f"[FileWriter] PRISM engine failed: {e}, trying legacy...")
            
            # FALLBACK 1: evidence_document (ReportLab AST)
            try:
                from python.helpers.evidence_document import parse_markdown, render_to_file
                
                doc = parse_markdown(
                    content=content,
                    title=title if title else None,
                    template=normalized_template if normalized_template else None,
                    author="KOREV Evidence"
                )
                render_to_file(doc, path)
                
                PrintStyle(font_color="green").print(f"[FileWriter] PDF generated (evidence_document fallback)")
                
            except Exception as e2:
                PrintStyle(font_color="yellow").print(f"[FileWriter] evidence_document failed: {e2}, trying legacy...")
                
                # FALLBACK 2: legacy pdf_generator
                try:
                    from python.helpers.pdf_generator import generate_pdf
                    
                    generate_pdf(
                        content=content,
                        output_path=path,
                        title=title if title else None,
                        author="KOREV Evidence",
                        template_name=normalized_template if normalized_template else None
                    )
                    
                    PrintStyle(font_color="green").print(f"[FileWriter] PDF generated (legacy fallback)")
                    
                except Exception as e3:
                    PrintStyle(font_color="red").print(f"[FileWriter] All PDF engines failed: {e3}")
                    self._write_text(path.replace('.pdf', '.txt'), content)
                    raise Exception(f"PDF generation failed. Created .txt instead. Error: {e3}")
    
    def _write_csv(self, path: str, content: str):
        """Create CSV file."""
        import csv
        
        # Parse content as rows (newline-separated, comma-separated)
        with open(path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            for line in content.strip().split('\n'):
                # Handle both comma and semicolon separators
                if ';' in line and ',' not in line:
                    row = [cell.strip() for cell in line.split(';')]
                else:
                    row = [cell.strip() for cell in line.split(',')]
                writer.writerow(row)
    
    def _write_excel(self, path: str, content: str):
        """Create Excel file."""
        import pandas as pd
        
        # Parse content as rows
        rows = []
        for line in content.strip().split('\n'):
            if ';' in line and ',' not in line:
                row = [cell.strip() for cell in line.split(';')]
            else:
                row = [cell.strip() for cell in line.split(',')]
            rows.append(row)
        
        # First row as header
        if rows:
            df = pd.DataFrame(rows[1:], columns=rows[0] if rows else None)
            df.to_excel(path, index=False)
        else:
            pd.DataFrame().to_excel(path, index=False)
    
    def _write_text(self, path: str, content: str):
        """Create text file."""
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)
