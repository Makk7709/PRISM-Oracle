"""
DEF-CDG-2 regression test (audit hostile 29 mai 2026).

Garantit que validate_final_output ne peut PAS etre contourne par
reformulation de l'output. Si la query d'origine etait critique (LEVEL 3),
le gate doit continuer a exiger un consensus, MEME si l'output est
reformule sans keywords critiques.

Le defaut originel : `validate_final_output` re-classifie la criticite sur
`output[:1000]` au lieu de la query d'origine. Un output formule en
langage doux ("various factors merit consideration") retombe sur LEVEL 1
default et passe le gate sans consensus, alors que la query originale
("Should I sign this employment contract?") exigeait un consensus.

Mitigation : le parametre `original_query` permet de rejouer la
classification sur la query initiale. C'est le caller (agent.py, etc.) qui
DOIT le fournir pour assurer la non-bypassabilite.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from python.helpers.critical_decision_gate import (
    CriticalDecisionGate,
    GateDecision,
)


@pytest.mark.asyncio
async def test_validate_final_output_with_original_query_blocks_bypass():
    """
    Query critique + output reformule sans keywords critiques + sans
    consensus_result => doit FAIL_CLOSED quand original_query est fourni.
    """
    gate = CriticalDecisionGate()
    
    critical_query = "Should I sign this employment contract?"
    reformulated_output = (
        "Various factors merit consideration regarding the proposed agreement. "
        "The arrangement appears to be standard in nature and reflects typical "
        "industry practice."
    )
    
    result = await gate.validate_final_output(
        output=reformulated_output,
        agent_profile="legal_safe",
        consensus_result=None,
        original_query=critical_query,
    )
    
    assert result.decision == GateDecision.FAIL_CLOSED, (
        f"DEF-CDG-2: gate a laisse passer un output reformule sans consensus "
        f"alors que la query d'origine etait critique. decision={result.decision}"
    )
    assert result.can_emit is False
    assert result.consensus_required is True


@pytest.mark.asyncio
async def test_validate_final_output_without_original_query_falls_back_to_output():
    """
    Sans original_query, le comportement legacy est conserve (rétro-compat) :
    classification sur output[:1000]. Documente la limite.
    """
    gate = CriticalDecisionGate()
    
    reformulated_output = (
        "Various factors merit consideration regarding the proposed agreement."
    )
    
    result = await gate.validate_final_output(
        output=reformulated_output,
        agent_profile="legal_safe",
        consensus_result=None,
    )
    
    assert result.decision == GateDecision.ALLOW, (
        "Sans original_query, le gate retombe sur output → LEVEL 1 default "
        "→ pas de consensus requis. Comportement legacy attendu."
    )


@pytest.mark.asyncio
async def test_validate_final_output_check1_passes_with_consensus_approved():
    """
    Query critique + output reformule + consensus_result approuve =>
    le CHECK 1 (consensus requis) doit PASSER. Les checks suivants
    (strict_evidence, claim sourcing) peuvent encore fail-closer selon
    le evidence_pack fourni ; ce test isole la verification du CHECK 1.
    """
    gate = CriticalDecisionGate()
    
    critical_query = "Should I sign this employment contract?"
    output = "Based on the consensus, you should proceed with caution."
    consensus_result = {"approved": True, "status": "APPROVED"}
    
    result = await gate.validate_final_output(
        output=output,
        agent_profile="legal_safe",
        consensus_result=consensus_result,
        original_query=critical_query,
    )
    
    if result.decision == GateDecision.FAIL_CLOSED:
        assert "consensus" not in (result.fail_closed_response or "").lower() or (
            "preuve" in (result.fail_closed_response or "").lower()
            or "claim" in (result.fail_closed_response or "").lower()
            or "source" in (result.fail_closed_response or "").lower()
        ), (
            "Si FAIL_CLOSED, ce doit etre pour strict_evidence ou claims sourcing, "
            "PAS pour absence de consensus (qui est approuve dans ce test)."
        )
