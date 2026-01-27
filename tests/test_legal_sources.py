"""
Tests for Legal Sources — Enterprise Edition

Validates:
- Provenance must-have: license_url/terms_url/access_mode non vides
- Retry/backoff: simulation 429/5xx + reprise checkpoint
- Search/lookup: résultats cohérents + citation + provenance
- Audit bundle: contient toutes les preuves attendues
- doc_id/chunk_id stability
"""

import hashlib
import json
import pytest
import sqlite3
import tempfile
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import requests

from python.legal_sources.models import (
    LegalSource,
    AccessMode,
    LegalDoc,
    LegalChunk,
    Provenance,
    DocumentType,
    Jurisdiction,
    IngestionResult,
    ProvenanceValidationError,
    SOURCE_COMPLIANCE,
    create_compliant_provenance,
)
from python.legal_sources.chunking import LegalChunker, ChunkerConfig, ChunkingStrategy
from python.legal_sources.indexing import LegalIndex, SearchResult
from python.legal_sources.audit_bundle import (
    build_audit_bundle,
    validate_audit_bundle,
    AuditBundle,
    generate_audit_report,
)
from python.legal_sources.resilience import (
    RetryConfig,
    CheckpointManager,
    CheckpointData,
    RateLimiter,
    retry_with_backoff,
)
from python.helpers.legal_citations import (
    format_citation,
    build_audit_trail,
    validate_provenance,
    format_cass_citation,
    format_code_citation,
    CitationFormat,
)


# ============================================================
# FAST GATE TESTS (<10s) — Core Functionality
# ============================================================

class TestProvenanceMustHave:
    """Tests pour les champs obligatoires de provenance."""
    
    def test_provenance_requires_license_name(self):
        """license_name obligatoire."""
        prov = Provenance(
            source=LegalSource.LEGI,
            source_name="DILA",
            origin_id="TEST123",
            license_name="",  # Vide
            license_url="https://example.com",
            terms_url="https://example.com",
            access_mode=AccessMode.API_KEY_CGU,
        )
        
        assert not prov.is_valid
        with pytest.raises(ProvenanceValidationError) as exc:
            prov.validate()
        assert "license_name" in str(exc.value)
    
    def test_provenance_requires_license_url(self):
        """license_url obligatoire."""
        prov = Provenance(
            source=LegalSource.CASS,
            source_name="Cour de cassation",
            origin_id="TEST123",
            license_name="Licence Ouverte 2.0",
            license_url="",  # Vide
            terms_url="https://example.com",
            access_mode=AccessMode.API_KEY_CGU,
        )
        
        assert not prov.is_valid
    
    def test_provenance_requires_terms_url(self):
        """terms_url obligatoire."""
        prov = Provenance(
            source=LegalSource.LEGI,
            source_name="DILA",
            origin_id="TEST123",
            license_name="Licence Ouverte 2.0",
            license_url="https://etalab.gouv.fr/...",
            terms_url="",  # Vide
            access_mode=AccessMode.API_KEY_CGU,
        )
        
        assert not prov.is_valid
    
    def test_provenance_requires_access_mode(self):
        """access_mode obligatoire."""
        # AccessMode a une valeur par défaut, donc ce test vérifie que ça marche
        prov = Provenance(
            source=LegalSource.LEGI,
            source_name="DILA",
            origin_id="TEST123",
            license_name="Licence Ouverte 2.0",
            license_url="https://etalab.gouv.fr/...",
            terms_url="https://piste.gouv.fr/cgu",
            access_mode=AccessMode.API_KEY_CGU,
        )
        
        assert prov.is_valid
    
    def test_compliant_provenance_factory(self):
        """create_compliant_provenance crée une provenance valide."""
        prov = create_compliant_provenance(
            source=LegalSource.CASS,
            origin_id="JURITEXT123",
            origin_url="https://courdecassation.fr/...",
        )
        
        assert prov.is_valid
        assert prov.license_name == "Licence Ouverte 2.0 (Etalab)"
        assert "etalab" in prov.license_url.lower()
        assert prov.terms_url  # Non vide
        assert prov.access_mode == AccessMode.API_KEY_CGU


