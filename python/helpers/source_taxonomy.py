"""
Source Taxonomy — Classification FR des sources juridiques pour rapports Evidence.

Fournit :
- SourceTypeFR : taxonomie fine des types de sources juridiques FR et EU
- SourceOrigin : editeur/base de donnees d'origine
- Inference regex : derive automatiquement le type et l'origine a partir
  du titre, de la reference ou de l'URL d'une source
- Scoring de fiabilite : pourcentage calibre par type de source

Alignement : compatible avec SourceType de legal_citations_db.py mais
plus granulaire (CEDH ≠ CJUE, circulaires, avis d'autorite, etc.)
"""

import re
from enum import Enum
from typing import Optional, Tuple


# ═══════════════════════════════════════════════════════════════════════════════
# ENUMS
# ═══════════════════════════════════════════════════════════════════════════════

class SourceTypeFR(str, Enum):
    """Taxonomie des types de sources juridiques francaises et europeennes."""
    JURISPRUDENCE_CASS = "jurisprudence_cass"
    JURISPRUDENCE_CA = "jurisprudence_ca"
    JURISPRUDENCE_CE = "jurisprudence_ce"
    JURISPRUDENCE_CJUE = "jurisprudence_cjue"
    JURISPRUDENCE_CEDH = "jurisprudence_cedh"
    TEXTE_LEGISLATIF = "texte_legislatif"
    TEXTE_REGLEMENTAIRE = "texte_reglementaire"
    REGLEMENT_UE = "reglement_ue"
    DIRECTIVE_UE = "directive_ue"
    RAPPORT_OFFICIEL = "rapport_officiel"
    CIRCULAIRE = "circulaire"
    AVIS_AUTORITE = "avis_autorite"
    DOCTRINE = "doctrine"
    CONVENTION_COLLECTIVE = "convention_collective"
    AUTRE = "autre"


class SourceOrigin(str, Enum):
    """Editeur ou base de donnees source."""
    LEGIFRANCE = "legifrance"
    EUR_LEX = "eur_lex"
    JUDILIBRE = "judilibre"
    HUDOC = "hudoc"
    MIN_JUSTICE = "min_justice"
    CNIL = "cnil"
    DACS = "dacs"
    AMF = "amf"
    SENAT = "senat"
    ASSEMBLEE = "assemblee_nationale"
    CONSEIL_ETAT = "conseil_etat"
    AUTRE = "autre"


# ═══════════════════════════════════════════════════════════════════════════════
# FIABILITE PAR TYPE (calibre, reproductible)
#
# Referentiel : la fiabilite est fonction de la force normative de la source.
# - Textes de loi/codes = force juridique contraignante → 95-100
# - Reglements UE = directement applicables → 95
# - Jurisprudence haute juridiction = autorite forte → 85-90
# - Directives UE = doivent etre transposees → 85
# - Rapports officiels = valeur informative forte → 75
# - Circulaires = interpretatives, non contraignantes → 65
# - Avis d'autorite = soft law → 70
# - Doctrine = analyse subjective → 60
# - Convention collective = force normative sectorielle → 80
# - Autre/inconnu → 50
# ═══════════════════════════════════════════════════════════════════════════════

_RELIABILITY_BY_TYPE = {
    SourceTypeFR.TEXTE_LEGISLATIF: 95,
    SourceTypeFR.TEXTE_REGLEMENTAIRE: 90,
    SourceTypeFR.REGLEMENT_UE: 95,
    SourceTypeFR.DIRECTIVE_UE: 85,
    SourceTypeFR.JURISPRUDENCE_CASS: 90,
    SourceTypeFR.JURISPRUDENCE_CE: 90,
    SourceTypeFR.JURISPRUDENCE_CA: 80,
    SourceTypeFR.JURISPRUDENCE_CJUE: 90,
    SourceTypeFR.JURISPRUDENCE_CEDH: 88,
    SourceTypeFR.RAPPORT_OFFICIEL: 75,
    SourceTypeFR.CIRCULAIRE: 65,
    SourceTypeFR.AVIS_AUTORITE: 70,
    SourceTypeFR.CONVENTION_COLLECTIVE: 80,
    SourceTypeFR.DOCTRINE: 60,
    SourceTypeFR.AUTRE: 50,
}


def get_reliability_for_type(source_type: SourceTypeFR) -> int:
    """Retourne le score de fiabilite (0-100) calibre par type de source."""
    return _RELIABILITY_BY_TYPE.get(source_type, 50)


# ═══════════════════════════════════════════════════════════════════════════════
# INFERENCE DU TYPE — Regex sur titre/reference/excerpt
#
# Ordre de priorite : les patterns les plus specifiques d'abord.
# CEDH est teste AVANT CJUE pour eviter le faux positif "Cour europeenne".
# ═══════════════════════════════════════════════════════════════════════════════

