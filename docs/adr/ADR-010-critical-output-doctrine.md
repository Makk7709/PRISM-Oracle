# ADR-010 — Doctrine de sortie critique : router → consensus → sortie signée (fail-closed)

**Date :** 30 mai 2026
**Statut :** Accepté (doctrine cible — implémentation en cours, cf. `docs/audit/critical_path_remediation_report.md`)
**Périmètre :** chemin critique `input → criticality_router → consensus → consensus_result → sortie signée`.
**Relations :** **résout l'arbitrage laissé ouvert par `ADR-009-response-gate-disabled.md` (Tranche B)** ; s'appuie sur `ADR-008-consensus-v1-to-v2-migration.md` (API consensus v2).

> **Note de numérotation** : la mission visait `ADR-009-critical-output-doctrine.md`, mais `ADR-009`
> est déjà attribué (gate désactivé). Pour éviter une collision de numéro d'ADR (défaut de cohérence
> documentaire), la doctrine cible est consignée ici sous **ADR-010**. ADR-009 reste l'état transitoire
> « avant » ; ADR-010 est la doctrine « cible » qui clôt sa Tranche B.

---

## Contexte

La cartographie `docs/audit/critical_request_path_map.md` (2026-05-30) a prouvé trois ruptures sur le
chemin critique réel :

- **R-1** : le gate de sortie est code mort (`response.py:56` → L58-153 inatteignables).
- **R-2** : `consensus_result` n'atteint jamais la sortie (écrit en 2 points, consommé nulle part).
- **R-3** : la signature ne couvre que 3/9 champs requis ; la sortie utilisateur n'est jamais signée ;
  secret absent ⇒ fail-soft silencieux (section omise).

ADR-009 a explicitement reporté l'arbitrage fail-closed/fail-soft à une « Tranche B » conditionnée à :
`consensus_result` réellement alimenté, bannière limitée au LEVEL 3, doctrine écrite, tests E2E verts.
**Le présent ADR tranche cette doctrine.**

---

## Décision — Doctrine de sortie critique

### D1 — Routage obligatoire
Toute requête est évaluée par `criticality_router.assess(...)`. Le `criticality_level` et le booléen
`consensus_required` produits sont **autoritatifs** et propagés jusqu'à la finalisation de la sortie.
Il existe **une seule** source de vérité pour `consensus_required` (le router) ; les déclencheurs
spécifiques (legal_pipeline) doivent **converger** vers cette source, pas la dupliquer.

**Taxonomie de criticité (champ explicite `CriticalityAssessment.level`, ajout 2026-06-01) :**
- **LEVEL 1** — requête simple (définition, résumé, météo, calcul) : jamais de consensus, *sauf opt-in
  explicite de l'utilisateur*.
- **LEVEL 2** — zone professionnelle (analyse, comparaison, conseil) : **pas** de consensus par défaut,
  mais **activable à la demande**. Deux déclencheurs : (a) **opt-in utilisateur** dans le chat
  (`CONSENSUS_OPT_IN_PATTERNS` : « par consensus », « /consensus », « second avis »…) → `consensus_opt_in=True` ;
  (b) `force_consensus=True` du caller.
- **LEVEL 3** — requête critique (cas réel, décision, litige, responsabilité, action critique) :
  consensus **toujours** requis.

Le router est resté longtemps binaire (LEVEL 1 / LEVEL 3, LEVEL 2 = défaut implicite non distinct).
Cet ADR acte la **réintroduction d'un LEVEL 2 distinct** avec consensus opt-in, sans affaiblir le
fail-closed des sorties critiques (le gate `critical_output` continue de s'appuyer sur
`requires_consensus`, pas sur le label `level`).

### D2 — Consensus obligatoire si requis
Si `consensus_required = true`, un `consensus_result` **valide** (statut terminal `APPROVED` /
`REJECTED` / `NO_CONSENSUS` / `INFRA_FAILURE`, schéma `ConsensusResultSchema` respecté) est
**obligatoire**. Il est produit par **l'unique API canonique** `run_consensus(...)` (cf. ADR-008),
peuplé, et transmis jusqu'à la sortie.

### D3 — Fail-closed par défaut
Si `consensus_required = true` et que `consensus_result` est **absent, invalide, en timeout critique,
ou incohérent**, la sortie critique est **bloquée (fail-closed)**. Le blocage est explicite, tracé
(`trace_id`/`correlation_id`), et renvoie un motif structuré — **jamais** un `success` maquillé sur un
`consensus_result` vide.

### D4 — Fail-soft seulement si policy explicite
Le fail-soft (émettre avec bannière « NON VALIDÉ » au lieu de bloquer) n'est autorisé **que** si une
**policy explicite** l'active pour le niveau de criticité concerné (`policy.fail_soft_allowed = true`).
En l'absence de policy explicite, le comportement est fail-closed. **Aucune** activation implicite,
**aucune** bannière par défaut, **aucun** fail-open silencieux sur exception.

### D5 — Signature obligatoire et opposable
Toute sortie critique porte une **signature vérifiable** (HMAC-SHA256, ou RSA-PSS si configuré). La
signature couvre **au minimum** :
`input_hash`, `output_hash`, `consensus_result_hash`, `criticality_level`, `policy_id`/`policy_version`,
`timestamp`, `trace_id`/`correlation_id`, `model`/`provider` metadata si disponible,
`human_review_required` si applicable.
**Une sortie critique non signée est une sortie non opposable** : elle doit échouer explicitement.

