"""
TDD — Strict validation tests for deploy/Dockerfile.backend OCR dependencies.

These tests verify that the backend image includes all required packages
for OCR to function: poppler-utils (pdf2image), tesseract-ocr, language packs.

IMPORTANT: Tests T02–T04 explicitly target the "runtime" stage of the
multi-stage Dockerfile, NOT the "python-deps" build stage.

Spec: docs/AUDIT_OCR_2026-02-11.md
Rule: No simplification — each dependency must be explicitly asserted.
"""

from __future__ import annotations

import os
import pathlib
import re
import subprocess

import pytest

ROOT = pathlib.Path(__file__).resolve().parent.parent
DOCKERFILE = ROOT / "deploy" / "Dockerfile.backend"

# Image name derived from docker-compose (same logic as compose file)
_IMAGE = os.environ.get("EVIDENCE_IMAGE", "korev/evidence-backend:latest")


def _read_dockerfile() -> str:
    return DOCKERFILE.read_text(encoding="utf-8", errors="replace")


def _extract_runtime_stage() -> str:
    """Return only the 'runtime' stage of the multi-stage Dockerfile.

    Searches for 'FROM ... AS runtime' and returns everything from that
    line until the next FROM or end-of-file.  This ensures tests assert
    on the *runtime* image that ships, not on the build-only stage.
    """
    content = _read_dockerfile()
    # Match 'FROM <image> AS runtime' (case-insensitive)
    match = re.search(r"^FROM\s+.+\s+AS\s+runtime", content, re.MULTILINE | re.IGNORECASE)
    assert match, "Dockerfile must contain a 'FROM ... AS runtime' stage"
    stage_start = match.start()

    # Find the next FROM (= next stage) or end-of-file
    next_from = re.search(r"^FROM\s+", content[match.end() :], re.MULTILINE)
    if next_from:
        stage_end = match.end() + next_from.start()
    else:
        stage_end = len(content)

    return content[stage_start:stage_end]


def _extract_runtime_apt_block() -> str:
    """Return the first 'RUN apt-get' block inside the runtime stage."""
    runtime = _extract_runtime_stage()
    apt_match = re.search(r"RUN\s+apt-get\s+update.*?(?=\nRUN\s|\nCOPY\s|\nFROM\s|\nENV\s|\nUSER\s|\Z)",
                          runtime, re.DOTALL)
    assert apt_match, "runtime stage must contain a RUN apt-get block"
    return apt_match.group(0)


# ═══════════════════════════════════════════════════════════════════════════════
# T01 — Dockerfile exists
# ═══════════════════════════════════════════════════════════════════════════════

class TestT01_DockerfileExists:
    def test_dockerfile_backend_exists(self):
        assert DOCKERFILE.exists(), "deploy/Dockerfile.backend must exist"

    def test_dockerfile_has_runtime_stage(self):
        content = _read_dockerfile()
        assert re.search(r"FROM\s+.+\s+AS\s+runtime", content, re.IGNORECASE), (
            "Dockerfile.backend must define a 'FROM ... AS runtime' stage"
        )


# ═══════════════════════════════════════════════════════════════════════════════
# T02 — Poppler (required by pdf2image convert_from_path)
# ═══════════════════════════════════════════════════════════════════════════════

class TestT02_PopplerRequired:
    """poppler-utils provides pdftoppm — required by pdf2image."""

    def test_poppler_in_runtime_stage(self):
        runtime = _extract_runtime_stage()
        assert "poppler-utils" in runtime, (
            "runtime stage MUST install poppler-utils — "
            "pdf2image.convert_from_path requires it for PDF-to-image conversion"
        )

    def test_poppler_in_runtime_apt_block(self):
        apt_block = _extract_runtime_apt_block()
        assert "poppler-utils" in apt_block, (
            "poppler-utils must be in the runtime apt-get RUN block"
        )


# ═══════════════════════════════════════════════════════════════════════════════
# T03 — Tesseract OCR engine
# ═══════════════════════════════════════════════════════════════════════════════

class TestT03_TesseractRequired:
    """Tesseract is the OCR engine used by pytesseract."""

    def test_tesseract_ocr_in_runtime(self):
        runtime = _extract_runtime_stage()
        assert "tesseract-ocr" in runtime, (
            "runtime stage MUST install tesseract-ocr (base package)"
        )

    def test_tesseract_ocr_fra_in_runtime(self):
        runtime = _extract_runtime_stage()
        assert "tesseract-ocr-fra" in runtime, (
            "runtime stage MUST install tesseract-ocr-fra for French"
        )

    def test_tesseract_ocr_eng_in_runtime(self):
        runtime = _extract_runtime_stage()
        assert "tesseract-ocr-eng" in runtime, (
            "runtime stage MUST install tesseract-ocr-eng for English"
        )


