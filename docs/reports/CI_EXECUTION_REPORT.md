# Rapport d'exécution CI — Python 3.11 (vérité exécutable)

> **Date :** 2026-05-29  
> **Environnement :** macOS arm64, Python 3.11.12 (Homebrew), venv `.venv-ci311`  
> **Méthode :** reproduction locale du workflow `.github/workflows/tests.yml` via `scripts/ci_install_deps.sh` + `scripts/run_tests.sh`  
> **Contrainte respectée :** aucun changement de comportement produit (gates CI, deps, doc, variables de test uniquement).

---

## 1. Synthèse exécutive — état rouge / vert

| Gate | Commande | Résultat | Bloquant merge ? |
|---|---|:---:|---|
| **Blocking** | `./scripts/run_tests.sh blocking` | **VERT** — 708 tests (134 + 110 + 464), 1 skip | **OUI** |
| **Unit** | `./scripts/run_tests.sh unit` (+ `EVIDENCE_HMAC_KEY`) | **ROUGE** — 3807 passed, **12 failed**, 36 skipped | Non (`continue-on-error: true`) |
| **Full** | `./scripts/run_tests.sh full` | **INCOMPLET** — abort **TIMEOUT** ~70 % sur `test_reasoning_engine.py` | Non (rapport) |
| **Extended** | `./scripts/run_tests.sh extended` | Non exécuté intégralement dans cette session | Non (rapport) |

**Verdict opérationnel :** la CI peut être **verte sur les gates bloquants** dès le premier push workflow. Le gate **unit** fournit une vérité rouge exploitable (12 échecs catalogués) sans bloquer B+C. La **full-suite** ne doit pas être merge-bloquante tant que les tests non hermétiques ne sont pas isolés.

---

## 2. Installation des dépendances (durcissement figé)

### 2.1 Ordre d'installation (aligné Docker / CI)

```bash
pip install -r requirements.txt    # d'abord
pip install -r requirements2.txt   # override openai/litellm (ne pas fusionner en une commande)
pip install -r requirements.dev.txt  # inclut pytest-timeout depuis ce rapport
python -m playwright install --with-deps chromium
```

**Ne pas** exécuter `pip install -r requirements.txt -r requirements2.txt` en une seule commande : résolution impossible (`browser-use` vs `openai==1.99.5`).

### 2.2 Paquets système (Ubuntu CI — workflow)

`tesseract-ocr`, `poppler-utils`, `libsndfile1`, `libmagic1`, `ffmpeg`, `libgl1`, `libglib2.0-0`

### 2.3 Variables d'environnement CI (test, non prod)

| Variable | Valeur CI | Effet |
|---|---|---|
| `EVIDENCE_ENV` | `development` | Chemins dev/test |
| `CONSENSUS_SIMULATION` | `true` | Votes consensus simulés |
| `REDIS_URL` | `redis://localhost:6379/0` | Tests rate-limit multi-worker |
| `EVIDENCE_HMAC_KEY` | `ci-test-hmac-key-minimum-32-characters-long` | **−10 échecs unit** (session16) si absent |

### 2.4 Écarts plateforme connus

| Problème | macOS dev | Ubuntu CI (attendu) |
|---|---|---|
| `duckduckgo-search` → `pyreqwest-impersonate` (Rust) | Échec build wheel | Wheels Linux généralement OK |
| `langchain-unstructured[all-docs]` | Extra `all-docs` invalide (warning uv) | Idem — à corriger dans `requirements.txt` phase ultérieure |
| `unstructured` / PDF stack | Installe `fitz` (PyMuPDF) → casse tests AGPL | Idem si même stack |

### 2.5 Scripts ajoutés

- `scripts/ci_install_deps.sh` — installe le venv CI (repli sans `duckduckgo-search` sur macOS)
- `scripts/run_tests.sh` — cibles `blocking`, `unit`, `extended`, `full`, …

---

## 3. Gates bloquants — VERT (preuve locale Python 3.11)

```
scope     → 134 passed
fast      → 110 passed
security  → 464 passed, 1 skipped
blocking  → exit 0
```

**Exclusions documentées du gate `fast` :** `tests/test_reasoning_engine.py` (non hermétique, hang réseau/LLM malgré `CONSENSUS_SIMULATION`).

---

## 4. Gate unitaire — ROUGE (12 échecs, classés)

Commande :

```bash
EVIDENCE_HMAC_KEY=ci-test-hmac-key-minimum-32-characters-long \
REDIS_URL=redis://localhost:6379/0 \
./scripts/run_tests.sh unit
```

Périmètre : hors `tests/e2e`, `integration`, `infra`, `property`, hors `test_reasoning_engine.py`, `test_dockerfile_backend_ocr.py`, `-m "not slow"`.

### 4.1 Table de classification

