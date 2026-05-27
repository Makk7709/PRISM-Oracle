<!-- markdownlint-disable MD060 MD032 MD029 MD014 MD013 MD040 MD036 MD034 MD031 MD022 -->

# Documentation Technique Standardisee — KOREV Evidence

## 1. Identification du projet

- **Nom du projet** : KOREV Evidence (repository `PRISM-Oracle`, branche `diag-grow/transmission-evidence`).
- **Type de projet** : plateforme multi-agents d'IA appliquee aux professions reglementees, fondee sur un fork du framework Agent Zero (MIT) avec ajouts proprietaires.
- **Domaine d'application** : declare dans le README — juridique, medical, finance, strategie, cybersecurite. Le code observe confirme la presence de profils agents dedies a ces domaines (cf. section 6).
- **Statut observe** : produit en developpement actif, livre sous forme d'image Docker via `deploy/docker-compose.yml`, comportant un fichier `VERSION.json` indiquant `Evidence v1.3.0` (commit reference `d674d01a`, 26 avril 2026). HEAD courant audite : `641b2c44` (20 mai 2026).
- **Langage principal** : Python 3.11 (cf. `.github/workflows/main_gate.yml`, `PYTHON_VERSION: '3.11'`).
- **Frameworks principaux** :
  - Flask 3.0.3 (Web, cf. `requirements.txt` et `run_ui.py`).
  - LiteLLM (abstraction multi-LLM, installation dans `docker/run/Dockerfile`, commentaire ligne 16 de `requirements.txt`).
  - LangChain core 0.3.49 + community 0.3.19 (`requirements.txt`).
  - sentence-transformers 3.0.1, faiss-cpu 1.11.0 (embeddings + vector search).
  - Pydantic 2.11.7 (contrats de donnees).
  - MCP 1.13.1 + fastmcp 2.3.4 (Model Context Protocol).
  - Playwright 1.52.0, browser-use 0.5.11 (automatisation navigateur).
  - PostgreSQL via Docker Compose (`deploy/docker-compose.yml`, service `evidence-postgres`).
  - Caddy (TLS, reverse proxy, service `evidence-caddy`).
  - Samba (partages multi-utilisateurs, service `evidence-samba`).
  - ReportLab, pypdf, pdfplumber, weasyprint (generation et extraction PDF).
  - Pytesseract, pdf2image (OCR).
- **Date de generation** : 20 mai 2026.
- **Perimetre audite** : branche `diag-grow/transmission-evidence`, HEAD `641b2c44`. Lecture directe de :
  - `agents/`, `agent.py`, `run_ui.py`, `models.py`, `initialize.py`, `preload.py`.
  - `python/api/` (72 endpoints REST observes), `python/helpers/` (~149 modules), `python/extensions/` (24 dossiers), `python/security/`, `python/observability/`, `python/legal_sources/`, `python/tools/`.
  - `prompts/`, `tests/`, `mcp_servers/`, `deploy/`, `docker/`, `legal/`.
  - `.github/workflows/` (3 fichiers CI).
  - `docs/`, `docs/adr/` (7 ADR).

Les volumes hors perimetre (donnees runtime, `memory/`, `logs/`, `tmp/`, `__pycache__/`, `venv/`) n'ont pas ete audites.

---

## 2. Resume executif

KOREV Evidence est une plateforme Python/Flask multi-agents construite par fork du framework open-source Agent Zero (MIT). Le projet a ajoute une couche proprietaire substantielle visant a securiser, controler et tracer les decisions d'agents specialises (juridique, medical, financier, recherche, etc.) destines a des professions reglementees.

Le code observe est structure autour de trois axes techniques :

1. **Une couche de delegation et d'orchestration** entre un agent principal et des agents subordonnes specialises, implementee dans `python/tools/call_subordinate.py` et controlee par un router determinste optionnel (`python/helpers/router/`) et un router de criticite (`python/helpers/criticality_router.py`).
2. **Une couche de validation par consensus** (debat collaboratif a trois LLMs, trois rounds, dans `python/helpers/collaborative_consensus.py`) avec une variante "pipeline adversarial" qui peut court-circuiter le debat legacy si elle a deja effectue sa propre validation.
3. **Une couche operationnelle** comprenant un serveur Flask, ~72 endpoints REST, une persistance Postgres + pgvector annoncee (ADR-007), un proxy TLS Caddy, des partages Samba multi-utilisateurs, et trois serveurs MCP integres (OpenAlex, PubMed, SemanticScholar).

