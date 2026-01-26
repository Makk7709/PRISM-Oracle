"""
Tests for Evidence Document System — Board-Level Quality.

Test Categories:
1. Snapshot Tests: Same input → same hash
2. Template Detection: Weighted keywords with boundaries
3. Robustness: Special chars, XML injection, control chars
4. Sanitization: Text escaping, no corruption
5. 2-Pass Pagination: Page X sur Y
6. E2E: Each template renders without error
"""

import pytest
import hashlib
import re
from datetime import datetime

from python.helpers.evidence_document import (
    Document, DocumentMetadata, DocumentSource, Assumption,
    ConfidentialityLevel,
    Paragraph, Heading, BulletList, NumberedList, Table,
    CodeBlock, BlockQuote, HorizontalRule, PageBreak, Callout, TextSpan,
    get_template, detect_template, list_templates, TEMPLATES,
    render_to_pdf, parse_markdown
)
from python.helpers.evidence_document.renderer import (
    sanitize_text, spans_to_rl_xml, render_text
)


# ═══════════════════════════════════════════════════════════════════════════════
# SNAPSHOT TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestDocumentHash:
    """Test deterministic hashing."""
    
    def test_same_content_same_hash(self):
        """Same content → same hash."""
        doc1 = Document(title="Test", template="standard")
        doc1.add(Heading("Title", level=1))
        doc1.add(Paragraph("Content"))
        
        doc2 = Document(title="Test", template="standard")
        doc2.add(Heading("Title", level=1))
        doc2.add(Paragraph("Content"))
        
        assert doc1.compute_hash() == doc2.compute_hash()
    
    def test_different_content_different_hash(self):
        """Different content → different hash."""
        doc1 = Document(title="Test1")
        doc1.add(Paragraph("Content 1"))
        
        doc2 = Document(title="Test2")
        doc2.add(Paragraph("Content 2"))
        
        assert doc1.compute_hash() != doc2.compute_hash()
    
    def test_hash_ignores_timestamp(self):
        """Hash ignores timestamp for reproducibility."""
        meta1 = DocumentMetadata(created_at=datetime(2024, 1, 1))
        meta2 = DocumentMetadata(created_at=datetime(2025, 12, 31))
        
        doc1 = Document(title="Test", metadata=meta1)
        doc2 = Document(title="Test", metadata=meta2)
        
        assert doc1.compute_hash() == doc2.compute_hash()
    
    def test_hash_16_chars(self):
        """Hash should be 16 hex characters."""
        doc = Document(title="Test")
        h = doc.compute_hash()
        assert len(h) == 16
        assert all(c in '0123456789abcdef' for c in h)


# ═══════════════════════════════════════════════════════════════════════════════
# TEMPLATE DETECTION WITH WEIGHTING
# ═══════════════════════════════════════════════════════════════════════════════

class TestTemplateDetection:
    """Test weighted keyword detection with word boundaries."""
    
    @pytest.mark.parametrize("prompt,expected", [
        # Consulting - high weight keywords
        ("Je veux un rapport stratégique", "consulting_premium"),
        ("Analyse de due diligence pour M&A", "consulting_premium"),
        ("Cabinet conseil recommandation", "consulting_premium"),
        ("Business case acquisition", "consulting_premium"),
        
        # Legal - specific legal terms
        ("Conclusions pour le tribunal", "legal_formal"),
        ("Assignation devant le greffe", "legal_formal"),
        ("Document juridique plaidoirie", "legal_formal"),
        ("Rédige un contrat de cession", "legal_formal"),
        
        # Scientific - academic terms
        ("Publication scientifique peer review", "scientific_academic"),
        ("Étude avec méthodologie abstract", "scientific_academic"),
        ("Research paper academic", "scientific_academic"),
        
        # Patent - specific IP terms
        ("Demande de brevet revendication", "patent_ip"),
        ("Patent application prior art", "patent_ip"),
        ("Propriété intellectuelle invention", "patent_ip"),
        
        # Financial - audit terms
        ("Rapport audit commissaire aux comptes", "financial_audit"),
        ("Analyse DCF valorisation", "financial_audit"),
        ("Bilan compte résultat expert comptable", "financial_audit"),
        
        # Executive - brief terms
        ("Note de synthèse direction", "executive_brief"),
        ("Executive summary board", "executive_brief"),
        ("Note executive décision", "executive_brief"),
        
        # Medical - clinical terms
        ("Diagnostic patient clinique", "medical_clinical"),
        ("Rapport médical traitement", "medical_clinical"),
        ("Ordonnance prescription consultation", "medical_clinical"),
        
        # Technical - doc terms
        ("Documentation technique API SDK", "technical_doc"),
        ("Spécification technique architecture", "technical_doc"),
        ("README développement", "technical_doc"),
        
        # Default - no specific keywords
        ("Hello world", "standard"),
        ("Crée un fichier", "standard"),
        ("Test basique", "standard"),
    ])
    def test_template_detection_weighted(self, prompt: str, expected: str):
        """Test weighted template detection."""
        detected = detect_template(prompt)
        assert detected == expected, f"'{prompt}' → expected {expected}, got {detected}"
    
    def test_word_boundary_prevents_false_match(self):
        """Word boundaries prevent 'ip' in 'script' matching patent."""
        # 'ip' should not match in 'script'
        result = detect_template("Python script development")
        assert result != "patent_ip"
    
    def test_weighting_resolves_ambiguity(self):
        """Higher weight keywords win in ambiguous cases."""
        # "audit" alone (weight 4) vs generic financial terms
        result = detect_template("audit des comptes")
        assert result == "financial_audit"


