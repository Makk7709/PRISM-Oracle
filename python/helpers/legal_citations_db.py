"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                    LEGAL-SAFE MODE — CITATIONS DATABASE                     ║
║                                                                              ║
║  Index des références juridiques valides pour validation FR/EU.             ║
║  Utilisé pour vérifier que les citations ne sont pas inventées.             ║
║                                                                              ║
║  Version: 1.0.0                                                              ║
║  © 2025 Korev AI — Proprietary                                               ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum
from typing import Optional


# ═══════════════════════════════════════════════════════════════════════════════
# ENUMS
# ═══════════════════════════════════════════════════════════════════════════════

class CodeType(str, Enum):
    """Types de codes juridiques français."""
    CIVIL = "civil"
    TRAVAIL = "travail"
    COMMERCE = "commerce"
    PENAL = "penal"
    CONSOMMATION = "consommation"
    PROCEDURE_CIVILE = "procedure_civile"
    PROCEDURE_PENALE = "procedure_penale"
    PROPRIETE_INTELLECTUELLE = "propriete_intellectuelle"
    SECURITE_SOCIALE = "securite_sociale"
    GENERAL_IMPOTS = "general_impots"
    ENVIRONNEMENT = "environnement"
    URBANISME = "urbanisme"
    CONSTRUCTION = "construction"
    ASSURANCES = "assurances"
    MONETAIRE_FINANCIER = "monetaire_financier"


class SourceType(str, Enum):
    """Types de sources juridiques."""
    CODE = "code"
    LOI = "loi"
    DECRET = "decret"
    ORDONNANCE = "ordonnance"
    REGLEMENT_UE = "reglement_ue"
    DIRECTIVE_UE = "directive_ue"
    JURISPRUDENCE_CASS = "jurisprudence_cass"
    JURISPRUDENCE_CE = "jurisprudence_ce"
    JURISPRUDENCE_CEDH = "jurisprudence_cedh"
    JURISPRUDENCE_CJUE = "jurisprudence_cjue"


# ═══════════════════════════════════════════════════════════════════════════════
# DATA CLASSES
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class CodeArticle:
    """Représentation d'un article de code."""
    code: CodeType
    article: str
    titre: Optional[str] = None
    en_vigueur: bool = True
    date_version: Optional[str] = None


@dataclass
class ReglementUE:
    """Représentation d'un règlement européen."""
    numero: str
    annee: int
    nom_court: Optional[str] = None
    articles_principaux: list[int] = None


@dataclass
class DirectiveUE:
    """Représentation d'une directive européenne."""
    numero: str
    annee: int
    nom_court: Optional[str] = None


@dataclass
class ValidationResult:
    """Résultat de validation d'une citation."""
    is_valid: bool
    source_type: Optional[SourceType] = None
    normalized_citation: Optional[str] = None
    confidence: float = 0.0
    warning: Optional[str] = None


# ═══════════════════════════════════════════════════════════════════════════════
# CODES FRANÇAIS — Structure des articles
# ═══════════════════════════════════════════════════════════════════════════════

# Patterns d'articles valides par code
CODE_ARTICLE_PATTERNS = {
    CodeType.CIVIL: [
        r"[LRD]?\d{1,4}(?:-\d+)?(?:-\d+)?",  # Ex: 1103, L123-4, R456-7-8
    ],
    CodeType.TRAVAIL: [
        r"L\d{4}-\d+(?:-\d+)?",  # Ex: L1234-5, L1234-5-1
        r"R\d{4}-\d+(?:-\d+)?",  # Ex: R1234-5
        r"D\d{4}-\d+(?:-\d+)?",  # Ex: D1234-5
    ],
    CodeType.COMMERCE: [
        r"L\d{3}-\d+(?:-\d+)?",  # Ex: L123-4
        r"R\d{3}-\d+(?:-\d+)?",
    ],
    CodeType.PENAL: [
        r"\d{3}-\d+(?:-\d+)?",  # Ex: 311-1, 222-33-2
        r"R\d{3}-\d+(?:-\d+)?",
    ],
    CodeType.CONSOMMATION: [
        r"L\d{3}-\d+(?:-\d+)?",
        r"R\d{3}-\d+(?:-\d+)?",
    ],
    CodeType.GENERAL_IMPOTS: [
        r"\d{1,4}(?:\s*[A-Z])?(?:\s*bis)?(?:\s*ter)?",  # Ex: 38, 39 A, 44 sexies
    ],
}