Le projet est documente sur ~865 fichiers Markdown (incluant ADR, audits internes, rapports de valorisation, manuels d'installation, presentations). 170 fichiers de tests sont presents dans `tests/`, organises en sous-dossiers e2e / integration / property / golden / security / regression / harness. Un README revendique 3 846 cas de tests collectes par pytest ; ce chiffre n'a pas ete re-execute dans le present audit.

**Points techniques saillants observes** :

- Architecture multi-agents avec budget guard partage (`python/helpers/execution_budget.py`) anti-cascade.
- Couche de securite explicite : authentification Argon2id, rate limiting, RBAC, anti-injection (`python/security/`).
- 7 ADR (Architecture Decision Records) documentes (`docs/adr/`).
- 3 workflows CI GitHub (`legal_pipeline_ci.yml`, `main_gate.yml`, `security_ci.yml`).
- Annexe d'audit licence `pip-licenses` 2026-05-15 livree dans `docs/annexes-externes/AE-11_*`.

**Reserves**:

- Plusieurs fonctionnalites dependent de variables d'environnement non confirmees en production (`DETERMINISTIC_ROUTER_V2`, `EVIDENCE_MAX_*`, `reasoning_pipeline_enabled`). Voir section 12.
- La portion de code heritee d'Agent Zero (MIT) doit etre distinguee de la valeur proprietaire. Inventaire detaille disponible dans `docs/valuation/02_AGENT_ZERO_DELTA.md` (hors perimetre du present document).
- Le terme "PRISM" apparait dans les docstrings du code mais ne designe pas une implementation unique : il est utilise collectivement pour referencer un ensemble de modules de consensus.

---

## 3. Perimetre fonctionnel constate

Liste des fonctionnalites visibles par observation directe du code et de la documentation embarquee. Aucune fonctionnalite revendiquee a ete inferee.

| Fonctionnalite | Statut observe | Fichiers / modules concernes | Commentaire |
|---|---|---|---|
| Authentification utilisateur (login/logout/session) | Implemente | `run_ui.py` (routes `/login`, `/logout`), `python/security/auth.py`, `python/helpers/user_manager.py` | Hash Argon2id, cf. `deploy/users.json.example`. |
| Multi-utilisateur avec workspaces dedies | Implemente | `python/security/authorization.py`, `deploy/docker-compose.yml` service `evidence-samba` | Volumes Samba par utilisateur (`/shared/users/<username>`). |
| Healthchecks et metriques | Implemente | `python/helpers/health_endpoints.py` (routes `/healthz`, `/readyz`, `/metrics`), `python/api/health.py`, `python/api/observability_metrics.py` | Endpoints Flask exposes. |
| Delegation a des agents specialises | Implemente | `python/tools/call_subordinate.py` (classe `Delegation`) | 11 profils dans `agents/` (cf. section 6). |
| Router determinste anti-injection | Implemente, feature-flagged | `python/helpers/router/` (5 modules), activation via `DETERMINISTIC_ROUTER_V2=1\|2\|3` | Etat de production non confirme par le repo. |
| Criticality routing | Implemente | `python/helpers/criticality_router.py` (`CONSENSUS_REQUIRED_PROFILES`, `LEVEL1_SIMPLE_PATTERNS`, `LEVEL3_CRITICAL_PATTERNS`) | Decide si consensus requis. |
| Consensus collaboratif a trois LLMs | Implemente | `python/helpers/collaborative_consensus.py` (`run_collaborative_consensus`) | Trois rounds, 60 s max. |
| Pipeline adversarial (alternative au consensus legacy) | Implemente | `python/helpers/adversarial_consensus_integration.py`, `python/api/adversarial_*.py` (4 endpoints), `python/extensions/legal_safe_mode/_10_legal_safe_integration.py` | Bypass via flag `_adversarial_dossier_id`. |
| Pipeline juridique (Legal-Safe Mode) | Implemente | `python/helpers/legal_*.py` (10+ fichiers, ~12 000 LOC), `python/extensions/legal_safe_mode/`, `python/legal_sources/` | Pipeline d'ingestion + redaction + verification. |
| Pipeline strategique | Implemente | `python/helpers/strategic_*.py`, `python/extensions/strategic_validation/` | Validation strategique structuree. |
| Pipeline medical (agent specialise) | Implemente | `agents/medical/` (avec `extensions/`, `tools/`, `demos/`), `python/helpers/medical_contract.py` | Profil medical avec contrats specifiques. |
| Generation de rapports / PDF | Implemente | `python/helpers/pdf_generator.py`, `python/helpers/evidence_pdf_engine.py`, `python/helpers/reporting/evidence_native.py`, `python/api/export_strategic_pdf.py` | ReportLab + WeasyPrint. |
| OCR sur documents | Implemente | `python/tools/pdf_ocr.py`, dependances `pytesseract`, `pdf2image` | Image OCR via Tesseract. |
| Document Q&A et extraction | Implemente | `python/tools/document_query.py`, `python/helpers/document_query.py` | Pipeline RAG sur documents. |
| Knowledge base et indexation | Implemente | `python/api/import_knowledge.py`, `python/api/knowledge_reindex.py`, `knowledge/` | Indexation et recherche. |
| Memory consolidation | Implemente | `python/helpers/memory_consolidation.py`, `python/helpers/memory.py`, endpoints `memory_*` | Persistance memoire d'agents. |
| Backup et restore | Implemente | `python/api/backup_*.py` (8 endpoints), `python/helpers/backup.py` | Sauvegarde et restoration. |
| Scheduler de taches | Implemente | `python/helpers/task_scheduler.py`, `python/api/scheduler_*.py` (5 endpoints) | Planification de taches. |
| Notifications | Implemente | `python/api/notification_*.py` (4 endpoints), `python/helpers/notification_*.py` | Systeme de notifications. |
| Chat management (create / load / export / reset / rename) | Implemente | `python/api/chat_*.py` (8 endpoints) | Gestion de conversations. |
| MCP integration | Implemente | `mcp_servers/openalex/`, `mcp_servers/pubmed/`, `mcp_servers/semanticscholar/`, `python/helpers/mcp_handler.py` | Trois serveurs MCP integres. |
| Risk dashboard et register | Implemente | `python/helpers/dynamic_risk_register.py`, `python/api/risk_dashboard.py`, `python/extensions/monologue_end/_36_risk_assessment.py` | Suivi dynamique des risques. |
| Audit reports | Implemente | `python/api/audit_reports.py`, `python/helpers/audit_report_renderer.py` | Generation de rapports d'audit. |
| Human review workflow | Implemente | `python/api/human_review.py`, `python/helpers/human_review*.py` | Escalade humaine. |
| Replay engine | Implemente | `python/api/replay.py`, `python/helpers/replay_*.py` | Re-execution de scenarios. |
| TTS et transcription audio | Implemente | `python/api/synthesize.py`, `python/api/transcribe.py`, deps `kokoro`, `openai-whisper` | Fonctionnalite optionnelle. |
| Tunnel external (cloudflared / flaredantic) | Implemente | `python/api/tunnel.py`, `python/api/tunnel_proxy.py`, `run_tunnel.py`, dep `flaredantic` | Expose le service sans IP publique. |
| Browser automation | Implemente | `python/tools/browser_agent.py`, deps `playwright`, `browser-use` | Agent navigateur. |
| Search engine | Implemente | `python/tools/search_engine.py`, dep `duckduckgo-search` | Recherche web. |
| Image generation | Implemente | `python/tools/generate_image.py` | Generation d'images. |
| Code execution sandboxe | Implemente | `python/tools/code_execution_tool.py` | Execution de code dans un sous-process. |
| File reader / writer | Implemente | `python/tools/file_reader.py`, `python/tools/file_writer.py` | Lecture/ecriture de fichiers. |

---

## 4. Architecture technique

### 4.1 Vue d'ensemble

Architecture monolithique Python/Flask multi-services en Docker Compose. Le code applicatif principal vit dans un conteneur backend ; un conteneur frontend distinct (`Dockerfile.frontend`) sert l'interface ; un Postgres conteneurise stocke les donnees structurees ; un Caddy fait office de reverse proxy avec TLS automatique ; Samba expose des partages utilisateur.

### 4.2 Schema textuel (deduit de `deploy/docker-compose.yml` et du code)

```text
              Internet
                 |
         +---------------+
         |  Caddy (TLS)  |   evidence-caddy
         +---------------+
              |
       +------+---------+
       |                |
       v                v
+----------------+  +----------------+
| Flask backend  |  | Static frontend|
| evidence-      |  | webui/         |
| backend        |  +----------------+
| (run_ui.py)    |
+----------------+
       |                 +------------------------+
       | PG conn         | Volumes Docker         |
       v                 |                        |
+----------------+       |  evidence-data         |
| Postgres       |       |  evidence-logs         |
| evidence-      |       |  evidence-audit        |
| postgres       |       |  evidence-shared       |
+----------------+       |  evidence-tmp          |
                         |  evidence-memory       |
                         +------------------------+
       |
       v
+----------------+      +---------------------+
| Samba          |      | MCP servers         |
| evidence-      |      | OpenAlex, PubMed,   |
| samba          |      | SemanticScholar     |
+----------------+      +---------------------+
                                |
                                v
                        +---------------------+
                        | LLM providers       |
                        | (via litellm)       |
                        +---------------------+
```

### 4.3 Backend

- Application Flask 3.0.3 (`run_ui.py` ~1 fichier d'environ 20 KB) exposant ~75 endpoints REST repartis dans `python/api/` (1 fichier par endpoint, soit 72 fichiers Python).
- Routes publiques minimales (`/login`, `/logout`, `/healthz`, `/`) declarees dans `run_ui.py`. Le reste des endpoints est enregistre dynamiquement.
- `python/helpers/` contient ~149 modules de logique metier (orchestration, consensus, legal pipeline, strategic pipeline, evidence_document, reporting, observability, etc.).
- `python/extensions/` contient 24 dossiers d'extensions du cycle de vie d'agent (hooks `agent_init`, `monologue_start`, `tool_execute_before`, `response_stream`, etc.) — pattern herite d'Agent Zero, etendu par les ajouts proprietaires.
- Modele LLM : `models.py` (~7 KB) plus `python/helpers/models_*.py`, abstraction via LiteLLM.

### 4.4 Frontend

- Repertoire `webui/` contenant HTML/CSS/JS (pas de framework JS observe : pas de `package.json` ni `node_modules` versionnes dans le repo). Composants vanilla et templates legers.
- Fichiers `index.html`, `login.html`, `index.css`, `index.js`, sous-dossiers `components/`, `i18n/`, `js/`, `css/`, `vendor/`.
- Build : non documente comme processus de build separe ; servi directement par Flask ou par le conteneur frontend.

### 4.5 Base de donnees

- PostgreSQL conteneurise (service `evidence-postgres` dans `deploy/docker-compose.yml`).
- ADR-007 (`docs/adr/ADR-007-postgres-pgvector-adoption.md`) documente une migration vers Postgres + pgvector. Etat reel de l'adoption non re-verifie dans le present audit.
- Code de connexion : `python/helpers/database.py`, `python/helpers/db_connection.py` (presents dans `python/helpers/`).
- Avant cette migration, plusieurs composants utilisent un stockage filesystem (`memory/`, `data/`, `logs/`).

### 4.6 APIs et endpoints

- 72 endpoints REST dans `python/api/` (un fichier par endpoint).
- Pattern : chaque endpoint expose une classe ou fonction, enregistree dynamiquement par le framework hérité d'Agent Zero.
- Endpoints sensibles (administratifs) proteges par session et RBAC (`python/security/authorization.py`).

### 4.7 Services internes / pipelines

- **Pipeline Legal-Safe** : `python/helpers/legal_orchestrator.py` (~77 KB), `python/helpers/legal_pipeline.py`, `python/extensions/legal_safe_mode/` (10 extensions), `python/legal_sources/` (fetchers, indexing, audit_bundle).
- **Pipeline Strategique** : `python/helpers/strategic_orchestrator.py`, `strategic_pipeline.py`, `strategic_charts.py`, `strategic_contract.py`.
- **Reasoning Engine** : `python/helpers/reasoning_engine.py` (~41 KB), `metacognition.py` (~39 KB).
- **Consensus** : `python/helpers/collaborative_consensus.py`, `consensus_manager.py`, `consensus_arbiter.py`, `consensus_contracts.py`, `adversarial_consensus_integration.py`, `research_consensus_integration.py`.

### 4.8 Agents IA

- 11 profils agents fonctionnels + 1 gabarit `_example` (cf. section 6 pour detail).
- Architecture multi-agents avec delegation hierarchique (`Agent.number` incremente a chaque niveau, lien `DATA_NAME_SUPERIOR` / `DATA_NAME_SUBORDINATE`, cf. `agent.py:368-369`).
- Budget guard partage entre superieur et subordonne (`python/helpers/execution_budget.py`).

### 4.9 Stockage

- Volumes Docker persistants : `evidence-data`, `evidence-logs`, `evidence-audit`, `evidence-shared`, `evidence-tmp`, `evidence-memory`, `evidence-postgres-data`.
- Filesystem-first sur certains composants (memoire, knowledge), avec une migration vers RDBMS planifiee (ADR-007).

### 4.10 Authentification et autorisation

- `python/security/auth.py` (Argon2id via `argon2-cffi`).
- `python/security/authorization.py` (RBAC).
- `python/security/rate_limit/` (sous-package, rate limiting Redis ou memoire).
- `python/security/ip.py` (IP filtering).
- `python/security/path_safety.py` (anti-traversal).
- `python/security/upload_validation.py`.
- `python/security/shell_safety.py`.
- `python/security/security_audit.py` (audit log).

### 4.11 Deploiement

- `deploy/docker-compose.yml` (orchestre 20 services et volumes).
- `deploy/Dockerfile.backend` et `deploy/Dockerfile.frontend`.
- `DockerfileLocal` pour developpement local.
- `docker/base/`, `docker/run/` pour la stratification d'images.
- Documentation `docs/GUIDE_DEPLOIEMENT_ENTREPRISE.md`, `docs/MANUEL_INSTALLATION_CLIENT.md`, `docs/INFRA_SERVEUR_OVH.md`.
- `deploy/RUNBOOK.md` documente la procedure operationnelle.

### 4.12 Dependances externes

61 dependances directes dans `requirements.txt`, 2 dans `requirements.dev.txt`. Inventaire complet et classification licence dans `docs/annexes-externes/AE-11_pip-licenses_2026-05-15.md`.

---

## 5. Structure du depot

Volumetrie globale (mesuree par `find ... | wc -l` et `wc -l`) :

- 613 fichiers Python (hors `venv/`, `__pycache__/`, `node_modules/`).
- 191 467 lignes Python totales (incluant docstrings et commentaires).
- 865 fichiers Markdown (incluant documentation, README, guides, ADR, rapports).
- 170 fichiers `test_*.py` dans `tests/`.
- 7 ADR dans `docs/adr/`.
- 3 workflows CI dans `.github/workflows/`.

| Chemin | Role identifie | Importance |
|---|---|---|
| `agent.py` | Classe principale `Agent`, `AgentContext`, `AgentConfig`, gestion du monologue | Critique |
| `run_ui.py` | Application Flask, login, sessions, healthz | Critique |
| `initialize.py`, `preload.py`, `prepare.py` | Bootstrap de l'application | Critique |
| `models.py` | Abstraction des modeles LLM | Critique |
| `agents/` | 11 profils agents + 1 gabarit | Critique |
| `python/api/` | 72 endpoints REST | Critique |
| `python/helpers/` | ~149 modules metier (orchestrateurs, consensus, legal, strategic, evidence, reporting) | Critique |
| `python/extensions/` | 24 dossiers d'extensions du cycle de vie d'agent | Eleve |
| `python/security/` | Authentification, autorisation, rate limiting, validations | Critique |
| `python/observability/` | Runtime metrics | Eleve |
| `python/legal_sources/` | Ingestion Legifrance, Judilibre, CNIL ; FTS5 | Eleve |
| `python/tools/` | ~30 outils utilisables par les agents (`call_subordinate`, `document_query`, `pdf_ocr`, `browser_agent`, etc.) | Critique |
| `prompts/` | Prompts systeme et utilitaires des agents | Eleve |
| `tests/` | 170 fichiers de tests (e2e, integration, golden, security, property, regression) | Critique |
| `mcp_servers/openalex/`, `mcp_servers/pubmed/`, `mcp_servers/semanticscholar/` | Serveurs MCP integres | Eleve |
| `deploy/` | Docker Compose, Dockerfiles, postgres init, scripts | Critique |
| `docker/`, `DockerfileLocal` | Images Docker base et runtime | Critique |
| `webui/` | Frontend HTML/CSS/JS | Eleve |
| `knowledge/` | Base de connaissances | Eleve |
| `memory/`, `data/`, `logs/`, `tmp/` | Donnees runtime (hors perimetre audit) | Operationnel |
| `docs/` | 865 fichiers documentaires (manuels, ADR, audits, presentations) | Eleve |
| `docs/adr/` | 7 Architecture Decision Records | Eleve |
| `docs/annexes-externes/` | Annexe AE-11 (audit licence) | Eleve |
| `docs/architecture/` | Schema architecture verifiee de la delegation | Eleve |
| `legal/` | LICENSE, THIRD_PARTY_NOTICES, KOREV_LICENSE | Eleve |
| `.github/workflows/` | 3 workflows CI (legal_pipeline, main_gate, security_ci) | Eleve |
| `scripts/` | Scripts d'administration et de provisioning | Modere |
| `instruments/`, `lib/`, `fonts/`, `usr/` | Ressources auxiliaires | Modere |
| `test_*.py` (racine) | 4 scripts de test orphelins (`test_adversarial_*.py`, `test_consensus_simple.py`) | A clarifier (cf. section 12) |
| `requirements*.txt` | Dependances (61 + 2 dev) | Critique |
| `pytest.ini`, `Makefile`, `cspell.json`, `jsconfig.json` | Configuration outillage | Modere |
| `LICENSE`, `SECURITY.md`, `README.md`, `VERSION.json` | Metadata projet | Eleve |
| `KOREV-Evidence.pdf` | Plaquette commerciale (artefact non technique) | Faible |

---

## 6. Modules proprietaires identifies

Le projet est explicitement issu d'un fork du framework Agent Zero (MIT). Le perimetre proprietaire est documente en detail dans `docs/valuation/02_AGENT_ZERO_DELTA.md` et `docs/valuation/03_EVIDENCE_PROPRIETARY_MODULES.md`. Le tableau ci-dessous reprend uniquement les modules dont la presence dans le code et l'absence de l'upstream Agent Zero peuvent etre directement constatees a la lecture des fichiers.

| Module | Role | Niveau de specificite | Elements valorisables | Reserve |
|---|---|---|---|---|
| Profils agents specialises (`agents/legal_safe/`, `agents/medical/`, `agents/legal_drafting_guarded/`, `agents/finance/`, `agents/researcher/`, `agents/sales/`, `agents/marketing/`, `agents/multitask/`) | Personnalisation par domaine metier (prompts, extensions, tools, contrats) | Eleve | Prompts metiers, contrats specialises (`medical_contract.py`, `legal_agent_contracts.py`), demos | Le profil de base `default` est herite d'Agent Zero. Les ajouts metier sont proprietaires. |
| Router determinste anti-injection (`python/helpers/router/`, 5 modules, ~115 KB) | Routage policy-driven, detection injection, classification d'intents, board-level triggers | Eleve | Policy de patterns, contrats `RouteDecision`, metriques | Activation feature-flagged (`DETERMINISTIC_ROUTER_V2`) ; etat de production non confirme. |
| Criticality router (`python/helpers/criticality_router.py`, ~50 KB) | Decide si consensus est requis selon profil, domaine, niveau de criticite | Eleve | Logique de Level 1/2/3, `CONSENSUS_REQUIRED_PROFILES`, `LEVEL3_CRITICAL_PATTERNS` | — |
| Consensus collaboratif (`python/helpers/collaborative_consensus.py`, ~40 KB) | Debat structure a trois LLMs en trois rounds | Eleve | Architecture de debat, `DebateVerdict`, badges de validation, fail-closed | Necessite trois fournisseurs LLM configures. |
| Pipeline adversarial (`python/helpers/adversarial_*.py`, `python/api/adversarial_*.py`) | Alternative au consensus legacy avec dossier d'analyse | Eleve | Dossier d'analyse, decision, list, endpoints REST | Bypass declaratif via flag (cf. section 12). |
| Pipeline Legal-Safe (`python/helpers/legal_*.py`, `python/extensions/legal_safe_mode/`, `python/legal_sources/`, `contract_drafting/`) | Ingestion sources legales, indexation FTS5, contract drafting, mode safe | Eleve | ~12 000 LOC dedies, fetchers Legifrance/Judilibre/CNIL, audit bundle | Effort de developpement metier specifique. |
| Pipeline strategique (`python/helpers/strategic_*.py`, `python/extensions/strategic_validation/`) | Validation strategique structuree, enrichissement route | Eleve | Contracts pydantic, charts, orchestrator | — |
| Reasoning engine + metacognition (`python/helpers/reasoning_engine.py`, `metacognition.py`) | Couche de raisonnement, auto-evaluation, escalade non-diluable (SAFE_REFUSE / HUMAN_REVIEW / ASK_CLARIFY / NONE) | Eleve | ~80 KB cumule, escalade structuree | Comportement no-PII par design ; non re-execute runtime ici. |
| Evidence framework (`python/helpers/evidence_document/`, `python/helpers/reporting/evidence_native.py`) | Generation de rapports auditables, integrite cryptographique annoncee | Eleve | Templates, renderer, native reporting | Modules d'integrite a verifier dans une mission dediee. |
| PDF / OCR engine (`python/helpers/evidence_pdf_engine.py`, `python/helpers/pdf_generator.py`, `python/tools/pdf_ocr.py`) | Generation PDF (ReportLab + WeasyPrint), OCR (Tesseract via pdf2image) | Modere a Eleve | Circuit breakers et timeouts si presents (a verifier) | Couche metier substantielle. |
| Multi-tenant security (`python/security/`, `python/helpers/user_manager.py`, `deploy_config.py`) | Argon2id, RBAC, rate limiting, IP filtering, path safety, upload validation, audit log | Eleve | 9 sous-modules security, Redis/memoire rate limiting | Cf. SECURITY.md. |
| Audit-proof workflow (`python/helpers/replay_*.py`, `python/api/replay.py`, `human_review*.py`, `dynamic_risk_register.py`) | Replay engine, human review, risk register dynamique | Eleve | Endpoints REST + helpers | — |
| MCP servers integres (`mcp_servers/openalex/`, `mcp_servers/pubmed/`, `mcp_servers/semanticscholar/`) | Adaptateurs MCP vers bases scientifiques publiques | Modere | Code adapter local | OpenAlex et SemanticScholar embarquent leur propre LICENSE (a verifier pour conformite). |
| Suite de tests TDD industrielle (`tests/`) | 170 fichiers de tests, 9 sous-categories | Eleve | ~30 000 LOC tests d'apres `docs/valuation/03_*` (non re-verifie ici) | Non re-execute dans cette mission. |

Reserve generale : la distinction proprietaire vs herite Agent Zero doit s'appuyer sur l'inventaire detaille de `docs/valuation/02_AGENT_ZERO_DELTA.md` et sur les verifications `git diff <fork>..HEAD`. Le present document constate uniquement la presence et la localisation des modules.

---

## 7. Dependances et composants externes

Source principale : `requirements.txt` (61 dependances directes), `docs/annexes-externes/AE-11_pip-licenses_2026-05-15.md` (scan complet du venv).

| Dependance | Usage observe | Criticite | Risque associe |
|---|---|---|---|
| Flask 3.0.3 | Serveur web et routing | Critique | Faible (BSD-3-Clause). |
| LiteLLM (installation Dockerfile) | Abstraction multi-LLM | Critique | Dependance externe rapide a changer en cas de probleme upstream. |
| LangChain core 0.3.49 + community 0.3.19 | Composants RAG, chains, prompts | Eleve | Versions epinglees ; vigilance sur les CVE LangChain frequentes. |
| sentence-transformers 3.0.1 | Embeddings | Eleve | Faible (Apache 2.0). |
| faiss-cpu 1.11.0 | Vector store | Eleve | Faible (MIT). |
| Pydantic 2.11.7 | Contrats de donnees | Critique | Faible (MIT). |
| MCP 1.13.1 + fastmcp 2.3.4 + fasta2a 0.5.0 | Model Context Protocol | Eleve | Specification recente, evolution possible. |
| browser-use 0.5.11 + playwright 1.52.0 | Automatisation navigateur | Modere | Surface d'attaque significative, sandboxing requis. |
| docker 7.1.0 | Controle de conteneurs depuis Python | Modere | Necessite acces socket Docker. |
| psutil >=7.0.0 | Monitoring process | Modere | — |
| paramiko 3.5.0 | SSH client | Modere | LGPL (compatible commercial par linkage Python). |
| crontab 1.0.1 | Tasks scheduling | Modere | LGPL. |
| pypdf 6.0.0 + pdfplumber >=0.11.0 + pikepdf 10.2.0 | Manipulation PDF | Modere | pikepdf est sous MPL 2.0. |
| pytesseract 0.3.13 + pdf2image 1.17.0 | OCR | Modere | Necessite Tesseract installe (image Docker). |
| reportlab >=4.0.0 + weasyprint 68.1 | Generation PDF | Modere | weasyprint depend de pyphen (triple licence GPL/LGPL/MPL 1.1, utilise sous MPL 1.1). |
| openai-whisper 20250625 + kokoro >=0.9.2 + espeakng-loader 0.2.4 | Transcription et TTS | Faible (optionnel) | `espeakng-loader` charge dynamiquement la librairie eSpeak NG (GPL v3+). Cf. AE-11. |
| argon2-cffi >=23.1.0 | Hash de mots de passe | Critique | Faible (MIT). |
| redis >=5.0.0 | Rate limiting multi-worker | Eleve | Dependance externe runtime (service `evidence-redis` non explicitement liste dans `docker-compose.yml`, mais le code prevoit fallback memoire). |
| GitPython 3.1.43 | Operations Git internes | Modere | — |
| duckduckgo-search 6.1.12 | Recherche web | Modere | Service externe non controle ; gerer les changements API. |
| newspaper3k 0.2.8 | Extraction d'article | Modere | Maintenu de facon irreguliere. |
| unstructured \[all-docs\] 0.16.23 + langchain-unstructured | Extraction multi-format | Eleve | Tres large dependance ; surveiller maintenance. |
| flaredantic 0.1.4 | Tunnel external | Modere | Dependance jeune. |
| Postgres + Caddy + Samba | Services Docker | Critique | Bonnes pratiques operationnelles standards. |

Synthese licence (cf. AE-11) :

- 0 package GPL pur, 0 AGPL, 0 SSPL en dependances directes ou transitives.
- 5 LGPL, 5 MPL 2.0 compatibles commercial sous reserve de linkage dynamique et de non-modification.
- 1 cas isolable (`espeakng-loader`) chargeant une librairie GPL native ; hors perimetre valorisable.

---

## 8. Donnees, securite et conformite

### 8.1 Gestion des secrets

- Variables d'environnement chargees via `python-dotenv 1.1.0` (cf. `requirements.txt`).
- Fichier `.env` non versionne (verification par `.gitignore` indirecte).
- Fichier d'exemple `deploy/users.json.example` sanitise (verification mission 15 mai 2026, cf. `docs/valuation/10_FINAL_TRANSMISSION_CHECKLIST.md`).
- Pas de secret exploitable identifie sur les fichiers trackes apres la mission anti-secrets J-0 (cf. `docs/valuation/11_FACTUAL_INTEGRITY_AUDIT.md` section 7).

### 8.2 Authentification

- Hash de mots de passe Argon2id (`python/security/auth.py`, dependance `argon2-cffi`).
- Session Flask avec secret key (cf. `run_ui.py`).
- Mode multi-utilisateur via `deploy/users.json` (`python/helpers/user_manager.py`).
- Rejet documente des mots de passe en clair en production (cf. `docs/SPEC_MULTI_USER_WORKSPACE.md` regle R1).

### 8.3 Autorisations

- RBAC par roles `user` / `admin` (cf. `docs/SPEC_MULTI_USER_WORKSPACE.md`).
- Module `python/security/authorization.py` (autorisation par ressource).
- Isolation par tenant via `python/helpers/user_manager.py` et workspaces dedies.

### 8.4 Logs

- Audit log dans `python/security/security_audit.py`.
- Logs structures (annonce dans `docs/valuation/02_AGENT_ZERO_DELTA.md`).
- Observability metrics : `python/observability/runtime.py`, endpoint `/metrics` (`python/api/observability_metrics.py`).
- Volumes Docker dedies : `evidence-logs`, `evidence-audit`.

### 8.5 Donnees personnelles

- Documentation interne fait reference a une politique no-PII par design dans les escalades du reasoning engine (`docs/valuation/03_EVIDENCE_PROPRIETARY_MODULES.md`).
- Verification automatique runtime non observee dans la presente mission.
- Mention RGPD dans des documents internes (manuel installation, demonstration cabinet avocats). Aucun document n'engage la conformite a un standard externe certifie.

### 8.6 Chiffrement

- TLS termine par Caddy (configuration automatique selon documentation Caddy ; cf. service `evidence-caddy` dans `docker-compose.yml`).
- Chiffrement at-rest non observe explicitement dans le code (depend de l'infrastructure du deploiement).

### 8.7 Auditabilite

- Replay engine (`python/helpers/replay_*.py`, endpoint `/replay`).
- Audit reports (`python/helpers/audit_report_renderer.py`).
- Audit bundle juridique (`python/legal_sources/audit_bundle.py`).
- Pipeline adversarial avec `dossier_id` trackable.

### 8.8 Conformite AI Act / RGPD

Le projet revendique dans `docs/valuation/02_AGENT_ZERO_DELTA.md` un "alignement architectural avec exigences AI Act et RGPD (auto-evalue, sans certification externe)". Le present audit confirme la presence de :

- escalades non-diluables documentees ;
- audit log centralise ;
- workflow de human review ;
- registre de risques dynamique.

Aucune certification externe AI Act ou RGPD n'est documentee. Toute affirmation de conformite doit etre rattachee a un audit externe a venir.

### 8.9 Mention SECURITY.md

Un fichier `SECURITY.md` est present a la racine. Son contenu n'a pas ete examine ligne par ligne dans le present audit.

---

## 9. Tests, qualite et maintenabilite

### 9.1 Tests presents

- 170 fichiers `test_*.py` dans `tests/`.
- 9 sous-dossiers structurels : `e2e/`, `integration/`, `golden/`, `security/`, `property/`, `regression/`, `harness/`, `chat_personalization/`, `infra/`, `fixtures/`.
- Markers pytest declares dans `pytest.ini` : `fast`, `integration`, `e2e`, `property`, `security`, `slow`, `redis`.
- Conftest dedies : `tests/conftest.py`, `tests/conftest_pdf.py`.
- Le README annonce 3 846 cas collectes ; le present audit n'a pas re-execute `pytest --collect-only` (cf. section 12).

### 9.2 Tests orphelins racine

4 fichiers `test_*.py` situes a la racine du repo (non sous `tests/`) :

- `test_adversarial_e2e_scenarios.py`
- `test_adversarial_instruction.py`
- `test_adversarial_integration.py`
- `test_consensus_simple.py`

Leur statut (deplace, draft, integre au gate CI ?) n'est pas clarifie par leur emplacement. A confirmer avec le porteur (cf. section 12).

### 9.3 Qualite structurelle

- Modularisation visible (149 helpers, 24 dossiers d'extensions, 72 endpoints isoles).
- Convention de nommage homogene (`snake_case` Python, `_NN_` pour les hooks d'extensions ordonnes).
- Docstrings substantielles dans les modules audites (`call_subordinate.py`, `criticality_router.py`, `collaborative_consensus.py`, `execution_budget.py`).
- Type hints generalises (`from typing import ...` present partout).

### 9.4 Dette technique visible

- 4 fichiers de tests racine non integres a `tests/`.
- Persistance filesystem-first sur certains composants, migration RDBMS planifiee (ADR-007).
- Commentaires de header en partie obsoletes par rapport au contrat reel (exemple : commentaire `call_subordinate.py:13` annonce 30-40 s pour le debat alors que le contrat est 60 s).
- Drives de submodules dans `mcp_servers/openalex/` et `mcp_servers/semanticscholar/` (signales par `git status`).

### 9.5 Documentation existante

- 865 fichiers Markdown.
- 7 ADR formels dans `docs/adr/`.
- Annexes externes (AE-11 audit licence).
- Guides operationnels : `docs/MANUEL_INSTALLATION_CLIENT.md`, `docs/GUIDE_DEPLOIEMENT_ENTREPRISE.md`, `docs/INFRA_SERVEUR_OVH.md`, `deploy/RUNBOOK.md`.
- Documentation architecture : `docs/architecture/EVIDENCE_DELEGATION_ARCHITECTURE_VERIFIED.md`, `docs/ARCHITECTURE_C4_DIAGRAMS.md`.
- Onboarding : `docs/ONBOARDING_AYA_30_60_90.md`, `docs/DEVELOPER_ONBOARDING_ARCHITECTURE_GUIDE.md`, `docs/PLAN_INTEGRATION_LEAD_ENGINEER_30_60_90_INTERNAL.md`.

### 9.6 CI / CD

3 workflows GitHub Actions :

| Workflow | Declencheur | Perimetre |
|---|---|---|
| `legal_pipeline_ci.yml` | Push / PR sur changements legaux | Tests invariants legal + tests unitaires + nightly E2E |
| `main_gate.yml` | PR sur `main` (tous changements) | Gate principal, regression globale |
| `security_ci.yml` | Push / PR sur changements securite | Security tests + coverage 95% min + multi-worker Redis |

Le repo expose egalement un `Makefile` avec cibles `audit-verify`, `audit-lint`, `audit-smoke` pour declencher localement les controles documentaires.

---

## 10. Niveau de maturite estime

| Axe | Niveau observe | Commentaire |
|---|---|---|
| Fonctionnel | Avance | 11 profils agents specialises, ~30 outils, 72 endpoints REST, pipelines metiers complets (legal, strategic, medical, evidence). |
| Technique | Avance | Architecture multi-couches, hooks d'extensions, contrats pydantic, modularite eleve. Persistance partiellement filesystem-first (en transition vers RDBMS). |
| Securite | Avance | Argon2id, RBAC, rate limiting Redis, anti-injection, audit log, CI dediee securite (95% coverage). Pas de certification externe documentee. |
| Maintenabilite | Intermediaire a avance | Documentation extensive, ADR formels, type hints, separation des responsabilites. Quelques fichiers de tests orphelins, commentaires obsoletes ponctuels. |
| Scalabilite | Intermediaire | Architecture conteneurisee (Docker), Caddy + Postgres + Samba multi-services. Pas de cluster Kubernetes documente. Rate limiting prevu pour multi-worker via Redis. |
| Documentation | Avance | 865 fichiers Markdown, 7 ADR, guides operationnels, audits internes formels, annexes licence. |
| Industrialisation | Intermediaire a avance | CI/CD GitHub Actions, Docker production, runbook deploiement. Pas de monitoring SaaS documente (mention `newrelic_agent.log` sans configuration verifiee). |

Le projet presente un niveau d'industrialisation et de qualite documentaire au-dessus de la moyenne des projets de meme age et de meme taille. Les zones les plus matures sont la securite et la documentation. Les zones a renforcer sont l'observabilite production-grade et la finalisation de la migration RDBMS.

---

## 11. Elements utiles pour valorisation

Cette section liste les **elements observables dans le repo** pouvant soutenir une evaluation technique. Aucune valorisation financiere n'est avancee ici ; le pack dedie est dans `docs/valuation/`.

### 11.1 Volume de code utile

- ~191 000 lignes Python (hors `venv/`, `__pycache__/`).
- ~149 helpers metier dans `python/helpers/`, dont une dizaine au-dessus de 30 KB chacun.
- 72 endpoints REST avec un fichier dedie chacun.
- 170 fichiers de tests structures.

### 11.2 Complexite fonctionnelle

- Pipeline Legal-Safe substantiel (~12 000 LOC d'apres documentation interne, a re-verifier).
- Pipeline strategique avec validation structuree.
- Reasoning engine et metacognition (~80 KB cumule).
- Consensus multi-arbitre.

### 11.3 Differenciation par rapport au framework de base

- Le fork d'Agent Zero introduit 11 profils metier specialises et toute la couche d'evidence / audit / consensus.
- Inventaire detaille dans `docs/valuation/02_AGENT_ZERO_DELTA.md`.

### 11.4 Reutilisabilite

- Architecture modulaire (extensions, profils, tools) permet le branchement de nouveaux domaines metier sans refonte.
- Contrats pydantic publics.
- Abstraction LiteLLM permet de changer de fournisseur LLM sans reecriture du metier.

### 11.5 Profondeur metier

- Profils metier avec prompts, extensions, tools, demos, contrats dedies (`agents/medical/`, `agents/legal_safe/`).
- Sources juridiques publiques integrees (Legifrance, Judilibre, CNIL via `python/legal_sources/fetchers/`).
- Trois serveurs MCP scientifiques (OpenAlex, PubMed, SemanticScholar).

### 11.6 Propriete intellectuelle potentielle

- Logique de routing determinste (`policy.py`, ~30 KB) et de criticite (`criticality_router.py`, ~50 KB) — code metier specifique.
- Pipeline adversarial avec dossiers d'analyse persistents.
- Suite de tests TDD industrielle.

### 11.7 Niveau d'integration

- Tout integre en Docker Compose, prets a deployer (cf. `deploy/docker-compose.yml`).
- TLS automatique via Caddy.
- Multi-utilisateur isole par Samba + RBAC + workspaces.

### 11.8 Actifs documentaires

- 865 fichiers Markdown organises (ADR, guides, audits, onboarding, presentations).
- 7 ADR formels.
- Pack de valorisation interne dans `docs/valuation/`.
- Annexe licence externalisable (AE-11).

### 11.9 Tests

- 170 fichiers organises en 9 categories.
- 3 workflows CI distincts.
- Gate securite avec coverage 95% minimum sur `python/security/`.

### 11.10 Preuves d'usage presentes dans le repo

- `KOREV-Evidence.pdf` (plaquette commerciale).
- `docs/DEMONSTRATION_CABINET_AVOCATS.md` + PDF.
- `docs/MEDICAL_AGENT_HARDENING_REPORT.md` (rapport de hardening medical).
- `docs/preuves-execution/` (traces execution, pytest collect, metriques Git).
- Aucune mention contractuelle client n'a ete extraite dans le present audit.

---

## 12. Limites et points a confirmer

| Point | Pourquoi c'est a confirmer | Impact potentiel |
|---|---|---|
| Etat de production des feature flags (`DETERMINISTIC_ROUTER_V2`, `DETERMINISTIC_ROUTER`, `reasoning_pipeline_enabled`, `EVIDENCE_MAX_*`) | Aucun fichier `.env` ou de production trackant les valeurs runtime n'a ete audite dans cette mission. | Modere — le comportement reel des composants d'audit (router, budget, reasoning) depend de leur activation. |
| Nombre exact de tests collectes par pytest | Le README cite 3 846 ; le present audit n'a pas re-execute `pytest --collect-only`. | Faible — donnee verifiable rapidement, mais a re-mesurer pour transmission externe. |
| Statut des 4 fichiers `test_*.py` a la racine du repo | Position inhabituelle (hors `tests/`), pas integres explicitement aux workflows CI observes. | Modere — peut signaler des drafts ou des tests deconnectes. |
| Etat reel de la migration Postgres + pgvector (ADR-007) | ADR documente une transition ; le code de migration et la couverture de tests RDBMS n'ont pas ete inspectes ligne par ligne. | Modere — gap entre roadmap et execution a verifier. |
| Periodicite et statut des derniers passages CI sur `main` | Le repo expose les workflows mais le present audit n'a pas verifie les runs reels sur GitHub Actions. | Faible — facile a verifier via l'UI GitHub. |
| Couverture de tests reelle hors `python/security/` | Le seuil 95% est annonce uniquement sur `python/security/`. La couverture globale n'est pas declaree. | Modere — a mesurer (commande `pytest --cov`). |
| Distinction precise proprietaire vs herite Agent Zero pour chaque fichier | L'inventaire est dans `docs/valuation/02_AGENT_ZERO_DELTA.md`, mais le present audit ne re-verifie pas fichier par fichier. | Modere — necessaire pour valorisation IP. |
| Conformite NDA des mentions clients (DICA, Tarmac, Centrale Lille) dans les documents internes | Verification documentaire contractuelle externe au perimetre technique (deja signalee dans `docs/valuation/12_EXTERNAL_AUDITOR_READINESS_REPORT.md`, RES-2). | Modere — releve d'une decision du porteur. |
| Robustesse du bypass adversarial (flag `_adversarial_dossier_id`) | Aucun controle d'integrite n'est observe dans `call_subordinate.py:367-381`. Repose sur la confiance interne. | Modere — surface d'emission localisee a un seul fichier dans la branche auditee. |
| Coexistence du terme "PRISM" avec deux implementations distinctes (collaborative legacy + adversarial) | Risque de confusion documentaire ; cf. `docs/architecture/EVIDENCE_DELEGATION_ARCHITECTURE_VERIFIED.md` section 13.2. | Faible a modere — corrige par formulation prudente. |
| Drives de submodules `mcp_servers/openalex/` et `mcp_servers/semanticscholar/` | Marques `M` dans `git status` mais non commites. Pas vu de mise a jour pinning. | Faible — operationnel. |
| Performance reelle des LLMs et timeouts du debat collaboratif | Les contrats annoncent 60 s max ; aucun benchmark runtime n'a ete observe dans cette mission. | Modere — depend de la charge et des fournisseurs. |
| Configuration newrelic ou autre APM | `newrelic_agent.log` present a la racine, configuration non auditee. | Faible — operationnel. |
| Acces socket Docker depuis le conteneur backend | La dependance `docker 7.1.0` suggere une interaction avec le daemon Docker. Surface a auditer. | Modere — implications securite si expose. |

---

## 13. Conclusion technique

KOREV Evidence est une plateforme Python/Flask multi-agents construite par fork du framework Agent Zero (MIT). L'analyse du code observe sur la branche `diag-grow/transmission-evidence` au HEAD `641b2c44` montre une base technique substantielle : ~191 000 lignes Python, 11 profils agents specialises, 72 endpoints REST, 149 modules de logique metier, 170 fichiers de tests organises en 9 categories, 865 fichiers de documentation, 7 ADR formels, 3 workflows CI distincts.

Les briques differenciantes par rapport au framework hérité concernent en priorite les pipelines metiers (Legal-Safe, strategique, medical, evidence), la couche de delegation et de consensus (router determinste anti-injection, criticality router, consensus collaboratif a trois LLMs, pipeline adversarial), la couche de securite multi-tenant (Argon2id, RBAC, rate limiting Redis, anti-injection, audit log, gate CI dedie 95% coverage) et la couche d'auditabilite (replay engine, human review, risk register dynamique, audit reports).

Le niveau de maturite est avance sur les axes fonctionnel, technique, securite et documentation, et intermediaire a avance sur la maintenabilite, la scalabilite et l'industrialisation. La principale dette technique visible concerne la finalisation de la migration RDBMS planifiee (ADR-007) et quelques artefacts mineurs (fichiers de tests orphelins, commentaires obsoletes ponctuels, drives de submodules).

Plusieurs zones methodologiques restent a confirmer avec le porteur : l'etat de production des feature flags qui controlent les composants d'audit, la couverture de tests reelle hors perimetre securite, la distinction fichier par fichier entre code proprietaire et code herite, et la couverture NDA des mentions clients presentes dans les documents internes.

Sous ces reserves, le code observe constitue une base technique coherente, structuree et documentee, exploitable pour une analyse approfondie de valorisation IP, d'audit technique ou de due diligence. Aucune affirmation de conformite reglementaire externe (AI Act certifie, RGPD certifie) n'est faite par le code lui-meme ; toute communication externe en ce sens doit etre rattachee a un audit independant.

---

*Fin du document.*
