<div align="center">

# `Korev Evidence`

### Système Cognitif Autonome de Nouvelle Génération

[![Version](https://img.shields.io/badge/Version-3.0-0A192F?style=for-the-badge)](https://github.com/Makk7709/PRISM-Evidence)
[![License](https://img.shields.io/badge/License-Proprietary-red?style=for-the-badge)](./LICENSE)
[![Tests](https://img.shields.io/badge/Tests-3739%20Collected-green?style=for-the-badge)](#tests)

**Plateforme multi-agents d'IA de confiance pour professions réglementées — juridique, médical, finance, stratégie, cybersécurité.**

[Installation](#installation) •
[Fonctionnalités](#fonctionnalités-clés) •
[Architecture](#architecture) •
[Documentation](./docs/)

</div>

---

## Présentation

Korev Evidence est une plateforme multi-agents d'IA de confiance conçue pour les professions réglementées (avocats, médecins, chercheurs, consultants, finance). Elle combine :

- **12 Agents Spécialisés** — Juridique, médical, rédaction contractuelle, stratégie, finance, cybersécurité, recherche, développement, marketing, ventes
- **Consensus Multi-LLM** — Validation croisée en 3 rounds pour les réponses critiques (quorum 2/3)
- **Pipelines Métier** — Juridique (FTS5 Légifrance), médical (PRISM + FAERS), stratégique (4 agents + consolidation), contrats (Act Leak Guard fail-closed)
- **Multi-Tenant Strict** — Isolation par organisation avec rôles OWNER/MEMBER
- **Raisonnement Métacognitif** — Auto-évaluation et escalade intelligente (non-diluable)
- **Recherche Académique** — 8+ serveurs MCP (ArXiv, PubMed, Semantic Scholar, EUR-Lex, OpenAlex, Crossref, Tavily, Brave)
- **Protocole A2A** — Communication agent-to-agent via FastA2A (client + serveur)
- **Extraction PDF Robuste** — Pipeline avec circuit breakers, timeouts stricts, OCR Tesseract
- **Speech** — Transcription (Whisper) + synthèse vocale (Kokoro TTS)
- **3739 Tests** — 158 fichiers de tests, CI/CD GitHub Actions (3 pipelines)

---

## Fonctionnalités Clés

### 1. Moteur de Raisonnement (ReasoningEngine)

Système de métacognition avec politique d'escalade non-diluable :

| Niveau | Seuil | Action |
|--------|-------|--------|
| `SAFE_REFUSE` | confidence < 0.35 | Refuse poliment, explique pourquoi |
| `HUMAN_REVIEW` | confidence < 0.35 | Demande validation humaine |
| `ASK_CLARIFY` | confidence < 0.5 | Pose des questions ciblées |
| `NONE` | confidence ≥ 0.5 | Exécution autonome |

**Invariants garantis :**
- Monotonie : les signaux ne peuvent que durcir l'escalade
- Non-dilution : aucune logique ne peut abaisser le niveau d'escalade
- No-PII : aucune donnée utilisateur dans les logs/exceptions

### 2. Recherche Académique Intégrée

5 serveurs MCP installés pour la recherche scientifique :

| Serveur | Usage | Exemples |
|---------|-------|----------|
| **ArXiv** | Preprints, ML/AI, Physics | "dernières publications sur transformers" |
| **Semantic Scholar** | Citations, auteurs | "articles de Yann LeCun" |
| **OpenAlex** | Métriques, institutions | "publications MIT 2024" |
| **Crossref** | DOI, métadonnées | "10.1038/nature12373" |
| **EUR-Lex** | Droit européen | "RGPD article 17" |

**Politique intelligente de sélection :**
```
Query: "RGPD droit à l'oubli"
→ Intent détecté: EU_LEGISLATION
→ Outils autorisés: [eurlex_search] (primary)
→ Fallback: [openalex_search, crossref_search]
```

### 3. Extraction PDF Production-Ready

Pipeline robuste avec protection contre les blocages :

- **Circuit Breaker** — Désactive automatiquement les moteurs défaillants
- **Timeouts stricts** — Total: 25s, Par page: 4s, Par moteur: 6s
- **Reconstruction géométrique** — Tables extraites sans dépendances lourdes
- **Fallback automatique** — PyMuPDF → Camelot → Tabula → Géométrie

```python
# Configuration par défaut (sécurisée)
config = get_default_config()
# - Tous les moteurs externes OFF
# - OCR OFF (activable si nécessaire)
# - Logs sans contenu utilisateur
```

### 4. Deterministic Router v2

Routage multi-intent policy-driven sans jugement LLM :

| Feature | Description |
|---------|-------------|
| **Multi-Intent** | Détection simultanée finance + legal + sales |
| **Board-Level** | 40+ keywords M&A, IPO, LBO, COMEX |
| **Anti-Injection** | Patterns FR + EN, blocage high-stakes |
| **Observability** | Métriques divergence, latency, would_block |

**Modes d'activation :**
```bash
DETERMINISTIC_ROUTER_V2=1  # Audit-only (logs, pas de changement)
DETERMINISTIC_ROUTER_V2=2  # Enforcement soft (bloque high-stakes)
```

**High-stakes = board_level OU legal/medical OU (strength≥0.65 + finance/legal)**

### 5. Interface Korev Evidence

Design system personnalisé avec typographie Playfair Display :

- **Welcome Screen** — Page d'accueil brandée
- **Chat Interface** — Bulles de conversation élégantes
- **Dark/Light Mode** — Thème persistant
- **Multilingual** — FR, EN (auto-détection)

---

## Architecture

```
korev-evidence/
├── python/
│   ├── helpers/
│   │   ├── metacognition.py      # ReasoningEngine
│   │   ├── research_tool_policy.py # Politique outils recherche
│   │   ├── research_executor.py   # Exécution avec fallback
│   │   ├── router/               # Deterministic Router v2
│   │   │   ├── router.py         # Moteur de routage
│   │   │   ├── policy.py         # Keywords, thresholds, rules
│   │   │   ├── routing_contract.py # Contrats stricts
│   │   │   ├── metrics.py        # Observabilité
│   │   │   └── judge.py          # Détection contradictions
│   │   └── pdf_extraction/        # Pipeline PDF
│   │       ├── config.py          # Configuration centralisée
│   │       ├── pipeline.py        # Extraction avec timeouts
│   │       └── types.py           # Types de données
│   └── tools/                     # Outils de l'agent
├── webui/                         # Interface React/Alpine
├── prompts/                       # System prompts personnalisables
├── conf/
│   └── model_providers.yaml       # Configuration LLM providers
├── tests/                         # 346 tests unitaires
└── scripts/
    ├── install-windows.bat        # Installation Windows
    ├── install-mac.sh             # Installation Mac/Linux
    └── router_prod_validation.py  # Validation production Router
```

---

## Installation

### Prérequis

- **Python 3.11+**
- **Clé API OpenRouter** (pour les LLMs)
- Optionnel : Clé OpenAI (pour génération d'images DALL-E)

### Installation Rapide

#### Windows

```batch
# 1. Copier le dossier korev-evidence
# 2. Double-cliquer sur:
scripts\install-windows.bat
```

#### Mac / Linux

```bash
cd korev-evidence/scripts
chmod +x install-mac.sh
./install-mac.sh
```

### Configuration

1. Éditer `.env` :
```env
API_KEY_OPENROUTER=sk-or-votre-cle
WEB_UI_PORT=5050
```

2. Ouvrir http://localhost:5050

### Lancement Manuel

```bash
# Activer l'environnement virtuel
source venv/bin/activate  # Mac/Linux
venv\Scripts\activate     # Windows

# Lancer Evidence
python run_ui.py
```

---

## Configuration des Modèles

Evidence utilise **OpenRouter** comme provider principal, donnant accès à tous les modèles :

| Modèle | Usage recommandé |
|--------|------------------|
| `openai/gpt-4o` | Chat principal, tâches complexes |
| `openai/gpt-4.1-mini` | Utilitaire, tâches rapides |
| `anthropic/claude-3.5-sonnet` | Raisonnement, code |
| `google/gemini-2.0-flash` | Multimodal, vision |

**Changer de modèle :** Paramètres → Agent Settings → Chat Model

---

## Tests

346 tests unitaires couvrant les composants critiques :

```bash
# Lancer tous les tests
python -m pytest tests/ -v

# Tests spécifiques
python -m pytest tests/test_metacognition_policy.py      # 42 tests
python -m pytest tests/test_research_tool_policy.py      # 27 tests
python -m pytest tests/test_router*.py                   # 204 tests (Router v2)
python -m pytest tests/test_pdf_extraction*.py           # 43 tests

# Validation production (pas pytest)
PYTHONPATH=. DETERMINISTIC_ROUTER_V2=2 python scripts/router_prod_validation.py
```

| Suite | Tests | Couverture |
|-------|-------|------------|
| **Deterministic Router v2** | 204 | Multi-intent, injection, board-level, determinism |
| Metacognition Policy | 42 | Escalade, monotonie, no-PII |
| Research Tool Policy | 27 | Intent detection, validation |
| Research Executor | 30 | Fallback, logging, integration |
| PDF Extraction | 43 | Timeouts, circuit breaker |

---

## Exemples d'Utilisation

### Recherche Académique
```
"Trouve les 5 derniers articles sur les Large Language Models publiés sur ArXiv"
"Quelles sont les citations de l'article DOI 10.1038/nature12373 ?"
"Résume le règlement RGPD article 17 sur le droit à l'effacement"
```

### Analyse de Documents
```
"Extrais les tableaux de ce rapport PDF et convertis-les en CSV"
"Analyse ce contrat et identifie les clauses de responsabilité"
```

### Développement
```
"Crée une API REST avec FastAPI pour gérer des utilisateurs"
"Refactorise ce code Python pour suivre les bonnes pratiques"
```

### Finance & Business
```
"Analyse les KPIs de ce trimestre et génère un rapport"
"Compare ces deux offres commerciales"
```

---

## Documentation

| Document | Description |
|----------|-------------|
| [Manuel Installation Client](./docs/MANUEL_INSTALLATION_CLIENT.md) | Guide complet d'installation |
| [Guide Rapide](./docs/GUIDE_RAPIDE_INSTALLATION.md) | Référence rapide 1 page |
| [Architecture](./docs/architecture.md) | Design système |
| [Extensibilité](./docs/extensibility.md) | Créer des outils/extensions |
| [Dépannage](./docs/troubleshooting.md) | Problèmes courants |

---

## Changelog

### v2.1.0 — Janvier 2026

#### Nouveautés
- **Deterministic Router v2** — Routage policy-driven sans LLM judgment
  - Multi-intent detection (finance + legal + sales simultanés)
  - 40+ keywords board-level (M&A, IPO, LBO, COMEX, due diligence)
  - Anti-injection FR + EN avec blocage high-stakes
  - Métriques: divergence_rate, would_block, latency
  - Enforcement soft: `DETERMINISTIC_ROUTER_V2=2`
- **204 tests Router** — Determinism, contract safety, injection, board-level
- **Production Reality Tests** — 4 tests réalité (enforcement, non-régression, volume, thread-safety)

#### Améliorations
- High-stakes élargi: board_level OR critical_intent OR strategic_signal
- Canonicalization unique partagée (router/metrics/logs)
- Error rate-limiting (60s cooldown)
- Log EXECUTION_ABORTED_BY_ROUTER explicite

### v2.0.0 — Janvier 2026

#### Nouveautés
- **ReasoningEngine** — Moteur de métacognition avec escalade non-diluable
- **Research MCP Servers** — 5 serveurs (ArXiv, Semantic Scholar, OpenAlex, Crossref, EUR-Lex)
- **Research Tool Policy** — Sélection intelligente d'outils par intent
- **PDF Extraction Pipeline** — Circuit breakers, timeouts stricts, reconstruction géométrique
- **Scripts Installation** — Windows (.bat) et Mac (.sh) prêts pour clients
- **Branding Korev Evidence** — Typographie Playfair Display, design complet

#### Améliorations
- Configuration simplifiée (OpenRouter uniquement requis)
- 346 tests unitaires couvrant les invariants critiques
- Logs sécurisés sans données utilisateur (No-PII)
- Documentation client complète (FR)

### v1.0.0 — Décembre 2025

- Rebranding initial Korev Evidence
- Mode Jour/Nuit avec persistance
- Profils métiers : Finance, Marketing, Sales
- Support OCR pour PDF scannés

---

## Licence

Ce projet est sous licence proprietaire KOREV AI. Voir [LICENSE](./LICENSE) pour les termes complets.

Les licences des composants open-source integres sont conservees dans [legal/THIRD_PARTY_NOTICES.txt](./legal/THIRD_PARTY_NOTICES.txt).

---

<div align="center">

**Korev Evidence** — Système Cognitif Autonome

Développé par **KOREV AI**

</div>
