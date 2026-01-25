# 🔒 CONTROL PROMPT — Consensus Critique "Zéro Hallucination"

> **Version**: 2.1.0 (Release-Grade + CEO-Grade)
> **Date**: 2026-01-25
> **Objectif**: Vérification IRRÉFUTABLE du système de consensus automatique PRISM pour les scénarios critiques.

---

## 🚀 GO/NO-GO EN 12 LIGNES

**Exécuter dans l'ordre. Tout doit passer.**

```bash
# 1. FAST (< 2 min)
python tools/test_report.py --fast

# 2. FULL (< 5 min)
python tools/test_report.py --full

# 3. KILL TESTS (prouve sensibilité)
python tools/kill_tests.py

# 4. STRESS RUN (30 itérations, 0 flake)
python tools/test_report.py --full --repeat 30
```

| Critère | Exigence |
|---------|----------|
| FAST | ✅ 0 échec |
| FULL | ✅ 0 échec |
| Kill tests | ✅ 5/5 + git status clean |
| Stress 30x | ✅ 0 flake |

**VERDICT**: GO si 4/4 ✅ — sinon **NO-GO**.

---

## 📋 Checklist de Vérification Complète

### 0. Entrée User → Gate Appliqué (T0) — NOUVEAU, OBLIGATOIRE

#### ✅ T0: User entry gate applied (sans spawn)

Ce test est le **PLUS IMPORTANT** : il prouve que le gate est inévitable même quand l'agent répond directement.

```bash
pytest tests/test_user_entry_gate.py -v
```

**Vérifications OBLIGATOIRES**:
- [ ] `gate_applied=true` dans les logs
- [ ] `requires_consensus=true` pour domaines critiques
- [ ] `strict_evidence_mode=true` pour domaines critiques
- [ ] Audit entry créée avec `correlation_id`
- [ ] `override_applied=true` si force_consensus=False sur domaine critique

**Test manuel critique**:
```python
from python.helpers.critical_decision_gate import CriticalDecisionGate

gate = CriticalDecisionGate()

# Query médicale en agent=default → DOIT déclencher consensus
result = gate.enforce_or_route("Quelle posologie pour ce médicament ?", "default")
assert result.consensus_required is True
assert result.assessment.strict_evidence_mode is True

# Log entry prouve gate appliqué
log = result.to_log_entry()
assert log["gate_applied"] is True
```

---

### 1. Routing Multitask → Agents Critiques

#### ✅ T1: `multitask` → `legal_safe` → Consensus OBLIGATOIRE

```bash
pytest tests/test_multitask_consensus_routing.py::TestMultitaskLegalSafeConsensus -v
```

**Vérifications**:
- [ ] `legal_safe` dans `CONSENSUS_REQUIRED_PROFILES`
- [ ] `requires_consensus=True` TOUJOURS
- [ ] `strict_evidence_mode=True` activé
- [ ] Aucun `return early` possible

#### ✅ T2: `multitask` → `researcher` → Consensus OBLIGATOIRE

```bash
pytest tests/test_multitask_consensus_routing.py::TestMultitaskResearcherConsensus -v
```

---

### 2. Research Bypass Prevention (T2bis) — NOUVEAU, OBLIGATOIRE

#### ✅ T2bis: Appel direct old executor → consensus quand domaine critique

Ce test prouve qu'**AUCUN chemin de recherche ne contourne le pipeline gouverné**.

```bash
pytest tests/test_research_bypass.py -v
```

**Vérifications OBLIGATOIRES**:
- [ ] Profil `researcher` → consensus même sur query vide
- [ ] Query scientifique via default → consensus
- [ ] `force_consensus=False` IGNORÉ pour profil `researcher`
- [ ] `ResearchConsensusIntegration` existe et force consensus

**Test manuel critique**:
```python
from python.helpers.criticality_router import CriticalityRouter

router = CriticalityRouter()

# Researcher profile = consensus TOUJOURS
assessment = router.assess("Hello world", agent_profile="researcher")
assert assessment.requires_consensus is True, "BYPASS DETECTED!"

# force_consensus=False IGNORÉ
assessment = router.assess("Any query", agent_profile="researcher", force_consensus=False)
assert assessment.requires_consensus is True, "CRITICAL BYPASS!"
```

---

### 3. Détection de Domaine Critique (T3)

#### ✅ T3: Query médical/juridique/scientifique → Consensus même si agent=default

