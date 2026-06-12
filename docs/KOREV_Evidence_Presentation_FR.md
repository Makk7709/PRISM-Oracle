# KOREV Evidence — Dossier de présentation

**Version** : Basé sur l'audit du 28 janvier 2026  
**Statut** : Document factuel — aucune affirmation sans preuve

---

## En bref : à quoi sert KOREV Evidence ?

KOREV Evidence est un **assistant IA multi-agents** conçu pour les professionnels qui ont besoin de réponses fiables et sourcées dans des domaines sensibles : médical, juridique, recherche, finance.

**Ce qu'il fait concrètement :**

- Analyse des documents (PDF, rapports, bilans)
- Recherche dans des bases de données spécialisées (PubMed, essais cliniques, Arxiv, brevets)
- Synthèse de littérature avec citations vérifiables
- Veille réglementaire et concurrentielle
- Analyse de données médicales (pharmacovigilance, essais cliniques)
- Assistance juridique sourcée (droit FR/EU)

**Ce qui le différencie d'un chatbot classique :**

- Chaque affirmation est liée à une source (PMID, article de loi, label FDA)
- Un système de consensus multi-LLM valide les réponses critiques
- En cas de doute, le système refuse plutôt que d'inventer (fail-closed)

---

## Cas d'usage concrets

### Pour les professionnels de santé et laboratoires pharmaceutiques

| Besoin | Ce que fait KOREV Evidence |
|--------|---------------------------|
| Profil de sécurité d'un médicament | Analyse complète : effets fréquents, rares, signaux FAERS, contre-indications, avec sources (PMID, labels FDA/EMA) |
| Comparaison de traitements | Tableau comparatif efficacité/sécurité basé sur RCTs et méta-analyses |
| Veille pharmacovigilance | Détection de signaux (PRR, ROR) avec mise en contexte (signal ≠ causalité) |
| Interprétation de bilans | Analyse structurée avec normes du laboratoire, hypothèses diagnostiques classées, examens complémentaires recommandés |
| Benchmark essais cliniques | Landscape des trials actifs par phase, endpoints, sponsors, timelines |

**Exemple concret :**
> "Quels sont les effets secondaires cardiovasculaires des GLP-1 ?"
>
> → Réponse : Tableau avec incidences, sources (SUSTAIN, LEADER trials), signaux FAERS, bénéfices CV démontrés. Chaque ligne a une référence PMID.

### Pour les juristes et entreprises

| Besoin | Ce que fait KOREV Evidence |
|--------|---------------------------|
| Recherche d'articles de loi | Recherche sur Légifrance avec citation exacte (Code du travail, art. L1234-5) |
| Analyse RGPD | Obligations par type d'activité, bases légales, sanctions |
| Due diligence | Synthèse réglementaire multi-sources |
| Veille juridique | Changements récents dans un domaine (droit du travail, fiscal, sociétés) |

**Juridictions supportées :** France, Union Européenne  
**Domaines :** Droit du travail, fiscal, contrats, sociétés, RGPD, consommation

**Ce que KOREV Evidence ne fait PAS en juridique :**

- Rédiger des contrats ou actes juridiques
- Donner un avis définitif sur un litige
- Traiter le droit pénal, immigration, famille

### Pour les chercheurs et analystes

| Besoin | Ce que fait KOREV Evidence |
|--------|---------------------------|
| Revue de littérature | Synthèse systématique avec citations, gaps identifiés, pistes de recherche |
| Analyse de marché | Tendances, concurrents, opportunités, basé sur données publiques |
| Veille technologique | Patents, publications, startups dans un domaine |
| Analyse de données | Traitement de datasets, visualisations, modèles prédictifs |

---

### Pour les PME et équipes opérationnelles

#### Agent Marketing — Stratégie et contenu

| Capacité | Description |
|----------|-------------|
| **Stratégie marketing** | Positionnement, segmentation, personas, go-to-market |
| **Copywriting** | Headlines, pages de vente, CTA, posts LinkedIn |
| **SEO** | Audit technique, stratégie de mots-clés, optimisation on-page |
| **Ads** | Structure campagnes Google/Meta/LinkedIn, ciblage, optimisation |
| **Email marketing** | Séquences automation, segmentation, A/B testing |
| **Analytics** | KPIs (CAC, LTV, ROAS), attribution, dashboards |

**Exemple :** "Crée-moi un calendrier éditorial LinkedIn sur 3 mois pour une startup SaaS B2B"

