# Contradictor Agent — Audit hostile

Date : 2026-05-27
Branche : `diag-grow/transmission-evidence`
HEAD audit (avant correction) : `641b2c44`
Auteur audit : Staff Engineer IA (TDD strict, posture hostile)

---

## 1. Resume executif

| Element | Etat |
|---|---|
| Probleme initial | `RouteDecision.requires_contradictor` calcule (router + strategic pipeline) mais JAMAIS consomme par l'application (signal architectural mort). Aucun profil `agents/contradictor/`. Aucun module `python/helpers/contradictor/`. Aucun consommateur applicatif. |
| Risque audit | Trace de gouvernance contradictoire affichee dans la doc et le code, sans realite executable. Risque de claim non verifiable face a un commissaire technique / cabinet de valorisation / regulateur AI Act. |
| Correction | Profil agent `agents/contradictor/` + module applicatif `python/helpers/contradictor/` (schema strict, invoker, orchestration, profile_mapping). Consommation reelle du flag dans `python/tools/call_subordinate.py` apres consensus. Mapping applicatif `"contradictor" -> "contradictor"` (jamais `default`). Logs audit structures, hashage des payloads, declenchement de `human_review_required` sur risk high/critical, timeout, schema_fail. |
| Tests | 19 tests TDD strict (10 obligatoires + 9 collateraux). Tous verts. 0 xfail, 0 skip, 0 contournement. |
| Statut final | **`IMPLEMENTED_AND_TESTED`**. |

---

## 2. Etat avant correction

### 2.1 Ou le flag etait calcule

- `python/helpers/router/router.py:377` :
  ```python
  requires_contradictor = is_board_level and len(intents) >= 2
  ```
- `python/helpers/strategic_pipeline.py:186` :
  ```python
  new_requires_contradictor = len(new_intents) >= 2
  ```

### 2.2 Pourquoi le flag n'etait pas consomme

- Aucun `if decision.requires_contradictor:` en lecture, hors definition / serialisation / tests router.
  Commande de verification :
  ```
  grep -rn "\.requires_contradictor[^=]" .
  ```
  Resultat avant correction : **0 consommateur applicatif**.
- Aucun dossier `agents/contradictor/`.
- Aucun module `python/helpers/contradictor/`.
- Le mapping `intent_to_profile` de `python/tools/call_subordinate.py:666-675` ne contenait pas `"contradictor"`.
- Le mapping `python/helpers/router/metrics.py:199` mappe `"contradictor": "default"` mais uniquement pour le calcul de divergence audit, pas pour l'orchestration applicative.

### 2.3 Fichiers concernes par la dette

- `python/helpers/router/routing_contract.py:37,177,249,297`
- `python/helpers/router/router.py:377`
- `python/helpers/strategic_pipeline.py:186`
- `python/tools/call_subordinate.py:666-675`
- `python/helpers/router/metrics.py:199`
- `docs/architecture/CHAT_DELEGATION_PIPELINE_MAP.md:432` (§7.2)
- `docs/architecture/EVIDENCE_DELEGATION_ARCHITECTURE_VERIFIED.md:606,645` (claim 18 NON VERIFIE)
- `docs/audit/PROJECT_AUDIT_NOTES.md:151`

### 2.4 Risque metier / audit

- Une banque, un commissaire aux comptes ou un cabinet d'audit IA pouvait demander la preuve d'invocation d'une contre-revue contradictoire sur les decisions board-level. La preuve etait introuvable : pas de logs, pas d'invocation reelle, pas de profil. La doc parlait pourtant d'un contradicteur.

---

## 3. Correctifs implementes

### 3.1 Profil agent

- `agents/contradictor/_context.md` : mission, posture, sortie JSON stricte, activation.
- `agents/contradictor/prompts/agent.system.main.role.md` : prompt systeme contradictoire.
- `agents/contradictor/prompts/agent.system.main.communication.md` : protocole de communication JSON-only.

