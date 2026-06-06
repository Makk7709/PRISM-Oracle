"""
Legal Sources — Data Models

Schémas normalisés pour documents juridiques avec traçabilité complète.
Conformité audit: chaque champ licence/CGU est sourcé et vérifié.
"""

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

# Constantes (déduplication littéraux — python:S1192)
_TERMS_NAME_PISTE = "CGU PISTE"

# Constantes (déduplication littéraux — python:S1192)
_LICENSE_ETALAB = "Licence Ouverte 2.0 (Etalab)"
_URL_ETALAB_LICENSE = "https://www.etalab.gouv.fr/licence-ouverte-open-licence/"
_URL_PISTE_CGU = "https://piste.gouv.fr/cgu"


class LegalSource(str, Enum):
    """Sources de données juridiques supportées."""
    LEGI = "legi"           # Codes, lois, règlements consolidés
    JORF = "jorf"           # Journal Officiel
    CASS = "cass"           # Cour de cassation (Judilibre)
    JADE = "jade"           # Jurisprudence administrative
    CONSTIT = "constit"     # Conseil constitutionnel


class AccessMode(str, Enum):
    """Modes d'accès aux sources."""
    OPEN_DOWNLOAD = "OPEN_DOWNLOAD"       # Téléchargement libre
    API_KEY_CGU = "API_KEY_CGU"           # API avec clé + CGU
    REQUEST_TO_ADMIN = "REQUEST_TO_ADMIN" # Demande préalable admin
    PARTNERSHIP = "PARTNERSHIP"           # Partenariat requis


class Jurisdiction(str, Enum):
    """Types de juridictions."""
    LEGISLATIVE = "legislative"           # Lois, codes
    EXECUTIVE = "executive"               # Décrets, arrêtés
    JUDICIAL_CIVIL = "judicial_civil"     # Justice civile
    JUDICIAL_PENAL = "judicial_penal"     # Justice pénale
    JUDICIAL_SOCIAL = "judicial_social"   # Droit social
    JUDICIAL_COMMERCIAL = "judicial_commercial"  # Droit commercial
    ADMINISTRATIVE = "administrative"     # Conseil d'État, CAA, TA
    CONSTITUTIONAL = "constitutional"     # Conseil constitutionnel


class DocumentType(str, Enum):
    """Types de documents juridiques."""
    # Législatif
    CODE = "code"
    LOI = "loi"
    ORDONNANCE = "ordonnance"
    DECRET = "decret"
    ARRETE = "arrete"
    CIRCULAIRE = "circulaire"
    
    # Jurisprudence
    ARRET = "arret"
    DECISION = "decision"
    JUGEMENT = "jugement"
    AVIS = "avis"
    
    # Constitutionnel
    QPC = "qpc"
    DC = "dc"  # Contrôle de constitutionnalité
    
    # Autre
    OTHER = "other"


class ProvenanceValidationError(Exception):
    """Erreur de validation de provenance."""
    pass


