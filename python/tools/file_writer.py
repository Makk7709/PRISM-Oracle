"""
File Writer Tool — Create files (PDF, CSV, Excel, text).

This tool provides a simple interface for creating common file formats
without requiring the agent to write Python code.
"""

import os
from datetime import datetime
from python.helpers.tool import Tool, Response
from python.helpers import files
from python.helpers.print_style import PrintStyle


class FileWriter(Tool):
    """
    Simple file writer for common formats.
    Supports: PDF, CSV, Excel, TXT, JSON, Markdown
    """

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
        
        # Ensure output directory exists
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
            
            return Response(
                message=f"✅ File created successfully!\n\n"
                        f"**Filename:** {final_filename}\n"
                        f"**Path:** {output_path}\n"
                        f"**Size:** {os.path.getsize(output_path)} bytes",
                break_loop=False
            )
            
        except Exception as e:
            return Response(
                message=f"Error creating file: {e}",
                break_loop=False
            )
    
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
        
        Legacy mappings (pour compatibilité):
        - mckinsey -> consulting_premium
        - legal -> legal_formal
        - scientific -> scientific_academic
        - patent -> patent_ip
        - financial -> financial_audit
        - executive -> executive_brief
        - medical -> medical_clinical
        - technical -> technical_doc
        """
        # Template mapping for backwards compatibility
        template_map = {
            "mckinsey": "consulting_premium",
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
        
        try:
            from python.helpers.evidence_document import parse_markdown, render_to_file
            
            PrintStyle(font_color="cyan").print(
                f"[FileWriter] PDF content: {len(content)} chars, template={normalized_template or 'auto'}"
            )
            
            # Parse markdown to Document AST
            doc = parse_markdown(
                content=content,
                title=title if title else None,
                template=normalized_template if normalized_template else None,
                author="Korev Evidence"
            )
            
            # Render to file
            render_to_file(doc, path)
            
            PrintStyle(font_color="green").print(
                f"[FileWriter] PDF generated: {doc.template} template, {len(doc.elements)} elements"
            )
            
        except Exception as e:
            PrintStyle(font_color="yellow").print(f"[FileWriter] New system failed: {e}, trying legacy...")
            
            # Fallback to legacy pdf_generator
            try:
                from python.helpers.pdf_generator import generate_pdf
                
                generate_pdf(
                    content=content,
                    output_path=path,
                    title=title if title else None,
                    author="Korev Evidence",
                    template_name=normalized_template if normalized_template else None
                )
                
                PrintStyle(font_color="green").print(f"[FileWriter] PDF generated (legacy)")
                
            except Exception as e2:
                PrintStyle(font_color="red").print(f"[FileWriter] PDF error: {e2}")
                # Final fallback
                self._write_text(path.replace('.pdf', '.txt'), content)
                raise Exception(f"PDF generation failed. Created .txt instead. Error: {e2}")
    
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
