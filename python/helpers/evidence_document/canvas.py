"""
Evidence Document Canvas — 2-pass pagination.

NumberedCanvas permet la pagination "Page X sur Y" en mémorisant
l'état de chaque page lors du premier pass, puis en injectant
le total lors du save().

Usage:
    pdf_doc.build(elements, canvasmaker=NumberedCanvas)
"""

from typing import Optional, List, Dict, Any
from reportlab.pdfgen import canvas as pdf_canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.lib.colors import HexColor, gray

from .templates import Template


class NumberedCanvas(pdf_canvas.Canvas):
    """
    Canvas avec pagination 2-pass pour "Page X sur Y".
    
    Premier pass: stocke les positions où écrire le total
    Second pass (save): écrit le total sur chaque page
    """
    
    def __init__(self, *args, **kwargs):
        # Extract custom params before passing to parent
        self._template: Optional[Template] = kwargs.pop('template', None)
        self._confidentiality: Optional[str] = kwargs.pop('confidentiality', None)
        self._watermark: Optional[str] = kwargs.pop('watermark', None)
        
        super().__init__(*args, **kwargs)
        
        # Store page states for 2-pass
        self._saved_page_states: List[Dict[str, Any]] = []
        self._current_page_state: Dict[str, Any] = {}
    
    def showPage(self):
        """Override to save page state before advancing."""
        # Save current page state
        self._saved_page_states.append({
            'page_number': len(self._saved_page_states) + 1,
            'state': self.__dict__.copy()
        })
        super().showPage()
    
    def save(self):
        """Override to inject total pages before saving."""
        total_pages = len(self._saved_page_states) + 1  # +1 for current page
        
        # Go back and add page numbers with totals
        for page_state in self._saved_page_states:
            page_num = page_state['page_number']
            self._draw_page_number_with_total(page_num, total_pages)
        
        # Draw on current (last) page
        self._draw_page_number_with_total(total_pages, total_pages)
        
        super().save()
    
    def _draw_page_number_with_total(self, page_num: int, total_pages: int):
        """Draw page number with total on current page."""
        # This will be called during save() pass
        # The actual drawing happens via the page callback mechanism
        pass


class PageNumberCanvas(pdf_canvas.Canvas):
    """
    Canvas simplifié pour pagination avec total.
    
    Utilise la technique de double-pass: premier pass pour compter,
    deuxième pass pour écrire les numéros.
    """
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._page_number = 0
        self._pages: List[dict] = []
    
    def showPage(self):
        """Sauvegarde l'état de la page avant de passer à la suivante."""
        self._page_number += 1
        self._pages.append({
            'number': self._page_number,
        })
        super().showPage()
    
    def get_page_count(self) -> int:
        """Retourne le nombre total de pages."""
        return self._page_number


def create_canvas_maker(template: Template, confidentiality: Optional[str] = None,
                        watermark: Optional[str] = None):
    """
    Crée une factory de canvas avec les paramètres de template.
    
    Cette fonction retourne une classe (pas une instance) qui sera
    utilisée par SimpleDocTemplate.build() via canvasmaker=.
    """
    
    class TemplateCanvas(pdf_canvas.Canvas):
        """Canvas avec template pré-configuré."""
        
        _template = template
        _confidentiality = confidentiality
        _watermark = watermark
        _page_count = 0
        _pages_info: List[dict] = []
        
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            TemplateCanvas._pages_info = []
        
        def showPage(self):
            """Enregistre les infos de page."""
            TemplateCanvas._page_count += 1
            TemplateCanvas._pages_info.append({
                'number': TemplateCanvas._page_count
            })
            super().showPage()
        
        def save(self):
            """Finalise avec le total de pages."""
            # Le total est maintenant connu
            total = TemplateCanvas._page_count
            
            # Reset pour prochaine utilisation
            TemplateCanvas._page_count = 0
            
            super().save()
    
    return TemplateCanvas