| # | Test | Catégorie | Cause racine | Action phase 2 (hors scope actuel) |
|---|---|---|---|---|
| 1 | `chat_style_extension` … `test_extension_prepends_to_system_prompt` | **Régression / drift produit** | Extension injecte du **tutoiement** ; le test attend **vouvoiement** | Mettre à jour le test ou le prompt (arbitrage produit) |
| 2 | `test_session_yenoyikz_repro` … `test_T18_yenoyikz_correct_path_succeeds` | **Régression / chemin** | Chemin yenoyikz ne « réussit » plus comme attendu | Investiguer routing / fixture |
| 3 | `test_evidence_document` … `test_cover_page_toggle` | **Environnement / golden fragile** | Taille PDF `2620 > 2625` (moteur ReportLab vs WeasyPrint) | Golden ou marquer `integration` |
| 4–5 | `test_markdown_pdf_shim` … `test_fitz/pymupdf_not_importable` | **Dépendance transitive** | `unstructured`/stack installe **PyMuPDF (AGPL)** | Exclure fitz du venv CI ou marquer test `infra` |
| 6–11 | `test_pdf_characterization` (6 tests) | **Golden / env** | `Golden text mismatch` — binaires poppler/tesseract ou regen `--regen-golden` | CI avec golden figé ou job dédié |
| 12 | `test_rebrand_agent_zero` … `test_api_files_get_supports_app_path` | **Régression réelle** | `api_files_get.py` ne gère plus le préfixe `/app/` | Corriger code ou test (hors consensus) |

**Sans `EVIDENCE_HMAC_KEY` :** +10 échecs sur `test_session16_e2e_final.py` et `test_session9_storage_tokens.py` → **config CI**, pas régression produit.

---

## 5. Tests non hermétiques (à exclure du gate bloquant `full`)

| Fichier / répertoire | Symptôme | Mécanisme |
|---|---|---|
| `tests/test_reasoning_engine.py` | **TIMEOUT session** (~30 s pytest.ini) | `test_timeout_handling` : `asyncio.sleep(100)` réel + timeout global inexistant → cf. fiche quarantaine §5.1 |
| `tests/test_dockerfile_backend_ocr.py` | FAILED | Requiert **build Docker** + binaires dans image |
| `tests/e2e/` | Mixte (beaucoup PASS, dépend volume Docker) | Sessions Flask, chemins `/app` |
| `tests/integration/` | Long / PDF | Fichiers, OCR, intégrité binaire |
| `tests/infra/` | SKIPPED sans compose | Postgres / pgvector / dump-restore |
| `tests/property/` | Hypothesis / lents | Hors gate rapide |

**Full-suite locale :** arrêt à ~70 % sur `test_reasoning_engine.py::TestEdgeCases::test_timeout_handling` (+ timeout global).

### 5.1 Fiche de quarantaine — `test_timeout_handling`

| Champ | Valeur |
|---|---|
| **Test** | `tests/test_reasoning_engine.py::TestEdgeCases::test_timeout_handling` (L536-555) |
| **Statut** | **NON-HERMETIC / QUARANTINE CANDIDATE** |
| **Classification** | Dette d'herméticité de test — **PAS une régression produit** |
| **Symptôme** | La session pytest se bloque ~100 s puis est tuée par `pytest.ini timeout = 30` → `Timeout`, ce qui interrompt toute la full-suite (~70 %). |

**Cause probable (étayée par le code, L539-553) :**

1. Le test instancie un mock dont la coroutine fait un **`asyncio.sleep(100)` en temps réel** (horloge réelle, non simulée).
2. Il configure `ReasoningConfig(timeout_seconds=0.1)` en s'attendant à ce que le moteur coupe l'exécution.
3. Le commentaire **du test lui-même** reconnaît : *« L'implémentation actuelle n'a pas de timeout global, mais les exécuteurs individuels ont des timeouts »*. Le `timeout_seconds=0.1` n'est donc **pas appliqué** au mock injecté (`llm_executor=slow_executor`), dont l'`execute` custom court-circuite le chemin de timeout par-exécuteur.
4. Conséquence : aucun timeout applicatif ne se déclenche, le `sleep(100)` court réellement, et seul le garde-fou `pytest-timeout` (30 s) finit par tuer le test.

**Pourquoi c'est de l'herméticité, pas une régression :** le test dépend du **temps mural réel** et d'un chemin de timeout **non garanti par le contrat actuel** du moteur. Le projet sait déjà tester un timeout proprement : `tests/test_harness_integrity.py::TestTimeoutWithoutWaiting` utilise un **faux temps** et passe **instantanément**. Le comportement de sortie critique (consensus/gate) n'est pas concerné par ce test.

**Impact :**
- Sur le gate **bloquant** (`scope`/`fast`/`security`) : **aucun** — le test n'y figure pas (`test_reasoning_engine.py` exclu du `fast`).
- Sur le gate **`full`** : **bloquant de session** (interrompt la collecte des résultats des 30 % restants) → c'est précisément pourquoi `full` est **non bloquant pour le merge** et traité comme signal d'audit.
- Sur le gate **`unit`** : neutralisé (fichier exclu via `--ignore=tests/test_reasoning_engine.py`).

