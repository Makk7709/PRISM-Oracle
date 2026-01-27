"""
Legal Sources — Audit Bundle Export

Export de bundles d'audit pour traçabilité complète.
Chaque bundle contient les preuves nécessaires pour un audit juridique.
"""

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from .models import LegalChunk, Provenance


@dataclass
class AuditEntry:
    """Entrée d'audit pour un chunk."""
    chunk_id: str
    doc_id: str
    source: str
    citation: str
    pinpoint: str
    text_excerpt: str  # Premiers 500 caractères
    
    # Provenance complète
    origin_id: str
    origin_url: Optional[str]
    retrieved_at: str
    license_name: str
    license_url: str
    terms_name: str
    terms_url: str
    access_mode: str
    content_hash: Optional[str]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "chunk_id": self.chunk_id,
            "doc_id": self.doc_id,
            "source": self.source,
            "citation": self.citation,
            "pinpoint": self.pinpoint,
            "text_excerpt": self.text_excerpt,
            "provenance": {
                "origin_id": self.origin_id,
                "origin_url": self.origin_url,
                "retrieved_at": self.retrieved_at,
                "license_name": self.license_name,
                "license_url": self.license_url,
                "terms_name": self.terms_name,
                "terms_url": self.terms_url,
                "access_mode": self.access_mode,
                "content_hash": self.content_hash,
            },
        }


@dataclass
class AuditBundle:
    """
    Bundle d'audit complet.
    
    Contient toutes les informations nécessaires pour
    prouver la provenance et la légalité des données utilisées.
    """
    bundle_id: str
    created_at: datetime
    description: str
    
    # Entrées
    entries: List[AuditEntry] = field(default_factory=list)
    
    # Métadonnées
    total_chunks: int = 0
    sources_used: List[str] = field(default_factory=list)
    licenses_used: List[Dict[str, str]] = field(default_factory=list)
    
    # Intégrité
    bundle_hash: str = ""
    
    def __post_init__(self):
        if not self.bundle_id:
            self.bundle_id = self._compute_bundle_id()
        if not self.bundle_hash:
            self.bundle_hash = self._compute_bundle_hash()
    
    def _compute_bundle_id(self) -> str:
        """Génère un ID unique pour le bundle."""
        key = f"{self.created_at.isoformat()}:{len(self.entries)}"
        return hashlib.sha256(key.encode()).hexdigest()[:12]
    
    def _compute_bundle_hash(self) -> str:
        """Calcule le hash du contenu pour intégrité."""
        content = json.dumps([e.to_dict() for e in self.entries], sort_keys=True)
        return hashlib.sha256(content.encode()).hexdigest()[:16]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "bundle_id": self.bundle_id,
            "created_at": self.created_at.isoformat(),
            "description": self.description,
            "total_chunks": self.total_chunks,
            "sources_used": self.sources_used,
            "licenses_used": self.licenses_used,
            "bundle_hash": self.bundle_hash,
            "entries": [e.to_dict() for e in self.entries],
        }
    
    def to_json(self, indent: int = 2) -> str:
        """Sérialise en JSON."""
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)
    
    def save(self, path: Path) -> None:
        """Sauvegarde le bundle dans un fichier."""
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(self.to_json())


def build_audit_bundle(
    chunks: List[Dict[str, Any]],
    description: str = "Audit bundle",
) -> AuditBundle:
    """
    Construit un bundle d'audit à partir de chunks.
    
    Args:
        chunks: Liste de chunks (dicts avec provenance)
        description: Description du bundle
        
    Returns:
        AuditBundle avec toutes les preuves
    """
    entries = []
    sources = set()
    licenses = {}
    
    for chunk_data in chunks:
        provenance = chunk_data.get("provenance", {})
        source = chunk_data.get("source", "unknown")
        
        # Extraire les infos
        text = chunk_data.get("text", "")
        text_excerpt = text[:500] + "..." if len(text) > 500 else text
        
        entry = AuditEntry(
            chunk_id=chunk_data.get("chunk_id", ""),
            doc_id=chunk_data.get("doc_id", ""),
            source=source,
            citation=chunk_data.get("citation", ""),
            pinpoint=chunk_data.get("pinpoint", ""),
            text_excerpt=text_excerpt,
            origin_id=provenance.get("origin_id", ""),
            origin_url=provenance.get("origin_url"),
            retrieved_at=provenance.get("retrieved_at", ""),
            license_name=provenance.get("license_name", ""),
            license_url=provenance.get("license_url", ""),
            terms_name=provenance.get("terms_name", ""),
            terms_url=provenance.get("terms_url", ""),
            access_mode=provenance.get("access_mode", ""),
            content_hash=provenance.get("content_hash"),
        )
        entries.append(entry)
        
        # Collecter sources et licences
        sources.add(source)
        license_key = provenance.get("license_name", "")
        if license_key and license_key not in licenses:
            licenses[license_key] = {
                "name": license_key,
                "url": provenance.get("license_url", ""),
            }
    
    bundle = AuditBundle(
        bundle_id="",
        created_at=datetime.utcnow(),
        description=description,
        entries=entries,
        total_chunks=len(entries),
        sources_used=sorted(list(sources)),
        licenses_used=list(licenses.values()),
    )
    
    # Recalculer hash après ajout des entrées
    bundle.bundle_hash = bundle._compute_bundle_hash()
    
    return bundle


