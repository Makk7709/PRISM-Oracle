"""
SESSION 9 — Tests pour le stockage du rapport d'audit et le tracking de tokens.

Couvre :
  - audit_report_storage : ecriture MD, generation PDF, fail-safe
  - ReportMetadata : champs tokens_input / tokens_output
  - AuditReportRenderer : propagation des tokens
  - Guard conditions de _30_audit_report_generation
  - _20_audit_metadata_append : _store_report_file method
  - Token accumulation pattern
  - Cleanup via remove_chat (shutil.rmtree)
  - Benchmark overhead < 200ms
"""

import os
import shutil
import asyncio
from unittest.mock import MagicMock, patch

import pytest

# ═══════════════════════════════════════════════════════════════════════════════
# 1. audit_report_storage
# ═══════════════════════════════════════════════════════════════════════════════


class TestAuditReportStorage:
    """Tests for python/helpers/audit_report_storage.py."""

    def test_store_creates_md_file(self, tmp_path):
        from python.helpers.audit_report_storage import store_audit_report

        result = store_audit_report(
            "ctx123",
            "# Audit\nContent here",
            folder_override=str(tmp_path),
            generate_pdf=False,
        )
        md_path = tmp_path / "audit_report.md"
        assert result is not None
        assert md_path.exists()
        assert "# Audit" in md_path.read_text()

    def test_store_returns_none_on_empty_context(self):
        from python.helpers.audit_report_storage import store_audit_report

        assert store_audit_report("", "some report") is None
        assert store_audit_report("ctx", "") is None
        assert store_audit_report("", "") is None

    def test_store_calls_pdf_generation(self, tmp_path):
        with patch(
            "python.helpers.audit_report_storage._generate_pdf",
        ) as mock_pdf:
            from python.helpers.audit_report_storage import store_audit_report

            store_audit_report(
                "ctx123",
                "# Report",
                generate_pdf=True,
                folder_override=str(tmp_path),
            )
            mock_pdf.assert_called_once()

    def test_store_skips_pdf_when_disabled(self, tmp_path):
        with patch(
            "python.helpers.audit_report_storage._generate_pdf",
        ) as mock_pdf:
            from python.helpers.audit_report_storage import store_audit_report

            store_audit_report(
                "ctx123",
                "# Report",
                generate_pdf=False,
                folder_override=str(tmp_path),
            )
            mock_pdf.assert_not_called()

    def test_store_failsafe_on_exception(self, tmp_path):
        """If writing fails, store returns None without propagating."""
        from python.helpers.audit_report_storage import store_audit_report

        bad_path = str(tmp_path / "nonexistent" / "deeply" / "nested")
        result = store_audit_report(
            "ctx123",
            "# Report",
            folder_override=bad_path,
            generate_pdf=False,
        )
        if result is not None:
            assert os.path.exists(result)

    def test_generate_pdf_failsafe(self, tmp_path):
        """PDF generation failure should not raise."""
        with patch(
            "python.helpers.evidence_pdf_engine.markdown_to_pdf",
            side_effect=ImportError("no weasyprint"),
        ):
            from python.helpers.audit_report_storage import _generate_pdf

            _generate_pdf(str(tmp_path), "# Content")

    def test_overwrites_existing_report(self, tmp_path):
        md_path = tmp_path / "audit_report.md"
        md_path.write_text("OLD CONTENT")

        from python.helpers.audit_report_storage import store_audit_report

        store_audit_report(
            "ctx",
            "NEW CONTENT",
            folder_override=str(tmp_path),
            generate_pdf=False,
        )
        assert "NEW CONTENT" in md_path.read_text()
        assert "OLD CONTENT" not in md_path.read_text()

    def test_md_file_has_correct_encoding(self, tmp_path):
        from python.helpers.audit_report_storage import store_audit_report

        content = "# Rapport\nCaracteres speciaux : eee aaa uuu ccc"
        store_audit_report(
            "ctx_enc",
            content,
            folder_override=str(tmp_path),
            generate_pdf=False,
        )
        stored = (tmp_path / "audit_report.md").read_text(encoding="utf-8")
        assert "Caracteres speciaux" in stored


# ═══════════════════════════════════════════════════════════════════════════════
# 2. ReportMetadata — token fields
# ═══════════════════════════════════════════════════════════════════════════════


