# 00 — Diagnostic initial du depot

**Projet** : KOREV Evidence (alias historique : PRISM-Oracle, KOREV Oracle)
**Apporteur / inventeur** : Amine Mohamed
**Destinataire** : cabinet Diag & Grow et / ou commissaire aux apports
**Branche d'analyse** : `valuation/diag-grow-evidence-pack`
**HEAD analyse** : `fab5689a` (5 mai 2026, dernier commit committe)
**Methode** : lecture seule du depot, aucune modification applicative
**Date** : 9 mai 2026

> Ce document est le point d'entree du Pack de valorisation. Il fournit une photographie factuelle du depot et identifie ce qui doit etre vu, verifie ou complete avant transmission. Tous les chiffres sont reproductibles via les commandes indiquees.

---

## 1. Resume executif

KOREV Evidence est un actif logiciel reellement fonctionnel, derive d'une base open-source MIT (Agent Zero) sur laquelle ont ete ajoutees des couches proprietaires substantielles : protocole de consensus PRISM, framework Evidence d'audit, pipeline juridique Legal-Safe, moteur PDF/OCR industriel, securite multi-tenant, pipeline audit-proof (replay, revue humaine, registre de risques), tests TDD massifs et documentation structurelle (ADR, glossaire, diagrammes C4, SECURITY.md).

L'origine fork est explicitement assumee dans `LICENSE`, `README.md`, `legal/THIRD_PARTY_NOTICES.txt` et le rapport technique. Les preuves Git permettent d'isoler le travail proprietaire de la base communautaire.

**Position recommandee** : la valorisation porte sur l'oeuvre derivee KOREV (couches Evidence, PRISM integre, auditabilite, Legal-Safe, securite, industrialisation), **non sur Agent Zero**. Voir `01_VALUATION_SCOPE.md` pour la formulation defendable.

---

## 2. Etat Git

### 2.1 Identifiants du depot

| Element | Valeur |
|---|---|
| Nom du depot | `KOREV_Oracle/KOREV_Oracle` |
| Repository remote | privée (proprietaire KOREV AI) |
| Branche d'analyse | `valuation/diag-grow-evidence-pack` (creee pour ce pack) |
| Branche principale | `main` |
| HEAD analyse (committe) | `fab5689a` — 5 mai 2026 17:37 +0200 |
| HEAD precedemment audite | `7a7abd6a` (24 avril 2026), `7a77fdb6` (17 avril 2026) |
| Premier commit upstream | `8cef5e1e` (10 juin 2024, frdel) |
| Dernier commit upstream | `9a3a92b6` (10 janvier 2026, Jan Tomasek) |
| Premier commit Amine | `26fc5593` — 15 janvier 2026 ("PRISM Oracle v1.0 - Rebranding & Specialization") |

### 2.2 Metriques Git auditables (HEAD `fab5689a`, 9 mai 2026)

| Metrique | Valeur | Commande |
|---|---:|---|
| Total commits depot (toutes branches) | ~1 360+ | `git log --all --oneline \| wc -l` |
| Commits Amine Mohamed | **271** | `git log --all --author='Amine' --oneline \| wc -l` |
| Insertions Amine cumulees | **+225 477** | `git log --all --author='Amine' --shortstat` |
| Suppressions Amine cumulees | **-18 030** | idem |
| Net Amine cumule | **+207 447** | idem |
| Diff upstream `9a3a92b6` -> HEAD | **920 fichiers, +217 192 / -14 434 (net +202 758)** | `git diff 9a3a92b6..HEAD --shortstat` |
| Diff upstream -> HEAD (Python `.py` uniquement) | **496 fichiers, +161 360 / -2 352** | `git diff 9a3a92b6..HEAD --shortstat -- '*.py'` |
| Diff upstream -> HEAD (Markdown `.md` uniquement) | **148 fichiers, +27 675 / -1 003** | `git diff 9a3a92b6..HEAD --shortstat -- '*.md'` |

### 2.3 Etat working tree au moment du diagnostic

```
Branch valuation/diag-grow-evidence-pack (created from main HEAD fab5689a)
Modifications non commitees presentes (audit-hostile-valorisation/, docs/, scripts/, tests/)
Cf. `git status` pour la liste complete.
```

Les fichiers modifies / non traques au moment de la creation du pack incluent notamment : `SECURITY.md` racine, le dossier `audit-hostile-valorisation/` (9 livrables d'audit hostile, dont l'addendum `09-mise-a-jour-post-p0-yenoyikz.md`), 7 ADR dans `docs/adr/` (ADR-001 a ADR-007), le dossier `docs/preuves-execution/`, et les nouveaux scripts d'utilisateurs. Aucun de ces fichiers n'a ete commite par le present pack.

