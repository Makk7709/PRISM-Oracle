# Process Contractuel KOREV Evidence

## Vue d'ensemble

Pipeline industriel **fail-closed** pour la generation de projets de contrats de licence logiciel ON-PREM.

**Separation stricte des roles :**

- `legal_drafting_guarded` = REDACTEUR (produit le projet)
- `legal_safe` = JUGE (gate d'audit, veto absolu)

## Architecture Pipeline

```text
┌─────────────────────────────────────────────────────────────┐
│                    REQUETE UTILISATEUR                        │
│         "Redige un contrat de licence ON-PREM"               │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│              ROUTER (Intent Detection)                       │
│   intent = contract_drafting → legal_drafting_guarded        │
│   intent = legal_audit       → legal_safe                    │
│   Decision.type = "legal_contract" (jamais "pricing")        │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│          1. LEGAL_DRAFTING_GUARDED (Redaction)               │
│                                                               │
│   ● Temperature = 0 (deterministe)                           │
│   ● Templates: CP + CG + 6 Annexes                          │
│   ● Variables injectables ({client_name}, {jurisdiction}...) │
│   ● Disclaimer: "PROJET — A VALIDER PAR UN JURISTE"         │
│   ● Options A/B si info manquante                            │
│   ● Zero garantie absolue                                    │
│                                                               │
│   Sortie: ContractDraft (sections + variables + disclaimer)  │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│              2. ACT LEAK GUARD (Scan)                        │
│                                                               │
│   16 patterns P0 (BLOQUANTS):                                │
│     ● Remise/cession/transfert code source                   │
│     ● Cession propriete intellectuelle                       │
│     ● Transfert savoir-faire                                 │
│     ● Garanties absolues (zero risque, conformite totale)    │
│     ● Acces depot/repository                                 │
│     ● Garantit la conformite                                 │
│     ● Cession irrevocable                                    │
│     ● Acces libre/illimite systemes                          │
│                                                               │
│   9 patterns P1 (WARNINGS):                                  │
│     ● SLA 24/7 non encadre                                   │
│     ● Disponibilite 99.99%+                                  │
│     ● Garantie de resultat                                   │
│     ● Obligation de resultat                                 │
│     ● SLA 99.9% garanti                                      │
│     ● RGPD sans role clair                                   │
│     ● Indexation ambigue                                     │
│     ● Penalites illimitees                                   │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│           3. LEGAL_SAFE GATE (Audit Fail-Closed)             │
│                                                               │
│   INVARIANTS:                                                 │
│     ● P0 trouve → REJECT (can_release = False)               │
│     ● Disclaimer absent → REJECT                             │
│     ● can_release = True ⟺ verdict = APPROVE                │
│     ● Veto ABSOLU (aucun override possible)                  │
│                                                               │
│   Sortie: GateVerdict (verdict + findings + audit_report)    │
└──────────────┬─────────────────────┬────────────────────────┘
               │                     │
        ┌──────┘                     └──────┐
        ▼                                   ▼
┌───────────────────┐           ┌───────────────────────┐
│    4a. PASS       │           │    4b. FAIL           │
│                   │           │                       │
│ ● Contrat rendu   │           │ ● Contrat BLOQUE     │
│ ● Stamp LEGAL_SAFE│           │ ● rendered = ""      │
│ ● Export autorise  │           │ ● Corrections listees│
│ ● PDF possible     │           │ ● Export INTERDIT    │
└───────────────────┘           └───────────────────────┘
```

## Regles de Gouvernance

| Regle | Description |
|-------|-------------|
| Decision.type | Toujours `legal_contract` (jamais `pricing`) |
| Veto legal_safe | ABSOLU — aucun mecanisme ne peut overrider |
| MULTI_AGENT_CONSENSUS | Ne peut JAMAIS donner de verdict juridique |
| Export | IMPOSSIBLE sans PASS legal_safe |
| Disclaimer | OBLIGATOIRE dans tout projet |

## Modules

| Fichier | Description |
|---------|-------------|
| `models.py` | Dataclasses (ContractDraft, GateVerdict, LeakFinding, DraftingOutput) |
| `templates.py` | Templates contractuels (CP, CG, Annexes 1-6) |
| `leak_guard.py` | Act Leak Guard (16 P0 + 9 P1 patterns) |
| `gate.py` | Gate d'audit fail-closed |
| `orchestrator.py` | Pipeline complet + router intent |
| `export_control.py` | Controle d'export (blocage PDF sans PASS) |
| `governance.py` | Regles de gouvernance |

## Checklist P0/P1 (Audit Interne)

### P0 — BLOQUANTS (1 seul = contrat bloque)

- [ ] Remise/livraison/cession code source
- [ ] Cession propriete intellectuelle
- [ ] Transfert savoir-faire
- [ ] Acces au depot/repository de code
- [ ] Garantie zero risque / zero bug / sans faille
- [ ] Conformite totale
- [ ] Garantit la conformite (absolu)
- [ ] Cession/transfert irrevocable
- [ ] Acces libre/illimite aux systemes
- [ ] Disclaimer absent

### P1 — WARNINGS (sigales, n'empechent pas la release)

- [ ] SLA 24/7 non encadre
- [ ] Disponibilite 99.99%+ promise
- [ ] Garantie/obligation de resultat
- [ ] SLA 99.9% garanti sans moyens
- [ ] RGPD sans role clair
- [ ] Indexation ambigue (pas d'indice)
- [ ] Penalites illimitees / sans plafond

## Tests

```bash
# Tests complets (124 tests)
python3 -m pytest tests/test_contract_drafting.py tests/test_contract_drafting_phase2.py tests/test_control_prompt_ultra_strict.py -v

# Prompt de controle ultra-exigeant uniquement
python3 -m pytest tests/test_control_prompt_ultra_strict.py -v
```

---
(c) 2026 Korev AI — Proprietary