# ═══════════════════════════════════════════════════════════════════════════════
# T04 — All OCR deps in single RUN (layer efficiency)
# ═══════════════════════════════════════════════════════════════════════════════

class TestT04_OCRDepsGrouped:
    """OCR packages should be grouped in the same apt-get RUN."""

    def test_tesseract_and_poppler_in_same_runtime_apt_block(self):
        apt_block = _extract_runtime_apt_block()
        assert "tesseract-ocr" in apt_block and "poppler-utils" in apt_block, (
            "tesseract and poppler must be in the same apt-get RUN "
            "inside the runtime stage"
        )

    def test_all_language_packs_in_same_runtime_apt_block(self):
        apt_block = _extract_runtime_apt_block()
        for lang in ("tesseract-ocr-fra", "tesseract-ocr-eng"):
            assert lang in apt_block, (
                f"{lang} must be in the runtime apt-get block alongside tesseract-ocr"
            )


# ═══════════════════════════════════════════════════════════════════════════════
# T05 — requirements.txt : whisper version pinned (reproducibility)
# ═══════════════════════════════════════════════════════════════════════════════

class TestT05_WhisperPinned:
    """openai-whisper must be pinned to a specific version in requirements.txt."""

    def test_whisper_in_requirements(self):
        reqs = (ROOT / "requirements.txt").read_text()
        assert "openai-whisper" in reqs, "openai-whisper must be in requirements.txt"

    def test_whisper_version_pinned(self):
        reqs = (ROOT / "requirements.txt").read_text()
        # Must be pinned with == (not >= or git+)
        assert re.search(r"openai-whisper==\d{8}", reqs), (
            "openai-whisper must be pinned to a dated release (e.g. ==20250625), "
            "not a git+https or unpinned version"
        )


# ═══════════════════════════════════════════════════════════════════════════════
# T06 — Build succeeds (integration)
# ═══════════════════════════════════════════════════════════════════════════════

class TestT06_DockerBuild:
    """Verify the backend image builds successfully."""

    @pytest.mark.slow
    def test_docker_build_succeeds(self):
        result = subprocess.run(
            [
                "docker", "compose",
                "-f", str(ROOT / "deploy" / "docker-compose.yml"),
                "build", "evidence-backend",
            ],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=900,
        )
        assert result.returncode == 0, f"Docker build failed:\n{result.stderr[-2000:]}"


# ═══════════════════════════════════════════════════════════════════════════════
# T07 — Whisper + OCR imports in container (smoke test)
# ═══════════════════════════════════════════════════════════════════════════════

class TestT07_ContainerSmokeWhisperOcr:
    """Verify whisper, pytesseract, pdf2image are importable in the built image."""

    @pytest.mark.slow
    def test_whisper_importable(self):
        result = subprocess.run(
            ["docker", "run", "--rm", _IMAGE, "python", "-c", "import whisper; print('whisper OK')"],
            capture_output=True, text=True, timeout=60,
        )
        assert result.returncode == 0, f"whisper import failed: {result.stderr}"
        assert "whisper OK" in result.stdout

    @pytest.mark.slow
    def test_pytesseract_importable(self):
        result = subprocess.run(
            ["docker", "run", "--rm", _IMAGE, "python", "-c", "import pytesseract; print('pytesseract OK')"],
            capture_output=True, text=True, timeout=60,
        )
        assert result.returncode == 0, f"pytesseract import failed: {result.stderr}"
        assert "pytesseract OK" in result.stdout

    @pytest.mark.slow
    def test_pdf2image_importable(self):
        result = subprocess.run(
            ["docker", "run", "--rm", _IMAGE, "python", "-c", "import pdf2image; print('pdf2image OK')"],
            capture_output=True, text=True, timeout=60,
        )
        assert result.returncode == 0, f"pdf2image import failed: {result.stderr}"
        assert "pdf2image OK" in result.stdout

    @pytest.mark.slow
    def test_tesseract_binary_present(self):
        """Verify tesseract CLI is available in the container."""
        result = subprocess.run(
            ["docker", "run", "--rm", _IMAGE, "tesseract", "--version"],
            capture_output=True, text=True, timeout=30,
        )
        assert result.returncode == 0, f"tesseract binary not found: {result.stderr}"
        assert "tesseract" in result.stdout.lower()

    @pytest.mark.slow
    def test_pdftoppm_binary_present(self):
        """Verify pdftoppm (poppler) is available in the container."""
        result = subprocess.run(
            ["docker", "run", "--rm", _IMAGE, "pdftoppm", "-v"],
            capture_output=True, text=True, timeout=30,
        )
        # pdftoppm -v outputs to stderr
        combined = result.stdout + result.stderr
        assert "pdftoppm" in combined.lower() or result.returncode == 0, (
            f"pdftoppm binary not found: {combined}"
        )
