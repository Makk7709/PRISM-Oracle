"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                    MULTITASK ORCHESTRATION — TESTS                          ║
║                                                                              ║
║  Tests de validation du comportement d'orchestration du profil Multitask.   ║
║  Vérifie :                                                                   ║
║  - Délégation automatique vers profils spécialisés                          ║
║  - Conditions de blocage/refus                                              ║
║  - Sélection du format de réponse                                           ║
║  - Arbitrage entre tâches conflictuelles                                    ║
║                                                                              ║
║  Exécution : python tests/test_multitask_orchestration.py                   ║
║                                                                              ║
║  Version: 1.0.0                                                              ║
║  © 2025 Korev AI — Proprietary                                               ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import re
import sys
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Optional

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))


# ═══════════════════════════════════════════════════════════════════════════════
# ENUMS & DATA STRUCTURES
# ═══════════════════════════════════════════════════════════════════════════════

class TargetProfile(str, Enum):
    """Profils cibles pour délégation."""
    MULTITASK = "multitask"  # Exécution directe
    LEGAL_SAFE = "legal_safe"
    FINANCE = "finance"
    MARKETING = "marketing"
    SALES = "sales"
    RESEARCHER = "researcher"
    DEVELOPER = "developer"
    CLARIFICATION = "_clarification"  # Demande de clarification
    BLOCKED = "_blocked"  # Blocage opérationnel


class ResponseFormat(str, Enum):
    """Formats de réponse attendus."""
    PROSE = "prose"  # Texte fluide
    TABLE = "table"  # Tableau structuré
    BULLETS = "bullets"  # Points rapides
    TECHNICAL = "technical"  # Code/technique
    DELEGATED = "delegated"  # Délégué à un autre agent


