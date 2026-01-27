"""
Tests for Legal Sources — Models, Chunking, Citations

Validates:
- doc_id stability (same input => same doc_id)
- chunk_id stability
- Provenance completeness
- Citation formatting
- Chunking determinism
"""

import hashlib
import pytest
from datetime import datetime

from python.legal_sources.models import (
    LegalSource,
    LegalDoc,
    LegalChunk,
    Provenance,
    DocumentType,
    Jurisdiction,
    IngestionResult,
)
from python.legal_sources.chunking import LegalChunker, ChunkerConfig, ChunkingStrategy
from python.helpers.legal_citations import (
    format_citation,
    build_audit_trail,
    validate_provenance,
    format_cass_citation,
    format_code_citation,
    CitationFormat,
)


class TestLegalDocIdStability:
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
            title="Article 1134",
            citation="Art. 1134 C. civ.",
        )
        
        assert doc1.doc_id == doc2.doc_id
    
    def test_different_origin_different_doc_id(self):
        """Différents origin_id => différents doc_id."""
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
            origin_id="LEGIARTI000006070722",
            document_type=DocumentType.CODE,
            jurisdiction=Jurisdiction.LEGISLATIVE,
            title="Article 1135",
            citation="Art. 1135 C. civ.",
        )
        
        assert doc1.doc_id != doc2.doc_id
    
    def test_doc_id_is_hex(self):
        """doc_id doit être un hash hex."""
        doc = LegalDoc(
            doc_id="",
            source=LegalSource.CASS,
            origin_id="JURITEXT000007024188",
            document_type=DocumentType.ARRET,
            jurisdiction=Jurisdiction.JUDICIAL_CIVIL,
            title="Test",
            citation="Test",
        )
        
        # Doit être hex (pas UUID)
        assert all(c in "0123456789abcdef" for c in doc.doc_id)
        assert len(doc.doc_id) == 16


class TestLegalChunkIdStability:
    """Tests pour la stabilité des chunk_id."""
    
    def test_same_doc_same_index_same_chunk_id(self):
        """Même doc_id + index => même chunk_id."""
        provenance = Provenance(
            source=LegalSource.LEGI,
            source_name="DILA",
            origin_id="TEST",
        )
        
        chunk1 = LegalChunk(
            chunk_id="",
            doc_id="abc123",
            chunk_index=0,
            text="Test content",
            source=LegalSource.LEGI,
            document_type=DocumentType.CODE,
            citation="Art. 1 C. civ.",
            pinpoint="al. 1",
            provenance=provenance,
        )
        
        chunk2 = LegalChunk(
            chunk_id="",
            doc_id="abc123",
            chunk_index=0,
            text="Different content",  # Contenu différent
            source=LegalSource.LEGI,
            document_type=DocumentType.CODE,
            citation="Art. 1 C. civ.",
            pinpoint="al. 1",
            provenance=provenance,
        )
        
        # chunk_id basé sur doc_id + index, pas sur contenu
        assert chunk1.chunk_id == chunk2.chunk_id
    
    def test_different_index_different_chunk_id(self):
        """Différents index => différents chunk_id."""
        provenance = Provenance(
            source=LegalSource.LEGI,
            source_name="DILA",
            origin_id="TEST",
        )
        
        chunk1 = LegalChunk(
            chunk_id="",
            doc_id="abc123",
            chunk_index=0,
            text="Content 1",
            source=LegalSource.LEGI,
            document_type=DocumentType.CODE,
            citation="Art. 1 C. civ.",
            pinpoint="al. 1",
            provenance=provenance,
        )
        
        chunk2 = LegalChunk(
            chunk_id="",
            doc_id="abc123",
            chunk_index=1,
            text="Content 2",
            source=LegalSource.LEGI,
            document_type=DocumentType.CODE,
            citation="Art. 1 C. civ.",
            pinpoint="al. 2",
            provenance=provenance,
        )
        
        assert chunk1.chunk_id != chunk2.chunk_id


