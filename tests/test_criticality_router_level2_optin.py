"""
Tests TDD — LEVEL 2 (analyses/comparaisons) + opt-in consensus utilisateur.

Spécification (décision produit, 2026-06-01) :

  LEVEL 1 — requête simple (définition, résumé, météo, calcul…) → JAMAIS de
            consensus, SAUF opt-in explicite de l'utilisateur.
  LEVEL 2 — zone professionnelle (analyse, comparaison, conseil) → PAS de
            consensus par défaut, MAIS l'utilisateur peut le DEMANDER dans le
            chat (opt-in) → consensus requis.
  LEVEL 3 — requête critique (cas réel, décision, litige, responsabilité,
            action critique) → consensus TOUJOURS requis.

Le router expose désormais un champ `level` (CriticalityLevel) explicite, et
détecte une demande explicite de consensus formulée par l'utilisateur.

Déterministes : aucun appel LLM. Aucune simplification d'assertion.
"""

import pytest

from python.helpers.criticality_router import (
    CriticalityRouter,
    CriticalityLevel,
    CriticalDomain,
)


@pytest.fixture
def router():
    return CriticalityRouter(is_production=False)


# ═══════════════════════════════════════════════════════════════════════════════
# 1. Le champ `level` existe et classe correctement les 3 niveaux
# ═══════════════════════════════════════════════════════════════════════════════

def test_level1_simple_definition(router):
    a = router.assess(query="Qu'est-ce qu'un contrat synallagmatique ?", agent_profile="legal_safe")
    assert a.level == CriticalityLevel.LEVEL_1
    assert a.requires_consensus is False


def test_level2_analysis_no_consensus_by_default(router):
    # Analyse/comparaison professionnelle, sans cas réel ni action critique.
    a = router.assess(
        query="Compare les avantages et inconvénients d'une SAS et d'une SARL.",
        agent_profile="default",
    )
    assert a.level == CriticalityLevel.LEVEL_2
    assert a.requires_consensus is False


def test_level3_real_case_consensus(router):
    a = router.assess(
        query="Mon employeur m'a licencié sans motif, que puis-je faire ?",
        agent_profile="legal_safe",
    )
    assert a.level == CriticalityLevel.LEVEL_3
    assert a.requires_consensus is True


# ═══════════════════════════════════════════════════════════════════════════════
# 2. Opt-in consensus utilisateur sur une requête LEVEL 2
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.parametrize("phrase", [
    "Compare la SAS et la SARL, valide par consensus.",
    "Analyse ces deux options et vérifie par consensus.",
    "Compare ces stratégies /consensus",
    "Analyse comparative des deux offres [consensus]",
    "Compare ces approches, je veux un second avis.",
    "Compare these two designs, please cross-check by consensus.",
    "Compare les deux et utilise le consensus multi-agents.",
])
def test_level2_optin_triggers_consensus(router, phrase):
    a = router.assess(query=phrase, agent_profile="default")
    assert a.requires_consensus is True, f"opt-in non détecté: {phrase!r}"
    assert a.level == CriticalityLevel.LEVEL_2


def test_optin_overrides_level1_bypass(router):
    # Une requête simple (définition) AVEC marqueur d'opt-in, et SANS verbe
    # d'action critique : l'opt-in seul doit lever le bypass LEVEL 1.
    # (NB: "valide/valider" est lui-même une CRITICAL_ACTION → LEVEL 3, donc on
    #  isole ici l'opt-in pur via le marqueur /consensus.)
    a = router.assess(
        query="C'est quoi une clause pénale ? /consensus",
        agent_profile="default",
    )
    assert a.requires_consensus is True
    assert a.level == CriticalityLevel.LEVEL_2
    assert a.consensus_opt_in is True


def test_optin_does_not_downgrade_critical_action(router):
    # Garde-fou : si la requête contient une action critique ("fais valider"),
    # elle reste LEVEL 3 même si elle contient aussi un opt-in.
    a = router.assess(
        query="C'est quoi une clause pénale ? Fais valider par consensus.",
        agent_profile="default",
    )
    assert a.requires_consensus is True
    assert a.level == CriticalityLevel.LEVEL_3
    # La criticité intrinsèque est le driver, pas l'opt-in.
    assert a.consensus_opt_in is False


def test_optin_reason_is_traced(router):
    a = router.assess(query="Compare A et B par consensus.", agent_profile="default")
    assert any("opt-in" in r.lower() or "user" in r.lower() for r in a.reasons)


# ═══════════════════════════════════════════════════════════════════════════════
# 3. Pas de faux positifs (le mot « consensus » employé descriptivement)
# ═══════════════════════════════════════════════════════════════════════════════

def test_no_false_positive_definition_about_consensus(router):
    # L'utilisateur demande la DÉFINITION du consensus, pas un consensus.
    a = router.assess(query="Qu'est-ce que le consensus scientifique ?", agent_profile="default")
    assert a.level == CriticalityLevel.LEVEL_1
    assert a.requires_consensus is False


def test_no_false_positive_medical_level2(router):
    # Question médicale professionnelle (pas cas réel, pas opt-in) → pas de consensus.
    a = router.assess(query="Quels sont les effets secondaires du paracétamol ?", agent_profile="default")
    assert a.requires_consensus is False
    assert a.domain == CriticalDomain.MEDICAL


# ═══════════════════════════════════════════════════════════════════════════════
# 4. Précédence : un override explicite du caller prime sur l'opt-in
# ═══════════════════════════════════════════════════════════════════════════════

def test_caller_force_false_suppresses_user_optin(router):
    # force_consensus=False (override debug explicite) neutralise l'opt-in user.
    a = router.assess(
        query="Compare A et B par consensus.",
        agent_profile="default",
        force_consensus=False,
    )
    assert a.requires_consensus is False


def test_caller_force_true_still_works(router):
    a = router.assess(query="Bonjour", agent_profile="default", force_consensus=True)
    assert a.requires_consensus is True


# ═══════════════════════════════════════════════════════════════════════════════
# 5. Sérialisation d'audit
# ═══════════════════════════════════════════════════════════════════════════════

def test_to_dict_contains_level(router):
    a = router.assess(query="Compare A et B.", agent_profile="default")
    d = a.to_dict()
    assert d["level"] == "LEVEL_2"


def test_level3_serialized(router):
    a = router.assess(query="Dois-je signer ce contrat ou refuser ?", agent_profile="legal_safe")
    assert a.to_dict()["level"] == "LEVEL_3"