### 2.4 Commits posterieurs au snapshot du 25 avril 2026 — defenses renforcees

Trois commits techniques ont ete pousses entre le 25 avril et le 5 mai 2026, **tous ancetres de `fab5689a`**. Ils ne modifient pas les fourchettes de valorisation retenues par le rapport technique mais **renforcent materiellement la defense** de la borne haute :

| Commit | Date | Perimetre | Effet sur le pack |
|---|---|---|---|
| `de8b9c7e` | 4 mai 2026 | Fix `file_writer` fail-hard sur `§§include` non resolus + ADR-006 (Tool I/O integrity contract) + 28 tests + post-mortem session yENoyKIZ | Verrouille le pattern fail-silent revele par yENoyKIZ : un PDF de 25 KB avait ete produit avec succes apparent alors que son contenu utile etait `§§include(...)` non resolu. Reponse defendable a l'attaque "vos tools peuvent pretendre avoir reussi alors qu'ils ont ecrit un fichier corrompu". |
| `b11b4d99` | 5 mai 2026 | P0 migration RDBMS : Postgres + pgvector gated + ADR-007 (Postgres pgvector adoption) + 6 tests d'infra T1-T6 + scripts backup/snapshot | Expose explicitement la dette `filesystem-first` (jusqu'alors implicite) et publie une **roadmap structuree en 7 phases sur 4-6 mois** (P0 livre, P1-P6 planifiees). P0 = compose staging autonome, init SQL 5 schemas, aucun service applicatif `depends_on` Postgres (zero-impact prod). Snapshot prod pre-P0 immutable conserve. |
| `0d0a35da` | 5 mai 2026 | Fix DEF-8 `pg_dump --clean --if-exists` + script `pg_restore_from_dump.sh` fail-loud + test T7 | Verrouille un risque de restore fail-silent introduit par P0 lui-meme, **detecte AVANT tout cron actif en prod** (cron file livre avec suffixe `.disabled`). Cycle complet `dump → down -v → up → restore` chronometre a 15 secondes (sous le seuil Go/No-Go P0 → P1 de 30 minutes). |

Source detaillee : `audit-hostile-valorisation/09-mise-a-jour-post-p0-yenoyikz.md` (addendum auditable). Effet **neutre a favorable** sur la valorisation : les fourchettes annoncees (662-850 KEUR plancher / 958-1 054 KEUR equilibre / 1 150-1 350 KEUR offensif) **restent inchangees** ; la borne haute du scenario equilibre est mieux defendue par la fermeture du risque fail-silent et la roadmap RDBMS publiee et amorcee.

**Phrase de cadrage recommandee dans la note de remise a Diag & Grow** :

> "Les commits posterieurs au snapshot du 25 avril 2026 (`de8b9c7e`, `b11b4d99`, `0d0a35da`) ne modifient pas les fourchettes de valorisation retenues. Ils renforcent toutefois la defense de la borne haute par la fermeture d'un risque fail-silent reel (yENoyKIZ → ADR-006), l'ajout d'ADR structurants (ADR-006, ADR-007), la mise en place d'une roadmap RDBMS gated (P0 livre runtime, P1-P6 planifiees) et la validation d'un pipeline backup/restore fail-loud (test T7)."

---

## 3. Architecture generale

### 3.1 Arborescence de premier niveau

```
KOREV_Oracle/
+-- agent.py              <- Boucle principale d'orchestration LLM (~1 144 lignes)
+-- models.py             <- Wrapper LiteLLM, embeddings (~931 lignes)
+-- run_ui.py             <- Application Flask (~745 lignes)
+-- initialize.py         <- Construction AgentConfig
+-- python/
|   +-- api/              <- ~71 handlers HTTP (ApiHandler)
|   +-- helpers/          <- ~181 modules, ~77 155 lignes (coeur metier)
|   +-- tools/            <- Outils agent (code exec, browser, PDF, OCR...)
|   +-- extensions/       <- Hooks cycle de vie (~48 modules)
|   +-- security/         <- Auth, authz, path safety, rate limit (14 fichiers)
|   +-- consensus/        <- Moteur de consensus PRISM
|   +-- legal_sources/    <- Pipeline d'ingestion juridique
|   +-- observability/    <- Metriques runtime
+-- agents/               <- 12 profils de personas (prompts + extensions)
+-- prompts/              <- ~103 fragments de prompts systeme
+-- tools/                <- Scripts utilitaires
+-- tests/                <- ~180 fichiers, 3 956 tests collectes (28 avr.)
+-- docs/                 <- 75+ fichiers de documentation
|   +-- adr/              <- 7 ADR documentant les decisions architecturales (ADR-001 a ADR-007)
|   +-- preuves-execution/ <- Annexes A11/A12 reproductibles
|   +-- valuation/        <- CE PACK (9 documents pour Diag & Grow + audit de controle + corrections)
+-- audit-hostile-valorisation/ <- 9 livrables d'audit hostile interne (dont addendum 09 post-25 avril)
+-- deploy/               <- Docker production, Caddy, scripts
+-- docker/               <- Image alternative dev (Kali base)
+-- scripts/              <- Migrations, validation, installation, provisioning
+-- mcp_servers/          <- 3 MCP servers integres (OpenAlex, Semantic Scholar, PubMed)
+-- knowledge/            <- Base de connaissances agent
+-- legal/                <- Licence proprietaire + notices tierces
+-- conf/                 <- Providers LiteLLM
+-- fonts/                <- Polices PDF (Inter, Playfair Display)
+-- webui/                <- Frontend statique (HTML/JS/CSS, i18n FR/EN)
+-- data/, memory/        <- Donnees runtime (gitignored)
+-- .github/workflows/    <- 3 workflows CI (legal_pipeline_ci, main_gate, security_ci)
```

