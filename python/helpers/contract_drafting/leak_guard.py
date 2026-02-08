"""
╔══════════════════════════════════════════════════════════════════════════════╗
║           ACT LEAK GUARD — Détection de clauses dangereuses                 ║
║                                                                              ║
║  Scanne les textes contractuels pour détecter :                             ║
║    P0 (BLOQUANT) :                                                           ║
║      - Remise / cession / transfert de code source                          ║
║      - Cession de propriété intellectuelle                                  ║
║      - Transfert de savoir-faire                                            ║
║      - Garantie "zéro risque" / "sans faille"                               ║
║      - "Conformité totale" (promesse irréaliste)                            ║
║      - Livraison de sources / repository                                    ║
║                                                                              ║
║    P1 (WARNING) :                                                            ║
║      - SLA 24/7 non encadré                                                ║
║      - Promesses de disponibilité extrême (99.999%)                         ║
║      - Garantie de résultat sans plafond                                    ║
║                                                                              ║
║  © 2026 Korev AI — Proprietary                                              ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

from __future__ import annotations

import re
from typing import Dict, List, Tuple

from python.helpers.contract_drafting.models import FindingSeverity, LeakFinding


# ═══════════════════════════════════════════════════════════════════════════════
# PATTERNS P0 — BLOQUANTS
# ═══════════════════════════════════════════════════════════════════════════════

_P0_PATTERNS: List[Tuple[re.Pattern, str, str]] = [
    # --- Code source ---
    (
        re.compile(r"remise\s+d[ue]\s+code\s+source", re.IGNORECASE),
        "remise du code source",
        "Supprimer toute clause de remise de code source — le Client obtient une licence d'usage uniquement",
    ),
    (
        re.compile(r"livr(?:aison|er?)\s+(?:du\s+)?code\s+source", re.IGNORECASE),
        "livraison du code source",
        "Remplacer par une livraison de l'exécutable uniquement",
    ),
    (
        re.compile(r"code\s+source\s+(?:sera|seront|est|remis|livré|transmis|fourni)", re.IGNORECASE),
        "code source transféré",
        "Supprimer — aucun transfert de code source autorisé",
    ),
    (
        re.compile(r"(?:accès|acces)\s+(?:au\s+)?repository\s+(?:git|svn|code)", re.IGNORECASE),
        "accès au repository de code",
        "Supprimer l'accès au repository — livraison exécutable uniquement",
    ),
    (
        re.compile(r"sources?\s+du\s+logiciel\s+(?:seront|sera|est|remis|livré)", re.IGNORECASE),
        "sources du logiciel transférées",
        "Remplacer par licence d'usage de l'exécutable",
    ),
    # --- Cession IP ---
    (
        re.compile(r"cession\s+(?:d[eu]\s+)?(?:tous\s+(?:les\s+)?)?(?:droits|propriété|code)", re.IGNORECASE),
        "cession de droits/propriété",
        "Remplacer par une licence d'usage non exclusive — aucune cession de PI — Réf: Art. L.122-6 CPI",
    ),
    # --- Savoir-faire ---
    (
        re.compile(r"(?:transfert|transmet(?:tre)?|livraison|transmission)\s+(?:\w+\s+)?(?:d[eu]?\s+)?(?:son\s+)?savoir[- ]faire", re.IGNORECASE),
        "transfert de savoir-faire",
        "Supprimer — le savoir-faire reste propriété exclusive de l'Éditeur",
    ),
    # --- Garanties absolues ---
    (
        re.compile(r"(?:garantie?\s+)?z[ée]ro\s+risque", re.IGNORECASE),
        "garantie zéro risque",
        "Remplacer par une obligation de moyens avec plafond de responsabilité",
    ),
    (
        re.compile(r"sans\s+(?:aucune?\s+)?faille", re.IGNORECASE),
        "garantie sans faille",
        "Aucun logiciel ne peut être garanti sans faille — utiliser une obligation de moyens",
    ),
    (
        re.compile(r"conformit[ée]\s+totale", re.IGNORECASE),
        "conformité totale",
        "Remplacer par 'conformité raisonnable' ou 'meilleurs efforts de conformité'",
    ),
    (
        re.compile(r"z[ée]ro\s+(?:bug|erreur|interruption|défaut)", re.IGNORECASE),
        "garantie zéro défaut",
        "Aucune garantie zéro bug n'est réaliste — utiliser une obligation de moyens",
    ),
    # --- Accès au dépôt de code ---
    (
        re.compile(r"(?:accès|acces)\s+(?:au\s+)?d[ée]p[oô]t\s+(?:de\s+)?code", re.IGNORECASE),
        "accès au dépôt de code",
        "Supprimer — le dépôt de code est propriété exclusive de l'Éditeur",
    ),
    # --- Garantit la conformité (absolue) ---
    (
        re.compile(r"garantit?\s+la\s+conformit[ée]", re.IGNORECASE),
        "garantie absolue de conformité",
        "Remplacer par 'meilleurs efforts de conformité' ou 'obligation de moyens' — Réf: art. 1231-1 C. civ.",
    ),
    # --- Transfert/cession irrévocable de droits ---
    (
        re.compile(r"(?:transf[ée]r[ée]s?|c[ée]d[ée]s?|transmis)\s+(?:\w+\s+)*?(?:de\s+manière\s+)?irr[ée]vocable", re.IGNORECASE),
        "transfert irrévocable de droits",
        "Supprimer — la licence d'usage est révocable et non cessible",
    ),
    # --- Accès libre/illimité aux systèmes ---
    # NOTE: exclude negations like "aucun accès permanent" which is a protective clause
    (
        re.compile(r"acc[èe]de\s+librement|(?<!aucun\s)accès\s+(?:libre|illimité|sans\s+restriction)", re.IGNORECASE),
        "accès libre/illimité aux systèmes",
        "Encadrer l'accès : autorisation écrite préalable, session limitée, journalisation — Réf: Annexe 3 Sécurité",
    ),
    # --- Escrow / dépôt de code chez tiers ---
    (
        re.compile(r"(?:escrow|d[ée]p[oô]t)\s+(?:du\s+)?code\s+(?:source\s+)?(?:chez|auprès)", re.IGNORECASE),
        "dépôt/escrow de code source chez tiers",
        "L'escrow de code source doit être approuvé explicitement — ne pas inclure par défaut",
    ),
]


# ═══════════════════════════════════════════════════════════════════════════════
# PATTERNS P1 — WARNINGS
# ═══════════════════════════════════════════════════════════════════════════════

_P1_PATTERNS: List[Tuple[re.Pattern, str, str]] = [
    # --- SLA irréaliste ---
    (
        re.compile(r"24\s*[h/]\s*24|24\s*heures?\s*sur\s*24|7\s*[j/]\s*7|24h/24|7j/7|24/7", re.IGNORECASE),
        "SLA 24/7 non encadré",
        "Préciser les conditions et limites du support 24/7 ou réduire aux jours ouvrés",
    ),
    (
        re.compile(r"99[.,]99(?:9+)?\s*%", re.IGNORECASE),
        "disponibilité 99.99%+ promise",
        "En ON-PREM, la disponibilité dépend de l'infrastructure Client — limiter à l'engagement de l'Éditeur",
    ),
    (
        re.compile(r"garantie?\s+de\s+r[ée]sultat", re.IGNORECASE),
        "garantie de résultat",
        "Préférer une obligation de moyens avec plafond de responsabilité",
    ),
    # --- Obligation de résultat implicite ---
    (
        re.compile(r"obligation\s+de\s+r[ée]sultat", re.IGNORECASE),
        "obligation de résultat implicite",
        "Remplacer par obligation de moyens sauf si expressément convenu — Réf: art. 1231-1 C. civ.",
    ),
    # --- SLA 99.9% garanti ---
    (
        re.compile(r"(?:disponibilit[ée]\s+)?(?:garanti[eé]?\s+(?:de\s+)?)?99[.,]9\s*%|99[.,]9\s*%\s*(?:garanti|assur[eé])", re.IGNORECASE),
        "SLA 99.9% garanti sans moyens",
        "En ON-PREM, la disponibilité dépend de l'infra Client — limiter à l'obligation de moyens côté Éditeur",
    ),
    # --- RGPD sans rôle clair ---
    (
        re.compile(r"(?:traite|traitement)\s+(?:les\s+|des\s+)?donn[ée]es\s+(?:personnelles\s+)?du\s+Client", re.IGNORECASE),
        "traitement de données sans rôle RGPD explicite",
        "Préciser le rôle (responsable / sous-traitant) et activer l'Annexe 4 (DPA art. 28 RGPD)",
    ),
    # --- Indexation ambiguë ---
    (
        re.compile(r"r[ée]vis[ée]s?\s+(?:annuellement|chaque\s+ann[ée]e)\s+(?:selon|en\s+fonction\s+de)\s+(?:l['\u2019]?[ée]volution|les?\s+co[ûu]ts?)", re.IGNORECASE),
        "indexation ambiguë (pas d'indice précis)",
        "Préciser un indice : Syntec, IPC, ou autre référence chiffrée — Réf: art. 1164 C. civ.",
    ),
    # --- Pénalités illimitées ---
    (
        re.compile(r"p[ée]nalit[ée]s?\s+(?:illimit[ée]es?|sans\s+(?:plafond|limite))", re.IGNORECASE),
        "pénalités sans plafond",
        "Plafonner les pénalités (ex: 10-15% du montant annuel) — Réf: art. 1231-5 C. civ.",
    ),
    # --- Responsabilité illimitée ---
    (
        re.compile(r"responsabilit[ée]\s+(?:illimit[ée]e|sans\s+(?:plafond|limite)|totale)", re.IGNORECASE),
        "responsabilité sans plafond",
        "Plafonner la responsabilité (montant payé sur 12 mois) — Réf: art. 1170, 1231-5 C. civ.",
    ),
]


# ═══════════════════════════════════════════════════════════════════════════════
# SCAN FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════════

def scan_for_leaks(text: str, section: str = "UNKNOWN") -> List[LeakFinding]:
    """Scanne un texte pour détecter des clauses dangereuses.
    
    Args:
        text:    Le texte contractuel à scanner
        section: Le nom de la section (pour traçabilité)
    
    Returns:
        Liste de LeakFinding (P0, P1, P2)
    """
    findings: List[LeakFinding] = []
    
    # Scan P0 (bloquants)
    for pattern, name, recommendation in _P0_PATTERNS:
        for match in pattern.finditer(text):
            # Extraire le contexte (50 chars avant/après)
            start = max(0, match.start() - 50)
            end = min(len(text), match.end() + 50)
            context = text[start:end].strip()
            findings.append(LeakFinding(
                severity=FindingSeverity.P0,
                pattern=name,
                context=context,
                recommendation=recommendation,
                section=section,
            ))
    
    # Scan P1 (warnings)
    for pattern, name, recommendation in _P1_PATTERNS:
        for match in pattern.finditer(text):
            start = max(0, match.start() - 50)
            end = min(len(text), match.end() + 50)
            context = text[start:end].strip()
            findings.append(LeakFinding(
                severity=FindingSeverity.P1,
                pattern=name,
                context=context,
                recommendation=recommendation,
                section=section,
            ))
    
    return findings


def scan_for_leaks_by_section(sections: Dict[str, str]) -> List[LeakFinding]:
    """Scanne toutes les sections d'un contrat.
    
    Args:
        sections: Dict section_name → texte
    
    Returns:
        Liste consolidée de LeakFinding avec section identifiée
    """
    all_findings: List[LeakFinding] = []
    for section_name, section_text in sections.items():
        findings = scan_for_leaks(section_text, section=section_name)
        all_findings.extend(findings)
    return all_findings
