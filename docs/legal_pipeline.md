# Legal Pipeline — Evidence

> **AVERTISSEMENT**: Ce module garantit la provenance et la traçabilité des sources,
> pas l'exhaustivité ni l'interprétation juridique.
> Le droit opposable n'est authentifié que sur les sites officiels.

**Version**: 1.1.0 (P0.7 Premium Gate)

---

## P0.7 — Premium Quality Gate

### Invariants strictement enforced

| ID | Invariant | Description | Test |
|----|-----------|-------------|------|
| **A** | Deterministic audit_bundle_id | Hash stable (draft_id + mode + chunks + citations). Aucun timestamp. | T1 |
| **B** | Provenance obligatoire | Mode ≠ REFUSAL => provenance non vide. Sinon => REFUSAL. | T2 |
| **C** | Consensus requis | BOARD ou MEDIUM/HIGH => consensus obligatoire. Sinon => REFUSAL. | T3, T4 |
| **D** | Claims requis | OPERATIONAL/BOARD => claims obligatoires. Sinon => Judge REJECT. | T5 |
| **E** | SOURCES_PRESENT strict | OPERATIONAL/BOARD => rules sans citations = FAIL (pas WARN). | T6 |
| **F** | Mode cohérent | APPROVED_POSITION ssi consensus_status == "APPROVED". | T7 |
| **G** | Fail-closed explicite | Toute violation => REFUSAL avec missing_info code standard. | Tous |
| **H** | Zéro présomption FR | BOARD + jurisdiction UNKNOWN => FAIL. Pas de présomption silencieuse. | T8 |

### Codes missing_info standards

```python
class MissingInfoCode:
    FACTS_LIST = "facts_list"
    JURISDICTION = "jurisdiction"
    JURISDICTION_CLARIFICATION = "jurisdiction_clarification"
    CLAIMS_REQUIRED = "claims_required"
    UNSUPPORTED_CLAIMS = "unsupported_claims"
    PROVENANCE_MISSING = "provenance_missing"
    CONSENSUS_REQUIRED = "consensus_required"
    CONSENSUS_REJECTED = "consensus_rejected"
    CITATIONS_MISSING = "citations_missing"
    APPLICATION_MISSING = "application_missing"
    SOURCES_MISSING = "sources_missing"
```

### Matrice Consensus

| Risk Tier | Scope | Consensus requis? |
|-----------|-------|-------------------|
| LOW | INFO | ❌ Non |
| LOW | OPERATIONAL | ❌ Non |
| LOW | BOARD | ✅ Oui |
| MEDIUM | * | ✅ Oui |
| HIGH | * | ✅ Oui (unanimité) |

### Comportement fail-closed

```text
┌─────────────────────────────────────────────────────────────────────────────┐
│  Si consensus requis mais absent    → REFUSAL (consensus_required)         │
│  Si consensus requis mais rejeté    → REFUSAL (consensus_rejected)         │
│  Si provenance manquante (non-REFUSAL) → REFUSAL (provenance_missing)      │
│  Si OPERATIONAL/BOARD sans claims   → Judge REJECT (claims_required)       │
│  Si BOARD + jurisdiction UNKNOWN    → Judge REJECT (jurisdiction)          │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Vue d'ensemble

```text
┌─────────────────────────────────────────────────────────────────────────────┐
│                        EVIDENCE LEGAL PIPELINE                              │
│                                                                             │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐              │
│  │  ROUTER  │───▶│  LEGAL   │───▶│  JUDGE   │───▶│CONSENSUS │───▶ OUTPUT   │
│  │ (Intent) │    │  AGENT   │    │ (Check)  │    │ (Validate)│              │
│  └──────────┘    └──────────┘    └──────────┘    └──────────┘              │
│       │                │              │               │                     │
│       ▼                ▼              ▼               ▼                     │
│   risk_tier        LegalDraft    checklist       contract                  │
│   scope            + Claims      binaire         compliance                 │
│   jurisdiction     + Citations   6 checks        3 items                    │
└─────────────────────────────────────────────────────────────────────────────┘
```

## P0.1 — Routing Juridique

### LegalRiskTier

| Tier | Description | Exemples |
|------|-------------|----------|
| `LOW` | Question simple, info publique | "Qu'est-ce que l'article 1134?" |
| `MEDIUM` | Interprétation, clause, contrat | "Clause de non-concurrence valide?" |
| `HIGH` | M&A, IPO, restructuration, contentieux majeur | "Due diligence M&A", "Pourvoi en cassation" |

### DecisionScope

| Scope | Description | Consensus requis |
|-------|-------------|------------------|
| `INFO` | Information pure | Non |
| `OPERATIONAL` | Conseil opérationnel | 2/3 si MEDIUM+ |
| `BOARD` | Décision stratégique | 2/3 + judge_pass |

### Jurisdiction

| Jurisdiction | Patterns détectés |
|--------------|-------------------|
| `FR` | Code civil, C. civ., Cass., tribunal, prud'hommes |
| `EU` | RGPD, GDPR, CJUE, directive européenne |
| `MIXED` | FR + EU mélangé (nécessite clarification) |
| `UNKNOWN` | Non détecté (présumé FR pour INFO/OPERATIONAL) |

### Usage

```python
from python.helpers.legal_pipeline import detect_legal_context, LegalRiskTier