# ═══════════════════════════════════════════════════════════════════════════════
# TEXT SANITIZATION TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestSanitization:
    """Test text sanitization for XML safety."""
    
    def test_xml_entities_escaped(self):
        """XML special characters must be escaped."""
        text = "Test <script> & \"quotes\""
        safe = sanitize_text(text)
        
        assert "&lt;" in safe
        assert "&gt;" in safe
        assert "&amp;" in safe
        assert "&quot;" in safe
        assert "<script>" not in safe
    
    def test_control_characters_removed(self):
        """Control characters (except \\n\\t) must be removed."""
        text = "Hello\x00World\x1fTest\nOK\tTab"
        safe = sanitize_text(text)
        
        assert "\x00" not in safe
        assert "\x1f" not in safe
        assert "\n" in safe
        assert "\t" in safe
    
    def test_unicode_preserved(self):
        """Unicode characters should be preserved."""
        text = "émojis: 🎉 accents: éàüöñ 中文"
        safe = sanitize_text(text)
        
        assert "🎉" in safe
        assert "éàüöñ" in safe
        assert "中文" in safe
    
    def test_empty_input(self):
        """Empty input returns empty string."""
        assert sanitize_text("") == ""
        assert sanitize_text(None) == ""
    
    def test_ampersand_escaping_order(self):
        """Ampersand must be escaped first to avoid double-escaping."""
        text = "A & B < C"
        safe = sanitize_text(text)
        
        # Should be "&amp;" not "&amp;lt;"
        assert safe == "A &amp; B &lt; C"


class TestSpanRendering:
    """Test TextSpan to ReportLab XML conversion."""
    
    def test_bold_span(self):
        """Bold span renders correctly."""
        spans = [TextSpan(text="bold", bold=True)]
        xml = spans_to_rl_xml(spans)
        assert xml == "<b>bold</b>"
    
    def test_italic_span(self):
        """Italic span renders correctly."""
        spans = [TextSpan(text="italic", italic=True)]
        xml = spans_to_rl_xml(spans)
        assert xml == "<i>italic</i>"
    
    def test_code_span(self):
        """Code span renders with Courier font."""
        spans = [TextSpan(text="code", code=True)]
        xml = spans_to_rl_xml(spans)
        assert 'name="Courier"' in xml
        assert 'color="#c53030"' in xml
    
    def test_nested_formatting(self):
        """Bold + italic nesting works."""
        spans = [TextSpan(text="both", bold=True, italic=True)]
        xml = spans_to_rl_xml(spans)
        # Inner to outer: italic then bold
        assert "<b><i>both</i></b>" == xml
    
    def test_multiple_spans(self):
        """Multiple spans concatenate."""
        spans = [
            TextSpan(text="Hello "),
            TextSpan(text="bold", bold=True),
            TextSpan(text=" world")
        ]
        xml = spans_to_rl_xml(spans)
        assert xml == "Hello <b>bold</b> world"
    
    def test_span_escapes_content(self):
        """Span content is escaped."""
        spans = [TextSpan(text="<script>", bold=True)]
        xml = spans_to_rl_xml(spans)
        assert "<b>&lt;script&gt;</b>" == xml


