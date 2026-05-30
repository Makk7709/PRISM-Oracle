# Audit hostile — chemin critique Evidence (post-remédiation ADR-010)

> **Date** : 2026-05-30 · **Branche** : `feat/critical-path-realignment`
> **Posture** : auditeur réglementaire hostile. Aucune réponse rassurante non prouvée.
> **Portée prouvée** : chemin de l'outil `response` (chat) **ET** chemin pipeline court-circuité
> (legal / adversarial / contract drafting), désormais tous deux signés v2 (P1-1 résolu).
> Réserves restantes : validateur collaboratif parallèle + migration medical/smoke (voir Q3/Q10).

---

## Réponses frontales aux 10 questions

### Q1 — Peut-on encore produire une sortie critique sans `consensus_result` alors qu'un consensus est requis ?
**Chemin chat (`response`) : NON.** `finalize_critical_output` bloque (FAIL_CLOSED) si
`requires_consensus=True` et consensus absent/invalide (prouvé : `test_missing_consensus_fail_closed`,
E2E `test_critical_request_without_consensus_is_fail_closed`). Le fail-soft n'est possible qu'avec
`policy.fail_soft_allowed=True` explicite.
**Chemin pipeline (legal) : NON (P1-1 résolu).** Le short-circuit `agent.py` appelle désormais
`finalize_pipeline_short_circuit` → même gate consolidé. Le pipeline legal mappe son propre
`consensus_status` via `map_legal_consensus` : `APPROVED` → signé opposable ; `REJECTED`/`NO_CONSENSUS`/
`INFRA_FAILURE` → émis avec bannière « NON VALIDÉE » **uniquement** sous policy fail-soft explicite
(`legal-pipeline`), sinon fail-closed ; consensus non exécuté (INFO/low-risk) → signé non critique.
Prouvé : `tests/test_legal_pipeline_signed_output.py` (13 tests, dont E2E extension réelle).

### Q2 — Peut-on encore produire une sortie critique non signée ?
**Chemin chat : NON pour une sortie critique** (elle est signée, sinon bloquée).
- **Garde-fou d'exception** (`response.py`) : **CORRIGÉ (P0-1 résolu)**. En cas d'erreur du gate, le
  texte brut n'est émis **que si la non-criticité est prouvée** (`requires_consensus is False`) ;
  sinon (critique ou indéterminée) → **fail-closed** (prouvé :
  `tests/test_response_tool_failclosed.py`).
**Chemin pipeline : NON (P1-1 résolu).** Toute sortie court-circuitée est signée v2 ou fail-closed.
Le short-circuit `agent.py` applique **le même garde-fou que P0-1** : si la finalisation lève une
exception et que la sortie n'est pas prouvée non critique (`_pipeline_requires_consensus is False`),
le système émet un message **fail-closed**, jamais la sortie critique brute.

### Q3 — Existe-t-il plusieurs chemins consensus actifs concurrents ?
**OUI, encore partiellement.** Réduit : 2 modules orphelins supprimés, 2 dépréciés. **Restent actifs :**
- `run_consensus` (PRISM) — **canonique**.
- `collaborative_consensus.run_collaborative_consensus` — débat 3-rounds utilisé par
  `call_subordinate`, **n'utilise pas** `run_consensus` (subsystème parallèle).
- `legal_pipeline.requires_consensus(ctx)` — **déclencheur** distinct de `CriticalityRouter`.
→ Un seul *exécuteur* canonique, mais un *validateur parallèle* (collaboratif) et un *déclencheur*
parallèle subsistent. → **P1/P2**.

### Q4 — Existe-t-il du code mort donnant une illusion de sécurité ?
**Réduit, mais un résidu.** Le bloc gate mort de `response.py` et `_create_reliability_warning` sont
**supprimés**. **Cependant** `python/helpers/critical_decision_gate.py` (`enforce_or_route`,
`validate_final_output`) n'a désormais **plus aucun appelant production** (le chemin passe par
`critical_output`). Il reste dans l'arbre → risque d'illusion « il existe un gate » alors qu'il est
inerte. → **P2** (supprimer ou rediriger vers `critical_output`).

### Q5 — Le fail-soft peut-il s'activer sans policy explicite ?
**NON.** `OutputPolicy.fail_soft_allowed` défaut `False`. Sans policy explicite → FAIL_CLOSED
(prouvé : `test_fail_soft_requires_explicit_policy`).

### Q6 — La signature est-elle réellement vérifiable après coup ?
**OUI, fonctionnellement** (`verify_evidence_signature`, prouvé). **MAIS** aucune vérification
automatisée au moment de la lecture/audit n'est encore câblée (pas d'endpoint). La vérifiabilité est
disponible mais non *exercée* en production. → **P2**.

### Q7 — Une modification du payload invalide-t-elle bien la signature ?
**OUI.** Altération de `output` **ou** de `consensus_result` → vérification `False` (prouvé :
`test_signature_rejected_on_tamper`, E2E tamper).

### Q8 — Le système échoue-t-il proprement si le secret HMAC est absent ?
**OUI en production sur sortie critique** : FAIL_CLOSED (prouvé :
`test_no_secret_in_production_fail_closed`). Hors critique / en dev : émission dégradée non signée,
**tracée** (`EMIT_UNSIGNED_DEGRADED`), jamais silencieuse.

