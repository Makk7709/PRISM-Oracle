<div align="center">

# `Korev Evidence`

### Système Cognitif Autonome de Nouvelle Génération

[![Version](https://img.shields.io/badge/Version-2.0-0A192F?style=for-the-badge)](https://github.com/Makk7709/PRISM-Evidence)
[![License](https://img.shields.io/badge/License-MIT-blue?style=for-the-badge)](./LICENSE)
[![Tests](https://img.shields.io/badge/Tests-142%20Passed-green?style=for-the-badge)](#tests)

**Un assistant IA enterprise-grade avec raisonnement avancé, recherche académique intégrée et extraction de documents intelligente.**

[Installation](#installation) •
[Fonctionnalités](#fonctionnalités-clés) •
[Architecture](#architecture) •
[Documentation](./docs/)

</div>

---

## Présentation

Korev Evidence est un framework d'agent IA autonome conçu pour les professionnels exigeants. Il combine :

- **Raisonnement Métacognitif** — Auto-évaluation et escalade intelligente
- **Recherche Académique** — Accès à 5 bases de données scientifiques
- **Extraction PDF Robuste** — Pipeline avec circuit breakers et timeouts
- **Multi-Agents** — Coopération hiérarchique pour tâches complexes

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

### 4. Interface Korev Evidence

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
│   │   └── pdf_extraction/        # Pipeline PDF
│   │       ├── config.py          # Configuration centralisée
│   │       ├── pipeline.py        # Extraction avec timeouts
│   │       └── types.py           # Types de données
│   └── tools/                     # Outils de l'agent
├── webui/                         # Interface React/Alpine
├── prompts/                       # System prompts personnalisables
├── conf/
│   └── model_providers.yaml       # Configuration LLM providers
├── tests/                         # 142 tests unitaires
└── scripts/
    ├── install-windows.bat        # Installation Windows
    └── install-mac.sh             # Installation Mac/Linux
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

142 tests unitaires couvrant les composants critiques :

```bash
# Lancer tous les tests
python -m pytest tests/ -v

# Tests spécifiques
python -m pytest tests/test_metacognition_policy.py      # 42 tests
python -m pytest tests/test_research_tool_policy.py      # 27 tests
python -m pytest tests/test_research_executor.py         # 30 tests
python -m pytest tests/test_pdf_extraction_config.py     # 18 tests
python -m pytest tests/test_pdf_extraction_pipeline_timeouts.py  # 25 tests
```

| Suite | Tests | Couverture |
|-------|-------|------------|
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
- 142 tests unitaires couvrant les invariants critiques
- Logs sécurisés sans données utilisateur (No-PII)
- Documentation client complète (FR)

### v1.0.0 — Décembre 2025

- Rebranding initial Korev Evidence
- Mode Jour/Nuit avec persistance
- Profils métiers : Finance, Marketing, Sales
- Support OCR pour PDF scannés

---

## Licence

Ce projet est sous licence MIT. Voir [LICENSE](./LICENSE) pour plus de détails.

La licence MIT originale d'Agent Zero est respectée et conservée dans [legal/THIRD_PARTY_NOTICES.txt](./legal/THIRD_PARTY_NOTICES.txt).

---

<div align="center">

**Korev Evidence** — Système Cognitif Autonome

Développé par **KOREV AI**

</div>