### D6 — Fail-closed si secret absent en production
En environnement de production, si le secret de signature (`EVIDENCE_HMAC_KEY` ou clé RSA) est absent,
toute sortie critique est **bloquée (fail-closed)**. L'avalement silencieux actuel de l'exception de
signature (section d'intégrité omise) est **proscrit** pour les sorties critiques. Le fail-soft sur
secret absent reste tolérable **hors** chemin critique (rapports informatifs non opposables) uniquement.

### D7 — Une seule API consensus, un seul gate alimenté
Il existe **une** API interne canonique de consensus (`run_consensus`) et **un** point de finalisation
critique qui consomme `consensus_result` et appose la signature. Les intégrations consensus
redondantes/orphelines (`consensus_integration`, `consensus_mcp_integration`,
`research_consensus_integration`, `research_pipeline`) sont **supprimées** ou **dépréciées avec
redirection stricte** — jamais maintenues comme chemins parallèles actifs.

### D8 — Consolidation, pas de nouvelle couche
La doctrine est implémentée en **consolidant les couches existantes** (gate de décision + bloc
d'intégrité/`AuditReportRenderer`), point de passage déjà universel sur les chemins classic et
pipeline. **Aucune nouvelle couche d'abstraction** ni seconde API consensus n'est introduite.

### D9 — Fraîcheur des données (recency) — doctrine stricte
Une sortie critique repose souvent sur des données **sensibles au temps** (lois en vigueur, taux,
données marché, faits d'entreprise). Deux mécanismes complémentaires l'encadrent :

1. **Prompt système (préventif, transverse)** : `prompts/agent.system.freshness_policy.md` est injecté
   dans **tous** les agents (cf. `python/extensions/system_prompt/_10_system_prompt.py`). Il impose,
   à la date du jour, de **vérifier la fraîcheur via outils avant d'affirmer**, d'indiquer la **date
   *as-of*** de toute donnée sensible au temps, et d'apposer une bannière « potentiellement obsolète »
   si la fraîcheur ne peut pas être prouvée.

2. **Gate (filet de sécurité, escalade)** : `finalize_critical_output(..., recency_verified=...)`. Sur
   une sortie **critique** dont la fraîcheur n'est **pas affirmativement prouvée** (`recency_verified`
   à `None` ou `False`), le gate **force `human_review_required = True`** (champ couvert par la
   signature) et appose la **bannière d'obsolescence**. Ce n'est **pas** un blocage (la sortie reste
   signée et émise), mais une **escalade tracée et opposable** : jamais une donnée périmée présentée
   comme courante en silence. Une fraîcheur prouvée en amont (`recency_verified=True`) lève l'escalade.

> **Limite assumée (v2)** : le flag `recency_verified` lui-même n'est pas (encore) un champ du payload
> signé ; sa conséquence — `human_review_required` — l'est. Un passage à une signature v3 couvrant
> explicitement la fraîcheur est un suivi possible (cf. risques résiduels du rapport de remédiation).

---

## Matrice de comportement

| criticality | consensus_required | consensus_result | secret signature | policy.fail_soft | recency_verified | Résultat |
|---|---|---|---|---|---|---|
| non-critique | false | n/a | présent | n/a | n/a | sortie signée (non bloquante) |
| critique | true | valide (APPROVED) | présent | n/a | **true** | **sortie signée + consensus_result** |
| critique | true | valide (APPROVED) | présent | n/a | **None/false** | **sortie signée + bannière obsolescence + human_review escaladé** |
| critique | true | absent / invalide / timeout | présent | false | — | **FAIL-CLOSED (bloqué)** |
| critique | true | absent / invalide / timeout | présent | **true (explicite)** | — | sortie + bannière « NON VALIDÉ » tracée |
| critique | true/false | — | **absent (prod)** | — | — | **FAIL-CLOSED (bloqué)** |
| critique | true | REJECTED | présent | false | — | **FAIL-CLOSED (bloqué, motif: rejected)** |

---

## Conséquences

### Positives
- Chaîne opposable de bout en bout : entrée → router → consensus → `consensus_result` → signature.
- La signature lie cryptographiquement la décision de consensus et la policy au payload.
- Comportement déterministe et défendable devant un auditeur réglementaire.

### Négatives / risques
- Réintroduction d'un blocage dur : nécessite que `consensus_result` soit réellement alimenté
  (sinon régression « tout bloqué »). Mitigation : critères D1-D2 + tests E2E avant activation.
- La signature étendue change le payload signé : **incompatible** avec les signatures historiques
  (5 champs). Mitigation : `signature_version` bumpée ; les anciens rapports restent vérifiables avec
  l'algorithme v1 (verify rétro-compatible par version).

## Critères d'acceptation (clôture de la Tranche B d'ADR-009)
1. `consensus_result` alimenté et consommé sur le chemin de sortie critique. ✅ à prouver (Phase 4)
2. Bannière fail-soft limitée au cas policy-explicite (jamais par défaut). ✅ à prouver (Phase 7)
3. Doctrine écrite (présent ADR). ✅
4. Tests E2E entrée critique → sortie signée verts en CI 3.11. ✅ à prouver (Phase 8)
5. Aucune régression « bannière/blocage systématique » hors critique. ✅ à prouver (Phase 7-8)

## Références
- `docs/audit/critical_request_path_map.md` (cartographie réelle vs attendue).
- `docs/adr/ADR-009-response-gate-disabled.md` (état transitoire ; Tranche B résolue ici).
- `docs/adr/ADR-008-consensus-v1-to-v2-migration.md` (`run_consensus` canonique).
- `docs/reports/PROD_READINESS_AUDIT.md` (RISK-01 sortie non validée).