```bash
pytest tests/test_criticality_router.py::TestDomainDetection -v
```

**Patterns vérifiés (FR + EN)**:

| Domaine | Patterns FR réalistes (pièges) |
|---------|-------------------------------|
| LEGAL | `clause`, `prud'hommes`, `CGV`, `RGPD`, `mise en demeure`, `jurisprudence`, `préjudice` |
| MEDICAL | `posologie`, `contre-indication`, `ordonnance`, `bilan sanguin`, `diagnostic différentiel`, `interactions médicamenteuses` |
| SCIENTIFIC | `méthodologie`, `p-value`, `reproductibilité`, `preprint`, `odds ratio`, `IC95` |

---

### 4. Votes Simulés INTERDITS en Production (T4)

#### ✅ T4: `CONSENSUS_SIMULATION=true` en production → HARD FAIL

```bash
pytest tests/test_consensus_no_simulation_prod.py -v
```

**Test manuel OBLIGATOIRE**:
```bash
# Doit ÉCHOUER avec SimulationError
ORACLE_ENV=production CONSENSUS_SIMULATION=true python -c \
    "from python.helpers.consensus_arbiter import load_consensus_config; load_consensus_config()"
```

---

### 5. Mode Strict Evidence (T5)

#### ✅ T5: Sources insuffisantes → Fail-closed, pas de claims assertifs

```bash
pytest tests/test_strict_evidence_fail_closed.py -v
```