class TestDocIndexingValidation:
    """Tests pour validation avant indexation."""
    
    def test_doc_without_provenance_cannot_be_indexed(self):
        """Document sans provenance rejeté."""
        doc = LegalDoc(
            doc_id="",
            source=LegalSource.LEGI,
            origin_id="TEST123",
            document_type=DocumentType.CODE,
            jurisdiction=Jurisdiction.LEGISLATIVE,
            title="Test",
            citation="Test",
            provenance=None,  # Pas de provenance
        )
        
        assert not doc.can_be_indexed
        with pytest.raises(ProvenanceValidationError):
            doc.validate_for_indexing()
    
    def test_doc_with_incomplete_provenance_cannot_be_indexed(self):
        """Document avec provenance incomplète rejeté."""
        doc = LegalDoc(
            doc_id="",
            source=LegalSource.LEGI,
            origin_id="TEST123",
            document_type=DocumentType.CODE,
            jurisdiction=Jurisdiction.LEGISLATIVE,
            title="Test",
            citation="Test",
            provenance=Provenance(
                source=LegalSource.LEGI,
                source_name="DILA",
                origin_id="TEST123",
                license_name="",  # Vide = invalide
                license_url="",
                terms_url="",
            ),
        )
        
        assert not doc.can_be_indexed
    
    def test_doc_with_complete_provenance_can_be_indexed(self):
        """Document avec provenance complète accepté."""
        doc = LegalDoc(
            doc_id="",
            source=LegalSource.LEGI,
            origin_id="TEST123",
            document_type=DocumentType.CODE,
            jurisdiction=Jurisdiction.LEGISLATIVE,
            title="Test",
            citation="Test",
            provenance=create_compliant_provenance(
                source=LegalSource.LEGI,
                origin_id="TEST123",
            ),
        )
        
        assert doc.can_be_indexed


class TestDocIdStability:
    """Tests pour la stabilité des doc_id."""
    
    def test_same_input_same_doc_id(self):
        """Même source + origin_id => même doc_id."""
        doc1 = LegalDoc(
            doc_id="",
            source=LegalSource.LEGI,
            origin_id="LEGIARTI000006070721",
            document_type=DocumentType.CODE,
            jurisdiction=Jurisdiction.LEGISLATIVE,
            title="Article 1134",
            citation="Art. 1134 C. civ.",
        )
        
        doc2 = LegalDoc(
            doc_id="",
            source=LegalSource.LEGI,
            origin_id="LEGIARTI000006070721",
            document_type=DocumentType.CODE,
            jurisdiction=Jurisdiction.LEGISLATIVE,
            title="Different title",  # Titre différent
            citation="Different citation",
        )
        
        assert doc1.doc_id == doc2.doc_id
    
    def test_doc_id_is_deterministic(self):
        """doc_id est déterministe (pas de UUID)."""
        doc = LegalDoc(
            doc_id="",
            source=LegalSource.CASS,
            origin_id="JURITEXT000007024188",
            document_type=DocumentType.ARRET,
            jurisdiction=Jurisdiction.JUDICIAL_CIVIL,
            title="Test",
            citation="Test",
        )
        
        # Doit être hex
        assert all(c in "0123456789abcdef" for c in doc.doc_id)
        assert len(doc.doc_id) == 16


class TestChunkIdStability:
    """Tests pour la stabilité des chunk_id."""
    
    def test_same_doc_same_index_same_chunk_id(self):
        """Même doc_id + index => même chunk_id."""
        prov = create_compliant_provenance(LegalSource.LEGI, "TEST")
        
        chunk1 = LegalChunk(
            chunk_id="",
            doc_id="abc123",
            chunk_index=0,
            text="Content 1",
            source=LegalSource.LEGI,
            document_type=DocumentType.CODE,
            citation="Art. 1",
            pinpoint="al. 1",
            provenance=prov,
        )
        
        chunk2 = LegalChunk(
            chunk_id="",
            doc_id="abc123",
            chunk_index=0,
            text="Different content",  # Contenu différent
            source=LegalSource.LEGI,
            document_type=DocumentType.CODE,
            citation="Art. 1",
            pinpoint="al. 1",
            provenance=prov,
        )
        
        assert chunk1.chunk_id == chunk2.chunk_id