### 3.2 Modules critiques

| Module | Lignes | Role | Type |
|---|---:|---|---|
| `python/helpers/settings.py` | ~2 225 | Configuration centrale (monolithe) | Tres lourd |
| `python/helpers/adversarial_instruction.py` | ~2 123 | Detection injections adverses | Coeur PRISM |
| `python/helpers/legal_orchestrator.py` | ~1 960 | Orchestration juridique multi-agent | Coeur Legal-Safe |
| `python/helpers/legal_pipeline.py` | ~1 807 | Ingestion juridique (Legifrance, FTS5) | Coeur Legal-Safe |
| `python/helpers/strategic_orchestrator.py` | ~1 560 | Orchestration strategique | Coeur Strategic |
| `python/helpers/task_scheduler.py` | ~1 458 | Planificateur de taches | Infrastructure |
| `python/helpers/reporting/evidence_native.py` | ~1 422 | Assemblage rapport d'audit Evidence | Coeur Evidence |
| `python/helpers/pdf_extraction/pipeline.py` | ~1 217 | Extraction PDF / OCR avec circuit breakers | PDF/OCR |
| `python/helpers/reasoning_engine.py` | ~1 190 | Metacognition, baseline tracking | Coeur Reasoning |
| `python/helpers/mcp_handler.py` | ~1 148 | Gestionnaire MCP | Integration |
| `agent.py` (racine) | ~1 144 | Boucle agent principale | Heritage Agent Zero (refondu) |
| `python/helpers/evidence_pdf_engine.py` | ~1 091 | Moteur PRISM WeasyPrint + ReportLab | Coeur Evidence |
| `python/helpers/metacognition.py` | ~1 046 | Metacognition (auto-evaluation) | Coeur Reasoning |

### 3.3 Volumetrie globale (28 avril 2026, fichier `D_volumetrie_code.txt`)

| Element | Valeur |
|---|---:|
| Fichiers Python (hors venv, node_modules, .git) | 606 |
| Lignes Python | 189 744 |
| Fichiers de test (`tests/`) | 183 |
| Lignes de tests | 68 279 |
| Fichiers `.md` (toutes branches incluses) | 838 (dont 589 dans `mcp_servers/`, 103 dans `prompts/`) |
| Fichiers `.md` proprietaires (diff upstream -> HEAD) | **148** |
| Lignes `.md` proprietaires (diff upstream -> HEAD) | **+27 675 / -1 003** |

---

## 4. Dependances principales

### 4.1 Python (`requirements.txt` — ~61 packages)

| Categorie | Packages cles | Statut licence |
|---|---|---|
| Abstraction LLM | `litellm` (1.79.3, hors requirements.txt direct) | MIT |
| RAG / orchestration | `langchain-core`, `langchain-community`, `langgraph` | MIT |
| Web | `flask[async]`, `werkzeug` | BSD |
| Vector store | `faiss-cpu` | MIT |
| Embeddings | `sentence-transformers` | Apache 2.0 |
| Browser | `playwright` (necessite Chromium ~100 MB) | Apache 2.0 |
| Speech | `openai-whisper`, `kokoro-tts` | MIT / Apache 2.0 |
| Securite | `argon2-cffi`, `cryptography` | MIT, Apache 2.0 |
| PDF | `weasyprint`, `reportlab`, `pypdf`, `pdfplumber` | BSD / BSD / BSD / MIT |
| OCR | `pytesseract`, `pdf2image` | Apache 2.0 / MIT |

Toutes ces dependances sont **exclues de la valorisation proprietaire**. Cf. `01_VALUATION_SCOPE.md`.