@dataclass
class Provenance:
    """
    Traçabilité complète d'un document ou chunk.
    
    CONFORMITÉ AUDIT: Chaque élément indexé DOIT avoir une provenance complète
    avec licence et CGU vérifiées et sourcées.
    
    Champs obligatoires pour indexation:
    - source, source_name, origin_id
    - license_name, license_url
    - terms_url, access_mode
    - retrieved_at
    """
    # === Source (obligatoire) ===
    source: LegalSource
    source_name: str  # "DILA", "Cour de cassation", etc.
    
    # === Identifiants (obligatoire) ===
    origin_id: str  # ID d'origine (LEGITEXT..., JURITEXT..., etc.)
    origin_url: Optional[str] = None  # URL Légifrance/Judilibre si disponible
    
    # === Acquisition (obligatoire) ===
    retrieved_at: datetime = field(default_factory=datetime.utcnow)
    api_version: Optional[str] = None
    
    # === Licence (OBLIGATOIRE - sourcée et vérifiée) ===
    license_name: str = ""  # Ex: "Licence Ouverte 2.0 (Etalab)"
    license_url: str = ""   # Ex: "https://www.etalab.gouv.fr/licence-ouverte-open-licence/"
    
    # === CGU/Terms (OBLIGATOIRE - sourcées) ===
    terms_name: str = ""    # Ex: "CGU PISTE + CGU Cour de cassation"
    terms_url: str = ""     # Ex: "https://piste.gouv.fr/cgu"
    
    # === Mode d'accès (OBLIGATOIRE) ===
    access_mode: AccessMode = AccessMode.API_KEY_CGU
    
    # === Intégrité ===
    content_hash: Optional[str] = None  # SHA256 du contenu brut
    
    # === Pinpoint (pour chunks) ===
    pinpoint: Optional[str] = None  # Article, section, paragraphe
    chunk_index: Optional[int] = None
    
    def validate(self) -> None:
        """
        Valide que la provenance est complète pour indexation.
        
        Raises:
            ProvenanceValidationError: Si champs obligatoires manquants
        """
        missing = []
        
        if not self.source:
            missing.append("source")
        if not self.source_name:
            missing.append("source_name")
        if not self.origin_id:
            missing.append("origin_id")
        if not self.license_name:
            missing.append("license_name")
        if not self.license_url:
            missing.append("license_url")
        if not self.terms_url:
            missing.append("terms_url")
        if not self.access_mode:
            missing.append("access_mode")
        
        if missing:
            raise ProvenanceValidationError(
                f"Provenance incomplète pour indexation. Champs manquants: {missing}. "
                f"AUDIT: Aucun document ne peut être indexé sans provenance complète."
            )
    
    @property
    def is_valid(self) -> bool:
        """Vérifie si la provenance est valide pour indexation."""
        try:
            self.validate()
            return True
        except ProvenanceValidationError:
            return False
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "source": self.source.value,
            "source_name": self.source_name,
            "origin_id": self.origin_id,
            "origin_url": self.origin_url,
            "retrieved_at": self.retrieved_at.isoformat(),
            "api_version": self.api_version,
            "license_name": self.license_name,
            "license_url": self.license_url,
            "terms_name": self.terms_name,
            "terms_url": self.terms_url,
            "access_mode": self.access_mode.value,
            "content_hash": self.content_hash,
            "pinpoint": self.pinpoint,
            "chunk_index": self.chunk_index,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Provenance":
        access_mode = data.get("access_mode", "API_KEY_CGU")
        if isinstance(access_mode, str):
            access_mode = AccessMode(access_mode)
        
        return cls(
            source=LegalSource(data["source"]),
            source_name=data["source_name"],
            origin_id=data["origin_id"],
            origin_url=data.get("origin_url"),
            retrieved_at=datetime.fromisoformat(data["retrieved_at"]),
            api_version=data.get("api_version"),
            license_name=data.get("license_name", ""),
            license_url=data.get("license_url", ""),
            terms_name=data.get("terms_name", ""),
            terms_url=data.get("terms_url", ""),
            access_mode=access_mode,
            content_hash=data.get("content_hash"),
            pinpoint=data.get("pinpoint"),
            chunk_index=data.get("chunk_index"),
        )


# === Source Compliance Registry ===
# Données vérifiées et sourcées pour chaque source