# Noms des codes (pour normalisation)
CODE_NAMES = {
    CodeType.CIVIL: ["Code civil", "C. civ.", "CC"],
    CodeType.TRAVAIL: ["Code du travail", "C. trav.", "CT"],
    CodeType.COMMERCE: ["Code de commerce", "C. com."],
    CodeType.PENAL: ["Code pénal", "C. pén.", "CP"],
    CodeType.CONSOMMATION: ["Code de la consommation", "C. conso."],
    CodeType.PROCEDURE_CIVILE: ["Code de procédure civile", "CPC"],
    CodeType.PROCEDURE_PENALE: ["Code de procédure pénale", "CPP"],
    CodeType.PROPRIETE_INTELLECTUELLE: ["Code de la propriété intellectuelle", "CPI"],
    CodeType.SECURITE_SOCIALE: ["Code de la sécurité sociale", "CSS"],
    CodeType.GENERAL_IMPOTS: ["Code général des impôts", "CGI"],
    CodeType.ENVIRONNEMENT: ["Code de l'environnement", "C. env."],
    CodeType.URBANISME: ["Code de l'urbanisme", "C. urb."],
    CodeType.CONSTRUCTION: ["Code de la construction et de l'habitation", "CCH"],
    CodeType.ASSURANCES: ["Code des assurances", "C. ass."],
    CodeType.MONETAIRE_FINANCIER: ["Code monétaire et financier", "CMF"],
}


# ═══════════════════════════════════════════════════════════════════════════════
# RÈGLEMENTS ET DIRECTIVES UE
# ═══════════════════════════════════════════════════════════════════════════════

# Règlements UE majeurs
REGLEMENTS_UE = {
    "RGPD": ReglementUE(
        numero="2016/679",
        annee=2016,
        nom_court="RGPD",
        articles_principaux=[1, 2, 3, 4, 5, 6, 7, 9, 12, 13, 14, 15, 16, 17, 18, 20, 21, 22, 23, 24, 25, 26, 27, 28, 30, 32, 33, 34, 35, 37, 44, 45, 46, 49, 77, 79, 82, 83]
    ),
    "eIDAS": ReglementUE(
        numero="910/2014",
        annee=2014,
        nom_court="eIDAS",
    ),
    "P2B": ReglementUE(
        numero="2019/1150",
        annee=2019,
        nom_court="P2B (platform to business)",
    ),
    "DSA": ReglementUE(
        numero="2022/2065",
        annee=2022,
        nom_court="DSA (Digital Services Act)",
    ),
    "DMA": ReglementUE(
        numero="2022/1925",
        annee=2022,
        nom_court="DMA (Digital Markets Act)",
    ),
    "AI_ACT": ReglementUE(
        numero="2024/1689",
        annee=2024,
        nom_court="AI Act",
    ),
}

# Directives UE majeures
DIRECTIVES_UE = {
    "droits_consommateurs": DirectiveUE(
        numero="2011/83",
        annee=2011,
        nom_court="Droits des consommateurs",
    ),
    "ecommerce": DirectiveUE(
        numero="2000/31",
        annee=2000,
        nom_court="Commerce électronique",
    ),
    "clauses_abusives": DirectiveUE(
        numero="93/13",
        annee=1993,
        nom_court="Clauses abusives",
    ),
    "conditions_travail": DirectiveUE(
        numero="2019/1152",
        annee=2019,
        nom_court="Conditions de travail transparentes",
    ),
    "temps_travail": DirectiveUE(
        numero="2003/88",
        annee=2003,
        nom_court="Temps de travail",
    ),
    "protection_donnees_police": DirectiveUE(
        numero="2016/680",
        annee=2016,
        nom_court="Protection données police/justice",
    ),
}


# ═══════════════════════════════════════════════════════════════════════════════
# JURISPRUDENCE — Patterns valides
# ═══════════════════════════════════════════════════════════════════════════════

JURISPRUDENCE_PATTERNS = {
    SourceType.JURISPRUDENCE_CASS: [
        # Cass. soc., 15 mars 2023, n° 21-12.345
        r"Cass\.\s*(?:soc|civ|com|crim|ass\.?\s*plén|ch\.?\s*mixte)[.,]?",
        r"Cass\.\s*(?:1re|2e|3e)\s*civ\.",
        r"n°\s*\d{2}-\d{2}\.\d{3}",
        r"Cassation",
    ],
    SourceType.JURISPRUDENCE_CE: [
        # CE, 15 mars 2023, n° 456789
        r"CE[,.]?\s*(?:ass|sect)?\.?\s*\d{1,2}\s*(?:janv|févr|mars|avr|mai|juin|juill|août|sept|oct|nov|déc)\.?\s*\d{4}",
        r"Conseil\s+d'[EÉ]tat",
    ],
    SourceType.JURISPRUDENCE_CEDH: [
        r"CEDH",
        r"Cour\s+(?:européenne|EDH)",
        r"c\.\s+France",  # Ex: X c. France
    ],
    SourceType.JURISPRUDENCE_CJUE: [
        r"CJUE",
        r"CJCE",
        r"C-\d+/\d+",  # Ex: C-123/19
        r"Cour\s+de\s+justice",
    ],
}