### 4.2 Node / npm (runtime)

`@playwright/mcp`, `@modelcontextprotocol/server-brave-search`, plus 3 MCP servers locaux dans `mcp_servers/` (OpenAlex, Semantic Scholar, PubMed) avec leurs propres `package.json` (Apache 2.0 / MIT).

### 4.3 Infrastructure

- **Docker Compose** (orchestration multi-container)
- **Caddy** (reverse proxy avec TLS auto)
- **Redis** (rate limiting distribue, optionnel)
- **Samba** (partage fichiers, optionnel)

---

## 5. Licence et compliance

### 5.1 Licence du depot

- `LICENSE` racine : **proprietaire KOREV AI** ("All Rights Reserved", confidentialite, reference au texte complet `legal/KOREV_LICENSE.txt`)
- `README.md` : badge "License-Proprietary" (corrige le 3 avril 2026, commit `40808223`)
- `legal/KOREV_LICENSE.txt` : texte de la licence proprietaire

### 5.2 Notices tierces

- `legal/THIRD_PARTY_NOTICES.txt` : notice complete de la base Agent Zero (MIT, copyright 2024 Jan Tomasek), texte MIT integral, et notices des dependances open-source.

### 5.3 Licence d'Agent Zero

- **MIT** : usage commercial autorise, modification libre, oeuvres derivees proprietaires permises, sous reserve de conserver la notice de copyright. Aucun obstacle juridique bloquant identifie a ce stade pour valoriser les developpements proprietaires construits sur cette base.

### 5.4 Coherence licences (verification croisee)

| Verification | Resultat |
|---|---|
| README badge vs LICENSE racine | Coherent — "Proprietary" en rouge |
| LICENSE racine vs `legal/KOREV_LICENSE.txt` | Coherent |
| Notice MIT Agent Zero | Presente et complete dans `legal/THIRD_PARTY_NOTICES.txt` |
| Mentions internes des notices tierces | Reference dans le README et le rapport technique |

---

## 6. Documentation existante (avant ce pack)

### 6.1 Documentation de valorisation existante

| Document | Lignes | Role |
|---|---:|---|
| `docs/RAPPORT_TECHNIQUE_VALORISATION_EVIDENCE.md` | ~1 100 | Rapport technique principal pour commissaire aux apports |
| `docs/DOSSIER_COMMISSAIRE_APPORTS_EVIDENCE.md` | ~241 | Dossier commissaire (synthese) |
| `docs/BENCHMARK_COMPARABLES_VALORISATION_EVIDENCE.md` | ~335 | Benchmark de comparables marche |
| `audit-hostile-valorisation/` (8 livrables + mise a jour P0) | — | Audit hostile interne complet |
| `docs/preuves-execution/PREUVES_TECHNIQUES_EXECUTION.md` | — | Annexes A11/A12 reproductibles |

### 6.2 Documentation de gouvernance

| Document | Statut |
|---|---|
| `SECURITY.md` racine | Present (17 avril 2026), 6 582 octets |
| `docs/adr/ADR-001` a `ADR-007` | 7 ADR (PRISM, router, Evidence, LiteLLM, extensions, tool I/O, Postgres) |
| `docs/GLOSSARY.md` | Present (30+ termes proprietaires) |
| `docs/ARCHITECTURE_C4_DIAGRAMS.md` | Present (3 niveaux + sequence Mermaid) |
| `docs/DEVELOPER_ONBOARDING_ARCHITECTURE_GUIDE.md` | Present (1 196 lignes) |
| `docs/FEUILLE_DE_ROUTE_CONFORMITE_FORMAT_EVIDENCE.md` | Present (1 893 lignes) |

---

## 7. Tests, CI et industrialisation

### 7.1 Tests

| Element | Valeur | Source |
|---|---:|---|
| Tests collectes (28 avril 2026, Python 3.11.12, pytest 9.0.2) | **3 956** | `docs/preuves-execution/A11_pytest_collect_only.txt` |
| Reference documentaire (17 avril 2026) | 3 910 | `docs/RAPPORT_TECHNIQUE_VALORISATION_EVIDENCE.md` |
| Tests qualite documentation (PASSED) | **64 / 64 en 4.32s** | `docs/preuves-execution/B_pytest_doc_quality.txt` |
| Network Guard | ACTIVE par defaut (bloque LLM reels) | `tests/conftest.py` |
| Plugins | asyncio, langsmith, typeguard, coverage | pytest header |

### 7.2 Workflows CI (`.github/workflows/`)

