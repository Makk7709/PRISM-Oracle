"""
Tests for Evidence Document System.

Tests:
- Snapshot: même entrée => même hash (hors timestamp)
- Template detection: corpus de prompts -> template attendu
- Robustness: caractères spéciaux, longues listes, tables larges
- AST serialization: round-trip JSON
"""

import pytest
import hashlib
from datetime import datetime

from python.helpers.evidence_document import (
    Document, DocumentMetadata, DocumentSource, Assumption,
    ConfidentialityLevel,
    Paragraph, Heading, BulletList, NumberedList, Table,
    CodeBlock, BlockQuote, HorizontalRule, PageBreak, Callout,
    get_template, detect_template, list_templates, TEMPLATES,
    render_to_pdf, parse_markdown
)


# ═══════════════════════════════════════════════════════════════════════════════
# SNAPSHOT TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestDocumentHash:
    """Test that document hashes are deterministic."""
    
    def test_same_content_same_hash(self):
        """Same content should produce same hash."""
        doc1 = Document(title="Test", template="standard")
        doc1.add(Heading("Title", level=1))
        doc1.add(Paragraph("Content"))
        
        doc2 = Document(title="Test", template="standard")
        doc2.add(Heading("Title", level=1))
        doc2.add(Paragraph("Content"))
        
        assert doc1.compute_hash() == doc2.compute_hash()
    
    def test_different_content_different_hash(self):
        """Different content should produce different hash."""
        doc1 = Document(title="Test1", template="standard")
        doc1.add(Paragraph("Content 1"))
        
        doc2 = Document(title="Test2", template="standard")
        doc2.add(Paragraph("Content 2"))
        
        assert doc1.compute_hash() != doc2.compute_hash()
    
    def test_hash_ignores_timestamp(self):
        """Hash should ignore timestamp for reproducibility."""
        meta1 = DocumentMetadata(created_at=datetime(2024, 1, 1))
        meta2 = DocumentMetadata(created_at=datetime(2025, 1, 1))
        
        doc1 = Document(title="Test", metadata=meta1)
        doc2 = Document(title="Test", metadata=meta2)
        
        # Hash should be same despite different timestamps
        assert doc1.compute_hash() == doc2.compute_hash()


# ═══════════════════════════════════════════════════════════════════════════════
# TEMPLATE DETECTION TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestTemplateDetection:
    """Test automatic template detection from user prompts."""
    
    @pytest.mark.parametrize("prompt,expected", [
        # Consulting
        ("Fais-moi un rapport stratégique", "consulting_premium"),
        ("Strategic analysis for the board", "consulting_premium"),
        ("Due diligence M&A acquisition", "consulting_premium"),
        ("Business case transformation", "consulting_premium"),
        
        # Legal
        ("Document juridique pour le tribunal", "legal_formal"),
        ("Rédige des conclusions pour l'avocat", "legal_formal"),
        ("Contrat de cession de parts", "legal_formal"),
        ("Assignation devant le greffe", "legal_formal"),
        
        # Scientific
        ("Publication scientifique avec abstract", "scientific_academic"),
        ("Research paper methodology", "scientific_academic"),
        ("Étude académique peer review", "scientific_academic"),
        
        # Patent
        ("Demande de brevet pour invention", "patent_ip"),
        ("Patent application avec revendications", "patent_ip"),
        ("Propriété intellectuelle IP dépôt", "patent_ip"),
        
        # Financial
        ("Rapport financier audit comptable", "financial_audit"),
        ("Analyse bilan compte résultat", "financial_audit"),
        ("Due diligence financière DCF", "financial_audit"),
        
        # Executive
        ("Note de synthèse pour la direction", "executive_brief"),
        ("Executive summary pour le board", "executive_brief"),
        ("Brief décision CEO", "executive_brief"),
        
        # Medical
        ("Rapport médical diagnostic patient", "medical_clinical"),
        ("Consultation clinique traitement", "medical_clinical"),
        ("Examen pathologie hôpital", "medical_clinical"),
        
        # Technical
        ("Documentation technique API", "technical_doc"),
        ("Architecture système développement", "technical_doc"),
        ("Spécification SDK readme", "technical_doc"),
        
        # Default (no match)
        ("Crée un fichier simple", "standard"),
        ("Hello world", "standard"),
    ])
    def test_template_detection(self, prompt: str, expected: str):
        """Test that prompts map to expected templates."""
        detected = detect_template(prompt)
        assert detected == expected, f"Expected {expected} for '{prompt}', got {detected}"


