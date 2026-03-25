import os
from dataclasses import dataclass

from python.helpers.document_workload import (
    contains_doc_keywords,
    is_document_heavy_request,
    select_utility_model_config,
)


@dataclass
class _Model:
    name: str


class TestDocumentWorkloadDetection:
    def test_detects_by_many_attachments(self, monkeypatch):
        monkeypatch.setenv("EVIDENCE_DOC_HEAVY_MIN_ATTACHMENTS", "6")
        attachments = [f"/tmp/doc_{i}.pdf" for i in range(6)]
        assert is_document_heavy_request("tri des factures", attachments) is True

    def test_detects_by_many_pdfs_and_keywords(self, monkeypatch):
        monkeypatch.setenv("EVIDENCE_DOC_HEAVY_MIN_PDFS", "3")
        attachments = ["/tmp/a.pdf", "/tmp/b.pdf", "/tmp/c.pdf"]
        assert (
            is_document_heavy_request(
                "classe moi les factures PEFC avec toutes les pages",
                attachments,
            )
            is True
        )

    def test_detects_by_explicit_volume_in_message(self):
        assert is_document_heavy_request("classer 80 pdf par type PEFC", []) is True
        assert is_document_heavy_request("analyse 120 factures", []) is True

    def test_non_heavy_for_small_simple_prompt(self):
        assert is_document_heavy_request("resume ce texte", ["/tmp/one.pdf"]) is False

    def test_keyword_detection(self):
        assert contains_doc_keywords("Tri des factures PDF PEFC") is True
        assert contains_doc_keywords("bonjour, comment ca va") is False


class TestUtilityModelRouting:
    def test_routes_to_chat_model_for_doc_heavy(self):
        utility = _Model(name="gpt-4.1-mini")
        chat = _Model(name="gpt-4.1")
        selected, reason = select_utility_model_config(
            utility_model_config=utility,
            chat_model_config=chat,
            message="classer 80 pdf de factures",
            attachments=[],
        )
        assert selected is chat
        assert reason == "document_heavy_route_to_chat_model"

    def test_keeps_utility_model_for_normal_tasks(self):
        utility = _Model(name="gpt-4.1-mini")
        chat = _Model(name="gpt-4.1")
        selected, reason = select_utility_model_config(
            utility_model_config=utility,
            chat_model_config=chat,
            message="renomme cette conversation",
            attachments=[],
        )
        assert selected is utility
        assert reason == "default_utility_model"