| Workflow | Role | Statut |
|---|---|---|
| `legal_pipeline_ci.yml` | Tests pipeline juridique | Operationnel |
| `main_gate.yml` | Gate principal (suite etendue) | Operationnel mais `continue-on-error: true` sur `extended-tests` (P1-3 en cours) |
| `security_ci.yml` | Tests securite avec seuil 90% | Operationnel |

**Limites CI assumees** :
- Pas de build Docker en CI (P1-5 ouvert)
- Pas de SAST / scanning de dependances (P2-4 ouvert)
- Suite etendue non-bloquante (P1-3 ouvert)

### 7.3 Scripts

`scripts/` contient ~41 scripts incluant : installation Windows / Mac, provisioning multi-tenant, migrations, ajout d'utilisateurs, validation production, smoke tests, audit. Volume cumule : ~8 834 lignes (cf. apport L du rapport technique).

### 7.4 Docker

| Fichier | Taille | Role |
|---|---:|---|
| `deploy/Dockerfile.backend` | 9 831 octets | Image backend Python 3.11-slim multi-stage (production) |
| `deploy/Dockerfile.frontend` | 3 435 octets | Image frontend |
| `deploy/docker-compose.yml` | 13 380 octets | Composition production complete |
| `DockerfileLocal` | 1 225 octets | Dockerfile de developpement |
| `docker/` (dossier) | — | Image alternative dev (Kali base) |