def build_audit_bundle_from_chunks(
    chunks: List[LegalChunk],
    description: str = "Audit bundle",
) -> AuditBundle:
    """
    Construit un bundle d'audit à partir d'objets LegalChunk.
    
    Args:
        chunks: Liste de LegalChunk
        description: Description du bundle
        
    Returns:
        AuditBundle avec toutes les preuves
    """
    chunk_dicts = [c.to_dict() for c in chunks]
    return build_audit_bundle(chunk_dicts, description)


def validate_audit_bundle(bundle: AuditBundle) -> Dict[str, Any]:
    """
    Valide qu'un bundle d'audit est complet.
    
    Vérifie que chaque entrée a:
    - license_name, license_url non vides
    - terms_url non vide
    - access_mode non vide
    - origin_id non vide
    
    Returns:
        Dict avec valid (bool), missing_fields (list), warnings (list)
    """
    missing_fields = []
    warnings = []
    
    required_provenance_fields = [
        "license_name",
        "license_url",
        "terms_url",
        "access_mode",
        "origin_id",
    ]
    
    for i, entry in enumerate(bundle.entries):
        entry_dict = entry.to_dict()
        provenance = entry_dict.get("provenance", {})
        
        for field in required_provenance_fields:
            if not provenance.get(field):
                missing_fields.append(f"entry[{i}].provenance.{field}")
        
        # Warnings (non-bloquants)
        if not provenance.get("origin_url"):
            warnings.append(f"entry[{i}]: origin_url missing (recommended)")
        if not provenance.get("content_hash"):
            warnings.append(f"entry[{i}]: content_hash missing (recommended for integrity)")
    
    return {
        "valid": len(missing_fields) == 0,
        "missing_fields": missing_fields,
        "warnings": warnings,
        "total_entries": len(bundle.entries),
        "bundle_id": bundle.bundle_id,
    }


def generate_audit_report(bundle: AuditBundle) -> str:
    """
    Génère un rapport d'audit en Markdown.
    
    Args:
        bundle: AuditBundle à documenter
        
    Returns:
        Rapport Markdown
    """
    lines = [
        f"# Audit Report — {bundle.bundle_id}",
        "",
        f"**Generated**: {bundle.created_at.isoformat()}",
        f"**Description**: {bundle.description}",
        f"**Total Chunks**: {bundle.total_chunks}",
        f"**Bundle Hash**: `{bundle.bundle_hash}`",
        "",
        "## Sources Used",
        "",
    ]
    
    for source in bundle.sources_used:
        lines.append(f"- {source}")
    
    lines.extend([
        "",
        "## Licenses",
        "",
    ])
    
    for lic in bundle.licenses_used:
        lines.append(f"- **{lic['name']}**: [{lic['url']}]({lic['url']})")
    
    lines.extend([
        "",
        "## Entries",
        "",
        "| # | Source | Citation | Origin ID | License |",
        "|---|--------|----------|-----------|---------|",
    ])
    
    for i, entry in enumerate(bundle.entries[:20]):  # Limiter à 20 pour lisibilité
        lines.append(
            f"| {i+1} | {entry.source} | {entry.citation} | "
            f"`{entry.origin_id[:20]}...` | {entry.license_name} |"
        )
    
    if len(bundle.entries) > 20:
        lines.append(f"| ... | *{len(bundle.entries) - 20} more entries* | | | |")
    
    # Validation
    validation = validate_audit_bundle(bundle)
    
    lines.extend([
        "",
        "## Validation",
        "",
        f"**Status**: {'✅ Valid' if validation['valid'] else '❌ Invalid'}",
        "",
    ])
    
    if validation["missing_fields"]:
        lines.append("### Missing Fields")
        lines.append("")
        for field in validation["missing_fields"][:10]:
            lines.append(f"- {field}")
        if len(validation["missing_fields"]) > 10:
            lines.append(f"- *... and {len(validation['missing_fields']) - 10} more*")
    
    if validation["warnings"]:
        lines.append("")
        lines.append("### Warnings")
        lines.append("")
        for warn in validation["warnings"][:10]:
            lines.append(f"- {warn}")
    
    return "\n".join(lines)