ctx = detect_legal_context("Analyse M&A avec due diligence")

assert ctx.risk_tier == LegalRiskTier.HIGH
assert ctx.scope == DecisionScope.BOARD
```

---

## P0.2 — LegalDraft + Claims

### Structure du Draft

```python
@dataclass
class LegalDraft:
    # Structure IRAC/FIRAC
    facts: List[str]       # Faits (séparés du droit)
    rules: List[str]       # Articles, arrêts cités
    application: str       # Comment les règles s'appliquent aux faits
    risks: List[str]       # Risques identifiés
    next_action: str       # Recommandation concrète
    
    # Claims list (P0.2 core)
    claims: List[LegalClaim]
```

### Claims Types

| Type | Description | Valide? |
|------|-------------|---------|
| `CITED` | Claim avec citation source | ✅ si citation présente |
| `HYPOTHESIS` | Hypothèse explicite | ✅ toujours |
| `UNSUPPORTED` | Claim sans source | ❌ jamais |

### Règle d'or

> **Chaque claim DOIT pointer vers une citation OU être marqué hypothèse.**
> Un claim `UNSUPPORTED` fait échouer le Judge.

### Usage

```python
draft = LegalDraft(draft_id="...", query="...")

# Claim cité
draft.add_cited_claim(
    text="Le contrat est valide",
    citation="Art. 1134 C. civ.",
)

# Hypothèse explicite
draft.add_hypothesis_claim(
    text="Le délai est probablement de 5 ans",
    basis="Non spécifié dans les faits fournis"
)

# Vérifier
assert draft.has_unsupported_claims == False
```

---

## P0.3 — Judge Checklist Binaire

### Les 6 Checks

| Check | Description | Critique? |
|-------|-------------|-----------|
| `SOURCES_PRESENT` | Règles juridiques citées | ✅ Oui |
| `FACTS_SEPARATED` | Faits ≠ droit | ✅ Oui |
| `APPLICATION_PRESENT` | Règle → faits expliqué | ✅ Oui |
| `NO_UNSUPPORTED_CLAIMS` | Zéro claim sans source/hypothèse | ✅ Oui |
| `JURISDICTION_CLEAR` | Juridiction identifiée | ⚠️ BOARD only |
| `ABROGATION_HANDLED` | Textes abrogés signalés | ✅ Oui |

### Verdicts

| Verdict | Condition | Action |
|---------|-----------|--------|
| `APPROVE` | Tous les checks critiques passent | → Consensus |
| `REJECT` | ≥1 check critique échoue | → REFUSAL |
| `REQUEST_INFO` | Checks passent mais infos manquantes | → REFUSAL (demande d'infos) |

### Usage

```python
from python.helpers.legal_pipeline import judge_legal_draft

result = judge_legal_draft(draft)

if result.verdict == LegalJudgeVerdict.APPROVE:
    # Passer au consensus
    ...
else:
    print(f"Critical failures: {result.critical_failures}")
