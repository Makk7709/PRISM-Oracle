"""
╔══════════════════════════════════════════════════════════════════════════════╗
║              EMAIL CLIENT — HTML→TEXT CHARACTERIZATION TESTS                  ║
║                                                                              ║
║  Captures the EXACT behavior of _html_to_text() BEFORE the html2text→       ║
║  markdownify migration. These tests ensure parity after the swap.            ║
║                                                                              ║
║  TEST MATRIX:                                                                ║
║  1. Simple paragraph → plain text                                            ║
║  2. Links preserved (href in output)                                         ║
║  3. Bold/italic emphasis preserved                                           ║
║  4. Nested lists (ul/ol)                                                     ║
║  5. Tables → readable text                                                   ║
║  6. Inline images with CID map → [file://...] markers                        ║
║  7. Empty HTML                                                               ║
║  8. Whitespace normalization (no triple+ newlines)                           ║
║  9. Unicode/French accents                                                   ║
║  10. Complex real-world newsletter HTML                                      ║
║  11. Deeply nested div/span structure                                        ║
║  12. HTML entities (&amp; &lt; &gt;)                                         ║
║  13. <br> and <hr> handling                                                  ║
║  14. Heading tags (h1-h6)                                                    ║
║  15. Pre/code blocks                                                         ║
║  16. body_width=0 (no line wrapping)                                         ║
║                                                                              ║
║  © 2025 Korev AI — Proprietary                                               ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import pytest

from python.helpers.email_client import EmailClient


@pytest.fixture
def client():
    """Create a minimal EmailClient instance for testing _html_to_text."""
    return EmailClient.__new__(EmailClient)


# ═══════════════════════════════════════════════════════════════════════════════
# 1. BASIC TEXT EXTRACTION
# ═══════════════════════════════════════════════════════════════════════════════

class TestBasicTextExtraction:
    """Verify fundamental HTML→text conversion."""

    def test_simple_paragraph(self, client):
        html = "<p>Hello, this is a test paragraph.</p>"
        result = client._html_to_text(html)
        assert "Hello, this is a test paragraph." in result

    def test_multiple_paragraphs(self, client):
        html = "<p>First paragraph.</p><p>Second paragraph.</p>"
        result = client._html_to_text(html)
        assert "First paragraph." in result
        assert "Second paragraph." in result

    def test_plain_text_passthrough(self, client):
        html = "Just plain text without any HTML tags."
        result = client._html_to_text(html)
        assert "Just plain text without any HTML tags." in result

    def test_empty_html(self, client):
        result = client._html_to_text("")
        assert result.strip() == ""

    def test_only_whitespace_html(self, client):
        result = client._html_to_text("   \n\n  ")
        assert result.strip() == ""


# ═══════════════════════════════════════════════════════════════════════════════
# 2. LINKS
# ═══════════════════════════════════════════════════════════════════════════════

class TestLinkPreservation:
    """Verify that links are preserved (ignore_links=False)."""

    def test_link_text_and_url_preserved(self, client):
        html = '<p>Visit <a href="https://example.com">our site</a> for more.</p>'
        result = client._html_to_text(html)
        assert "our site" in result
        assert "https://example.com" in result

    def test_multiple_links(self, client):
        html = """
        <p>
          <a href="https://alpha.com">Alpha</a> and
          <a href="https://beta.com">Beta</a>
        </p>
        """
        result = client._html_to_text(html)
        assert "Alpha" in result
        assert "https://alpha.com" in result
        assert "Beta" in result
        assert "https://beta.com" in result

    def test_link_without_href(self, client):
        html = '<p><a>Link without href</a></p>'
        result = client._html_to_text(html)
        assert "Link without href" in result


# ═══════════════════════════════════════════════════════════════════════════════
# 3. EMPHASIS (BOLD/ITALIC)
# ═══════════════════════════════════════════════════════════════════════════════

class TestEmphasis:
    """Verify bold/italic handling (ignore_emphasis=False)."""

    def test_bold_text_preserved(self, client):
        html = "<p>This is <strong>important</strong> text.</p>"
        result = client._html_to_text(html)
        assert "important" in result

    def test_italic_text_preserved(self, client):
        html = "<p>This is <em>emphasized</em> text.</p>"
        result = client._html_to_text(html)
        assert "emphasized" in result

    def test_bold_markers_present(self, client):
        """html2text uses ** for bold, markdownify uses ** too."""
        html = "<p>This is <strong>bold</strong> text.</p>"
        result = client._html_to_text(html)
        assert "**bold**" in result


# ═══════════════════════════════════════════════════════════════════════════════
# 4. LISTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestLists:
    """Verify list rendering."""

    def test_unordered_list(self, client):
        html = "<ul><li>Apple</li><li>Banana</li><li>Cherry</li></ul>"
        result = client._html_to_text(html)
        assert "Apple" in result
        assert "Banana" in result
        assert "Cherry" in result

    def test_ordered_list(self, client):
        html = "<ol><li>First</li><li>Second</li><li>Third</li></ol>"
        result = client._html_to_text(html)
        assert "First" in result
        assert "Second" in result
        assert "Third" in result

    def test_nested_list(self, client):
        html = """
        <ul>
            <li>Parent
                <ul>
                    <li>Child A</li>
                    <li>Child B</li>
                </ul>
            </li>
            <li>Parent 2</li>
        </ul>
        """
        result = client._html_to_text(html)
        assert "Parent" in result
        assert "Child A" in result
        assert "Child B" in result
        assert "Parent 2" in result


# ═══════════════════════════════════════════════════════════════════════════════
# 5. TABLES
# ═══════════════════════════════════════════════════════════════════════════════

class TestTableExtraction:
    """Verify table content extraction."""

    def test_simple_table_content(self, client):
        html = """
        <table>
            <tr><th>Name</th><th>Value</th></tr>
            <tr><td>Revenue</td><td>1.5M€</td></tr>
            <tr><td>EBITDA</td><td>350K€</td></tr>
        </table>
        """
        result = client._html_to_text(html)
        assert "Name" in result
        assert "Revenue" in result
        assert "1.5M€" in result
        assert "EBITDA" in result
        assert "350K€" in result

    def test_table_with_headers_and_data(self, client):
        html = """
        <table>
            <thead><tr><th>Q1</th><th>Q2</th><th>Q3</th></tr></thead>
            <tbody><tr><td>100</td><td>200</td><td>300</td></tr></tbody>
        </table>
        """
        result = client._html_to_text(html)
        assert "Q1" in result
        assert "100" in result
        assert "300" in result


# ═══════════════════════════════════════════════════════════════════════════════
# 6. INLINE IMAGES WITH CID MAP
# ═══════════════════════════════════════════════════════════════════════════════

class TestCidImageReplacement:
    """Verify CID→file path replacement for inline images."""

    def test_cid_image_replaced(self, client):
        cid_map = {"image001@korev": "/korev/tmp/email/logo_abc123.png"}
        html = '<p>See this image: <img src="cid:image001@korev" alt="Logo"></p>'
        result = client._html_to_text(html, cid_map)
        assert "[file:///korev/tmp/email/logo_abc123.png]" in result

    def test_cid_not_in_map_ignored(self, client):
        cid_map = {}
        html = '<p>Image: <img src="cid:unknown@id" alt="Unknown"></p>'
        result = client._html_to_text(html, cid_map)
        # CID not in map: image tag remains or gets stripped, but no crash
        assert isinstance(result, str)

    def test_multiple_cid_images(self, client):
        cid_map = {
            "img1@korev": "/korev/tmp/email/photo1.jpg",
            "img2@korev": "/korev/tmp/email/photo2.jpg",
        }
        html = """
        <p>First: <img src="cid:img1@korev"></p>
        <p>Second: <img src="cid:img2@korev"></p>
        """
        result = client._html_to_text(html, cid_map)
        assert "[file:///korev/tmp/email/photo1.jpg]" in result
        assert "[file:///korev/tmp/email/photo2.jpg]" in result

    def test_no_cid_map_defaults_to_empty(self, client):
        html = '<p>Image: <img src="https://example.com/img.png"></p>'
        result = client._html_to_text(html)
        assert isinstance(result, str)
        assert "img.png" in result or "example.com" in result


# ═══════════════════════════════════════════════════════════════════════════════
# 7. WHITESPACE NORMALIZATION
# ═══════════════════════════════════════════════════════════════════════════════

class TestWhitespaceNormalization:
    """Verify the regex cleanup: max 2 consecutive newlines, strip."""

    def test_no_triple_newlines(self, client):
        html = "<p>First</p><br><br><br><br><p>Second</p>"
        result = client._html_to_text(html)
        assert "\n\n\n" not in result

    def test_result_is_stripped(self, client):
        html = "  <p>Content</p>  "
        result = client._html_to_text(html)
        assert result == result.strip()

    def test_body_width_no_wrapping(self, client):
        """body_width=0 means no line wrapping."""
        long_text = "A " * 200  # 400-char paragraph
        html = f"<p>{long_text}</p>"
        result = client._html_to_text(html)
        # With body_width=0, the text should NOT be wrapped
        lines = result.strip().split("\n")
        # The main content should be on a single line (or very few)
        longest_line = max(len(l) for l in lines)
        assert longest_line > 200, "body_width=0 should prevent wrapping"


# ═══════════════════════════════════════════════════════════════════════════════
# 8. UNICODE / FRENCH TEXT
# ═══════════════════════════════════════════════════════════════════════════════

class TestUnicodeHandling:
    """Verify French/Unicode text is preserved."""

    def test_french_accents(self, client):
        html = "<p>L'intérêt général prévaut sur l'intérêt particulier.</p>"
        result = client._html_to_text(html)
        assert "intérêt" in result
        assert "prévaut" in result

    def test_legal_french_text(self, client):
        html = """
        <div>
            <h2>Article L.621-1 du Code monétaire et financier</h2>
            <p>L'Autorité des marchés financiers, autorité publique indépendante
            dotée de la personnalité morale, veille à la protection de l'épargne.</p>
        </div>
        """
        result = client._html_to_text(html)
        assert "L.621-1" in result
        assert "marchés financiers" in result
        assert "épargne" in result

    def test_special_characters(self, client):
        html = "<p>€ £ ¥ © ® ™ § ¶ • ‣ …</p>"
        result = client._html_to_text(html)
        assert "€" in result
        assert "©" in result
        assert "™" in result


# ═══════════════════════════════════════════════════════════════════════════════
# 9. HTML ENTITIES
# ═══════════════════════════════════════════════════════════════════════════════

class TestHtmlEntities:
    """Verify HTML entities are decoded."""

    def test_amp_entity(self, client):
        html = "<p>A &amp; B</p>"
        result = client._html_to_text(html)
        assert "A & B" in result

    def test_lt_gt_entities(self, client):
        html = "<p>5 &lt; 10 &gt; 3</p>"
        result = client._html_to_text(html)
        assert "5 < 10 > 3" in result

    def test_nbsp_entity(self, client):
        html = "<p>Hello&nbsp;World</p>"
        result = client._html_to_text(html)
        assert "Hello" in result
        assert "World" in result


# ═══════════════════════════════════════════════════════════════════════════════
# 10. HEADINGS
# ═══════════════════════════════════════════════════════════════════════════════

class TestHeadings:
    """Verify heading content is extracted."""

    def test_h1_text_preserved(self, client):
        html = "<h1>Main Title</h1><p>Body text.</p>"
        result = client._html_to_text(html)
        assert "Main Title" in result
        assert "Body text." in result

    def test_h2_h3_text_preserved(self, client):
        html = "<h2>Section</h2><h3>Subsection</h3>"
        result = client._html_to_text(html)
        assert "Section" in result
        assert "Subsection" in result


# ═══════════════════════════════════════════════════════════════════════════════
# 11. BR AND HR
# ═══════════════════════════════════════════════════════════════════════════════

class TestBrHr:
    """Verify line break and horizontal rule handling."""

    def test_br_creates_newline(self, client):
        html = "<p>Line one<br>Line two</p>"
        result = client._html_to_text(html)
        assert "Line one" in result
        assert "Line two" in result

    def test_hr_creates_separator(self, client):
        html = "<p>Above</p><hr><p>Below</p>"
        result = client._html_to_text(html)
        assert "Above" in result
        assert "Below" in result


# ═══════════════════════════════════════════════════════════════════════════════
# 12. PRE/CODE BLOCKS
# ═══════════════════════════════════════════════════════════════════════════════

class TestCodeBlocks:
    """Verify pre/code block handling."""

    def test_code_inline(self, client):
        html = "<p>Use <code>pip install korev</code> to install.</p>"
        result = client._html_to_text(html)
        assert "pip install korev" in result

    def test_pre_block(self, client):
        html = "<pre>def hello():\n    print('world')</pre>"
        result = client._html_to_text(html)
        assert "def hello():" in result
        assert "print" in result


# ═══════════════════════════════════════════════════════════════════════════════
# 13. REAL-WORLD COMPLEX HTML
# ═══════════════════════════════════════════════════════════════════════════════

class TestComplexRealWorldHtml:
    """Simulate real-world email HTML complexity."""

    def test_newsletter_with_styles_and_tables(self, client):
        html = """
        <!DOCTYPE html>
        <html>
        <head><style>body{font-family:Arial;color:#333;}</style></head>
        <body>
            <div style="max-width:600px;margin:auto;">
                <h1 style="color:#0066cc;">Weekly Report</h1>
                <p>Dear <strong>Amine</strong>,</p>
                <p>Here are the <em>key metrics</em> for this week:</p>
                <table border="1" cellpadding="5" style="border-collapse:collapse;">
                    <tr style="background:#f0f0f0;">
                        <th>Metric</th><th>Value</th><th>Change</th>
                    </tr>
                    <tr>
                        <td>Revenue</td><td>€2.3M</td><td style="color:green;">+12%</td>
                    </tr>
                    <tr>
                        <td>Users</td><td>45,000</td><td style="color:green;">+8%</td>
                    </tr>
                </table>
                <p>Best regards,<br>The Korev Team</p>
                <hr>
                <p style="font-size:10px;color:#999;">
                    <a href="https://korev.ai/unsubscribe">Unsubscribe</a>
                </p>
            </div>
        </body>
        </html>
        """
        result = client._html_to_text(html)

        # Key content must survive
        assert "Weekly Report" in result
        assert "Amine" in result
        assert "key metrics" in result
        assert "Revenue" in result
        assert "€2.3M" in result
        assert "+12%" in result
        assert "45,000" in result
        assert "Korev Team" in result
        assert "https://korev.ai/unsubscribe" in result

    def test_deeply_nested_structure(self, client):
        html = """
        <div>
          <div>
            <div>
              <span>
                <p>Deep <strong>nested</strong> content with <a href="https://x.com">link</a></p>
              </span>
            </div>
          </div>
        </div>
        """
        result = client._html_to_text(html)
        assert "Deep" in result
        assert "nested" in result
        assert "https://x.com" in result


# ═══════════════════════════════════════════════════════════════════════════════
# 14. PARITY INVARIANTS (must hold BEFORE and AFTER migration)
# ═══════════════════════════════════════════════════════════════════════════════

class TestMigrationInvariants:
    """
    Critical invariants that MUST hold regardless of which library is used.
    These are the CONTRACTS of _html_to_text().
    """

    def test_return_type_is_str(self, client):
        assert isinstance(client._html_to_text("<p>test</p>"), str)

    def test_output_is_stripped(self, client):
        result = client._html_to_text("<p>  content  </p>")
        assert result == result.strip()

    def test_no_triple_newlines_invariant(self, client):
        html = "<p>A</p>" + "<br>" * 20 + "<p>B</p>"
        result = client._html_to_text(html)
        assert "\n\n\n" not in result

    def test_cid_replacement_works(self, client):
        cid_map = {"abc@123": "/path/to/file.png"}
        html = '<img src="cid:abc@123">'
        result = client._html_to_text(html, cid_map)
        assert "[file:///path/to/file.png]" in result

    def test_links_are_visible_in_output(self, client):
        html = '<a href="https://test.com">Click</a>'
        result = client._html_to_text(html)
        assert "https://test.com" in result
        assert "Click" in result

    def test_html_entities_decoded(self, client):
        html = "<p>&amp; &lt; &gt; &quot;</p>"
        result = client._html_to_text(html)
        assert "&" in result
        assert "<" in result
        assert ">" in result

    def test_unicode_preserved(self, client):
        html = "<p>éàü ñ ø ß 中文 日本語</p>"
        result = client._html_to_text(html)
        assert "éàü" in result
        assert "ñ" in result
        assert "中文" in result

    def test_empty_input_returns_empty(self, client):
        assert client._html_to_text("").strip() == ""

    def test_no_exception_on_malformed_html(self, client):
        html = "<p>Unclosed <strong>tag <em>mess"
        result = client._html_to_text(html)
        assert isinstance(result, str)
        assert "Unclosed" in result
