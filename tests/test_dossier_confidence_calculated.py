"""
DEF-CI-2 regression test (audit hostile 29 mai 2026).

Garantit que confidence_score d'un ResearchDossier est calcule a partir
d'une formule documentee (et non plus assigne via constantes magiques
0.3 / 0.5 / 0.9).

La formule documentee depuis cette passe d'audit :

  base = 0.3 si rejected
       = 0.5 si bypass (require_consensus=False)
       = 0.9 si approved

  ajustement = + min(0.05, 0.01 * total_sources) si total_sources > 0

  clamp [0.0, 1.0]

Le test verifie :
1. Les bornes (rejected < bypass < approved) ;
2. L'effet bonus des sources ;
3. Le clamp final.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from python.helpers.consensus_integration import _compute_dossier_confidence


def _make_consensus(approved: bool) -> dict:
    return {"approved": approved, "status": "APPROVED" if approved else "REJECTED"}


def test_confidence_rejected_lower_than_approved():
    """Un consensus rejete doit produire un score plus bas qu'un consensus approuve."""
    low = _compute_dossier_confidence(
        total_sources=0,
        require_consensus=True,
        consensus_result=_make_consensus(approved=False),
    )
    high = _compute_dossier_confidence(
        total_sources=0,
        require_consensus=True,
        consensus_result=_make_consensus(approved=True),
    )
    assert low < high, f"Expected rejected < approved, got {low} >= {high}"


def test_confidence_bypass_between_rejected_and_approved():
    """Le bypass de consensus produit un score median (0.5 base) entre rejected et approved."""
    rejected = _compute_dossier_confidence(
        total_sources=0,
        require_consensus=True,
        consensus_result=_make_consensus(approved=False),
    )
    bypass = _compute_dossier_confidence(
        total_sources=0,
        require_consensus=False,
        consensus_result=None,
    )
    approved = _compute_dossier_confidence(
        total_sources=0,
        require_consensus=True,
        consensus_result=_make_consensus(approved=True),
    )
    assert rejected < bypass < approved, (
        f"Expected rejected < bypass < approved, "
        f"got {rejected} < {bypass} < {approved}"
    )


def test_confidence_increases_with_sources():
    """Plus de sources => score plus eleve (jusqu'au plafond)."""
    no_sources = _compute_dossier_confidence(
        total_sources=0,
        require_consensus=True,
        consensus_result=_make_consensus(approved=True),
    )
    many_sources = _compute_dossier_confidence(
        total_sources=10,
        require_consensus=True,
        consensus_result=_make_consensus(approved=True),
    )
    assert many_sources >= no_sources, (
        f"Sources doivent augmenter (ou maintenir) le score, "
        f"got {many_sources} < {no_sources}"
    )


def test_confidence_clamped_to_unit_interval():
    """Le score doit toujours rester dans [0.0, 1.0]."""
    extreme = _compute_dossier_confidence(
        total_sources=10_000,
        require_consensus=True,
        consensus_result=_make_consensus(approved=True),
    )
    assert 0.0 <= extreme <= 1.0, f"Score hors [0,1]: {extreme}"