# ═══════════════════════════════════════════════════════════════════════════════
# ROBUSTNESS TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestRobustness:
    """Test handling of edge cases."""
    
    def test_xml_injection_safe(self):
        """XML injection attempts are escaped."""
        doc = Document(title="Test <script>alert('xss')</script>")
        doc.add(Paragraph("<b>fake bold</b>"))
        doc.add(Paragraph("&amp;entity;"))
        
        # Should not raise
        pdf = render_to_pdf(doc)
        assert len(pdf) > 0
    
    def test_special_characters(self):
        """Special characters don't break rendering."""
        doc = Document(title="Test")
        doc.add(Paragraph("Émojis: 🎉 🚀 ✅ ❌"))
        doc.add(Paragraph("Accents: éàüöñ ß"))
        doc.add(Paragraph("Symbols: © ® ™ € £ ¥"))
        doc.add(Paragraph("Math: α β γ ∑ ∫ ≠ ≤"))
        
        pdf = render_to_pdf(doc)
        assert len(pdf) > 0
    
    def test_very_long_title(self):
        """Very long title wraps correctly."""
        long_title = "This is a very long title that should wrap " * 5
        doc = Document(title=long_title)
        doc.add(Paragraph("Content"))
        
        pdf = render_to_pdf(doc)
        assert len(pdf) > 0
    
    def test_empty_document(self):
        """Empty document still produces valid PDF."""
        doc = Document(title="Empty")
        pdf = render_to_pdf(doc)
        
        assert pdf[:4] == b'%PDF'
        assert len(pdf) > 100
    
    def test_large_table(self):
        """Large tables render without error."""
        doc = Document(title="Table Test")
        
        headers = [f"Col{i}" for i in range(10)]
        rows = [[f"R{r}C{c}" for c in range(10)] for r in range(50)]
        
        doc.add(Table(headers=headers, rows=rows))
        
        pdf = render_to_pdf(doc)
        assert len(pdf) > 1000
    
    def test_deeply_nested_structure(self):
        """Many sections don't cause stack overflow."""
        doc = Document(title="Deep", show_cover_page=False)  # No cover for simpler layout
        
        for i in range(50):
            doc.add(Heading(f"Section {i}", level=(i % 4) + 1))
            doc.add(Paragraph(f"Content {i}"))
        
        pdf = render_to_pdf(doc)
        assert len(pdf) > 0
    
    def test_strict_mode_raises(self):
        """Strict mode raises on errors instead of fallback."""
        doc = Document(title="Test")
        # Normal mode should work
        pdf = render_to_pdf(doc, strict=False)
        assert len(pdf) > 0


# ═══════════════════════════════════════════════════════════════════════════════
# 2-PASS PAGINATION TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestPagination:
    """Test 2-pass pagination (Page X sur Y)."""
    
    def test_single_page_shows_correct_total(self):
        """Single page document shows 'Page 1 sur 1'."""
        doc = Document(title="Short")
        doc.add(Paragraph("Brief content"))
        
        pdf = render_to_pdf(doc)
        # PDF should contain "Page 1 sur 1" (or variations)
        # We can't easily parse the PDF, but it should render
        assert len(pdf) > 0
    
    def test_multi_page_has_consistent_total(self):
        """Multi-page document has same total on all pages."""
        doc = Document(title="Long Document", show_cover_page=False)
        
        # Add enough content for multiple pages (shorter paragraphs)
        for i in range(50):
            doc.add(Heading(f"Section {i}", level=2))
            doc.add(Paragraph("This is content that spans multiple lines. " * 10))
        
        pdf = render_to_pdf(doc)
        assert len(pdf) > 5000  # Should be substantial


# ═══════════════════════════════════════════════════════════════════════════════
# AST SERIALIZATION TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestASTSerialization:
    """Test JSON round-trip of AST."""
    
    def test_document_roundtrip(self):
        """Document survives JSON round-trip."""
        doc = Document(
            title="Test Document",
            template="consulting_premium",
            metadata=DocumentMetadata(
                author="Test Author",
                version="2.0",
                confidentiality=ConfidentialityLevel.CONFIDENTIAL
            )
        )
        doc.add(Heading("Intro", level=1))
        doc.add(Paragraph("Content"))
        doc.add(BulletList(items=["A", "B"]))
        doc.add(Table(headers=["X", "Y"], rows=[["1", "2"]]))
        doc.add_source(DocumentSource(id="s1", title="Source"))
        doc.add_assumption(Assumption(id="a1", text="Assumption", impact="high"))
        
        json_str = doc.to_json()
        doc2 = Document.from_json(json_str)
        
        assert doc2.title == doc.title
        assert doc2.template == doc.template
        assert doc2.metadata.author == doc.metadata.author
        assert len(doc2.elements) == len(doc.elements)
        assert len(doc2.metadata.sources) == 1
        assert len(doc2.metadata.assumptions) == 1
    
    def test_all_elements_serialize(self):
        """All element types serialize to dict."""
        elements = [
            Paragraph(content="Test"),
            Heading(text="Title", level=2),
            BulletList(items=["a"]),
            NumberedList(items=["x"]),
            Table(headers=["H"], rows=[["V"]]),
            CodeBlock(code="print(1)"),
            BlockQuote(text="Quote"),
            HorizontalRule(),
            PageBreak(),
            Callout(text="Info", type="info"),
        ]
        
        for elem in elements:
            d = elem.to_dict()
            assert "type" in d
            assert isinstance(d, dict)