```

---

## P0.4 — Consensus sur Contrat

### Ce que le Consensus vote

Le consensus vote sur le **contrat**, pas sur l'**opinion**:

| Item | Question |
|------|----------|
| `CONTRACT_COMPLIANCE` | Citations présentes, provenance, structure complète? |
| `CLAIM_SUPPORT` | Tous les claims sont supportés? |
| `RISK_TIER_CONSISTENCY` | Profondeur de réponse cohérente avec le risque? |

### Quorum par Risk Tier

| Risk Tier | Quorum | Unanimité |
|-----------|--------|-----------|
| `LOW` | 2/3 | Non |
| `MEDIUM` | 2/3 | Non |
| `BOARD` | 2/3 + judge_pass | Non |
| `HIGH` | 3/3 | Oui + escalade |

### Usage

```python
from python.helpers.legal_pipeline import build_legal_consensus_proposal

proposal = build_legal_consensus_proposal(draft, judge_result)

assert proposal.required_approvals == 2  # ou 3 pour HIGH
assert proposal.require_unanimity == False  # ou True pour HIGH
```

---

## P0.5 — Output Modes

### Les 3 Modes

| Mode | Bandeau | Condition |
|------|---------|-----------|
| `APPROVED_POSITION` | ✅ POSITION VALIDÉE | Consensus APPROVED |
| `SAFE_ANALYSIS` | 🔒 ANALYSE SÉCURISÉE | Judge OK, LOW risk ou pas de consensus |
| `REFUSAL_REQUEST_INFO` | ⚠️ REFUS | Judge REJECT ou infos manquantes |

### Toujours présent

- `audit_bundle_id` (même en refus)
- `disclaimer` (toujours)
- `citations` et `provenance` (si disponibles)

### Usage

```python
from python.helpers.legal_pipeline import build_legal_output

output = build_legal_output(draft, judge_result, consensus_result)

print(output.get_banner())
# "✅ POSITION VALIDÉE — Consensus atteint, sources vérifiées"

print(output.to_markdown())
# Markdown formaté avec structure complète
```

---

## P0.6 — Scénarios E2E

### Scénario 1: LOW

**Query**: "Qu'est-ce que l'article 1134 du code civil?"

```text
Router → risk_tier=LOW, scope=INFO, jurisdiction=FR
Draft  → facts=1, rules=1, application=OK
Judge  → APPROVE (6/6 checks)
Output → SAFE_ANALYSIS (pas de consensus requis pour LOW)
```

### Scénario 2: MEDIUM/BOARD

**Query**: "Analyse clause de non-concurrence dans contrat commercial"

```text
Router → risk_tier=MEDIUM, scope=OPERATIONAL, jurisdiction=FR
Draft  → facts=3, rules=2, application=OK, claims=2
Judge  → APPROVE
Consensus → 2/3 required
Output → APPROVED_POSITION si consensus OK
```

### Scénario 3: HIGH (M&A)

**Query**: "Due diligence M&A LBO avec valorisation"

```text
Router → risk_tier=HIGH, scope=BOARD, jurisdiction=FR
Draft  → facts=4, rules=3, application=OK, claims=3, risks=4
Judge  → APPROVE
Consensus → 3/3 unanimité + escalade
Output → APPROVED_POSITION ou SAFE_ANALYSIS si rejet
```

---

## Anti-Hallucination

### Le piège classique

> Citation correcte mais conclusion fausse.

### Défenses

1. **Claims list**: Chaque affirmation doit pointer vers une source ou être marquée hypothèse
2. **Judge APPLICATION_PRESENT**: Vérifie que règle→faits est expliqué
3. **Consensus CLAIM_SUPPORT**: Vote sur la cohérence faits→règle→application
4. **REQUEST_INFO**: Demande d'infos si faits insuffisants

---

## Files

| File | Description |
|------|-------------|
| `python/helpers/legal_pipeline.py` | Pipeline complet (P0.1-P0.5) |
| `python/helpers/legal_retrieval.py` | Retrieval en 2 temps (exact + search) |
| `tests/test_legal_pipeline.py` | 38 tests E2E |
| `docs/legal_pipeline.md` | Cette documentation |

---

## Version

**legal_pipeline@v1.2.0** (P0.8-P0.9 Production Lock) — 2026-01-25

Compatible avec `legal_sources@v1.0-enterprise`

---

## P0.8-P0.9 — Production Lock

### Single Entry Point: Legal Orchestrator

```python
from python.helpers.legal_orchestrator import run_legal_pipeline

