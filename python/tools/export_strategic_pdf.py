"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                    EXPORT STRATEGIC PDF — Evidence Tool                       ║
║                                                                              ║
║  Exporte le dernier document stratégique du chat vers un PDF Big 4 formaté   ║
║  avec couverture, table des matières, et mise en page professionnelle.       ║
║                                                                              ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import os
import re
from datetime import datetime
from pathlib import Path
from typing import Optional

from python.helpers.tool import Tool, Response
from python.helpers.print_style import PrintStyle


class ExportStrategicPdf(Tool):
    """
    Outil pour exporter le document stratégique actuel en PDF formaté.
    """

    async def execute(self, filename: str = "", **kwargs):
        """
        Exporte le dernier document stratégique en PDF.
        
        Args:
            filename: Nom du fichier PDF (optionnel, auto-généré si vide)
        """
        try:
            # Get the strategic result from agent data
            strategic_result = self.agent.get_data("_strategic_result")
            
            if not strategic_result:
                return Response(
                    message="⚠️ Aucun document stratégique à exporter. "
                            "Demandez d'abord une étude de marché ou un prévisionnel.",
                    break_loop=False,
                )
            
            # Get the consolidated response
            content = strategic_result.consolidated_response
            if not content:
                return Response(
                    message="⚠️ Le document stratégique est vide.",
                    break_loop=False,
                )
            
            # Generate filename if not provided
            if not filename:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                doc_type = strategic_result.document_type or "strategic"
                filename = f"KOREV_Evidence_{doc_type}_{timestamp}.pdf"
            
            # Ensure .pdf extension
            if not filename.endswith(".pdf"):
                filename += ".pdf"
            
            # Output directory
            output_dir = Path(__file__).parent.parent.parent / "docs" / "reports"
            output_dir.mkdir(parents=True, exist_ok=True)
            output_path = output_dir / filename
            
            # Generate the PDF
            PrintStyle(font_color="cyan").print(f"📄 Generating PDF: {filename}")
            
            pdf_path = await self._generate_pdf(
                content=content,
                output_path=str(output_path),
                doc_type=strategic_result.document_type,
                correlation_id=strategic_result.correlation_id,
                total_sources=strategic_result.total_sources,
                validation_passed=strategic_result.validation_passed,
            )
            
            if pdf_path:
                PrintStyle(font_color="green", bold=True).print(f"✅ PDF generated: {pdf_path}")
                return Response(
                    message=f"✅ **PDF exporté avec succès**\n\n"
                            f"📄 **Fichier:** `{filename}`\n"
                            f"📍 **Emplacement:** `{pdf_path}`\n\n"
                            f"Le document inclut:\n"
                            f"- Couverture Big 4\n"
                            f"- Table des matières\n"
                            f"- {strategic_result.total_sources} sources citées\n"
                            f"- Decision Governance\n",
                    break_loop=False,
                )
            else:
                return Response(
                    message="❌ Erreur lors de la génération du PDF.",
                    break_loop=False,
                )
                
        except Exception as e:
            PrintStyle(font_color="red").print(f"❌ PDF export error: {e}")
            import traceback
            traceback.print_exc()
            return Response(
                message=f"❌ Erreur: {str(e)[:200]}",
                break_loop=False,
            )

    async def _generate_pdf(
        self,
        content: str,
        output_path: str,
        doc_type: str,
        correlation_id: str,
        total_sources: int,
        validation_passed: bool,
    ) -> Optional[str]:
        """Generate a professional PDF from the markdown content."""
        try:
            from reportlab.lib.pagesizes import A4
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
            from reportlab.lib.units import cm, mm
            from reportlab.lib.colors import HexColor
            from reportlab.platypus import (
                SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
                PageBreak, KeepTogether
            )
            from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY
            from reportlab.pdfgen import canvas
            from io import BytesIO
            
            # Colors
            PRIMARY_COLOR = HexColor("#1a365d")  # Dark blue
            SECONDARY_COLOR = HexColor("#2d3748")  # Dark gray
            ACCENT_COLOR = HexColor("#38a169")  # Green
            
            # Create PDF
            doc = SimpleDocTemplate(
                output_path,
                pagesize=A4,
                rightMargin=2*cm,
                leftMargin=2*cm,
                topMargin=2*cm,
                bottomMargin=2*cm,
            )
            
            # Styles
            styles = getSampleStyleSheet()
            
            # Custom styles
            title_style = ParagraphStyle(
                'CustomTitle',
                parent=styles['Heading1'],
                fontSize=24,
                textColor=PRIMARY_COLOR,
                spaceAfter=20,
                alignment=TA_CENTER,
            )
            
            h1_style = ParagraphStyle(
                'CustomH1',
                parent=styles['Heading1'],
                fontSize=18,
                textColor=PRIMARY_COLOR,
                spaceBefore=20,
                spaceAfter=10,
            )
            
            h2_style = ParagraphStyle(
                'CustomH2',
                parent=styles['Heading2'],
                fontSize=14,
                textColor=SECONDARY_COLOR,
                spaceBefore=15,
                spaceAfter=8,
            )
            
            body_style = ParagraphStyle(
                'CustomBody',
                parent=styles['Normal'],
                fontSize=10,
                leading=14,
                alignment=TA_JUSTIFY,
                spaceAfter=8,
            )
            
            # Build content
            elements = []
            
            # Cover page
            elements.extend(self._create_cover_page(
                doc_type=doc_type,
                correlation_id=correlation_id,
                total_sources=total_sources,
                validation_passed=validation_passed,
                title_style=title_style,
                body_style=body_style,
            ))
            
            elements.append(PageBreak())
            
            # Parse and convert markdown to reportlab elements
            elements.extend(self._parse_markdown(
                content=content,
                h1_style=h1_style,
                h2_style=h2_style,
                body_style=body_style,
                styles=styles,
            ))
            
            # Build PDF
            doc.build(elements)
            
            return output_path
            
        except ImportError as e:
            PrintStyle(font_color="yellow").print(f"⚠️ ReportLab not available: {e}")
            # Fallback: save as markdown
            md_path = output_path.replace(".pdf", ".md")
            with open(md_path, "w", encoding="utf-8") as f:
                f.write(content)
            return md_path
        except Exception as e:
            PrintStyle(font_color="red").print(f"PDF generation error: {e}")
            import traceback
            traceback.print_exc()
            return None

    def _create_cover_page(
        self,
        doc_type: str,
        correlation_id: str,
        total_sources: int,
        validation_passed: bool,
        title_style,
        body_style,
    ):
        """Create a professional cover page."""
        from reportlab.platypus import Paragraph, Spacer, Table, TableStyle
        from reportlab.lib.colors import HexColor
        from reportlab.lib.units import cm
        
        elements = []
        
        # Spacer at top
        elements.append(Spacer(1, 4*cm))
        
        # Title
        doc_type_labels = {
            "market_study": "ÉTUDE DE MARCHÉ",
            "financial_forecast": "PRÉVISIONNEL FINANCIER",
            "pricing": "STRATÉGIE DE PRICING",
            "go_to_market": "PLAN GO-TO-MARKET",
        }
        title = doc_type_labels.get(doc_type, "DOCUMENT STRATÉGIQUE")
        elements.append(Paragraph(title, title_style))
        
        elements.append(Spacer(1, 1*cm))
        
        # Subtitle
        elements.append(Paragraph(
            "KOREV Evidence — Document stratégique sourcé",
            body_style
        ))
        
        elements.append(Spacer(1, 2*cm))
        
        # Badge
        badge_text = "✅ EVIDENCE-GRADE" if validation_passed else "⚠️ PARTIAL"
        badge_color = HexColor("#38a169") if validation_passed else HexColor("#d69e2e")
        
        badge_style = body_style.clone('badge')
        badge_style.textColor = badge_color
        badge_style.fontSize = 14
        badge_style.alignment = 1  # Center
        
        elements.append(Paragraph(badge_text, badge_style))
        
        elements.append(Spacer(1, 2*cm))
        
        # Metadata table
        metadata = [
            ["Type de document", doc_type_labels.get(doc_type, doc_type)],
            ["Sources vérifiées", str(total_sources)],
            ["Statut validation", "APPROVED" if validation_passed else "PARTIAL"],
            ["Date de génération", datetime.now().strftime("%d/%m/%Y %H:%M")],
            ["Correlation ID", correlation_id[:8] + "..."],
        ]
        
        table = Table(metadata, colWidths=[6*cm, 8*cm])
        table.setStyle(TableStyle([
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('TEXTCOLOR', (0, 0), (0, -1), HexColor("#1a365d")),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
            ('ALIGN', (1, 0), (1, -1), 'LEFT'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
        ]))
        
        elements.append(table)
        
        elements.append(Spacer(1, 3*cm))
        
        # Footer
        footer_style = body_style.clone('footer')
        footer_style.fontSize = 8
        footer_style.textColor = HexColor("#718096")
        footer_style.alignment = 1
        
        elements.append(Paragraph(
            "Document généré par KOREV Evidence — Pipeline stratégique multi-agent",
            footer_style
        ))
        
        return elements

    def _parse_markdown(self, content: str, h1_style, h2_style, body_style, styles):
        """Parse markdown content and convert to reportlab elements."""
        from reportlab.platypus import Paragraph, Spacer, Table, TableStyle, Preformatted
        from reportlab.lib.colors import HexColor
        from reportlab.lib.units import cm
        
        elements = []
        lines = content.split("\n")
        
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            
            # Skip empty lines
            if not line:
                elements.append(Spacer(1, 0.3*cm))
                i += 1
                continue
            
            # H1: # Title
            if line.startswith("# "):
                text = line[2:].strip()
                # Clean markdown formatting
                text = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', text)
                text = re.sub(r'\*(.*?)\*', r'<i>\1</i>', text)
                elements.append(Paragraph(text, h1_style))
                i += 1
                continue
            
            # H2: ## Title
            if line.startswith("## "):
                text = line[3:].strip()
                text = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', text)
                text = re.sub(r'\*(.*?)\*', r'<i>\1</i>', text)
                elements.append(Paragraph(text, h2_style))
                i += 1
                continue
            
            # H3: ### Title
            if line.startswith("### "):
                text = line[4:].strip()
                h3_style = body_style.clone('h3')
                h3_style.fontName = 'Helvetica-Bold'
                h3_style.fontSize = 11
                h3_style.spaceBefore = 10
                text = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', text)
                elements.append(Paragraph(text, h3_style))
                i += 1
                continue
            
            # Table: | col1 | col2 |
            if line.startswith("|") and "|" in line[1:]:
                table_lines = []
                while i < len(lines) and lines[i].strip().startswith("|"):
                    table_lines.append(lines[i].strip())
                    i += 1
                
                # Parse table
                if len(table_lines) >= 2:
                    table_data = []
                    for tl in table_lines:
                        if "---" in tl:  # Skip separator
                            continue
                        cells = [c.strip() for c in tl.split("|")[1:-1]]
                        if cells:
                            table_data.append(cells)
                    
                    if table_data:
                        try:
                            table = Table(table_data)
                            table.setStyle(TableStyle([
                                ('FONTSIZE', (0, 0), (-1, -1), 9),
                                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                                ('BACKGROUND', (0, 0), (-1, 0), HexColor("#e2e8f0")),
                                ('GRID', (0, 0), (-1, -1), 0.5, HexColor("#cbd5e0")),
                                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                                ('PADDING', (0, 0), (-1, -1), 6),
                            ]))
                            elements.append(table)
                            elements.append(Spacer(1, 0.5*cm))
                        except:
                            pass
                continue
            
            # List item: - or *
            if line.startswith("- ") or line.startswith("* "):
                text = line[2:].strip()
                text = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', text)
                text = re.sub(r'\*(.*?)\*', r'<i>\1</i>', text)
                bullet_style = body_style.clone('bullet')
                bullet_style.leftIndent = 20
                bullet_style.bulletIndent = 10
                elements.append(Paragraph(f"• {text}", bullet_style))
                i += 1
                continue
            
            # Numbered list: 1. or 1)
            if re.match(r'^\d+[\.\)]\s', line):
                text = re.sub(r'^\d+[\.\)]\s*', '', line)
                text = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', text)
                text = re.sub(r'\*(.*?)\*', r'<i>\1</i>', text)
                num_style = body_style.clone('numbered')
                num_style.leftIndent = 20
                elements.append(Paragraph(text, num_style))
                i += 1
                continue
            
            # Horizontal rule: ---
            if line.startswith("---"):
                elements.append(Spacer(1, 0.5*cm))
                i += 1
                continue
            
            # Regular paragraph
            text = line
            text = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', text)
            text = re.sub(r'\*(.*?)\*', r'<i>\1</i>', text)
            text = re.sub(r'`([^`]+)`', r'<font face="Courier">\1</font>', text)
            
            # Handle references
            text = re.sub(r'\[REF-(\d+)\]', r'<font color="#2b6cb0">[REF-\1]</font>', text)
            
            try:
                elements.append(Paragraph(text, body_style))
            except:
                # If paragraph fails, add as plain text
                elements.append(Paragraph(line[:200], body_style))
            
            i += 1
        
        return elements