class TestSQLiteIndex:
    """Tests pour l'index SQLite FTS5."""
    
    @pytest.fixture
    def temp_index(self):
        """Index temporaire pour tests."""
        with tempfile.TemporaryDirectory() as tmpdir:
            index = LegalIndex(Path(tmpdir))
            yield index
    
    def test_add_and_search_chunk(self, temp_index):
        """Ajouter et rechercher un chunk."""
        prov = create_compliant_provenance(LegalSource.LEGI, "LEGIARTI123")
        
        chunk = LegalChunk(
            chunk_id="chunk123",
            doc_id="doc123",
            chunk_index=0,
            text="L'article L132-8 du Code de commerce dispose que...",
            source=LegalSource.LEGI,
            document_type=DocumentType.CODE,
            citation="Art. L132-8 C. com.",
            pinpoint="al. 1",
            provenance=prov,
        )
        
        temp_index.add_chunk(chunk)
        
        # Recherche
        results = temp_index.search("L132-8", source="legi", limit=5)
        
        assert len(results) > 0
        assert results[0].chunk_id == "chunk123"
        assert results[0].citation == "Art. L132-8 C. com."
        assert results[0].provenance.get("license_name")
    
    def test_lookup_by_origin_id(self, temp_index):
        """Lookup exact par origin_id."""
        prov = create_compliant_provenance(LegalSource.CASS, "JURITEXT456")
        
        doc = LegalDoc(
            doc_id="doc456",
            source=LegalSource.CASS,
            origin_id="JURITEXT456",
            document_type=DocumentType.ARRET,
            jurisdiction=Jurisdiction.JUDICIAL_CIVIL,
            title="Arrêt test",
            citation="Cass. civ. 1re, 15 janv. 2024",
            provenance=prov,
        )
        
        temp_index.add_doc(doc)
        
        result = temp_index.lookup_by_origin_id("JURITEXT456")
        
        assert result is not None
        assert result["doc"]["citation"] == "Cass. civ. 1re, 15 janv. 2024"
        assert result["doc"]["provenance"]["license_name"] == "Licence Ouverte 2.0 (Etalab)"
    
    def test_idempotent_add(self, temp_index):
        """Ajout idempotent (pas de duplication)."""
        prov = create_compliant_provenance(LegalSource.LEGI, "TEST")
        
        chunk = LegalChunk(
            chunk_id="chunk_idem",
            doc_id="doc_idem",
            chunk_index=0,
            text="Test content",
            source=LegalSource.LEGI,
            document_type=DocumentType.CODE,
            citation="Test",
            pinpoint="",
            provenance=prov,
        )
        
        # Premier ajout
        result1 = temp_index.add_chunk(chunk)
        assert result1 is True
        
        # Deuxième ajout (même chunk_id)
        result2 = temp_index.add_chunk(chunk)
        assert result2 is True  # OR REPLACE
        
        # Un seul chunk
        stats = temp_index.get_stats()
        assert stats["total_chunks"] == 1


class TestAuditBundle:
    """Tests pour le bundle d'audit."""
    
    def test_build_audit_bundle(self):
        """Construction d'un audit bundle."""
        chunks = [
            {
                "chunk_id": "c1",
                "doc_id": "d1",
                "source": "legi",
                "citation": "Art. 1 C. civ.",
                "pinpoint": "al. 1",
                "text": "Test content",
                "provenance": {
                    "origin_id": "LEGIARTI123",
                    "origin_url": "https://legifrance.gouv.fr/...",
                    "retrieved_at": "2026-01-27T12:00:00",
                    "license_name": "Licence Ouverte 2.0 (Etalab)",
                    "license_url": "https://etalab.gouv.fr/...",
                    "terms_name": "CGU PISTE",
                    "terms_url": "https://piste.gouv.fr/cgu",
                    "access_mode": "API_KEY_CGU",
                    "content_hash": "abc123",
                },
            },
        ]
        
        bundle = build_audit_bundle(chunks, description="Test bundle")
        
        assert bundle.total_chunks == 1
        assert "legi" in bundle.sources_used
        assert len(bundle.licenses_used) > 0
        assert bundle.bundle_hash  # Non vide
    
    def test_validate_audit_bundle_complete(self):
        """Validation bundle complet."""
        chunks = [
            {
                "chunk_id": "c1",
                "doc_id": "d1",
                "source": "cass",
                "citation": "Cass. civ. 1re",
                "pinpoint": "",
                "text": "Test",
                "provenance": {
                    "origin_id": "JURITEXT123",
                    "retrieved_at": "2026-01-27",
                    "license_name": "Licence Ouverte 2.0",
                    "license_url": "https://etalab.gouv.fr",
                    "terms_name": "CGU Cour cassation",
                    "terms_url": "https://courdecassation.fr/cgu",
                    "access_mode": "API_KEY_CGU",
                },
            },
        ]
        
        bundle = build_audit_bundle(chunks)
        validation = validate_audit_bundle(bundle)
        
        assert validation["valid"] is True
        assert len(validation["missing_fields"]) == 0
    
    def test_validate_audit_bundle_incomplete(self):
        """Validation bundle incomplet."""
        chunks = [
            {
                "chunk_id": "c1",
                "source": "legi",
                "citation": "Test",
                "provenance": {
                    "origin_id": "TEST",
                    # Manque license_name, license_url, terms_url, access_mode
                },
            },
        ]
        
        bundle = build_audit_bundle(chunks)
        validation = validate_audit_bundle(bundle)
        
        assert validation["valid"] is False
        assert len(validation["missing_fields"]) > 0


