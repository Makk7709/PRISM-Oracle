"""
Legal Citations — Helper pour citations juridiques opposables

Génère des citations standardisées et un audit trail complet
pour les documents juridiques indexés.

Usage:
    from python.helpers.legal_citations import format_citation, build_audit_trail
    
    citation = format_citation(chunk_metadata)
    audit = build_audit_trail(chunks_used)
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional, Union


@dataclass
class CitationFormat:
    """Formats de citation supportés."""
    COURT = "court"      # Format court: "Art. 1134 C. civ."
    FULL = "full"        # Format complet avec date et source
    ACADEMIC = "academic"  # Format académique avec URL
    INLINE = "inline"    # Format pour citation inline dans le texte


def format_citation(
    chunk_meta: Dict[str, Any],
    format: str = CitationFormat.COURT,
) -> str:
    """
    Génère une citation formatée pour un chunk juridique.
    
    Args:
        chunk_meta: Métadonnées du chunk (provenance, citation, etc.)
        format: Format de citation souhaité
    
    Returns:
        Citation formatée
    
    Examples:
        >>> format_citation({"citation": "Art. 1134 C. civ."})
        "Art. 1134 C. civ."
        
        >>> format_citation(chunk_meta, format="full")
        "Art. 1134 Code civil, version en vigueur au 01/01/2024 (LEGITEXT000006070721)"
    """
    source = chunk_meta.get("source", "")
    citation = chunk_meta.get("citation", "")
    pinpoint = chunk_meta.get("pinpoint", "")
    provenance = chunk_meta.get("provenance", {})
    
    if format == CitationFormat.COURT:
        return _format_court(citation, pinpoint)
    
    elif format == CitationFormat.FULL:
        return _format_full(chunk_meta, provenance)
    
    elif format == CitationFormat.ACADEMIC:
        return _format_academic(chunk_meta, provenance)
    
    elif format == CitationFormat.INLINE:
        return _format_inline(citation, pinpoint)
    
    return citation


def _format_court(citation: str, pinpoint: str) -> str:
    """Format court: citation + pinpoint si disponible."""
    if pinpoint and pinpoint not in citation:
        return f"{citation}, {pinpoint}"
    return citation


def _format_full(meta: Dict, provenance: Dict) -> str:
    """Format complet avec date et identifiant."""
    citation = meta.get("citation", "")
    origin_id = provenance.get("origin_id", "")
    retrieved_at = provenance.get("retrieved_at", "")
    
    # Parser la date
    date_str = ""
    if retrieved_at:
        try:
            if isinstance(retrieved_at, str):
                dt = datetime.fromisoformat(retrieved_at.replace("Z", "+00:00"))
            else:
                dt = retrieved_at
            date_str = dt.strftime("%d/%m/%Y")
        except (ValueError, AttributeError):
            pass
    
    parts = [citation]
    if date_str:
        parts.append(f"version consultée le {date_str}")
    if origin_id:
        parts.append(f"({origin_id})")
    
    return ", ".join(parts)


def _format_academic(meta: Dict, provenance: Dict) -> str:
    """Format académique avec URL source."""
    citation = meta.get("citation", "")
    origin_url = provenance.get("origin_url", "")
    retrieved_at = provenance.get("retrieved_at", "")
    
    parts = [citation]
    
    if origin_url:
        parts.append(f"disponible sur: {origin_url}")
    
    if retrieved_at:
        try:
            if isinstance(retrieved_at, str):
                dt = datetime.fromisoformat(retrieved_at.replace("Z", "+00:00"))
            else:
                dt = retrieved_at
            parts.append(f"(consulté le {dt.strftime('%d %B %Y')})")
        except (ValueError, AttributeError):
            pass
    
    return ", ".join(parts)


def _format_inline(citation: str, pinpoint: str) -> str:
    """Format pour citation inline dans le texte."""
    base = citation
    if pinpoint and pinpoint not in citation:
        base = f"{citation} ({pinpoint})"
    return f"[{base}]"


def build_audit_trail(chunks_used: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Construit un audit trail complet pour une réponse utilisant des chunks.
    
    L'audit trail garantit la traçabilité complète des sources utilisées
    pour générer une réponse.
    
    Args:
        chunks_used: Liste des chunks utilisés (avec leurs métadonnées)
    
    Returns:
        Dict contenant:
        - sources: Liste des sources uniques
        - citations: Citations formatées
        - provenance: Détails de provenance par source
        - timestamp: Horodatage de l'audit
        - checksums: Hash des contenus pour vérification
    
    Example:
        >>> audit = build_audit_trail(chunks)
        >>> audit["sources"]
        ["LEGI", "CASS"]
        >>> audit["citations"]
        ["Art. 1134 C. civ.", "Cass. civ. 1re, 15 janv. 2024"]
    """
    if not chunks_used:
        return {
            "sources": [],
            "citations": [],
            "provenance": [],
            "timestamp": datetime.utcnow().isoformat(),
            "checksums": [],
            "warning": "No sources provided",
        }
    
    sources = set()
    citations = []
    provenance_list = []
    checksums = []
    
    for chunk in chunks_used:
        # Source
        source = chunk.get("source", "")
        if source:
            sources.add(source)
        
        # Citation
        citation = format_citation(chunk, format=CitationFormat.FULL)
        if citation and citation not in citations:
            citations.append(citation)
        
        # Provenance
        prov = chunk.get("provenance", {})
        if prov:
            provenance_list.append({
                "source": source,
                "origin_id": prov.get("origin_id", ""),
                "origin_url": prov.get("origin_url", ""),
                "retrieved_at": prov.get("retrieved_at", ""),
                "license": prov.get("license", ""),
                "pinpoint": prov.get("pinpoint", "") or chunk.get("pinpoint", ""),
            })
        
        # Checksum
        content_hash = prov.get("content_hash") or chunk.get("content_hash", "")
        if content_hash and content_hash not in checksums:
            checksums.append(content_hash)
    
    return {
        "sources": sorted(list(sources)),
        "citations": citations,
        "provenance": provenance_list,
        "timestamp": datetime.utcnow().isoformat(),
        "checksums": checksums,
        "total_chunks": len(chunks_used),
    }