_TYPE_PATTERNS: list[Tuple[re.Pattern, SourceTypeFR]] = [
    # -- Jurisprudence FR --
    (re.compile(
        r"Cass\.\s*(?:soc|civ|com|crim|ass\.?\s*pl[eé]n|ch\.?\s*mixte)"
        r"|Cass\.\s*(?:1re|2e|3e)\s*civ\."
        r"|Cour\s+de\s+cassation"
        r"|Cassation"
        r"|n[°o]\s*\d{2}-\d{2}\.\d{3}",
        re.IGNORECASE,
    ), SourceTypeFR.JURISPRUDENCE_CASS),

    (re.compile(
        r"\bCE[,.\s]+(?:ass|sect)?"
        r"|Conseil\s+d[''][EÉe]tat",
        re.IGNORECASE,
    ), SourceTypeFR.JURISPRUDENCE_CE),

    (re.compile(
        r"\bCA\s+(?:de\s+)?(?:Paris|Lyon|Marseille|Bordeaux|Toulouse|Versailles|Aix)"
        r"|Cour\s+d['']appel",
        re.IGNORECASE,
    ), SourceTypeFR.JURISPRUDENCE_CA),

    # -- Jurisprudence EU (CEDH AVANT CJUE) --
    (re.compile(
        r"\bCEDH\b"
        r"|Cour\s+europ[eé]enne\s+des\s+droits"
        r"|c\.\s+France\b",
        re.IGNORECASE,
    ), SourceTypeFR.JURISPRUDENCE_CEDH),

    (re.compile(
        r"\bCJUE\b"
        r"|\bCJCE\b"
        r"|C-\d+/\d+"
        r"|Cour\s+de\s+justice\s+(?:de\s+l['']UE|de\s+l['']Union)",
        re.IGNORECASE,
    ), SourceTypeFR.JURISPRUDENCE_CJUE),

    # -- Textes UE --
    (re.compile(
        r"[Rr][eè]glement\s*\(?UE\)?\s*(?:n[°o])?\s*\d{4}/\d+"
        r"|RGPD|AI\s*Act|DSA|DMA|eIDAS|P2B",
        re.IGNORECASE,
    ), SourceTypeFR.REGLEMENT_UE),

    (re.compile(
        r"[Dd]irective\s*\(?UE\)?\s*(?:n[°o])?\s*\d{4}/\d+"
        r"|[Dd]irective\s*(?:\d{2,4}/\d+)",
        re.IGNORECASE,
    ), SourceTypeFR.DIRECTIVE_UE),

    # -- Convention collective --
    (re.compile(
        r"[Cc]onvention\s+collective"
        r"|CCN\b"
        r"|[Aa]ccord\s+(?:de\s+)?branche"
        r"|IDCC\s*\d+",
        re.IGNORECASE,
    ), SourceTypeFR.CONVENTION_COLLECTIVE),

    # -- Circulaire --
    (re.compile(
        r"[Cc]irculaire"
        r"|[Cc]irc\.\s*(?:DGFIP|DGT|DACS|DGCCRF)",
        re.IGNORECASE,
    ), SourceTypeFR.CIRCULAIRE),

    # -- Avis d'autorite --
    (re.compile(
        r"\bCNIL\b"
        r"|\bAMF\b"
        r"|\bACPR\b"
        r"|\bANSSI\b"
        r"|[Dd][eé]lib[eé]ration\s+(?:CNIL|AMF)"
        r"|[Rr]ecommandation\s+(?:CNIL|AMF|ANSSI)"
        r"|[Aa]vis\s+(?:du\s+)?(?:CNIL|AMF|ACPR|CSA|ARCEP|HADOPI|HAS)",
        re.IGNORECASE,
    ), SourceTypeFR.AVIS_AUTORITE),

    # -- Rapport officiel --
    (re.compile(
        r"[Rr]apport\s+(?:du\s+|de\s+la\s+|de\s+l[''])?(?:S[eé]nat|Assembl[eé]e|gouvernement|Cour\s+des\s+comptes|IGAS|IGF)"
        r"|[Rr][eé]ponse\s+minist[eé]rielle",
        re.IGNORECASE,
    ), SourceTypeFR.RAPPORT_OFFICIEL),

    # -- Texte reglementaire --
    (re.compile(
        r"[Dd][eé]cret\s+(?:n[°o])?\s*\d{4}"
        r"|[Aa]rr[eê]t[eé]\s+(?:du|minist[eé]riel)",
        re.IGNORECASE,
    ), SourceTypeFR.TEXTE_REGLEMENTAIRE),

    # -- Texte legislatif (le plus large, en dernier) --
    (re.compile(
        r"Art(?:icle)?\.?\s*[LRD]?\s*\d+"
        r"|[Ll]oi\s+(?:n[°o])?\s*\d{4}"
        r"|[Oo]rdonnance\s+(?:n[°o])?\s*\d{4}"
        r"|Code\s+(?:civil|du\s+travail|de\s+commerce|p[eé]nal|de\s+la\s+consommation)"
        r"|C\.\s*(?:civ|trav|com|p[eé]n|conso)\.",
        re.IGNORECASE,
    ), SourceTypeFR.TEXTE_LEGISLATIF),
]