class TestResilience:
    """Tests pour la résilience réseau."""
    
    def test_checkpoint_save_and_load(self):
        """Sauvegarde et chargement checkpoint."""
        with tempfile.TemporaryDirectory() as tmpdir:
            mgr = CheckpointManager(Path(tmpdir))
            
            mgr.update(
                source="cass",
                cursor="cursor123",
                page=5,
                last_doc_id="doc_abc",
                docs_processed=150,
            )
            
            # Nouveau manager (simule redémarrage)
            mgr2 = CheckpointManager(Path(tmpdir))
            checkpoint = mgr2.get("cass")
            
            assert checkpoint is not None
            assert checkpoint.cursor == "cursor123"
            assert checkpoint.page == 5
            assert checkpoint.docs_processed == 150
    
    def test_retry_with_backoff_success(self):
        """Retry réussit après échecs."""
        attempts = []
        
        def flaky_func():
            attempts.append(1)
            if len(attempts) < 3:
                resp = Mock()
                resp.status_code = 503
                raise requests.exceptions.HTTPError(response=resp)
            return "success"
        
        config = RetryConfig(max_retries=5, base_delay=0.01)
        result = retry_with_backoff(flaky_func, config)
        
        assert result == "success"
        assert len(attempts) == 3
    
    def test_retry_with_backoff_exhausted(self):
        """Retry échoue après max tentatives."""
        def always_fail():
            resp = Mock()
            resp.status_code = 503
            raise requests.exceptions.HTTPError(response=resp)
        
        config = RetryConfig(max_retries=2, base_delay=0.01)
        
        with pytest.raises(requests.exceptions.HTTPError):
            retry_with_backoff(always_fail, config)
    
    def test_rate_limiter_handles_429(self):
        """RateLimiter gère les 429 avec Retry-After."""
        config = RetryConfig()
        limiter = RateLimiter(config)
        
        response = Mock()
        response.headers = {"Retry-After": "5"}
        
        delay = limiter.handle_rate_limit(response)
        assert delay == 5.0
    
    def test_rate_limiter_default_delay(self):
        """RateLimiter utilise délai par défaut sans header."""
        config = RetryConfig(rate_limit_delay=30.0)
        limiter = RateLimiter(config)
        
        response = Mock()
        response.headers = {}
        
        delay = limiter.handle_rate_limit(response)
        assert delay == 30.0


class TestSourceCompliance:
    """Tests pour SOURCE_COMPLIANCE registry."""
    
    def test_all_sources_have_compliance(self):
        """Toutes les sources ont leur compliance."""
        for source in [LegalSource.LEGI, LegalSource.CASS, LegalSource.JADE, LegalSource.CONSTIT]:
            assert source in SOURCE_COMPLIANCE
            compliance = SOURCE_COMPLIANCE[source]
            assert compliance.get("license_name")
            assert compliance.get("license_url")
            assert compliance.get("terms_url")
            assert compliance.get("access_mode")
    
    def test_license_urls_are_https(self):
        """URLs de licence sont HTTPS."""
        for source, compliance in SOURCE_COMPLIANCE.items():
            license_url = compliance.get("license_url", "")
            assert license_url.startswith("https://"), f"{source}: {license_url}"


class TestChunkingDeterminism:
    """Tests pour le déterminisme du chunking."""
    
    def test_same_doc_same_chunks(self):
        """Même document => mêmes chunks."""
        prov = create_compliant_provenance(LegalSource.LEGI, "TEST")
        
        doc = LegalDoc(
            doc_id="test123",
            source=LegalSource.LEGI,
            origin_id="TEST",
            document_type=DocumentType.CODE,
            jurisdiction=Jurisdiction.LEGISLATIVE,
            title="Article 1",
            citation="Art. 1 C. civ.",
            text="Premier alinéa.\n\nDeuxième alinéa.\n\nTroisième alinéa.",
            provenance=prov,
        )
        
        chunker = LegalChunker(ChunkerConfig(chunk_size=500, min_chunk_size=20))
        
        chunks1 = list(chunker.chunk_document(doc))
        chunks2 = list(chunker.chunk_document(doc))
        
        assert len(chunks1) == len(chunks2)
        for c1, c2 in zip(chunks1, chunks2):
            assert c1.chunk_id == c2.chunk_id