class TestProvenanceCompleteness:
    """Tests pour la complétude de la provenance."""
    
    def test_provenance_required_fields(self):
        """Provenance doit avoir les champs obligatoires."""
        prov = Provenance(
            source=LegalSource.CASS,
            source_name="Cour de cassation",
            origin_id="JURITEXT000007024188",
            origin_url="https://www.courdecassation.fr/decision/123",
            license="Licence Ouverte 2.0",
        )
        
        assert prov.source == LegalSource.CASS
        assert prov.origin_id
        assert prov.license
        assert prov.retrieved_at  # Auto-généré
    
    def test_provenance_serialization(self):
        """Provenance se sérialise et désérialise correctement."""
        prov = Provenance(
            source=LegalSource.LEGI,
            source_name="DILA",
            origin_id="LEGIARTI000006070721",
            origin_url="https://legifrance.gouv.fr/...",
            content_hash="abc123",
            pinpoint="al. 2",
            chunk_index=3,
        )
        
        data = prov.to_dict()
        restored = Provenance.from_dict(data)
        
        assert restored.source == prov.source
        assert restored.origin_id == prov.origin_id
        assert restored.pinpoint == prov.pinpoint
        assert restored.chunk_index == prov.chunk_index
    
    def test_validate_provenance_complete(self):
        """Validation passe avec provenance complète."""
        chunk_meta = {
            "source": "legi",
            "citation": "Art. 1134 C. civ.",
            "provenance": {
                "origin_id": "LEGIARTI000006070721",
                "retrieved_at": "2026-01-25T12:00:00",
                "license": "Licence Ouverte 2.0",
                "origin_url": "https://legifrance.gouv.fr/...",
                "content_hash": "abc123",
            },
        }
        
        result = validate_provenance(chunk_meta)
        assert result["valid"] is True
        assert len(result["missing"]) == 0
    
    def test_validate_provenance_incomplete(self):
        """Validation échoue avec provenance incomplète."""
        chunk_meta = {
            "source": "legi",
            # Manque citation
            "provenance": {
                "origin_id": "LEGIARTI000006070721",
                # Manque retrieved_at, license
            },
        }
        
        result = validate_provenance(chunk_meta)
        assert result["valid"] is False
        assert "citation" in result["missing"]


class TestChunkingDeterminism:
    """Tests pour le déterminisme du chunking."""
    
    def test_same_doc_same_chunks(self):
        """Même document => mêmes chunks."""
        doc = LegalDoc(
            doc_id="test123",
            source=LegalSource.LEGI,
            origin_id="LEGIARTI000006070721",
            document_type=DocumentType.CODE,
            jurisdiction=Jurisdiction.LEGISLATIVE,
            title="Article 1134",
            citation="Art. 1134 C. civ.",
            text="Les conventions légalement formées tiennent lieu de loi à ceux qui les ont faites.\n\nElles ne peuvent être révoquées que de leur consentement mutuel, ou pour les causes que la loi autorise.\n\nElles doivent être exécutées de bonne foi.",
            provenance=Provenance(
                source=LegalSource.LEGI,
                source_name="DILA",
                origin_id="LEGIARTI000006070721",
            ),
        )
        
        chunker = LegalChunker(ChunkerConfig(
            strategy=ChunkingStrategy.PARAGRAPH,
            chunk_size=500,
        ))
        
        chunks1 = list(chunker.chunk_document(doc))
        chunks2 = list(chunker.chunk_document(doc))
        
        assert len(chunks1) == len(chunks2)
        for c1, c2 in zip(chunks1, chunks2):
            assert c1.chunk_id == c2.chunk_id
            assert c1.text == c2.text
    
    def test_chunking_preserves_provenance(self):
        """Chaque chunk a une provenance."""
        doc = LegalDoc(
            doc_id="test123",
            source=LegalSource.CASS,
            origin_id="JURITEXT000007024188",
            document_type=DocumentType.ARRET,
            jurisdiction=Jurisdiction.JUDICIAL_CIVIL,
            title="Arrêt test",
            citation="Cass. civ. 1re, 15 janv. 2024",
            text="Attendu que le demandeur fait grief...\n\nMais attendu que la cour d'appel a retenu...\n\nPar ces motifs, rejette.",
            provenance=Provenance(
                source=LegalSource.CASS,
                source_name="Cour de cassation",
                origin_id="JURITEXT000007024188",
                origin_url="https://courdecassation.fr/...",
            ),
        )
        
        chunker = LegalChunker()
        chunks = list(chunker.chunk_document(doc))
        
        assert len(chunks) > 0
        for chunk in chunks:
            assert chunk.provenance is not None
            assert chunk.provenance.origin_id == doc.origin_id
            assert chunk.provenance.source == LegalSource.CASS


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
        assert "15 janv. 2024" in citation
        assert "22-18.456" in citation
    
    def test_format_code_citation(self):
        """Citation article de code."""
        citation = format_code_citation(
            code_name="Code civil",
            article_num="1134",
        )
        
        assert citation == "Art. 1134 C. civ."
    
    def test_format_code_citation_with_alinea(self):
        """Citation avec alinéa."""
        citation = format_code_citation(
            code_name="Code civil",
            article_num="1134",
            alinea=2,
        )
        
        assert citation == "Art. 1134, al. 2 C. civ."
    
    def test_format_citation_court(self):
        """Format court."""
        chunk_meta = {
            "citation": "Art. 1134 C. civ.",
            "pinpoint": "al. 2",
        }
        
        result = format_citation(chunk_meta, format=CitationFormat.COURT)
        assert "Art. 1134 C. civ." in result
        assert "al. 2" in result
    
    def test_format_citation_full(self):
        """Format complet."""
        chunk_meta = {
            "citation": "Art. 1134 C. civ.",
            "provenance": {
                "origin_id": "LEGIARTI000006070721",
                "retrieved_at": "2024-01-25T12:00:00",
            },
        }
        
        result = format_citation(chunk_meta, format=CitationFormat.FULL)
        assert "Art. 1134 C. civ." in result
        assert "LEGIARTI000006070721" in result