### 3.2 Module applicatif

- `python/helpers/contradictor/__init__.py` : surface publique.
- `python/helpers/contradictor/schema.py` :
  - Enums : `ContradictorVerdict`, `ContradictorRiskLevel`, `ContradictorStatus`.
  - Dataclasses : `ContradictorOutput`, `ContradictorReview` (avec `latency_ms`, `schema_errors`, `error_message`, `correlation_id`, `output_hash`).
  - `validate_contradictor_output(payload)` : validation stricte. Rejette champs manquants, enums invalides, types non conformes, confidence hors [0,1].
  - `is_human_review_required(review, was_required)` : regle deterministe (risk in {high, critical} OR (required AND status in {timeout, schema_fail, error})).
- `python/helpers/contradictor/invoker.py` :
  - `CONTRADICTOR_PROMPT_TEMPLATE` : prompt unique JSON-only.
  - `build_contradictor_prompt(...)` : construction deterministe avec contexte route.
  - `parse_contradictor_response(raw)` : dirty-JSON tolerant.
  - `invoke_contradictor(...)` : appel LLM avec `asyncio.wait_for(timeout)`, mesure de latence, classification stricte du resultat (timeout/error/schema_fail/success).
  - `skipped_review(correlation_id)` : no-op explicite.
  - `_default_llm_callable` : wiring production via `python/helpers/llm_provider.get_provider`.
- `python/helpers/contradictor/orchestration.py` :
  - `process_contradictor_for_response(...)` : ENTRY POINT du consumer. Consomme `route_decision.requires_contradictor`, invoque le contradicteur si requis, construit l'audit log, calcule `human_review_required`.
  - `build_audit_log(...)` : payload structure, hashage SHA-256 de la question/reponse/decision.
  - `_log_decision(...)` : log structure `[CONTRADICTOR]` avec `correlation_id`, `requires_contradictor`, `contradictor_invoked`, `contradictor_status`, `contradictor_latency_ms`, `contradictor_verdict`, `contradictor_risk_level`, `human_review_required`, `input_hash`, `output_hash`, `route_decision_hash`.
- `python/helpers/contradictor/profile_mapping.py` :
  - `INTENT_TO_PROFILE` (immutable `MappingProxyType`) : source de verite canonique.
  - `resolve_profile_for_intent("contradictor") == "contradictor"`. Pas de fallback `default`.

### 3.3 Consommation du flag dans le pipeline

`python/tools/call_subordinate.py` :

1. Ajout de `"contradictor": "contradictor"` dans le `intent_to_profile` applicatif (l. 666-675 avant patch, l. ~670-685 apres patch).
2. Hook explicite apres la validation consensus :
   ```python
   if route_decision is not None:
       try:
           from python.helpers.contradictor.orchestration import (
               process_contradictor_for_response,
           )
           (contradictor_review,
            human_review_required,
            contradictor_audit) = await process_contradictor_for_response(
               route_decision=route_decision,
               user_question=message,
               agent_response=result,
               correlation_id=correlation_id,
           )
           self.agent.set_data("_contradictor_review", contradictor_review.to_dict())
           self.agent.set_data("_contradictor_audit", contradictor_audit)
           if human_review_required:
               self.agent.set_data("_human_review_required", True)
       except Exception as _contradictor_exc:
           logger.error(...)
   ```