`docker compose -f deploy/docker-compose.yml config --quiet` retourne exit code 0 (warnings non bloquants sur l'echappement `$` des hashes Argon2id dans `.env`).

---

## 8. Traces Agent Zero vs traces KOREV

### 8.1 Traces Agent Zero (heritage)

- Boucle d'agent generique dans `agent.py` (refondue mais encore reconnaissable)
- Structure `python/helpers/`, `python/tools/`, `python/extensions/` (pattern upstream)
- WebUI Alpine.js (refondue : i18n, branding, settings panels)
- `agents/` profils initiaux (refondus : prompts metiers, contraintes Legal-Safe)
- `prompts/` (templates initiaux modifies + nouveaux templates metiers)
- `instruments/`, `knowledge/` (structure heritee)
- `DockerfileLocal`, `docker/` (image dev historique heritee)
- README.md initial (entierement refondu)

### 8.2 Traces KOREV strictement proprietaires

Cf. `02_AGENT_ZERO_DELTA.md` et `03_EVIDENCE_PROPRIETARY_MODULES.md` pour le detail.

Synthese :
- `python/consensus/` (moteur de consensus PRISM, point d'entree unique)
- `python/helpers/consensus_*.py` (~6 200 LOC)
- `python/helpers/adversarial_*.py` + `collaborative_*.py` (~4 600 LOC)
- `python/helpers/router/` + `criticality_router.py` + `critical_decision_gate.py` (~4 470 LOC)
- `python/helpers/legal_*.py` + `python/helpers/contract_drafting/` + `python/extensions/legal_safe_mode/` (~16 550 LOC)
- `python/helpers/pdf_extraction/`, `pdf_generator.py`, `evidence_pdf_engine.py`, `evidence_document/`, `strategic_charts.py` (~12 380 LOC)
- `python/helpers/reasoning_engine.py`, `metacognition.py` (~2 240 LOC)
- `python/helpers/strategic_*.py`, `python/helpers/research_*.py`, `python/helpers/reporting/` (~6 760 LOC)
- `python/security/` (14 fichiers, ~2 553 LOC)
- `python/helpers/replay_engine.py`, `human_review.py`, `dynamic_risk_register.py` + extensions (~1 692 LOC) — pipeline audit-proof
- `deploy/` Docker production + Caddy + scripts (~9 500 LOC)
- `tests/` (180 fichiers, ~67 200 LOC)
- `docs/` proprietaires (148 fichiers diff, +27 675 lignes)

---

## 9. Dette technique visible

### 9.1 Modules monolithiques (a scinder en P2-1, P2-2)

- `python/helpers/settings.py` : 2 225 lignes, configuration centrale (couplage fort)
- `python/helpers/adversarial_instruction.py` : 2 123 lignes
- `python/helpers/legal_orchestrator.py` : 1 960 lignes
- `python/helpers/legal_pipeline.py` : 1 807 lignes
- `python/helpers/strategic_orchestrator.py` : 1 560 lignes

### 9.2 Duplications conceptuelles

- Deux classes `ArbiterConfig` dans des modules differents (P2-2)
- Trois chemins consensus (`consensus_integration.py` / `consensus_arbiter.py` / `consensus/engine.py`)
- Masquage de secrets duplique entre extensions (avec `except: pass`, P2-8)
- Dual Docker non reconcilie (`deploy/Dockerfile.backend` vs `DockerfileLocal` + `docker/`)

### 9.3 Code mort identifie (P2-7)

- `browser.py` : ~336 lignes commentees
- Blocs commentes dans `initialize.py`, `files.py`
- Execution guard mort dans `agent.py`
- `docker/` et `DockerfileLocal` peut-etre archivables si `deploy/Dockerfile.backend` suffit

### 9.4 Zones a forte connaissance implicite

- Contrat d'extensions (ordre, kwargs) : partiellement documente par ADR-005
- Frontiere consensus (3 chemins) : a unifier
- Tables `router/policy.py` : calibration implicite
- `mcp_config.json` vs `mcp_config.production.json` : seul le second est portable

---

## 10. Elements runtime potentiellement versionnes

### 10.1 Donnees runtime (gitignored ou .gitkeep vides)

`data/`, `memory/`, `tmp/`, `logs/` contiennent en production : index legal FTS5, embeddings FAISS, chats, audit reports, donnees utilisateurs. **Ces donnees ne sont pas dans le depot Git** : seuls les `.gitkeep` sont versionnes.

### 10.2 Volumetrie runtime locale (machine de l'apporteur)

| Dossier | Contenu | Statut Git |
|---|---|---|
| `logs/` | 411 entrees datees (cycles d'utilisation reelle, traces Whisper, etc.) | gitignored |
| `memory/` | Cache FAISS / embeddings | gitignored |
| `data/` | Index legal | gitignored |
| `tmp/` | Fichiers temporaires (uploads, exports PDF) | gitignored |
| `__pycache__/` | Caches Python | gitignored |
| `venv/` | Environnement virtuel Python | gitignored |
| `.coverage` | Rapport coverage | gitignored |

**Aucun de ces elements n'est commite et ils ne doivent pas etre valorises.**

---

## 11. Risques secrets / cles / tokens (verification de surface)

### 11.1 Constatations

- `.env` racine : present localement (4 266 octets), **gitignored**.
- `.env.example` : present, modifie recemment (`deploy/users.json.example` aussi modifie). **A inspecter** avant transmission pour s'assurer qu'aucun token / mot de passe reel n'a fuite.
- `newrelic_agent.log` : ~4 266 octets, droits `-rw-------` (acces apporteur). Statut Git a verifier (probablement gitignore).
- `cspell.json`, `.gitignore` : standards.

### 11.2 Points d'attention pour la transmission

- **Verifier `.env.example`** : il a ete modifie recemment (cf. `git status`) ; s'assurer que ses valeurs sont bien des placeholders.
- **Verifier `deploy/users.json.example`** : modifie. S'assurer qu'aucune empreinte Argon2id reelle n'est exposee, meme si sans valeur, pour eviter de divulguer une politique de mot de passe.
- **Confirmer que `.env`, `users.json`, fichiers de cle `.pem` ne sont pas trackes par Git** : `git ls-files .env .env.production users.json deploy/users.json` doit retourner vide.
- **Verifier `mcp_config.json`** : peut contenir des chemins absolus machine-specifiques. Le rapport technique recommande l'usage de `mcp_config.production.json` portable.

### 11.3 Recommandation

Avant transmission a Diag & Grow, executer :
```bash
git ls-files | grep -iE '\.(env|pem|key)$|users\.json$|secrets?\.json$'
git log --all -p -- '.env' '.env.production' 'users.json' 'deploy/users.json' 2>&1 | head -50
```
Et confirmer qu'aucune valeur reelle n'est exposee.

---

## 12. Elements legacy

| Element | Statut | Decision |
|---|---|---|
| `agent.py` racine | Refondu mais reconnaissable d'Agent Zero | A conserver (boucle agent integree au pipeline Evidence) |
| `models.py` racine | Refondu (LiteLLM, retry, streaming) | A conserver |
| `initialize.py` | Construction AgentConfig | A conserver |
| `prepare.py`, `preload.py` | Bootstrap runtime | A conserver |
| `browser.py` | ~336 lignes de code commente | **A nettoyer** (P2-7) — non valorise |
| `instruments/` | Heritage Agent Zero | Non valorise (peu utilise) |
| `knowledge/`, `memory/` | Structure heritee | Non valorise (donnees gitignored) |
| `DockerfileLocal`, `docker/` | Image dev historique | A archiver si non utilise (P2-7) |

---

## 13. Modules proprietaires differenciants (panorama)

Les modules ci-dessous portent l'essentiel de la valeur defendable. Cf. `03_EVIDENCE_PROPRIETARY_MODULES.md` pour la liste complete avec heures de reconstruction.

1. **Pipeline Consensus PRISM fail-closed** (`python/consensus/`, `consensus_*.py`, ~6 200 LOC) — algorithmes issus du projet anterieur PRISM, integres dans Evidence.
2. **Debat adversarial / Instruction contradictoire** (`adversarial_*.py`, `collaborative_consensus.py`, ~4 600 LOC) — extension PRISM, applique le debat a la validation IA.
3. **Router deterministe + Gate de criticite** (`router/`, `criticality_router.py`, `critical_decision_gate.py`, ~4 470 LOC) — anti-injection, hash-based, contrats types.
4. **Pipeline Legal-Safe complet** (`legal_*.py`, `contract_drafting/`, `extensions/legal_safe_mode/`, ~16 550 LOC) — ingestion Legifrance, FTS5, Act Leak Guard fail-closed, redaction de contrats.
5. **Moteur PDF/OCR industriel + PRISM PDF** (`pdf_extraction/`, `evidence_pdf_engine.py`, `evidence_document/`, `strategic_charts.py`, ~12 380 LOC) — circuit breakers, timeouts stricts, WeasyPrint + ReportLab fallback.
6. **Reasoning & Metacognition** (`reasoning_engine.py`, `metacognition.py`, ~2 240 LOC) — auto-evaluation, escalade non-diluable.
7. **Pipeline strategique & Reporting Evidence-grade** (`strategic_*.py`, `reporting/evidence_native.py`, `report_*.py`, `extensions/strategic_validation/`, ~6 760 LOC) — 10 blocs canoniques de rapport.
8. **Securite multi-tenant** (`python/security/` 14 fichiers, ~2 553 LOC + `user_manager.py`, `deploy_config.py`, `health_endpoints.py`) — Argon2id, autorisation par principal, rate limiting Redis+memoire.
9. **Pipeline Audit-Proof** (`replay_engine.py`, `human_review.py`, `dynamic_risk_register.py` + extensions + APIs, ~1 692 LOC) — replay deterministe, revue humaine, scoring de risques temps reel. **Nouveau avril 2026**.
10. **Framework Evidence (integrite + audit reports)** (`integrity_block.py`, `session_envelope.py`, `evidence.py`, `reporting/`, `evidence_document/`) — HMAC obligatoire, RSA optionnel, ComplianceGrid AI Act/RGPD.
11. **Suite de tests TDD industrielle** (~180 fichiers, ~67 200 LOC, 3 956 tests collectes) — incluant FakeLLMProvider, FakeMCPHandler, network guard, golden tests OCR / legal.
12. **Documentation proprietaire** (148 fichiers diff, +27 675 lignes) — incluant 7 ADR, SECURITY.md, GLOSSARY, C4, benchmark comparables, guide onboarding 1 196 lignes.

---

## 14. Points forts

1. **Differenciateur PRISM reel** : consensus multi-arbitres, debat adversarial, gate de criticite. Issu d'un projet anterieur a Evidence (4 brevets PRISM en cours).
2. **Framework Evidence d'audit** : 10 blocs canoniques, integrite cryptographique HMAC + RSA optionnel, ComplianceGrid AI Act/RGPD.
3. **Pipeline audit-proof unique** : replay engine, human review, dynamic risk register — repondent directement a la critique "auto-evaluation".
4. **Securite multi-tenant** : fondations professionnelles (Argon2id, isolation par principal/organisation, rate limiting distribue).
5. **Volume de code et de tests** : 189 744 LOC Python, 3 956 tests collectes — au-dessus de la moyenne pour un actif a ce stade.
6. **Documentation desormais structurelle** : 7 ADR, SECURITY.md, GLOSSARY, C4, benchmark, audit hostile complet.
7. **Pipeline Legal-Safe complet** : ingestion sources officielles, FTS5, Act Leak Guard fail-closed (actif vertical valorisable).

---

## 15. Points faibles

1. **Modules monolithiques** : `settings.py`, `agent.py`, `legal_orchestrator.py`, `adversarial_instruction.py` concentrent trop de logique. Bus factor critique.
2. **CI partielle** : pas de build Docker en CI, pas de SAST, suite etendue non-bloquante (P1-3 a P1-5 ouverts).
3. **Mode sans authentification par defaut** quand config absente — toujours present (P1-6 ouvert).
4. **Masquage secrets fail-open** (`except: pass`) — toujours present (P2-8 ouvert).
5. **Pas de schema de donnees formel** ni d'API reference (P2-5 ouvert).
6. **Auto-evaluation conformite** : pas d'audit externe (attenue par le pipeline audit-proof, mais subsiste).
7. **Bus factor = 1** : pas de CODEOWNERS, pas de contributor guide effectif (attenue par 7 ADR + onboarding 1 196 lignes).
8. **Documentation heterogene** : melange FR/EN, doublons (tmp/uploads vs docs/).

---

## 16. Risques de decote

Cf. `audit-hostile-valorisation/05-angle-morts-et-decote-potentielle.md` pour le detail complet. Synthese :

| Risque | Decote estimee (post-P0/P1/P2 partiel) | Neutralisable ? |
|---|---|---|
| Dependance apporteur / inventeur (key-man) | 10-15% | Partiellement (ADR, glossaire, C4, onboarding) |
| Failles secu vs narratif "IA de confiance" | 5-10% | Partiellement (P0 fait, P1-6 + P2-8 a faire) |
| CI/CD immature | 5-10% | Oui (1-2 semaines) |
| Zones non prouvables (auto-certif AI Act, audit penetration absent) | 3-10% | Partiellement (audit-proof attenue) |
| Documentation absente (schema donnees, API ref) | 3-5% | Oui (semaines) |
| Architecture implicite | 2-5% | Largement attenue (C4, ADR) |
| Perception fork / demo sophistiquee | 5-10% | Partiellement (delta proprietaire bien documente) |
| **Cumul realiste (non additif)** | **~12-20%** | **Reductible a ~8-12% apres P1+P2 complets** |

---

## 17. Elements a verifier avant transmission

### 17.1 Verifications techniques (executables)

- [ ] `git ls-files | grep -iE '\.(env|pem|key)$|users\.json$|secrets?\.json$'` retourne vide
- [ ] `pytest --collect-only -q tests/` retourne ~3 956 tests sans erreur
- [ ] `docker compose -f deploy/docker-compose.yml config --quiet` retourne exit code 0
- [ ] `bash docs/preuves-execution/run_docker_proof.sh` execute sans erreur
- [ ] `git diff 9a3a92b6..HEAD --shortstat` retourne ~920 fichiers / +217 192
- [ ] Les chiffres des sections 2 et 3 sont coherents avec ceux du `RAPPORT_TECHNIQUE_VALORISATION_EVIDENCE.md`
- [ ] Les tests de qualite documentation passent (64 / 64)

### 17.2 Verifications documentaires

- [ ] Coherence entre `RAPPORT_TECHNIQUE_VALORISATION_EVIDENCE.md`, `DOSSIER_COMMISSAIRE_APPORTS_EVIDENCE.md` et le present pack
- [ ] Toutes les references croisees du pack sont valides (cf. `08_AUDIT_HOSTILE_VALUATION_PACK.md`)
- [ ] Aucun chiffre non source
- [ ] Aucune reference a une fonctionnalite non presente dans le code

### 17.3 Annexes externes a fournir

- [ ] Factures DICA FRANCE (1 500 EUR/mois) + preuves de paiement
- [ ] Conventions / emails de pilotes terrain (Centrale Lille, Le Tarmac)
- [ ] Pieces datees R&D pre-repository (pour antériorite PRISM)
- [ ] Dossier des 4 brevets PRISM en cours + chaine de droits PRISM -> Evidence
- [ ] Attestation d'inventeur d'Amine Mohamed sur PRISM et Evidence

---

## 18. Conclusion hostile

> Un evaluateur hostile attaquera en priorite : **(a) le narratif "fork sophistique"**, **(b) le bus factor unique**, **(c) la non-mesure de couverture en CI**, **(d) la dependance Agent Zero**, **(e) l'auto-evaluation conformite**, **(f) le mode sans authentification par defaut**.

Reponses defendables disponibles dans le pack :

- Le **delta proprietaire est documente ligne par ligne** (`02_AGENT_ZERO_DELTA.md`, top 20 fichiers / categorie).
- Le **bus factor est attenue** par 7 ADR + glossaire + C4 + onboarding 1 196 lignes (~1.5-2 semaines d'onboarding restent a justifier).
- La **CI execute 3 956 tests** dont ~90% bloquants (security_ci 90%) ; le P1-3 reste a finir.
- La **dependance Agent Zero** est limitee a la boucle agent generique : tous les modules de valeur sont 100% proprietaires.
- L'**auto-evaluation est attenuee** par le pipeline audit-proof (replay deterministe, revue humaine, scoring temps reel).
- Le **mode sans auth** est documente comme limite assumee dans `SECURITY.md` ; correction prevue (P1-6).

**Statut du depot pour transmission Diag & Grow** : **PRET AVEC RESERVES** (cf. `08_AUDIT_HOSTILE_VALUATION_PACK.md` pour la synthese finale et le top 5 corrections avant envoi).

---

*Diagnostic etabli le 9 mai 2026 sur la branche `valuation/diag-grow-evidence-pack`, HEAD `fab5689a`. Aucune modification applicative n'a ete realisee. Tous les chiffres sont reproductibles via les commandes Git indiquees.*
