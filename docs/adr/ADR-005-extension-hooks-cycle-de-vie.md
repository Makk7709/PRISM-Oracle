# ADR-005 — Systeme d'extensions par hooks sur le cycle de vie de l'agent

**Date :** 19 janvier 2026
**Statut :** Accepte
**Auteur :** Amine Mohamed

## Contexte

L'agent KOREV Evidence doit pouvoir etre specialise selon le profil (juridique, medical, financier, recherche) sans modifier le noyau d'orchestration (`agent.py`). Il faut egalement pouvoir injecter des comportements transversaux (audit, masquage de secrets, memorisation, validation strategique) de maniere composable et ordonnee.

Agent Zero fournissait un mecanisme d'extensions basique. La question etait : comment le structurer pour permettre la specialisation par profil tout en garantissant un ordre d'execution previsible et une separation des responsabilites.

## Decision

Implementer un systeme d'extensions base sur des hooks de cycle de vie, avec les proprietes suivantes :

1. **Hooks nommes** : chaque point d'extension correspond a un moment du cycle de vie de l'agent. 24 hooks sont definis : `agent_init`, `system_prompt`, `monologue_start`, `monologue_end`, `message_loop_start`, `message_loop_end`, `message_loop_prompts_before`, `message_loop_prompts_after`, `before_main_llm_call`, `response_stream`, `response_stream_chunk`, `response_stream_end`, `reasoning_stream`, `reasoning_stream_chunk`, `reasoning_stream_end`, `tool_execute_before`, `tool_execute_after`, `hist_add_before`, `hist_add_tool_result`, `legal_safe_mode`, `strategic_validation`, `user_message_ui`, `util_model_call_before`, `error_format`.

2. **Convention de nommage** : chaque module d'extension est un fichier `_<ordre>_<description>.py` dans un repertoire portant le nom du hook. L'ordre numerique (lexicographique) determine la sequence d'execution : `_05_` s'execute avant `_10_`, qui s'execute avant `_20_`.

3. **Classe de base** : chaque extension herite de `Extension` et implemente `async def execute(self, **kwargs)`. Les kwargs transmis dependent du hook.

4. **Mutation par liste** : les hooks de type prompt (`system_prompt`, `message_loop_prompts_*`) recoivent une `list[str]` que les extensions modifient par `append()` ou `insert(0, ...)`.

5. **Chargement dynamique** : `load_classes_from_folder()` charge les extensions par introspection du repertoire.

6. **Specialisation par profil** : chaque profil d'agent (`agents/<nom>/`) peut fournir ses propres extensions dans un sous-repertoire, qui s'ajoutent aux extensions globales.

## Consequences

**Positives :**
- Le noyau (`agent.py`) reste stable : les nouvelles fonctionnalites s'ajoutent par extension sans modifier le monologue.
- L'ordre d'execution est explicite, deterministe et auditable (convention de nommage numerique).
- 48 modules d'extension actuellement : audit, masquage, replay, risk assessment, memorisation, validation strategique, legal-safe mode.
- La specialisation par profil permet de configurer des agents radicalement differents (juridique vs medical vs recherche) sans duplication de code.

**Negatives :**
- Le contrat entre le noyau et les extensions est implicite (pas de schema formel des kwargs par hook).
- Un conflit d'ordre entre deux extensions du meme hook peut causer des comportements inattendus.
- La charge cognitive pour un nouveau developpeur est elevee : comprendre les 24 hooks et leurs interactions necessite le guide d'onboarding.
- Certains hooks (`legal_safe_mode`) contiennent des modules monolithiques (51 838 octets pour `_10_legal_safe_integration.py`).

## Alternatives rejetees

| Alternative | Raison du rejet |
|---|---|
| **Middleware Flask classique** | Ne couvre que les requetes HTTP, pas le cycle de vie interne de l'agent (monologue, outils, streams) |
| **Event emitter (pub/sub)** | Pas de garantie d'ordre d'execution, difficulte a gerer les mutations de prompts |
| **Decorateurs Python** | Couplage fort au noyau, pas de chargement dynamique par profil |
| **Plugin system avec entry points** | Sur-ingenierie pour le cas d'usage, complexite de packaging |
| **Modification directe de agent.py** | Non scalable, conflits de merge, bus factor critique |