def infer_source_type(
    title: Optional[str] = None,
    excerpt: Optional[str] = None,
    publisher: Optional[str] = None,
) -> SourceTypeFR:
    """
    Infere le SourceTypeFR a partir du titre, de l'extrait et du publisher.
    Teste titre en priorite, puis excerpt, puis publisher.
    """
    for text in (title, excerpt, publisher):
        if not text:
            continue
        for pattern, source_type in _TYPE_PATTERNS:
            if pattern.search(text):
                return source_type
    return SourceTypeFR.AUTRE


# ═══════════════════════════════════════════════════════════════════════════════
# INFERENCE DE L'ORIGINE — URL et publisher
# ═══════════════════════════════════════════════════════════════════════════════

_ORIGIN_URL_PATTERNS: list[Tuple[re.Pattern, SourceOrigin]] = [
    (re.compile(r"legifrance\.gouv\.fr", re.IGNORECASE), SourceOrigin.LEGIFRANCE),
    (re.compile(r"eur-lex\.europa\.eu", re.IGNORECASE), SourceOrigin.EUR_LEX),
    (re.compile(r"courdecassation\.fr|judilibre", re.IGNORECASE), SourceOrigin.JUDILIBRE),
    (re.compile(r"hudoc\.echr\.coe\.int", re.IGNORECASE), SourceOrigin.HUDOC),
    (re.compile(r"justice\.gouv\.fr", re.IGNORECASE), SourceOrigin.MIN_JUSTICE),
    (re.compile(r"cnil\.fr", re.IGNORECASE), SourceOrigin.CNIL),
    (re.compile(r"amf-france\.org", re.IGNORECASE), SourceOrigin.AMF),
    (re.compile(r"senat\.fr", re.IGNORECASE), SourceOrigin.SENAT),
    (re.compile(r"assemblee-nationale\.fr", re.IGNORECASE), SourceOrigin.ASSEMBLEE),
    (re.compile(r"conseil-etat\.fr", re.IGNORECASE), SourceOrigin.CONSEIL_ETAT),
]

_ORIGIN_PUBLISHER_MAP = {
    "legifrance": SourceOrigin.LEGIFRANCE,
    "eur-lex": SourceOrigin.EUR_LEX,
    "eur_lex": SourceOrigin.EUR_LEX,
    "judilibre": SourceOrigin.JUDILIBRE,
    "cour de cassation": SourceOrigin.JUDILIBRE,
    "hudoc": SourceOrigin.HUDOC,
    "cnil": SourceOrigin.CNIL,
    "amf": SourceOrigin.AMF,
    "dacs": SourceOrigin.DACS,
    "ministère de la justice": SourceOrigin.MIN_JUSTICE,
    "senat": SourceOrigin.SENAT,
    "sénat": SourceOrigin.SENAT,
    "assemblée nationale": SourceOrigin.ASSEMBLEE,
    "conseil d'état": SourceOrigin.CONSEIL_ETAT,
    "conseil d'etat": SourceOrigin.CONSEIL_ETAT,
}


def infer_source_origin(
    url: Optional[str] = None,
    publisher: Optional[str] = None,
) -> SourceOrigin:
    """
    Infere le SourceOrigin a partir de l'URL puis du publisher.
    URL est prioritaire car plus fiable que le publisher textuel.
    """
    if url:
        for pattern, origin in _ORIGIN_URL_PATTERNS:
            if pattern.search(url):
                return origin

    if publisher:
        pub_lower = publisher.lower().strip()
        for key, origin in _ORIGIN_PUBLISHER_MAP.items():
            if key in pub_lower:
                return origin

    return SourceOrigin.AUTRE


# ═══════════════════════════════════════════════════════════════════════════════
# CLASSIFICATION COMPLETE
# ═══════════════════════════════════════════════════════════════════════════════

def classify_source(
    title: Optional[str] = None,
    excerpt: Optional[str] = None,
    publisher: Optional[str] = None,
    url: Optional[str] = None,
) -> Tuple[SourceTypeFR, SourceOrigin, int]:
    """
    Classification complete d'une source juridique.

    Returns:
        (source_type_fr, origin, reliability_percent)
    """
    source_type = infer_source_type(title=title, excerpt=excerpt, publisher=publisher)
    origin = infer_source_origin(url=url, publisher=publisher)
    reliability = get_reliability_for_type(source_type)
    return source_type, origin, reliability