class TestAuditTrail:
    """Tests pour l'audit trail."""
    
    def test_build_audit_trail(self):
        """Construction d'un audit trail."""
        chunks = [
            {
                "source": "legi",
                "citation": "Art. 1134 C. civ.",
                "provenance": {
                    "origin_id": "LEGIARTI000006070721",
                    "retrieved_at": "2024-01-25T12:00:00",
                    "license": "Licence Ouverte 2.0",
                    "content_hash": "abc123",
                },
            },
            {
                "source": "cass",
                "citation": "Cass. civ. 1re, 15 janv. 2024",
                "provenance": {
                    "origin_id": "JURITEXT000007024188",
                    "retrieved_at": "2024-01-25T12:00:00",
                    "license": "Licence Ouverte 2.0",
                    "content_hash": "def456",
                },
            },
        ]
        
        audit = build_audit_trail(chunks)
        
        assert "legi" in audit["sources"]
        assert "cass" in audit["sources"]
        assert len(audit["citations"]) == 2
        assert len(audit["provenance"]) == 2
        assert len(audit["checksums"]) == 2
        assert audit["total_chunks"] == 2
    
    def test_audit_trail_empty(self):
        """Audit trail avec liste vide."""
        audit = build_audit_trail([])
        
        assert audit["sources"] == []
        assert "warning" in audit


class TestIngestionResult:
    """Tests pour IngestionResult."""
    
    def test_success_when_no_errors(self):
        """Success = True si pas d'erreurs."""
        result = IngestionResult(
            source=LegalSource.LEGI,
            started_at=datetime.utcnow(),
            docs_fetched=100,
            docs_parsed=100,
            docs_indexed=100,
            docs_failed=0,
        )
        
        assert result.success is True
    
    def test_failure_when_errors(self):
        """Success = False si erreurs."""
        result = IngestionResult(
            source=LegalSource.LEGI,
            started_at=datetime.utcnow(),
            docs_fetched=100,
            docs_parsed=95,
            docs_indexed=90,
            docs_failed=5,
        )
        
        assert result.success is False
    
    def test_duration_calculation(self):
        """Calcul de la durée."""
        start = datetime(2024, 1, 25, 12, 0, 0)
        end = datetime(2024, 1, 25, 12, 5, 30)
        
        result = IngestionResult(
            source=LegalSource.CASS,
            started_at=start,
            completed_at=end,
        )
        
        assert result.duration_seconds == 330.0  # 5 min 30 sec


class TestLegalDocSerialization:
    """Tests pour la sérialisation des documents."""
    
    def test_to_dict_and_back(self):
        """Document se sérialise et désérialise."""
        doc = LegalDoc(
            doc_id="test123",
            source=LegalSource.LEGI,
            origin_id="LEGIARTI000006070721",
            document_type=DocumentType.CODE,
            jurisdiction=Jurisdiction.LEGISLATIVE,
            title="Article 1134",
            citation="Art. 1134 C. civ.",
            date=datetime(2024, 1, 1),
            text="Les conventions légalement formées...",
            code_name="Code civil",
            article_number="1134",
            provenance=Provenance(
                source=LegalSource.LEGI,
                source_name="DILA",
                origin_id="LEGIARTI000006070721",
            ),
        )
        
        data = doc.to_dict()
        restored = LegalDoc.from_dict(data)
        
        assert restored.doc_id == doc.doc_id
        assert restored.source == doc.source
        assert restored.origin_id == doc.origin_id
        assert restored.citation == doc.citation
        assert restored.code_name == doc.code_name
        assert restored.provenance.origin_id == doc.provenance.origin_id