# ═══════════════════════════════════════════════════════════════════════════════
# FONCTIONS DE VALIDATION
# ═══════════════════════════════════════════════════════════════════════════════

def validate_citation(citation: str) -> ValidationResult:
    """
    Valide une citation juridique.
    
    Args:
        citation: La citation à valider (ex: "Code civil, art. 1103")
        
    Returns:
        ValidationResult avec le statut de validation
    """
    citation_lower = citation.lower().strip()
    
    # Cas spécial : UNKNOWN est toujours valide (indique l'incertitude)
    if "unknown" in citation_lower:
        return ValidationResult(
            is_valid=True,
            source_type=None,
            normalized_citation="UNKNOWN",
            confidence=1.0,
            warning="Citation marquée comme incertaine"
        )
    
    # Vérifier les codes français
    result = _validate_code_francais(citation)
    if result.is_valid:
        return result
    
    # Vérifier les règlements UE
    result = _validate_reglement_ue(citation)
    if result.is_valid:
        return result
    
    # Vérifier les directives UE
    result = _validate_directive_ue(citation)
    if result.is_valid:
        return result
    
    # Vérifier la jurisprudence
    result = _validate_jurisprudence(citation)
    if result.is_valid:
        return result
    
    # Citation non reconnue
    return ValidationResult(
        is_valid=False,
        confidence=0.0,
        warning=f"Format de citation non reconnu: {citation}"
    )


def _validate_code_francais(citation: str) -> ValidationResult:
    """Valide une référence à un code français."""
    citation_lower = citation.lower()
    
    for code_type, names in CODE_NAMES.items():
        for name in names:
            if name.lower() in citation_lower:
                # Code trouvé, vérifier le format de l'article
                patterns = CODE_ARTICLE_PATTERNS.get(code_type, [])
                
                # Extraire la partie article
                art_match = re.search(r"art(?:icle)?\.?\s*([LRDA]?\d+(?:-\d+)*(?:\s*[a-z]+)?)", citation, re.IGNORECASE)
                
                if art_match:
                    article = art_match.group(1)
                    # Vérifier si le format correspond
                    for pattern in patterns:
                        if re.match(pattern, article, re.IGNORECASE):
                            return ValidationResult(
                                is_valid=True,
                                source_type=SourceType.CODE,
                                normalized_citation=f"{names[0]}, art. {article}",
                                confidence=0.9
                            )
                
                # Code trouvé mais format article suspect
                return ValidationResult(
                    is_valid=True,
                    source_type=SourceType.CODE,
                    normalized_citation=citation,
                    confidence=0.6,
                    warning="Format d'article non standard"
                )
    
    return ValidationResult(is_valid=False, confidence=0.0)


def _validate_reglement_ue(citation: str) -> ValidationResult:
    """Valide une référence à un règlement UE."""
    citation_upper = citation.upper()
    
    # Vérifier les règlements connus
    for short_name, reglement in REGLEMENTS_UE.items():
        if short_name in citation_upper or reglement.numero in citation:
            # Vérifier si un article est mentionné
            art_match = re.search(r"art(?:icle)?\.?\s*(\d+)", citation, re.IGNORECASE)
            
            confidence = 0.9
            warning = None
            
            if art_match and reglement.articles_principaux:
                article_num = int(art_match.group(1))
                if article_num not in reglement.articles_principaux:
                    confidence = 0.7
                    warning = f"Article {article_num} non dans la liste des articles principaux connus"
            
            return ValidationResult(
                is_valid=True,
                source_type=SourceType.REGLEMENT_UE,
                normalized_citation=f"Règlement (UE) {reglement.numero} ({reglement.nom_court})",
                confidence=confidence,
                warning=warning
            )
    
    # Pattern générique règlement UE
    if re.search(r"r[èe]glement\s*\(?(?:UE|CE)\)?\s*(?:n[°o]?\s*)?\d{4}/\d+", citation, re.IGNORECASE):
        return ValidationResult(
            is_valid=True,
            source_type=SourceType.REGLEMENT_UE,
            normalized_citation=citation,
            confidence=0.7,
            warning="Règlement UE non référencé dans la base"
        )
    
    return ValidationResult(is_valid=False, confidence=0.0)