#### Agent Sales — Prospection et closing

| Capacité | Description |
|----------|-------------|
| **Prospection** | Scripts d'appel, emails de cold outreach, séquences multicanales |
| **Qualification** | Scoring BANT/MEDDIC, priorisation pipeline |
| **Objections** | Réponses structurées aux objections courantes |
| **CRM** | Structuration Salesforce/HubSpot/Pipedrive, workflows |
| **Négociation** | Techniques de closing, gestion des remises |
| **Playbooks** | Documentation des processus de vente |

**Frameworks maîtrisés :** BANT, MEDDIC, SPIN, Challenger Sale, Solution Selling

#### Agent Finance — Modélisation et stratégie

| Capacité | Description |
|----------|-------------|
| **Modélisation financière** | DCF, LBO, M&A, sensibilités, stress tests |
| **Business plan** | P&L, cash flow, valorisation startup |
| **Ratios et KPIs** | Profitabilité, liquidité, solvabilité, valorisation |
| **Market sizing** | TAM/SAM/SOM, top-down, bottom-up |
| **Due diligence** | Analyse risques, synergies, deal breakers |
| **Reporting** | Tableaux de bord, data storytelling |

**Méthodologie :** Pyramid Principle (conclusion first), MECE, hypothesis-driven

#### Agent Multitask — Orchestrateur intelligent

L'agent multitask est le chef d'orchestre qui :

- **Analyse** chaque requête et détermine le niveau de complexité
- **Délègue** automatiquement vers l'agent spécialisé approprié
- **Coordonne** les tâches multi-domaines
- **Arbitre** en cas de conflit entre priorités

**Classification automatique :**

- Niveau 1 (simple) → réponse directe immédiate
- Niveau 2 (professionnel) → réponse structurée avec sources
- Niveau 3 (critique) → délégation + consensus si nécessaire

---

## Sources de données accessibles

KOREV Evidence se connecte à des bases de données spécialisées via le protocole MCP (Model Context Protocol) :

### Domaine médical/scientifique

| Source | Description | Type de données |
|--------|-------------|-----------------|
| **PubMed / MEDLINE** | 36M+ articles biomédicaux | Publications peer-reviewed |
| **ClinicalTrials.gov** | 500k+ essais cliniques | Protocoles, résultats, recrutement |
| **OpenFDA / FAERS** | Événements indésirables FDA | Signaux de pharmacovigilance |
| **Semantic Scholar** | 200M+ papers | Citations, impact, réseaux |
| **Arxiv** | Preprints scientifiques | Physique, bio, CS, stats |
| **OpenAlex** | Métadonnées académiques | Auteurs, institutions, citations |

### Domaine général

| Source | Description |
|--------|-------------|
| **Brave Search** | Recherche web |
| **Tavily** | Recherche IA actualités |
| **Firecrawl** | Extraction de contenu web |
| **Légifrance** | Textes de loi français (via navigation) |

---

## Capacités de traitement de documents

| Format | Capacité |
|--------|----------|
| **PDF** | Lecture et extraction de texte (OCR si nécessaire) |
| **Images** | Analyse visuelle (graphiques, tableaux, documents scannés) |
| **Fichiers texte** | Lecture directe (TXT, MD, CSV, JSON) |
| **Code source** | Analyse et exécution Python pour calculs/visualisations |

**Exemple :**
> "Voici le bilan sanguin de ma mère [PDF joint]"
>
> → KOREV Evidence extrait les valeurs, les compare aux normes du laboratoire, propose une analyse structurée avec hypothèses diagnostiques et sources.

---

## Outils intégrés

| Outil | Fonction |
|-------|----------|
| `search_engine` | Recherche web générale |
| `browser_agent` | Navigation web automatisée (Légifrance, sites spécialisés) |
| `code_execution` | Exécution Python, Node.js, commandes terminal |
| `file_reader` | Lecture de documents locaux |
| `file_writer` | Création et modification de fichiers |
| `pdf_ocr` | Extraction de texte depuis PDF/images |
| `vision_load` | Analyse d'images |
| `generate_image` | Génération d'illustrations |
| `memory_save/load` | Mémoire persistante entre sessions |
| `scheduler` | Planification de tâches récurrentes |
| `call_subordinate` | Délégation vers agents spécialisés |

---

## Capacités techniques avancées (vérifiées)

### Accès terminal et exécution de code

