# Audit de Mise en Production — Chaîne Consensus / Gate Critique

> Périmètre : criticality router, consensus engine (v2), CriticalDecisionGate, point de sortie `response`.
> Posture : audit hostile, secteur réglementé/critique. Aucune affirmation non vérifiable.
> Date de l'évaluation : 2026-05-29.

---

## 1. Verdict exécutif

**NON prêt pour la production en l'état**, pour une raison bloquante unique et structurelle :

> **Le gate de validation de sortie n'est jamais exécuté.** La méthode `ResponseTool.execute`
> (`python/tools/response.py`) retourne la réponse **avant** d'atteindre le bloc
> `CriticalDecisionGate`. Tout le code de validation (consensus, evidence stricte, claims non
> sourcées, bannière de fiabilité) est **inatteignable**.

Le docstring du module affirmait : *« Aucune réponse critique ne peut sortir sans validation du
gate. »* Cette affirmation était fausse. **Corrigé le 2026-05-29** (Tranche A) : le docstring de
`response.py` reflète désormais l'état réel (gate désactivé), et la désactivation est tracée dans
`docs/adr/ADR-009-response-gate-disabled.md`. La **fausse assurance documentaire est levée**
(RISK-02). En revanche, le risque sous-jacent — **absence de validation de sortie** — reste ouvert
(RISK-01) tant que la Tranche B n'est pas réalisée.

Les corrections de cohérence menées précédemment (anti-bypass `original_query`, idempotence
`_finalize_proposal`, docstrings, ADR-008) sont **correctes en isolation et testées vertes**, mais
une partie d'entre elles (notamment l'anti-bypass DEF-CDG-2) est **inerte en production** tant que le
gate de sortie n'est pas réellement appelé.

---

## 2. Cartographie réelle de l'enforcement (vérifiée)

| Étage | Composant | État réel |
|---|---|---|
| Entrée (délégation) | `python/tools/call_subordinate.py` → `router.assess()` + injection des flags consensus | ✅ **Actif** |
| Run consensus | `python/helpers/research_pipeline.py::_validate_consensus` → `python/consensus/engine.py::run_consensus` | ✅ **Actif** (chemin recherche uniquement) |
| Flag `config.require_consensus` posé sur le subordonné | consommé par la boucle agent | ⚠️ **Inerte** — `agent.py` ne lit pas ce flag ; aucune extension non plus |
| Sortie (gate) | `python/tools/response.py::ResponseTool.execute` | ❌ **Code mort** (return anticipé avant le gate) |
| Reporting | `python/helpers/reporting/evidence_native.py` (badges) + `report_job.py` (flag `require_consensus`) | ⚠️ `evidence_native.py` sélectionne `ValidationMode.CONSENSUS` et rend des badges ; `report_job.py` expose un flag `require_consensus` (défaut `False`). **Aucun des deux n'appelle** `run_consensus`. |

**Conclusion factuelle** : le consensus est réellement exécuté **uniquement** dans le pipeline de
recherche. Le gate de sortie générique et le reporting ne l'appliquent pas.

---

## 3. Nature exacte du « blocage silencieux » d'origine

Le commentaire de `response.py` justifie la désactivation par *« le gate complexe causait des
blocages silencieux »*. L'analyse du code mort montre que le gate était déjà conçu en
**fail-soft + fail-open** :

- `if not gate_result.can_emit:` → **n'interrompt pas** ; ajoute une bannière « Avertissement de
  fiabilité / Non validé par consensus » et émet quand même (méthode `_create_reliability_warning`).
- `except Exception:` → **fail-open** (log + passe).

Le symptôme réel le plus probable n'était donc pas un blocage dur mais une **bannière s'affichant sur
quasiment toutes les réponses** : `consensus_result` est presque toujours `None` (consensus non câblé
hors recherche) ⇒ `can_emit == False` ⇒ bannière systématique. La désactivation par `return`
anticipé a supprimé le bruit… **et toute la garantie avec**.

> Implication pour la décision de risque : **réactiver le gate est moins risqué que craint** (il ne
> bloque pas en dur), à condition de ne déclencher la bannière que sur du **vrai LEVEL 3** et
> d'alimenter réellement `consensus_result`. Décision fail-closed vs fail-soft : **ouverte**, à
> arbitrer.

---

## 4. Procédure d'exécution des tests

Runner unique : `scripts/run_tests.sh`. Variables de test déterministes posées automatiquement
(`EVIDENCE_ENV=development`, `CONSENSUS_SIMULATION=true`).

| Cible | Commande | Objet |
|---|---|---|
| Périmètre | `./scripts/run_tests.sh scope` | Consensus/gate/router — **baseline verte garantie en local** |
| Gate rapide | `./scripts/run_tests.sh fast` | Contrats PRISM, métacognition, harness (hermétiques) |
| Local étendu | `./scripts/run_tests.sh local` | Tout le hors-infra exécutable sur ce poste |
| Sécurité | `./scripts/run_tests.sh security` | `tests/security/` (certains cas exigent Redis) |
| **Gates bloquants CI** | `./scripts/run_tests.sh blocking` (workflow `gates-bloquants`) | **VERT** — 708 tests (cf. `CI_EXECUTION_REPORT.md`) |
| **Gate unitaire CI** | `./scripts/run_tests.sh unit` | **ROUGE** — 12 failed catalogués (non bloquant merge) |
| **Full gate (rapport)** | Job `gate-full-rapport` | Non bloquant — timeouts sur tests non hermétiques |
| Full gate (Docker local) | `./scripts/run_tests.sh docker` | Full-suite dans l'image runtime (Python 3.11+/Kali) = **contexte prod** |
| Full gate (hôte) | `PYTHON=python3.11 ./scripts/run_tests.sh full` | `pytest -q` complet — exige Python 3.10+ et toutes les deps |