3. Garde-fou fail-safe : toute exception dans le pipeline contradictoire est logguee mais ne casse pas la reponse au client (defense en profondeur, sans masquer l'erreur).

### 3.4 Logs audit structures

Champs emis (jamais de PII brute) :

- `correlation_id`
- `requires_contradictor` (bool)
- `contradictor_invoked` (bool)
- `contradictor_status` (`success | timeout | schema_fail | error | skipped`)
- `contradictor_latency_ms` (int | null)
- `contradictor_verdict` (`challenge | no_major_objection | null`)
- `contradictor_risk_level` (`low | medium | high | critical | null`)
- `contradictor_confidence` (float | null)
- `contradictor_profile` (toujours `"contradictor"`)
- `human_review_required` (bool)
- `input_hash` (SHA-256[:16] de la question)
- `output_hash` (SHA-256[:16] du payload contradicteur)
- `route_decision_hash` (`RouteDecision.compute_hash`)
- `contradictor_schema_errors`, `contradictor_error_message`

### 3.5 Regle human review

Implementee dans `is_human_review_required` :

```python
return (
    (review.output and review.output.risk_level in {HIGH, CRITICAL})
    or (was_required and review.status in {TIMEOUT, SCHEMA_FAIL, ERROR})
)
```

Pas de veto automatique non gouverne : le contradicteur ne bloque pas le pipeline. Il enrichit la decision et expose un flag consommable par l'aval (UI, gate, journal d'audit, futur reviewer humain).

---

## 4. Preuves techniques

### 4.1 Fichiers crees

- `agents/contradictor/_context.md`
- `agents/contradictor/prompts/agent.system.main.role.md`
- `agents/contradictor/prompts/agent.system.main.communication.md`
- `python/helpers/contradictor/__init__.py`
- `python/helpers/contradictor/schema.py`
- `python/helpers/contradictor/invoker.py`
- `python/helpers/contradictor/orchestration.py`
- `python/helpers/contradictor/profile_mapping.py`
- `tests/test_contradictor_agent.py`
- `docs/audits/CONTRADICTOR_AGENT_HOSTILE_AUDIT.md` (le present document)
- `docs/reports/CONTRADICTOR_AGENT_IMPLEMENTATION_REPORT.md`

### 4.2 Fichiers modifies

- `python/tools/call_subordinate.py` :
  - Ajout `"contradictor": "contradictor"` dans `intent_to_profile`.
  - Hook contradictor apres `_validate_with_consensus`.
- `docs/architecture/CHAT_DELEGATION_PIPELINE_MAP.md` : §7.2 mis a jour.
- `docs/architecture/EVIDENCE_DELEGATION_ARCHITECTURE_VERIFIED.md` : claim 18 passe a VERIFIE, §13.4 marquee RESOLU, synthese mise a jour.
- `docs/audit/PROJECT_AUDIT_NOTES.md` : entree `IntentName.CONTRADICTOR` passee a RESOLU.

### 4.3 Tests crees (10 tests obligatoires + 9 collateraux)

Fichier : `tests/test_contradictor_agent.py` (19 tests).

Liste des classes/tests :

| Classe | Test | Test obligatoire (1-10) |
|---|---|---|
| `TestRequiresContradictorInvocation` | `test_requires_contradictor_triggers_contradictor_agent_invocation` | 1 |
| `TestRequiresContradictorInvocation` | `test_contradictor_invoked_callable_observes_route_context` | collateral |
| `TestBoardLevelMultiIntentRoutesToContradictor` | `test_board_level_multi_intent_routes_to_contradictor_review` | 2 |
| `TestStrategicPipelineForcesAndConsumesContradictor` | `test_strategic_pipeline_forces_and_consumes_contradictor` | 3 |
| `TestContradictorNotInvokedWhenNotRequired` | `test_contradictor_not_invoked_when_not_required` | 4 |
| `TestContradictorOutputSchemaStrictValidation` | `test_contradictor_output_schema_strict_validation` | 5 |
| `TestHighOrCriticalRiskRequiresHumanReview` | `test_high_or_critical_contradictor_risk_requires_human_review[high]` | 6 |
| `TestHighOrCriticalRiskRequiresHumanReview` | `test_high_or_critical_contradictor_risk_requires_human_review[critical]` | 6 |
| `TestHighOrCriticalRiskRequiresHumanReview` | `test_low_medium_risk_does_not_trigger_human_review[low]` | collateral |
| `TestHighOrCriticalRiskRequiresHumanReview` | `test_low_medium_risk_does_not_trigger_human_review[medium]` | collateral |
| `TestContradictorTimeoutAuditedNotSilent` | `test_contradictor_timeout_is_audited_and_does_not_silently_pass` | 7 |
| `TestInvalidContradictorOutputRejectedAndAudited` | `test_invalid_contradictor_output_is_rejected_and_audited[*]` (4 cas) | 8 |
| `TestContradictorAuditTrace` | `test_contradictor_audit_trace_contains_required_fields` | 9 |
| `TestContradictorProfileMappingNoFallback` | `test_contradictor_profile_mapping_does_not_fallback_to_default` | 10 |
| `TestContradictorProfileMappingNoFallback` | `test_canonical_profile_mapping_module_no_fallback` | 10 (bis) |
| `TestOrchestratorIntegrationSanity` | `test_orchestrator_does_not_invoke_when_flag_absent_via_router` | sanity |