class TestTemplates:
    """Test template configurations."""
    
    def test_all_templates_have_required_fields(self):
        """All templates should have required fields."""
        for name, template in TEMPLATES.items():
            assert template.name == name
            assert template.display_name
            assert template.description
            assert template.primary_color.startswith('#')
            assert template.body_font
            assert template.body_size > 0
    
    def test_list_templates(self):
        """list_templates should return all templates."""
        templates = list_templates()
        assert len(templates) == len(TEMPLATES)
        
        for t in templates:
            assert "name" in t
            assert "display_name" in t
            assert "description" in t


# ═══════════════════════════════════════════════════════════════════════════════
# AST SERIALIZATION TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestASTSerialization:
    """Test JSON serialization/deserialization of AST."""
    
    def test_document_roundtrip(self):
        """Document should survive JSON round-trip."""
        doc = Document(
            title="Test Document",
            template="consulting_premium",
            metadata=DocumentMetadata(
                author="Test Author",
                version="2.0",
                confidentiality=ConfidentialityLevel.CONFIDENTIAL
            )
        )
        doc.add(Heading("Introduction", level=1))
        doc.add(Paragraph("This is a test paragraph."))
        doc.add(BulletList(items=["Item 1", "Item 2", "Item 3"]))
        doc.add(Table(
            headers=["Col A", "Col B"],
            rows=[["1", "2"], ["3", "4"]]
        ))
        doc.add_source(DocumentSource(
            id="src1",
            title="Test Source",
            url="https://example.com"
        ))
        
        # Serialize
        json_str = doc.to_json()
        
        # Deserialize
        doc2 = Document.from_json(json_str)
        
        # Compare
        assert doc2.title == doc.title
        assert doc2.template == doc.template
        assert doc2.metadata.author == doc.metadata.author
        assert doc2.metadata.confidentiality == doc.metadata.confidentiality
        assert len(doc2.elements) == len(doc.elements)
        assert len(doc2.metadata.sources) == 1
    
    def test_all_element_types_serialize(self):
        """All element types should serialize correctly."""
        elements = [
            Paragraph(content="Test"),
            Heading(text="Title", level=2),
            BulletList(items=["a", "b"]),
            NumberedList(items=["x", "y"], start=5),
            Table(headers=["H"], rows=[["V"]]),
            CodeBlock(code="print('hello')", language="python"),
            BlockQuote(text="Quote", source="Author"),
            HorizontalRule(),
            PageBreak(),
            Callout(text="Warning!", type="warning", title="Attention"),
        ]
        
        for elem in elements:
            d = elem.to_dict()
            assert "type" in d


# ═══════════════════════════════════════════════════════════════════════════════
# ROBUSTNESS TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestRobustness:
    """Test handling of edge cases."""
    
    def test_special_characters(self):
        """Special characters should be handled."""
        doc = Document(title="Test <>&\"'")
        doc.add(Paragraph("Content with <html> & ampersand"))
        doc.add(Paragraph("Émojis: 🎉 🚀 ✅"))
        doc.add(Paragraph("Accents: éàüöñ"))
        
        # Should not raise
        pdf = render_to_pdf(doc)
        assert len(pdf) > 0
    
    def test_long_content(self):
        """Long content should be handled."""
        doc = Document(title="Long Document")
        
        # Add many paragraphs
        for i in range(100):
            doc.add(Paragraph(f"This is paragraph {i} with some content. " * 5))
        
        # Should not raise
        pdf = render_to_pdf(doc)
        assert len(pdf) > 1000  # Should be a substantial PDF
    
    def test_large_table(self):
        """Large tables should be handled."""
        doc = Document(title="Table Test")
        
        headers = [f"Col {i}" for i in range(10)]
        rows = [[f"R{r}C{c}" for c in range(10)] for r in range(50)]
        
        doc.add(Table(headers=headers, rows=rows))
        
        # Should not raise
        pdf = render_to_pdf(doc)
        assert len(pdf) > 0
    
    def test_empty_document(self):
        """Empty document should produce valid PDF."""
        doc = Document(title="Empty")
        
        pdf = render_to_pdf(doc)
        assert len(pdf) > 0
    
    def test_nested_formatting(self):
        """Nested formatting should be handled."""
        doc = Document(title="Formatting Test")
        doc.add(Paragraph("**Bold with *italic* inside**"))
        doc.add(Paragraph("`code` and **bold** and *italic*"))
        
        # Should not raise
        pdf = render_to_pdf(doc)
        assert len(pdf) > 0


