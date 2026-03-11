# KOREV Evidence — Developer Onboarding & Architecture Guide

**Classification :** CONFIDENTIEL — Usage interne  
**Version :** 4.0 (patch anti-boucles infinies + garde-fous d'exécution)  
**Date :** 2026-03-11  
**Auteur :** Audit automatisé (Staff Engineer / Architecture Review)  
**Destinataire :** Lead Engineer entrant(e)  
**Note au lecteur :** Ce document est long. C'est volontaire. Lis-le de bout en bout pendant ta première semaine, puis utilise-le comme référence. Les sections les plus urgentes à lire en priorité sont marquées d'un signe (**LIRE EN PREMIER**).

---

## Table des matières

1. [Partie 1 : L'Hélicoptère — Vision et Architecture Globale](#partie-1--lhélicoptère)
2. [Partie 2 : Audit Critique et Red Teaming — Les Zones de Danger](#partie-2--audit-critique-et-red-teaming) (**LIRE EN PREMIER**)
3. [Partie 3 : Guide de Survie Opérationnel](#partie-3--guide-de-survie-opérationnel)
4. [Partie 4 : Feuille de Route — 30 Premiers Jours](#partie-4--feuille-de-route--30-premiers-jours) (**LIRE EN PREMIER**)

---

# Partie 1 : L'Hélicoptère

## 1.1 Ce que fait KOREV Evidence

KOREV Evidence est une plateforme multi-agents d'IA de confiance, conçue pour des environnements professionnels exigeants (cabinets d'avocats, entreprises, recherche). L'idée directrice : un utilisateur interagit avec un agent principal qui peut **déléguer** à des agents spécialisés (juridique, médical, recherche, sécurité, finance...), orchestrer des **consensus** entre agents, et produire des livrables traçables (rapports PDF, images, analyses).

Le différenciant par rapport à un ChatGPT-like : **l'auditabilité**. Chaque action d'agent est loggée, les sources sont tracées, et les réponses critiques (juridiques, médicales) passent par un pipeline de validation multi-agents.

## 1.2 Architecture Macro

```
┌─────────────────────────────────────────────────────────────────┐
│                        COUCHE RÉSEAU                            │
│  Internet → Caddy (HTTPS :443) → Flask Backend (:5050)          │
│                                    ├── WebUI (Alpine.js)        │
│                                    ├── MCP Proxy (/mcp)         │
│                                    └── A2A Server (/a2a)        │
│  Réseau interne → Samba (:445) → Dossiers partagés Windows      │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                     COUCHE APPLICATIVE                           │
│                                                                 │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐      │
│  │  Agent #0     │───▶│  Agent #1     │───▶│  Agent #2     │    │
│  │  (principal)  │◀───│  (subordinate)│◀───│  (sub-sub)    │    │
│  │  multitask    │    │  legal_safe   │    │  researcher   │    │
│  └──────┬───────┘    └──────────────┘    └──────────────┘      │
│         │                                                       │
│  ┌──────▼───────────────────────────────────────────┐          │
│  │              TOOLS (23 outils)                    │          │
│  │  code_execution │ generate_image │ search_engine  │          │
│  │  memory_save    │ file_reader    │ browser_agent  │          │
│  │  export_strategic_pdf │ document_query │ scheduler │          │
│  │  call_subordinate │ ...                           │          │
│  └──────────────────────────────────────────────────┘          │
│                                                                 │
│  ┌──────────────────────────────────────────────────┐          │
│  │         EXTENSIONS (45 fichiers, 24 hooks)       │          │
│  │  system_prompt │ recall_memories │ legal_pipeline │          │
│  │  strategic_validation │ memorize_fragments │ ...    │          │
│  └──────────────────────────────────────────────────┘          │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                    COUCHE PERSISTANCE                            │
│                                                                 │
│  Filesystem (Volumes Docker)                                    │
│  ├── evidence-tmp     → Chats, settings, images, scheduler     │
│  ├── evidence-shared  → Workspaces utilisateurs, commun        │
│  ├── evidence-memory  → FAISS indexes, embeddings cache        │
│  ├── evidence-data    → Legal index (SQLite FTS5)              │
│  ├── evidence-logs    → Application logs                       │
│  └── evidence-audit   → Audit trails                           │
│                                                                 │
│  Pas de SGBD traditionnel. Tout est fichier.                    │
└─────────────────────────────────────────────────────────────────┘
```

## 1.3 Anatomie d'une Requête Utilisateur (Data Flow)

Voici le parcours complet d'un message utilisateur, du clic au résultat :

```
1. FRONTEND (Alpine.js)
   └─ sendMessage() → POST /message_async {text, context, message_id}
       └─ Avec X-CSRF-Token dans le header

2. FLASK BACKEND (run_ui.py)
   └─ @_requires_auth → vérifie session
   └─ ApiHandler.process() → crée/récupère AgentContext
   └─ context.communicate(UserMessage) → lance monologue dans DeferredTask

3. AGENT MONOLOGUE (agent.py)
   └─ Extensions: monologue_start → message_loop_start
   └─ prepare_prompt():
       ├─ System prompt (role + environment + tools + project context)
       ├─ Memory recall (FAISS similarity search)
       └─ History (messages précédents)
   └─ call_chat_model() → LLM API (OpenAI, Anthropic, Google via LiteLLM)
   └─ process_tools():
       ├─ Parse JSON dans la réponse LLM
       ├─ Résolution: MCP tool → Profile tool → Default tool → Unknown
       └─ tool.execute() → Response(message, break_loop)
   └─ Si break_loop=False → boucle (✅ bornée par ExecutionBudget : max_iterations, max_llm_calls, max_tool_calls, deadline)
   └─ Extensions: message_loop_end → monologue_end

4. CAS SPÉCIAL : DÉLÉGATION
   └─ Tool "call_subordinate" → crée Agent #1 avec profil spécialisé
   └─ ExecutionBudget: check_delegation() → cycle detection, max_depth, max_delegations
   └─ propagate_budget() → même état partagé entre supérieur et subordonné
   └─ CriticalityRouter → consensus nécessaire ? (LEVEL 3 critique ou force_consensus)
   └─ Si oui : validation multi-LLM (3 rounds de débat collaboratif)
   └─ Résultat remonté à l'Agent #0

5. FRONTEND POLLING
   └─ poll() toutes les 25-250ms (adaptatif)
   └─ Récupère logs, contextes, streamed tokens
   └─ Rendu: messages.js → marked.parse() → DOM updates
```

## 1.4 Profils d'Agents et Spécialisations

Le système supporte 12 profils. Chaque profil est un répertoire sous `agents/` avec ses propres prompts, outils, extensions et settings.

| Profil | Rôle | Spécificités |
|--------|------|-------------|
| **default** | Prompts de base | Hérité par tous les profils, contient les prompts et settings par défaut |
| **multitask** | Agent par défaut | Généraliste, peut déléguer |
| **legal_safe** | Mode juridique sécurisé | Température=0, citations obligatoires, classification 3 niveaux, consensus multi-agents |
| **legal_drafting_guarded** | Rédaction juridique | Garde-fous rédactionnels |
| **medical** | Intelligence médicale | Consensus PRISM (protocole de validation multi-LLM), essais cliniques, FAERS, synthèse par preuves (GRADE) |
| **researcher** | Recherche approfondie | Littérature académique, orchestration de sous-agents |
| **hacker** | Analyste sécurité | Red/blue team, Kali, scoring de sévérité |
| **developer** | Développeur | Code, génération d'images, outils techniques |
| **finance** | Analyse financière | Modélisation, reporting |
| **sales** | Support ventes | Commercial |
| **marketing** | Marketing | Stratégie marketing |
| **_example** | Template | Pour créer de nouveaux profils |

**Analogie** : Imagine une entreprise. L'Agent #0 (multitask) est le chef de projet. Quand il reçoit une question juridique, il "appelle" l'Agent #1 (legal_safe) qui est l'avocat spécialisé. Si la question est critique, l'avocat convoque un "comité" (consensus) avec plusieurs LLMs qui débattent avant de valider la réponse. Le chef de projet ne renvoie jamais une réponse juridique non validée.

## 1.5 Mécanismes d'IA de Confiance

### Traçabilité
- Chaque action d'agent est loggée dans `context.log` (type, heading, content, kvps)
- Les logs sont persistés dans les fichiers de chat (`tmp/chats/{ctxid}/chat.json`)
- **Evidence Pack** (`python/helpers/evidence.py`) : objet structuré qui encapsule les sources, citations et métadonnées de confiance pour chaque réponse validée par le consensus
- Audit des opérations fichier dans `shared/audit/file_operations.jsonl` (via `WorkspaceManager`)
- Logs applicatifs dans le volume `evidence-logs`

### Garde-fous
- **Température forcée à 0** pour les profils critiques (legal_safe) — pas d'improvisation
- **CriticalityRouter** : détecte automatiquement les sujets nécessitant un consensus (basé sur des patterns LEVEL 3 critiques ou `force_consensus=True`, pas sur le profil agent)
- **Consensus multi-agents** : 3 rounds de débat entre LLMs — Round 1 (analyse indépendante par 3 LLMs en parallèle), Round 2 (débat croisé, sauté si unanimité au Round 1), Round 3 (synthèse et verdict)
- **Extension pipeline** : 24 hook points avec 45 extensions permettant d'intercepter et modifier le comportement à chaque étape
- **ExecutionBudget** (`python/helpers/execution_budget.py`) : ✅ garde-fou central anti-boucles infinies. Chaque exécution transporte un budget partagé qui borne :
  - `max_iterations` (défaut 25) — itérations du message loop
  - `max_depth` (défaut 5) — profondeur de récursion `_process_chain`
  - `max_delegations` (défaut 8) — nombre de délégations inter-agents
  - `max_tool_calls` (défaut 50) — nombre d'exécutions d'outils
  - `max_llm_calls` (défaut 30) — nombre d'appels LLM
  - `max_consensus_rounds` (défaut 3) — rounds de consensus
  - `deadline_seconds` (défaut 300s) — timeout global
  - Détection de cycles de délégation (A→B→A) et self-delegation
  - Tous les seuils sont configurables via variables d'environnement `EVIDENCE_*`
  - Arrêt immédiat avec `LOOP_GUARD_TRIGGERED` et log structuré en cas de dépassement
- **Exécution gardée** : `ExecutionGuard` (désactivé actuellement — remplacé par le prompt-based execution policy)

### Isolation utilisateur
- Projets : champ `owner` + filtrage API
- Images générées : sous-dossiers par utilisateur
- Mémoire : index FAISS séparés par utilisateur
- Workspaces : `shared/users/{username}/` avec documents, rapports, tmp

---

# Partie 2 : Audit Critique et Red Teaming

> *"Zéro complaisance. Si le système devait s'effondrer, voici par où ça commencerait."*

## 2.1 Vulnérabilités Critiques

### 🔴 CRITIQUE : Path Traversal dans `file_info` et `download_work_dir_file`

**Fichiers :** `python/api/file_info.py`, `python/api/download_work_dir_file.py`

Le chemin fourni par l'utilisateur est passé directement à `files.get_abs_path(path)` sans validation. Cette fonction fait un simple `os.path.join(base_dir, path)` sans résolution ni vérification. Un attaquant pourrait lire n'importe quel fichier du système :

```
POST /file_info {"path": "../../etc/passwd"}
```

`image_get.py` est protégé (il utilise `safe_path_join`), mais ses voisins ne le sont pas. C'est incohérent et dangereux.

**Impact :** Lecture arbitraire de fichiers (clés API dans `.env`, `users.json` avec les hashes).  
**Fix immédiat :** Appliquer `safe_path_join()` dans `file_info.py` et `download_work_dir_file.py`, comme c'est déjà fait dans `image_get.py`.

### 🔴 CRITIQUE : `api_files_get` — API Key + Pas de validation de chemin

L'endpoint `api_files_get` (destiné aux intégrations externes) accepte un chemin arbitraire avec comme seule protection une API key. Combiné à l'absence de `safe_path_join`, c'est un accès lecture à tout le filesystem.

### 🟠 ÉLEVÉ : Pas de sandbox pour l'exécution de code

`code_execution_tool.py` exécute du Python/Node/shell avec les privilèges du processus backend. En production Docker, c'est l'utilisateur `evidence` dans le container. Mais :
- Pas de container séparé, pas de seccomp, pas de cgroups dédiés
- Le code peut lire/écrire tout ce que le processus backend peut lire/écrire
- Un agent hallucinant pourrait exécuter `rm -rf /app/tmp/` et détruire toutes les données

### 🟠 ÉLEVÉ : Chats sans isolation utilisateur au stockage

Tous les chats sont dans `tmp/chats/` (un seul dossier). L'ownership est un champ `username` dans le JSON, mais :
- Aucun contrôle d'accès à l'API de chargement (`chat_load`)
- Si un utilisateur connaît le `ctxid` d'un autre, il peut charger son chat
- Au startup, TOUS les chats sont chargés en mémoire (`load_tmp_chats()`)

### 🟠 ÉLEVÉ : Fuite de file descriptors (observée en production)

Le backend a été trouvé avec 1023/1024 file descriptors ouverts, causant un crash complet. La cause probable : les sessions aiohttp, les connexions LLM, ou les index FAISS ne sont pas correctement fermés. Le `ulimits` a été monté à 65536, mais c'est un pansement — la fuite existe toujours.

## 2.2 Risques Multi-Agents

### Boucles infinies — ✅ NEUTRALISÉES (v4.0, mars 2026)

> **Patch appliqué** : `python/helpers/execution_budget.py` + modifications de `agent.py` et `python/tools/call_subordinate.py`. Voir tests : `tests/test_execution_budget.py` (34 tests).

Les deux vecteurs historiques de boucles infinies sont désormais bornés par le système **ExecutionBudget** :

1. **Profondeur de délégation** : ✅ `check_depth()` est appelé dans `_process_chain()` avant chaque récursion. Limite : `max_depth=5` (configurable via `EVIDENCE_MAX_DEPTH`). `check_delegation()` dans `call_subordinate.py` borne le nombre total de délégations (`max_delegations=8`) et détecte les cycles (A→B→A) via `delegation_visit_counts`.

2. **Boucle monologue** : ✅ `check_iteration()` est appelé avant chaque itération du message loop. Limite : `max_iterations=25` (configurable via `EVIDENCE_MAX_ITERATIONS`). `check_llm_call()` borne le nombre total d'appels LLM (`max_llm_calls=30`). `check_tool_call()` borne le nombre d'exécutions d'outils (`max_tool_calls=50`). Un `deadline_seconds=300` borne le temps total.

3. **Budget partagé** : L'état d'exécution (`ExecutionState`) est **propagé** du supérieur au subordonné via `propagate_budget()`. Les compteurs ne se réinitialisent jamais lors d'une délégation — un subordonné consomme le budget de son supérieur.

4. **Arrêt explicite** : Quand une limite est atteinte, une `BudgetExceededError` est levée et capturée dans les deux niveaux de la monologue. Le système retourne un message structuré `LOOP_GUARD_TRIGGERED` avec la raison exacte, les compteurs, et la chaîne de délégation.

**Scénario historique #1 (neutralisé) :** L'agent researcher délègue à medical, qui redélègue → `check_delegation()` détecte le cycle ou atteint `max_delegations`.

**Scénario historique #2 (neutralisé) :** Un agent boucle sur un tool partiel → `check_iteration()` + `check_tool_calls()` stoppent l'exécution.

**Risques résiduels :**
- Les appels `call_utility_model()` (hors monologue) ne décomptent pas du budget LLM global — risque faible, impact limité
- Les extensions `monologue_start` s'exécutent avant le check d'itération — ne peuvent pas contourner le garde mais ralentissent la détection d'un cycle de 1 itération

### Hallucinations croisées

Le consensus multi-agents (3 rounds) est un excellent garde-fou, MAIS :
- Les agents partagent le même `AgentContext` (mémoire, projet, config)
- Un agent qui écrit dans la mémoire FAISS peut influencer un autre qui la lit
- La consolidation mémoire utilise un LLM — un LLM qui hallucine pendant la consolidation corrompt la mémoire pour tous les agents suivants

### Perte de contexte

Le subordinate a sa propre `History` mais partage le `AgentContext`. Quand il retourne son résultat, le main agent ne reçoit qu'une string (le `tool_result`). Si le subordinate a produit 3 pages d'analyse, le main agent n'en voit qu'un résumé. L'information se dégrade à chaque niveau de délégation.

### Flags implicites de pipeline

Le mécanisme de coordination utilise des flags mutables sur l'objet Agent :
- `_pipeline_final_response`
- `_pipeline_validated_response`
- `_consensus_result`
- `_skip_llm`

Pas d'état machine explicite, pas de cleanup en cas d'erreur. Un crash au milieu d'un consensus laisse ces flags dans un état incohérent.

## 2.3 Guide de Débogage Multi-Agents (Focus IA de Confiance)

> *Tu vas être amené(e) à investiguer des cas où un agent a produit une réponse douteuse, où un consensus a validé une hallucination, ou où une chaîne de délégation s'est perdue. Voici comment enquêter.*

### Où sont les logs du consensus (les "3 rounds de débat") ?

Le consensus multi-agents est implémenté dans `python/tools/call_subordinate.py`, méthode `_validate_with_consensus()`. Chaque round de débat est loggé dans le `context.log` de l'`AgentContext` courant. Concrètement, voici comment remonter la trace :

1. **Dans l'interface web** : Ouvre le chat concerné. Les messages de type `tool` dans la timeline affichent les appels à `call_subordinate`. Le résultat inclut les métadonnées du consensus (provider, rounds, décision).

2. **Dans les fichiers de chat** : Le fichier `tmp/chats/{ctxid}/chat.json` contient l'intégralité du log structuré. Cherche les entrées de type `"tool"` avec `heading` contenant `"Consensus"` ou `"Subordinate"`. Le champ `kvps` contient les clés-valeurs de diagnostic (provider, latence, nombre de rounds, résultat du vote).

3. **Dans les logs Docker** : En production, lance `docker logs evidence-backend 2>&1 | grep -i "consensus\|CriticalityRouter\|subordinate"`. Les `PrintStyle` du module `call_subordinate.py` émettent des lignes colorées pour chaque étape : choix du routeur, lancement du consensus, résultat de chaque round, décision finale.

4. **En débogage local** : Place un breakpoint dans `_validate_with_consensus()` (ligne ~368 de `call_subordinate.py`). Les variables `rounds`, `votes`, `arbiter_response` contiennent l'état complet du débat.

### Comment vérifier qu'un agent `legal_safe` n'hallucine pas des jurisprudences ?

C'est le risque le plus dangereux du système. Un LLM qui invente une référence juridique (arrêt de Cour de cassation, article de loi) peut induire un professionnel du droit en erreur. Voici les garde-fous en place et leurs limites :

**Garde-fous actifs :**
- Le profil `legal_safe` force `temperature=0` (via `agents/legal_safe/extensions/monologue_start/_10_legal_safe_pipeline.py` qui appelle `python/extensions/legal_safe_mode/_10_legal_safe_integration.py`, ligne 534). Cela réduit la créativité du LLM et favorise les réponses factuelles.
- Le prompt système de `legal_safe` exige des citations explicites et une classification en 3 niveaux de confiance (NIVEAU 1 = source vérifiée, NIVEAU 2 = probable, NIVEAU 3 = incertain).
- L'index juridique SQLite FTS5 (`data/legal/index/legal_index.sqlite`) sert de source de vérité. La recherche FTS5 est effectuée par `python/helpers/legal_orchestrator.py` et `python/helpers/legal_retrieval.py`. Le pipeline dans `python/helpers/legal_pipeline.py` consomme les résultats (via `source_chunk_ids`) pour la validation et le jugement (`judge_legal_draft()`).

**Limites actuelles (honnêteté) :**
- Le LLM peut citer un arrêt avec un numéro légèrement modifié (ex: "Cass. civ. 1, 12 mars 2019, n°18-12.345" au lieu de "18-12.346"). L'index FTS5 ne fait pas de vérification automatique de numéros de pourvoi.
- Le consensus valide la cohérence de la réponse entre agents, pas la véracité des sources. Deux LLMs qui hallucinent le même arrêt se valideront mutuellement.
- Il n'existe pas de pipeline automatique de "fact-checking juridique" (cross-reference avec Légifrance ou Jurica en temps réel). C'est un chantier futur.

**Procédure de vérification manuelle :**
1. Dans le chat, identifie les citations juridiques (format "Cass.", "CE", "Art. L.", "Art. R.").
2. Recherche dans l'index : `docker exec evidence-backend python3 -c "import sqlite3; conn = sqlite3.connect('/app/data/legal/index/legal_index.sqlite'); print(conn.execute('SELECT doc_id, title FROM docs WHERE title LIKE \"%mot-clé%\"').fetchall())"`.
3. Si la référence n'est pas dans l'index, elle est potentiellement hallucinée. Flag le chat et remonte l'information.

### Comment tracer une chaîne de délégation complète

Quand un agent délègue puis que le subordinate redélègue, la trace se dilue. Pour reconstruire la chaîne :

1. Ouvre `tmp/chats/{ctxid}/chat.json`.
2. Cherche tous les `tool_name: "call_subordinate"` dans les agents (champ `agents` → chaque agent a son `history`).
3. L'Agent #0 (index 0) est le principal. L'Agent #1 (index 1) est le premier subordinate. Et ainsi de suite.
4. Chaque agent a sa propre `history` sérialisée. Tu peux reconstituer le "dialogue interne" complet.

**Attention :** Le subordinate partage le même `AgentContext` que le principal. Donc ses écritures mémoire (FAISS) affectent le principal. Si tu suspectes une contamination mémoire, inspecte `memory/users/{username}/{memory_subdir}/` — les fichiers `index.faiss` et `index.pkl` contiennent les vecteurs et les documents associés.

## 2.4 Single Points of Failure (SPOF)

| SPOF | Impact si défaillant | Probabilité | Mitigation existante |
|------|---------------------|-------------|----------------------|
| **Flask process unique** | Tout le backend tombe | Moyenne (observé avec ulimits) | `restart: unless-stopped` dans Docker Compose, healthcheck toutes les 30s |
| **`files.get_base_dir()`** | Toute résolution de path casse, sécurité compromise | Faible mais catastrophique | Aucune. Le système entier repose sur cette valeur. |
| **`settings.json`** | Config perdue, MCP token invalidé, settings UI perdus | Faible | Volume Docker persistant (`evidence-tmp`) |
| **SQLite legal_index** | Recherche juridique KO, pas de réplica | Moyenne | WAL activé pour la concurrence, mais pas de backup automatique |
| **FAISS in-memory** | Mémoire agent perdue au crash si pas persistée à temps | Moyenne | Persistance sur disque (`index.faiss`), mais pas de réplication |
| **Volume Docker `evidence-tmp`** | Tous les chats, settings, images perdus | Faible (sauf disque plein) | Docker volume nommé, mais pas de backup automatique |

## 2.5 Dette Technique Immédiate

### Ce qui a été fait "vite et bien" mais qui craquera

| Élément | Pourquoi c'est fait comme ça | Pourquoi ça va poser problème |
|---------|------------------------------|-------------------------------|
| **Polling HTTP au lieu de WebSocket** | Simple à implémenter, pas de gestion de connexion persistante | 25-250ms de latence, charge réseau inutile, ne scale pas au-delà de ~20 utilisateurs simultanés |
| **Tout en filesystem (JSON)** | Pas de dépendance SGBD, déploiement simple | Pas de requêtes complexes, pas de transactions, race conditions sur écritures concurrentes, tout en mémoire au startup |
| **`asyncio.run()` dans `__init__`** | Besoin d'appeler des extensions async à l'init de l'agent | Peut casser la boucle événementielle, incompatible avec certains serveurs ASGI |
| **Temperature en string `"1"`** | Hérité de la config JSON | Conversions fragiles, mutation directe de la config pour legal_safe |
| **Pas de build frontend** | Pas besoin avec Alpine.js + CDN | Pas de minification, pas de tree-shaking, CSP nécessite `unsafe-inline` et `unsafe-eval` |
| **Extension ordering par filename** | `_10_`, `_20_`, `_30_`... | Fragile, pas documenté, un mauvais nommage casse l'ordre |
| **MCP token recalculé à chaque normalisation** | Déterministe (hash de runtime_id + credentials), stable si credentials inchangés | Recalculé dans `normalize_settings()` à chaque appel de `get_settings()`. Pas de vraie rotation, mais recomputation coûteuse |
| **`mcp_config.json` avec chemins hardcodés** | Config développeur locale | `/Users/aminemohamed/Desktop` en production = fuite d'information |
| **index.html de 1300 lignes** | Tout-en-un, pas de composants | Maintenance cauchemardesque |
| **Pas de tests frontend** | Alpine.js rend le testing non-trivial | Régressions silencieuses sur chaque changement UI |

### Cadre de gestion de la dette : Patcher vs. Accepter (Anti-Panique)

> **Message direct au Lead Engineer :** Cette liste peut donner le vertige. C'est normal. La tentation sera forte de "tout refaire proprement". **Résiste.** Voici le cadre de décision qui te dit quoi traiter en urgence et quoi laisser tranquille.

**PATCHER IMMÉDIATEMENT (Semaine 1-2) — Sécurité :**
- Les failles de path traversal dans `file_info.py`, `download_work_dir_file.py`, `api_files_get.py`. Ce sont des vulnérabilités actives. Chaque jour où elles restent ouvertes est un jour où un utilisateur malveillant peut lire `.env` et `users.json`. Le pattern existe déjà dans `image_get.py` — tu as juste à le répliquer.
- L'isolation des chats (`persist_chat.py`). Le pattern existe déjà pour les projets et les images : sous-dossiers par utilisateur + contrôle d'accès dans l'API. C'est du copier-adapter.

**ACCEPTER PROVISOIREMENT (Mois 1-3) — Architecture :**
- **L'architecture filesystem (JSON au lieu de SQL).** Ne tente PAS de migrer vers PostgreSQL ou SQLite pour les chats et settings dans les 3 premiers mois. Raisons : (a) ça fonctionne pour le volume actuel (~11 utilisateurs, ~50-100 chats), (b) une migration SGBD touche TOUT le code (persist_chat, projects, settings, file_browser), (c) le risque de régression est énorme tant que tu ne maîtrises pas la codebase. Planifie cette migration quand le volume atteindra 500+ chats ou 50+ utilisateurs simultanés, avec des benchmarks réels.
- **Le polling HTTP.** Inélégant mais fonctionnel. La migration WebSocket est un Chantier de Fond (Semaine 3-4), pas une urgence de Semaine 1.
- **Le frontend monolithique (`index.html` 1300 lignes).** Ça fait mal aux yeux, mais ça ne génère pas de bugs tant que les changements sont localisés. Un refactoring frontend complet est un projet de 2-3 semaines à planifier au trimestre suivant.
- **`asyncio.run()` dans `__init__`.** Anti-pattern connu, mais le corriger nécessite de repenser l'initialisation des agents. À planifier quand tu migreras vers un framework ASGI.

**SURVEILLER ACTIVEMENT (Monitoring) :**
- La fuite de file descriptors. Le `ulimits` à 65536 est un pansement. Mets en place un monitoring (`docker exec evidence-backend bash -c "ls /proc/1/fd | wc -l"` dans un cron toutes les heures). Quand les FD remontent vers 1000+, un `docker compose restart evidence-backend` règle le problème temporairement. La cause racine (connexions aiohttp non fermées, index FAISS non libérés) est un chantier d'investigation pour le mois 2.

## 2.6 Confusion de nommage : PRISM / Evidence / KOREV

> *Tu vas rencontrer 3 noms différents dans le code. Voici la cartographie pour ne pas te perdre.*

| Nom | Signification | Où tu le verras |
|-----|---------------|-----------------|
| **KOREV** | Nom de la société/marque | Variables d'env (`KOREV_PRODUCTION`, `KOREV_BEHIND_PROXY`), branding UI, docs |
| **Evidence** | Nom du produit | Containers Docker (`evidence-backend`), volumes (`evidence-data`), noms de classes (`EvidencePack`), documentation |
| **PRISM** | Nom historique du protocole de consensus multi-LLM | Repo GitHub (`PRISM-Oracle`), `criticality_router.py` ("consensus PRISM"), agents medical/legal ("arbitres PRISM"), certains tests (`test_prism_*`) |

**Attention :** Le repo GitHub s'appelle `PRISM-Oracle`. Ce n'est PAS le nom du produit. C'est un héritage de la phase R&D initiale. Le produit s'appelle **KOREV Evidence**.

**Clarification PRISM :** Dans le code medical, "PRISM" désigne le protocole de validation par consensus multi-LLM (3 rounds de débat). Ce n'est pas un produit distinct — c'est une fonctionnalité interne d'Evidence.

## 2.7 Montée en charge — Pires scénarios

**Scénario 1 : 50 utilisateurs simultanés**
- Le polling HTTP (25-250ms par user) génère 200-2000 requêtes/seconde juste pour le poll
- Flask en mode synchrone (Werkzeug) ne supporte pas cette charge
- Les chats sont tous chargés en mémoire — avec 50 users actifs et 20 chats chacun, c'est 1000 `AgentContext` en RAM

**Scénario 2 : Agent en boucle** ✅ (mitigé par ExecutionBudget v4.0)
- ~~Un agent qui itère 50 fois dans sa monologue (pas de hard limit) accumule du contexte à chaque tour~~ → Borné à `max_iterations=25` par défaut
- ~~Le context window du LLM explose → erreurs API → retry → plus d'itérations → plus de mémoire~~ → Borné à `max_llm_calls=30` et `deadline_seconds=300`
- Le file descriptor leak s'accélère (chaque appel LLM ouvre des connexions) — ⚠ ce risque persiste indépendamment du budget

**Scénario 3 : Indexation légale massive**
- L'index SQLite FTS5 est un fichier unique, pas de sharding
- WAL aide la concurrence lecture/écriture mais pas la performance brute
- 100K documents → requêtes de plusieurs secondes

---

# Partie 3 : Guide de Survie Opérationnel

## 3.1 Setup Environnement de Développement

### Prérequis

```bash
# Python 3.11+ (3.12 non testé)
python3 --version

# Node.js 18+ (pour les MCP servers)
node --version

# Docker + Docker Compose (pour le déploiement)
docker --version && docker compose version

# Tesseract OCR (pour pdf_ocr et document_query)
tesseract --version

# Playwright (pour browser_agent)
playwright install
```

### Installation locale

```bash
# 1. Cloner le repo
git clone https://github.com/Makk7709/PRISM-Oracle.git
cd PRISM-Oracle

# 2. Environnement virtuel
python3 -m venv .venv
source .venv/bin/activate

# 3. Dépendances
pip install -r requirements.txt

# 4. Configuration
cp .env.example .env
# Éditer .env : au minimum API_KEY_OPENAI ou API_KEY_ANTHROPIC

# 5. Lancer
python run_ui.py
# → http://localhost:5050
```

### Configuration minimale `.env`

```env
# LLM API (au moins un)
API_KEY_OPENAI=sk-...
# ou API_KEY_ANTHROPIC=sk-ant-...

# Auth (vide = pas d'auth, dangereux)
AUTH_LOGIN=dev
AUTH_PASSWORD=devpass

# Mode dev
EVIDENCE_ENV=development
```

### Garde-fous d'exécution (optionnel, `.env`)

Les limites du système `ExecutionBudget` sont configurables via variables d'environnement. Les défauts sont conservateurs — ne les augmenter qu'en connaissance de cause.

```env
# Anti-boucle infinie (défauts sûrs, augmenter uniquement si nécessaire)
EVIDENCE_MAX_ITERATIONS=25        # Itérations max du message loop par exécution
EVIDENCE_MAX_DEPTH=5              # Profondeur max de récursion (_process_chain)
EVIDENCE_MAX_DELEGATIONS=8        # Délégations max inter-agents
EVIDENCE_MAX_TOOL_CALLS=50        # Appels d'outils max par exécution
EVIDENCE_MAX_LLM_CALLS=30         # Appels LLM max par exécution
EVIDENCE_MAX_CONSENSUS_ROUNDS=3   # Rounds de consensus max
EVIDENCE_DEADLINE_SECONDS=300     # Timeout global en secondes
EVIDENCE_MAX_DELEGATION_REVISITS=1 # Revisites autorisées par profil (0 = strict no-cycle)
```

### Mode Production (Docker)

```bash
cd deploy
cp .env.example .env
# Éditer .env avec les vrais API keys et mots de passe

# Si users.json existe : mode multi-utilisateur
cp users.json.example users.json
# Éditer users.json avec les comptes (hasher avec argon2)

# Build et lancer
docker compose build
docker compose up -d

# Vérifier
docker compose ps
docker logs -f evidence-backend
```

## 3.2 Arborescence des Fichiers Critiques

```
.
├── agent.py                 # ⭐ Cœur : AgentContext, Agent, monologue loop
├── models.py                # Configuration LLM (ModelConfig, providers)
├── initialize.py            # Bootstrap (agent config, job loop)
├── run_ui.py                # ⭐ Flask app, routes, auth, middleware
│
├── python/
│   ├── api/                 # ⭐ Endpoints REST (un fichier = un endpoint)
│   │   ├── projects.py      # CRUD projets + isolation owner
│   │   ├── image_get.py     # Servir images/fichiers
│   │   ├── message.py       # Recevoir messages utilisateur
│   │   └── ...
│   │
│   ├── helpers/             # ⭐ Logique métier
│   │   ├── projects.py      # Gestion projets filesystem
│   │   ├── memory.py        # FAISS vector store
│   │   ├── persist_chat.py  # Sérialisation/chargement chats
│   │   ├── settings.py      # Gestion settings (2222 lignes !)
│   │   ├── user_manager.py  # Auth multi-utilisateur
│   │   ├── runtime.py       # Détection Docker, environment
│   │   ├── files.py         # I/O fichiers, templates, placeholders
│   │   ├── legal_pipeline.py # Pipeline juridique (1807 lignes)
│   │   ├── legal_orchestrator.py # Orchestration recherche juridique + FTS5
│   │   ├── legal_retrieval.py   # Récupération dans l'index juridique
│   │   ├── collaborative_consensus.py # Moteur de débat 3 rounds
│   │   ├── criticality_router.py     # Évaluation criticité (LEVEL 1-3)
│   │   ├── execution_budget.py  # ⭐ Garde-fou anti-boucles infinies (budget, limites, cycles)
│   │   ├── evidence.py         # EvidencePack — traçabilité des sources
│   │   └── user_workspace.py   # Isolation workspaces par utilisateur
│   │
│   ├── tools/               # ⭐ Outils disponibles pour les agents
│   │   ├── call_subordinate.py  # Délégation (648 lignes)
│   │   ├── code_execution_tool.py # Exécution code (551 lignes)
│   │   ├── generate_image.py    # Génération images
│   │   └── ... (23 outils)
│   │
│   ├── extensions/          # ⭐ Hooks du pipeline agent
│   │   ├── monologue_start/
│   │   ├── message_loop_prompts_before/
│   │   └── ... (24 points d'extension)
│   │
│   └── security/            # Auth, path safety, CSRF, rate limit, upload validation
│
├── agents/                  # Profils d'agents
│   ├── default/prompts/     # Prompts de base (hérités par tous)
│   ├── multitask/           # Agent par défaut
│   ├── legal_safe/          # Mode juridique
│   └── ... (12 profils)
│
├── prompts/                 # System prompts par défaut
│   ├── agent.system.main.md # Point d'entrée (includes)
│   └── agent.system.main.*.md
│
├── webui/                   # Frontend
│   ├── index.html           # Page principale (1300 lignes)
│   ├── index.js             # ⭐ Polling, sendMessage, startPolling (699 lignes)
│   ├── js/                  # Logique (messages, settings, scheduler...)
│   └── components/          # Composants Alpine.js (sidebar, modals...)
│
├── deploy/                  # Déploiement production
│   ├── docker-compose.yml   # Orchestration (backend, Caddy, Samba)
│   ├── Dockerfile.backend   # Image Docker backend
│   ├── config/Caddyfile     # Reverse proxy
│   └── scripts/             # install.sh, upgrade.sh, rollback.sh
│
└── tests/                   # Tests
    ├── security/            # Tests sécurité (auth, path traversal)
    ├── e2e/                 # Tests end-to-end
    └── harness/             # Fixtures, fakes, assertions
```

## 3.3 Tests et Déploiement

### Tests existants

```bash
# Tests sécurité (les plus fiables)
pytest tests/security/ -v

# Tests e2e
pytest tests/e2e/ -v

# Tests garde-fous anti-boucles infinies (34 tests)
pytest tests/test_execution_budget.py -v

# Tests consensus / PRISM
pytest tests/test_prism_consensus.py tests/test_prism_tally_quorum.py tests/test_prism_timeouts.py -v

# Tous les tests
pytest tests/ -v
```

### CI/CD (GitHub Actions)

| Workflow | Trigger | Tests |
|----------|---------|-------|
| `main_gate.yml` | Pull Request vers main + workflow_dispatch | Smoke, security, Redis, core, extended |
| `security_ci.yml` | Changements dans `python/security/`, `tests/security/`, `run_ui.py` | Tests sécurité uniquement |
| `legal_pipeline_ci.yml` | Changements dans `python/legal_sources/`, `python/helpers/legal_*.py`, `python/extensions/legal_safe_mode/`, `tests/test_legal_*.py` | Pipeline juridique |

**Point critique :** Les tests "extended" ont `continue-on-error: true`. Des échecs sont silencieusement ignorés. Pas de déploiement automatique (pas de CD — le déploiement est manuel via SSH + docker cp ou rebuild).

### Procédure de déploiement actuelle (manuelle)

```bash
# 1. Sur la machine locale
git add . && git commit -m "description" && git push origin main

# 2. Copier les fichiers sur le serveur
scp fichier ubuntu@<IP>:~/PRISM-Oracle/fichier

# 3. Injecter dans le container
docker cp fichier evidence-backend:/app/fichier

# 4. Redémarrer
cd ~/PRISM-Oracle/deploy && docker compose restart evidence-backend

# OU rebuild complet (prend ~15 min)
docker compose build --no-cache evidence-backend
docker compose up -d evidence-backend
```

## 3.4 Conventions de Code et Règles Non Négociables

### Sécurité — JAMAIS faire

| Interdit | Pourquoi | Faire plutôt |
|----------|----------|--------------|
| `os.path.join(base, user_path)` sans validation | Path traversal | `safe_path_join(base, path)` de `python/security/path_safety.py` |
| Lire `.env` avec `open()` | Peut exposer des secrets | Utiliser `os.environ.get()` ou `settings.get_settings()` |
| `eval()` ou `exec()` avec input utilisateur | Injection de code | Utiliser `code_execution_tool` (⚠ pas de vrai sandbox actuellement — voir section 2.1) |
| Stocker des mots de passe en clair | Exposition | `hash_password()` de `python/security/auth.py` (Argon2id) |
| Créer un endpoint sans `@_requires_auth` | Auth bypass | Toujours utiliser le décorateur sauf pour `/healthz` et `/login` |
| Modifier `mcp_config.json` avec des chemins locaux | Fuite d'info en prod | Utiliser `mcp_config.production.json` |

### Conventions de code

- **API handlers** : 1 fichier par endpoint dans `python/api/`, classe héritant de `ApiHandler`
- **Extensions** : fichiers préfixés `_NN_` pour l'ordre d'exécution (ex: `_10_system_prompt.py`)
- **Profils d'agents** : un répertoire sous `agents/` avec `_context.md`, `prompts/`, optionnel `tools/`, `extensions/`, `settings.json`
- **Prompts** : Markdown avec placeholders `{{variable}}` et includes `{{ include "file.md" }}`
- **Settings** : Les clés sensibles vont dans `.env`, le reste dans `tmp/settings.json`

### Architecture décisionnelle

Quand tu veux ajouter une fonctionnalité, demande-toi :
1. **C'est un outil ?** → `python/tools/nom_tool.py` + prompt dans `prompts/agent.system.tool.nom_tool.md`
2. **C'est un hook sur le pipeline ?** → Extension dans `python/extensions/<point>/`
3. **C'est un nouveau type d'agent ?** → Nouveau profil dans `agents/`
4. **C'est une API pour le frontend ?** → Handler dans `python/api/` + fetch dans `webui/js/`
5. **C'est un setting ?** → Ajouter dans `settings.py` avec les bonnes catégories

---

# Partie 4 : Feuille de Route — 30 Premiers Jours

## Semaine 1-2 : Quick Wins (Familiarisation)

### Quick Win #1 : Corriger le path traversal dans `file_info.py` (**SÉCURITÉ CRITIQUE**)

**Fichier :** `python/api/file_info.py`  
**Effort :** 30 minutes  
**Impact :** Ferme une vulnérabilité critique exploitable immédiatement

**Le principe de sécurité à comprendre :**

Un path traversal, c'est quand un utilisateur envoie un chemin comme `../../etc/passwd` et que le serveur le concatène naïvement avec son répertoire de base :

```python
# DANGEREUX — ne fais JAMAIS ça
path = user_input                          # "../../etc/passwd"
abs_path = os.path.join("/app", path)      # "/app/../../etc/passwd"
# os.path.join ne vérifie rien. Le résultat résolu est "/etc/passwd".
```

La fonction `safe_path_join()` (dans `python/security/path_safety.py`) corrige ça en 3 étapes :
1. **Résolution** : elle appelle `Path.resolve()` (équivalent pathlib de `os.path.realpath()`) pour résoudre tous les `..`, symlinks et chemins relatifs en un chemin absolu canonique.
2. **Vérification de confinement** : elle vérifie que le chemin résolu commence bien par le répertoire de base (`/app/`). Si le résultat est `/etc/passwd`, il ne commence pas par `/app/` → rejeté.
3. **Rejet des symlinks** (optionnel en production) : pour empêcher un attaquant qui aurait créé un symlink `/app/data/lien → /etc/`.

```python
# SÛR — le pattern à suivre
from python.security.path_safety import safe_path_join, SecurityError
try:
    resolved = safe_path_join(base_dir, user_path, allow_symlinks=False)
except SecurityError:
    raise ValueError("Path is outside of allowed directory")
```

**Ce que tu dois faire concrètement :**
1. Ouvrir `python/api/file_info.py` et `python/api/download_work_dir_file.py`.
2. Repérer les appels à `files.get_abs_path(path)` qui prennent directement l'input utilisateur.
3. Les remplacer par `safe_path_join(files.get_base_dir(), path)`, exactement comme dans `python/api/image_get.py` (lignes 50-57 — c'est ton modèle).
4. Ajouter un test dans `tests/security/` qui vérifie qu'un chemin `../../etc/passwd` est rejeté.
5. Faire le même traitement dans `python/api/api_files_get.py`.

### Quick Win #2 : Ajouter du logging structuré sur les erreurs 500

**Fichier :** `run_ui.py`  
**Effort :** 1 heure  
**Impact :** Diagnostiquer les crashes en production sans fouiller les logs Docker

Actuellement, les erreurs 500 retournent un message générique côté utilisateur et un traceback dans les logs Docker. Ajouter un `@app.errorhandler(500)` qui logue dans un fichier structuré (JSON) avec timestamp, username, endpoint, traceback, et retourne un ID de corrélation à l'utilisateur.

### Quick Win #3 : Documenter les profils d'agents existants

**Répertoire :** `agents/*/`  
**Effort :** 2 heures  
**Impact :** Permet à toute l'équipe de comprendre quel profil utiliser quand

Chaque profil a un `_context.md` mais ils sont inégaux en qualité. Uniformiser avec : description, cas d'usage, temperature, outils activés, garde-fous spécifiques. C'est de la documentation, pas du code — zéro risque de casser quoi que ce soit.

## Semaine 3-4 : Chantiers de Fond

### Chantier #1 : Isolation des chats par utilisateur (PRIORITÉ HAUTE)

**État actuel :** Tous les chats dans `tmp/chats/`, ownership via un champ JSON.  
**Cible :** `tmp/chats/{username}/` avec contrôle d'accès dans l'API.  

**Pourquoi c'est prioritaire :**
- Un utilisateur peut théoriquement accéder aux chats d'un autre
- Au startup, tous les chats sont chargés en mémoire (ne scale pas)
- C'est le même pattern que ce qui a été fait pour les images et les projets

**Plan d'attaque :**
1. Modifier `persist_chat.py` : `save_tmp_chat()` et `load_tmp_chats()` pour utiliser des sous-dossiers par user
2. Migrer les chats existants (script one-shot, comme pour les images)
3. Ajouter un contrôle d'accès dans `chat_load.py` (vérifier `session['username']` vs chat owner)
4. Modifier `load_tmp_chats()` pour ne charger que les chats du user connecté (lazy loading)
5. Tests dans `tests/security/test_chat_isolation.py`

### Chantier #2 : Remplacer le polling HTTP par des WebSockets (PRIORITÉ MOYENNE)

**État actuel :** Long polling 25-250ms via POST `/poll`.  
**Cible :** WebSocket (ou SSE) pour le streaming temps réel.

**Pourquoi :**
- Le polling génère une charge réseau et serveur disproportionnée
- La latence perçue est mauvaise (250ms entre le moment où l'agent répond et l'affichage)
- Flask supporte les WebSockets via `flask-sock` ou migration vers ASGI avec `quart`

**Plan d'attaque :**
1. Évaluer `flask-sock` vs migration Quart (ASGI natif)
2. Implémenter un endpoint `/ws` qui stream les logs du contexte en temps réel
3. Adapter `webui/index.js` : remplacer `startPolling()` par un `WebSocket`
4. Garder le polling comme fallback (proxies d'entreprise bloquent parfois les WS)
5. Benchmark : mesurer le nombre de requêtes/seconde avant/après

---

## Annexe A : Inventaire complet des fichiers clés

| Fichier | Lignes | Criticité | Commentaire |
|---------|--------|-----------|-------------|
| `agent.py` | ~1015 | 🔴 Critique | Cœur du système, à comprendre en premier |
| `run_ui.py` | ~588 | 🔴 Critique | Point d'entrée Flask, auth, routing |
| `python/helpers/settings.py` | ~2222 | 🟠 Élevé | Monstre : gère toute la config, les secrets, le MCP |
| `python/helpers/legal_pipeline.py` | ~1807 | 🟠 Élevé | Pipeline juridique complet |
| `python/tools/call_subordinate.py` | ~648 | 🔴 Critique | Délégation + consensus — le cœur de l'orchestration multi-agents |
| `python/helpers/execution_budget.py` | ~260 | 🔴 Critique | Garde-fou anti-boucles infinies : budget, limites, cycles, deadline |
| `python/tools/code_execution_tool.py` | ~551 | 🟠 Élevé | Exécution de code — surface d'attaque |
| `python/helpers/memory.py` | ~581 | 🟠 Élevé | FAISS, embeddings, mémoire agent |
| `python/helpers/persist_chat.py` | ~300 | 🟡 Moyen | Sérialisation chats — pas d'isolation user |
| `python/helpers/projects.py` | ~389 | 🟡 Moyen | CRUD projets + isolation owner |
| `python/api/image_get.py` | ~237 | 🟡 Moyen | Modèle de bonne sécurité (safe_path_join) |
| `webui/js/messages.js` | ~1093 | 🟡 Moyen | Rendu des messages — complexe |
| `webui/js/scheduler.js` | ~1835 | 🟡 Moyen | Planificateur de tâches |
| `models.py` | ~930 | 🟡 Moyen | Providers LLM |

## Annexe B : Glossaire

| Terme | Définition |
|-------|-----------|
| **AgentContext** | Conteneur d'état pour une conversation (user, agents, log, config) |
| **Monologue** | Boucle interne d'un agent : prompt → LLM → tool → repeat |
| **Subordinate** | Agent créé par un autre via `call_subordinate` |
| **ExecutionBudget** | Système centralisé de garde-fous (`python/helpers/execution_budget.py`). Chaque exécution transporte un `ExecutionState` partagé et des `BudgetLimits`. Borne : itérations, profondeur, délégations, tool calls, LLM calls, consensus rounds, deadline. Configurable via env `EVIDENCE_*`. |
| **Extension** | Hook Python exécuté à un point précis du pipeline agent |
| **Profile** | Configuration complète d'un type d'agent (prompts, tools, extensions) |
| **CriticalityRouter** | Évalue la criticité d'une requête (LEVEL 1-3). Seuls les LEVEL 3 ou `force_consensus` déclenchent un consensus |
| **Consensus** | Débat collaboratif entre plusieurs LLMs pour valider une réponse (3 rounds : analyse indépendante → débat → synthèse) |
| **PRISM** | Nom historique du protocole de consensus multi-LLM. Utilisé dans le medical et le juridique. Le repo GitHub s'appelle encore `PRISM-Oracle` (héritage) |
| **Evidence Pack** | Objet structuré (`python/helpers/evidence.py`) qui encapsule sources, citations et métadonnées de confiance pour une réponse validée |
| **MCP** | Model Context Protocol — standard pour connecter des outils externes aux LLMs |
| **A2A** | Agent-to-Agent — protocole de communication inter-agents |
| **FAISS** | Facebook AI Similarity Search — index vectoriel pour la mémoire sémantique |
| **FTS5** | Full-Text Search 5 — module SQLite pour la recherche textuelle (index juridique) |
| **LiteLLM** | Proxy unifié pour appeler différents providers LLM (OpenAI, Anthropic, Google...) |
| **WorkspaceManager** | Gestionnaire d'espaces de travail par utilisateur (`python/helpers/user_workspace.py`) |
| **DeferredTask** | Wrapper asyncio pour exécuter la monologue agent dans un thread séparé (`python/helpers/defer.py`) |

## Annexe C : Contacts et Ressources

| Ressource | Emplacement |
|-----------|-------------|
| Repo GitHub | `https://github.com/Makk7709/PRISM-Oracle` |
| Serveur Production | OVH VPS, Docker Compose |
| Documentation existante | `docs/` (architecture, installation, legal, consensus) |
| CI/CD | `.github/workflows/` (main_gate, security, legal) |
| Logs production | `docker logs evidence-backend` ou volume `evidence-logs` |

## Annexe D : Matrice de Priorité (Vue Synthétique)

| Action | Urgence | Effort | Risque si ignoré |
|--------|---------|--------|------------------|
| Patcher path traversal (`file_info`, `download_work_dir_file`, `api_files_get`) | IMMÉDIAT | 30 min par fichier | Lecture arbitraire de fichiers (`.env`, `users.json`) |
| ~~Ajouter `max_iterations` à la monologue~~ | ✅ FAIT (v4.0) | — | ~~Agent en boucle infinie~~ → Borné par `ExecutionBudget.max_iterations=25` + `max_llm_calls=30` + `deadline=300s` |
| ~~Ajouter `max_depth` à la délégation~~ | ✅ FAIT (v4.0) | — | ~~Stack overflow, délégation récursive infinie~~ → Borné par `ExecutionBudget.max_depth=5` + `max_delegations=8` + cycle detection |
| Monitoring file descriptors | Semaine 1 | 1 heure (cron) | Crash backend en production (déjà observé) |
| Logging structuré des erreurs 500 | Semaine 1-2 | 1 heure | Diagnostics aveugles en production |
| Isoler les chats par utilisateur | Semaine 2-3 | 2-3 jours | Un utilisateur accède aux conversations d'un autre |
| Documenter les profils agents | Semaine 2 | 2 heures | Équipe ne sait pas quel profil utiliser |
| Remplacer polling par WebSocket | Mois 1-2 | 1 semaine | Latence élevée, charge serveur, ne scale pas |
| Sandbox code execution | Mois 2-3 | 1-2 semaines | Agent hallucinant peut détruire des données |
| Migrer filesystem vers SGBD | Mois 4+ | 3-4 semaines | Race conditions, pas de transactions (acceptable court terme) |
| Refactoring frontend | Mois 4+ | 2-3 semaines | Maintenance difficile (acceptable court terme) |

## Annexe E : Checklist "Premier Jour"

- [ ] Cloner le repo et lancer le backend en local (`python run_ui.py`)
- [ ] Se connecter à l'interface web, créer un chat, envoyer un message
- [ ] Lire `agent.py` en entier (1015 lignes — compte 2 heures)
- [ ] Lire `python/tools/call_subordinate.py` (648 lignes — le cœur multi-agents)
- [ ] Ouvrir un chat en mode `legal_safe`, poser une question juridique, observer la délégation et le consensus dans les logs
- [ ] Se connecter au serveur production en SSH, vérifier `docker compose ps`, lire les derniers logs
- [ ] Identifier les 3 fichiers de sécurité à patcher (Quick Win #1) et lire `image_get.py` comme modèle

---

*Ce document est un instantané au 2026-03-11 (v4.0, patch anti-boucles infinies + garde-fous d'exécution). Il doit être mis à jour à chaque changement architectural majeur. En cas de doute sur une information, la source de vérité est toujours le code, pas ce document.*
