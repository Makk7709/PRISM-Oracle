<div align="center">

# `KOREV Evidence`

### Plateforme multi-agents d'IA de confiance pour professions réglementées

[![Statut](https://img.shields.io/badge/Statut-Production-0A192F?style=for-the-badge)](#statut-du-d%C3%A9p%C3%B4t)
[![License](https://img.shields.io/badge/License-Proprietary-red?style=for-the-badge)](./LICENSE)
[![Tests](https://img.shields.io/badge/Tests-3956%20collect%C3%A9s%20(snapshot%2028%20avr.%202026)-green?style=for-the-badge)](./docs/METRICS_CANONICAL_SOURCE.md)

**Juridique · Médical · Finance · Stratégie · Cybersécurité — sorties critiques signées et fail-closed.**

[Installation](#installation) ·
[Architecture](#architecture-générale) ·
[Modules](#modules-actifs) ·
[Documentation](#documentation-de-référence) ·
[Auditeurs](#pour-les-auditeurs--commissaire-aux-apports)

</div>

---

## Présentation

KOREV Evidence est une plateforme multi-agents d'IA de confiance conçue pour les professions réglementées (avocats, médecins, chercheurs, consultants, finance). Construite sur une base d'orchestration open-source (Agent Zero, MIT), sa valeur propre porte sur les couches **Evidence / PRISM / Legal-Safe** : routage de criticité, consensus multi-LLM, et **sorties critiques signées avec doctrine fail-closed**.

Points clés :

- **12 profils d'agents** — juridique, médical, rédaction contractuelle (`legal_drafting_guarded`), contradicteur, stratégie/finance, cybersécurité (`hacker`), recherche, développement, marketing, ventes, multitâche, défaut.
- **Routage de criticité** — classification LEVEL 1/2/3 (`python/helpers/criticality_router.py`) déterminant si une requête exige un consensus.
- **Consensus multi-LLM (PRISM v2)** — API canonique `run_consensus()` (`python/consensus/engine.py`), quorum 2/3 sur votes valides.
- **Sorties critiques signées** — couche `critical_output` : signature v2 (RSA-PSS-SHA256 en prod, repli HMAC), anti-tamper, **fail-closed par défaut** sur les décisions critiques (voir [ADR-010](./docs/adr/ADR-010-critical-output-doctrine.md)).
- **Pipelines métier** — juridique (FTS5/Légifrance, Act Leak Guard fail-closed), médical (PRISM + FAERS), stratégique (multi-agents + consolidation).
- **Multi-tenant strict** — isolation par organisation, rôles OWNER/MEMBER.
- **Raisonnement métacognitif** — escalade non-diluable (`metacognition.py`, `reasoning_engine.py`).
- **Recherche académique** — serveurs MCP (ArXiv, PubMed, Semantic Scholar, OpenAlex, Crossref, EUR-Lex, etc.) ; 3 serveurs fournis localement dans `mcp_servers/` (`openalex`, `pubmed`, `semanticscholar`), les autres via configuration MCP.
- **Extraction PDF robuste** — circuit breakers, timeouts stricts, OCR Tesseract.

> **Métriques** : 3 956 tests collectés (snapshot probatoire 28 avril 2026, Python 3.11.12 / pytest 9.0.2). Source canonique unique : [`docs/METRICS_CANONICAL_SOURCE.md`](./docs/METRICS_CANONICAL_SOURCE.md). Tout autre chiffre rencontré ailleurs doit être considéré comme non canonique.

---

## Statut du dépôt

| | |
|---|---|
| **Doctrine de sortie critique** | Fail-closed par défaut, signée (ADR-010) — **active** |
| **Chemin chat critique** | Signé (consensus → `critical_output` → signature v2) |
| **Pipeline legal** | Signé ; fail-soft explicite documenté avec bannière « NON VALIDÉE » (réserve P1) |
| **Déploiement** | OVH (Docker Compose) via `scripts/deploy_prod.sh` |
| **Réserves connues (P1)** | `collaborative_consensus`, migration medical/smoke, modules de recherche dépréciés (cf. [Modules legacy](#modules-legacy--dépréciés)) |

> **La documentation active est prioritaire sur les documents archivés** (`docs/archive/`).

---

## Architecture générale

Pipeline d'une requête utilisateur jusqu'à la sortie :

```
Requête utilisateur
   │
   ▼
Agent.monologue()  ──►  criticality_router  (LEVEL 1 / 2 / 3)
   │                          │
   │                          ├─ LEVEL 1 (non critique) ─► réponse directe
   │                          │
   │                          └─ LEVEL 2/3 (critique) ───► consensus requis
   │                                                          │
   │   (délégation call_subordinate / pipeline legal)         ▼
   │                                              consensus engine (run_consensus, PRISM v2)
   │                                                          │
   ▼                                                          ▼
Point d'émission ──────────────────────────────►  critical_output.finalize_critical_output()
 • tool `response` (chat)                              • normalise consensus_result + policy + audit_metadata
 • short-circuit pipeline (agent.py)                   • signature v2 (RSA/HMAC) ou FAIL_CLOSED
                                                       ▼
                                              Sortie signée (ou blocage fail-closed explicite)
```

Cartographie détaillée et vérifiée :
- [`docs/audit/critical_request_path_map.md`](./docs/audit/critical_request_path_map.md) — chemin critique réel.
- [`docs/architecture/EVIDENCE_DELEGATION_ARCHITECTURE_VERIFIED.md`](./docs/architecture/EVIDENCE_DELEGATION_ARCHITECTURE_VERIFIED.md) — délégation, ancré code.
- [`docs/architecture/CHAT_DELEGATION_PIPELINE_MAP.md`](./docs/architecture/CHAT_DELEGATION_PIPELINE_MAP.md) — pipeline post-chat.
- [`docs/architecture.md`](./docs/architecture.md) — vue générique du framework (agents, outils, extensions, mémoire).

Arborescence (extrait) :

```
KOREV_Oracle/
├── agent.py                     # Boucle agent + short-circuit pipeline
├── python/
│   ├── consensus/engine.py      # run_consensus() — API canonique PRISM v2
│   ├── helpers/
│   │   ├── criticality_router.py    # Classification LEVEL 1/2/3
│   │   ├── critical_output.py       # Finalisation + signature v2 + fail-closed
│   │   ├── consensus_*.py           # Manager / arbiter / contracts
│   │   ├── metacognition.py         # ReasoningEngine
│   │   ├── router/                  # Deterministic Router v2
│   │   └── pdf_extraction/          # Pipeline PDF/OCR
│   ├── extensions/legal_safe_mode/  # Court-circuit pipeline legal
│   └── tools/                       # Outils agent (dont response.py)
├── conf/model_providers.yaml    # Configuration LLM providers
├── mcp_servers/                 # Serveurs MCP locaux (openalex, pubmed, semanticscholar)
├── webui/                       # Interface
├── prompts/ · agents/           # Prompts système + profils d'agents (runtime)
├── deploy/ · scripts/           # Compose, RUNBOOK, deploy_prod.sh
├── tests/                       # Suite de tests (cf. METRICS_CANONICAL_SOURCE)
└── docs/                        # Documentation (voir ci-dessous)
```

---

## Modules actifs

| Module | Rôle | Référence |
|---|---|---|
| `criticality_router` | Classification de criticité (déclenche le consensus) | `python/helpers/criticality_router.py` |
| `consensus/engine` (PRISM v2) | API canonique `run_consensus()` | `python/consensus/engine.py` |
| `critical_output` | Finalisation + signature v2 + fail-closed | `python/helpers/critical_output.py` |
| `legal_safe_mode` | Court-circuit pipeline juridique signé | `python/extensions/legal_safe_mode/` |
| Deterministic Router v2 | Routage multi-intent policy-driven | `python/helpers/router/` |
| ReasoningEngine | Métacognition + escalade non-diluable | `python/helpers/metacognition.py` |
| PDF extraction | Extraction robuste + OCR | `python/helpers/pdf_extraction/` |

### Moteur de raisonnement (escalade non-diluable)

| Niveau | Seuil | Action |
|--------|-------|--------|
| `SAFE_REFUSE` / `HUMAN_REVIEW` | confidence < 0.35 | Refus / validation humaine |
| `ASK_CLARIFY` | confidence < 0.5 | Questions ciblées |
| `NONE` | confidence ≥ 0.5 | Exécution autonome |

Invariants : monotonie (les signaux ne peuvent que durcir l'escalade), non-dilution, no-PII.

---

## Modules legacy / dépréciés

> Ces composants sont conservés pour compatibilité ou réserve, mais **ne sont pas la voie active**. Ne pas les présenter comme production-ready.

| Module / sujet | Statut | Note |
|---|---|---|
| `research_consensus_integration.py` | **Déprécié (P1)** | Bannière dépréciée dans le docstring ; migration à planifier |
| `research_pipeline.py` | **Déprécié (P1)** | Idem |
| `consensus_integration.py`, `consensus_mcp_integration.py` | **Supprimés** | Orphelins retirés lors du réalignement (mai 2026) |
| `collaborative_consensus` | **Réserve P1** | Non encore aligné sur la doctrine signée |
| Migration medical / smoke | **Réserve P1** | À migrer vers `critical_output` |

Doctrine et historique : [ADR-009](./docs/adr/ADR-009-response-gate-disabled.md) (gate désactivé, historique) → [ADR-010](./docs/adr/ADR-010-critical-output-doctrine.md) (doctrine courante).

---

## Installation

### Prérequis
- **Python 3.11+**
- Clé API **OpenRouter** (LLMs)
- Optionnel : clé OpenAI (images)

### Installation rapide

```bash
# Mac / Linux
cd scripts && chmod +x install-mac.sh && ./install-mac.sh

# Windows
scripts\install-windows.bat
```

### Configuration

```env
# .env
API_KEY_OPENROUTER=sk-or-...
WEB_UI_PORT=5050
```

### Lancement

```bash
python run_ui.py        # interface web (http://localhost:5050)
```

### Déploiement production (OVH / Docker Compose)

```bash
git push origin main
# sur le serveur : pull + rebuild + estampillage commit
./scripts/deploy_prod.sh
```

Procédure complète : [`deploy/RUNBOOK.md`](./deploy/RUNBOOK.md). (La topologie serveur détaillée n'est **pas** versionnée — référence interne hors dépôt.)

---

## Tests

```bash
python -m pytest tests/ -v
./scripts/run_tests.sh blocking     # gates bloquants (CI)
```

Sous-totaux indicatifs et chiffre probatoire : voir [`docs/METRICS_CANONICAL_SOURCE.md`](./docs/METRICS_CANONICAL_SOURCE.md) (source unique). Suites étendues (e2e, security, integration, infra) collectées séparément selon l'environnement.

---

## Configuration des modèles

OpenRouter comme provider principal (`conf/model_providers.yaml`) :

| Modèle | Usage recommandé |
|--------|------------------|
| `openai/gpt-4o` | Chat principal, tâches complexes |
| `openai/gpt-4.1-mini` | Utilitaire, tâches rapides |
| `anthropic/claude-3.5-sonnet` | Raisonnement, code |
| `google/gemini-2.0-flash` | Multimodal, vision |

Changer de modèle : Paramètres → Agent Settings → Chat Model.

---

## Contribution

- Travail sur branche dédiée + Pull Request.
- **Protocole interne de pre-commit-audit** (3 phases : relecture contradictoire du diff, checklist de défauts, re-audit total si défaut Critique/Important) **avant tout commit/push**.
- Ne pas réintroduire de références à des modules supprimés/dépréciés comme s'ils étaient actifs.

---

## Sécurité documentaire

- **Aucun secret** (mot de passe, clé privée, `.env`, topologie infra) ne doit être versionné. Le dépôt étant susceptible d'être public, traiter toute donnée d'infrastructure comme sensible.
- La documentation **active** prime sur les documents **archivés** (`docs/archive/`).
- Tout document décrivant un état dépassé doit être **archivé avec bannière**, jamais laissé en place comme s'il était courant.
- Le chiffre de tests canonique est dans `docs/METRICS_CANONICAL_SOURCE.md` ; ne pas propager d'autres chiffres.

---

## Documentation de référence

| Thème | Document |
|-------|----------|
| Installation client | [`docs/MANUEL_INSTALLATION_CLIENT.md`](./docs/MANUEL_INSTALLATION_CLIENT.md) · [`docs/GUIDE_RAPIDE_INSTALLATION.md`](./docs/GUIDE_RAPIDE_INSTALLATION.md) |
| Déploiement entreprise | [`docs/GUIDE_DEPLOIEMENT_ENTREPRISE.md`](./docs/GUIDE_DEPLOIEMENT_ENTREPRISE.md) · [`deploy/RUNBOOK.md`](./deploy/RUNBOOK.md) |
| Architecture (générique) | [`docs/architecture.md`](./docs/architecture.md) |
| Chemin critique & délégation | [`docs/audit/critical_request_path_map.md`](./docs/audit/critical_request_path_map.md) · [`docs/architecture/EVIDENCE_DELEGATION_ARCHITECTURE_VERIFIED.md`](./docs/architecture/EVIDENCE_DELEGATION_ARCHITECTURE_VERIFIED.md) |
| Doctrine sortie critique | [`docs/adr/ADR-010-critical-output-doctrine.md`](./docs/adr/ADR-010-critical-output-doctrine.md) |
| Remédiation chemin critique | [`docs/audit/critical_path_remediation_report.md`](./docs/audit/critical_path_remediation_report.md) · [`docs/audit/critical_path_hostile_audit.md`](./docs/audit/critical_path_hostile_audit.md) |
| ADRs | [`docs/adr/`](./docs/adr/) (ADR-006 → ADR-010) |
| Onboarding | [`docs/DEVELOPER_ONBOARDING_ARCHITECTURE_GUIDE.md`](./docs/DEVELOPER_ONBOARDING_ARCHITECTURE_GUIDE.md) · [`docs/missions/MISSION_AYA_01_cartographie_et_validation_e2e.md`](./docs/missions/MISSION_AYA_01_cartographie_et_validation_e2e.md) |
| Index des documents (carte) | [`docs/audit/PROJECT_AUDIT_NOTES.md`](./docs/audit/PROJECT_AUDIT_NOTES.md) |
| Métriques (source canonique) | [`docs/METRICS_CANONICAL_SOURCE.md`](./docs/METRICS_CANONICAL_SOURCE.md) |

---

## Documents archivés / historiques

Les documents obsolètes ou datés sont regroupés et signalés par bannière dans :

- [`docs/archive/`](./docs/archive/) — index complet et raisons d'archivage.
  - `docs/archive/obsolete/` — contradictoires avec le code actuel (à ne plus utiliser).
  - `docs/archive/historical/` — datés/corrects à l'époque, conservés pour traçabilité.

Rapport de nettoyage : [`docs/audit/documentation_cleanup_report_2026-05-31.md`](./docs/audit/documentation_cleanup_report_2026-05-31.md).

---

## Pour les auditeurs / commissaire aux apports

- **État actuel** : ce README, les ADRs (`docs/adr/`), la cartographie du chemin critique (`docs/audit/`), et la source canonique de métriques (`docs/METRICS_CANONICAL_SOURCE.md`).
- **Valorisation / due diligence** : [`docs/DOSSIER_COMMISSAIRE_APPORTS_EVIDENCE.md`](./docs/DOSSIER_COMMISSAIRE_APPORTS_EVIDENCE.md), [`docs/PACK_RDV_COMMISSAIRE_APPORTS.md`](./docs/PACK_RDV_COMMISSAIRE_APPORTS.md), [`docs/RAPPORT_TECHNIQUE_VALORISATION_EVIDENCE.md`](./docs/RAPPORT_TECHNIQUE_VALORISATION_EVIDENCE.md), dossier [`audit-hostile-valorisation/`](./audit-hostile-valorisation/).
- **Historique de conception** : `docs/archive/historical/` (snapshots datés, ne reflètent pas l'état courant).
- **Règle de lecture** : ne jamais confondre un document **archivé** (historique) avec l'**état actuel**. En cas de divergence, le code et les ADRs les plus récents font foi.

---

## Licence

Projet sous licence propriétaire **KOREV AI** — voir [LICENSE](./LICENSE). Composants open-source : [legal/THIRD_PARTY_NOTICES.txt](./legal/THIRD_PARTY_NOTICES.txt).

<div align="center">

**KOREV Evidence** — Développé par **KOREV AI** · contact : amine.mohamed@korev-ai.com

</div>