output = await run_legal_pipeline(
    query="Analyse de la clause de non-concurrence",
    correlation_id="corr_abc123",
    enforcement_level=3,  # Hard enforcement
    max_sources=5,
)
```

### Architecture Runtime

```text
┌─────────────────────────────────────────────────────────────────┐
│  run_legal_pipeline(query, route_decision, ...)                 │
│     ├── 1. Retrieval (exact + search, 2-stage)                  │
│     ├── 2. Draft construction (FIRAC + claims)                  │
│     ├── 3. Judge (binary checklist P0.7)                        │
│     ├── 4. Consensus (if required: BOARD/MEDIUM/HIGH)           │
│     └── 5. Output (APPROVED/SAFE/REFUSAL)                       │
└─────────────────────────────────────────────────────────────────┘
```

### Variables d'environnement

| Variable | Description | Valeur par défaut |
|----------|-------------|-------------------|
| `LEGAL_PIPELINE_ENABLED` | Active/désactive le pipeline | `1` (activé) |
| `LEGAL_ENFORCEMENT_LEVEL` | Niveau d'enforcement (0-3) | `3` (hard) |

**Niveaux d'enforcement:**

- 0 = OFF (REFUSAL systématique)
- 1 = Audit-only (log mais pas de blocage)
- 2 = Soft (blocage high-stakes)
- 3 = Hard (invariants P0.7 complets)

### Observabilité

**Logs JSON structurés:**

```json
{
  "correlation_id": "corr_abc123",
  "event": "legal_pipeline_end",
  "timestamp": 1706234567.123,
  "duration_ms": 1250.5,
  "output_mode": "approved_position",
  "consensus_status": "APPROVED"
}
```

**Métriques exposées:**

- `legal_pipeline_requests_total`
- `legal_pipeline_refusals_total` (par raison)
- `legal_pipeline_provenance_missing_total`
- `legal_pipeline_consensus_required_total`
- `legal_pipeline_latency_ms` (p50/p95)

### Rendu Cabinet-Grade (P0.9)

```python
from python.helpers.legal_rendering import render_legal_output_markdown

# 3 styles disponibles
md_info = render_legal_output_markdown(output, style="info")
md_operational = render_legal_output_markdown(output, style="operational")
md_board = render_legal_output_markdown(output, style="board")
```

**Styles:**

| Style | Audience | Contenu |
|-------|----------|---------|
| `info` | Utilisateurs | Court, pédagogique, sources compactes |
| `operational` | Juristes/Ops | FIRAC complet, next_action, checklist |
| `board` | Direction | Executive memo, risques classés, décisions |

**Garanties de rendu:**

- ✅ Bandeau toujours en tête
- ✅ Disclaimer toujours présent
- ✅ Sources toujours présentes (non-refusal)
- ✅ Citations + pinpoint + origin_url (si disponible)

### Raisons de refus standardisées

| Code | Description |
|------|-------------|
| `legal_pipeline_disabled` | Pipeline désactivé |
| `consensus_required` | Consensus requis mais non fourni |
| `consensus_rejected` | Consensus rejeté |
| `provenance_missing` | Provenance incomplète |
| `claims_required` | Claims obligatoires pour OPERATIONAL/BOARD |
| `sources_missing` | Aucune source citée |
| `jurisdiction` | Juridiction requise pour BOARD |

---

---

## P1 — Wiring Final

### Consensus réel (P1.2)

```python
# Simulation désactivée par défaut (production)
# Pour activer: LEGAL_CONSENSUS_SIMULATION=1

from python.helpers.legal_orchestrator import execute_consensus