### Baseline mesurée (poste dev, 2026-05-29)

| Cible | Résultat |
|---|---|
| `scope` | **134 passed** |
| `fast` | **110 passed** |

> **Réserve sur le gate `full`** : la full-suite inclut des tests **non hermétiques** (ex.
> `tests/test_reasoning_engine.py`, certains `tests/integration/` et `tests/e2e/`) qui dépendent d'un
> provider LLM ou d'un accès réseau et peuvent **se bloquer (timeout)** même avec
> `CONSENSUS_SIMULATION=true`. Avant d'ériger `full` en gate de merge **réellement** bloquant, ces
> tests doivent être soit mockés, soit marqués (`integration`/`e2e`/`slow`) et exclus du gate
> bloquant. Cf. RISK-06. Le workflow CI fourni est donc une **base à durcir**, pas une garantie
> validée de bout en bout (non exécutée dans cette itération, faute d'environnement 3.11 local).

---

## 5. Contraintes d'environnement (pourquoi la full-suite n'est pas probante en local)

1. **Python 3.9 local vs 3.10+ requis par le code.** Le poste exécute Python 3.9.6 ; de nombreux
   modules utilisent la syntaxe d'union `X | None` évaluée à l'import (TypedDict, dataclasses,
   annotations sans `from __future__ import annotations`). Sur 3.9, ces modules **échouent à la
   collection** — ce sont des **erreurs d'environnement, pas des régressions**. Les mêmes fichiers
   passent quand ils sont exécutés isolément avec leurs dépendances satisfaites.
2. **Dépendances optionnelles absentes en local** (ex. `markdownify`, ML lourd via
   `sentence-transformers`, `unstructured[all-docs]`, `openai-whisper`, `playwright`). Présentes dans
   l'image Docker, pas sur l'hôte de dev.
3. **Comportement pytest par défaut** : une seule erreur de collection **abandonne toute la session**.
   Le runner utilise `--continue-on-collection-errors` pour la cible `local` afin d'exécuter ce qui
   est importable et lister le reste dans le récapitulatif.

> **La validation full-suite probante est celle de la CI (`.github/workflows/tests.yml`, Python 3.11)
> ou de la cible `docker`.** Un poste macOS Python 3.9 ne peut pas servir de preuve de non-régression
> globale.

---

## 6. Registre de risques résiduels (style CVE)

| ID | Sévérité | Composant | Description | Statut |
|---|:---:|---|---|---|
| RISK-01 | **CRITIQUE** | `response.py::ResponseTool.execute` | Gate de sortie inatteignable (return anticipé). Aucune validation de sortie n'est appliquée. | **Ouvert** — réactivation conditionnée à ADR-009 (Tranche B, phase 2) |
| RISK-02 | **CRITIQUE** | `response.py` (docstring module) | Documentation affirmait une garantie de sécurité non tenue par le code. | **✅ Corrigé** (2026-05-29) — docstring rectifié + `ADR-009`. État réel documenté ; fausse assurance levée. |
| RISK-03 | IMPORTANT | `call_subordinate.py` → boucle agent | `config.require_consensus` posé sur le subordonné mais non consommé (`agent.py`/extensions). | **Ouvert** (Tranche C) |
| RISK-04 | IMPORTANT | `reporting/evidence_native.py` (+ flag `report_job.py`) | Badges `ValidationMode.CONSENSUS` rendus sans appel réel à `run_consensus`. | **Ouvert** |
| RISK-05 | MODÉRÉ | Suite de tests | Couverture de non-régression globale non démontrable en local (Python 3.9 + deps). | **Atténué** — runner `docker` + CI `.github/workflows/tests.yml` (Python 3.11) |
| RISK-06 | MODÉRÉ | `pytest.ini` (fast gate) | `test_reasoning_engine.py` listé comme « fast » mais non hermétique (hang réseau/LLM). | **Atténué** — exclu de la cible `fast` du runner |
| RISK-07 | MINEUR | Stack Pydantic | Code documenté v1 (`@validator`), runtime v2.11 (compat avec DeprecationWarning filtré). | **Accepté/documenté** |

---

## 7. Recommandations (ordre de priorité)

1. ~~**RISK-02 (immédiat, sans risque)** : corriger le docstring de `response.py` + ADR.~~
   **✅ FAIT (2026-05-29)** : docstring rectifié, `ADR-009` créé. Fausse assurance levée.
2. **RISK-01 (décision requise)** : choisir la doctrine de sortie (fail-closed vs fail-soft), puis
   réactiver le gate avec : déclenchement bannière limité au LEVEL 3, alimentation réelle de
   `consensus_result`, et **tests end-to-end** (entrée critique → sortie validée/bannière).
3. **RISK-03 / RISK-04** : câbler `require_consensus` dans la boucle agent et brancher le reporting
   sur `run_consensus`, ou retirer les badges trompeurs.
4. **CI** : exécuter `./scripts/run_tests.sh docker` (ou CI Python 3.11+) comme gate bloquant de merge,
   conformément aux gates documentés dans `pytest.ini`.

---

## 8. Ce qui est solide aujourd'hui

- Le moteur de consensus v2 (`python/consensus/engine.py`) et le router sont cohérents, documentés
  (ADR-008) et **verts en isolation** (`scope` = 134 tests).
- Le pipeline de recherche applique réellement le consensus (`_validate_consensus` → `run_consensus`).
- Les mécanismes anti-bypass (`original_query`) et fail-soft existent et sont testés ; ils deviennent
  effectifs dès que le gate de sortie est réactivé et correctement alimenté.