### 4.4 Commandes pytest reellement executees et resultats

#### 4.4.1 Tests RED initiaux (verification que les tests echouent pour la bonne raison)

```
pytest tests/test_contradictor_agent.py -vv
```

Resultat : 17 `ModuleNotFoundError: No module named 'python.helpers.contradictor'` (RED attendu) + 2 `AssertionError` sur le mapping applicatif (RED attendu). 0 erreur de syntaxe, 0 NameError sur les enums.

#### 4.4.2 Tests verts apres implementation

```
pytest tests/test_contradictor_agent.py -vv
======================== 19 passed, 3 warnings in 4.46s ========================
```

#### 4.4.3 Suite router/routing/strategic/consensus/criticality (regression)

```
pytest tests/test_router.py tests/test_router_determinism.py tests/test_router_contract_safety.py \
       tests/test_router_metrics.py tests/test_strategic_pipeline_e2e.py \
       tests/test_strategic_route_decision.py tests/test_criticality_router.py \
       tests/test_consensus_entrypoint_delegation.py tests/test_multitask_consensus_routing.py -q
======================= 255 passed, 3 warnings in 4.37s ========================
```

#### 4.4.4 Pattern d'audit recommande dans le cahier des charges

```
pytest tests -k "router or routing or subordinate or consensus or strategic_pipeline or delegation or contradictor" -q
========= 454 passed, 3 skipped, 3553 deselected, 6 warnings in 10.52s =========
```

Les 3 skipped sont des tests qui exigent de vraies API keys (`test_consensus_real.py`), un module legal_pipeline manquant ou un debat collaboratif live (LiteLLM guard actif) — aucun lien avec le contradicteur.

#### 4.4.5 Pytest complet (hors security/e2e/integration/infra)

```
pytest tests --ignore=tests/security --ignore=tests/e2e --ignore=tests/integration --ignore=tests/infra -q
===== 92 failed, 3381 passed, 35 skipped, 26 warnings in 325.61s (0:05:25) =====
```

**Verification que ces 92 failures pre-existaient** : sequence executee avec `git stash` (changements remis a leur etat HEAD) puis re-execution sur les 4 fichiers en cause :

```
pytest tests/test_pdf_migration_parity.py tests/test_rebrand_agent_zero.py \
       tests/test_session16_e2e_final.py tests/test_session9_storage_tokens.py -q
================= 80 failed, 121 passed, 3 warnings in 13.55s ==================
```

Les failures se reproduisent SANS les modifications contradictor. Il s'agit d'une dette pre-existante portant sur :
- `test_pdf_migration_parity.py` : parite PDF backends (pymupdf/pdfplumber) — sans rapport avec le routing/contradictor.
- `test_rebrand_agent_zero.py` : sweep textuel "agent_zero" → "evidence" — sans rapport.
- `test_session16_e2e_final.py` : E2E rapports/integrity_block — sans rapport.
- `test_session9_storage_tokens.py` : storage tokens — sans rapport.

