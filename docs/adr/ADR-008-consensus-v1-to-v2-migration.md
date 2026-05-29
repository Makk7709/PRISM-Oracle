# ADR-008 — Migration du moteur de consensus v1 (ConsensusManager) vers v2 (engine.run_consensus)

**Date :** 29 mai 2026
**Statut :** Accepte
**Auteur :** Amine Mohamed
**Branche d'origine :** `chore/diag-grow-metrics-hardening`

## Contexte

L'audit hostile du 29 mai 2026 portant sur la coherence du couple "routeur critique + consensus" (perimetre ~5 100 LOC : `criticality_router.py`, `critical_decision_gate.py`, `consensus_*.py`, `python/consensus/engine.py`) a revele une migration architecturale inachevee documentairement. Quatre fichiers concurrents s'auto-declaraient point d'entree du consensus :

| Fichier | Auto-declaration |
|---|---|
| `python/helpers/consensus_manager.py` | "PRISM CONSENSUS MANAGER — Systeme de consensus multi-IA" |
| `python/helpers/consensus_arbiter.py` | "CONSENSUS ARBITER — Real LLM Voting System" |
| `python/helpers/consensus_integration.py` | "PRISM CONSENSUS INTEGRATION ... ReasoningEngine" |
| `python/consensus/engine.py` | "PRISM Consensus Engine (single entrypoint)" |

Le test `tests/test_consensus_entrypoint_delegation.py` (passe vert) etablit pourtant formellement que `engine.run_consensus` est le seul point d'entree actif : `ConsensusOrchestrator.seek_consensus`, `ResearchPipeline.validate_with_consensus` et `research_with_consensus` y delegueront tous via un patch direct sur `python.consensus.engine.run_consensus`.