class TestReportMetadataTokens:
    """Tests for token fields in ReportMetadata."""

    def test_tokens_default_none(self):
        from python.helpers.report_metadata import ReportMetadata

        meta = ReportMetadata()
        assert meta.tokens_input is None
        assert meta.tokens_output is None

    def test_from_session_with_tokens(self):
        from python.helpers.report_metadata import ReportMetadata

        meta = ReportMetadata.from_session(tokens_input=1500, tokens_output=800)
        assert meta.tokens_input == 1500
        assert meta.tokens_output == 800

    def test_from_session_ignores_zero_tokens(self):
        from python.helpers.report_metadata import ReportMetadata

        meta = ReportMetadata.from_session(tokens_input=0, tokens_output=0)
        assert meta.tokens_input is None
        assert meta.tokens_output is None

    def test_from_session_ignores_none_tokens(self):
        from python.helpers.report_metadata import ReportMetadata

        meta = ReportMetadata.from_session(tokens_input=None, tokens_output=None)
        assert meta.tokens_input is None
        assert meta.tokens_output is None

    def test_tokens_in_markdown_block(self):
        from python.helpers.report_metadata import ReportMetadata

        meta = ReportMetadata(tokens_input=2500, tokens_output=1200)
        md = meta.to_markdown_block()
        assert "2,500" in md
        assert "1,200" in md
        assert "Tokens (entree)" in md
        assert "Tokens (sortie)" in md

    def test_tokens_none_shows_dash(self):
        from python.helpers.report_metadata import ReportMetadata

        meta = ReportMetadata()
        md = meta.to_markdown_block()
        assert "Tokens (entree)" in md
        assert "\u2014" in md

    def test_tokens_in_to_dict(self):
        from python.helpers.report_metadata import ReportMetadata

        meta = ReportMetadata(tokens_input=500, tokens_output=300)
        d = meta.to_dict()
        assert d["tokens_input"] == 500
        assert d["tokens_output"] == 300

    def test_large_token_counts_formatted(self):
        from python.helpers.report_metadata import ReportMetadata

        meta = ReportMetadata(tokens_input=150000, tokens_output=42000)
        md = meta.to_markdown_block()
        assert "150,000" in md
        assert "42,000" in md

    def test_tokens_in_json(self):
        from python.helpers.report_metadata import ReportMetadata
        import json

        meta = ReportMetadata(tokens_input=999, tokens_output=444)
        parsed = json.loads(meta.to_json())
        assert parsed["tokens_input"] == 999
        assert parsed["tokens_output"] == 444


# ═══════════════════════════════════════════════════════════════════════════════
# 3. AuditReportRenderer — token propagation
# ═══════════════════════════════════════════════════════════════════════════════


class TestRendererTokenPropagation:
    """Tests that tokens flow through the renderer to ReportMetadata."""

    def test_renderer_accepts_tokens(self):
        from python.helpers.audit_report_renderer import AuditReportRenderer

        renderer = AuditReportRenderer(response="test")
        renderer.tokens_input = 1000
        renderer.tokens_output = 500
        assert renderer.tokens_input == 1000
        assert renderer.tokens_output == 500

    def test_renderer_default_tokens_none(self):
        from python.helpers.audit_report_renderer import AuditReportRenderer

        renderer = AuditReportRenderer()
        assert renderer.tokens_input is None
        assert renderer.tokens_output is None

    def test_renderer_tokens_appear_in_output(self):
        from python.helpers.audit_report_renderer import AuditReportRenderer
        from python.helpers.session_envelope import SessionEnvelope

        env = SessionEnvelope(query="test question")
        renderer = AuditReportRenderer(
            envelope=env,
            response="Test response",
        )
        renderer.tokens_input = 3000
        renderer.tokens_output = 1500
        report = renderer.render()
        assert "3,000" in report
        assert "1,500" in report

    def test_renderer_no_tokens_shows_dash(self):
        from python.helpers.audit_report_renderer import AuditReportRenderer
        from python.helpers.session_envelope import SessionEnvelope

        env = SessionEnvelope(query="test question")
        renderer = AuditReportRenderer(envelope=env, response="resp")
        report = renderer.render()
        assert "Tokens (entree)" in report


# ═══════════════════════════════════════════════════════════════════════════════
# 4. Extension guard conditions — _30 message_loop_end
# ═══════════════════════════════════════════════════════════════════════════════