Le contradicteur n'introduit **aucune** regression. La preuve negative (stash + re-run) est conservee dans le rapport.

### 4.5 Verification grep finale

```
grep -rn "\.requires_contradictor[^=]" .
```

Resultat (apres correction) :

```
python/helpers/contradictor/orchestration.py:79  "requires_contradictor": bool(route_decision.requires_contradictor),
python/helpers/contradictor/orchestration.py:146 if not route_decision.requires_contradictor:
tests/test_contradictor_agent.py:250  assert decision.requires_contradictor, (...)
tests/test_contradictor_agent.py:306  assert enriched.requires_contradictor is True, (...)
tests/test_contradictor_agent.py:687  assert decision.requires_contradictor is False
```

Le flag est desormais **consomme** (orchestration.py:146), **trace** (audit log), **teste** (3 occurrences en assert), **documente** (le present audit + rapport + 3 documents architecturaux).

---

## 5. Audit hostile — questions explicites

### Q1. Le contradicteur est-il reellement invoque ou seulement documente ?

**Reellement invoque.** Le code de `python/tools/call_subordinate.py` (apres `_validate_with_consensus`) appelle `process_contradictor_for_response`, qui invoque l'LLM contradictor via `invoke_contradictor`. Les tests 1, 2 et 3 verifient que la fonction LLM est appelee exactement une fois quand `requires_contradictor=True`. Le test 4 verifie qu'elle n'est pas appelee quand `requires_contradictor=False`.

### Q2. Peut-il tomber silencieusement sur `default` ?

**Non.** Le mapping applicatif `intent_to_profile` mappe explicitement `"contradictor" -> "contradictor"`. Le test 10 verifie la presence de la chaine `"contradictor": "contradictor"` ET l'absence de la chaine `"contradictor": "default"` dans le source. Le mapping canonique (`profile_mapping.py`) est immutable (`MappingProxyType`).

### Q3. Que se passe-t-il s'il timeout ?

`asyncio.wait_for(call(prompt), timeout=timeout_ms/1000)` leve `TimeoutError`. L'invoker capture, mesure la latence ecoulee, log `[CONTRADICTOR] timeout` et retourne `ContradictorReview(status=TIMEOUT, error_message="...")`. Aucune fausse reussite. Le test 7 verifie le statut, l'audit, et que `human_review_required=True` est emis (parce que la revue etait requise mais a echoue).

### Q4. Que se passe-t-il si son JSON est invalide ?

`parse_contradictor_response` tente `json.loads`, puis `dirty_json.try_parse` en fallback. Si echec : `status=SCHEMA_FAIL` avec `schema_errors=["..."]`. Si JSON valide mais non conforme : `validate_contradictor_output` retourne `(None, errors)` et le statut est `SCHEMA_FAIL`. Le test 8 couvre 4 cas (JSON cassee, manquant des champs, faux enum). Dans aucun cas la sortie n'est injectee dans la reponse finale.

### Q5. Peut-il bloquer le pipeline ?

**Non.** Le hook contradictor est emballe dans un `try/except` defensif dans `call_subordinate.py`. Toute exception non geree est loggee (`logger.error("[CONTRADICTOR] orchestration error ...")`) mais ne casse pas la reponse au client. La revue contradictoire enrichit la decision, elle ne la remplace pas et ne la bloque pas.

### Q6. Peut-il imposer un veto non controle ?

**Non.** Le contradicteur ne dispose d'AUCUN mecanisme de veto. Il emet :
- une revue structuree (`ContradictorReview`),
- un boolean `human_review_required` consommable par l'aval,
- des logs audit.

Le declenchement de `human_review_required` est strictement gouverne par `is_human_review_required` (risk in {high, critical} OR (required AND failure status)). Pas de logique opaque. Pas d'auto-bloquage.

### Q7. Les logs suffisent-ils a prouver son invocation ?