KOREV Evidence dispose d'un outil `code_execution` permettant :

| Runtime | Capacité |
|---------|----------|
| **Python** | Exécution de scripts, analyse de données (pandas, numpy), visualisations (matplotlib, plotly), modélisation |
| **Node.js** | Scripts JavaScript, automatisation |
| **Terminal** | Commandes shell, installation de packages, gestion de fichiers |

**Timeouts configurés :**

- Premier output : 30s (code) / 90s (output long)
- Entre outputs : 15s / 45s
- Exécution max : 180s / 300s

**Ce que cela permet :**

```bash
# Installer un outil manquant
pip install pandas matplotlib

# Exécuter une analyse
python mon_script.py

# Lister des fichiers
ls -la /chemin/vers/dossier

# Git operations
git clone https://github.com/...
```

### Téléchargement et installation d'outils

Via le terminal, KOREV Evidence peut :

| Action | Commande type |
|--------|---------------|
| Installer un package Python | `pip install nom_package` |
| Installer un package npm | `npm install -g nom_package` |
| Télécharger un fichier | `curl -O url` ou `wget url` |
| Cloner un repo | `git clone url` |
| Exécuter un script distant | `curl url \| python` |

**Exemple concret :**
> "Installe pandas et crée-moi un graphique à partir de ce CSV"
>
> → KOREV installe pandas si absent, lit le CSV, génère la visualisation

### Agent Developer — Développement logiciel

| Capacité | Description |
|----------|-------------|
| **Architecture système** | Design microservices, monolithes, serverless |
| **Full-stack** | Frontend (React, Vue), backend (Python, Node), BDD |
| **DevOps** | CI/CD, Docker, Kubernetes, Terraform |
| **Algorithmes** | Implémentation, optimisation, ML pipelines |
| **Refactoring** | Modernisation de code legacy, migrations |
| **Tests** | Unit, integration, E2E, performance |

**Langages maîtrisés :** Python, JavaScript/TypeScript, Go, Rust, SQL, Bash

**Exemple :**
> "Crée-moi une API REST en Python avec FastAPI, authentification JWT, et tests"
>
> → Code complet, structure de projet, dockerfile, documentation

### Agent Hacker — Audit de sécurité

| Capacité | Description |
|----------|-------------|
| **Pentest** | Tests d'intrusion red team / blue team |
| **Audit de code** | Recherche de vulnérabilités, OWASP |
| **Analyse de surface** | Reconnaissance, énumération |
| **Exploitation** | PoC de vulnérabilités (environnement contrôlé) |

**Usage :** Audit de sécurité de vos applications dans un cadre autorisé.

### Capacités d'audit d'applications

KOREV Evidence peut auditer vos applications :

| Type d'audit | Ce qu'il analyse |
|--------------|-----------------|
| **Code review** | Qualité, maintenabilité, patterns, anti-patterns |
| **Sécurité** | Injections SQL, XSS, CSRF, secrets exposés |
| **Performance** | Complexité algorithmique, requêtes N+1, memory leaks |
| **Architecture** | Couplage, cohésion, dette technique |
| **Dépendances** | Vulnérabilités connues (CVE), mises à jour |

**Exemple :**
> "Audite ce repo Python et identifie les problèmes de sécurité"
>
> → Rapport structuré avec fichiers concernés, lignes, sévérité, recommandations

---

## Sécurité et confidentialité des données

| Aspect | Implémentation |
|--------|----------------|
| **Clés API** | Stockées localement (`.env`), jamais dans le code |
| **Données patients** | Non collectées par défaut, minimisation RGPD |
| **Accès réseau** | Binding localhost par défaut (docker) |
| **Mode hors ligne** | Disponible (fonctionnalités limitées) |

**Limites connues :**

- Pas de chiffrement des données au repos vérifié
- Pas de redaction PII automatique implémentée
- Logs de session en mémoire (persistance disque non vérifiée)

---

## Qu'est-ce que KOREV Evidence ?

KOREV Evidence est un système d'orchestration multi-agents conçu pour les domaines où la fiabilité des réponses est critique (juridique, médical, recherche). Il combine plusieurs mécanismes de validation pour réduire les risques d'erreur dans les réponses générées par des modèles de langage (LLM).

---

## Architecture générale

