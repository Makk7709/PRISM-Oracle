# ADR-004 — LiteLLM comme couche d'abstraction multi-LLM

**Date :** 15 janvier 2026
**Statut :** Accepte
**Auteur :** Amine Mohamed

## Contexte

KOREV Evidence doit pouvoir interroger plusieurs fournisseurs de modeles de langage (OpenAI, Anthropic, Google, OpenRouter, modeles locaux) sans coupler le code applicatif a l'API specifique de chaque fournisseur. Le systeme de consensus (ADR-001) requiert l'acces simultane a plusieurs modeles differents. Le choix de l'abstraction LLM a un impact structurant sur l'ensemble du code.

Agent Zero (le projet upstream) utilisait deja LiteLLM. La question etait : conserver LiteLLM, migrer vers une alternative, ou developper une couche maison.

## Decision

Conserver **LiteLLM** comme couche d'abstraction principale, avec les adaptations suivantes :

1. **Import centralise** dans `models.py` : `from litellm import completion, acompletion, embedding`.
2. **Configuration des providers** via `python/helpers/providers.py` et `ModelConfig` (dataclass typee avec provider, nom, API base, limites, vision).
3. **Suppression aggressive du logging** LiteLLM (`turn_off_logging()` dans `models.py`) pour eviter la pollution des logs en production.
4. **Rate limiting applicatif** (`python/helpers/rate_limiter.py`) en complement du rate limiting LiteLLM.
5. **Monkey-patch pour browser-use** (`browser_use_monkeypatch.py`) pour corriger des incompatibilites avec Playwright/LangChain.
6. **Compatibilite LangChain** via `SimpleChatModel` et `Embeddings` wrapper pour les cas d'usage RAG (`sentence-transformers` pour les embeddings locaux).

## Consequences

**Positives :**
- Acces a 100+ modeles via une interface unifiee (`completion()` / `acompletion()`).
- Le changement de fournisseur ne necessite qu'un changement de configuration, pas de code.
- Le consensus multi-LLM (ADR-001) peut interroger des modeles heterogenes dans le meme pipeline.
- Streaming supporte nativement.
- Continuité avec l'upstream Agent Zero, facilitant les cherry-picks.

**Negatives :**
- Dependance forte a une bibliotheque tierce (API instable, releases frequentes, bugs remontes).
- Version forcee (`1.79.3`) pour eviter les regressions, ce qui impose une maintenance de suivi.
- LiteLLM n'est pas dans `requirements.txt` (installe separement), ce qui complique la reproductibilite du build.
- Le monkey-patching (`litellm.modify_params = True`) est fragile et dependant de la version.

## Alternatives rejetees

| Alternative | Raison du rejet |
|---|---|
| **Appels directs aux SDK (openai, anthropic, google)** | Code duplique pour chaque provider, pas de standardisation, maintenance lourde |
| **LangChain comme couche unique** | Trop lourd, API instable, sur-abstraction pour les besoins de completion simple |
| **Couche maison (wrapper custom)** | Effort disproportionne, reinvention de la roue, maintenance solo |
| **LMQL / DSPy** | Paradigme different (programmation de prompts), pas adapte a l'orchestration multi-agents |
