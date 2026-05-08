# Rapport Technique de Valorisation — KOREV Evidence

**Objet :** Inventaire technique des actifs logiciels propriétaires de la plateforme KOREV Evidence, dans le cadre d'une évaluation par un commissaire aux apports.

**Date :** 17 avril 2026 (mise a jour ; premiere version : 11 fevrier 2026 ; verification Git complementaire : 25 avril 2026)  
**Préparé par :** Amine Mohamed — sur la base de l'analyse du dépôt Git  
**Dépôt :** `KOREV_Oracle/KOREV_Oracle` (branche `main`, HEAD verifie : `7a7abd6a` au 25 avril 2026)

---

## 1. Résumé exécutif

KOREV Evidence est une plateforme d'agents IA de confiance, construite à partir d'un **fork** du projet open-source **Agent Zero** (licence MIT). Le présent rapport distingue précisément :

- **La base upstream Agent Zero** : développée par la communauté open-source (frdel/Jan Tomášek + contributeurs), de juin 2024 à janvier 2026.
- **Le travail propriétaire d'Amine Mohamed** : refonte, spécialisation, industrialisation et création de modules, du **15 janvier 2026** au **24 avril 2026** (développement actif continu, incluant les corrections posterieures au rapport du 17 avril).

### État du code avant le travail propriétaire (10 janvier 2026)

| Métrique | Agent Zero upstream (10 jan. 2026) | KOREV Evidence (17 avr. 2026) | Ajout net |
|----------|-----------------------------------|-------------------------------|-----------|
| Fichiers Python | 210 | 599 | +389 |
| Lignes Python | 28 403 | 186 865 | +158 462 |
| Total fichiers (dépôt) | 1 221 | 1 796 | +575 |
| Fichiers WebUI (hors vendor) | 182 | 166 | -16 (refonte/restructuration) |
| Lignes WebUI (hors vendor) | 30 643 | 31 250 | +607 |
| Documentation (.md) | 130 fichiers / 9 426 lignes | 246 fichiers / ~38 100 lignes | +116 / +28 689 |
| Fichiers de test | 7 | 180 | +173 |
| Fonctions de test | — | 3 229 (3 910 collectees avec parametrisation) | +3 229 |

### Diff Git vérifié (commits d'Amine Mohamed uniquement)

```
267 commits d'Amine Mohamed, +221 481 insertions, -17 976 suppressions
Diff upstream 9a3a92b6 → HEAD 7a7abd6a : 898 files changed, +213 250 insertions, -14 434 suppressions
Période Git verifiee : 15 janvier 2026 → 24 avril 2026
```

---

## 2. Identification de la base open-source

### 2.1 Agent Zero — Le fork

