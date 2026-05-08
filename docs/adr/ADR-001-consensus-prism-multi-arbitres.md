# ADR-001 — Consensus PRISM multi-arbitres avec politique fail-closed

**Date :** 21 janvier 2026
**Statut :** Accepte
**Auteur :** Amine Mohamed

## Contexte

KOREV Evidence doit produire des reponses fiables dans des domaines critiques (juridique, medical, financier). Un modele de langage unique peut halluciner ou produire des reponses incorrectes sans signal d'alerte. Dans un contexte reglemente, une reponse fausse non detectee peut avoir des consequences juridiques.

Le projet anterieur PRISM avait deja explore des mecanismes de validation croisee entre modeles. La question etait : comment integrer ce mecanisme dans l'architecture Agent Zero de maniere a garantir qu'aucune decision critique ne soit emise sans validation ?

## Decision

Implementer un systeme de consensus multi-arbitres avec les proprietes suivantes :

1. **Plusieurs modeles LLM votent independamment** sur une question donnee (`ConsensusManager`, `ArbiterCaller`).
2. **Un quorum minimum est requis** pour qu'une decision soit consideree comme valide (defaut : 2/3 des arbitres disponibles).
3. **Politique fail-closed** : en cas d'absence de consensus ou d'indisponibilite d'arbitres, le systeme refuse de repondre plutot que de deviner. `ConsensusStatusEnum.NO_CONSENSUS` est retourne.
4. **Point d'entree unique** : toute decision de consensus passe par `ConsensusEngine.run_consensus()` (`python/consensus/engine.py`).
5. **Contrats types** (`python/helpers/consensus_contracts.py`) definissent les schemas de validation : `ConsensusPolicySchema`, `ConsensusResultSchema`, `ResponseEnvelopeSchema`.
6. **Verification en production** : `_ensure_real_votes_or_raise()` empeche qu'une decision soit approuvee sans votes reels en environnement de production.

## Consequences

**Positives :**
- Reduction mesurable du risque d'hallucination sur les decisions critiques.
- Tracabilite complete : chaque vote, chaque arbitre, chaque decision est journalise avec `correlation_id` et `decision_hash`.
- Le fail-closed protege contre les defaillances silencieuses.
- IP defensible : l'algorithme de consensus multi-LLM est un differenciateur technique reel.

**Negatives :**
- Cout d'inference multiplie par le nombre d'arbitres (2-3 arbitres actifs par defaut, configurable via UI ou `CONSENSUS_ARBITERS`).
- Latence supplementaire (attente du quorum).
- Complexite accrue : trois chemins de code coexistent (`engine.py`, `consensus_integration.py`, `consensus_arbiter.py`), ce qui cree une dette technique documentee dans l'audit hostile (livrable 03, constat A-2).

## Alternatives rejetees

| Alternative | Raison du rejet |
|---|---|
| **LLM unique avec prompt de verification** | Pas de diversite de modeles, pas de fail-closed possible, auto-evaluation sans validation croisee |
| **Validation humaine systematique** | Non scalable, latence incompatible avec un usage interactif |
| **Consensus par embeddings (distance semantique)** | Fragile, ne detecte pas les hallucinations factuelles, pas de signal binaire exploitable |
| **Abstention sur seuil de confiance** | Les scores de confiance des LLM ne sont pas calibres, approche peu fiable |