def format_sources_block(audit_trail: Dict[str, Any]) -> str:
    """
    Génère un bloc de sources formaté pour affichage.
    
    Args:
        audit_trail: Résultat de build_audit_trail()
    
    Returns:
        Bloc de texte formaté avec les sources
    """
    lines = ["**Sources:**"]
    
    citations = audit_trail.get("citations", [])
    if not citations:
        return "*Aucune source juridique citée.*"
    
    for i, citation in enumerate(citations, 1):
        lines.append(f"{i}. {citation}")
    
    # Ajouter licence si disponible
    provenance = audit_trail.get("provenance", [])
    if provenance:
        licenses = set(p.get("license", "") for p in provenance if p.get("license"))
        if licenses:
            lines.append("")
            lines.append(f"*Licence: {', '.join(licenses)}*")
    
    return "\n".join(lines)


def validate_provenance(chunk_meta: Dict[str, Any]) -> Dict[str, Any]:
    """
    Valide qu'un chunk a une provenance complète.
    
    Args:
        chunk_meta: Métadonnées du chunk
    
    Returns:
        Dict avec:
        - valid: bool
        - missing: Liste des champs manquants
        - warnings: Avertissements non-bloquants
    """
    required_fields = [
        "source",
        "citation",
    ]
    
    provenance_required = [
        "origin_id",
        "retrieved_at",
        "license",
    ]
    
    missing = []
    warnings = []
    
    # Vérifier champs principaux
    for field in required_fields:
        if not chunk_meta.get(field):
            missing.append(field)
    
    # Vérifier provenance
    prov = chunk_meta.get("provenance", {})
    if not prov:
        missing.append("provenance")
    else:
        for field in provenance_required:
            if not prov.get(field):
                missing.append(f"provenance.{field}")
    
    # Warnings (non-bloquants)
    if not prov.get("origin_url"):
        warnings.append("origin_url manquant (recommandé)")
    
    if not prov.get("content_hash"):
        warnings.append("content_hash manquant (recommandé pour intégrité)")
    
    return {
        "valid": len(missing) == 0,
        "missing": missing,
        "warnings": warnings,
    }


