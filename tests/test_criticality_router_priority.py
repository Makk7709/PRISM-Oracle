"""Tests de non-régression — priorité LEVEL 3 > LEVEL 1 (fail-closed).

Audit 2026-06-12 : la Règle 0 (bypass LEVEL 1) était évaluée AVANT la
détection LEVEL 3. Une requête critique réelle enrobée dans une formulation
simple ("explique-moi", "que signifie", "calcule", "traduis"…) était classée
LEVEL 1 et bypassait le consensus. 12/15 sondes critiques passaient sans
consensus. Doctrine Evidence : en cas de double match L1+L3, le niveau
critique DOIT gagner (fail-closed).

Symétriquement, les verbes de transaction (acheter/vendre/investir…) seuls
déclenchaient le consensus hors de tout contexte financier ("où acheter du
bon pain ?" → LEVEL 3). Ils sont désormais conditionnés au domaine
FINANCE_HIGH_RISK.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from python.helpers.criticality_router import (
    CriticalityLevel,
    CriticalityRouter,
)


@pytest.fixture
def router():
    return CriticalityRouter(is_production=True)


# ─────────────────────────────────────────────────────────────────────────────
# FAUX NÉGATIFS corrigés : requête critique réelle + formulation "simple"
# → LEVEL 3 + consensus (le match LEVEL 1 ne doit PAS l'emporter)
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("query", [
    # "explique" (L1) + cas personnel licenciement (L3)
    "Mon employeur m'a licencié hier, peux-tu expliquer mes recours ?",
    # "français" matchait le pattern traduction (L1) + "dois-je signer" (L3)
    "Dois-je signer ce contrat de travail selon le droit français ?",
    # "que signifie" (L1) + "j'ai reçu" une mise en demeure (L3)
    "Que signifie cette mise en demeure que j'ai reçue ce matin ?",
    # "résume" (L1) + assignation reçue (L3)
    "J'ai reçu une assignation au tribunal, résume-moi mes options",
    # "cherche" (L1) + "mon employeur" + poursuivre (L3)
    "Je cherche à poursuivre mon employeur aux prud'hommes",
    # "calculer" (L1) + dommages et intérêts à réclamer (L3)
    "Calculer les dommages et intérêts que je peux réclamer après mon licenciement",
    # "température" matchait météo (L1) + "mon patient" + urgences (L3)
    "Mon patient a une température de 39.5, dois-je l'envoyer aux urgences ?",
    # "la marche à suivre" matchait "ça marche" (L1) + porter plainte (L3)
    "Explique-moi la marche à suivre pour porter plainte contre mon voisin",
    # "c'est quoi" (L1) + "mes droits" cas réel (L3)
    "C'est quoi mes droits après ce licenciement abusif ?",
    # "définis" (L1) + "ma responsabilité" (L3)
    "Définis ma responsabilité pénale dans cet accident que j'ai causé",
    # "traduis" (L1) + "je dois la contester" (L3, pronom objet toléré)
    "Traduis cette clause de mon contrat et dis-moi si je dois la contester",
    # "liste" (L1) + "les recours que j'ai" (L3)
    "Liste les recours que j'ai contre mon assureur qui refuse de m'indemniser",
])
def test_critical_real_case_beats_level1_phrasing(router, query):
    assessment = router.assess(query=query, agent_profile="default")
    assert assessment.level == CriticalityLevel.LEVEL_3, (
        f"Attendu LEVEL_3 (fail-closed), obtenu {assessment.level.value} : {query}"
    )
    assert assessment.requires_consensus is True


def test_real_case_deadline_is_not_level1(router):
    """Délai de contestation d'un licenciement personnel : zone critique."""
    assessment = router.assess(
        query="Quel temps me reste-t-il pour contester mon licenciement ?",
        agent_profile="default",
    )
    assert assessment.level == CriticalityLevel.LEVEL_3
    assert assessment.requires_consensus is True


# ─────────────────────────────────────────────────────────────────────────────
# FAUX POSITIFS corrigés : verbes de transaction hors contexte financier
# → PAS de consensus
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("query", [
    "Où acheter du bon pain à Lyon ?",
    "Je veux vendre ma vieille console de jeux, quel prix ?",
    "Quel cadeau acheter pour ma mère ?",
])
def test_commerce_verbs_without_finance_context_no_consensus(router, query):
    assessment = router.assess(query=query, agent_profile="default")
    assert assessment.requires_consensus is False, (
        f"Verbe transactionnel hors contexte financier ne doit pas "
        f"déclencher le consensus : {query}"
    )


def test_commerce_verbs_with_finance_context_still_escalate(router):
    """En contexte financier détecté, les verbes de transaction restent critiques."""
    assessment = router.assess(
        query="Acheter des actions avec mon épargne retraite maintenant",
        agent_profile="default",
    )
    assert assessment.requires_consensus is True


# ─────────────────────────────────────────────────────────────────────────────
# GARDE-FOUS : les comportements voulus restent intacts
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("query", [
    "Qu'est-ce qu'un contrat synallagmatique ?",          # définition pure
    "Que signifie 'faute lourde' ?",                      # définition pure
    "Résume cet article de presse sur l'économie",        # résumé pur
    "Quelle est la météo demain à Paris ?",               # météo
    "Traduis ce paragraphe en anglais",                   # traduction pure
])
def test_pure_level1_still_bypasses_consensus(router, query):
    assessment = router.assess(query=query, agent_profile="default")
    assert assessment.level == CriticalityLevel.LEVEL_1
    assert assessment.requires_consensus is False


def test_level1_with_user_opt_in_still_gets_consensus(router):
    """L'opt-in utilisateur continue de primer sur le bypass LEVEL 1."""
    assessment = router.assess(
        query="Qu'est-ce qu'une clause pénale ? Valide par consensus.",
        agent_profile="default",
    )
    assert assessment.requires_consensus is True


def test_force_consensus_still_absolute(router):
    assessment = router.assess(
        query="Bonjour",
        agent_profile="default",
        force_consensus=True,
    )
    assert assessment.requires_consensus is True
