"""
Security Tests — Expression Injection in DocumentQueryStore filters

Vulnerability: document_uri values are injected directly into simpleeval
expressions via f-string interpolation:
    filter=f"document_uri == '{document_uri}'"

Attack vectors tested:
1. Single-quote breakout  →  ' or True or '
2. Boolean tautology       →  matches ALL documents instead of one
3. Function call injection →  simpleeval built-in functions
4. Nested quotes           →  double-quote / backslash escapes
5. Null byte injection     →  truncation attacks
6. Unicode tricks          →  homoglyph single quotes

These tests MUST FAIL before the fix (RED phase) and PASS after (GREEN phase).
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from langchain_core.documents import Document


# ---------------------------------------------------------------------------
# Helpers: build a minimal mock environment for DocumentQueryStore
# ---------------------------------------------------------------------------

def _make_mock_agent():
    """Create a minimal mock Agent for DocumentQueryStore."""
    agent = MagicMock()
    agent.config = MagicMock()
    agent.config.embeddings_model = "test"
    return agent


def _make_store_with_docs(docs: list[Document]):
    """
    Create a DocumentQueryStore with a pre-populated in-memory vector DB
    containing the given documents.
    """
    from python.helpers.document_query import DocumentQueryStore

    agent = _make_mock_agent()
    store = DocumentQueryStore(agent)

    # Build a fake VectorDB that holds the docs in memory
    all_docs = {doc.metadata.get("id", str(i)): doc for i, doc in enumerate(docs)}

    from python.helpers.vector_db import VectorDB, get_comparator

    fake_vdb = MagicMock(spec=VectorDB)

    # Replicate the REAL search_by_metadata logic from vector_db.py
    # This must mirror the actual implementation to catch injection issues
    async def real_search_by_metadata(filter: str, limit: int = 0):
        comparator = get_comparator(filter)
        result = []
        for doc in all_docs.values():
            if comparator(doc.metadata):
                result.append(doc)
                if 0 < limit <= len(result):
                    break
        return result

    fake_vdb.search_by_metadata = real_search_by_metadata

    # Also provide get_all_docs for list_documents
    mock_inner_db = MagicMock()
    mock_inner_db.get_all_docs.return_value = all_docs
    fake_vdb.db = mock_inner_db

    store.vector_db = fake_vdb

    return store


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def sample_docs():
    """Three documents with distinct URIs."""
    return [
        Document(
            page_content="Secret financial report Q4",
            metadata={
                "id": "doc-secret-1",
                "document_uri": "file:///data/secret_report.pdf",
                "chunk_index": 0,
                "total_chunks": 1,
            },
        ),
        Document(
            page_content="Public marketing brochure",
            metadata={
                "id": "doc-public-1",
                "document_uri": "file:///data/marketing.pdf",
                "chunk_index": 0,
                "total_chunks": 1,
            },
        ),
        Document(
            page_content="Internal HR policy document",
            metadata={
                "id": "doc-hr-1",
                "document_uri": "file:///data/hr_policy.pdf",
                "chunk_index": 0,
                "total_chunks": 1,
            },
        ),
    ]


# ═══════════════════════════════════════════════════════════════════════════
# TEST CLASS: Expression Injection via document_uri
# ═══════════════════════════════════════════════════════════════════════════

class TestExpressionInjectionDocumentQuery:
    """
    Verify that malicious document_uri values cannot break out of the
    filter expression and access other documents.
    """

    @pytest.mark.asyncio
    async def test_single_quote_breakout_tautology(self, sample_docs):
        """
        ATTACK: URI = "' or True or '"
        Injected expression becomes: document_uri == '' or True or ''
        → True for ALL documents (tautology)
        EXPECTED: must return 0 results (no document has that URI)
        """
        store = _make_store_with_docs(sample_docs)
        malicious_uri = "' or True or '"

        chunks = await store._get_document_chunks(malicious_uri)
        assert len(chunks) == 0, (
            f"INJECTION SUCCEEDED: tautology matched {len(chunks)} documents "
            f"instead of 0. Filter bypass confirmed."
        )

    @pytest.mark.asyncio
    async def test_single_quote_breakout_or_1_eq_1(self, sample_docs):
        """
        ATTACK: URI = "x' or '1'=='1"
        Injected expression: document_uri == 'x' or '1'=='1'
        → True for ALL documents
        """
        store = _make_store_with_docs(sample_docs)
        malicious_uri = "x' or '1'=='1"

        chunks = await store._get_document_chunks(malicious_uri)
        assert len(chunks) == 0, (
            f"INJECTION SUCCEEDED: '1'=='1' tautology matched {len(chunks)} docs"
        )

    @pytest.mark.asyncio
    async def test_boolean_operator_injection(self, sample_docs):
        """
        ATTACK: URI contains ' or document_uri != '
        This would make the filter: document_uri == '' or document_uri != ''
        → True for ALL documents
        """
        store = _make_store_with_docs(sample_docs)
        malicious_uri = "' or document_uri != '"

        chunks = await store._get_document_chunks(malicious_uri)
        assert len(chunks) == 0, (
            f"INJECTION SUCCEEDED: boolean operator injection matched {len(chunks)} docs"
        )

    @pytest.mark.asyncio
    async def test_function_call_injection(self, sample_docs):
        """
        ATTACK: URI tries to call a function via simpleeval.
        URI = "' or str(True) or '"
        """
        store = _make_store_with_docs(sample_docs)
        malicious_uri = "' or str(True) or '"

        chunks = await store._get_document_chunks(malicious_uri)
        assert len(chunks) == 0, (
            f"INJECTION SUCCEEDED: function call injection matched {len(chunks)} docs"
        )

    @pytest.mark.asyncio
    async def test_nested_quotes_injection(self, sample_docs):
        """
        ATTACK: URI with escaped/nested quotes.
        URI = \\' or True #
        """
        store = _make_store_with_docs(sample_docs)
        malicious_uri = "\\' or True #"

        chunks = await store._get_document_chunks(malicious_uri)
        assert len(chunks) == 0, (
            f"INJECTION SUCCEEDED: nested quotes injection matched {len(chunks)} docs"
        )

    @pytest.mark.asyncio
    async def test_null_byte_injection(self, sample_docs):
        """
        ATTACK: URI with null byte to truncate the expression.
        URI = "file:///data/secret_report.pdf\\x00' or True or '"
        """
        store = _make_store_with_docs(sample_docs)
        malicious_uri = "file:///data/secret_report.pdf\x00' or True or '"

        chunks = await store._get_document_chunks(malicious_uri)
        # Should match at most 1 doc (the secret_report), not all 3
        assert len(chunks) <= 1, (
            f"INJECTION SUCCEEDED: null byte injection matched {len(chunks)} docs"
        )

    @pytest.mark.asyncio
    async def test_unicode_homoglyph_quote(self, sample_docs):
        """
        ATTACK: URI uses Unicode homoglyph for single quote (U+2019, U+FF07).
        """
        store = _make_store_with_docs(sample_docs)
        # Right single quotation mark (U+2019)
        malicious_uri = "\u2019 or True or \u2019"

        chunks = await store._get_document_chunks(malicious_uri)
        assert len(chunks) == 0, (
            f"INJECTION SUCCEEDED: unicode homoglyph injection matched {len(chunks)} docs"
        )

    @pytest.mark.asyncio
    async def test_legitimate_uri_still_works(self, sample_docs):
        """
        REGRESSION: A legitimate URI must still match its document.
        """
        store = _make_store_with_docs(sample_docs)
        legitimate_uri = "file:///data/marketing.pdf"

        chunks = await store._get_document_chunks(legitimate_uri)
        assert len(chunks) == 1, (
            f"REGRESSION: legitimate URI returned {len(chunks)} instead of 1"
        )
        assert chunks[0].metadata["id"] == "doc-public-1"

    @pytest.mark.asyncio
    async def test_legitimate_uri_with_special_chars(self, sample_docs):
        """
        REGRESSION: URI with legitimate special characters (spaces, accents)
        should not be broken by sanitization.
        """
        special_doc = Document(
            page_content="Document with special name",
            metadata={
                "id": "doc-special-1",
                "document_uri": "file:///data/rapport résumé (2026).pdf",
                "chunk_index": 0,
                "total_chunks": 1,
            },
        )
        store = _make_store_with_docs(sample_docs + [special_doc])
        uri = "file:///data/rapport résumé (2026).pdf"

        chunks = await store._get_document_chunks(uri)
        assert len(chunks) == 1, (
            f"REGRESSION: special char URI returned {len(chunks)} instead of 1"
        )

    @pytest.mark.asyncio
    async def test_nonexistent_uri_returns_empty(self, sample_docs):
        """Normal behavior: non-existent URI returns 0 chunks."""
        store = _make_store_with_docs(sample_docs)
        chunks = await store._get_document_chunks("file:///does/not/exist.pdf")
        assert len(chunks) == 0

    @pytest.mark.asyncio
    async def test_delete_document_injection(self, sample_docs):
        """
        ATTACK: Malicious URI in delete_document should not affect other docs.
        Uses the same filter pattern.
        """
        store = _make_store_with_docs(sample_docs)

        # Mock delete_documents_by_ids to track what gets deleted
        deleted_ids = []
        async def mock_delete(ids):
            deleted_ids.extend(ids)
            return ids
        store.vector_db.delete_documents_by_ids = mock_delete

        malicious_uri = "' or True or '"
        await store.delete_document(malicious_uri)

        assert len(deleted_ids) == 0, (
            f"INJECTION SUCCEEDED: delete with tautology would delete "
            f"{len(deleted_ids)} docs instead of 0"
        )

    @pytest.mark.asyncio
    async def test_search_document_filter_injection(self, sample_docs):
        """
        ATTACK: Malicious URI in search_document's doc_filter.
        search_document builds: f"document_uri == '{document_uri}'"
        """
        store = _make_store_with_docs(sample_docs)

        # Mock the search to capture the filter
        captured_filters = []

        async def capture_search(query, limit=10, threshold=0.5, filter=""):
            captured_filters.append(filter)
            return []

        store.search_documents = capture_search

        malicious_uri = "' or True or '"
        await store.search_document(malicious_uri, "test query")

        # The filter should be safe (not contain raw injected content)
        if captured_filters:
            filter_str = captured_filters[0]
            # A safe filter should NOT evaluate to True for arbitrary metadata
            from python.helpers.vector_db import get_comparator
            comparator = get_comparator(filter_str)
            dummy_metadata = {"document_uri": "file:///other/doc.pdf"}
            assert not comparator(dummy_metadata), (
                f"INJECTION SUCCEEDED: filter '{filter_str}' matches arbitrary docs"
            )


# ═══════════════════════════════════════════════════════════════════════════
# TEST CLASS: document_qa filter injection via multiple URIs
# ═══════════════════════════════════════════════════════════════════════════

class TestDocumentQAFilterInjection:
    """
    Verify that malicious URIs in document_qa's multi-URI filter
    (built via build_or_filter) cannot break the expression.
    """

    def test_multi_uri_filter_build_safety(self):
        """
        document_qa now uses build_or_filter() which escapes values.
        A malicious URI must NOT inject extra OR conditions.
        """
        from python.helpers.vector_db import get_comparator, build_or_filter

        malicious_uris = [
            "file:///legit.pdf",
            "' or True or '",  # injection attempt
        ]

        # Use the NEW safe filter builder
        doc_filter = build_or_filter("document_uri", malicious_uris)

        # Test against an unrelated document
        comparator = get_comparator(doc_filter)
        unrelated = {"document_uri": "file:///totally_different.pdf"}

        result = comparator(unrelated)
        assert not result, (
            f"INJECTION SUCCEEDED: multi-URI filter matched unrelated document. "
            f"Filter: {doc_filter}"
        )

    def test_multi_uri_filter_legitimate_match(self):
        """
        Regression: build_or_filter must still match one of the listed URIs.
        """
        from python.helpers.vector_db import get_comparator, build_or_filter

        uris = ["file:///data/report.pdf", "file:///data/invoice.pdf"]
        doc_filter = build_or_filter("document_uri", uris)
        comparator = get_comparator(doc_filter)

        # Should match
        assert comparator({"document_uri": "file:///data/report.pdf"})
        assert comparator({"document_uri": "file:///data/invoice.pdf"})

        # Should NOT match
        assert not comparator({"document_uri": "file:///data/other.pdf"})

    def test_old_vulnerable_pattern_would_still_inject(self):
        """
        Canary test: prove that the OLD vulnerable pattern (raw f-string)
        is indeed exploitable.  This documents WHY the fix was necessary.
        """
        from python.helpers.vector_db import get_comparator

        malicious_uris = [
            "file:///legit.pdf",
            "' or True or '",
        ]

        # OLD vulnerable construction (DO NOT USE in production)
        old_filter = " or ".join(
            [f"document_uri == '{uri}'" for uri in malicious_uris]
        )

        comparator = get_comparator(old_filter)
        unrelated = {"document_uri": "file:///totally_different.pdf"}

        # This SHOULD be True (injection succeeds with old pattern)
        result = comparator(unrelated)
        assert result is True, (
            "Expected the OLD vulnerable pattern to be exploitable. "
            "If this fails, simpleeval's behavior may have changed."
        )