result = await execute_consensus(
    proposal,
    correlation_id="corr_123",
)
# result: {"status": "APPROVED"|"REJECTED"|"PENDING", "votes": {...}}
```

**Comportement fail-closed:**

- Consensus indisponible → status = "PENDING" (pas APPROVED)
- Timeout → status = "PENDING"
- HIGH risk en simulation → status = "PENDING"

### FTS5 Retrieval (P1.4)

```python
from python.helpers.legal_orchestrator import retrieve_from_fts5_index

ctx = retrieve_from_fts5_index(
    query="article 1134 code civil",
    jurisdiction="fr",
    max_results=5,
    correlation_id="corr_123",
)
# Utilise l'index SQLite FTS5 dans LEGAL_INDEX_PATH
```

**Variables:**

| Variable | Description | Défaut |
|----------|-------------|--------|
| `LEGAL_USE_FTS5_INDEX` | Utiliser l'index FTS5 | `1` |
| `LEGAL_INDEX_PATH` | Chemin vers l'index | `data/legal_index` |

### LLM Draft FIRAC (P1.3)

```python
from python.helpers.legal_orchestrator import build_legal_draft_with_llm

draft = await build_legal_draft_with_llm(
    query="...",
    legal_context=ctx,
    retrieval_context=retrieval_ctx,
    correlation_id="corr_123",
    call_llm_func=my_llm_func,  # async LLM function
)
```

**Contraintes:**

- Tous les claims doivent être CITED ou HYPOTHESIS
- UNSUPPORTED claims bloqués pour OPERATIONAL/BOARD
- Fallback vers draft basique si LLM échoue

### HTML Rendering robuste (P1.5)

```python
from python.helpers.legal_rendering import render_legal_output

# Markdown
md = render_legal_output(output, format="md")

# HTML (avec fallback natif si markdown lib indisponible)
html = render_legal_output(output, format="html")
```

**Garanties HTML:**

- Bandeau toujours présent
- Disclaimer toujours présent
- Sources toujours présentes (non-refusal)
- CSS inline pour portabilité

---

---

## P2 — Runtime Wiring + Réalité Terrain

### Router Hook (P2.a)

Le hook router dans `python/extensions/legal_safe_mode/_10_legal_safe_integration.py` :

```python
# Extension détecte automatiquement si le pipeline doit être utilisé
if self.should_use_legal_pipeline() and user_text:
    result = await self._execute_legal_pipeline(agent, user_text, correlation_id)
```

**Feature flags:**

| Variable | Description | Défaut |
|----------|-------------|--------|
| `LEGAL_PIPELINE_HOOK` | Activer le hook router | `1` |
| `KOREV_LEGAL_SAFE_MODE` | Mode legal-safe global | `false` |

### Corpus Fixture (P2.b)

```python
from tests.fixtures.legal_corpus import create_test_index, CORPUS

# Créer un index de test avec 20 docs
index = create_test_index(tmp_path)

# Rechercher
results = index.search("article 1103", limit=5)
```

**Contenu:**

- 7 articles Code civil (1103, 1104, 1112, 1128, 1134, 1240, 1241)
- 6 articles Code du travail (L1121-1, L1152-1, L1221-1, L1225-1, L1237-11, L3121-27)
- 7 arrêts Cour de cassation (clause non-concurrence, licenciement, etc.)

### Mock LLM (P2.c)

```python
from tests.fixtures.mock_llm import create_mock_llm, assert_firac_structure

# Créer un mock LLM déterministe
llm = create_mock_llm()

response = await llm(messages=[...], temperature=0)
parsed = json.loads(response)

assert_firac_structure(parsed)  # Valide la structure FIRAC
assert_no_unsupported_claims(parsed)  # Aucun claim UNSUPPORTED
```

### PDF Rendering (P2.d)

```python
from python.helpers.legal_rendering import render_legal_output, is_pdf_available

if is_pdf_available():
    pdf_bytes = render_legal_output(output, format="pdf")
    # ou
    render_legal_output(output, format="pdf", output_path="/path/to/file.pdf")