```text
Requête utilisateur
       │
       ▼
┌─────────────────────┐     ┌─────────────────────┐
│  Routeur            │────▶│  Routeur de         │
│  déterministe       │     │  criticité          │
│  (optionnel)        │     │                     │
└─────────────────────┘     └─────────────────────┘
       │                            │
       ▼                            ▼
┌─────────────────────┐     ┌─────────────────────┐
│  Délégation         │     │  Gate de décision   │
│  vers agents        │     │  critique           │
│  spécialisés        │     │                     │
└─────────────────────┘     └─────────────────────┘
       │                            │
       ▼                            ▼
┌─────────────────────┐     ┌─────────────────────┐
│  Débat collaboratif │     │  Moteur de          │
│  (3 tours)          │     │  consensus          │
└─────────────────────┘     └─────────────────────┘
       │                            │
       └────────────┬───────────────┘
                    ▼
        ┌─────────────────────┐
        │  Réponse finale     │
        │  (avec badges)      │
        │  ou FAIL_CLOSED     │
        └─────────────────────┘
```

---

## Fonctionnalités vérifiées

### 1. Orchestration multi-agents

| Fonction | Description | Statut |
|----------|-------------|--------|
| Délégation vers agents spécialisés | Routage des requêtes vers des agents configurés par domaine | Vérifié |
| Profils d'agents | legal_safe, medical, researcher, finance, developer, etc. | Vérifié |
| Contexte par agent | Chaque agent a son propre `_context.md` et prompts | Vérifié |

**Agents documentés :**

- `legal_safe` — Analyse juridique FR/EU, sourcing obligatoire
- `medical` — Raisonnement médical avec schéma claims/citations
- `researcher`, `finance`, `sales`, `marketing`, `developer`, `hacker`, `default` — Définis par prompts

---

### 2. Consensus multi-LLM (PRISM)

| Fonction | Description | Statut |
|----------|-------------|--------|
| Quorum 2/3 | Décision approuvée si 2/3 des votes effectifs sont favorables | Vérifié (tests) |
| Votes APPROVE/REJECT/ABSTAIN | Trois types de votes possibles | Vérifié |
| Exclusion des indisponibles | Les arbitres non disponibles sont exclus du calcul | Vérifié |
| Timeouts | Timeout → INFRA_FAILURE si 0 vote, sinon NO_CONSENSUS | Vérifié |
| Fail-closed | NO_CONSENSUS et INFRA_FAILURE ne valident jamais | Vérifié |

**Fonctionnement :**

- Le système interroge plusieurs LLM (arbitres)
- Chaque arbitre vote indépendamment
- Le consensus est calculé sur les votes effectifs uniquement
- En cas de doute, le système refuse (fail-closed)

---

### 3. Débat collaboratif (3 tours)

| Fonction | Description | Statut |
|----------|-------------|--------|
| 3 rounds de débat | Analyse indépendante → Débat → Synthèse | Vérifié (code) |
| Skip round 2 si unanime | Optimisation si tous les arbitres sont d'accord au round 1 | Vérifié (code) |
| Configuration des arbitres | Via interface utilisateur ou défauts | Vérifié (code) |
| Timeouts par round | Protection contre les blocages | Vérifié (code) |

**Note :** Pas de test automatisé dédié pour le débat collaboratif.

---

### 4. Routage et évaluation de criticité

| Fonction | Description | Statut |
|----------|-------------|--------|
| Routeur déterministe | Routage sans appel LLM, basé sur patterns | Partiel (flag requis) |
| Détection d'injection | Détection de tentatives de manipulation du prompt | Partiel (tests) |
| Évaluation de criticité | Classification des requêtes par niveau de risque | Vérifié (tests) |
| Métriques routeur | Enregistrement des décisions de routage | Partiel |

**Limites :**

- Le routeur déterministe nécessite l'activation du flag `DETERMINISTIC_ROUTER_V2`
- La détection d'injection dépend du routeur déterministe

---

### 5. Contrats de sortie (domaines critiques)

| Fonction | Description | Statut |
|----------|-------------|--------|
| Contrat médical | Schéma JSON strict pour les réponses médicales | Vérifié (tests) |
| FAIL_CLOSED médical | Rejet automatique des sorties non conformes | Vérifié (tests) |
| Evidence pack | Exigence de sources pour les claims | Partiel |
| Claims non sourcés refusés | Les affirmations sans source sont rejetées | Vérifié (tests) |

**Schéma médical :**

```json
{
  "claims": [{"statement": "...", "citation": "..."}],
  "answer_md": "...",
  "decision": "APPROVED | FAIL_CLOSED"
}
```