# === Helpers pour formats spécifiques ===

def format_cass_citation(
    chamber: str,
    date: datetime,
    pourvoi: str,
    solution: Optional[str] = None,
) -> str:
    """
    Formate une citation de la Cour de cassation.
    
    Format: "Cass. [chambre abrégée], [date], n° [pourvoi]"
    
    Args:
        chamber: Nom de la chambre
        date: Date de la décision
        pourvoi: Numéro de pourvoi
        solution: Solution (optionnel)
    
    Returns:
        Citation formatée
    """
    # Abréviations chambres
    chamber_abbrev = {
        "Première chambre civile": "civ. 1re",
        "Deuxième chambre civile": "civ. 2e",
        "Troisième chambre civile": "civ. 3e",
        "Chambre commerciale": "com.",
        "Chambre sociale": "soc.",
        "Chambre criminelle": "crim.",
        "Assemblée plénière": "ass. plén.",
        "Chambre mixte": "ch. mixte",
    }.get(chamber, chamber[:8] if chamber else "")
    
    # Format date français
    months = [
        "janv.", "févr.", "mars", "avr.", "mai", "juin",
        "juill.", "août", "sept.", "oct.", "nov.", "déc."
    ]
    date_str = f"{date.day} {months[date.month - 1]} {date.year}"
    
    # Construire
    parts = ["Cass."]
    if chamber_abbrev:
        parts.append(chamber_abbrev + ",")
    parts.append(date_str + ",")
    parts.append(f"n° {pourvoi}")
    
    if solution:
        parts.append(f"({solution})")
    
    return " ".join(parts)


def format_code_citation(
    code_name: str,
    article_num: str,
    alinea: Optional[int] = None,
) -> str:
    """
    Formate une citation d'article de code.
    
    Format: "Art. [num] [code abrégé]" ou "Art. [num], al. [n] [code]"
    
    Args:
        code_name: Nom du code
        article_num: Numéro d'article
        alinea: Numéro d'alinéa (optionnel)
    
    Returns:
        Citation formatée
    """
    # Abréviations codes
    code_abbrev = {
        "Code civil": "C. civ.",
        "Code pénal": "C. pén.",
        "Code de commerce": "C. com.",
        "Code du travail": "C. trav.",
        "Code de procédure civile": "C. pr. civ.",
        "Code de procédure pénale": "C. pr. pén.",
        "Code général des impôts": "CGI",
        "Code de la consommation": "C. consom.",
        "Code de la propriété intellectuelle": "CPI",
        "Code de l'environnement": "C. envir.",
        "Code de la santé publique": "CSP",
        "Code de la sécurité sociale": "CSS",
    }.get(code_name, code_name[:10])
    
    if alinea:
        return f"Art. {article_num}, al. {alinea} {code_abbrev}"
    return f"Art. {article_num} {code_abbrev}"


def format_qpc_citation(
    numero: str,
    date: datetime,
    intitule: Optional[str] = None,
) -> str:
    """
    Formate une citation de QPC du Conseil constitutionnel.
    
    Format: "Cons. const., [date], n° [numero]-QPC"
    
    Args:
        numero: Numéro de la décision (ex: "2024-1090")
        date: Date de la décision
        intitule: Intitulé de la QPC (optionnel)
    
    Returns:
        Citation formatée
    """
    months = [
        "janv.", "févr.", "mars", "avr.", "mai", "juin",
        "juill.", "août", "sept.", "oct.", "nov.", "déc."
    ]
    date_str = f"{date.day} {months[date.month - 1]} {date.year}"
    
    citation = f"Cons. const., {date_str}, n° {numero}-QPC"
    
    if intitule:
        citation += f", {intitule}"
    
    return citation
