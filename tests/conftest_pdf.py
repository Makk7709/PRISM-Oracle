"""
PDF Test Fixtures — shared pytest fixtures for all PDF-related tests.

Provides:
- pdf_fixtures_dir: Path to fixtures/pdfs/
- golden_dir: Path to golden/pdf_extraction/
- regenerate_golden: Whether to regenerate golden files (--regen-golden flag)
- Per-fixture helpers for loading PDF bytes and paths.

Usage in tests:
    def test_something(pdf_fixtures_dir):
        pdf_path = pdf_fixtures_dir / "text_simple.pdf"
        ...

Copyright 2025 Korev AI - Proprietary
"""

import json
import os
from pathlib import Path
from typing import Any

import pytest

from tests.fixtures.pdf_generator import (
    generate_all,
    get_fixture_path,
    get_fixture_bytes,
    list_fixtures,
    FIXTURES_DIR,
)


# ═══════════════════════════════════════════════════════════════════════════════
# PYTEST OPTIONS
# ═══════════════════════════════════════════════════════════════════════════════

# NOTE: pytest_addoption is defined here and auto-loaded via pytest_plugins
# in conftest.py. This is safe because pytest merges addoption hooks.
def pytest_addoption(parser):
    """Add custom CLI options for PDF tests."""
    try:
        parser.addoption(
            "--regen-golden",
            action="store_true",
            default=False,
            help="Regenerate golden files for characterization tests",
        )
    except ValueError:
        pass  # Already registered (e.g. via another conftest)


# ═══════════════════════════════════════════════════════════════════════════════
# DIRECTORIES
# ═══════════════════════════════════════════════════════════════════════════════

GOLDEN_DIR = Path(__file__).parent / "golden" / "pdf_extraction"


@pytest.fixture(scope="session")
def pdf_fixtures_dir() -> Path:
    """Path to generated PDF fixtures. Generates them if missing."""
    if not any(FIXTURES_DIR.glob("*.pdf")):
        generate_all()
    return FIXTURES_DIR


@pytest.fixture(scope="session")
def golden_dir() -> Path:
    """Path to golden files directory."""
    GOLDEN_DIR.mkdir(parents=True, exist_ok=True)
    return GOLDEN_DIR


@pytest.fixture(scope="session")
def regenerate_golden(request) -> bool:
    """Whether to regenerate golden files."""
    return request.config.getoption("--regen-golden", default=False)


# ═══════════════════════════════════════════════════════════════════════════════
# PER-FIXTURE ACCESSORS
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.fixture(scope="session")
def pdf_text_simple(pdf_fixtures_dir) -> Path:
    return get_fixture_path("text_simple")


@pytest.fixture(scope="session")
def pdf_text_multipage(pdf_fixtures_dir) -> Path:
    return get_fixture_path("text_multipage")


@pytest.fixture(scope="session")
def pdf_table_simple(pdf_fixtures_dir) -> Path:
    return get_fixture_path("table_simple")


@pytest.fixture(scope="session")
def pdf_table_financial(pdf_fixtures_dir) -> Path:
    return get_fixture_path("table_financial")


@pytest.fixture(scope="session")
def pdf_mixed_content(pdf_fixtures_dir) -> Path:
    return get_fixture_path("mixed_content")


@pytest.fixture(scope="session")
def pdf_empty(pdf_fixtures_dir) -> Path:
    return get_fixture_path("empty")


@pytest.fixture(scope="session")
def pdf_single_word(pdf_fixtures_dir) -> Path:
    return get_fixture_path("single_word")


@pytest.fixture(scope="session")
def pdf_dense_text(pdf_fixtures_dir) -> Path:
    return get_fixture_path("dense_text")


@pytest.fixture(scope="session")
def pdf_unicode_content(pdf_fixtures_dir) -> Path:
    return get_fixture_path("unicode_content")


@pytest.fixture(scope="session")
def pdf_corrupted(pdf_fixtures_dir) -> Path:
    return get_fixture_path("corrupted")


@pytest.fixture(scope="session")
def pdf_two_tables(pdf_fixtures_dir) -> Path:
    return get_fixture_path("two_tables")


# ═══════════════════════════════════════════════════════════════════════════════
# ALL FIXTURES AS PARAMS
# ═══════════════════════════════════════════════════════════════════════════════

_ALL_VALID_FIXTURES = [
    f for f in list_fixtures() if f not in ("corrupted",)
]


@pytest.fixture(
    scope="session",
    params=_ALL_VALID_FIXTURES,
    ids=lambda f: f,
)
def any_valid_pdf(request, pdf_fixtures_dir) -> Path:
    """Parametrized fixture yielding every valid PDF fixture path."""
    return get_fixture_path(request.param)


# ═══════════════════════════════════════════════════════════════════════════════
# GOLDEN FILE HELPERS
# ═══════════════════════════════════════════════════════════════════════════════

class GoldenFileHelper:
    """Helper for reading/writing golden files."""

    def __init__(self, golden_dir: Path, regenerate: bool):
        self._dir = golden_dir
        self._regen = regenerate

    def assert_or_create(self, name: str, actual: dict[str, Any]) -> None:
        """
        Compare actual result to golden file.
        If golden file doesn't exist or --regen-golden is set, create it.
        Otherwise assert equality.
        """
        filepath = self._dir / f"{name}.json"

        if self._regen or not filepath.exists():
            filepath.parent.mkdir(parents=True, exist_ok=True)
            filepath.write_text(
                json.dumps(actual, indent=2, ensure_ascii=False, sort_keys=True) + "\n"
            )
            if not filepath.exists():
                pytest.fail(f"Failed to write golden file: {filepath}")
            if self._regen:
                pytest.skip(f"Golden file regenerated: {filepath.name}")
            else:
                pytest.skip(f"Golden file created: {filepath.name} — run again to validate")
        
        expected = json.loads(filepath.read_text())
        assert actual == expected, (
            f"Golden file mismatch: {filepath.name}\n"
            f"To regenerate: pytest --regen-golden\n"
            f"Expected:\n{json.dumps(expected, indent=2)}\n\n"
            f"Actual:\n{json.dumps(actual, indent=2)}"
        )

    def assert_text_or_create(self, name: str, actual: str) -> None:
        """Same as assert_or_create but for plain text."""
        filepath = self._dir / f"{name}.txt"

        if self._regen or not filepath.exists():
            filepath.parent.mkdir(parents=True, exist_ok=True)
            filepath.write_text(actual)
            if self._regen:
                pytest.skip(f"Golden file regenerated: {filepath.name}")
            else:
                pytest.skip(f"Golden file created: {filepath.name} — run again to validate")
        
        expected = filepath.read_text()
        assert actual == expected, (
            f"Golden text mismatch: {filepath.name}\n"
            f"To regenerate: pytest --regen-golden"
        )


@pytest.fixture(scope="session")
def golden(golden_dir, regenerate_golden) -> GoldenFileHelper:
    """Golden file comparison helper."""
    return GoldenFileHelper(golden_dir, regenerate_golden)