### Q9 — Les tests E2E prouvent-ils le chemin réel ou seulement un chemin mocké ?
**Chemin réel pour tout sauf l'appel LLM.** Le E2E exécute `CriticalityRouter`, le **vrai moteur
PRISM** (`run_consensus` via `ConsensusOrchestrator`), la normalisation, la finalisation et la
signature HMAC réelle. **Seuls les arbitres LLM sont simulés** (`CONSENSUS_SIMULATION=true`, garde-fou
de test du dépôt qui interdit les appels LiteLLM réels). C'est une limite assumée et documentée, pas
un chemin entièrement mocké. **Chemin legal** : l'E2E
(`test_legal_extension_set_signing_context_e2e`) importe la **vraie** extension `legal_safe_mode`,
appelle sa méthode réelle `_set_signing_context` puis la fonction réelle
`finalize_pipeline_short_circuit` consommée par `agent.py` — verrouillant le contrat writer/reader.
Le `consensus_status` est mappé par `map_legal_consensus` (testé sur les 6 statuts).

### Q10 — Le résultat est-il défendable devant un auditeur réglementaire ?
**Défendable sur les chemins chat ET pipeline legal, réserves résiduelles limitées.**
- **Défendable** : fail-closed prouvé (chat + pipeline), signature 9 champs vérifiable, anti-tamper
  prouvé sur les deux chemins, secret absent = fail-closed, doctrine écrite (ADR-010), dette supprimée.
- **Réserves restantes** : (a) le validateur collaboratif parallèle (`collaborative_consensus`) reste
  un sous-système non opposable (**P1-3**) ; (b) migration medical/smoke des modules dépréciés
  (**P1-2**). Les trous ex-P0 (fail-open garde-fou) et ex-P1-1 (pipeline legal non signé) sont
  **corrigés**. Un auditeur pointerait encore (a) et (b), mais plus le chemin legal.

---

## PLAN DE REMÉDIATION PRIORISÉ

### P0 — Bloquant
| ID | Fichier | Action corrective exacte | Test attendu | Statut |
|---|---|---|---|---|
| P0-1 | `python/tools/response.py` | Le `except Exception` final ne doit **pas** émettre une sortie critique non signée. Si la criticité est True ou indéterminée → message **fail-closed** ; texte brut uniquement si non-criticité prouvée. | `tests/test_response_tool_failclosed.py` (2 tests) | **✅ RÉSOLU** (30/05/2026) |

> Re-audit après correction P0-1 (Phase 3 du protocole pré-commit) : la correction ne touche que le
> garde-fou d'exception de `response.py` ; aucun nouveau défaut Critique/Important introduit. Les
> chemins nominaux (EMIT_SIGNED / FAIL_CLOSED / FAIL_SOFT) restent inchangés et couverts par les 17
> tests doctrinaux + E2E.

### P1 — Important
| ID | Fichier | Action corrective exacte | Test attendu | Statut |
|---|---|---|---|---|
| P1-1 | `agent.py` (short-circuit pipeline), `legal_safe_mode`, `critical_output.py`, `legal_signing.py` | Faire passer la réponse pipeline par `finalize_critical_output` (signature v2) avant émission, avec garde-fou fail-closed identique à P0-1. | E2E pipeline legal → sortie signée v2 + vérifiable. | **✅ RÉSOLU** (30/05/2026) — `tests/test_legal_pipeline_signed_output.py` (13 tests) |
| P1-2 | `agents/medical/tools/prism_integration.py`, `tools/smoke_test.py` | Migrer vers l'API canonique `seek_consensus`/`run_consensus`, puis **supprimer** `research_consensus_integration.py` et `research_pipeline.py`. | Suite médicale verte sans ces modules ; `PRISM_AVAILABLE` reste `True`. | Ouvert |
| P1-3 | `python/tools/call_subordinate.py` / `collaborative_consensus.py` | Décider : soit faire transiter le résultat collaboratif par `consensus_result` normalisé consommé par le gate, soit documenter explicitement le collaboratif comme validateur subordonné non opposable. Supprimer la concurrence implicite. | Test : sortie de délégation critique → `consensus_result` peuplé et signé, ou bloquée. | Ouvert |

### P2 — Amélioration
| ID | Fichier | Action corrective exacte | Test attendu |
|---|---|---|---|
| P2-1 | `python/helpers/critical_decision_gate.py` | Supprimer le module orphelin **ou** le réduire à un wrapper qui délègue à `critical_output` (éliminer l'illusion d'un gate inerte). | Aucun import production ; tests adaptés. |
| P2-2 | `python/helpers/integrity_block.py` + `critical_output.py` | Unifier les deux représentations de signature (v1 5 champs / v2 9 champs) derrière une seule abstraction versionnée. | Round-trip v1/v2 vérifiable. |
| P2-3 | `python/api/` (audit) | Exposer `verify_evidence_signature` via un endpoint de vérification a posteriori + persister `signed_output` dans le rapport d'audit. | Test API : POST signed_output → 200 valid / 422 invalid. |
| P2-4 | `criticality_router` vs `legal_pipeline.requires_consensus` | Converger les deux déclencheurs `consensus_required` vers une source unique. | Test : mêmes entrées → même décision de criticité. |

---

## Conclusion d'audit

Les chemins critiques **chat ET pipeline legal** sont passés d'un état **non prouvé / non signé / gate
mort** à un état **fail-closed prouvé, signé sur 9 champs, vérifiable et anti-tamper**, avec suppression
nette de ~1240 lignes de dette. Les trous ex-P0 (fail-open garde-fou) et ex-P1-1 (pipeline legal non
signé) sont **corrigés et testés**. **Deux réserves résiduelles** subsistent : le validateur
collaboratif parallèle (**P1-3**) et la migration des modules dépréciés medical/smoke (**P1-2**).
Le système est désormais opposable sur ses deux chemins de sortie principaux ; les réserves restantes
sont périmétrées et n'affectent pas l'émission signée des sorties chat et legal.