```

---

### P6.1-VERIFY: Battery de tests "qui mérite la prod"

La mission P6.1-VERIFY ajoute une batterie de tests robustes pour le module `legal_diff`:

#### Couverture des tests

| Famille | Fichier | Tests | Description |
|---------|---------|-------|-------------|
| **Propriétés** | `test_legal_diff_properties.py` | 15 | Idempotence, symétrie, déterminisme, append-only stability |
| **Golden Files** | `test_legal_diff_golden.py` | 24 | Non-régression sur 13 cas de référence |
| **Fuzz Typo** | `test_legal_diff_fuzz_typography.py` | 30 | Robustesse aux variations typographiques |
| **Mutations** | `test_legal_diff_mutations.py` | 40 | Sensibilité aux changements normatifs |

#### Golden files (`tests/golden/legal_diff_cases/`)

13 cas couvrant:

- `01_no_change.json` - Textes identiques
- `02_add_paragraph.json` - Ajout neutre
- `03_remove_paragraph.json` - Suppression neutre
- `04_modify_small.json` - Reformulation mineure
- `05_modify_semantic_must.json` - peut→doit (aggravation)
- `06_modify_minimum.json` - Ajout minimum (aggravation)
- `07_add_exception.json` - Ajout exemption (relaxation)
- `08_remove_exception.json` - Suppression exemption (aggravation)
- `09_change_sanction.json` - Renforcement sanction (aggravation)
- `10_formatting_only.json` - Formatage seul (neutre)
- `11_interdit_autorise.json` - interdit→autorisé (relaxation)
- `12_prolongation_delai.json` - Prolongation délai (relaxation)
- `13_mixed_signals.json` - Signaux mixtes

#### Stratégie CI

- **FAST gate**: Propriétés + Golden + Mutations (sans dépendance externe)
- **NIGHTLY**: Fuzz typographique complet (25 tests supplémentaires)

#### Comment lire un échec

1. Les tests affichent le contexte complet (before/after/segments/signals)
2. Vérifier si c'est un problème de seuil (0.85) ou de lexique
3. Vérifier si le lexique manque une forme fléchie (féminin/pluriel)

#### Dette technique identifiée (P6.1-VERIFY)

~~- **Seuil 0.85**: Peut manquer des changements subtils (1-2 mots)~~ → **RÉSOLU P6.2**
~~- **Lexique base forms**: Ne détecte pas certaines formes fléchies (exemptées, autorisée)~~ → **RÉSOLU P6.2**
~~- **Normalisation typography**: Pas de normalisation unicode/apostrophes~~ → **RÉSOLU P6.2**

---

### P6.2: Hardening Diff Juridique (Unicode + Signal Override + Needle Tests)

P6.2 résout les trois failles identifiées dans P6.1-VERIFY.

#### P6.2.1 — Normalisation Unicode/Typographique

`normalize_legal_text(text: str) -> str` — fonction PURE et DÉTERMINISTE:

| Normalisation | Avant | Après |
|--------------|-------|-------|
| Unicode NFKC | décomposé | composé |
| Apostrophes | U+2019 (') | U+0027 (') |
| Tirets | U+2013 (–), U+2014 (—) | U+002D (-) |
| Espaces | NBSP (U+00A0), multiples | espace simple |
| Fins de ligne | \r\n | \n |

**Appliquée avant**: split paragraphes, calcul diff_hash

#### P6.2.2 — Signal Override (no-signal-change-ignored)

**INVARIANT**: Si un signal normatif apparaît ou disparaît, le changement est TOUJOURS rapporté.

```python
def should_force_diff(before: str, after: str) -> bool:
    """True si signals_before != signals_after"""
    ...