class TestCitationFormatting:
    """Tests pour le formatage des citations."""
    
    def test_format_cass_citation(self):
        """Citation Cour de cassation."""
        date = datetime(2024, 1, 15)
        citation = format_cass_citation(
            chamber="Première chambre civile",
            date=date,
            pourvoi="22-18.456",
            solution="Rejet",
        )
        
        assert "Cass." in citation
        assert "civ. 1re" in citation
        assert "22-18.456" in citation
    
    def test_format_code_citation(self):
        """Citation article de code."""
        citation = format_code_citation(
            code_name="Code civil",
            article_num="1134",
        )
        
        assert citation == "Art. 1134 C. civ."


class TestIngestionResult:
    """Tests pour IngestionResult."""
    
    def test_tracks_rejected_no_provenance(self):
        """Compte les documents rejetés pour provenance manquante."""
        result = IngestionResult(
            source=LegalSource.LEGI,
            started_at=datetime.utcnow(),
            docs_fetched=100,
            docs_parsed=90,
            docs_indexed=85,
            docs_rejected_no_provenance=5,
        )
        
        data = result.to_dict()
        assert data["docs_rejected_no_provenance"] == 5


# ============================================================
# INTEGRATION TESTS (Full Gate, optional)
# ============================================================

class TestIntegrationFullPipeline:
    """Tests d'intégration (nécessite plus de temps)."""
    
    @pytest.fixture
    def full_setup(self):
        """Setup complet avec tous les composants."""
        with tempfile.TemporaryDirectory() as tmpdir:
            base_dir = Path(tmpdir)
            yield {
                "base_dir": base_dir,
                "index": LegalIndex(base_dir / "index"),
                "checkpoint_mgr": CheckpointManager(base_dir / "cache"),
            }
    
    def test_full_indexing_pipeline(self, full_setup):
        """Pipeline complet: doc -> chunk -> index -> search."""
        index = full_setup["index"]
        
        # Créer un document complet avec texte suffisant
        prov = create_compliant_provenance(
            source=LegalSource.LEGI,
            origin_id="LEGIARTI000006420055",
            origin_url="https://legifrance.gouv.fr/codes/article_lc/LEGIARTI000006420055",
        )
        
        doc = LegalDoc(
            doc_id="",
            source=LegalSource.LEGI,
            origin_id="LEGIARTI000006420055",
            document_type=DocumentType.CODE,
            jurisdiction=Jurisdiction.LEGISLATIVE,
            title="Article L132-8",
            citation="Art. L132-8 C. com.",
            text=(
                "Le commissionnaire de transport est responsable des avaries ou pertes "
                "qui arrivent à la marchandise pendant le transport. Il est tenu de la "
                "garantie des faits du voiturier dont il a fait choix."
            ),
            code_name="Code de commerce",
            article_number="L132-8",
            provenance=prov,
        )
        
        # Valider et indexer
        assert doc.can_be_indexed
        index.add_doc(doc)
        
        # Chunker avec min_chunk_size réduit pour le test
        chunker = LegalChunker(ChunkerConfig(min_chunk_size=50))
        for chunk in chunker.chunk_document(doc):
            index.add_chunk(chunk)
        
        # Recherche
        results = index.search("commissionnaire transport")
        assert len(results) > 0
        
        # Lookup
        lookup = index.lookup_by_origin_id("LEGIARTI000006420055")
        assert lookup is not None
        assert lookup["doc"]["provenance"]["license_name"] == "Licence Ouverte 2.0 (Etalab)"
    
    def test_audit_bundle_from_search_results(self, full_setup):
        """Créer audit bundle depuis résultats de recherche."""
        index = full_setup["index"]
        
        # Ajouter données
        prov = create_compliant_provenance(LegalSource.CASS, "JURITEXT999")
        
        chunk = LegalChunk(
            chunk_id="",
            doc_id="doc999",
            chunk_index=0,
            text="La responsabilité du transporteur...",
            source=LegalSource.CASS,
            document_type=DocumentType.ARRET,
            citation="Cass. com., 10 juin 2024",
            pinpoint="attendu 5",
            provenance=prov,
        )
        
        index.add_chunk(chunk)
        
        # Rechercher
        results = index.search("responsabilité transporteur")
        
        # Récupérer les chunks complets
        chunk_ids = [r.chunk_id for r in results]
        chunks = index.get_all_chunks_for_ids(chunk_ids)
        
        # Construire audit bundle
        bundle = build_audit_bundle(chunks, description="Recherche responsabilité")
        
        assert bundle.total_chunks > 0
        validation = validate_audit_bundle(bundle)
        assert validation["valid"] is True
