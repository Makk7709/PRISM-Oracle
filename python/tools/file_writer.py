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
            if ext == '.pdf':
                self._write_pdf(output_path, content, title)
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
    
    def _write_pdf(self, path: str, content: str, title: str = ""):
        """Create professional PDF file with full Markdown support."""
        try:
            from python.helpers.pdf_generator import generate_pdf
            
            # Use the professional PDF generator
            generate_pdf(
                content=content,
                output_path=path,
                title=title if title else None,
                author="Korev Evidence"
            )
            
        except ImportError as e:
            # Fallback to basic reportlab if pdf_generator fails
            try:
                from reportlab.lib.pagesizes import A4
                from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
                from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
                
                doc = SimpleDocTemplate(path, pagesize=A4)
                styles = getSampleStyleSheet()
                story = []
                
                if title:
                    title_style = ParagraphStyle(
                        'Title',
                        parent=styles['Heading1'],
                        fontSize=18,
                        spaceAfter=30
                    )
                    story.append(Paragraph(title, title_style))
                
                for para in content.split('\n\n'):
                    if para.strip():
                        if para.startswith('# '):
                            story.append(Paragraph(para[2:], styles['Heading1']))
                        elif para.startswith('## '):
                            story.append(Paragraph(para[3:], styles['Heading2']))
                        elif para.startswith('### '):
                            story.append(Paragraph(para[4:], styles['Heading3']))
                        else:
                            story.append(Paragraph(para.replace('\n', '<br/>'), styles['Normal']))
                        story.append(Spacer(1, 12))
                
                doc.build(story)
                
            except ImportError:
                self._write_text(path.replace('.pdf', '.txt'), content)
                raise Exception("reportlab not installed. Created .txt instead.")
    
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