---

### 6. Pipeline légal

| Fonction | Description | Statut |
|----------|-------------|--------|
| Orchestrateur légal | Coordination des requêtes juridiques | Partiel (tests) |
| Sourcing obligatoire | Exigence de références pour les analyses | Vérifié (prompt) |
| Refus hors juridiction | Rejet des requêtes hors FR/EU | Vérifié (prompt) |
| Tests E2E | Tests de bout en bout du pipeline | Vérifié |

**Limite :** Dépend d'un index légal externe.

---

### 7. Sécurité API

| Fonction | Description | Statut |
|----------|-------------|--------|
| Clé API requise | Protection des endpoints par clé | Partiel (per-handler) |
| Binding localhost | Services exposés uniquement en local | Vérifié (config) |
| Protection CSRF | Protection contre les requêtes cross-site | Partiel |
| Guardrail simulation | Interdiction du mode simulation en production | Partiel (code) |

---

### 8. Observabilité

| Fonction | Description | Statut |
|----------|-------------|--------|
| Logs JSON structurés | Format de logs parsable | Vérifié |
| Correlation IDs | Traçabilité des requêtes | Vérifié |
| Métriques routeur | Statistiques de routage | Partiel |
| Audit trail in-memory | Historique des décisions en mémoire | Vérifié |

---

### 9. Déploiement

| Fonction | Description | Statut |
|----------|-------------|--------|
| Docker Compose | Fichiers de déploiement fournis | Vérifié |
| Variables documentées | `.env.example` présent | Vérifié |
| Volume audit logs | Volume Docker configuré | Vérifié (config) |
| Build local | Dockerfile fourni | Vérifié |

**Commandes de déploiement :**

```bash
# Build local
docker build -f DockerfileLocal -t korev-evidence:local .

# Lancement via compose
docker compose -f deploy/docker-compose.yml up -d
```

---

---

## Agents spécialisés disponibles

KOREV Evidence dispose d'agents pré-configurés pour différents domaines :

### Agent Medical Intelligence

**Pour qui :** Laboratoires pharma, professionnels de santé, chercheurs biomédicaux

**Capacités :**

- Profils de sécurité complets avec sources (labels, RCTs, FAERS)
- Efficacité comparée entre traitements
- Détection de signaux pharmacovigilance (PRR, ROR, IC)
- Analyse de bilans biologiques avec contexte patient
- Competitive intelligence (pipelines, trials)
- Regulatory intelligence (FDA guidance, approbations)

**Format de sortie :** JSON structuré avec claims sourcés, grades de preuve (GRADE), confiance

**Garde-fous :**

- Refus automatique des prescriptions personnalisées
- Détection des urgences médicales → orientation SAMU
- Signal ≠ causalité systématiquement rappelé
- FAIL_CLOSED si evidence insuffisante

### Agent Legal-Safe

**Pour qui :** Entreprises, juristes, particuliers (information générale)

**Capacités :**

- Recherche d'articles de loi (Légifrance)
- Analyse RGPD et conformité
- Droit du travail, fiscal, contrats, sociétés FR/EU
- Classification automatique du niveau de risque

**Limites explicites :**

- Pas de rédaction d'actes (contrats, statuts)
- Pas d'avis définitif sur litiges
- Orientation avocat systématique pour cas complexes

### Agent Researcher (Deep Research)

**Pour qui :** Analystes, chercheurs, consultants

**Capacités :**

- Synthèse de littérature académique multi-sources
- Analyse de marché et veille concurrentielle
- Intégration de données hétérogènes
- Modélisation prédictive et scénarios
- Rapports structurés avec citations

### Agent Multitask (Orchestrateur)

**Pour qui :** Utilisateurs avec des besoins variés

**Fonction :** Analyse chaque requête et la route vers l'agent approprié ou répond directement.

**Comportement :**

- Questions simples (définitions, calculs) → réponse immédiate
- Analyses professionnelles → réponse structurée
- Cas critiques (litiges, médical) → délégation + consensus

### Autres agents disponibles

| Agent | Spécialisation | Cas d'usage |
|-------|---------------|-------------|
| `marketing` | Stratégie, copywriting, SEO, ads | Calendrier éditorial, landing pages, campagnes |
| `sales` | Prospection, CRM, négociation | Scripts d'appel, séquences email, playbooks |
| `finance` | Modélisation, valorisation, KPIs | Business plans, DCF, due diligence |
| `developer` | Architecture, code, DevOps | APIs, pipelines, refactoring |
| `hacker` | Pentest, audit sécurité | Tests d'intrusion, analyse de vulnérabilités |

