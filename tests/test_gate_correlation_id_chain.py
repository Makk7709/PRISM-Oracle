"""
DEF-CDG-4 regression test (audit hostile 29 mai 2026).

Garantit qu'une meme transaction entree (enforce_or_route) -> sortie
(validate_final_output) peut etre tracee par un meme correlation_id.

Defaut originel : `enforce_or_route` cree un uuid4 a chaque appel,
`validate_final_output` cree un autre uuid4 different par defaut, et le
query_hash de CriticalityAssessment est un 3eme identifiant. Une seule
decision avait 3 IDs, rendant l'audit cross-section non-fonctionnel par
defaut.

Mitigation :
- enforce_or_route retourne un GateResult avec correlation_id ;
- le caller DOIT le re-passer a validate_final_output ;
- validate_final_output l'accepte deja via le parametre correlation_id ;
- ce test verifie que la chaine fonctionne et le documente.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from python.helpers.critical_decision_gate import CriticalDecisionGate


@pytest.mark.asyncio
async def test_correlation_id_propagates_from_entry_to_exit():
    """Le correlation_id de enforce_or_route doit pouvoir etre re-utilise."""
    gate = CriticalDecisionGate()
    
    entry = gate.enforce_or_route(
        query="What is a contract?",
        agent_profile="legal_safe",
    )
    
    assert entry.correlation_id is not None
    assert len(entry.correlation_id) > 0
    
    exit_result = await gate.validate_final_output(
        output="A contract is a legally binding agreement between two or more parties.",
        agent_profile="legal_safe",
        correlation_id=entry.correlation_id,
        original_query="What is a contract?",
    )
    
    assert exit_result.correlation_id == entry.correlation_id, (
        f"DEF-CDG-4: correlation_id non propage entre enforce_or_route "
        f"({entry.correlation_id}) et validate_final_output "
        f"({exit_result.correlation_id})."
    )


@pytest.mark.asyncio
async def test_correlation_id_independent_when_not_propagated():
    """Sans propagation, les correlation_id sont distincts (comportement legacy)."""
    gate = CriticalDecisionGate()
    
    entry = gate.enforce_or_route(
        query="What is a contract?",
        agent_profile="legal_safe",
    )
    
    exit_result = await gate.validate_final_output(
        output="A contract is a legally binding agreement.",
        agent_profile="legal_safe",
    )
    
    assert exit_result.correlation_id != entry.correlation_id, (
        "Sans propagation explicite, validate_final_output genere son propre "
        "correlation_id (comportement legacy attendu)."
    )