Cet ecart entre l'architecture reelle (single entrypoint v2) et l'architecture documentaire (quatre points d'entree concurrents) cree un risque documentaire pour tout audit externe (commissaire aux apports, due-diligence Diag & Grow, revue de code). Il fallait formaliser :

1. Qui est le point d'entree unique du consensus.
2. Pourquoi les modules v1 restent presents (compat ascendante, helpers).
3. Quelles methodes/symboles sont du code legacy non execute (a marquer ou retirer).

## Decision

### 1. Point d'entree unique

`python.consensus.engine.run_consensus` est le **point d'entree unique** pour toute decision de consensus dans KOREV Evidence. Tout nouveau caller DOIT passer par cette fonction.

Signature :

```python
async def run_consensus(
    evidence_pack: Optional[Dict[str, Any]],
    policy: Dict[str, Any],
) -> ConsensusDecision
```

Retour normalise : `ConsensusDecision` (dataclass) avec `proposal_id`, `decision_hash`, `status` (`ConsensusStatusEnum`), `approved` (`bool`), `votes`, `vote_count`, `decision_time_ms`, `correlation_id`, `warnings`.

### 2. Callers autorises (liste exhaustive)

**Callers DIRECTS** (appellent `engine.run_consensus` directement) :

- `python.helpers.consensus_arbiter.ConsensusOrchestrator.seek_consensus`
  (wrapper de compatibilite ascendante, retourne `ConsensusResult` legacy)
- `python.helpers.consensus_integration.ResearchPipeline.validate_with_consensus`
  (pipeline de recherche `ResearchDossier`)
- `python.helpers.consensus_mcp_integration.research_with_consensus`
  (facade MCP - aggregation sources externes)

**Callers INDIRECTS** (passent par un wrapper ci-dessus) :

- `python.helpers.research_consensus_integration` (utilise
  `ConsensusOrchestrator.seek_consensus` pour l'integration agent
  `researcher` / `legal_safe`)

Tout autre callsite est interdit sans mise a jour de la presente ADR.

### 3. Statut des modules v1

| Module | Statut |
|---|---|
| `python/helpers/consensus_manager.py` | **Composant interne**. Continue d'exposer les helpers `build_vote_prompt`, `parse_llm_vote_response_lax`, `generate_decision_hash`, ainsi que les dataclasses `ConsensusManager`, `DecisionProposal`, `VoteCount`, `ConsensusResult` qui sont consommees par `engine.py`. N'est plus un point d'entree public. |
| `python/helpers/consensus_arbiter.py::ConsensusOrchestrator` | **Wrapper de compat ascendante**. Son `seek_consensus()` delegue integralement a `engine.run_consensus`. Les methodes internes heritees (`_select_arbiters`, `_count_votes`, `_create_no_arbiter_result`, `_log_audit`) ne sont plus invoquees sur le chemin actif. Conservees pour compat ; cleanup prevu (passe ulterieure). `get_audit_log()` retourne `[]` tant que le chemin legacy n'est pas reactive (comportement attendu, voir note plus bas). |
| `python/helpers/consensus_arbiter.py::ArbiterCaller` | **Actif via le chemin legacy si appele directement.** Non utilise par `engine.run_consensus` qui implemente son propre chemin d'appel arbitre. |
| `python/helpers/consensus_integration.py::ArbiterLLM` + `_setup_arbiters` | **Code de compatibilite.** Les arbitres LLM crees par `_setup_arbiters` ne sont plus consommes par `validate_with_consensus` depuis la migration v2. Ils restent disponibles pour les tests d'integration legacy via `_collect_arbiter_vote`. |
| `python/helpers/consensus_contracts.py::parse_llm_vote_response` (version stricte) | **Reservee aux validations strictes** (tests + entrees externes contractuelles). Ne pas confondre avec `consensus_manager.parse_llm_vote_response_lax` (version tolerante) consommee sur le chemin production. |

### 4. Naming et renommages effectues lors de cette passe

- `parse_llm_vote_response` dans `consensus_manager.py` -> renomme **`parse_llm_vote_response_lax`** (alias retro-compatible conserve : `parse_llm_vote_response = parse_llm_vote_response_lax`).
- `ArbiterConfig` dans `consensus_integration.py` -> renomme **`LegacyArbiterConfig`** (alias retro-compatible conserve : `ArbiterConfig = LegacyArbiterConfig`).
- `CONSENSUS_REQUIRED_PROFILES` dans `criticality_router.py` -> **retire de `__all__`** mais reste importable au niveau module. La constante est conservee pour les imports existants ; son usage n'a aucun effet dans `assess()` (cf. point 5 ci-dessous).

### 5. Comportement clarifie du routeur

Le comportement de `CriticalityRouter.assess()` est documente formellement (cf. docstring entete de `criticality_router.py` post-passe d'audit) :

- **LEVEL 1** (definition, resume, explication, traduction, calcul) -> bypass consensus systematique, **meme pour les profils critiques** (`legal_safe`, `medical`, `researcher`).
- **LEVEL 3** (cas reel, decision a prendre, litige, responsabilite, action critique) -> consensus REQUIS.
- **LEVEL 2** (zone intermediaire) -> non implemente en niveau distinct ; tombe sur le default (consensus non requis).
- **Domaine critique detecte** -> metadonnees d'enrichissement uniquement ; ne declenche PAS le consensus.
- **`force_consensus=True`** passe par le caller -> consensus REQUIS inconditionnellement.

Les anciennes regles "TOUJOURS consensus" du docstring d'origine (legal_safe -> toujours, domaine critique -> toujours, action critique -> toujours) etaient en contradiction avec le code reel et ont ete retirees.

## Consequences

### Positives

1. **Audit-ready** : un commissaire aux apports lisant un docstring d'entete obtient une description fidele du comportement.
2. **Test de delegation explicite** : `test_consensus_entrypoint_delegation.py` documente formellement la regle "single entrypoint".
3. **Reduction du risque de regression silencieuse** : un developpeur externe ne peut plus appeler `ConsensusManager.propose()` en croyant utiliser le point d'entree officiel.
4. **Trace de migration** : la presente ADR fournit le contexte historique pour les passes de cleanup ulterieures.

### Negatives / Dette

1. **Methodes mortes encore presentes** dans `ConsensusOrchestrator` (`_select_arbiters`, `_count_votes`, `_create_no_arbiter_result`, `_log_audit`) -> a retirer dans une passe de cleanup dediee, apres confirmation qu'aucun import externe n'en depend.
2. **`get_audit_log()` retourne `[]`** par defaut -> a corriger en branchant l'audit log sur les decisions produites par `engine.run_consensus` (passe ulterieure).
3. **Pydantic v1** toujours utilise dans `consensus_contracts.py` -> migration v2 prevue dans un chantier dedie.
4. **`ResearchPipeline.arbiters`** instancie inutilement 3 `ArbiterLLM` non consommes -> a desactiver via flag `legacy_arbiters_enabled=False` par defaut dans une passe ulterieure.

## Critere de cloture

L'ADR-008 est considere clos lorsque :

1. Tous les docstrings d'entete des modules cites refletent la realite du code (verifie : passe d'audit hostile du 29 mai 2026).
2. La constante `CONSENSUS_REQUIRED_PROFILES` est marquee comme deprecated dans son commentaire (verifie).
3. Les renommages `parse_llm_vote_response_lax` et `LegacyArbiterConfig` sont effectifs avec aliases retro-compatibles (verifie).
4. Le test `test_consensus_entrypoint_delegation.py` passe vert (etat baseline conserve).

Une passe de cleanup ulterieure (ADR-009 ou suivante) traitera le retrait effectif du code mort liste dans "Negatives / Dette".

## Reference

- Audit hostile du 29 mai 2026, 36 defauts releves dont 6 critiques portant majoritairement sur le contrat documentaire (docstrings vs code).
- Tests de reference : `tests/test_consensus_entrypoint_delegation.py`, `tests/test_prism_consensus.py`, `tests/test_prism_tally_quorum.py`, `tests/test_criticality_router.py`.