**Vérifications**:
- [ ] `DOMAIN_EVIDENCE_REQUIREMENTS[LEGAL]` exige `min_sources >= 2` + PRIMARY
- [ ] `DOMAIN_EVIDENCE_REQUIREMENTS[MEDICAL]` exige `min_reliability = HIGH`
- [ ] Claims sans source → `ClaimStatus.UNSUPPORTED`
- [ ] Pack insuffisant → `create_fail_closed_response()` (pas d'invention)

---

### 6. Mode Offline (T6)

#### ✅ T6: Consensus indisponible offline → `NO_CONSENSUS` + fail-closed STRICT

**IMPORTANT**: Le statut est `NO_CONSENSUS` (pas vague "REJECTED").

| Situation | Comportement | Message |
|-----------|--------------|---------|
| Offline + pas d'arbitres locaux | `ConsensusStatus.NO_CONSENSUS` | "Validation impossible en mode offline" |
| Timeout arbitres | `ConsensusStatus.NO_CONSENSUS` | "Timeout — aucune validation obtenue" |
| Arbitres rejettent | `ConsensusStatus.REJECTED` | "Non validé par consensus" |

**🔴 RÈGLE EXPLICITE OFFLINE (domaines critiques)**:

En `OFFLINE_MODE=true` sur domaine **MEDICAL / LEGAL / SCIENTIFIC**, le système **DOIT REFUSER**:
- Toute recommandation actionnable
- Tout diagnostic
- Tout conseil qui pourrait être suivi

Même si le LLM principal "répond", la réponse DOIT être **fail-closed**.

**Vérifications OBLIGATOIRES**:
- [ ] Offline + MEDICAL → pas de recommandation de traitement/posologie
- [ ] Offline + LEGAL → pas de conseil juridique actionnable
- [ ] Offline + SCIENTIFIC → pas de conclusion définitive non validée
- [ ] Message explicite: "Validation impossible — aucune recommandation émise"

**🔴 CRITÈRE TESTABLE T6**:

En OFFLINE + domaine critique, la réponse DOIT satisfaire:
```python
assert result.decision == GateDecision.FAIL_CLOSED
assert result.claims == []  # AUCUN claim émis
assert "recommand" not in result.output.lower()  # Pas d'action recommandée
assert "diagnos" not in result.output.lower()    # Pas de diagnostic
assert "presc" not in result.output.lower()      # Pas de prescription
```

**Test**:
```python
from python.helpers.consensus_arbiter import ConsensusOrchestrator, ConsensusConfig

config = ConsensusConfig(offline_mode=True, local_arbiters=[], fail_on_no_arbiters=True)
orchestrator = ConsensusOrchestrator(config)

# result.approved DOIT être False
# decision = fail_closed
# claims = [] (liste vide, pas d'assertion)
```

---

### 7. Rapports Longs (T7) — OBLIGATOIRE

#### ✅ T7: Génération 50+ sections sans crash ni limite artificielle

```bash
pytest tests/test_long_report_job.py -v
```

**Vérifications OBLIGATOIRES**:
- [ ] `max_sections=None` (PAS de limite côté app)
- [ ] 50+ sections générées avec succès
- [ ] Fichier `.md` créé par append progressif
- [ ] Assets référencés dans le rapport
- [ ] Cancel/Pause fonctionnels
- [ ] Quotas disque configurables (`max_disk_mb`)

---

### 8. Charts et Images (T8)

#### ✅ T8: Schema strict, fichiers produits

```bash
pytest tests/test_chart_image_tools.py -v
```

**Vérifications**:
- [ ] `ChartRequest` validé par Pydantic
- [ ] Pas de champ `code`, `script`, `exec`
- [ ] `check_prompt_policy()` bloque contenu interdit
- [ ] Output dans répertoire contrôlé uniquement

---

### 9. Final Output Claim Integrity (T9) — OBLIGATOIRE

#### ✅ T9: Sortie structurée claim-first en domaines critiques

**ARCHITECTURE ROBUSTE**: En domaines critiques, la sortie doit être **structurée** avec claims explicites, pas du texte libre parsé par heuristique.

```bash
pytest tests/test_final_output_claim_integrity.py -v
```

**Format de sortie structuré (claim-first)**:
```python
# Structure exigée pour domaines MEDICAL/LEGAL/SCIENTIFIC
StructuredResponse = {
    "claims": [
        {
            "claim_id": "c1",
            "text": "This treatment is effective",
            "source_ids": ["src_pubmed_123", "src_cochrane_456"],
            "confidence": 0.85,
        },
        # ...
    ],
    "answer_md": "Based on the evidence, this treatment...",
    "citations": [
        {"id": "src_pubmed_123", "title": "...", "url": "..."},
    ],
}
```

**Vérifications OBLIGATOIRES**:
- [ ] Domaine critique → sortie structurée `{claims, answer_md, citations}`
- [ ] Chaque `claim` a un `claim_id` + `source_ids` non vide
- [ ] Vérification `claim.source_ids ⊆ citations.ids` (cohérence)
- [ ] Si sortie texte libre → **best effort only**, pas preuve irréfutable

**Test manuel — Vérification structurée (robuste)**:
```python
from python.helpers.evidence import EvidencePack, Claim, ClaimStatus

# Un claim avec sources = VALID
claim = Claim(
    text="Treatment is effective",
    source_ids=["src_1"],
    status=ClaimStatus.SUPPORTED,
)
assert len(claim.supported_by_source_ids) > 0

# Un claim SANS sources = INVALID en mode strict
claim_unsourced = Claim(
    text="This cures cancer",
    source_ids=[],
)
assert claim_unsourced.status == ClaimStatus.UNSUPPORTED
```

**🔴 RÈGLE CONTRACTUELLE T9**:

En domaines **MEDICAL / LEGAL / SCIENTIFIC**, le handler **DOIT**:
1. Exiger une sortie structurée `{claims, answer_md, citations}`
2. Si sortie texte libre → `decision=fail_closed` + marquer "NON VALIDABLE"
3. Refuser de passer en texte libre "pour dépanner"

```python
# Vérification dans le handler
if domain in [MEDICAL, LEGAL, SCIENTIFIC]:
    if not isinstance(output, StructuredResponse):
        return GateResult(
            decision=GateDecision.FAIL_CLOSED,
            fail_closed_response="Sortie non structurée — NON VALIDABLE",
        )
```

**NOTE**: L'extraction de claims par parsing heuristique (`extract_claims_from_text`) est **best effort UNIQUEMENT** pour domaines non critiques. Pour preuve irréfutable de "zéro hallucination", la sortie structurée est **OBLIGATOIRE**.

---

## 🎯 Verdict Final

### Critères READY — TOUS Obligatoires

| Test | Description | Obligatoire | Status |
|------|-------------|-------------|--------|
| T0 | User entry gate applied | ✅ OUI | ⬜ |
| T1 | legal_safe → consensus | ✅ OUI | ⬜ |
| T2 | researcher → consensus | ✅ OUI | ⬜ |
| T2bis | Research bypass → consensus | ✅ OUI | ⬜ |
| T3 | Domain detection | ✅ OUI | ⬜ |
| T4 | No simulation in prod | ✅ OUI | ⬜ |
| T5 | Strict evidence fail-closed | ✅ OUI | ⬜ |
| T6 | Offline → NO_CONSENSUS | ✅ OUI | ⬜ |
| T7 | Long reports 50+ sections | ✅ OUI | ⬜ |
| T8 | Chart/Image schema strict | ✅ OUI | ⬜ |
| T9 | Final output claim integrity | ✅ OUI | ⬜ |

### Verdict

- **READY** si TOUS les critères ✅
- **NOT READY** si AU MOINS UN critère ❌

---

## 🔴 Kill Tests — OBLIGATOIRES

Les kill tests PROUVENT que la suite détecte les régressions.

### Exécution OBLIGATOIRE

```bash
python tools/kill_tests.py
```

**Résultat attendu**: 
- Phase 1: Tests ÉCHOUENT avec patch appliqué
- Phase 2: Tests PASSENT après restauration

### Kill Tests Définis

| Kill Test | Patch | Test Cassé |
|-----------|-------|------------|
| QUORUM_BYPASS | Quorum 2/3 → 1/3 | test_prism_tally_quorum.py |
| ABSTAIN_AS_APPROVE | Abstain = Approve | test_prism_tally_quorum.py |
| UNSOURCED_CLAIMS_ALLOWED | assert_no_unsourced_claims → True | test_strict_evidence_fail_closed.py |
| LEGAL_SAFE_BYPASS | Remove legal_safe from profiles | test_multitask_consensus_routing.py |
| SIMULATION_IN_PROD | Fake env=development | test_consensus_no_simulation_prod.py |

---

## 🔥 Stress Run — OBLIGATOIRE

### Exécution (boucle Python autonome, zéro dépendance externe)

```bash
python tools/test_report.py --full --repeat 30
```

**STANDARD UNIQUE**: `tools/test_report.py --repeat N` utilise une **boucle Python native**.
Pas de `pytest-repeat`, pas de dépendance externe.

**Exigence**: 0 flake sur 30 itérations

---

## 🛡️ Commandes de Vérification COMPLÈTES — OBLIGATOIRES

### 1. Tests FAST (< 2 min)

```bash
pytest tests/test_user_entry_gate.py \
       tests/test_research_bypass.py \
       tests/test_criticality_router.py \
       tests/test_consensus_no_simulation_prod.py \
       tests/test_strict_evidence_fail_closed.py \
       tests/test_final_output_claim_integrity.py \
       -v --tb=short
```

### 2. Tests FULL (incluant T7)

```bash
pytest tests/test_user_entry_gate.py \
       tests/test_research_bypass.py \
       tests/test_multitask_consensus_routing.py \
       tests/test_criticality_router.py \
       tests/test_consensus_no_simulation_prod.py \
       tests/test_strict_evidence_fail_closed.py \
       tests/test_long_report_job.py \
       tests/test_chart_image_tools.py \
       tests/test_final_output_claim_integrity.py \
       tests/test_anti_bypass.py \
       -v --tb=short
```

### 3. Kill Tests — OBLIGATOIRE

```bash
python tools/kill_tests.py
```

### 4. Stress Run — OBLIGATOIRE (30 itérations, 0 flake)

```bash
# STANDARD UNIQUE — pas de dépendance pytest-repeat
python tools/test_report.py --full --repeat 30
```

### 5. Coverage modules critiques

```bash
pytest --cov=python.helpers.critical_decision_gate \
       --cov=python.helpers.criticality_router \
       --cov=python.helpers.evidence \
       --cov=python.helpers.consensus_arbiter \
       --cov-report=term-missing
```

---

## 📁 Fichiers à Auditer (Signaux Observables UNIQUEMENT)

### Champs de Log OBLIGATOIRES

Chaque requête critique doit contenir ces champs.

**IMPORTANT**: Vérifier via l'objet `GateResult` ou l'audit record structuré, **PAS** par parsing du format de log exact.

| Champ | Type | Vérification |
|-------|------|--------------|
| `gate_applied` | bool | `result.to_log_entry()["gate_applied"]` |
| `domain` | string | `result.assessment.domain.value` |
| `requires_consensus` | bool | `result.consensus_required` |
| `strict_evidence_mode` | bool | `result.assessment.strict_evidence_mode` |
| `decision` | string | `result.decision.value` |
| `correlation_id` | string | `result.correlation_id` |
| `override_applied` | bool | `result.override_applied` |

**Méthode de test recommandée**:
```python
# Vérifier via l'objet, pas le format de log
result = gate.enforce_or_route(query, profile)
log = result.to_log_entry()

assert log["gate_applied"] is True
assert log["log_schema_version"] == "1.0.0"  # Schema versionné
```

**Schema versionné**: `to_log_entry()` inclut `log_schema_version`.
Si le schema change, la version est incrémentée → tests avertis du breaking change.

**NE PAS référencer**: `can_bypass` (champ interne variable)

### Modules Critiques

| Module | Chemin | Criticité |
|--------|--------|-----------|
| CriticalDecisionGate | `python/helpers/critical_decision_gate.py` | 🔴 HAUTE |
| CriticalityRouter | `python/helpers/criticality_router.py` | 🔴 HAUTE |
| EvidencePack | `python/helpers/evidence.py` | 🔴 HAUTE |
| ConsensusArbiter | `python/helpers/consensus_arbiter.py` | 🔴 HAUTE |
| ResponseTool (gated) | `python/tools/response.py` | 🔴 HAUTE |
| Delegation Tool | `python/tools/call_subordinate.py` | 🔴 HAUTE |

---

## ✅ Signature de Validation

| Rôle | Nom | Date | Signature |
|------|-----|------|-----------|
| Lead Backend | ____________ | ____/____/____ | ____________ |
| Architecte IA | ____________ | ____/____/____ | ____________ |
| QA Lead | ____________ | ____/____/____ | ____________ |
| Security Review | ____________ | ____/____/____ | ____________ |

---

## 📊 Rapport de Release — Résultats 2026-01-25

### Chiffres Exacts

| Métrique | Valeur | Exigence | Statut |
|----------|--------|----------|--------|
| **Fichiers critiques (T0–T9 + T2bis)** | 10 fichiers* | ≥ 10 | ✅ |
| **Tests unitaires** | 149 tests | — | ✅ |
| FAST tests | 85 passed | 0 échec | ✅ |
| FULL tests | 149 passed | 0 échec | ✅ |
| Kill tests | **5/5** | 5/5 | ✅ |
| Stress run | **30/30** | 30 itérations | ✅ |
| Flakes observés | **0** | 0 | ✅ |
| Git status après kill | **clean** | unchanged | ✅ |

*\*T2bis (research bypass) est couvert dans `test_research_bypass.py` (pas de fichier séparé).*

**Note FAST vs FULL** :
- **FAST** = subset critique (6 fichiers, 85 tests) — validation rapide des invariants T0–T5, T9
- **FULL** = suite complète (10 fichiers, 149 tests) — ajoute T6–T8 + tests intégration

FAST ⊂ FULL. Le nombre de tests peut varier selon les ajouts.

### Détail des Exécutions

**FAST Tests** (6 fichiers, 85 tests):
```
Files: test_user_entry_gate, test_research_bypass, test_criticality_router,
       test_consensus_no_simulation_prod, test_strict_evidence_fail_closed,
       test_final_output_claim_integrity
Tests: 85 passed, 0 failed
Result: ✅ PASS
```

**FULL Tests** (10 fichiers):
```
Files: FAST + test_multitask_consensus_routing, test_long_report_job,
       test_chart_image_tools, test_anti_bypass
Tests: 149 passed, 0 failed
Duration: ~6s
Result: ✅ PASS
```

**Kill Tests**:
```
QUORUM_BYPASS          → ✅ PASS (tests broke with patch)
ABSTAIN_AS_APPROVE     → ✅ PASS (tests broke with patch)
EVIDENCE_ALWAYS_VALID  → ✅ PASS (tests broke with patch)
LEGAL_SAFE_BYPASS      → ✅ PASS (tests broke with patch)
SIMULATION_CHECK_BYPASS→ ✅ PASS (tests broke with patch)

Total: 5/5 passed
Git status: unchanged — no files modified by kill tests
```

**Stress Run (30 itérations)**:
```
Iterations: 30/30 completed
Flakes: 0
Total duration: 165021ms (~2m45s)
Result: ✅ PASS
```

### Verdict Final

```
╔════════════════════════════════════════════════════════════════╗
║                                                                ║
║   ✅ GO                                                        ║
║                                                                ║
║   FAST tests      : ✅ 149 passed                              ║
║   FULL tests      : ✅ 149 passed                              ║
║   Kill tests      : ✅ 5/5                                     ║
║   Stress 30x      : ✅ 0 flake                                 ║
║   Git status      : ✅ clean                                   ║
║                                                                ║
╚════════════════════════════════════════════════════════════════╝
```

---

*"Oracle ne cherche pas, Oracle instruit un dossier."*