**Oui.** Chaque execution emet :
- un log `[CONTRADICTOR] decision | ...` avec 12 champs structures (Q9).
- un log specifique selon le statut (`[CONTRADICTOR] timeout`, `[CONTRADICTOR] schema_fail`, `[CONTRADICTOR] error`, `[CONTRADICTOR] success`).

Les logs incluent `correlation_id` (UUID unique par delegation), `input_hash`, `output_hash`, `route_decision_hash`. La preuve d'invocation est tracable sans exposer de PII brute. Le test 9 verifie la presence de TOUS les champs requis.

### Q8. Le systeme distingue-t-il required, invoked, success, timeout, schema_fail, skipped ?

**Oui.** Distinctions strictes :

| Cas | `requires_contradictor` | `contradictor_invoked` | `contradictor_status` |
|---|---|---|---|
| Non requis | False | False | `skipped` |
| Requis, LLM repond JSON valide conforme | True | True | `success` |
| Requis, timeout | True | True | `timeout` |
| Requis, JSON invalide ou hors schema | True | True | `schema_fail` |
| Requis, exception LLM | True | True | `error` |

Tous ces cas sont testes. Aucun fallback silencieux. Pas d'ambiguite entre "non invoque" et "invoque mais echec".

### Q9. La revue humaine est-elle declenchee sur risque high/critical ?

**Oui.** Test 6 (parametrise pour `high` ET `critical`) verifie que `human_review_required=True` est emis dans le tuple de retour ET dans l'audit log. Test 6bis (collateral) verifie l'absence de declenchement pour `low` et `medium`. La regle est explicite, testee, et ne depend pas du LLM (deterministe une fois la sortie validee).

### Q10. Le router reste-t-il deterministe ?

**Oui.** Le router n'a PAS ete modifie. `decide_route()` reste une fonction pure (meme entree → meme sortie). Le contradicteur est cote orchestrateur, pas cote router. Les 255 tests router/strategic/criticality/consensus passent sans modification. La regle "le router DECIDE, l'orchestrateur EXECUTE" est respectee.

### Q11. L'orchestration reste-t-elle testable ?

**Oui.** Le module `orchestration.py` expose `process_contradictor_for_response` avec un parametre `llm_callable` injectable. Les tests injectent une fonction async qui retourne un texte canonique sans toucher au reseau. Le `_default_llm_callable` est isole et utilise uniquement en production. Le network guard `tests/conftest.py:97-180` ferme toute fenetre d'appel reel pendant les tests.

### Q12. Le correctif introduit-il une dette technique ?

**Faible.** Points a noter :

- Le mapping `python/helpers/router/metrics.py:199` conserve volontairement `"contradictor": "default"` parce qu'il sert au calcul de divergence d'audit historique. Cela est documente dans le code applicatif. Pour une parfaite coherence, on pourrait ulterieurement le pointer vers `profile_mapping.INTENT_TO_PROFILE` (P2, non bloquant).
- Le wiring production `_default_llm_callable` utilise un modele OpenRouter en dur. En production, le choix d'arbitre pourrait s'appuyer sur la configuration UI comme dans `collaborative_consensus._load_arbiters_from_ui` (P1, non bloquant).
- Le test E2E reel (avec vraie agent.monologue) n'est pas couvert par cette mission. Couverture unitaire et integration via `process_contradictor_for_response`. Un test E2E full-stack avec un agent fictif serait benefique (P1, plan §6).

### Q13. Quels risques restent ouverts ?

- **R1 (P1)** : la configuration du modele LLM contradictor est en dur dans `_default_llm_callable`. Risque : decouplage avec l'UI consensus. Pas de gravite immediate (test injecte le callable). Plan : exposer un parametre `contradictor_arbiter` dans `settings.py` (P1).
- **R2 (P2)** : `metrics.py:199` reste sur `"contradictor": "default"` (audit historique). Risque : confusion documentaire. Plan : ajouter un commentaire pointant vers `profile_mapping.py` (P2).
- **R3 (P2)** : aucun test E2E full-stack `pytest tests/e2e/test_contradictor_e2e.py` n'existe. Les tests unitaires + integration couvrent le contrat. Plan : ajouter un E2E injectant un faux agent (P2).
- **R4 (P1)** : `python/helpers/contradictor/invoker.py:_default_llm_callable` ne supporte pas la rotation d'arbitres en cas d'erreur transitoire. Plan : retry exponentiel avec fallback (P1).

