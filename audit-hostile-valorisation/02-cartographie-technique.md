# 02 — Cartographie Technique

**Projet** : KOREV Evidence  
**Date** : 3 avril 2026 (mise a jour : 17 avril 2026)  
**Methode** : lecture seule du depot, aucune modification

---

## 1. Vue d'ensemble du depot

### Metriques structurelles

| Metrique | Valeur |
|---|---|
| Fichiers source Python (`python/`) | ~356 fichiers, ~99 716 lignes |
| Fichiers de test (`tests/`) | ~180 fichiers, reference documentaire a 3 910 tests collectes avec parametrisation (audit initial : ~3 846 tests / 3 165 fonctions) |
| Fichiers Markdown (hors venv/vendor) | ~237 |
| Prompts LLM (`prompts/`) | ~103 fichiers |
| Profils d'agents (`agents/`) | ~12 profils |
| Extensions (`python/extensions/`) | ~48 modules |
| Outils agent (`python/tools/`) | ~23 modules |
| Handlers API (`python/api/`) | ~71 modules |
| MCP servers integres | 3 (OpenAlex, Semantic Scholar, PubMed) |
| Dependances Python (`requirements.txt`) | ~61 packages |
| Total fichiers Python (tout le depot) | ~599 fichiers, ~186 865 lignes |
| Total fichiers dans le depot | ~1 796 |

### Arborescence de premier niveau

```
KOREV_Oracle/
├── agent.py              ← Boucle principale d'orchestration LLM
├── models.py             ← Integration LiteLLM, embeddings
├── initialize.py         ← Construction AgentConfig
├── run_ui.py             ← Application Flask (745 lignes)
├── prepare.py            ← Preparation environnement runtime
├── preload.py            ← Prechargement Whisper/TTS/embeddings
├── python/               ← Bibliotheque applicative principale
│   ├── api/              ← 68 handlers HTTP (ApiHandler)
│   ├── helpers/          ← 177 modules (~75 000 lignes)
│   ├── tools/            ← Outils agent (code exec, browser, PDF...)
│   ├── extensions/       ← Hooks cycle de vie (46 modules)
│   ├── security/         ← Auth, authz, path safety, rate limit
│   ├── legal_sources/    ← Pipeline d'ingestion juridique
│   ├── consensus/        ← Moteur de consensus
│   └── observability/    ← Metriques runtime
├── agents/               ← Profils de personas (prompts + extensions)
├── prompts/              ← Fragments de prompts systeme
├── tools/                ← Scripts utilitaires (smoke, diagnostics)
├── tests/                ← Suite de tests (~180 fichiers, reference documentaire 3 910 tests avec parametrisation)
├── docs/                 ← Documentation (65 fichiers, ~22 981 lignes)
├── deploy/               ← Docker, Caddy, scripts de deploiement
├── docker/               ← Images Docker alternatives (base Kali)
├── scripts/              ← Migrations, validation, installation
├── mcp_servers/          ← Serveurs MCP integres (3)
├── knowledge/            ← Base de connaissances agent
├── legal/                ← Licence, notices tierces
├── conf/                 ← Providers LiteLLM, gitignore projets
├── fonts/                ← Polices pour PDF
├── webui/                ← Frontend statique (JS/HTML/CSS)
├── data/                 ← Donnees runtime (legal index)
├── memory/               ← Cache FAISS/embeddings
└── .github/workflows/    ← CI GitHub Actions (3 workflows)
```

---

## 2. Modules critiques et flux principaux

### 2.1 Boucle d'orchestration agent

```
Utilisateur → run_ui.py (Flask) → Agent.monologue() → LLM (LiteLLM)
                                      ↓
                              Extensions (hooks)
                                      ↓
                              Tool execution loop
                              ├── python/tools/*
                              ├── MCP servers (stdio/SSE)
                              └── Subordinate agents
                                      ↓
                              Response → History → Memory (FAISS)
```

