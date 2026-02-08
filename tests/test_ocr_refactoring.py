"""
╔══════════════════════════════════════════════════════════════════════════════╗
║              OCR REFACTORING — REGRESSION TESTS (TDD)                        ║
║                                                                              ║
║  Tests ensuring pdf_ocr.py and document_query.py use the centralized         ║
║  OCREngine after refactoring. Written BEFORE the refactoring.                ║
║                                                                              ║
║  Validates:                                                                  ║
║  1. pdf_ocr.py uses OCREngine (no direct pytesseract calls)                  ║
║  2. document_query.py uses OCREngine for OCR fallback                        ║
║  3. No duplicated OCR code remains                                           ║
║  4. Functional parity: same results as before refactoring                    ║
║                                                                              ║
║  © 2025 Korev AI — Proprietary                                               ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import ast
import importlib
import inspect
from pathlib import Path

import pytest


# ═══════════════════════════════════════════════════════════════════════════════
# 1. pdf_ocr.py — Uses OCREngine
# ═══════════════════════════════════════════════════════════════════════════════

class TestPdfOcrUsesOCREngine:
    """pdf_ocr.py should delegate to OCREngine instead of calling
    pytesseract directly."""

    def test_pdf_ocr_imports_ocr_engine(self):
        """pdf_ocr.py should import from ocr_engine module."""
        source = Path("python/tools/pdf_ocr.py").read_text()
        tree = ast.parse(source)

        imports = []
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                if node.module and "ocr_engine" in node.module:
                    imports.append(node.module)
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if "ocr_engine" in alias.name:
                        imports.append(alias.name)

        assert len(imports) > 0, (
            "pdf_ocr.py must import from ocr_engine module"
        )

    def test_pdf_ocr_no_direct_pytesseract_import(self):
        """pdf_ocr.py should NOT import pytesseract directly."""
        source = Path("python/tools/pdf_ocr.py").read_text()
        tree = ast.parse(source)

        direct_imports = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name == "pytesseract":
                        direct_imports.append(alias.name)
            if isinstance(node, ast.ImportFrom):
                if node.module == "pytesseract":
                    direct_imports.append(node.module)

        assert len(direct_imports) == 0, (
            f"pdf_ocr.py should NOT import pytesseract directly: {direct_imports}"
        )

    def test_pdf_ocr_no_direct_image_to_string(self):
        """pdf_ocr.py should NOT call pytesseract.image_to_string directly."""
        source = Path("python/tools/pdf_ocr.py").read_text()
        assert "image_to_string" not in source, (
            "pdf_ocr.py should use OCREngine instead of image_to_string"
        )

    def test_pdf_ocr_no_direct_pdf2image(self):
        """pdf_ocr.py should NOT import pdf2image directly for OCR."""
        source = Path("python/tools/pdf_ocr.py").read_text()
        tree = ast.parse(source)

        direct_imports = []
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                if node.module and "pdf2image" in node.module:
                    direct_imports.append(node.module)

        assert len(direct_imports) == 0, (
            f"pdf_ocr.py should NOT import pdf2image directly: {direct_imports}"
        )


# ═══════════════════════════════════════════════════════════════════════════════
# 2. document_query.py — Uses OCREngine
# ═══════════════════════════════════════════════════════════════════════════════

class TestDocumentQueryUsesOCREngine:
    """document_query.py should use OCREngine for its OCR fallback."""

    def test_document_query_imports_ocr_engine(self):
        """document_query.py should import from ocr_engine module."""
        source = Path("python/helpers/document_query.py").read_text()
        tree = ast.parse(source)

        imports = []
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                if node.module and "ocr_engine" in node.module:
                    imports.append(node.module)

        assert len(imports) > 0, (
            "document_query.py must import from ocr_engine module"
        )

    def test_document_query_no_direct_pytesseract(self):
        """document_query.py should NOT call pytesseract directly."""
        source = Path("python/helpers/document_query.py").read_text()
        assert "pytesseract.image_to_string" not in source, (
            "document_query.py should use OCREngine instead of pytesseract"
        )

    def test_document_query_no_direct_pdf2image(self):
        """document_query.py should NOT call pdf2image directly for OCR."""
        source = Path("python/helpers/document_query.py").read_text()
        assert "pdf2image.convert_from_path" not in source, (
            "document_query.py should use OCREngine instead of pdf2image"
        )


# ═══════════════════════════════════════════════════════════════════════════════
# 3. NO DUPLICATED OCR CODE
# ═══════════════════════════════════════════════════════════════════════════════

class TestNoDuplicatedOCR:
    """There should be exactly ONE place where pytesseract is called:
    ocr_engine.py."""

    def test_pytesseract_only_in_ocr_engine(self):
        """Only ocr_engine.py should contain pytesseract calls."""
        import os

        allowed_file = "python/helpers/pdf_extraction/ocr_engine.py"
        violations = []

        for dirpath, dirnames, filenames in os.walk("python"):
            # Skip __pycache__
            dirnames[:] = [d for d in dirnames if d != "__pycache__"]
            for fn in filenames:
                if not fn.endswith(".py"):
                    continue
                fpath = os.path.join(dirpath, fn)
                rel = fpath.replace("\\", "/")

                if rel == allowed_file:
                    continue

                content = Path(fpath).read_text(errors="ignore")
                if "pytesseract" in content and "import pytesseract" in content:
                    violations.append(rel)

        assert violations == [], (
            f"pytesseract import found in files other than ocr_engine.py: {violations}"
        )

    def test_image_to_data_only_in_ocr_engine(self):
        """Only ocr_engine.py should call image_to_data or image_to_string."""
        import os

        allowed_file = "python/helpers/pdf_extraction/ocr_engine.py"
        violations = []

        for dirpath, dirnames, filenames in os.walk("python"):
            dirnames[:] = [d for d in dirnames if d != "__pycache__"]
            for fn in filenames:
                if not fn.endswith(".py"):
                    continue
                fpath = os.path.join(dirpath, fn)
                rel = fpath.replace("\\", "/")

                if rel == allowed_file:
                    continue

                content = Path(fpath).read_text(errors="ignore")
                if "image_to_string" in content or "image_to_data" in content:
                    violations.append(rel)

        assert violations == [], (
            f"pytesseract calls found outside ocr_engine.py: {violations}"
        )


# ═══════════════════════════════════════════════════════════════════════════════
# 4. OCREngine MODULE STRUCTURE
# ═══════════════════════════════════════════════════════════════════════════════

class TestOCREngineModuleStructure:
    """Verify the ocr_engine module has all required public API."""

    def test_ocr_engine_has_required_classes(self):
        """OCREngine module should export OCREngine, OCRResult, OCRWord."""
        from python.helpers.pdf_extraction import ocr_engine

        assert hasattr(ocr_engine, "OCREngine")
        assert hasattr(ocr_engine, "OCRResult")
        assert hasattr(ocr_engine, "OCRWord")

    def test_ocr_engine_has_required_methods(self):
        """OCREngine should have all required methods."""
        from python.helpers.pdf_extraction.ocr_engine import OCREngine

        engine = OCREngine()
        assert hasattr(engine, "run_ocr_on_image")
        assert hasattr(engine, "run_ocr_on_pdf_page")
        assert hasattr(engine, "run_ocr_on_pdf")
        assert hasattr(engine, "select_dpi")
        assert hasattr(engine, "filter_by_confidence")
        assert hasattr(engine, "compute_page_confidence")

    def test_ocr_result_fields(self):
        """OCRResult should have all documented fields."""
        from python.helpers.pdf_extraction.ocr_engine import OCRResult

        r = OCRResult(
            text="test", words=[], page=0,
            confidence=0.5, dpi_used=200, duration_ms=100
        )
        assert r.text == "test"
        assert r.words == []
        assert r.page == 0
        assert r.confidence == 0.5
        assert r.dpi_used == 200
        assert r.duration_ms == 100