| Élément | Détail |
|---------|--------|
| Projet | Agent Zero (framework d'agents IA) |
| Licence | MIT (usage commercial autorisé, modification libre) |
| Auteur original | frdel / Jan Tomášek et contributeurs open-source |
| Premier commit upstream | `8cef5e1e` (10 juin 2024) — 52 fichiers, 854 lignes Python |
| Dernier commit upstream | `9a3a92b6` (10 janvier 2026) — 1 221 fichiers, 28 403 lignes Python |
| Contributeurs upstream | 35 contributeurs distincts. frdel / Jan Tomášek (créateur, deux signatures Git pour la même personne : 629 commits sous `frdel` + 45 commits sous `Jan Tomášek` = 674 commits cumulés). Autres contributeurs : 416 commits cumulés. |
| Évolution upstream | De juin 2024 à janvier 2026, la communauté a fait évoluer Agent Zero d'un POC (854 lignes) vers un framework plus complet (28 403 lignes Python, WebUI basique, Docker de dev) |

### 2.2 Ce que fournit Agent Zero au 10 janvier 2026

À la date où Amine Mohamed commence son travail, la base Agent Zero comprend :
- Un framework d'agent conversationnel (boucle agent/outil, gestion modèles)
- Une WebUI basique (182 fichiers hors vendor, 30 643 lignes)
- Des outils génériques (code execution, memory, knowledge, delegation)
- Des helpers Python (210 fichiers, 28 403 lignes)
- Un Docker de développement (non production-ready)
- Une documentation communautaire (130 fichiers .md, 9 426 lignes)
- 7 fichiers de test rudimentaires

**Ce qui manque :** spécialisation métier, architecture de production, sécurité entreprise, pipeline OCR/PDF, modules juridiques, multi-user, tests industriels, documentation de déploiement.

### 2.3 Licence MIT — Implications juridiques

La licence MIT accorde explicitement et irrévocablement :
- Le droit d'utiliser, copier, modifier et distribuer le logiciel
- Le droit d'usage **commercial** sans restriction
- Le droit de créer des **œuvres dérivées** propriétaires

La seule obligation principale : inclure la notice de copyright MIT dans les copies. **Aucun obstacle juridique bloquant n'est identifié à ce stade** pour valoriser les développements propriétaires construits sur cette base, sous réserve de conserver les notices tierces applicables et de faire confirmer le périmètre par le conseil juridique ou le commissaire aux apports.

### 2.4 Indépendance technologique vis-à-vis d'Agent Zero

Agent Zero doit être qualifié juridiquement et techniquement comme une **fondation open-source substituable**, non comme le siège principal de la valeur de l'apport.

La valeur valorisable ne porte pas sur la boucle conversationnelle générique fournie par Agent Zero, mais sur les couches propriétaires ajoutées au-dessus :
- le protocole PRISM de consensus multi-arbitres et ses contrats fail-closed ;
- le router déterministe et la gate de criticité ;
- le framework Evidence de rapports auditables avec intégrité cryptographique ;
- les pipelines métier Legal-Safe, médical, stratégique et PDF/OCR ;
- la sécurité multi-tenant, les logs d'audit, le replay engine, la revue humaine et le registre de risques dynamique ;
- la documentation d'architecture, les ADR, le glossaire, la politique de sécurité et les tests.

**Position défendable face au commissaire :** Agent Zero a réduit le coût initial d'amorçage, mais il ne fournit ni la spécialisation métier, ni le pipeline de preuve, ni les mécanismes de conformité, ni l'architecture d'exploitation qui fondent la valeur de KOREV Evidence. Une substitution de la base d'orchestration serait coûteuse mais techniquement possible ; une substitution des couches PRISM/Evidence/Legal-Safe exigerait de reconstruire l'essentiel de l'actif propriétaire.

---

## 3. Inventaire quantitatif des développements propriétaires

### 3.1 Périmètre

Le travail propriétaire est mesuré par le **diff entre le dernier commit upstream** (`9a3a92b6`, 10 janvier 2026) **et HEAD** (`7a7abd6a`, 24 avril 2026). Ce diff isole les développements intervenus après le fork.

La vérification au 24 avril 2026 (HEAD `7a7abd6a`) retourne :

```text
git diff 9a3a92b6..HEAD --shortstat
  898 files changed, 213 250 insertions(+), 14 434 deletions(-)
  Net : 198 816 lignes
git log --all --author='Amine' --shortstat
  267 commits, +221 481 insertions, -17 976 suppressions, net +203 505
```

Les tableaux détaillés ci-dessous reprennent les métriques de l'état audité du 17 avril 2026 (rapport initial : 894 fichiers, +210 891 / -14 431, net 196 460 ; 262 commits Amine, +219 008 / -17 859, net +201 149). Les commandes de la section 7.1 permettent de recalculer les métriques exactes à la date d'examen ; l'écart entre le 17 avril et le 24 avril est de +4 fichiers, +2 359 insertions, +3 suppressions et +5 commits Amine, soit +2 356 lignes nettes, lié aux corrections de résilience publiées entre le 17 et le 24 avril 2026.

### 3.2 Volume global

```text
git diff 9a3a92b6..HEAD :
  898 files changed, 213 250 insertions(+), 14 434 deletions(-)
  Net : 198 816 lignes (verification 24 avril 2026, HEAD 7a7abd6a)
```

| Type | Avant (upstream) | Après (Evidence) | Delta net | % ajouté par Amine |
|------|-----------------|-----------------|-----------|-------------------|
| Fichiers Python | 210 | 599 | +389 | 65 % des fichiers Python actuels |
| Lignes Python | 28 403 | 186 865 | +158 462 | 85 % du code Python actuel |
| WebUI (hors vendor) | 182 fichiers / 30 643 lig. | 166 fichiers / 31 250 lig. | -16 / +607 | Refonte & restructuration (¹) |
| Documentation .md | 130 / 9 426 lig. | 246 / ~38 100 lig. | +116 / +28 689 | 75 % de la doc actuelle |
| Fichiers de test | 7 | 180 | +173 | 96 % des tests actuels |
| Fonctions de test | ~0 | 3 229 (3 910 collectees) | +3 229 | ~100 % des tests actuels |

> (¹) La WebUI a fait l'objet d'un refactoring qualitatif (restructuration des composants, ajout de l'i18n, personnalisation du chat) sans augmentation nette du volume. Le travail frontal est mesuré par les **modifications fonctionnelles** (i18n, composants projets, settings) plutôt que par le delta LOC brut.

### 3.3 Vérification par les commits Git

| Métrique | Valeur |
|----------|--------|
| Commits d'Amine Mohamed | 262 |
| Insertions totales | +219 008 lignes |
| Suppressions totales | -17 859 lignes |
| Net | +201 149 lignes |
| Premier commit | 15 janvier 2026 |
| Dernier commit | 8 avril 2026 |
| Jours actifs de développement | 39 |

> **Verification complementaire au 25 avril 2026 :** `git log --all --author='Amine' --shortstat` retourne 267 commits, +221 481 insertions, -17 976 suppressions, soit +203 505 lignes nettes en cumul de commits. Ce compteur de commits ne se confond pas avec le diff net upstream -> HEAD, qui retourne 898 fichiers modifies, +213 250 insertions et -14 434 suppressions.

Ce diff est **reproductible et vérifiable** par tout auditeur :
```bash
git log --all --author='Amine' --shortstat --format=''
git diff 9a3a92b6..HEAD --stat
```

---

## 4. Inventaire des apports technologiques exclusifs

Chaque apport ci-dessous est une **brique technologique distincte**, inexistante dans Agent Zero, créée intégralement par Amine Mohamed. Ils sont classés par domaine fonctionnel.

---

### APPORT A — Système PRISM Consensus fail-closed (antériorité PRISM)

**Origine :** Algorithmes issus du projet **PRISM**, un projet antérieur d'Amine Mohamed. Le code consensus dans Evidence est une adaptation et intégration de ces algorithmes dans l'écosystème Agent Zero.

**Principe :** Validation multi-LLM des réponses critiques. Plusieurs modèles votent indépendamment, un arbitre consolide, le système refuse de répondre si le consensus n'est pas atteint (fail-closed).

| Fichier | LOC | Rôle |
|---------|-----|------|
| `python/consensus/engine.py` | 388 | Moteur central (point d'entrée unique `run_consensus()`) |
| `python/helpers/consensus_arbiter.py` | 886 | Orchestrateur multi-LLM, configuration des arbitres (2-3 actifs par defaut, configurable) |
| `python/helpers/consensus_manager.py` | 692 | Gestion des votes, types de décision, comptage |
| `python/helpers/consensus_contracts.py` | 386 | Contrats de sûreté (fail-closed, audit trail) |
| `python/helpers/consensus_integration.py` | 560 | Intégration dans le pipeline principal |
| `python/helpers/consensus_mcp_integration.py` | 447 | Pont avec les serveurs MCP |
| `python/helpers/research_consensus_integration.py` | 706 | Consensus appliqué à la recherche scientifique |
| Autres modules consensus | ~2 138 | Collaborative consensus, adversarial consensus integration |
| **Total Consensus** | **6 203** | **100 % Amine Mohamed, 0 % dans Agent Zero** |

---

### APPORT B — Instruction contradictoire & Débat adversarial (antériorité PRISM)

**Origine :** Extension du système PRISM, appliquant les principes du débat contradictoire à l'IA. Deux LLM argumentent pour et contre, un juge tranche.

| Fichier | LOC | Rôle |
|---------|-----|------|
| `python/helpers/adversarial_consensus_integration.py` | 1 144 | Pipeline d'instruction contradictoire intégré au consensus |
| `python/helpers/adversarial_instruction.py` | 2 123 | Moteur de débat : thèse/antithèse/synthèse, détection de domaine |
| `python/helpers/collaborative_consensus.py` | 991 | Consensus collaboratif (variante coopérative du débat) |
| `python/api/adversarial_analyze.py` | 112 | API : lancer une analyse contradictoire |
| `python/api/adversarial_dossier.py` | 105 | API : constituer un dossier contradictoire |
| `python/api/adversarial_decide.py` | 91 | API : décision arbitrée |
| `python/api/adversarial_list.py` | 55 | API : lister les analyses |
| **Total Débat adversarial** | **4 621** | **100 % Amine Mohamed, 0 % dans Agent Zero** |

---

### APPORT C — Router déterministe & Gate de criticité

**Principe :** Routage intelligent des requêtes selon leur criticité (domaine juridique, médical, financier…). Politique déterministe, pas de LLM dans la boucle de routage, injection-proof.

| Fichier | LOC | Rôle |
|---------|-----|------|
| `python/helpers/criticality_router.py` | 944 | Routeur déterministe v2 (policy-driven, anti-injection) |
| `python/helpers/critical_decision_gate.py` | 803 | Gate de sûreté pour décisions critiques |
| `python/helpers/router/router.py` | 589 | Routeur principal (hashing deterministe) |
| `python/helpers/router/policy.py` | 617 | Tables de mots-cles pour classification |
| `python/helpers/router/judge.py` | 424 | Juge de routage (évaluation de criticité) |
| `python/helpers/router/routing_contract.py` | 531 | Contrat de routage (enforcement levels) |
| `python/helpers/router/metrics.py` | 316 | Metriques de routage |
| `python/helpers/router/__init__.py` | 248 | Interface publique du module |
| **Total Router** | **4 472** | **100 % Amine Mohamed, 0 % dans Agent Zero** |

---

### APPORT D — Pipeline juridique complet (Legal-Safe)

**Principe :** Système complet de traitement juridique : ingestion de sources légales, citations, rédaction de contrats avec garde-fous, conformité, audit.

| Fichier | LOC | Rôle |
|---------|-----|------|
| `python/helpers/legal_pipeline.py` | 1 807 | Pipeline principal d'ingestion juridique |
| `python/helpers/legal_orchestrator.py` | 1 960 | Orchestrateur multi-agent juridique |
| `python/helpers/legal_diff.py` | 994 | Diff juridique (comparaison de versions) |
| `python/helpers/legal_agent_contracts.py` | 810 | Contrats d'agents juridiques |
| `python/helpers/legal_rendering.py` | 842 | Rendu des documents juridiques |
| `python/helpers/legal_retrieval.py` | 731 | Recherche dans les bases juridiques |
| `python/helpers/legal_safe_schema.py` | 588 | Schéma de sûreté juridique |
| `python/helpers/legal_citations.py` | 420 | Gestion des citations légales |
| `python/helpers/legal_citations_db.py` | 515 | Base de données de citations |
| `python/helpers/legal_safe_logger.py` | 513 | Logger sécurisé (audit trail) |
| `python/helpers/legal_safe_policy.py` | 496 | Politique de sûreté juridique |
| `python/helpers/legal_safe_runtime.py` | 475 | Runtime sécurisé |
| `python/helpers/legal_safe_renderer.py` | 424 | Rendu sécurisé |
| `python/extensions/legal_safe_mode/` | 1 028 | Extension d'intégration dans le système de prompts |
| `python/helpers/contract_drafting/` (7 fichiers) | 2 536 | Pipeline de rédaction de contrats (gate, templates, leak guard) |
| **Total Legal** | **16 556** | **100 % Amine Mohamed, 0 % dans Agent Zero** |

---

### APPORT E — Moteur PDF/OCR industriel (PRISM WeasyPrint Engine)

**Principe :** Pipeline complet : extraction texte PDF, fallback OCR (Tesseract + pdf2image), génération de PDF professionnels (WeasyPrint), templates, Evidence Document System.

| Fichier | LOC | Rôle |
|---------|-----|------|
| `python/helpers/pdf_extraction/pipeline.py` | 1 217 | Pipeline d'extraction avec circuit breakers |
| `python/helpers/pdf_extraction/ocr_engine.py` | 363 | Moteur OCR (Tesseract, DPI adaptatif) |
| `python/helpers/pdf_extraction/config.py` | 711 | Configuration du pipeline |
| `python/helpers/pdf_extraction/pdf_backend.py` | 363 | Backend PDF (pypdf/pdfplumber) |
| `python/helpers/pdf_extraction/types.py` | 386 | Types et structures de données |
| `python/helpers/pdf_generator.py` | 926 | Générateur PDF professionnel |
| `python/helpers/pdf_templates.py` | 631 | Templates de documents |
| `python/helpers/evidence_pdf_engine.py` | 1 091 | Moteur PRISM WeasyPrint unifie + fallback ReportLab premium (reecrit avril 2026) |
| `python/helpers/strategic_charts.py` | 664 | Generation automatique de graphiques PRISM depuis dossiers strategiques |
| `python/helpers/evidence_document/` (8 fichiers) | 3 472 | Système de documents Evidence (AST, canvas, layout, renderer) |
| `python/tools/pdf_ocr.py` | 173 | Outil OCR pour les agents |
| `python/tools/export_strategic_pdf.py` | 384 | Export PDF stratégique |
| **Total PDF/OCR** | **12 384** | **100 % Amine Mohamed, 0 % dans Agent Zero** |

---

### APPORT F — Métacognition & Reasoning Engine

**Principe :** Couche de raisonnement au-dessus du LLM : auto-évaluation, planification de tâches, suivi des décisions.

| Fichier | LOC | Rôle |
|---------|-----|------|
| `python/helpers/reasoning_engine.py` | 1 190 | Moteur de raisonnement (baseline tracking, validation) |
| `python/helpers/metacognition.py` | 1 046 | Métacognition (auto-évaluation, confiance calibrée) |
| **Total Reasoning** | **2 236** | **100 % Amine Mohamed, 0 % dans Agent Zero** |

---

### APPORT G — Pipeline stratégique & Reporting

**Principe :** Génération de documents stratégiques de qualité professionnelle, avec validation multi-agent et export PDF.

| Fichier | LOC | Rôle |
|---------|-----|------|
| `python/helpers/strategic_contract.py` | 843 | Contrats de qualité stratégique (Evidence-grade) |
| `python/helpers/strategic_pipeline.py` | 402 | Pipeline E2E de documents stratégiques |
| `python/helpers/research_pipeline.py` | 665 | Pipeline de recherche scientifique |
| `python/helpers/reporting/evidence_native.py` | 1 422 | Système de reporting natif Evidence |
| `python/helpers/reporting/report_job.py` | 635 | Jobs de rapports automatisés |
| `python/helpers/reporting/report_assembler.py` | 361 | Assembleur de rapports |
| `python/helpers/strategic_orchestrator.py` | 1 560 | Orchestrateur strategique multi-agents |
| `python/extensions/strategic_validation/` (3 fichiers) | 871 | Extensions de validation strategique (enforcement, monologue, stream) |
| **Total Stratégique** | **6 759** | **100 % Amine Mohamed, 0 % dans Agent Zero** |

---

### APPORT H — Sécurité entreprise & Multi-user

**Principe :** Hardening sécurité (Argon2id, rate limiting, PII sanitization), gestion multi-utilisateur, App Factory pattern.

| Fichier | LOC | Rôle |
|---------|-----|------|
| `python/security/` (14 fichiers) | 2 553 | Auth, authorization, rate limiting (Redis+memory), path safety, upload validation, shell safety, IP, audit |
| `python/helpers/user_manager.py` | 252 | Gestion multi-utilisateur |
| `python/helpers/deploy_config.py` | 538 | Configuration de déploiement sécurisée |
| `python/helpers/health_endpoints.py` | 339 | Endpoints de santé (healthz, readyz) |
| `python/helpers/rate_limiter.py` | 57 | Rate limiting helper (Redis-backed) |
| `python/helpers/evidence.py` | 674 | Module central Evidence (orchestration) |
| **Total Sécurité** | **4 413** | **100 % Amine Mohamed, 0 % dans Agent Zero** |

---

### APPORT I — Contrat métier spécialisé Medical

**Principe :** Contrat de sûreté domaine médical : le système refuse de répondre hors périmètre validé (kill tests, garde-fous).

| Fichier | LOC | Rôle |
|---------|-----|------|
| `python/helpers/medical_contract.py` | 769 | Contrat médical (kill tests, garde-fous) |
| **Total Contrat médical** | **769** | **100 % Amine Mohamed, 0 % dans Agent Zero** |

> Note : `strategic_contract.py` (843 LOC) est comptabilisé dans l'Apport G (Pipeline stratégique) et n'est pas redondé ici.

---

### APPORT J — Personnalisation du chat (Symbiose Homme-IA)

**Principe :** Paramétrage fin du comportement conversationnel : tutoiement, ton, persona, verbosité.

| Fichier | LOC | Rôle |
|---------|-----|------|
| `python/helpers/chat_style.py` | 116 | Génération du bloc de style |
| `python/extensions/system_prompt/_05_chat_style.py` | 29 | Injection dans le system prompt |
| **Total Chat** | **145** | **100 % Amine Mohamed, 0 % dans Agent Zero** |

---

### APPORT K — Internationalisation FR/EN

**Principe :** Système i18n complet avec fichiers de traduction et sélecteur de langue UI.

| Fichier | LOC | Rôle |
|---------|-----|------|
| `webui/i18n/fr.json` | 239 | Traduction française complète |
| `webui/i18n/en.json` | 239 | Traduction anglaise |
| **Total I18N** | **478** | **100 % Amine Mohamed, 0 % dans Agent Zero** |

---

### APPORT L — Architecture de production Docker

**Principe :** Passage d'un Docker de développement à une architecture production-ready (multi-stage, Caddy HTTPS, health checks, volumes, user isolation).

| Fichier | LOC | Rôle |
|---------|-----|------|
| `deploy/Dockerfile.backend` | 224 | Multi-stage build (Python 3.11 + Node.js 20) |
| `deploy/docker-compose.yml` | 352 | Orchestration Caddy + Flask + volumes + healthchecks |
| `deploy/config/Caddyfile` | 91 | Reverse proxy HTTPS automatique |
| `scripts/` | 8 834 | Scripts installation, migration, backup, CI, provisioning multi-tenant |
| **Total Deploy** | **9 501** | **100 % Amine Mohamed, 0 % dans Agent Zero** |

---

### APPORT M — Suite de tests TDD industrielle

| Métrique | Valeur |
|----------|--------|
| Fichiers de test | 180 |
| Fonctions de test | 3 229 (3 910 collectees avec parametrisation) |
| Lignes de code test | ~67 200 |
| Couverture | Consensus, legal, OCR, PDF, Docker, sécurité, chat, router, audit-proof, hostile hardening, qualité documentaire |

**Aucun test industriel n'existait dans Agent Zero (7 fichiers rudimentaires).**

---

### APPORT N — 12 Agents spécialisés + Intégrations MCP

| Agent | Spécialisation | Exclusif ? |
|-------|---------------|------------|
| `legal_safe` | Juridique sécurisé | Oui — prompts + contrats + garde-fous |
| `legal_drafting_guarded` | Rédaction juridique | Oui |
| `medical` | Domaine médical | Oui — contrat médical + kill tests |
| `finance` | Analyse financière | Oui — méthodologie stratégique |
| `developer` | Développement logiciel | Oui |
| `researcher` | Recherche scientifique | Oui — intégration MCP arXiv/Scholar |
| `marketing` | Marketing | Oui |
| `sales` | Commercial | Oui |
| `hacker` | Sécurité informatique | Oui |
| `multitask` | Orchestrateur multi-tâches | Oui — refonte complète |
| `default` | Configuration par défaut | Oui |

**11 serveurs MCP** configurés et intégrés, dont `semanticscholar` et `openalex` avec Dockerfiles propres.

---

### APPORT O — Documentation technique & fonctionnelle

116 documents Markdown ajoutés (+28 689 lignes), dont :

| Document | Lignes | Objet |
|----------|--------|-------|
| `GUIDE_DEPLOIEMENT_ENTREPRISE.md` | 1 340 | Guide de déploiement production |
| `DEMONSTRATION_CABINET_AVOCATS.md` | 565 | POC secteur juridique |
| `KOREV_Evidence_Presentation_FR.md` | — | Présentation commerciale |
| `SPEC_MULTI_USER_WORKSPACE.md` | — | Spécification multi-utilisateur |
| `SPEC_CHAT_PERSONALIZATION.md` | — | Spécification personnalisation chat |
| `MANUEL_INSTALLATION_CLIENT.md` | — | Manuel installation client |
| Checklists CTO, Audit, Contrôle | — | Documents de gouvernance |
| `SECURITY.md` | ~120 | Politique de sécurité, divulgation responsable, pratiques implémentées |
| `docs/adr/` (5 ADR) | ~225 | Décisions architecturales (PRISM, router, Evidence, LiteLLM, extensions) |
| `docs/GLOSSARY.md` | ~92 | Glossaire des termes propriétaires Evidence (30+ entrées) |
| `docs/ARCHITECTURE_C4_DIAGRAMS.md` | ~252 | Diagrammes C4 Mermaid (contexte, containers, composants, séquence) |
| `docs/BENCHMARK_COMPARABLES_VALORISATION_EVIDENCE.md` | ~335 | Benchmark de comparables et positionnement de marché |

---

### APPORT P — Pipeline Audit-Proof (replay, human review, risk register) — NOUVEAU avril 2026

**Principe :** Pipeline de preuve d'audit complet : rejeu deterministe de sessions, workflow de revue humaine pour decisions critiques, registre de risques dynamique avec scoring automatise. Ces briques adressent directement la critique "auto-evaluation sans validation externe" identifiee lors de l'audit hostile.

| Fichier | LOC | Rôle |
|---------|-----|------|
| `python/helpers/replay_engine.py` | 327 | Moteur de rejeu deterministe de sessions |
| `python/helpers/human_review.py` | 327 | Workflow de revue humaine (approbation/rejet/escalade) |
| `python/helpers/dynamic_risk_register.py` | 403 | Registre de risques dynamique avec scoring temps reel |
| `python/extensions/monologue_end/_35_replay_snapshot.py` | 112 | Extension de capture de snapshots pour rejeu |
| `python/extensions/monologue_end/_36_risk_assessment.py` | 137 | Extension d'evaluation automatique des risques |
| `python/api/replay.py` | 145 | API : rejeu de session |
| `python/api/human_review.py` | 143 | API : workflow de revue humaine |
| `python/api/risk_dashboard.py` | 98 | API : tableau de bord des risques |
| **Total Audit-Proof** | **1 692** | **100 % Amine Mohamed, 0 % dans Agent Zero** |

---

### Synthèse des apports

| # | Apport | LOC | Antériorité PRISM |
|---|--------|-----|-------------------|
| A | Consensus PRISM fail-closed | 6 203 | **Oui** |
| B | Débat adversarial / Instruction contradictoire | 4 621 | **Oui** |
| C | Router déterministe & Gate de criticité | 4 472 | Non (création Evidence) |
| D | Pipeline juridique Legal-Safe | 16 556 | Non (création Evidence) |
| E | Moteur PDF/OCR industriel + PRISM Charts | 12 384 | Partiel (PRISM WeasyPrint) |
| F | Métacognition & Reasoning Engine | 2 236 | Non (création Evidence) |
| G | Pipeline stratégique, Reporting & Orchestration | 6 759 | Non (création Evidence) |
| H | Sécurité entreprise, Multi-user & Module security/ | 4 413 | Non (création Evidence) |
| I | Contrat métier Medical | 769 | Non (création Evidence) |
| J | Personnalisation du chat | 145 | Non (création Evidence) |
| K | Internationalisation FR/EN | 478 | Non (création Evidence) |
| L | Architecture Docker production + scripts | 9 501 | Non (création Evidence) |
| M | Suite de tests TDD | ~67 200 | Non (création Evidence) |
| N | 12 Agents + 11 MCP servers | — | Non (création Evidence) |
| O | Documentation (116 fichiers ajoutés) | +28 689 | Non (création Evidence) |
| P | Pipeline Audit-Proof (replay, review, risk) | 1 692 | Non (création Evidence, avril 2026) |
| | **Total code propriétaire (A–M, P)** | **~137 400** | **~10 824 LOC d'antériorité PRISM** |
| | **Total avec documentation (A–P)** | **~166 100** | |

---

## 5. Historique de développement

### 5.1 Chronologie — Distinction upstream / propriétaire

| Date | Événement | Auteur |
|------|-----------|--------|
| 10 juin 2024 | Création du dépôt Agent Zero (52 fichiers, 854 lignes) | frdel (open-source) |
| Juin 2024 – Jan. 2026 | Évolution communautaire Agent Zero (1 090 commits) | 34 contributeurs open-source |
| 10 janvier 2026 | **Dernier commit upstream** (`9a3a92b6`) — état : 1 221 fichiers, 28 403 lignes Python | Jan Tomášek |
| **15 janvier 2026** | **Premier commit d'Amine Mohamed** — Rebranding PRISM Oracle v1.0 | **Amine Mohamed** |
| 18 janvier 2026 | Rebranding Korev Oracle + conformité légale MIT | Amine Mohamed |
| 21–27 janvier 2026 | Phase intensive : legal, OCR, PDF, consensus, router, agents | Amine Mohamed |
| 25 janvier 2026 | Renommage final → KOREV Evidence | Amine Mohamed |
| 5–6 février 2026 | Sécurité Phase 1 P0 (Argon2, rate limiting, CI) | Amine Mohamed |
| 8–9 février 2026 | Legal pipeline, PDF unifié, démonstration avocat | Amine Mohamed |
| 11 février 2026 | Personnalisation du chat | Amine Mohamed |
| Fév.–mars 2026 | Tests massifs, hardening, multi-tenant, scheduler, notifications | Amine Mohamed |
| **3 avril 2026** | **Audit hostile interne — commit `892a79cb`** | **Amine Mohamed** |
| 3 avril 2026 | Corrections P0 critiques : licence proprietaire, HMAC RuntimeError, logs, RBAC | Amine Mohamed |
| 4 avril 2026 | Pipeline audit-proof : replay engine, human review, dynamic risk register | Amine Mohamed |
| 4 avril 2026 | Rewrite moteur PRISM PDF (WeasyPrint + ReportLab), generation auto de charts | Amine Mohamed |
| 7–8 avril 2026 | Provisioning multi-tenant, nettoyage entites, fix FTS5 index | Amine Mohamed |
| **17 avril 2026** | **Remediations P1/P2 : SECURITY.md, 5 ADR, GLOSSARY.md, diagrammes C4, benchmark comparables, audit hostile complet, 64 tests TDD documentation** | **Amine Mohamed** |
| **17 avril 2026** | **Derniere mise a jour — score maturite 69/100 (livrables documentation non commites a date)** | **Amine Mohamed** |
| **24 avril 2026** | Corrections resilience image generation et fallback provider — HEAD verifie `7a7abd6a` | **Amine Mohamed** |

### 5.2 Intensité du travail propriétaire

| Période | Commits | Réalisations clés |
|---------|---------|-------------------|
| 15–18 jan. | 9 | Rebranding, i18n FR/EN, conformité MIT |
| 19–25 jan. | 51 | Legal-Safe, OCR, PDF pro, consensus, router, Excel, MCP |
| 26 jan.–1 fév. | 40 | Agents spécialisés, documents stratégiques, scripts install |
| 2–8 fév. | 18 | Sécurité P0, CI, legal pipeline, démonstration avocat |
| 9–11 fév. | 16 | PDF unifié, chat personnalisation, Docker production |
| Fév.–mars 2026 | ~112 | Tests massifs, hardening multi-tenant, scheduler, notifications, conformite |
| 3–8 avr. 2026 | 16 | Corrections P0 securite, audit-proof pipeline, PRISM PDF rewrite, charts |
| 17 avr. 2026 | — | Remediations P1/P2 : SECURITY.md, 5 ADR, glossaire, C4, benchmark, audit hostile |
| **Total** | **267 commits (262 au 8 avril)** | **~40 jours actifs sur 99 jours calendaires (15 jan. – 24 avr. 2026)** |

### 5.3 Répartition des contributions (dépôt complet)

| Source | Commits | Lignes ajoutées | Rôle |
|--------|---------|----------------|------|
| **Amine Mohamed** | **267** (262 au 8 avril) | **+221 481** (+219 008 au 8 avril) | **Architecte, spécialisation, industrialisation** |
| frdel (Jan Tomášek) | 674 | +83 985 | Créateur Agent Zero, framework de base |
| 33 autres contributeurs | 416 | ~variable | Communauté open-source Agent Zero |
| **Total dépôt** | **1 357** (1 352 au 8 avril) | — | — |

**Point clé pour le commissaire :** Les 1 090 commits non-Amine (calcul : 1 357 commits totaux du dépôt — 267 commits d'Amine Mohamed = 1 090) regroupent frdel/Jan Tomášek (créateur, 674 commits sous deux signatures Git) et la communauté open-source (416 commits cumulés). Ils constituent la base open-source MIT librement disponible. Les commits d'Amine Mohamed constituent le travail propriétaire valorisable. Le rapport initial audité retenait **262 commits** et **+219 008 lignes** au 8 avril 2026 ; la vérification du 24 avril relève **267 commits** et **+221 481 insertions**, soit un écart de +5 commits et +2 473 insertions sur 16 jours, lié aux corrections de résilience (image generation, fallback provider).

### 5.4 Antériorité R&D pré-repository : traitement probatoire

Le dossier doit distinguer deux niveaux de preuve :

1. **Prouvé par le dépôt** : l'existence d'une antériorité PRISM est corroborée par les noms de modules, ADR et documents techniques qui décrivent PRISM comme un projet prédécesseur intégré à Evidence. Cette preuve suffit à soutenir que les briques de consensus et de débat adversarial ne sont pas une simple customisation d'Agent Zero.
2. **Probatoire hors dépôt** : l'affirmation selon laquelle **5 années de R&D précèdent le premier repository** n'est pas démontrable par le seul historique Git disponible dans ce dépôt. Elle peut être intégrée au dossier comme actif immatériel si elle est accompagnée des pièces datées détenues par l'apporteur : carnets de conception, dépôts antérieurs, exports de notes, emails, maquettes, noms de fichiers, factures d'outils, captures de prototypes, ou attestations.

**Formulation juridiquement défendable à ce stade :** "Amine Mohamed, inventeur de PRISM et de KOREV Evidence, indique que les briques conceptuelles PRISM et la méthodologie de validation contradictoire résultent d'un travail de R&D antérieur au dépôt Evidence. Le dépôt actuel en matérialise une partie dans le code ; les pièces d'antériorité externe sont à annexer pour permettre leur revue par le commissaire aux apports et Diag & Grow."

**Portefeuille brevets PRISM :** **4 brevets PRISM sont en cours** et seront présentés séparément aux commissaires aux apports ; le consensus anti-hallucination fait partie du périmètre breveté. Ces brevets ne doivent pas être qualifiés de brevets Evidence tant que leur titulaire, leur périmètre et leur lien juridique avec Evidence ne sont pas annexés. Amine Mohamed est inventeur de PRISM et de KOREV Evidence ; leur effet sur la valorisation d'Evidence dépend d'une chaîne de droits explicite : cession, licence, apport ou autorisation d'exploitation PRISM -> Evidence.

**Effet valorisation :** avec pièces externes datées, cette antériorité renforce la crédibilité technique et explique la productivité observée. Elle peut justifier une prime qualitative ou un complément de coût de reproduction au titre du savoir-faire non codé et de la brique consensus PRISM intégrée à Evidence, sous réserve d'éviter tout double comptage et de documenter la chaîne de droits PRISM -> Evidence.

---

## 6. Estimation du coût de reproduction

### 6.1 Méthode

La méthode des **coûts de reproduction** estime la valeur de l'actif en calculant le coût qu'il faudrait engager pour recréer un logiciel fonctionnellement équivalent à partir de la base open-source. C'est la méthode la plus courante en évaluation d'actifs logiciels pour un commissaire aux apports (référence : norme IVS 210 — Actifs incorporels).

### 6.2 Décomposition du volume propriétaire

Le périmètre est strictement le **diff entre le dernier commit upstream** (`9a3a92b6`) **et HEAD**. Le total vérifié par `git diff` est, au 24 avril 2026, de **198 816 insertions nettes** (213 250 insertions, 14 434 suppressions). La décomposition ci-dessous a été calibrée sur l'état audité du 17 avril (196 460 insertions nettes) ; l'écart de +2 356 lignes lié aux corrections du 17–24 avril est absorbé par les fourchettes d'estimation et n'a pas d'effet matériel sur la valorisation.

| Composant | LOC delta | Complexité | Productivité (LOC/j-h) | Effort (j-h) |
|-----------|-----------|------------|------------------------|---------------|
| Modules safety-critical (A–B, D, P : consensus, adversarial, legal, audit-proof) | ~29 100 | Très élevée (fail-closed, expertise juridique) | 50–80 | 364–582 |
| Modules domaine-spécifiques (C, E–J : router, PDF/OCR, reasoning, stratégique, sécurité, médical, chat) | ~31 200 | Élevée (expertise domaine, intégration) | 60–100 | 312–520 |
| Backend Python : API, extensions, outils, intégrations (hors ci-dessus et tests) | ~27 500 | Moyenne–Élevée | 80–150 | 183–344 |
| Suite de tests TDD (3 910 tests collectes avec parametrisation dans l'environnement de reference ; collecte locale Python 3.9 du 25 avril interrompue apres 3 608 tests collectes et 19 erreurs de compatibilite) | ~66 000 | Moyenne (volume, simulation LLM) | 120–250 | 264–550 |
| Architecture Docker/deploy/scripts (ex nihilo) | ~9 500 | Élevée (DevOps, multi-tenant) | 60–100 | 95–158 |
| Configuration, CI/CD, WebUI, i18n, prompts d'agents | ~5 500 | Moyenne | 80–150 | 37–69 |
| Documentation technique (107 fichiers, delta) | ~27 700 | Faible–Moyenne | 200–400 | 69–139 |
| **Total (rapproché du git diff)** | **~196 500** (état 17 avril) / **~198 800** (état 24 avril) | | | **1 324–2 362 j-h** |

> **Note de rapprochement :** La somme (~196 500) de la décomposition est cohérente, à moins de 0,1 % près, avec les 196 460 insertions nettes du diff Git de l'état audité du 17 avril (210 891 insertions, 14 431 suppressions). Au 24 avril 2026, le diff total atteint 198 816 insertions nettes (213 250 / -14 434), soit +2 356 lignes en 7 jours (~+1,2 %), sans impact matériel sur les fourchettes d'effort. Les livrables de documentation crees le 17 avril 2026 (SECURITY.md, 5 ADR, GLOSSARY.md, C4, benchmark — ~1 025 lignes supplementaires et 64 tests) ne sont pas inclus dans cette decomposition, qui est strictement fondee sur le diff Git. Leur impact financier (effort supplementaire de ~5–10 j-h) est absorbe par les fourchettes d'estimation.

### 6.3 Justification des ratios d'effort

Les estimations d'effort sont basées sur les benchmarks industriels suivants (source : COCOMO II, ISBSG, Capers Jones). Les fourchettes appliquées sont le **sous-ensemble pertinent** de chaque catégorie, ajusté à la complexité spécifique du composant.

| Type de code | Benchmark de référence (LOC/j-h) | Fourchette appliquée | Composants |
|-------------|----------------------------------|---------------------|------------|
| Code complexe safety-critical | 30–60 | 50–80 | Consensus, adversarial, legal, audit-proof |
| Code domaine-spécifique | 50–100 | 60–100 | Router, PDF/OCR, reasoning, stratégique, sécurité |
| Code backend standard | 60–150 | 80–150 | API, extensions, outils, intégrations |
| Tests automatisés | 100–250 | 120–250 | Suite TDD (3 910 tests collectes dans l'environnement de reference, simulation LLM) |
| DevOps / Infrastructure as Code | 50–100 | 60–100 | Docker, deploy, scripts |
| Documentation technique | 200–500 | 200–400 | 107 fichiers Markdown |

Ces ratios correspondent aux standards de productivité d'une **équipe** de développeurs seniors et incluent le temps de conception, spécification, implémentation, debugging, code review et tests d'intégration. Le bas de fourchette (productivité élevée) fournit l'estimation conservatrice ; le haut (productivité basse) l'estimation haute.

### 6.4 Estimation financière indicative

TJM (taux journalier moyen) d'un développeur senior IA/Full-stack en France (2026) :

| Scénario | TJM | Jours-homme | Coût de reproduction |
|----------|-----|-------------|---------------------|
| Conservateur (productivité haute) | 500 € | 1 324 | **662 000 €** |
| Médian | 650 € | 1 843 | **1 197 950 €** |
| Haut (benchmark strict) | 800 € | 2 362 | **1 889 600 €** |

> Le TJM de 500–800 € correspond au marché français des prestations de développement IA/full-stack en 2026 (sources : Malt, Free-Work, Syntec Numérique). Un cabinet de conseil technique (Big4, cabinets spécialisés) facturerait 800–1 200 €/jour, ce qui placerait l'estimation haute au-delà de 2 M€.

### 6.4bis Scénarios de valorisation recommandés

| Scénario | Valeur de référence | Position face au commissaire | Conditions de défense |
|----------|--------------------:|------------------------------|-----------------------|
| Conservateur audit-proof | **662 000 € à 850 000 €** | Valeur basse, fortement défendable | Retient le bas du coût de reproduction et une décote de prudence élevée si la revue des annexes R&D reste incomplète ou insuffisante. |
| Défendable équilibré | **~958 000 € à 1 054 000 €** | Scénario recommandé | S'appuie sur le coût médian après décote technique résiduelle de 12–20 %, avec preuves Git, ADR, benchmark, audit hostile et documentation technique. Les factures DICA FRANCE à 1 500 €/mois et les preuves terrain permettent de défendre le haut de fourchette si elles sont annexées. |
| Offensif maîtrisé | **1 150 000 € à 1 350 000 €** | Négociable, non automatique | Nécessite un dossier probatoire renforcé : factures DICA FRANCE, preuves de paiement disponibles, pièces datées de R&D pré-repository, dossier des 4 brevets PRISM en cours avec chaîne de droits PRISM -> Evidence, preuve d'exécutabilité des tests, confirmations de pilotes terrain, build Docker vérifié, matrice des dépendances externes et justification des sources de marché. |

**Stratégie recommandée :** présenter le scénario équilibré comme valeur cible et conserver le scénario offensif comme borne haute de négociation. Le dossier ne doit pas demander une prime de marché fondée sur des multiples d'entreprise ; ces comparables servent uniquement à démontrer que le coût de reproduction retenu n'est pas excessif.

### 6.5 Facteurs de valorisation complémentaires (hors coût de reproduction)

Le coût de reproduction ne capture qu'une partie de la valeur de l'actif. Un commissaire aux apports pourrait également considérer :

| Facteur | Impact sur la valorisation |
|---------|--------------------------|
| **Antériorité PRISM** | Les algorithmes de consensus et de débat adversarial (A, B) sont issus d'un projet antérieur. La valeur de R&D accumulée dépasse le simple coût de réécriture. |
| **Brevets PRISM en cours** | 4 brevets PRISM sont en cours, dont un périmètre couvrant le consensus anti-hallucination. À ne pas présenter comme brevets Evidence sans chaîne de droits ; à annexer comme actif PRISM lié à la brique consensus intégrée. |
| **Expertise domaine** | Les modules juridique (D), médical (I) et financier (G) intègrent une expertise métier qui nécessiterait des consultants spécialisés en plus des développeurs. |
| **Time-to-market** | Reproduire ce logiciel prendrait **12–24 mois** à une équipe de 3–4 développeurs seniors. L'avance temporelle constitue un avantage concurrentiel significatif. |
| **Positionnement commercial** | Evidence cible un marché de niche (IA de confiance pour professions réglementées) avec peu de concurrents directs. |
| **Traction commerciale initiale** | Des factures DICA FRANCE sont disponibles à annexer pour **1 500 €/mois**, soit **18 000 €/an en run-rate annualisé**. Ce niveau ne suffit pas à fonder une méthode par multiples de revenus, mais il réduit l'objection "pré-revenue" et soutient le haut de fourchette du scénario défendable. |
| **Pilotes terrain** | Des pièces sont disponibles à annexer concernant la Chaire Construction 4.0 à Centrale Lille autour du Pr Zoubeir Lafhaj, ainsi que l'écosystème Le Tarmac by inovallée. Ces éléments doivent être annexés par emails, conventions ou attestations. |
| **Potentiel de revenus** | La méthode des revenus (DCF) pourrait donner une valorisation supérieure si un business plan et un historique commercial plus long sont disponibles. |
| **Coût d'opportunité** | Le temps de reproduction (12–24 mois) implique un manque à gagner commercial considérable pour un concurrent. |

> Ces facteurs complementaires sont developpes et situes dans un contexte de marche en section 6bis (References de marche et positionnement comparatif).

### 6.6 Note sur la productivité observée

Dans l'état audité du 8 avril, Amine Mohamed avait réalisé environ **40 jours actifs** de développement (262 commits, +219 008 lignes, ~5 500 lignes/jour). La vérification du 24 avril porte ce cumul à 267 commits et +221 481 insertions sur la période 15 janvier – 24 avril 2026. Cette productivité exceptionnelle s'explique par :
- Une expertise approfondie du framework Agent Zero, acquise bien avant le fork
- L'expérience accumulée sur le projet antérieur PRISM (algorithmes de consensus, moteur PDF)
- Un travail intensif et soutenu (commits quotidiens, weekends inclus)
- L'utilisation d'outils de développement modernes (IA-assisté)
- La connaissance intime du domaine (juridique, sécurité, conformité)

Le coût de reproduction par une **équipe** ne disposant pas de cette expertise préalable serait significativement plus élevé. C'est précisément l'objet de l'estimation ci-dessus : elle reflète le coût de **recréation à neuf** par une équipe de développeurs compétents mais sans connaissance spécifique du projet ni de son domaine métier. La productivité observée (~5 600 LOC/jour) est 30 à 100 fois supérieure aux benchmarks d'équipe (50–200 LOC/j-h), ce qui confirme la valeur de l'expertise accumulée.

> L'estimation par les couts de reproduction constitue la methode principale de valorisation retenue pour le present dossier. La section suivante apporte un eclairage complementaire en positionnant l'actif Evidence dans une grille de references de marche, afin de verifier la coherence de cette estimation avec les niveaux de valeur observes pour des actifs logiciels de complexite et de criticite comparables.

---

## 6bis. References de marche et positionnement comparatif de l'actif Evidence

Le chapitre complet est disponible dans le document annexe : `docs/BENCHMARK_COMPARABLES_VALORISATION_EVIDENCE.md`.

Ce benchmark situe Evidence dans la categorie des **infrastructures de decision, d'orchestration et de confiance** (categorie C), distincte des SaaS B2B standards (categorie A) et des SaaS metier enrichis par IA (categorie B). Cette categorisation repose sur les caracteristiques techniques documentees de l'actif : architecture multi-agents avec consensus deterministe, pipeline de conformite embarque, tracabilite et auditabilite natives, routage deterministe anti-injection, specialisation metier verticale.

Le positionnement dans la categorie C ne conduit pas a modifier l'estimation par les couts de reproduction. Il confirme que cette estimation (fourchette de 662 000 a 1 889 600 euros) s'inscrit dans un ordre de grandeur coherent avec les references de marche pour des actifs logiciels de cette categorie, ou les niveaux de valeur sont structurellement superieurs a ceux d'un SaaS standard.

Les limites methodologiques de cet exercice sont detaillees dans le document annexe (section 6), notamment la distinction entre valorisation d'entreprise et valorisation d'actif, la volatilite des multiples dans le secteur IA, et l'absence de transactions directement comparables.

---

## 7. Éléments de preuve pour le commissaire aux apports

> Les sections precedentes ont etabli la valeur de l'actif par deux approches complementaires : le cout de reproduction (section 6) et le positionnement comparatif de marche (section 6bis). La presente section fournit les elements de preuve permettant a un evaluateur externe de verifier ces estimations.

### 7.1 Preuves techniques vérifiables

| Preuve | Commande de vérification |
|--------|-------------------------|
| Diff upstream → Evidence | `git diff 9a3a92b6 HEAD --stat` |
| Commits d'Amine uniquement | `git log --all --author='Amine' --shortstat` |
| Historique horodaté complet | `git log --all --format='%H %ai %an %s'` |
| Code source intégral | Dépôt Git complet avec historique |
| Tests exécutables | `pytest tests/ -v` (3 910 tests collectes) |
| Build Docker fonctionnel | `docker compose -f deploy/docker-compose.yml build` |
| Smoke test conteneur | `docker run --rm korev/evidence-backend:latest python -c "import whisper; import pytesseract; print('OK')"` |

### 7.2 Documents complémentaires disponibles

- Guide de déploiement entreprise (`docs/GUIDE_DEPLOIEMENT_ENTREPRISE.md`)
- Démonstration cabinet d'avocats (`docs/DEMONSTRATION_CABINET_AVOCATS.md`)
- Spécifications fonctionnelles (multi-user, chat, legal pipeline)
- Audits techniques (OCR, pré-déploiement, sécurité)
- Checklists CTO et contrôle qualité
- Politique de sécurité (`SECURITY.md`) : divulgation responsable, pratiques implémentées, limites connues
- 5 Architecture Decision Records (`docs/adr/ADR-001` à `ADR-005`) : PRISM, router, Evidence, LiteLLM, extensions
- Glossaire technique (`docs/GLOSSARY.md`) : 30+ termes propriétaires Evidence
- Diagrammes d'architecture C4 (`docs/ARCHITECTURE_C4_DIAGRAMS.md`) : contexte, containers, composants, séquence
- Benchmark de comparables de marché (`docs/BENCHMARK_COMPARABLES_VALORISATION_EVIDENCE.md`)
- Guide d'onboarding développeur (`docs/DEVELOPER_ONBOARDING_ARCHITECTURE_GUIDE.md`, 1 196 lignes)
- Audit hostile complet (8 livrables, dossier `audit-hostile-valorisation/`, incluant l'audit dédié du dossier commissaire aux apports)
- Dossier des 4 brevets PRISM en cours, incluant le périmètre consensus anti-hallucination et la chaîne de droits PRISM -> Evidence, à annexer au dossier final
- Factures DICA FRANCE établissant un revenu récurrent de 1 500 €/mois, avec preuves de paiement disponibles, à annexer au dossier final
- Preuves de pilotes terrain : Centrale Lille / Chaire Construction 4.0 / Pr Zoubeir Lafhaj, et Le Tarmac by inovallée, à annexer au dossier final

### 7.3 Transparence sur la base open-source

La base Agent Zero (licence MIT) est explicitement identifiée :
- Premier commit upstream : `8cef5e1e` du 10 juin 2024
- Dernier commit upstream : `9a3a92b6` du 10 janvier 2026
- État upstream avant travail propriétaire : 1 221 fichiers, 28 403 lignes Python, 210 fichiers Python
- 34 contributeurs communautaires, 1 090 commits
- Licence MIT : usage commercial autorisé sans restriction

---

## 8. Conclusion

KOREV Evidence est une **œuvre dérivée substantielle** de la base Agent Zero. Entre le 15 janvier et le 24 avril 2026, Amine Mohamed a réalisé 267 commits totalisant **+221 481 insertions** en cumul auteur, transformant un framework communautaire (28 403 lignes Python, pas de spécialisation métier) en une plateforme industrielle (186 865 lignes Python dans l'état audité du 17 avril, 12 agents spécialisés, sécurité entreprise, architecture Docker production, 3 910 tests collectes, pipeline audit-proof avec rejeu et revue humaine, documentation structurée incluant politique de sécurité, ADR, glossaire et diagrammes C4).

Les développements propriétaires — **898 fichiers modifiés** dans le diff upstream → HEAD au 24 avril 2026 (+213 250 insertions, -14 434 suppressions, soit **198 816 lignes nettes**), pipeline juridique complet, OCR/PDF industriel avec moteur PRISM, pipeline audit-proof (replay, human review, risk register), architecture de déploiement, suite de tests TDD — constituent un **actif logiciel autonome et valorisable**. Ces chiffres sont reproductibles via les commandes de la section 7.1.

Depuis l'audit hostile interne du 3 avril 2026, les quatre failles critiques (P0) ont été corrigées : incoherence de licence resolue, cle HMAC par defaut supprimee, mots de passe retires des logs, RBAC audit_reports aligne avec la politique declaree. Les remediations P1 et P2 partielles ont ete executees le 17 avril 2026 : politique de securite formalisee (SECURITY.md), 5 Architecture Decision Records, glossaire technique, diagrammes C4, benchmark de comparables de marche. Le score de maturite technique est passe de 58/100 a **69/100** (scorecard detaillee dans `audit-hostile-valorisation/07-scorecard-valorisation.md`). Le potentiel apres achevement complet des remediations P2 restantes est estime a 76/100.

Le coût de reproduction, estimé selon la méthode COCOMO II avec des benchmarks industriels (Capers Jones, ISBSG), se situe entre **662 000 €** (hypothèse conservatrice) et **1 889 600 €** (benchmark strict), avec une estimation médiane de **~1 200 000 €**. Apres application de la decote technique residuelle de 12–20 % (score 69/100), la **valeur nette estimee se situe entre 958 000 € et 1 054 000 €**, avec une mediane de **~1 006 000 €**. Ces chiffres reflètent le coût qu'engagerait une équipe de développeurs seniors pour recréer un logiciel fonctionnellement équivalent, hors antériorité PRISM et expertise domaine.

Des factures DICA FRANCE sont disponibles à annexer pour **1 500 €/mois** de revenu récurrent, soit **18 000 €/an en run-rate annualisé**. Ce niveau de revenu ne remplace pas la méthode par coûts de reproduction, mais il renforce significativement la preuve d'exploitabilité commerciale et permet de défendre le haut de la fourchette recommandée. Les pièces disponibles concernant les tests terrain auprès de Centrale Lille / Chaire Construction 4.0 / Pr Zoubeir Lafhaj et de l'écosystème Le Tarmac by inovallée constituent des signaux complémentaires, sous réserve d'annexer les justificatifs correspondants.

Le positionnement comparatif de l'actif, detaille en section 6bis, confirme que cette estimation s'inscrit dans un ordre de grandeur coherent avec les references de marche pour des infrastructures de decision et de confiance, categorie dans laquelle Evidence se situe par ses caracteristiques techniques (consensus multi-agents, auditabilite native, pipeline de conformite, routage deterministe).

La base open-source sert de fondation technique au même titre que Linux sert de fondation à Red Hat Enterprise Linux, ou Apache Spark à Databricks. La valeur réside dans la couche propriétaire de spécialisation, d'intégration, de sécurisation et d'industrialisation.

---

*Ce rapport a été établi à partir de l'analyse du dépôt Git. Toutes les métriques sont reproductibles via les commandes indiquées en section 7.1.*