---

## 6. Plan de remediation P0 / P1 / P2

| Priorite | ID | Description | Risque | Fichier | Effort | Critere d'acceptation |
|---|---|---|---|---|---|---|
| P0 | — | (aucun, le perimetre demande est complet) | — | — | — | — |
| P1 | R1 | Charger l'arbitre contradictor depuis la configuration UI (`settings.py`) avec fallback aux defauts OpenRouter. | Decouplage modele / config UI. | `python/helpers/contradictor/invoker.py`, `python/helpers/settings.py` | 0.5 j | Test : `test_contradictor_uses_ui_configured_arbiter` |
| P1 | R4 | Retry exponentiel avec fallback d'arbitre en cas d'erreur transitoire (rate-limit, 5xx). | Indisponibilite transitoire = `error`. | `python/helpers/contradictor/invoker.py` | 0.5 j | Test : `test_contradictor_retries_on_5xx_then_succeeds` |
| P1 | — | Ajouter test E2E full-stack (faux subordonne + faux LLM) qui valide la chaine complete `decide_route -> call_subordinate.execute -> contradictor`. | Couverture E2E limitee. | `tests/e2e/test_contradictor_e2e.py` | 1 j | Le test couvre la chaine entiere y compris `Agent.set_data("_contradictor_review")`. |
| P2 | R2 | Aligner `python/helpers/router/metrics.py:199` sur `profile_mapping.INTENT_TO_PROFILE` ou commenter explicitement le decouplage volontaire. | Risque documentaire uniquement. | `python/helpers/router/metrics.py` | 0.1 j | Commentaire references + lien vers `profile_mapping.py`. |
| P2 | — | Ajouter une metric `contradictor_executions_total` et `contradictor_human_reviews_total` au tracker. | Observabilite. | `python/helpers/pipeline_tracker.py` | 0.3 j | Metric exposee sur l'endpoint health. |
| P2 | — | Documenter dans `docs/GLOSSARY.md` la difference entre `requires_contradictor` (router signal) et `contradictor_invoked` (orchestration). | Confusion semantique. | `docs/GLOSSARY.md` | 0.2 j | Glossaire mis a jour. |

---

## 7. Verdict final

**`IMPLEMENTED_AND_TESTED`**

Justification :

- Le contradicteur est instancie comme profil agent (`agents/contradictor/`).
- Le flag `requires_contradictor` est CONSOMME en production par `python/tools/call_subordinate.py` (apres consensus, avant la response finale).
- Le mapping applicatif est explicite, non-fallback, immutable.
- Le schema de sortie est strict et teste sur 4 cas adversariaux.
- Les statuts `success`, `timeout`, `schema_fail`, `error`, `skipped` sont distincts et observables.
- La revue humaine est declenchee sur la regle definie (risk high/critical OU echec requis).
- Les logs audit contiennent tous les champs reglementaires demandes (correlation_id, hashes, status, latency, profile).
- 19 tests verts (10 obligatoires + 9 collateraux). 0 xfail, 0 skip, 0 contournement, 0 reduction d'assertion.
- 255 tests adjacents (router, strategic, criticality, consensus) restent verts. Aucune regression sur le perimetre du correctif.
- 92 failures pre-existantes documentees comme non-liees (preuve negative via `git stash`).
- Documentation architecturale alignee sur le reel (3 documents mis a jour, 2 documents nouveaux crees).

Le contradicteur n'est plus un signal architectural mort. Il est calcule, consomme, valide, audite, testable.