```

**Conséquence**: même si le ratio SequenceMatcher > 0.85 (textes très similaires), un changement `peut→doit` sera détecté.

#### P6.2.3 — Lexique fléchi minimal

Extensions grammaticales sans NLP externe:

| Mot base | Variantes ajoutées |
|----------|-------------------|
| autorisé | autorisée, autorisés, autorisées |
| obligatoire | obligatoires |
| exempté | exemptée, exemptés, exemptées |
| interdit | interdite, interdits, interdites |
| minimum | minimaux, minimale, minimales |
| peut | peuvent, pourra, pourront |
| doit | doivent, devra, devront |

#### Tests P6.2 (Needle Tests)

`tests/test_legal_diff_needle.py` — 37 tests:

| Catégorie | Tests | Description |
|-----------|-------|-------------|
| Needle peut→doit | 2 | 1-2 mots dans phrase ≥25 mots |
| Needle minimum | 2 | +minimum/-minimum détectés |
| Needle exemption | 2 | +exemption/-exemption détectés |
| Needle sanction | 2 | +sanction/-sanction détectés |
| Needle interdit→autorisé | 2 | Mutations bidirectionnelles |
| Typo-only | 6 | 0 segments après normalisation |
| Déterminisme | 3 | 10 runs → même hash |
| Signal override | 5 | Invariant no-signal-change-ignored |
| Formes fléchies | 6 | Détection autorisée, exemptées, etc. |
| Normalisation | 7 | Tests unitaires normalize_legal_text |

#### Stratégie CI mise à jour

- **FAST gate**: properties + golden + mutations + **needle** + fuzz_fast
- **NIGHTLY**: fuzz_nightly complet

#### Invariants P6.2

```text
┌─────────────────────────────────────────────────────────────────────┐
│ 🔒 NO-SIGNAL-CHANGE-IGNORED                                         │
│    Si extract_normative_signals(before) != extract_normative_signals(after)
│    → segment présent (MODIFY/ADD/REMOVE)                            │
│    → detected_signals non vide si qualification != NEUTRAL          │
└─────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────┐
│ 🔒 TYPO-ONLY = 0 SEGMENTS                                           │
│    Textes identiques après normalisation → total_segments == 0      │
│    Apostrophes, tirets, NBSP, espaces multiples ignorés             │
└─────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────┐
│ 🔒 HASH STABILITY                                                   │
│    diff_hash calculé sur textes normalisés                          │
│    Variations typo → même hash                                      │
└─────────────────────────────────────────────────────────────────────┘
```

---

### Changelog v1.4.0 (P2 Runtime Wiring)

- **P2.a Router Hook**: Extension `legal_safe_mode` appelle `run_legal_pipeline`
- **P2.b Corpus Fixture**: 20 docs légaux pour tests E2E
- **P2.c Mock LLM**: `create_mock_llm()` avec réponses FIRAC contractuelles
- **P2.d PDF Rendering**: `render_legal_output_pdf()` via evidence_document
- 83 tests (46 P0.7 + 26 P0.8-P1 + 11 P2)

### Changelog v1.3.0 (P1 Wiring)

- **P1.2 Consensus réel**: `execute_consensus()` utilise `seek_consensus()` avec LLM arbiters
- **P1.3 LLM Draft FIRAC**: `build_legal_draft_with_llm()` avec prompt structuré
- **P1.4 FTS5 Retrieval**: `retrieve_from_fts5_index()` connecté à `LegalIndex`
- **P1.5 HTML robuste**: `render_legal_output_html()` avec fallback natif
- Simulation consensus désactivée par défaut (prod mode)
- 72 tests (46 P0.7 + 26 P0.8-P1)

### Changelog v1.2.0

- **P0.8 Production Lock**: Orchestrateur unique, feature flags, observabilité
- **P0.9 Premium Output**: Rendu cabinet-grade (3 styles), templates stricts
- `run_legal_pipeline()`: Single entry point avec correlation_id
- `resolve_provenance_strict()`: Plus de TODO, erreur explicite si manquant
- `LegalPipelineMetrics`: Métriques p50/p95, compteurs
- `render_legal_output_markdown()`: Templates INFO/OPERATIONAL/BOARD
- 62 tests (46 P0.7 + 16 P0.8-P0.9)

### Changelog v1.1.0

- **P0.7 Premium Gate**: 8 invariants stricts enforced
- `generate_audit_bundle_id()`: maintenant déterministe (no timestamp)
- `build_legal_output()`: enforce consensus + provenance
- `judge_legal_draft()`: checks CLAIMS_REQUIRED et SOURCES_PRESENT stricts
- `requires_consensus()`: nouvelle fonction centrale
- `MissingInfoCode`: codes standards pour fail-closed
- 46 tests (dont 8 tests d'invariants P0.7)