**Fichiers cles** :
- `agent.py` : boucle `monologue()` (~1 144 lignes), execution d'outils, gestion du budget
- `models.py` : wrapper LiteLLM avec retry, streaming, browser compat (~931 lignes)
- `python/helpers/mcp_server.py` : proxy MCP dynamique, authentification par token URL

### 2.2 Pipeline PRISM / Consensus

```
call_subordinate → ConsensusManager → ArbiterCaller(s)
                        ↓                    ↓
                   Votes (min quorum)    LLM arbitres
                        ↓
                   DecisionProposal
                        ↓
                   check_consensus (fail-closed)
                        ↓
                   RouteDecision (deterministe)
```

**Fichiers cles** :
- `python/helpers/consensus_manager.py` : gestion des propositions et quorum (~658 lignes)
- `python/helpers/consensus_arbiter.py` : appels LLM aux arbitres (~841 lignes)
- `python/consensus/engine.py` : point d'entree `run_consensus`
- `python/helpers/router/router.py` : routage deterministe avec hashing
- `python/helpers/router/policy.py` : tables de mots-cles pour classification

### 2.3 Framework de conformite Evidence

```
SessionEnvelope → ReasoningEngine → ComplianceGrid
      ↓                ↓                  ↓
 Metadata         MetaDecision      AI Act articles
      ↓                ↓                  ↓
AuditReportRenderer ← IntegrityBlock (HMAC/RSA)
      ↓
Rapport Markdown (10 blocs canoniques)
      ↓
Archivage + signature
```

**Fichiers cles** :
- `python/helpers/reporting/evidence_native.py` : assemblage du rapport (~1 422 lignes)
- `python/helpers/integrity_block.py` : hashes SHA-256 + HMAC/RSA (cle HMAC obligatoire, RuntimeError si absente)
- `python/helpers/reasoning_engine.py` : moteur de raisonnement (~1 190 lignes)
- `python/helpers/session_envelope.py` : metadonnees de session
- `python/helpers/replay_engine.py` : rejeu deterministe de sessions (~327 lignes) — **nouveau avril 2026**
- `python/helpers/human_review.py` : workflow de revue humaine (~327 lignes) — **nouveau avril 2026**
- `python/helpers/dynamic_risk_register.py` : registre de risques dynamique (~403 lignes) — **nouveau avril 2026**

### 2.4 Pipeline juridique

```
Sources officielles (Legifrance, Judilibre, CNIL)
      ↓
Fetchers (python/legal_sources/fetchers/)
      ↓
Chunking → Indexation FTS5 (SQLite)
      ↓
legal_orchestrator.py → Recherche + reponse
```

**Fichiers cles** :
- `python/helpers/legal_orchestrator.py` (~1 961 lignes)
- `python/helpers/legal_pipeline.py` (~1 807 lignes)
- `python/legal_sources/` : fetchers, chunking, indexation

---

## 3. Dependances structurantes

### Python (critiques)

| Dependance | Role | Risque |
|---|---|---|
| `litellm` | Abstraction multi-LLM | Installe hors `requirements.txt`, version forcee `1.79.3` |
| `langchain-core` + `langchain-community` | RAG, embeddings, orchestration | Stack lourde, API instable |
| `flask[async]` | Serveur web | Standard, stable |
| `faiss-cpu` | Index vectoriel memoire | Performance limitee sans GPU |
| `sentence-transformers` | Embeddings locaux | Poids telecharges au runtime |
| `playwright` | Navigateur headless | Necessite Chromium (~100 MB) |
| `openai-whisper` | Speech-to-text | Modele lourd, dependencies C |
| `argon2-cffi` | Hashing mots de passe | Standard industrie |
| `weasyprint` | Generation PDF | Dependances systeme lourdes |
| `cryptography` | RSA pour signatures | Standard |

### Node.js (runtime)

| Dependance | Role |
|---|---|
| `@playwright/mcp` | MCP server navigateur (npx) |
| `@modelcontextprotocol/server-brave-search` | MCP recherche Brave (npx) |
| MCP servers locaux (OpenAlex, etc.) | `axios`, `express` |

### Infrastructure