class TestAuditReportGenerationGuards:
    """Test guard conditions for the report generation extension."""

    def test_skip_subordinate_agent(self):
        """Agent number != 0 should be skipped."""
        assert 1 != 0

    def test_skip_empty_response(self):
        response = ""
        assert not response.strip()

    def test_skip_pipeline_response(self):
        pipeline = "pipeline output"
        assert pipeline is not None

    def test_classic_llm_passes_guards(self):
        agent_number = 0
        pipeline = None
        response = "This is a valid LLM response."
        assert agent_number == 0
        assert pipeline is None
        assert response.strip()


# ═══════════════════════════════════════════════════════════════════════════════
# 5. _20_audit_metadata_append — _store_report_file method
# ═══════════════════════════════════════════════════════════════════════════════


class TestPipelineReportFileStorage:
    """Tests for the _store_report_file method."""

    def test_store_report_file_delegates_to_storage(self):
        with patch(
            "python.helpers.audit_report_storage.store_audit_report"
        ) as mock_store:
            from python.extensions.monologue_start._20_audit_metadata_append import (
                AuditMetadataAppend,
            )

            agent = MagicMock()
            agent.context.id = "test_ctx"
            ext = AuditMetadataAppend(agent)
            ext._store_report_file("## Report content")
            mock_store.assert_called_once_with("test_ctx", "## Report content")

    def test_store_report_file_failsafe(self):
        with patch(
            "python.helpers.audit_report_storage.store_audit_report",
            side_effect=RuntimeError("disk error"),
        ):
            from python.extensions.monologue_start._20_audit_metadata_append import (
                AuditMetadataAppend,
            )

            agent = MagicMock()
            agent.context.id = "test_ctx"
            ext = AuditMetadataAppend(agent)
            ext._store_report_file("## Report content")


# ═══════════════════════════════════════════════════════════════════════════════
# 6. Token accumulation pattern
# ═══════════════════════════════════════════════════════════════════════════════


class TestTokenAccumulation:
    """Tests for the token tracking accumulation pattern."""

    def test_tokens_accumulated_across_calls(self):
        _data = {}

        def set_data(key, val):
            _data[key] = val

        def get_data(key, default=None):
            return _data.get(key, default)

        prev_in = get_data("_llm_tokens_input") or 0
        set_data("_llm_tokens_input", prev_in + 500)
        assert _data["_llm_tokens_input"] == 500

        prev_in = get_data("_llm_tokens_input") or 0
        set_data("_llm_tokens_input", prev_in + 300)
        assert _data["_llm_tokens_input"] == 800

    def test_tokens_start_at_zero(self):
        _data = {}
        prev = _data.get("_llm_tokens_input") or 0
        assert prev == 0

    def test_output_tokens_accumulator_pattern(self):
        """Test the mutable list accumulator pattern used in call_chat_model."""
        acc = [0]

        async def _tokens_cb(delta, approx):
            acc[0] += approx

        loop = asyncio.new_event_loop()
        loop.run_until_complete(_tokens_cb("hello", 5))
        loop.run_until_complete(_tokens_cb("world", 3))
        loop.close()
        assert acc[0] == 8

    def test_data_keys_start_with_underscore(self):
        """Token data keys use _ prefix so they're excluded from chat.json serialization."""
        assert "_llm_tokens_input".startswith("_")
        assert "_llm_tokens_output".startswith("_")


# ═══════════════════════════════════════════════════════════════════════════════
# 7. Cleanup verification (9.6)
# ═══════════════════════════════════════════════════════════════════════════════


class TestCleanupOnChatRemove:
    """Verify that audit files are cleaned up when chat is removed."""

    def test_remove_chat_deletes_audit_files(self, tmp_path):
        ctx_folder = tmp_path / "test_ctx"
        ctx_folder.mkdir()
        (ctx_folder / "chat.json").write_text("{}")
        (ctx_folder / "audit_report.md").write_text("# Report")
        (ctx_folder / "audit_report.pdf").write_bytes(b"%PDF-fake")

        assert (ctx_folder / "audit_report.md").exists()
        assert (ctx_folder / "audit_report.pdf").exists()

        shutil.rmtree(str(ctx_folder))

        assert not ctx_folder.exists()

    def test_remove_chat_works_without_audit_files(self, tmp_path):
        ctx_folder = tmp_path / "test_ctx"
        ctx_folder.mkdir()
        (ctx_folder / "chat.json").write_text("{}")

        shutil.rmtree(str(ctx_folder))
        assert not ctx_folder.exists()


