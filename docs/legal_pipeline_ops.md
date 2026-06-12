# Legal Pipeline Operations Guide

> **P3 Production Hardening** — Runbook pour l'exploitation du pipeline juridique KOREV Evidence.

---

## Table des matières

1. [Feature Flags](#feature-flags)
2. [Budget & Timeouts](#budget--timeouts)
3. [CI Gates](#ci-gates)
4. [Index Management](#index-management)
5. [Diagnostic REFUSAL](#diagnostic-refusal)
6. [Metrics](#metrics)
7. [Troubleshooting](#troubleshooting)

---

## Feature Flags

| Variable | Description | Défaut | Impact |
|----------|-------------|--------|--------|
| `LEGAL_PIPELINE_ENABLED` | Active/désactive le pipeline | `1` | Si `0`, toutes les requêtes → REFUSAL |
| `LEGAL_PIPELINE_HOOK` | Active le hook router dans l'extension | `1` | Si `0`, le mode legal_safe ne route pas vers le pipeline |
| `LEGAL_PIPELINE_IDEMPOTENCE` | Active le cache idempotent | `1` | Si `0`, chaque requête est recalculée |
| `LEGAL_CONSENSUS_SIMULATION` | Mode simulation pour le consensus | `0` (prod) | Si `1`, pas d'appels LLM pour consensus |
| `LEGAL_USE_FTS5_INDEX` | Utilise l'index FTS5 pour retrieval | `1` | Si `0`, fallback sur retrieval basique |
| `LEGAL_INDEX_PATH` | Chemin vers l'index FTS5 | `data/legal_index` | Doit pointer vers un index valide |

### Exemple de configuration production

```bash
export LEGAL_PIPELINE_ENABLED=1
export LEGAL_PIPELINE_IDEMPOTENCE=1
export LEGAL_CONSENSUS_SIMULATION=0  # Production: appels LLM réels
export LEGAL_USE_FTS5_INDEX=1
export LEGAL_INDEX_PATH=/data/legal_index
```

---

## Budget & Timeouts

### Configuration des budgets (en ms)

| Variable | Description | Défaut | Recommandé prod |
|----------|-------------|--------|-----------------|
| `LEGAL_BUDGET_TOTAL_MS` | Budget total pipeline | 12000 | 12000-15000 |
| `LEGAL_BUDGET_RETRIEVAL_MS` | Budget FTS5 retrieval | 3000 | 3000-5000 |
| `LEGAL_BUDGET_LLM_DRAFT_MS` | Budget génération draft FIRAC | 5000 | 5000-8000 |
| `LEGAL_BUDGET_JUDGE_MS` | Budget judge (local) | 500 | 500 |
| `LEGAL_BUDGET_CONSENSUS_MS` | Budget consensus LLM | 8000 | 8000-12000 |
| `LEGAL_BUDGET_RENDERING_MS` | Budget rendering MD/HTML | 1000 | 1000 |

### Comportement timeout

Si une étape dépasse son budget :

1. **Retrieval timeout** → REFUSAL avec `missing_info=["retrieval_timeout"]`
2. **Consensus timeout** (si requis) → REFUSAL avec `missing_info=["consensus_timeout"]`
3. **Rendering timeout** → Fallback sur rendering basique

**Invariant** : Jamais de `SAFE_ANALYSIS` si consensus requis et timeout.

---

## CI Gates

### FAST Gate (PR/Push)

Exécuté sur chaque PR et push.

```bash
# Variables
CI_NIGHTLY=0
LEGAL_USE_FTS5_INDEX=0

# Commande
pytest tests/test_legal_*.py -k 'not nightly' -v
```

**Ce qui est testé** :

- P0.7 invariants (46 tests)
- P0.8-P1 orchestrator (26 tests)
- P2 runtime wiring (11 tests)
- P3 idempotence & budget (20+ tests)

**Ce qui n'est PAS testé** :

- FTS5 index retrieval
- E2E avec corpus réel

### NIGHTLY Full

Exécuté quotidiennement à 2:00 AM UTC.

```bash
# Variables
CI_NIGHTLY=1
LEGAL_USE_FTS5_INDEX=1
LEGAL_INDEX_PATH=data/legal_index

# Build index
python scripts/build_legal_index_test.py --output data/legal_index

# Run tests
pytest tests/test_legal_*.py -v
```

**Ce qui est testé** :

- Tout le FAST gate
- FTS5 index retrieval réel
- E2E avec corpus de 20 documents
- Validation provenance stricte

---

## Index Management

### Build de l'index de test

```bash
# Build avec corpus fixture (20 docs)
python scripts/build_legal_index_test.py --output data/legal_index --verbose

# Validation seule (sans build)
python scripts/build_legal_index_test.py --validate-only
```

### Structure de l'index

```text
data/legal_index/
├── index.sqlite          # Index FTS5
├── build_report.json     # Rapport de build
└── chunks/               # Chunks indexés
```

### Mise à jour du corpus

1. Modifier `tests/fixtures/legal_corpus.py`
2. Valider la provenance :

   ```bash
   python scripts/build_legal_index_test.py --validate-only
   ```

3. Reconstruire l'index :

   ```bash
   python scripts/build_legal_index_test.py --output data/legal_index
   ```

### Provenance requise

Chaque document doit avoir :

```python
{
    "provenance": {
        "source": "legi",           # Source (legi, cass, etc.)
        "source_name": "Légifrance", # Nom lisible
        "origin_url": "https://...", # URL de la source
        "license_name": "Licence Ouverte 2.0",  # Licence
        "access_mode": "api",        # Mode d'accès
    }
}
```

---

## Diagnostic REFUSAL

### Causes de REFUSAL

| `missing_info` | Cause | Action |
|----------------|-------|--------|
| `no_sources` | Aucune source trouvée | Vérifier l'index, reformuler la query |
| `insufficient_provenance` | Provenance manquante | Vérifier le corpus |
| `consensus_required_not_approved` | Consensus requis mais non approuvé | Vérifier les arbiters LLM |
| `consensus_timeout` | Timeout sur consensus | Augmenter `LEGAL_BUDGET_CONSENSUS_MS` |
| `retrieval_timeout` | Timeout sur retrieval | Augmenter `LEGAL_BUDGET_RETRIEVAL_MS` |
| `judge_failed` | Échec au judge (claims non sourcés, etc.) | Vérifier le draft |
| `legal_pipeline_disabled` | Pipeline désactivé | Vérifier `LEGAL_PIPELINE_ENABLED` |

### Exemple d'output REFUSAL

```json
{
  "mode": "refusal_request_info",
  "answer": "Information insuffisante pour fournir une analyse.",
  "missing_info": ["no_sources"],
  "audit_bundle_id": "audit_a1b2c3d4",
  "citations": [],
  "consensus_status": null
}
```

### Debug d'un REFUSAL

1. Vérifier les logs JSON :

   ```bash
   grep "correlation_id" logs/legal_pipeline.log | jq .
   ```

2. Chercher l'événement `legal_pipeline_end` :

   ```json
   {
     "event": "legal_pipeline_end",
     "correlation_id": "xxx",
     "output_mode": "refusal_request_info",
     "missing_info": ["no_sources"]
   }
   ```

3. Remonter les événements :
   - `legal_retrieval_end` → Vérifier `total_results`
   - `judge_result` → Vérifier `verdict` et `missing_info`
   - `consensus_required` → Si présent, vérifier le consensus

---

## Metrics

### Accès aux metrics

```python
from python.helpers.legal_orchestrator import get_legal_pipeline_metrics

metrics = get_legal_pipeline_metrics()
print(metrics.to_dict())
```

### Metrics disponibles

| Metric | Description |
|--------|-------------|
| `requests_total` | Nombre total de requêtes |
| `refusals_total` | Nombre de REFUSAL |
| `timeout_total` | Nombre de timeouts |
| `idempotent_hits` | Hits du cache idempotent |
| `double_run_blocked` | Tentatives de double-run bloquées |
| `latency_p50_ms` | Latence médiane |
| `latency_p95_ms` | Latence p95 |
| `retrieval_p50_ms` | Latence retrieval p50 |
| `consensus_p50_ms` | Latence consensus p50 |

### Export des metrics (CI)

```bash
python -c "
from python.helpers.legal_orchestrator import get_legal_pipeline_metrics
import json
print(json.dumps(get_legal_pipeline_metrics().to_dict(), indent=2))
" > metrics.json
```

---

## Troubleshooting

### "Index not available"

```text
LEGAL_INDEX_AVAILABLE = False
```

**Causes** :

- Module `python.legal_sources.indexing` non importable
- Index SQLite absent ou corrompu

**Solutions** :

1. Vérifier l'installation : `pip install -e .`
2. Reconstruire l'index : `python scripts/build_legal_index_test.py`

### "Double-run blocked"

```json
{"event": "legal_pipeline_skip_duplicate", "correlation_id": "xxx"}
```

**Cause** : Le pipeline a déjà été exécuté pour ce `correlation_id`.

**Solution** : C'est le comportement attendu (P3.2). Si vous voulez forcer une ré-exécution, utilisez un nouveau `correlation_id`.

### "Idempotent cache hit"

```json
{"event": "idempotent_cache_hit", "idempotency_key": "xxx"}
```

**Cause** : La requête a déjà été exécutée avec les mêmes paramètres.

**Solution** :

- C'est le comportement attendu (P3.1)
- Pour forcer le recalcul : `LEGAL_PIPELINE_IDEMPOTENCE=0`
- Ou modifier la query/context

### "Consensus timeout"

```json
{"event": "step_timeout", "step": "consensus", "budget_ms": 8000}
```

**Causes** :

- LLM arbiters trop lents
- Réseau lent vers les LLM

**Solutions** :

1. Augmenter `LEGAL_BUDGET_CONSENSUS_MS`
2. Vérifier la latence LLM
3. En test : utiliser `LEGAL_CONSENSUS_SIMULATION=1`

---

## Exemples d'outputs

### APPROVED_POSITION (md)

```markdown
# ⚖️ POSITION JURIDIQUE VALIDÉE

> 🟢 Cette analyse a été approuvée par consensus.

## Faits
- Question relative aux conditions de validité d'un contrat

## Règles applicables
- **Art. 1128 C. civ.** : Conditions de validité du contrat

## Application
L'article 1128 du Code civil énonce les trois conditions...

---
**Audit** : `audit_abc123` | **Consensus** : APPROVED
```

### REFUSAL (html)

```html
<div class="legal-banner refusal">
  ⚠️ INFORMATION COMPLÉMENTAIRE REQUISE
</div>
<div class="legal-content">
  <p>Les informations fournies ne permettent pas...</p>
  <p><strong>Informations manquantes :</strong> no_sources</p>
</div>
<div class="legal-disclaimer">
  Cette réponse ne constitue pas un avis juridique.
</div>
```

---

## Changelog

### v1.0.0 (P3)

- Initial ops documentation
- Feature flags reference
- Budget configuration
- CI gates (FAST + NIGHTLY)
- Diagnostic REFUSAL guide
- Metrics reference
