"""
Contract Drafting Guarded — Pipeline de rédaction contractuelle sécurisée.

Architecture:
    Draft (legal_drafting_guarded) → Gate (leak_guard + audit) → Output (fail-closed)

Modules:
    models.py      — Dataclasses (ContractDraft, GateVerdict, LeakFinding, etc.)
    templates.py   — Templates contractuels (CP, CG, Annexes)
    leak_guard.py  — Act Leak Guard (détection clauses dangereuses)
    gate.py        — Gate d'audit (P0/P1/P2, fail-closed)
    orchestrator.py — Pipeline Draft → Gate → Output

© 2026 Korev AI — Proprietary
"""