# ═══════════════════════════════════════════════════════════════════════════════
# MARKDOWN PARSER TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestMarkdownParser:
    """Test Markdown to AST conversion."""
    
    def test_parse_headers(self):
        """Headers should be parsed correctly."""
        md = """# Title
## Section
### Subsection
"""
        doc = parse_markdown(md)
        
        headings = [e for e in doc.elements if isinstance(e, Heading)]
        assert len(headings) == 3
        assert headings[0].level == 1
        assert headings[1].level == 2
        assert headings[2].level == 3
    
    def test_parse_lists(self):
        """Lists should be parsed correctly."""
        md = """
- Item 1
- Item 2
- Item 3

1. First
2. Second
3. Third
"""
        doc = parse_markdown(md)
        
        bullets = [e for e in doc.elements if isinstance(e, BulletList)]
        numbered = [e for e in doc.elements if isinstance(e, NumberedList)]
        
        assert len(bullets) == 1
        assert len(bullets[0].items) == 3
        assert len(numbered) == 1
        assert len(numbered[0].items) == 3
    
    def test_parse_table(self):
        """Tables should be parsed correctly."""
        md = """
| Header 1 | Header 2 |
|----------|----------|
| Cell 1   | Cell 2   |
| Cell 3   | Cell 4   |
"""
        doc = parse_markdown(md)
        
        tables = [e for e in doc.elements if isinstance(e, Table)]
        assert len(tables) == 1
        assert tables[0].headers == ["Header 1", "Header 2"]
        assert len(tables[0].rows) == 2
    
    def test_parse_code_block(self):
        """Code blocks should be parsed correctly."""
        md = """
```python
def hello():
    print("world")
```
"""
        doc = parse_markdown(md)
        
        codes = [e for e in doc.elements if isinstance(e, CodeBlock)]
        assert len(codes) == 1
        assert codes[0].language == "python"
        assert "def hello" in codes[0].code
    
    def test_auto_detect_template(self):
        """Template should be auto-detected from content."""
        md = "# Rapport Stratégique\n\nAnalyse stratégique pour le board..."
        doc = parse_markdown(md)
        
        assert doc.template == "consulting_premium"
    
    def test_explicit_template(self):
        """Explicit template should override detection."""
        md = "# Rapport\n\nContenu..."
        doc = parse_markdown(md, template="legal_formal")
        
        assert doc.template == "legal_formal"


# ═══════════════════════════════════════════════════════════════════════════════
# RENDERING TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestRendering:
    """Test PDF rendering."""
    
    def test_basic_render(self):
        """Basic document should render to PDF."""
        doc = Document(title="Test")
        doc.add(Heading("Hello", level=1))
        doc.add(Paragraph("World"))
        
        pdf = render_to_pdf(doc)
        
        # Check PDF header
        assert pdf[:4] == b'%PDF'
    
    def test_all_templates_render(self):
        """All templates should render without errors."""
        for template_name in TEMPLATES.keys():
            doc = Document(title=f"Test {template_name}", template=template_name)
            doc.add(Heading("Test Section", level=1))
            doc.add(Paragraph("Test content for this template."))
            doc.add(BulletList(items=["Item 1", "Item 2"]))
            
            pdf = render_to_pdf(doc)
            assert pdf[:4] == b'%PDF', f"Template {template_name} failed to render"
    
    def test_sources_and_assumptions_render(self):
        """Sources and assumptions should be included."""
        doc = Document(title="Test", show_sources=True, show_assumptions=True)
        doc.add(Paragraph("Content"))
        doc.add_source(DocumentSource(id="1", title="Source 1"))
        doc.add_assumption(Assumption(id="A1", text="Assumption 1", impact="high"))
        
        pdf = render_to_pdf(doc)
        assert len(pdf) > 0
    
    def test_cover_page_toggle(self):
        """Cover page should be toggleable."""
        doc_with = Document(title="With Cover", show_cover_page=True)
        doc_with.add(Paragraph("Content"))
        
        doc_without = Document(title="Without Cover", show_cover_page=False)
        doc_without.add(Paragraph("Content"))
        
        pdf_with = render_to_pdf(doc_with)
        pdf_without = render_to_pdf(doc_without)
        
        # Both should render
        assert len(pdf_with) > 0
        assert len(pdf_without) > 0
        # With cover should be larger (has extra page)
        assert len(pdf_with) > len(pdf_without)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