SOURCE_COMPLIANCE = {
    LegalSource.LEGI: {
        "source_name": "DILA (Direction de l'Information Légale et Administrative)",
        "license_name": _LICENSE_ETALAB,
        "license_url": _URL_ETALAB_LICENSE,
        "terms_name": _TERMS_NAME_PISTE,
        "terms_url": _URL_PISTE_CGU,
        "access_mode": AccessMode.API_KEY_CGU,
    },
    LegalSource.JORF: {
        "source_name": "DILA (Direction de l'Information Légale et Administrative)",
        "license_name": _LICENSE_ETALAB,
        "license_url": _URL_ETALAB_LICENSE,
        "terms_name": _TERMS_NAME_PISTE,
        "terms_url": _URL_PISTE_CGU,
        "access_mode": AccessMode.API_KEY_CGU,
    },
    LegalSource.CASS: {
        "source_name": "Cour de cassation",
        "license_name": _LICENSE_ETALAB,
        "license_url": _URL_ETALAB_LICENSE,
        "terms_name": "CGU PISTE + CGU Réutilisation Cour de cassation",
        "terms_url": "https://www.courdecassation.fr/conditions-generales-dutilisation-pour-la-reutilisation-des-donnees-issues-des-decisions-de-justice",
        "access_mode": AccessMode.API_KEY_CGU,
    },
    LegalSource.JADE: {
        "source_name": "DILA (données Conseil d'État)",
        "license_name": _LICENSE_ETALAB,
        "license_url": _URL_ETALAB_LICENSE,
        "terms_name": "Conditions DILA FTPS",
        "terms_url": "https://echanges.dila.gouv.fr/OPENDATA/AVERTISSEMENT-Donnees_a_caractere_personnel.pdf",
        "access_mode": AccessMode.REQUEST_TO_ADMIN,
    },
    LegalSource.CONSTIT: {
        "source_name": "Conseil constitutionnel",
        "license_name": _LICENSE_ETALAB,
        "license_url": _URL_ETALAB_LICENSE,
        "terms_name": _TERMS_NAME_PISTE,
        "terms_url": _URL_PISTE_CGU,
        "access_mode": AccessMode.API_KEY_CGU,
    },
}


def create_compliant_provenance(
    source: LegalSource,
    origin_id: str,
    origin_url: Optional[str] = None,
    content_hash: Optional[str] = None,
    pinpoint: Optional[str] = None,
    chunk_index: Optional[int] = None,
) -> Provenance:
    """
    Crée une Provenance conforme avec licence/CGU vérifiées.
    
    Utilise SOURCE_COMPLIANCE pour garantir que tous les champs
    obligatoires sont remplis avec des valeurs sourcées.
    """
    compliance = SOURCE_COMPLIANCE.get(source)
    if not compliance:
        raise ValueError(f"Source {source} not in compliance registry")
    
    return Provenance(
        source=source,
        source_name=compliance["source_name"],
        origin_id=origin_id,
        origin_url=origin_url,
        retrieved_at=datetime.utcnow(),
        license_name=compliance["license_name"],
        license_url=compliance["license_url"],
        terms_name=compliance["terms_name"],
        terms_url=compliance["terms_url"],
        access_mode=compliance["access_mode"],
        content_hash=content_hash,
        pinpoint=pinpoint,
        chunk_index=chunk_index,
    )


