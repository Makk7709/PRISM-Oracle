# Rapport de remédiation — chemin critique Evidence (router → consensus → sortie signée)

> **Date** : 2026-05-30
> **Branche** : `feat/critical-path-realignment`
> **Doctrine appliquée** : `docs/adr/ADR-010-critical-output-doctrine.md` (fail-closed par défaut)
> **Cartographie de référence** : `docs/audit/critical_request_path_map.md`

---

## 1. Objectif et critère de réussite

Transformer la sortie critique d'Evidence en chaîne opposable :
`entrée → criticality_router → consensus → consensus_result → signature → sortie audit-ready`,
avec comportement **fail-closed** défendable.

**Critère de réussite (mission)** : une requête critique produit une sortie **signée, vérifiable,
alimentée par un `consensus_result` réel**, et bloquée proprement si ces conditions ne sont pas
réunies. → **ATTEINT** sur le chemin de l'outil `response` (chat) **ET** sur le chemin pipeline
court-circuité (legal / adversarial / contract drafting) depuis P1-1 (30/05/2026). Voir §6 pour les
réserves résiduelles (collaboratif, medical/smoke).

---

## 2. Architecture retenue — consolidation (pas de nouvelle couche)

Conformément à ADR-010 §D7/D8 et au choix de conception validé :

- **Une seule API consensus** : `run_consensus(evidence_pack, policy) -> ConsensusDecision`
  (`python/consensus/engine.py`), atteinte via `ConsensusOrchestrator.seek_consensus`.
- **Un seul point de finalisation critique** : nouveau module
  `python/helpers/critical_output.py`, qui **consolide** la décision du gate (fail-closed/fail-soft)
  et la signature, en **réutilisant** les primitives cryptographiques existantes de
  `integrity_block.py` (HMAC-SHA256 / RSA-PSS via `log_signer`). Aucune nouvelle primitive crypto,
  aucune seconde API consensus.
- **Câblage à l'émission (2 points, 1 seule doctrine)** :
  - Chemin **chat** : l'outil `response` (`python/tools/response.py`) appelle le router puis
    `finalize_critical_output(...)` avant d'émettre.
  - Chemin **pipeline** (P1-1) : le short-circuit unique de `agent.py` appelle
    `finalize_pipeline_short_circuit(...)` (même fonction `finalize_critical_output` sous-jacente)
    pour **toute** sortie pré-calculée (legal / adversarial / contract). L'extension `legal_safe_mode`
    pose le contexte de signature (`_consensus_result`, `_pipeline_requires_consensus`, policy) ;
    `python/helpers/legal_signing.py::map_legal_consensus` traduit `LegalOutput.consensus_status` en
    `consensus_result` normalisé.
  Le blocage fail-closed est appliqué **au point d'émission** (la couche audit s'exécute après et ne
  peut pas « dé-émettre »).

---

## 3. Fichiers modifiés / créés / supprimés

