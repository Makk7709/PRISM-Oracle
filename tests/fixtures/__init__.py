"""Test fixtures for Korev Evidence legal pipeline."""

from .legal_corpus import (
    CORPUS,
    CODE_CIVIL_ARTICLES,
    CODE_TRAVAIL_ARTICLES,
    JURISPRUDENCE_CASS,
    create_test_index,
    get_corpus_size,
    get_corpus_citations,
)

from .mock_llm import (
    create_mock_llm,
    create_consensus_mock,
    MockLLMResponses,
    assert_firac_structure,
    assert_no_unsupported_claims,
)

__all__ = [
    # Corpus
    "CORPUS",
    "CODE_CIVIL_ARTICLES",
    "CODE_TRAVAIL_ARTICLES",
    "JURISPRUDENCE_CASS",
    "create_test_index",
    "get_corpus_size",
    "get_corpus_citations",
    # Mock LLM
    "create_mock_llm",
    "create_consensus_mock",
    "MockLLMResponses",
    "assert_firac_structure",
    "assert_no_unsupported_claims",
]