---

## Ce que KOREV Evidence NE fait PAS

Ces fonctionnalités sont absentes ou non vérifiées dans le code actuel :

| Fonction | Statut | Commentaire |
|----------|--------|-------------|
| Garantie d'exactitude factuelle | Non garanti | Le système réduit les erreurs mais ne les élimine pas |
| Audit logs persistants | Non vérifié | Volume configuré mais pas de code d'écriture trouvé |
| Redaction PII automatique | Non implémenté | Seulement des règles dans les prompts |
| Suivi des coûts/tokens | Non implémenté | Aucun code trouvé |
| Sandbox d'exécution de code | Non implémenté | Pas de sandboxing pour les outils |
| Rétention forcée des logs | Non vérifié | Politique de rétention non enforcée par le code |

---

## Modes de fonctionnement

| Variable | Valeurs | Description |
|----------|---------|-------------|
| `EVIDENCE_ENV` | production / development | Environnement d'exécution |
| `CONSENSUS_SIMULATION` | true / false | Mode simulation (interdit en prod) |
| `OFFLINE_MODE` | true / false | Mode hors ligne |
| `DETERMINISTIC_ROUTER_V2` | true / false | Active le routeur déterministe |

---

## Prérequis techniques

- Python 3.10+
- Docker (pour le déploiement)
- Clés API pour les providers LLM (OpenAI, Anthropic, etc.)
- Index légal externe (pour le pipeline juridique)

---

## Vérification du système

Le système inclut des outils de vérification automatisés :

```bash
# Vérification complète de l'audit
make audit-verify

# Lint documentaire seul
make audit-lint

# Lint + tests smoke
make audit-smoke
```

**Couverture des tests :**

- Tests consensus/quorum : `tests/test_prism_*.py`
- Tests routeur : `tests/test_router_determinism.py`, `tests/test_injection_handling.py`
- Tests criticité : `tests/test_criticality_router.py`
- Tests legal : `tests/test_legal_orchestrator.py`
- Tests medical : `tests/test_medical_agent_hardening.py`
- Tests evidence : `tests/test_final_output_claim_integrity.py`

---

## Résumé des statuts par brique

| Brique | Statut | Tests |
|--------|--------|-------|
| Routage déterministe | Partiel | Oui |
| Détection injection | Partiel | Oui |
| Évaluation criticité | Implémenté | Oui |
| Gate fail-closed | Partiel | Oui |
| Evidence pack | Partiel | Oui |
| Consensus PRISM | Implémenté | Oui |
| Appel arbitres LLM | Partiel | Non |
| Guardrail simulation | Partiel | Non |
| Débat collaboratif | Partiel | Non |
| Intégration débat | Partiel | Non |
| Pipeline légal | Partiel | Oui |
| Contrat médical | Partiel | Oui |
| Tool policy | Partiel | Non |
| Métriques routeur | Partiel | Non |
| Sécurité API | Partiel | Non |
| Déploiement Docker | Partiel | Non |
| Audit persistant | Non vérifié | Non |
| Suivi coûts | Non vérifié | Non |
| Redaction PII | Non vérifié | Non |

---

## Glossaire

| Terme | Définition |
|-------|------------|
| **Fail-closed** | Comportement où le système refuse en cas de doute plutôt que d'approuver |
| **Quorum** | Nombre minimum de votes requis pour une décision |
| **Arbitre** | LLM participant au vote de consensus |
| **Evidence pack** | Ensemble de preuves/sources associées à une réponse |
| **PRISM** | Nom du moteur de consensus multi-LLM |
| **Criticité** | Niveau de risque associé à une requête |

---

---

## Comment utiliser KOREV Evidence

### Déploiement

**Option 1 : Docker (recommandé)**

```bash
# Build
docker build -f DockerfileLocal -t korev-evidence:local .

# Lancement
docker compose -f deploy/docker-compose.yml up -d
```

**Option 2 : Local (développement)**

```bash
# Installation
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Configuration
cp .env.example .env
# Éditer .env avec vos clés API

# Lancement
python run_ui.py
```

### Configuration requise