### Créés
| Fichier | Rôle |
|---|---|
| `python/helpers/critical_output.py` | Gate consolidé + signature 9 champs + vérification (cœur ADR-010). |
| `python/helpers/legal_signing.py` | **(P1-1)** `map_legal_consensus` : mapping léger `consensus_status` → `consensus_result` (testable sans boot LLM). |
| `docs/adr/ADR-010-critical-output-doctrine.md` | Doctrine fail-closed (tranche l'arbitrage ADR-009). |
| `docs/audit/critical_request_path_map.md` | Cartographie réel vs attendu. |
| `tests/test_critical_output_doctrine.py` | 15 tests unitaires (9 cas doctrinaux + variantes). |
| `tests/e2e/test_critical_request_signed_output.py` | 2 tests E2E (chaîne réelle + fail-closed). |
| `tests/test_response_tool_failclosed.py` | 2 tests (garde-fou P0-1 : fail-closed si critique/indéterminé). |
| `tests/test_legal_pipeline_signed_output.py` | **(P1-1)** 13 tests (mapping 6 statuts + finalisation legal + anti-tamper + fail-closed + E2E extension réelle). |

### Modifiés
| Fichier | Changement |
|---|---|
| `python/tools/response.py` | Suppression du **code mort** (gate inatteignable + `_create_reliability_warning`) ; câblage du gate consolidé actif ; sortie signée exposée via `Response.additional["signed_output"]`. |
| `agent.py` | **(P1-1)** Short-circuit pipeline recâblé via `finalize_pipeline_short_circuit` (signature v2) avec garde-fou fail-closed identique à P0-1 ; purge des clés de signature après émission. |
| `python/extensions/legal_safe_mode/_10_legal_safe_integration.py` | **(P1-1)** Helper `_set_signing_context` + pose du contexte de signature aux 3 branches succès (legacy legal, adversarial, contract drafting). |
| `python/helpers/critical_output.py` | **(P1-1)** Ajout `finalize_pipeline_short_circuit` (lecture du contexte agent → `finalize_critical_output`). |
| `python/consensus/engine.py` | Docstring corrigée (références aux modules supprimés / dépréciés). |
| `docs/adr/ADR-009-response-gate-disabled.md` | Pointeur vers ADR-010 (Tranche B tranchée). |
| `python/helpers/research_consensus_integration.py` | Bannière **DÉPRÉCIÉ** (migration P1). |
| `python/helpers/research_pipeline.py` | Bannière **DÉPRÉCIÉ** (migration P1). |
| `tests/test_consensus_entrypoint_delegation.py` | Retrait des 2 tests des modules supprimés ; conserve la délégation orchestrateur→engine. |
| `tests/test_observability_logs.py` | Retrait du test du wrapper MCP supprimé ; conserve router/engine. |

### Supprimés (modules orphelins, 0 appelant production — vérifié)
| Fichier | Justification |
|---|---|
| `python/helpers/consensus_integration.py` | `ResearchPipeline` legacy : aucun import production (tests/`__main__` seulement). |
| `python/helpers/consensus_mcp_integration.py` | Façade MCP : aucun import production. |
| `tests/test_dossier_confidence_calculated.py` | Testait `_compute_dossier_confidence` (fonction morte du module supprimé). |

**Bilan diff (phase chat)** : 12 fichiers, +165 / −1407 lignes (net **−1242** : suppression de dette).
**Ajout P1-1 (chemin legal)** : 2 fichiers créés (`legal_signing.py`, `test_legal_pipeline_signed_output.py`)
+ 4 fichiers modifiés (`agent.py`, extension legal_safe, `critical_output.py`, docs), sans suppression
de comportement métier (le rendu des pipelines existants est conservé, encapsulé par la signature).

---

## 4. Doctrine appliquée (ADR-010, résumé exécutable)

| Condition | Comportement implémenté |
|---|---|
| `requires_consensus=True` + `consensus_result` APPROVED + secret présent | **EMIT_SIGNED** (sortie signée 9 champs). |
| `requires_consensus=True` + consensus absent/REJECTED/NO_CONSENSUS/INFRA_FAILURE/incohérent | **FAIL_CLOSED** (bloqué), sauf… |
| …`policy.fail_soft_allowed=True` (explicite) | **FAIL_SOFT_BANNER** (émis + bannière « NON VALIDÉE » + signé). |
| Secret de signature absent **en production** + sortie critique | **FAIL_CLOSED**. |
| `requires_consensus=False` (non critique) | **EMIT_NONCRITICAL_SIGNED** (signé, jamais bloqué, **pas de bannière** → pas de régression UX). |

La signature couvre les **9 champs** : `input_hash`, `output_hash`, `consensus_result_hash`,
`criticality_level`, `policy_id`, `policy_version`, `timestamp`, `trace_id`, `model`,
`human_review_required` (`signature_version=2`).

---

## 5. Preuves de tests

**Commande exacte :**
```bash
EVIDENCE_ENV=development CONSENSUS_SIMULATION=true \
  .venv-ci311/bin/python -m pytest \
  tests/test_critical_output_doctrine.py \
  tests/e2e/test_critical_request_signed_output.py \
  tests/test_response_tool_failclosed.py \
  tests/test_consensus_entrypoint_delegation.py \
  tests/test_observability_logs.py -q
```
**Résultat : `22 passed`.**

Régression élargie (consensus + intégrité + criticité) :
```bash
EVIDENCE_ENV=development CONSENSUS_SIMULATION=true \
  .venv-ci311/bin/python -m pytest \
  tests/test_prism_consensus.py tests/test_anti_bypass.py tests/test_research_bypass.py \
  tests/test_evidence_prism_integration.py tests/test_session8_integrity_renderer.py \
  tests/test_session10_hardening.py tests/test_session13_document_hash_rsa.py -q --timeout=120
```
**Résultat : `168 passed`.**

Couverture doctrinale (9 cas exigés) :

| Cas mission | Test | Verdict |
|---|---|---|
| router → requires_consensus=true | `test_router_returns_requires_consensus_true` | ✅ |
| consensus_result peuplé | `test_valid_consensus_emits_signed` / E2E | ✅ |
| absence consensus_result → fail-closed | `test_missing_consensus_fail_closed` | ✅ |
| consensus_result invalide → fail-closed | `test_invalid_consensus_fail_closed` (paramétré) | ✅ |
| fail-soft seulement si policy explicite | `test_fail_soft_requires_explicit_policy` | ✅ |
| signature avec secret valide | `test_signature_generated_with_secret` | ✅ |
| signature refusée si payload modifié | `test_signature_rejected_on_tamper` | ✅ |
| absence secret HMAC en prod → fail-closed | `test_no_secret_in_production_fail_closed` | ✅ |
| consensus non requis → sortie signée | `test_non_critical_output_is_signed` | ✅ |
| **E2E** entrée→router→consensus réel→signé→vérifié→tamper | `test_critical_request_to_signed_output_full_chain` | ✅ |

> Le E2E exécute le **vrai moteur PRISM** (`run_consensus`) ; seuls les **appels LLM aux arbitres**
> sont simulés (`CONSENSUS_SIMULATION=true`), garde-fou de test standard du dépôt.

### Preuves P1-1 — chemin pipeline legal

**Commande exacte :**
```bash
EVIDENCE_ENV=development CONSENSUS_SIMULATION=true \
  python3 -m pytest tests/test_legal_pipeline_signed_output.py -q
```
**Résultat : `13 passed`.**

| Cas P1-1 | Test | Verdict |
|---|---|---|
| mapping `consensus_status` (APPROVED/REJECTED/NO_CONSENSUS/INFRA_FAILURE/None/"") | `test_map_legal_consensus` (paramétré ×6) | ✅ |
| legal APPROVED → sortie signée opposable | `test_legal_approved_emits_signed` | ✅ |
| legal REJECTED + policy fail-soft explicite → bannière + signé | `test_legal_rejected_fail_soft_banner` | ✅ |
| legal REJECTED **sans** fail-soft → fail-closed | `test_legal_rejected_without_failsoft_blocks` | ✅ |
| legal sans consensus (INFO/low-risk) → signé non critique, sans bannière | `test_legal_no_consensus_noncritical_signed` | ✅ |
| anti-tamper sortie legal signée | `test_legal_signed_output_tamper_detected` | ✅ |
| secret absent en prod + sortie legal critique → fail-closed (D6) | `test_legal_no_secret_production_fail_closed` | ✅ |
| **E2E** extension réelle `_set_signing_context` → `finalize_pipeline_short_circuit` → signé + tamper | `test_legal_extension_set_signing_context_e2e` | ✅ |

> L'E2E importe la **vraie** extension `legal_safe_mode` (sous `CONSENSUS_SIMULATION=true`) et exécute
> la fonction réelle consommée par `agent.py`, verrouillant le contrat writer/reader.

---

## 6. Limites restantes

1. **Chemin pipeline legal — RÉSOLU (P1-1).** Le short-circuit de `agent.py` passe désormais par
   `finalize_pipeline_short_circuit` → signature v2 (9 champs) ou fail-closed. Réserve mineure : pour
   `REJECTED`/`NO_CONSENSUS`/`INFRA_FAILURE`, la policy `legal-pipeline` autorise **explicitement** le
   fail-soft (bannière « NON VALIDÉE » + signature) plutôt que de remplacer la sortie déjà rendue par
   le pipeline ; choix doctrinal documenté (D4), à durcir en fail-closed strict si l'auditeur l'exige.
2. **Double mécanisme de signature transitoire.** `integrity_block` (v1, 5 champs) reste utilisé pour
   le *bloc d'intégrité du rapport d'audit* ; `critical_output` (v2, 9 champs) est la signature
   *opposable de sortie*. Cohabitation documentée, non contradictoire, mais à unifier. **P2.**
3. **Récupération de la requête à l'émission** repose sur `agent.last_user_message` ; robuste mais
   dépend de l'état de l'agent. **P2.**
4. **`consensus_result` n'est peuplé sur le chemin chat que par la délégation** (`call_subordinate`).
   Une requête critique répondue **directement** (sans délégation) sera donc **fail-closed** — c'est
   doctrinalement voulu, mais cela impose que les requêtes critiques transitent par un chemin qui
   exécute réellement le consensus.
5. **Modules dépréciés non supprimés** (`research_consensus_integration`, `research_pipeline`) :
   importés par l'agent médical et `tools/smoke_test`. Suppression différée pour éviter une
   régression silencieuse de sécurité médicale. **P1.**

---

## 7. Risques résiduels

| ID | Risque | Sévérité | Mitigation |
|---|---|---|---|
| RR-1 | ~~Le garde-fou `except Exception` de `response.py` émet la réponse non signée si le gate plante.~~ | ~~Important~~ **RÉSOLU** | Corrigé (P0-1) : fail-closed si criticité True/indéterminée ; texte brut seulement si non-criticité prouvée (`test_response_tool_failclosed.py`). |
| RR-2 | Activation du fail-closed en prod : une requête critique répondue en direct sera bloquée → changement de comportement visible. | Important | Déploiement via PR ; rollout à surveiller ; doctrine = voulu. |
| RR-3 | ~~Le chemin pipeline (legal) reste sur signature v1 (5 champs).~~ | ~~Modéré~~ **RÉSOLU** | P1-1 : short-circuit recâblé sur signature v2 + fail-closed (`test_legal_pipeline_signed_output.py`). |
| RR-5 | Policy `legal-pipeline` autorise le fail-soft (bannière) sur consensus non APPROVED. | Mineur | Choix doctrinal explicite (D4) ; durcissable en fail-closed strict via `fail_soft_allowed=False`. |
| RR-4 | `human_review_required` / `model` peuvent être `None` à l'émission (métadonnées non toujours disponibles). | Mineur | Champs optionnels signés comme `null` (déterministe). |

---

## 8. Prochaines recommandations (priorisées)

- ~~**P1** Recâbler le short-circuit pipeline (`agent.py`) sur `finalize_critical_output`~~ — **FAIT** (P1-1).
- **P1** Migrer l'agent médical (`agents/medical/tools/prism_integration.py`) et `tools/smoke_test`
  vers l'API canonique, puis **supprimer** `research_consensus_integration` et `research_pipeline`.
- ~~**P1** Durcir le garde-fou d'exception de `response.py` (RR-1)~~ — **FAIT** (P0-1).
- **P2** Unifier `integrity_block` (v1) et `critical_output` (v2) derrière une seule représentation
  de signature.
- **P2** Persister `signed_output` dans le rapport d'audit + exposer `verify_evidence_signature` via
  un endpoint d'audit (vérification a posteriori automatisée).