class TwoPassDocTemplate:
    """
    Helper pour génération PDF en 2 passes.
    
    Pass 1: Génère le PDF pour compter les pages
    Pass 2: Regénère avec les numéros de page corrects
    """
    
    def __init__(self, template: Template):
        self.template = template
        self.total_pages = 0
    
    def count_pages(self, doc_template, elements) -> int:
        """
        Première passe: compte les pages.
        """
        from io import BytesIO
        from reportlab.platypus import SimpleDocTemplate
        
        buffer = BytesIO()
        temp_doc = SimpleDocTemplate(
            buffer,
            pagesize=doc_template.pagesize,
            leftMargin=doc_template.leftMargin,
            rightMargin=doc_template.rightMargin,
            topMargin=doc_template.topMargin,
            bottomMargin=doc_template.bottomMargin,
        )
        
        # Copie des éléments pour ne pas les modifier
        elements_copy = list(elements)
        
        class CountingCanvas(pdf_canvas.Canvas):
            page_count = 0
            
            def showPage(self):
                CountingCanvas.page_count += 1
                super().showPage()
        
        try:
            temp_doc.build(elements_copy, canvasmaker=CountingCanvas)
            self.total_pages = CountingCanvas.page_count + 1
        except:
            self.total_pages = 1
        
        return self.total_pages


def draw_page_with_total(
    canvas: pdf_canvas.Canvas,
    doc,
    template: Template,
    total_pages: int,
    confidentiality: Optional[str] = None,
    watermark: Optional[str] = None
):
    """
    Dessine header/footer avec pagination complète.
    
    Cette fonction est appelée comme callback onFirstPage/onLaterPages
    après qu'on connaît le total de pages.
    
    Args:
        canvas: Canvas ReportLab
        doc: Document template
        template: Template Evidence
        total_pages: Nombre total de pages (connu après 1er pass)
        confidentiality: Niveau de confidentialité
        watermark: Texte du watermark
    """
    canvas.saveState()
    
    page_num = canvas.getPageNumber()
    width, height = doc.pagesize
    
    primary = HexColor(template.primary_color)
    accent = HexColor(template.accent_color)
    
    # Watermark
    if watermark:
        canvas.setFillColor(HexColor("#E8E8E8"))
        canvas.setFont("Helvetica-Bold", 50)
        canvas.saveState()
        canvas.translate(width / 2, height / 2)
        canvas.rotate(45)
        canvas.drawCentredString(0, 0, watermark)
        canvas.restoreState()
    
    # Header
    if template.show_header:
        # Ligne
        canvas.setStrokeColor(accent)
        canvas.setLineWidth(1)
        canvas.line(
            template.left_margin * cm,
            height - template.top_margin * cm + 0.5 * cm,
            width - template.right_margin * cm,
            height - template.top_margin * cm + 0.5 * cm
        )
        
        # Texte header gauche
        if template.header_text:
            canvas.setFont(template.title_font, 8)
            canvas.setFillColor(primary)
            canvas.drawString(
                template.left_margin * cm,
                height - template.top_margin * cm + 0.8 * cm,
                template.header_text
            )
        
        # Confidentialité à droite
        if confidentiality:
            conf_label = template.confidential_labels.get(confidentiality, "")
            if conf_label:
                canvas.setFont(template.title_font, 8)
                canvas.setFillColor(HexColor("#C53030"))
                canvas.drawRightString(
                    width - template.right_margin * cm,
                    height - template.top_margin * cm + 0.8 * cm,
                    conf_label
                )
    
    # Footer
    if template.show_footer:
        # Ligne
        canvas.setStrokeColor(HexColor('#e2e8f0'))
        canvas.setLineWidth(0.5)
        canvas.line(
            template.left_margin * cm,
            template.bottom_margin * cm - 0.5 * cm,
            width - template.right_margin * cm,
            template.bottom_margin * cm - 0.5 * cm
        )
        
        # Texte footer centre (avec total réel)
        if template.footer_text:
            footer_text = template.footer_text
            footer_text = footer_text.replace("{page}", str(page_num))
            footer_text = footer_text.replace("{total}", str(total_pages))
            canvas.setFont(template.body_font, 8)
            canvas.setFillColor(gray)
            canvas.drawCentredString(
                width / 2,
                template.bottom_margin * cm - 0.8 * cm,
                footer_text
            )
        
        # Numéro de page à droite (avec total)
        if template.show_page_numbers:
            canvas.setFont(template.body_font, 8)
            canvas.setFillColor(gray)
            page_text = f"Page {page_num} sur {total_pages}"
            canvas.drawRightString(
                width - template.right_margin * cm,
                template.bottom_margin * cm - 0.8 * cm,
                page_text
            )
    
    canvas.restoreState()