@dataclass
class LegalDoc:
    """
    Document juridique normalisé.
    
    Schéma unique pour tous les types de sources (LEGI, CASS, JADE, etc.)
    
    AUDIT: Document ne peut être indexé que si provenance.is_valid == True
    """
    # === Identifiants (stables, déterministes) ===
    doc_id: str  # Hash stable: SHA256(source + origin_id)
    
    # === Métadonnées source ===
    source: LegalSource
    origin_id: str  # ID d'origine (LEGITEXT..., JURITEXT..., ECLI, etc.)
    
    # === Classification ===
    document_type: DocumentType
    jurisdiction: Jurisdiction
    
    # === Identification ===
    title: str
    citation: str  # Format court: "Art. 1134 C. civ." ou "Cass. civ. 1re, 15 janv. 2024"
    
    # === Dates ===
    date: Optional[datetime] = None  # Date du document
    date_publication: Optional[datetime] = None
    date_effect: Optional[datetime] = None  # Date d'entrée en vigueur
    
    # === Contenu ===
    text: str = ""
    summary: Optional[str] = None
    
    # === Métadonnées spécifiques ===
    # Pour LEGI (codes)
    code_name: Optional[str] = None  # "Code civil", "Code pénal", etc.
    article_number: Optional[str] = None  # "1134", "L. 121-1", etc.
    articles_refs: List[str] = field(default_factory=list)  # Références articles liés
    
    # Pour CASS (arrêts)
    court: Optional[str] = None  # "Cour de cassation"
    chamber: Optional[str] = None  # "Première chambre civile"
    decision_number: Optional[str] = None  # Numéro de pourvoi
    ecli: Optional[str] = None  # European Case Law Identifier
    solution: Optional[str] = None  # "Rejet", "Cassation", etc.
    
    # Pour JADE (administratif)
    formation: Optional[str] = None  # "Assemblée", "Section", etc.
    
    # === Traçabilité (OBLIGATOIRE pour indexation) ===
    provenance: Optional[Provenance] = None
    
    # === Intégrité ===
    content_hash: str = ""  # SHA256 du texte normalisé
    
    def __post_init__(self):
        """Calcule les champs dérivés."""
        if not self.doc_id:
            self.doc_id = self._compute_doc_id()
        if not self.content_hash and self.text:
            self.content_hash = self._compute_content_hash()
    
    def _compute_doc_id(self) -> str:
        """
        Génère un doc_id stable et déterministe.
        
        Invariant: même source + origin_id => même doc_id
        """
        key = f"{self.source.value}:{self.origin_id}"
        return hashlib.sha256(key.encode()).hexdigest()[:16]
    
    def _compute_content_hash(self) -> str:
        """Hash du contenu pour détecter les modifications."""
        normalized = self.text.strip().lower()
        return hashlib.sha256(normalized.encode()).hexdigest()[:12]
    
    def validate_for_indexing(self) -> None:
        """
        Valide que le document peut être indexé.
        
        AUDIT: Refuse l'indexation si provenance incomplète.
        
        Raises:
            ProvenanceValidationError: Si provenance manquante ou incomplète
        """
        if not self.provenance:
            raise ProvenanceValidationError(
                f"Document {self.doc_id} n'a pas de provenance. "
                f"AUDIT: Aucun document ne peut être indexé sans provenance."
            )
        self.provenance.validate()
    
    @property
    def can_be_indexed(self) -> bool:
        """Vérifie si le document peut être indexé."""
        try:
            self.validate_for_indexing()
            return True
        except ProvenanceValidationError:
            return False
    
    def to_dict(self) -> Dict[str, Any]:
        """Sérialise pour stockage/indexation."""
        return {
            "doc_id": self.doc_id,
            "source": self.source.value,
            "origin_id": self.origin_id,
            "document_type": self.document_type.value,
            "jurisdiction": self.jurisdiction.value,
            "title": self.title,
            "citation": self.citation,
            "date": self.date.isoformat() if self.date else None,
            "date_publication": self.date_publication.isoformat() if self.date_publication else None,
            "date_effect": self.date_effect.isoformat() if self.date_effect else None,
            "text": self.text,
            "summary": self.summary,
            "code_name": self.code_name,
            "article_number": self.article_number,
            "articles_refs": self.articles_refs,
            "court": self.court,
            "chamber": self.chamber,
            "decision_number": self.decision_number,
            "ecli": self.ecli,
            "solution": self.solution,
            "formation": self.formation,
            "provenance": self.provenance.to_dict() if self.provenance else None,
            "content_hash": self.content_hash,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "LegalDoc":
        """Désérialise depuis stockage."""
        provenance = None
        if data.get("provenance"):
            provenance = Provenance.from_dict(data["provenance"])
        
        return cls(
            doc_id=data["doc_id"],
            source=LegalSource(data["source"]),
            origin_id=data["origin_id"],
            document_type=DocumentType(data["document_type"]),
            jurisdiction=Jurisdiction(data["jurisdiction"]),
            title=data["title"],
            citation=data["citation"],
            date=datetime.fromisoformat(data["date"]) if data.get("date") else None,
            date_publication=datetime.fromisoformat(data["date_publication"]) if data.get("date_publication") else None,
            date_effect=datetime.fromisoformat(data["date_effect"]) if data.get("date_effect") else None,
            text=data.get("text", ""),
            summary=data.get("summary"),
            code_name=data.get("code_name"),
            article_number=data.get("article_number"),
            articles_refs=data.get("articles_refs", []),
            court=data.get("court"),
            chamber=data.get("chamber"),
            decision_number=data.get("decision_number"),
            ecli=data.get("ecli"),
            solution=data.get("solution"),
            formation=data.get("formation"),
            provenance=provenance,
            content_hash=data.get("content_hash", ""),
        )


@dataclass
class LegalChunk:
    """
    Chunk de document juridique pour indexation vectorielle.
    
    Chaque chunk conserve sa provenance complète pour citation.
    AUDIT: Chunk ne peut être créé que si provenance valide.
    """
    # === Identifiants ===
    chunk_id: str  # Hash stable: SHA256(doc_id + chunk_index)
    doc_id: str  # Référence au document parent
    chunk_index: int  # Position dans le document
    
    # === Contenu ===
    text: str
    
    # === Métadonnées héritées ===
    source: LegalSource
    document_type: DocumentType
    citation: str  # Citation du document parent
    pinpoint: str  # Position précise: "Art. 1134, al. 2"
    
    # === Traçabilité (OBLIGATOIRE) ===
    provenance: Provenance
    
    # === Vecteur (optionnel, rempli après embedding) ===
    embedding: Optional[List[float]] = None
    
    def __post_init__(self):
        if not self.chunk_id:
            self.chunk_id = self._compute_chunk_id()
        # Valider provenance à la création
        if self.provenance:
            self.provenance.validate()
    
    def _compute_chunk_id(self) -> str:
        """ID déterministe du chunk."""
        key = f"{self.doc_id}:{self.chunk_index}"
        return hashlib.sha256(key.encode()).hexdigest()[:16]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "chunk_id": self.chunk_id,
            "doc_id": self.doc_id,
            "chunk_index": self.chunk_index,
            "text": self.text,
            "source": self.source.value,
            "document_type": self.document_type.value,
            "citation": self.citation,
            "pinpoint": self.pinpoint,
            "provenance": self.provenance.to_dict(),
            "embedding": self.embedding,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "LegalChunk":
        return cls(
            chunk_id=data["chunk_id"],
            doc_id=data["doc_id"],
            chunk_index=data["chunk_index"],
            text=data["text"],
            source=LegalSource(data["source"]),
            document_type=DocumentType(data["document_type"]),
            citation=data["citation"],
            pinpoint=data["pinpoint"],
            provenance=Provenance.from_dict(data["provenance"]),
            embedding=data.get("embedding"),
        )


@dataclass
class IngestionResult:
    """Résultat d'une opération d'ingestion."""
    source: LegalSource
    started_at: datetime
    completed_at: Optional[datetime] = None
    
    # Compteurs
    docs_fetched: int = 0
    docs_parsed: int = 0
    docs_indexed: int = 0
    docs_skipped: int = 0  # Déjà présents (idempotence)
    docs_failed: int = 0
    docs_rejected_no_provenance: int = 0  # Rejetés pour provenance manquante
    
    chunks_created: int = 0
    
    # Résilience
    retries_total: int = 0
    rate_limited_count: int = 0  # 429 reçus
    
    # Erreurs
    errors: List[str] = field(default_factory=list)
    
    # Checkpoint
    last_cursor: Optional[str] = None
    last_doc_id: Optional[str] = None
    
    @property
    def success(self) -> bool:
        return self.docs_failed == 0 and len(self.errors) == 0
    
    @property
    def duration_seconds(self) -> float:
        if self.completed_at and self.started_at:
            return (self.completed_at - self.started_at).total_seconds()
        return 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "source": self.source.value,
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "duration_seconds": self.duration_seconds,
            "docs_fetched": self.docs_fetched,
            "docs_parsed": self.docs_parsed,
            "docs_indexed": self.docs_indexed,
            "docs_skipped": self.docs_skipped,
            "docs_failed": self.docs_failed,
            "docs_rejected_no_provenance": self.docs_rejected_no_provenance,
            "chunks_created": self.chunks_created,
            "retries_total": self.retries_total,
            "rate_limited_count": self.rate_limited_count,
            "errors": self.errors,
            "last_cursor": self.last_cursor,
            "last_doc_id": self.last_doc_id,
            "success": self.success,
        }