def _validate_directive_ue(citation: str) -> ValidationResult:
    """Valide une référence à une directive UE."""
    # Vérifier les directives connues
    for short_name, directive in DIRECTIVES_UE.items():
        if directive.numero in citation:
            return ValidationResult(
                is_valid=True,
                source_type=SourceType.DIRECTIVE_UE,
                normalized_citation=f"Directive {directive.numero}/UE ({directive.nom_court})",
                confidence=0.9
            )
    
    # Pattern générique directive UE
    if re.search(r"directive\s*(?:\(?(?:UE|CE)\)?\s*)?(?:n[°o]?\s*)?\d{4}/\d+", citation, re.IGNORECASE):
        return ValidationResult(
            is_valid=True,
            source_type=SourceType.DIRECTIVE_UE,
            normalized_citation=citation,
            confidence=0.7,
            warning="Directive UE non référencée dans la base"
        )
    
    return ValidationResult(is_valid=False, confidence=0.0)


def _validate_jurisprudence(citation: str) -> ValidationResult:
    """Valide une référence jurisprudentielle."""
    for source_type, patterns in JURISPRUDENCE_PATTERNS.items():
        for pattern in patterns:
            if re.search(pattern, citation, re.IGNORECASE):
                return ValidationResult(
                    is_valid=True,
                    source_type=source_type,
                    normalized_citation=citation,
                    confidence=0.8,
                    warning="Référence jurisprudentielle - vérification recommandée"
                )
    
    return ValidationResult(is_valid=False, confidence=0.0)


def validate_multiple_citations(citations: list[str]) -> dict[str, ValidationResult]:
    """
    Valide plusieurs citations.
    
    Args:
        citations: Liste de citations
        
    Returns:
        Dict citation -> ValidationResult
    """
    return {citation: validate_citation(citation) for citation in citations}


def get_citation_suggestions(domain: str) -> list[str]:
    """
    Retourne des suggestions de citations pour un domaine.
    
    Args:
        domain: Domaine juridique (ex: "droit_travail")
        
    Returns:
        Liste de citations suggérées
    """
    suggestions = {
        "droit_travail": [
            "Code du travail, art. L1221-1 (contrat de travail)",
            "Code du travail, art. L1231-1 (rupture CDI)",
            "Code du travail, art. L1232-1 (licenciement pour motif personnel)",
            "Code du travail, art. L1233-1 (licenciement économique)",
            "Code du travail, art. L1152-1 (harcèlement moral)",
            "Code du travail, art. L1153-1 (harcèlement sexuel)",
            "Code du travail, art. L3121-1 (durée du travail)",
        ],
        "rgpd_donnees": [
            "RGPD, art. 5 (principes relatifs au traitement)",
            "RGPD, art. 6 (licéité du traitement)",
            "RGPD, art. 7 (consentement)",
            "RGPD, art. 13 (information)",
            "RGPD, art. 15 (droit d'accès)",
            "RGPD, art. 17 (droit à l'effacement)",
            "RGPD, art. 33 (notification de violation)",
        ],
        "contrats": [
            "Code civil, art. 1101 (définition du contrat)",
            "Code civil, art. 1103 (force obligatoire)",
            "Code civil, art. 1104 (bonne foi)",
            "Code civil, art. 1128 (conditions de validité)",
            "Code civil, art. 1217 (inexécution)",
            "Code civil, art. 1231-1 (dommages-intérêts)",
        ],
        "fiscal": [
            "CGI, art. 38 (bénéfice imposable)",
            "CGI, art. 39 (charges déductibles)",
            "CGI, art. 256 (TVA - opérations imposables)",
            "LPF, art. L10 (droit de contrôle)",
        ],
        "consommation": [
            "Code de la consommation, art. L111-1 (information précontractuelle)",
            "Code de la consommation, art. L121-1 (pratiques commerciales déloyales)",
            "Code de la consommation, art. L212-1 (clauses abusives)",
            "Code de la consommation, art. L221-1 (contrats à distance)",
        ],
    }
    
    return suggestions.get(domain, [])


# ═══════════════════════════════════════════════════════════════════════════════
# EXPORTS
# ═══════════════════════════════════════════════════════════════════════════════

__all__ = [
    # Enums
    "CodeType",
    "SourceType",
    # Data classes
    "CodeArticle",
    "ReglementUE",
    "DirectiveUE",
    "ValidationResult",
    # Databases
    "CODE_NAMES",
    "REGLEMENTS_UE",
    "DIRECTIVES_UE",
    # Functions
    "validate_citation",
    "validate_multiple_citations",
    "get_citation_suggestions",
]