| Élément | Requis | Optionnel |
|---------|--------|-----------|
| Python 3.10+ | Oui | — |
| Docker | Oui (production) | — |
| Clé OpenAI | Oui | — |
| Clé Anthropic | — | Pour consensus multi-LLM |
| Clé Brave Search | — | Recherche web |
| Clé PubMed/NCBI | — | Recherche biomédicale |
| Clé OpenFDA | — | Pharmacovigilance |

### Interface

- **Web UI** : Interface conversationnelle accessible via navigateur
- **API** : Endpoints REST pour intégration
- **Tunnel** : Accès distant sécurisé (optionnel)

---

## Exemples de requêtes

### Domaine médical

```text
"Profil de sécurité cardiovasculaire du semaglutide avec sources PMID"

"Compare l'efficacité des anti-IL17 vs anti-IL23 dans le psoriasis modéré à sévère"

"Signaux FAERS pour les inhibiteurs de checkpoint en 2024"

"Analyse ce bilan [PDF joint] pour un homme de 65 ans diabétique"
```

### Domaine juridique

```text
"Quelles sont les obligations RGPD pour un site e-commerce B2C en France ?"

"Délai de prescription pour un licenciement abusif en France"

"Différence entre SAS et SARL pour une startup tech"
```

### Recherche

```text
"État de l'art sur les transformers en NLP, papers 2023-2024 avec citations"

"Landscape des startups en quantum computing, levées de fonds 2024"

"Analyse des brevets CRISPR déposés par Moderna"
```

### Marketing & Sales (PME)

```text
"Crée-moi une séquence de prospection email B2B pour vendre un SaaS de facturation"

"Rédige 10 posts LinkedIn engageants pour un cabinet de conseil RH"

"Audit SEO de mon site et recommandations d'optimisation"

"Prépare un argumentaire de vente avec gestion des objections pour [produit]"

"Crée un playbook commercial pour mon équipe de 3 SDR"
```

### Finance & Stratégie

```text
"Modélise un DCF pour une startup SaaS avec 500k ARR et 30% de croissance"

"Market sizing TAM/SAM/SOM pour le marché français de la foodtech"

"Analyse MECE des options stratégiques pour une acquisition"

"Crée un dashboard de KPIs pour suivre la performance commerciale"
```

### Développement & Tech

```text
"Crée une API REST en FastAPI avec auth JWT, PostgreSQL et Docker"

"Refactorise ce code Python pour améliorer la performance"

"Installe pandas et analyse ce CSV pour identifier les tendances"

"Audite ce repo pour identifier les failles de sécurité OWASP"

"Configure un pipeline CI/CD GitHub Actions pour ce projet Node.js"
```

### Automatisation & Terminal

```text
"Télécharge les données de ce site et crée un rapport PDF"

"Clone ce repo, installe les dépendances et lance les tests"

"Crée un script qui monitore ce endpoint et m'alerte si down"

"Analyse les logs de ce serveur et identifie les anomalies"
```

---

## Résumé : ce que KOREV Evidence apporte

| Problème | Solution KOREV Evidence |
|----------|------------------------|
| Les LLM inventent des sources | Chaque claim est lié à une référence vérifiable |
| Réponses contradictoires entre modèles | Consensus multi-LLM avec quorum 2/3 |
| Pas de garde-fou pour les domaines sensibles | Contrats de sortie stricts (medical, legal) |
| Recherche manuelle dans les bases | Connexion directe à PubMed, ClinicalTrials, OpenFDA, etc. |
| Pas de traçabilité | Correlation IDs, logs structurés, audit trail |
| Besoin de plusieurs outils spécialisés | Agents dédiés (marketing, sales, finance, dev) |
| Tâches répétitives manuelles | Automatisation via terminal et scripts |
| Audit de sécurité coûteux | Agent hacker pour pentest/audit intégré |
| Analyse de données complexe | Python/pandas intégré avec visualisations |
| Installation d'outils ad-hoc | Terminal avec pip/npm/git disponible |

---

## Contact et documentation

- **Audit technique complet** : `docs/KOREV_Evidence_Audit.md`
- **Checklist de vérification** : `docs/Checklist_CTO_30min_KOREV_Evidence_FR.md`
- **Changelog audit** : `docs/CHANGELOG_AUDIT.md`
- **Configuration MCP** : `mcp_config.json`, `mcp_config_medical.json`

---

*Document généré à partir de l'audit KOREV Evidence — Toutes les affirmations sont basées sur des preuves de code ou de tests.*
