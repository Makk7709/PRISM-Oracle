# ADR-002 — Router deterministe par hashing, sans LLM, anti-injection

**Date :** 23 janvier 2026
**Statut :** Accepte
**Auteur :** Amine Mohamed

## Contexte

Les requetes entrantes dans Evidence doivent etre classifiees selon leur domaine (juridique, medical, financier, technique) et leur niveau de criticite (standard, board-level). Cette classification determine le profil d'agent active, le niveau de consensus requis et les garde-fous appliques.

Utiliser un LLM pour le routage introduit un risque d'injection : un utilisateur malveillant pourrait formuler sa requete de maniere a manipuler la classification et contourner les garde-fous. De plus, un routage par LLM est non-deterministe : la meme requete peut etre classifiee differemment selon le run.

## Decision

Implementer un router purement deterministe avec les proprietes suivantes :

1. **Aucun LLM dans la boucle de routage.** La classification repose exclusivement sur des tables de mots-cles (`python/helpers/router/policy.py`) et du hashing SHA-256.
2. **Meme entree → meme sortie** : la fonction `decide_route()` est une fonction pure. Le `route_id` est derive du hash SHA-256 du texte canonicalise.
3. **Detection d'injection** : `INJECTION_PATTERNS` dans `policy.py` detecte les tentatives de manipulation du routage (jailbreak, prompt injection).
4. **Contrat de routage** (`routing_contract.py`) : `RouteDecision` est un objet type valide par `validate_route_decision()` avant propagation.
5. **Classification multi-intent** : une requete peut activer plusieurs intents (ex: `finance` + `legal_safe`), avec des regles de combinaison explicites (`MULTI_INTENT_RULES`).
6. **Metriques** (`metrics.py`) : chaque decision de routage est instrumentee pour audit.

## Consequences

**Positives :**
- Comportement 100 % reproductible et testable (propriete critique pour l'auditabilite).
- Immunite aux attaques par injection de prompt sur la couche de routage.
- Performance : le routage est quasi-instantane (pas d'appel reseau).
- Auditabilite : le `route_id` deterministe permet de rejouer une decision de routage.

**Negatives :**
- La classification par mots-cles peut manquer des nuances semantiques qu'un LLM capterait.
- Les tables de mots-cles dans `policy.py` necessitent une maintenance manuelle lors de l'ajout de nouveaux domaines.
- La calibration des seuils (`BOARD_LEVEL_THRESHOLD`) est empirique.

## Alternatives rejetees

| Alternative | Raison du rejet |
|---|---|
| **Routage par LLM (classification zero-shot)** | Non-deterministe, injectable, latence, cout d'inference |
| **Routage par embeddings + seuil cosine** | Deterministe si le modele d'embedding est fixe, mais fragile aux reformulations adversariales, et depend d'un modele externe |
| **Routage par regles regex strictes** | Trop rigide, maintenance lourde, pas de notion de multi-intent |
| **Absence de routage (agent unique)** | Pas de garde-fous adaptes au domaine, pas de differenciation de criticite |