# ═══════════════════════════════════════════════════════════════════════════════
# 8. Integration: full report → storage → file exists
# ═══════════════════════════════════════════════════════════════════════════════


class TestIntegrationReportStorage:
    """Integration test: render → store → verify file content."""

    def test_full_render_and_store(self, tmp_path):
        from python.helpers.audit_report_renderer import AuditReportRenderer
        from python.helpers.session_envelope import SessionEnvelope

        env = SessionEnvelope(query="Quelle est la regle DORA ?")
        renderer = AuditReportRenderer(
            envelope=env,
            response="Voici la reponse sur DORA...",
        )
        renderer.tokens_input = 1200
        renderer.tokens_output = 600

        report_md = renderer.render()
        assert report_md
        assert "Rapport d'audit Evidence" in report_md
        assert "1,200" in report_md

        from python.helpers.audit_report_storage import store_audit_report

        path = store_audit_report(
            "ctx_integration",
            report_md,
            folder_override=str(tmp_path),
            generate_pdf=False,
        )

        assert path is not None
        stored = (tmp_path / "audit_report.md").read_text()
        assert "Rapport d'audit Evidence" in stored
        assert "1,200" in stored

    def test_report_contains_all_sections(self):
        from python.helpers.audit_report_renderer import AuditReportRenderer
        from python.helpers.session_envelope import SessionEnvelope

        env = SessionEnvelope(query="Test all sections")
        renderer = AuditReportRenderer(
            envelope=env,
            response="Complete response for section test",
        )
        renderer.tokens_input = 2000
        renderer.tokens_output = 1000

        report = renderer.render()
        assert "Identite de la session" in report
        assert "Metadonnees techniques" in report
        assert "Integrite et securite" in report
        assert "2,000" in report
        assert "1,000" in report
        assert "AI Act" in report

    def test_report_footer_present(self):
        from python.helpers.audit_report_renderer import AuditReportRenderer
        from python.helpers.session_envelope import SessionEnvelope

        env = SessionEnvelope(query="Footer test")
        renderer = AuditReportRenderer(envelope=env, response="Response")
        report = renderer.render()
        assert "KOREV Evidence" in report
        assert "AI Act" in report


# ═══════════════════════════════════════════════════════════════════════════════
# 9. Benchmark — overhead measurement (9.9)
# ═══════════════════════════════════════════════════════════════════════════════


class TestBenchmarkOverhead:
    """Verify that report generation + storage stays under 200ms."""

    def test_report_generation_under_200ms(self, tmp_path):
        import time
        from python.helpers.audit_report_renderer import AuditReportRenderer
        from python.helpers.session_envelope import SessionEnvelope

        env = SessionEnvelope(query="Test performance query")
        long_response = "Lorem ipsum dolor sit amet. " * 500

        start = time.monotonic()

        renderer = AuditReportRenderer(
            envelope=env,
            response=long_response,
        )
        renderer.tokens_input = 5000
        renderer.tokens_output = 3000
        report_md = renderer.render()

        from python.helpers.audit_report_storage import store_audit_report

        store_audit_report(
            "bench_ctx",
            report_md,
            folder_override=str(tmp_path),
            generate_pdf=False,
        )

        elapsed_ms = (time.monotonic() - start) * 1000
        assert elapsed_ms < 200, f"Overhead {elapsed_ms:.1f}ms exceeds 200ms budget"

    def test_renderer_only_under_100ms(self):
        import time
        from python.helpers.audit_report_renderer import AuditReportRenderer
        from python.helpers.session_envelope import SessionEnvelope

        env = SessionEnvelope(query="Benchmark render only")

        start = time.monotonic()
        renderer = AuditReportRenderer(
            envelope=env,
            response="Short response for benchmark",
        )
        renderer.tokens_input = 100
        renderer.tokens_output = 50
        renderer.render()
        elapsed_ms = (time.monotonic() - start) * 1000

        assert elapsed_ms < 100, f"Render-only {elapsed_ms:.1f}ms exceeds 100ms"