| Composant | Role |
|---|---|
| Docker Compose | Orchestration multi-container |
| Caddy | Reverse proxy, TLS automatique |
| Redis (optionnel) | Rate limiting distribue, task store |
| Samba | Partage fichiers (optionnel) |

---

## 4. Zones critiques identifiees

### Haute charge cognitive (modules > 1 000 lignes)

| Module | Lignes | Risque |
|---|---|---|
| `python/helpers/settings.py` | ~2 225 | Monolithe de configuration, couplage fort |
| `python/helpers/adversarial_instruction.py` | ~2 123 | Detection d'injections adverses |
| `python/helpers/legal_orchestrator.py` | ~1 960 | Orchestration juridique |
| `python/helpers/legal_pipeline.py` | ~1 807 | Pipeline d'ingestion juridique |
| `python/helpers/strategic_orchestrator.py` | ~1 560 | Orchestration strategique |
| `python/helpers/task_scheduler.py` | ~1 458 | Planificateur de taches |
| `python/helpers/reporting/evidence_native.py` | ~1 422 | Assemblage rapport d'audit |
| `python/helpers/pdf_extraction/pipeline.py` | ~1 217 | Extraction PDF/OCR |
| `python/helpers/reasoning_engine.py` | ~1 190 | Moteur de raisonnement |
| `python/helpers/mcp_handler.py` | ~1 148 | Gestionnaire MCP |
| `agent.py` | ~1 144 | Boucle agent principale |
| `python/helpers/evidence_pdf_engine.py` | ~1 091 | Moteur PRISM PDF (WeasyPrint + ReportLab) — **reecrit avril 2026** |
| `python/helpers/metacognition.py` | ~1 046 | Metacognition (auto-evaluation, confiance calibree) |

### Zones a forte connaissance implicite

1. **Contrat d'extensions** : l'ordre d'execution et les kwargs attendus par chaque hook ne sont pas documentes dans un schema formel.
2. **Interactions PRISM** : `consensus_integration.py` vs `consensus_arbiter.py` vs `engine.py` — trois chemins de code pour le consensus, aux frontieres floues.
3. **Routage** : `router/policy.py` contient de grandes tables de mots-cles dont la calibration est implicite.
4. **MCP** : `mcp_config.json` utilise des chemins absolus machine-specifiques ; `mcp_config.production.json` est le seul portable.

### Zones opaques

1. **`helpers/` est un fourre-tout** — 181 fichiers, ~77 155 lignes, pas de sous-structure systematique.
2. **Dual Docker** : `deploy/Dockerfile.backend` (production) vs `DockerfileLocal` + `docker/` (dev, base Kali) — deux histoires paralleles non reconciliees.
3. **Donnees runtime** : `data/`, `memory/`, `tmp/` sont des `.gitkeep` vides dans git mais contiennent des donnees critiques en production (index legal, embeddings, chats).

---

## 5. Infrastructure de deploiement

```
                    Internet
                       │
                   ┌───┴───┐
                   │ Caddy  │ ← TLS, reverse proxy
                   │  :443  │
                   └───┬───┘
                       │
          ┌────────────┼────────────┐
          │            │            │
    ┌─────┴─────┐ ┌───┴────┐ ┌────┴────┐
    │ evidence  │ │ evidence│ │  samba  │
    │ -backend  │ │ -demo   │ │  :445   │
    │  :5050    │ │  :5050  │ └─────────┘
    └───────────┘ └────────┘
          │
    ┌─────┴─────┐
    │  Volumes  │
    │  Docker   │
    │ (data,    │
    │  keys,    │
    │  audit)   │
    └───────────┘
```

**Points d'attention** :
- Le port 5050 n'est PAS publie sur l'hote par defaut (Caddy proxy)
- Les scripts `install.sh`/`upgrade.sh` utilisent `127.0.0.1:5050` pour le health check — incoherent avec la config par defaut
- Pas de build Docker en CI — l'image est construite directement sur le serveur
- Pas de monitoring/alerting integre au repo (pas de Prometheus, Grafana, Sentry)