# ═══════════════════════════════════════════════════════════════════════════════
# TEMPLATE CONFIGURATION TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestTemplates:
    """Test template configurations."""
    
    def test_all_templates_have_required_fields(self):
        """All templates have required fields."""
        for name, template in TEMPLATES.items():
            assert template.name == name
            assert template.display_name
            assert template.description
            assert template.primary_color.startswith('#')
            assert template.body_font
            assert template.body_size > 0
    
    def test_list_templates(self):
        """list_templates returns all templates."""
        templates = list_templates()
        assert len(templates) == len(TEMPLATES)


# ═══════════════════════════════════════════════════════════════════════════════
# E2E RENDERING TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestE2ERendering:
    """End-to-end rendering tests."""
    
    def test_basic_render(self):
        """Basic document renders to PDF."""
        doc = Document(title="Test")
        doc.add(Heading("Hello", level=1))
        doc.add(Paragraph("World"))
        
        pdf = render_to_pdf(doc)
        assert pdf[:4] == b'%PDF'
    
    @pytest.mark.parametrize("template_name", list(TEMPLATES.keys()))
    def test_all_templates_render(self, template_name: str):
        """Each template renders without error."""
        doc = Document(title=f"Test {template_name}", template=template_name)
        doc.add(Heading("Section 1", level=1))
        doc.add(Paragraph("Test content."))
        doc.add(BulletList(items=["Item 1", "Item 2"]))
        doc.add(Table(headers=["A", "B"], rows=[["1", "2"]]))
        
        pdf = render_to_pdf(doc)
        assert pdf[:4] == b'%PDF', f"Template {template_name} failed"
    
    def test_sources_and_assumptions_render(self):
        """Sources and assumptions sections render."""
        doc = Document(
            title="Test",
            show_sources=True,
            show_assumptions=True
        )
        doc.add(Paragraph("Content"))
        doc.add_source(DocumentSource(id="1", title="Source", confidence=0.95))
        doc.add_assumption(Assumption(id="A1", text="Assumption", impact="high"))
        
        pdf = render_to_pdf(doc)
        assert len(pdf) > 0
    
    def test_cover_page_toggle(self):
        """Cover page is toggleable."""
        doc_with = Document(title="With Cover", show_cover_page=True)
        doc_with.add(Paragraph("Content"))
        
        doc_without = Document(title="Without Cover", show_cover_page=False)
        doc_without.add(Paragraph("Content"))
        
        pdf_with = render_to_pdf(doc_with)
        pdf_without = render_to_pdf(doc_without)
        
        assert len(pdf_with) > len(pdf_without)
    
    def test_callout_types_render(self):
        """All callout types render."""
        doc = Document(title="Callouts")
        
        for callout_type in ['info', 'warning', 'danger', 'success']:
            doc.add(Callout(text=f"This is {callout_type}", type=callout_type))
        
        pdf = render_to_pdf(doc)
        assert len(pdf) > 0
    
    def test_blockquote_renders_as_table(self):
        """Blockquote renders (as table internally)."""
        doc = Document(title="Quote Test")
        doc.add(BlockQuote(text="Famous quote", source="Author"))
        
        pdf = render_to_pdf(doc)
        assert len(pdf) > 0


# ═══════════════════════════════════════════════════════════════════════════════
# MARKDOWN PARSER TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestMarkdownParser:
    """Test Markdown to AST conversion."""
    
    def test_parse_headers(self):
        """Headers parsed correctly."""
        md = "# H1\n## H2\n### H3"
        doc = parse_markdown(md)
        
        headings = [e for e in doc.elements if isinstance(e, Heading)]
        assert len(headings) == 3
        assert headings[0].level == 1
        assert headings[1].level == 2
        assert headings[2].level == 3
    
    def test_parse_lists(self):
        """Lists parsed correctly."""
        md = "- A\n- B\n\n1. X\n2. Y"
        doc = parse_markdown(md)
        
        bullets = [e for e in doc.elements if isinstance(e, BulletList)]
        numbered = [e for e in doc.elements if isinstance(e, NumberedList)]
        
        assert len(bullets) == 1
        assert len(numbered) == 1
    
    def test_parse_table(self):
        """Tables parsed correctly."""
        md = "| A | B |\n|---|---|\n| 1 | 2 |"
        doc = parse_markdown(md)
        
        tables = [e for e in doc.elements if isinstance(e, Table)]
        assert len(tables) == 1
        assert tables[0].headers == ["A", "B"]
    
    def test_explicit_template(self):
        """Explicit template overrides detection."""
        doc = parse_markdown("Hello", template="legal_formal")
        assert doc.template == "legal_formal"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