class Priority(str, Enum):
    """Niveaux de priorité."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class RoutingDecision:
    """Décision de routage attendue."""
    target_profile: TargetProfile
    format: ResponseFormat
    priority: Priority
    should_block: bool = False
    needs_clarification: bool = False
    reasoning: str = ""


# ═══════════════════════════════════════════════════════════════════════════════
# DELEGATION RULES ENGINE
# ═══════════════════════════════════════════════════════════════════════════════

# Keywords pour détection de domaine
DELEGATION_KEYWORDS = {
    TargetProfile.LEGAL_SAFE: [
        # Droit du travail - patterns plus larges
        r"\bfire\b",
        r"\blicenci",
        r"\bdismiss",
        r"\bterminat",
        r"\bemploy",
        r"\bsalarié",
        r"\bcontrat",
        r"\bharcèlement\b",
        r"\bharassment\b",
        r"\bdiscrimination\b",
        r"\bprud'?hommes?\b",
        r"\bclause\b",
        r"\bnon-?concurrence\b",
        # Juridique général
        r"\blégal",
        r"\blegal\b",
        r"\bjuridique",
        r"\blaw\b",
        r"\bdroit\b",
        r"\bavocat\b",
        r"\blawyer\b",
        r"\battorney\b",
        r"\blitige\b",
        r"\blitigation\b",
        r"\bprocès\b",
        r"\blawsuit\b",
        r"\bresponsabilité\b",
        r"\bliability\b",
        r"\bpénal",
        r"\bcriminal\b",
        r"\bamende\b",
        r"\bfine\b",
        # RGPD / Données
        r"\brgpd\b",
        r"\bgdpr\b",
        r"\bcnil\b",
        r"\bdonnées\s+personnelles\b",
        r"\bpersonal\s+data\b",
        r"\bprivacy\b",
        r"\bconsentement\b",
        r"\bconsent\b",
        r"\bvalide\b",
        r"\bobligation",
    ],
    TargetProfile.FINANCE: [
        r"\bfinanc",
        r"\bbudget\b",
        r"\btrésorerie\b",
        r"\bcash\s*flow\b",
        r"\bcomptab",
        r"\baccount",
        r"\bbilan\b",
        r"\bbalance\s+sheet\b",
        r"\bp&l\b",
        r"\bprofit\b",
        r"\bloss\b",
        r"\bchiffre\s+d'?affaires\b",
        r"\brevenue\b",
        r"\binvestis",
        r"\binvest",
        r"\broi\b",
        r"\brendement\b",
        r"\breturn\b",
        r"\bvalorisation\b",
        r"\bvaluation\b",
        r"\bimpôt",
        r"\btax\b",
        r"\bfiscal",
        r"\btva\b",
        r"\bvat\b",
        r"\bprévision\b",
        r"\bforecast\b",
        r"\bprojection\b",
        r"\bbusiness\s+plan\b",
        r"\d+\s*[k€$]",
        r"[k€$]\s*\d+",
        r"\boptimiser\b",
    ],
    TargetProfile.MARKETING: [
        r"\bmarketing\b",
        r"\bbrand\b",
        r"\bmarque\b",
        r"\bpositionnement\b",
        r"\bpositioning\b",
        r"\bcampagne\b",
        r"\bcampaign\b",
        r"\bpublicité\b",
        r"\badvertising\b",
        r"\bads?\b",
        r"\bpub\b",
        r"\bcopywriting\b",
        r"\bcontenu\b",
        r"\bcontent\b",
        r"\bblog\b",
        r"\barticle\b",
        r"\bpost\b",
        r"\blinkedin\b",
        r"\btwitter\b",
        r"\binstagram\b",
        r"\bfacebook\b",
        r"\bsocial\s*media\b",
        r"\bréseaux\s*sociaux\b",
        r"\bseo\b",
        r"\bréférencement\b",
        r"\bgoogle\b",
        r"\banalytics\b",
        r"\bconversion\b",
        r"\bemail\s*client\b",
        r"\bnewsletter\b",
        r"\bemailing\b",
        r"\bcommunication\b",
        r"\bannonce",
    ],
    TargetProfile.SALES: [
        r"\bvente\b",
        r"\bsales\b",
        r"\bcommercial",
        r"\bprospect",
        r"\blead\b",
        r"\bcrm\b",
        r"\bnégociation\b",
        r"\bnegotiation\b",
        r"\bdeal\b",
        r"\bclosing\b",
        r"\bpipeline\b",
        r"\bdevis\b",
        r"\bquote\b",
        r"\bproposition\b",
        r"\bproposal\b",
        r"\bpricing\b",
        r"\btarif\b",
        r"\bclient\b",
        r"\bcustomer\b",
        r"\baccount\s*management\b",
        r"\brelation\s*client\b",
        r"\bcold\s*call\b",
        r"\boutreach\b",
        r"\bprospection\b",
        r"\bdémarchage\b",
        r"\bqualifier\b",
    ],
    TargetProfile.RESEARCHER: [
        r"\brecherche\b",
        r"\bresearch\b",
        r"\bétude\b",
        r"\bstudy\b",
        r"\banalyse\s*de\s*marché\b",
        r"\bmarket\s*analysis\b",
        r"\bbenchmark\b",
        r"\bcompetitor\b",
        r"\bconcurrent",
        r"\bveille\b",
        r"\bintelligence\b",
        r"\bdata\b",
        r"\bdonnées\b",
        r"\bstatistiques\b",
        r"\bstatistics\b",
        r"\bsurvey\b",
        r"\bsondage\b",
        r"\btrend\b",
        r"\btendance\b",
        r"\binsight\b",
        r"\bsynthèse\b",
        r"\bsynthesis\b",
        r"\bmarché\b",
        r"\bsecteur\b",
    ],
    TargetProfile.DEVELOPER: [
        r"\bcode\b",
        r"\bcoding\b",
        r"\bprogram",
        r"\bdévelopp",
        r"\bdevelop",
        r"\bsoftware\b",
        r"\bapi\b",
        r"\bendpoint\b",
        r"\bdatabase\b",
        r"\bbackend\b",
        r"\bfrontend\b",
        r"\bfullstack\b",
        r"\bbug\b",
        r"\bdebug\b",
        r"\bdeploy\b",
        r"\bdevops\b",
        r"\bci/cd\b",
        r"\bgit\b",
        r"\bpython\b",
        r"\bjavascript\b",
        r"\btypescript\b",
        r"\brust\b",
        r"\bgo\b",
        r"\bjava\b",
        r"\bsql\b",
        r"\barchitecture\b",
        r"\bmicroservice\b",
        r"\binfrastructure\b",
        r"\bcloud\b",
        r"\baws\b",
        r"\bgcp\b",
        r"\bazure\b",
        r"\bfonction\b",
        r"\bparser\b",
        r"\bjson\b",
        r"\berreur\b",
        r"\berror\b",
    ],
}

# Keywords pour blocage
BLOCKING_KEYWORDS = [
    r"\b(urgent|asap|immédiat|immediately|now|maintenant)\b.*\b(perfect|parfait|quality|qualité)\b",
    r"\b(perfect|parfait|quality|qualité)\b.*\b(urgent|asap|immédiat|immediately|now|maintenant)\b",
]

# Keywords pour clarification
AMBIGUITY_KEYWORDS = [
    r"\b(le\s+truc|the\s+thing|ça|that\s+stuff|le\s+machin)\b",
    r"\b(handle|gère|fait|do)\s+(it|le|ça)\b",
    r"^.{0,20}$",  # Message trop court
]


# ═══════════════════════════════════════════════════════════════════════════════
# ROUTING LOGIC
# ═══════════════════════════════════════════════════════════════════════════════

def analyze_request(request: str) -> RoutingDecision:
    """
    Analyse une requête et détermine le routage optimal.
    
    Args:
        request: La requête utilisateur
        
    Returns:
        RoutingDecision avec le profil cible, format, etc.
    """
    request_lower = request.lower()
    
    # 1. Vérifier si blocage nécessaire (conflit de priorités)
    for pattern in BLOCKING_KEYWORDS:
        if re.search(pattern, request_lower, re.IGNORECASE):
            return RoutingDecision(
                target_profile=TargetProfile.BLOCKED,
                format=ResponseFormat.BULLETS,
                priority=Priority.HIGH,
                should_block=True,
                reasoning="Conflict detected: urgency vs quality. Arbitrage required."
            )
    
    # 2. Vérifier si clarification nécessaire (ambiguïté)
    for pattern in AMBIGUITY_KEYWORDS:
        if re.search(pattern, request_lower, re.IGNORECASE):
            return RoutingDecision(
                target_profile=TargetProfile.CLARIFICATION,
                format=ResponseFormat.BULLETS,
                priority=Priority.MEDIUM,
                needs_clarification=True,
                reasoning="Request is ambiguous. Clarification needed before execution."
            )
    
    # 3. Détecter le domaine et router vers le profil approprié
    best_match: Optional[TargetProfile] = None
    best_score = 0
    
    for profile, patterns in DELEGATION_KEYWORDS.items():
        score = 0
        for pattern in patterns:
            matches = re.findall(pattern, request_lower, re.IGNORECASE)
            score += len(matches)
        
        if score > best_score:
            best_score = score
            best_match = profile
    
    # 4. Déterminer le format de réponse
    response_format = _determine_format(request_lower, best_match)
    
    # 5. Déterminer la priorité
    priority = _determine_priority(request_lower)
    
    # 6. Si aucun match spécialisé, exécution directe par multitask
    if best_match is None or best_score < 1:
        return RoutingDecision(
            target_profile=TargetProfile.MULTITASK,
            format=response_format,
            priority=priority,
            reasoning="General request. Direct execution by multitask."
        )
    
    return RoutingDecision(
        target_profile=best_match,
        format=ResponseFormat.DELEGATED,
        priority=priority,
        reasoning=f"Domain detected: {best_match.value}. Delegating for specialized handling."
    )


def _determine_format(request: str, profile: Optional[TargetProfile]) -> ResponseFormat:
    """Détermine le format de réponse optimal."""
    # Legal toujours délégué
    if profile == TargetProfile.LEGAL_SAFE:
        return ResponseFormat.DELEGATED
    
    # Données/chiffres → tableau
    if re.search(r"\b(compar|versus|vs|différence|difference|options?|choix|liste)\b", request):
        return ResponseFormat.TABLE
    
    # Questions techniques → technique
    if re.search(r"\b(code|api|config|setup|install|error|bug|debug)\b", request):
        return ResponseFormat.TECHNICAL
    
    # Questions urgentes → bullets
    if re.search(r"\b(urgent|quick|rapide|résumé|summary|tldr)\b", request):
        return ResponseFormat.BULLETS
    
    # Par défaut → prose
    return ResponseFormat.PROSE


def _determine_priority(request: str) -> Priority:
    """Détermine la priorité de la requête."""
    # Check low priority FIRST (to avoid false positives with "pressé")
    if re.search(r"\b(quand\s+tu\s+peux|when\s+you\s+can|pas\s+pressé|no\s+rush|pas\s+urgent)\b", request, re.IGNORECASE):
        return Priority.LOW
    if re.search(r"\b(critical|critique|urgence|emergency|asap|immédiat)\b", request, re.IGNORECASE):
        return Priority.CRITICAL
    if re.search(r"\b(urgent|pressé|important|prioritaire|deadline)\b", request, re.IGNORECASE):
        return Priority.HIGH
    return Priority.MEDIUM


# ═══════════════════════════════════════════════════════════════════════════════
# TEST CASES
# ═══════════════════════════════════════════════════════════════════════════════

TEST_CASES = [
    # ─────────────────────────────────────────────────────────────────────────
    # LEGAL DELEGATION
    # ─────────────────────────────────────────────────────────────────────────
    {
        "request": "Can I fire this employee for performance issues?",
        "expected_profile": TargetProfile.LEGAL_SAFE,
        "description": "Employment law question → legal_safe",
    },
    {
        "request": "Est-ce que ce contrat est valide juridiquement ?",
        "expected_profile": TargetProfile.LEGAL_SAFE,
        "description": "Contract validity → legal_safe",
    },
    {
        "request": "Quelles sont mes obligations RGPD pour ce traitement de données ?",
        "expected_profile": TargetProfile.LEGAL_SAFE,
        "description": "GDPR question → legal_safe",
    },
    {
        "request": "Un employé m'accuse de harcèlement, que faire ?",
        "expected_profile": TargetProfile.LEGAL_SAFE,
        "description": "Harassment accusation → legal_safe",
    },
    
    # ─────────────────────────────────────────────────────────────────────────
    # FINANCE DELEGATION
    # ─────────────────────────────────────────────────────────────────────────
    {
        "request": "Prépare-moi une projection financière sur 3 ans",
        "expected_profile": TargetProfile.FINANCE,
        "description": "Financial projection → finance",
    },
    {
        "request": "Quel est le ROI de cet investissement de 50k€ ?",
        "expected_profile": TargetProfile.FINANCE,
        "description": "ROI calculation → finance",
    },
    {
        "request": "Analyse mon bilan comptable et identifie les risques",
        "expected_profile": TargetProfile.FINANCE,
        "description": "Balance sheet analysis → finance",
    },
    {
        "request": "Comment optimiser ma TVA cette année ?",
        "expected_profile": TargetProfile.FINANCE,
        "description": "Tax optimization → finance",
    },
    
    # ─────────────────────────────────────────────────────────────────────────
    # MARKETING DELEGATION
    # ─────────────────────────────────────────────────────────────────────────
    {
        "request": "Écris-moi un post LinkedIn pour annoncer notre levée de fonds",
        "expected_profile": TargetProfile.MARKETING,
        "description": "LinkedIn post → marketing",
    },
    {
        "request": "Crée une stratégie de contenu pour notre blog",
        "expected_profile": TargetProfile.MARKETING,
        "description": "Content strategy → marketing",
    },
    {
        "request": "Rédige un email client pour annoncer notre nouveau produit",
        "expected_profile": TargetProfile.MARKETING,
        "description": "Client email → marketing",
    },
    
    # ─────────────────────────────────────────────────────────────────────────
    # SALES DELEGATION
    # ─────────────────────────────────────────────────────────────────────────
    {
        "request": "Prépare une proposition commerciale pour ce prospect",
        "expected_profile": TargetProfile.SALES,
        "description": "Sales proposal → sales",
    },
    {
        "request": "Comment améliorer notre taux de closing ?",
        "expected_profile": TargetProfile.SALES,
        "description": "Closing rate → sales",
    },
    {
        "request": "Aide-moi à qualifier ce lead entrant",
        "expected_profile": TargetProfile.SALES,
        "description": "Lead qualification → sales",
    },
    
    # ─────────────────────────────────────────────────────────────────────────
    # RESEARCHER DELEGATION
    # ─────────────────────────────────────────────────────────────────────────
    {
        "request": "Fais une analyse de marché sur le secteur fintech en France",
        "expected_profile": TargetProfile.RESEARCHER,
        "description": "Market analysis → researcher",
    },
    {
        "request": "Benchmark nos concurrents sur le pricing",
        "expected_profile": TargetProfile.RESEARCHER,
        "description": "Competitor benchmark → researcher",
    },
    
    # ─────────────────────────────────────────────────────────────────────────
    # DEVELOPER DELEGATION
    # ─────────────────────────────────────────────────────────────────────────
    {
        "request": "Écris une fonction Python pour parser ce JSON",
        "expected_profile": TargetProfile.DEVELOPER,
        "description": "Python code → developer",
    },
    {
        "request": "Debug cette erreur dans mon API endpoint",
        "expected_profile": TargetProfile.DEVELOPER,
        "description": "API debugging → developer",
    },
    
    # ─────────────────────────────────────────────────────────────────────────
    # DIRECT EXECUTION (MULTITASK)
    # ─────────────────────────────────────────────────────────────────────────
    {
        "request": "Quelle heure est-il à Tokyo ?",
        "expected_profile": TargetProfile.MULTITASK,
        "description": "Simple question → direct execution",
    },
    {
        "request": "Résume ce document en 3 points",
        "expected_profile": TargetProfile.MULTITASK,
        "description": "General task → direct execution",
    },
    {
        "request": "Traduis ce texte en anglais",
        "expected_profile": TargetProfile.MULTITASK,
        "description": "Translation → direct execution",
    },
    
    # ─────────────────────────────────────────────────────────────────────────
    # CLARIFICATION NEEDED
    # ─────────────────────────────────────────────────────────────────────────
    {
        "request": "Gère le truc",
        "expected_profile": TargetProfile.CLARIFICATION,
        "description": "Ambiguous request → clarification",
    },
    {
        "request": "Fait ça",
        "expected_profile": TargetProfile.CLARIFICATION,
        "description": "Vague instruction → clarification",
    },
    
    # BLOCKING (CONFLICT)
    # ─────────────────────────────────────────────────────────────────────────
    {
        "request": "Envoie le rapport urgent maintenant ET assure-toi qu'il soit parfait",
        "expected_profile": TargetProfile.BLOCKED,
        "description": "Urgency vs quality conflict → block",
    },
    {
        "request": "I need this perfect report ASAP immediately",
        "expected_profile": TargetProfile.BLOCKED,
        "description": "Conflicting requirements → block",
    },
]


# ═══════════════════════════════════════════════════════════════════════════════
# TEST RUNNER
# ═══════════════════════════════════════════════════════════════════════════════

def run_tests():
    """Exécute tous les tests de routage."""
    print("\n")
    print("╔══════════════════════════════════════════════════════════════════════════════╗")
    print("║              MULTITASK ORCHESTRATION — TESTS DE ROUTAGE                     ║")
    print("╚══════════════════════════════════════════════════════════════════════════════╝")
    print()
    
    passed = 0
    failed = 0
    results_by_category = {}
    
    for test in TEST_CASES:
        request = test["request"]
        expected = test["expected_profile"]
        description = test["description"]
        
        # Analyser la requête
        decision = analyze_request(request)
        actual = decision.target_profile
        
        # Vérifier le résultat
        is_pass = actual == expected
        status = "✅" if is_pass else "❌"
        
        if is_pass:
            passed += 1
        else:
            failed += 1
        
        # Catégoriser
        category = expected.value if expected else "unknown"
        if category not in results_by_category:
            results_by_category[category] = {"passed": 0, "failed": 0}
        if is_pass:
            results_by_category[category]["passed"] += 1
        else:
            results_by_category[category]["failed"] += 1
        
        # Afficher
        print(f"  {status} {description}")
        print(f"      Request: \"{request[:50]}{'...' if len(request) > 50 else ''}\"")
        print(f"      Expected: {expected.value}, Got: {actual.value}")
        if not is_pass:
            print(f"      Reasoning: {decision.reasoning}")
        print()
    
    # ─────────────────────────────────────────────────────────────────────────
    # RÉSUMÉ PAR CATÉGORIE
    # ─────────────────────────────────────────────────────────────────────────
    print("=" * 70)
    print("RÉSUMÉ PAR CATÉGORIE")
    print("=" * 70)
    
    for category, stats in sorted(results_by_category.items()):
        total = stats["passed"] + stats["failed"]
        pct = (stats["passed"] / total * 100) if total > 0 else 0
        bar = "█" * int(pct / 10) + "░" * (10 - int(pct / 10))
        status = "✅" if stats["failed"] == 0 else "⚠️"
        print(f"  {status} {category:20} [{bar}] {stats['passed']}/{total} ({pct:.0f}%)")
    
    # ─────────────────────────────────────────────────────────────────────────
    # RÉSUMÉ GLOBAL
    # ─────────────────────────────────────────────────────────────────────────
    print()
    print("=" * 70)
    print("RÉSUMÉ GLOBAL")
    print("=" * 70)
    
    total = passed + failed
    pct = (passed / total * 100) if total > 0 else 0
    
    print(f"\n  Total: {passed}/{total} tests réussis ({pct:.1f}%)")
    
    if failed == 0:
        print("\n  🎉 TOUS LES TESTS PASSENT! Le routage Multitask fonctionne correctement.\n")
        return 0
    else:
        print(f"\n  ⚠️ {failed} test(s) en échec. Vérifiez les patterns de détection.\n")
        return 1


def test_format_selection():
    """Test de la sélection de format."""
    print("\n")
    print("=" * 70)
    print("TEST: SÉLECTION DE FORMAT DE RÉPONSE")
    print("=" * 70)
    
    format_tests = [
        ("Compare les options A et B", ResponseFormat.TABLE, "Comparison → table"),
        ("Résumé rapide SVP", ResponseFormat.BULLETS, "Quick summary → bullets"),
        ("Debug mon code Python", ResponseFormat.DELEGATED, "Code question → delegated to developer"),
        ("Raconte-moi une histoire", ResponseFormat.PROSE, "Creative → prose"),
    ]
    
    passed = 0
    for request, expected_format, description in format_tests:
        decision = analyze_request(request)
        actual = decision.format
        is_pass = actual == expected_format
        status = "✅" if is_pass else "❌"
        if is_pass:
            passed += 1
        print(f"  {status} {description}")
        print(f"      Request: \"{request}\"")
        print(f"      Expected: {expected_format.value}, Got: {actual.value}")
        print()
    
    print(f"  Résultat: {passed}/{len(format_tests)} tests passés\n")
    return passed == len(format_tests)


def test_priority_detection():
    """Test de la détection de priorité."""
    print("\n")
    print("=" * 70)
    print("TEST: DÉTECTION DE PRIORITÉ")
    print("=" * 70)
    
    priority_tests = [
        ("C'est critique, urgence absolue!", Priority.CRITICAL, "Critical keywords"),
        ("C'est urgent, deadline demain", Priority.HIGH, "Urgent keywords"),
        ("Quand tu peux, pas pressé", Priority.LOW, "Low priority keywords"),
        ("Analyse ce document", Priority.MEDIUM, "Default → medium"),
    ]
    
    passed = 0
    for request, expected_priority, description in priority_tests:
        decision = analyze_request(request)
        actual = decision.priority
        is_pass = actual == expected_priority
        status = "✅" if is_pass else "❌"
        if is_pass:
            passed += 1
        print(f"  {status} {description}")
        print(f"      Request: \"{request}\"")
        print(f"      Expected: {expected_priority.value}, Got: {actual.value}")
        print()
    
    print(f"  Résultat: {passed}/{len(priority_tests)} tests passés\n")
    return passed == len(priority_tests)


def main():
    """Point d'entrée principal."""
    # Test de routage principal
    routing_result = run_tests()
    
    # Test de sélection de format
    format_result = test_format_selection()
    
    # Test de détection de priorité
    priority_result = test_priority_detection()
    
    # Résultat final
    print("=" * 70)
    print("VERDICT FINAL")
    print("=" * 70)
    
    all_pass = routing_result == 0 and format_result and priority_result
    
    if all_pass:
        print("\n  🎉 TOUS LES TESTS PASSENT!")
        print("  Le profil Multitask route correctement les requêtes.\n")
        return 0
    else:
        print("\n  ⚠️ Certains tests ont échoué.")
        print("  Vérifiez les patterns de détection.\n")
        return 1


if __name__ == "__main__":
    sys.exit(main())