**Condition de réintégration dans le gate bloquant :**
Le test redevient éligible au gate bloquant lorsque **l'un** des deux est vrai :
- **(A) Réécriture hermétique** : remplacer `asyncio.sleep(100)` réel par une horloge simulée (pattern `TestTimeoutWithoutWaiting`) **et** asserter le comportement de timeout réellement garanti par le moteur (timeout par-exécuteur), sans dépendre d'un timeout global inexistant ; OU
- **(B) Implémentation d'un timeout global** dans `ReasoningEngine` honorant `timeout_seconds`, puis assertion déterministe (déclenchement < 1 s en faux temps).

Tant que ni (A) ni (B), le test reste **`@pytest.mark.integration`/quarantaine** (P0 ci-dessous) et **hors** du gate bloquant. Aucune ouverture de B+C n'est autorisée tant que ce point n'est pas neutralisé ou explicitement quarantainé via marqueur.

---

## 6. Échecs observés dans la full-suite partielle (avant abort)

| Test | Catégorie |
|---|---|
| `test_chat_style_extension` (idem unit) | Drift produit |
| `test_dockerfile_backend_ocr` (6 tests) | Docker / infra |
| `test_markdown_pdf_shim` (fitz/pymupdf) | Dépendance AGPL |
| `test_pdf_characterization` (6 tests) | Golden |

---

## 7. Plan de durcissement CI (sans changement comportement produit)

### Phase immédiate (fait ou à merger)

1. **Workflow en 4 jobs** : `blocking` (merge bloquant) + `unit` / `extended` / `full` (`continue-on-error: true`).
2. **`EVIDENCE_HMAC_KEY`** dans le workflow — supprime les faux positifs session16.
3. **`pytest-timeout`** dans `requirements.dev.txt` — plus d'install ad hoc oubliée.
4. **`scripts/ci_install_deps.sh`** + cibles `blocking` / `unit` / `extended` dans `run_tests.sh`.
5. **`.gitignore`** : `.venv-ci311/`, `.ci-logs/`, junit artifacts.

### Phase durcissement (avant de rendre `unit` bloquant)

| Priorité | Action | Type |
|---|---|---|
| P0 | **Quarantaine `test_timeout_handling`** : marqueur explicite (`@pytest.mark.integration` ou `@pytest.mark.skip(reason="NON-HERMETIC, cf. CI_EXECUTION_REPORT §5.1")`) — neutralise le blocage de session `full` | CI only (marker) |
| P0 | Marquer `@pytest.mark.integration` : `test_reasoning_engine.py`, `test_dockerfile_backend_ocr.py`, `test_pdf_characterization.py` | CI only (markers) |
| P0 | Gate `full` = `pytest -m "not integration and not e2e and not slow"` | CI only |
| P1 | Documenter/contraindre **exclusion PyMuPDF** en CI (variable `KOREV_CI_NO_PYMUPDF=1` + assert install) ou accepter skip AGPL | Env |
| P1 | Figer golden PDF sous Ubuntu uniquement (artifact) | CI infra |
| P2 | Trier les **12 échecs unit** : drift chat, rebrand api, yenoyikz | Tests / produit (phase 2 B+C) |
| P2 | Corriger `langchain-unstructured[all-docs]` → extra valide | `requirements.txt` |

### Critère pour ouvrir B+C (gate consensus/gate sortie)

- `blocking` **VERT** sur GitHub Actions (≥ 1 run vert post-merge workflow).
- `unit` **≤ N échecs** avec liste blanche explicite OU **0 failed** après tri P2.
- Aucun **TIMEOUT** sur le chemin `scope` + `fast` + `security`.
- **`test_timeout_handling` neutralisé** : soit réintégré hermétiquement (condition A/B §5.1), soit explicitement quarantainé par marqueur. **B+C restent fermés tant que ce point n'est ni neutralisé ni quarantainé.**

---

## 8. Commandes de reproduction

```bash
# 1. Environnement
./scripts/ci_install_deps.sh

# 2. Gates bloquants (doit être VERT)
PYTHON=.venv-ci311/bin/python \
  EVIDENCE_ENV=development CONSENSUS_SIMULATION=true \
  REDIS_URL=redis://localhost:6379/0 \
  ./scripts/run_tests.sh blocking

# 3. Gate unitaire (ROUGE attendu — 12 failed)
PYTHON=.venv-ci311/bin/python \
  EVIDENCE_ENV=development CONSENSUS_SIMULATION=true \
  EVIDENCE_HMAC_KEY=ci-test-hmac-key-minimum-32-characters-long \
  REDIS_URL=redis://localhost:6379/0 \
  ./scripts/run_tests.sh unit
```

Logs archivés localement : `.ci-logs/scope.log`, `fast.log`, `security.log`, `unit-gate.log`, `full-suite.log` (gitignored).

---

## 9. Références

- `docs/reports/PROD_READINESS_AUDIT.md` — risques produit (RISK-01 gate sortie)
- `docs/adr/ADR-009-response-gate-disabled.md` — gate désactivé (pas de B tant que CI non probante)
- `.github/workflows/tests.yml` — pipeline GitHub Actions
