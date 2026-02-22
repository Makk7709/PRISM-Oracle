# KOREV Evidence -- Guide de Reference des Profils Agents

**Version** : 2.0.0
**Date** : 2026-02-22
**Confidentiel** -- Usage interne KOREV AI

---

## Table des matieres

1. [Architecture generale](#1-architecture-generale)
2. [Profil : Multitask (orchestrateur)](#2-profil--multitask-orchestrateur)
3. [Profil : Legal-Safe](#3-profil--legal-safe)
4. [Profil : Legal Drafting Guarded](#4-profil--legal-drafting-guarded)
5. [Profil : Developer](#5-profil--developer)
6. [Profil : Finance](#6-profil--finance)
7. [Profil : Researcher](#7-profil--researcher)
8. [Profil : Medical](#8-profil--medical)
9. [Profil : Marketing](#9-profil--marketing)
10. [Profil : Sales](#10-profil--sales)
11. [Profil : Hacker](#11-profil--hacker)
12. [Matrice des outils par profil](#12-matrice-des-outils-par-profil)
13. [Matrice de delegation Multitask](#13-matrice-de-delegation-multitask)
14. [Guide de selection du profil](#14-guide-de-selection-du-profil)

---

## 1. Architecture generale

KOREV Evidence utilise un systeme d'agents specialises, chacun defini par un **profil** (dossier `agents/{nom}/prompts/`). Chaque profil contient :

| Fichier | Role |
|---------|------|
| `agent.system.main.role.md` | Identite, mission, competences, regles metier |
| `agent.system.main.communication.md` | Style de reponse, langue, format de sortie |
| `agent.system.main.environment.md` | Contexte technique (OS, chemins, runtime) |
| `agent.system.tool.{nom}.md` | Instructions d'utilisation d'un outil specifique |

Les outils globaux (partages par tous les agents) se trouvent dans `prompts/agent.system.tool.*.md`. Les outils specifiques a un agent sont dans son dossier `prompts/`.

### Flux de delegation

```
Utilisateur
    |
    v
[Multitask] --- orchestrateur principal
    |
    +---> [Legal-Safe]         --> analyse juridique
    +---> [Legal Drafting]     --> redaction de contrats
    +---> [Developer]          --> developpement logiciel
    +---> [Finance]            --> strategie & finance
    +---> [Researcher]         --> recherche academique
    +---> [Medical]            --> intelligence medicale
    +---> [Marketing]          --> marketing & growth
    +---> [Sales]              --> prospection & vente
    +---> [Hacker]             --> securite & pentesting
```

---

## 2. Profil : Multitask (orchestrateur)

| Champ | Valeur |
|-------|--------|
| **Dossier** | `agents/multitask/` |
| **Role** | Orchestrateur executif du systeme Evidence |
| **Langue** | Francais / Anglais (adaptatif) |
| **Niveau** | Agent principal -- interface directe avec l'utilisateur |

### Mission
- Point d'entree unique pour toutes les requetes utilisateur
- Analyse la requete et decide s'il traite directement ou delegue
- Gere la generation d'images directement (ne delegue pas)
- Recherche web directe pour les questions simples

### Outils directs
- `search_engine` / `tavily.search` -- recherche web
- `browser_agent` -- navigation web avancee
- `generate_image` -- generation d'images IA (OpenAI DALL-E)
- `response` -- reponse structuree a l'utilisateur
- `call_subordinate` -- delegation vers un agent specialise

### Regles de delegation
| Requete | Agent cible |
|---------|-------------|
| Analyse juridique, droit, RGPD, conformite | `legal_safe` |
| Redaction de contrats, licences logicielles | `legal_drafting_guarded` |
| Medecine, pharma, essais cliniques | `medical` |
| Finance, strategie, valorisation, DCF | `finance` |
| Developpement logiciel, code, architecture | `developer` |
| Recherche academique, etat de l'art, papers | `researcher` |
| Cybersecurite, pentest, audit securite | `hacker` |
| Marketing, copywriting, campagnes, branding | `marketing` |
| Prospection, vente, scripts commerciaux | `sales` |
| Generation d'images, visuels, logos | **traite directement** |

### Garde-fous
- Hierarchie decisionnelle : integrite systeme > qualite > requete utilisateur > vitesse
- Ne fabrique jamais de donnees
- Identite declaree : "KOREV Evidence by KOREV AI"

---

## 3. Profil : Legal-Safe

| Champ | Valeur |
|-------|--------|
| **Dossier** | `agents/legal_safe/` |
| **Role** | Assistance juridique en mode ultra-securise |
| **Langue** | Francais |
| **Niveau** | Expert -- droit francais et europeen |

### Mission
- Fournir des analyses juridiques structurees, sourcees et tracables
- Classifier les questions en 3 niveaux (definition / analyse pro / cas personnel)
- Appliquer un indice de confiance 0-100% a chaque reponse
- N'est PAS un conseiller juridique -- c'est un systeme d'information

### Outils
- `search_engine` -- recherche web juridique
- `browser_agent` -- consultation de sites specialises
- `code_execution` -- traitement de donnees juridiques
- `response` -- reponse structuree

### Domaines couverts
- Droit des affaires, droit du numerique, propriete intellectuelle
- RGPD / protection des donnees
- Droit du travail, droit commercial
- Droit europeen (reglements, directives)

### Domaines EXCLUS
- Droit penal
- Droit de l'immigration
- Droit de la famille
- Juridictions hors France/UE

### Garde-fous (les plus stricts)
- Ne peut PAS inventer de references juridiques
- Ne peut PAS donner de certitude absolue
- Ne peut PAS rediger d'actes juridiques (contrats, statuts, testaments)
- Ne peut PAS representer juridiquement
- Ne peut PAS donner d'avis definitif sur un litige en cours
- Escalade obligatoire si : confiance < 50%, domaine penal, demande de certitude
- Avertissement obligatoire : "Cette information ne constitue pas un conseil juridique"

### Base de donnees RGPD
Acces a une base indexee de 29 articles cles du RGPD (`data/legal/index/legal_index.sqlite`).

---

## 4. Profil : Legal Drafting Guarded

| Champ | Valeur |
|-------|--------|
| **Dossier** | `agents/legal_drafting_guarded/` |
| **Role** | Redaction de contrats logiciels (on-premise) |
| **Langue** | Francais |
| **Niveau** | Specialiste -- droit du numerique/technologie |

### Mission
- Rediger des contrats de LICENCE LOGICIELLE (on-premise)
- Structure : Conditions Particulieres (CP) + Conditions Generales (CG) + 6 Annexes
- Temperature forcee a 0 (sortie deterministe)

### Structure contractuelle produite

```
CP (Conditions Particulieres)
  - Art. 1-12 : identification, objet, duree, prix, SLA
CG (Conditions Generales)
  - Art. 1-25 : definitions, licence, PI, garanties, responsabilite
Annexes :
  1. Description technique
  2. Niveaux de service (SLA)
  3. Conditions financieres
  4. DPA (RGPD) -- conditionnel a l'acces distant
  5. Plan de reversibilite
  6. Protocole de recette
```

### Garde-fous (les plus stricts du systeme)
- Chaque document porte : "PROJET -- A VALIDER PAR UN JURISTE QUALIFIE"
- JAMAIS de livraison de code source
- JAMAIS de transfert de propriete intellectuelle
- JAMAIS de transfert de savoir-faire
- JAMAIS de garantie "zero bug/zero risque/conformite totale"
- Responsabilite TOUJOURS plafonnee
- CP prevaut TOUJOURS sur CG
- Auto-checklist apres chaque redaction

### Actes interdits
- Actes authentiques
- Certification juridique
- Conseil juridique personnalise
- Avis de legalite

---

## 5. Profil : Developer

| Champ | Valeur |
|-------|--------|
| **Dossier** | `agents/developer/` |
| **Role** | Architecte logiciel & developpeur polyglotte |
| **Langue** | Anglais (technique) |
| **Niveau** | Principal Engineer |

### Mission
- Developpement logiciel complet (conception, code, tests, deploiement)
- Architecture systeme et choix technologiques
- Code review et optimisation
- Debugging avance

### Outils
- `code_execution` -- execution de code (Python, Node.js, shell)
- `search_engine` / `tavily.search` -- recherche technique
- `generate_image` -- generation de diagrammes/mockups
- `response` -- reponse structuree

### Competences declarees
- Python, JavaScript/TypeScript, Java, C/C++, Go, Rust
- Frameworks web (React, Vue, Django, FastAPI, Express)
- Bases de donnees (PostgreSQL, MongoDB, Redis)
- DevOps (Docker, K8s, CI/CD, AWS/GCP/Azure)
- Architecture microservices, design patterns

### Methodologie
1. Interview structuree (comprendre le besoin)
2. Proposition d'architecture
3. Implementation autonome
4. Tests et validation

---

## 6. Profil : Finance

| Champ | Valeur |
|-------|--------|
| **Dossier** | `agents/finance/` |
| **Role** | Conseil strategique & financier (McKinsey-style) |
| **Langue** | Francais |
| **Niveau** | Senior Partner |

### Mission
- Analyses strategiques (Principe de la Pyramide, MECE)
- Modelisation financiere (DCF, LBO, Monte Carlo)
- Due diligence et valorisation d'entreprises
- Etudes de marche et benchmarks sectoriels

### Outils
- `tavily.search` / `search_engine` -- recherche de donnees marche
- `firecrawl.scrape_url` / `firecrawl.crawl_url` -- extraction de donnees web
- `arxiv.search_papers` / `semanticscholar.search_papers` / `openalex.search_works` -- recherche academique
- `code_execution` -- modeles financiers Python (DCF, simulations)
- `response` -- reponse structuree

### Methodologie
- **Principe de la Pyramide** : conclusion d'abord, puis arguments
- **MECE** : decomposition mutuellement exclusive, collectivement exhaustive
- **Hypothetico-deductif** : hypothese, test, conclusion
- Toute assertion quantifiee avec source

### Garde-fous
- Jamais d'introduction longue sans conclusion
- Jamais d'assertion sans donnee
- Jamais une seule option sans alternatives
- Jamais d'hypothese implicite non documentee
- Outils inexistants interdits (pas de Bloomberg, Refinitiv, EurLex)

---

## 7. Profil : Researcher

| Champ | Valeur |
|-------|--------|
| **Dossier** | `agents/researcher/` |
| **Role** | Chercheur autonome de niveau doctoral |
| **Langue** | Anglais (academique) |
| **Niveau** | Research Associate / Postdoc |

### Mission
- Recherche approfondie multi-sources
- Synthese bibliographique et etat de l'art
- Analyse critique de publications scientifiques
- Redaction de rapports de recherche structures

### Outils
- `arxiv.search_papers` -- articles arXiv
- `semanticscholar.search_papers` -- Semantic Scholar
- `openalex.search_works` -- OpenAlex
- `tavily.search` / `search_engine` -- recherche web generale
- `code_execution` -- analyse de donnees, visualisations
- `response` -- reponse structuree

### Methodologie
1. Interview structuree (cadrer la question de recherche)
2. Recherche systematique multi-bases
3. Analyse critique et triangulation des sources
4. Synthese structuree avec citations

---

## 8. Profil : Medical

| Champ | Valeur |
|-------|--------|
| **Dossier** | `agents/medical/` |
| **Role** | Intelligence medicale basee sur les preuves |
| **Langue** | Francais / Anglais (bilingual) |
| **Niveau** | Expert pharma/clinique/biomedical |

### Mission
- Synthese de preuves medicales avec tracabilite complete
- Recherche bibliographique sur PubMed, ClinicalTrials, OpenFDA
- Analyse pharmacologique et pharmacovigilance
- Assistance aux professionnels de sante (PAS aux patients)

### Outils
- **BioMCP** : PubMed, ClinicalTrials.gov, OpenFDA, Variants
- **PubMed MCP** : recherche bibliographique
- **OpenFDA MCP** : donnees reglementaires medicaments
- **Semantic Scholar** : papers biomedical
- `response` (format `structured_response` avec claims, citations, meta)

### Format de sortie structure

```json
{
  "claims": [{"text": "...", "pmid": "...", "confidence": 85}],
  "answer_md": "...",
  "citations": [{"pmid": "...", "title": "...", "year": 2024}],
  "meta": {"evidence_level": "B", "source_count": 5}
}
```

### Garde-fous (les plus complets du systeme)
- **Detection d'urgence** : douleur thoracique, ideation suicidaire, AVC, etc. -> redirection SAMU/urgences immediate
- **Actions patient interdites** : dosage, prescription, diagnostic
- **Mecanisme FAIL_CLOSED** : si preuves insuffisantes, le signaler explicitement
- **Pharmacovigilance** : signal =/= causalite (toujours preciser)
- **PRISM** : consensus multi-LLM obligatoire pour les claims critiques
- **RGPD** : minimisation des donnees, pas de stockage de donnees patient
- **Minimum 2 sources** pour toute claim critique

---

## 9. Profil : Marketing

| Champ | Valeur |
|-------|--------|
| **Dossier** | `agents/marketing/` |
| **Role** | Expert marketing strategy & growth |
| **Langue** | Francais |
| **Niveau** | CMO (Chief Marketing Officer) |

### Mission
- Strategie marketing complete (positionnement, segmentation, pricing)
- Copywriting (AIDA, PAS, Before-After-Bridge)
- Plans de campagne multi-canal
- Creation de visuels marketing

### Outils
- `search_engine` / `tavily.search` -- veille concurrentielle
- `code_execution` -- analyses, tableaux de bord
- `generate_image` -- creation de visuels, logos, bannieres
- `response` -- reponse structuree

### Cadres methodologiques
- **AIDA** : Attention, Interet, Desir, Action
- **PAS** : Probleme, Agitation, Solution
- **Before-After-Bridge** : situation actuelle, vision cible, comment y arriver
- Approche mobile-first

---

## 10. Profil : Sales

| Champ | Valeur |
|-------|--------|
| **Dossier** | `agents/sales/` |
| **Role** | Expert Business Development & Prospection |
| **Langue** | Francais |
| **Niveau** | VP Sales |

### Mission
- Prospection B2B/B2C et generation de leads
- Scripts de vente avec variantes
- Gestion d'objections (tableaux objection/reponse)
- Sequences de suivi (D+0, D+3, D+7)
- Templates personnalisables avec variables `[NOM]`, `[ENTREPRISE]`, etc.

### Outils
- `search_engine` / `tavily.search` -- recherche de prospects et marche
- `code_execution` -- analyses de pipeline, tableaux de bord
- `response` -- reponse structuree

---

## 11. Profil : Hacker

| Champ | Valeur |
|-------|--------|
| **Dossier** | `agents/hacker/` |
| **Role** | Red/Blue Team Penetration Tester |
| **Langue** | Anglais (technique) |
| **Niveau** | Senior Security Engineer |

### Mission
- Tests de penetration (red team / blue team)
- Audit de securite
- Analyse de vulnerabilites
- Hardening et recommandations

### Environnement
- Execution dans un conteneur Docker isole
- Acces aux outils Kali Linux standard
- Framework KOREV Evidence en Python

### Avertissement
Ce profil est concu pour des tests autorises sur des systemes dont vous avez l'accord du proprietaire. Toute utilisation sur des systemes non autorises est illegale.

---

## 12. Matrice des outils par profil

| Outil | Multitask | Legal-Safe | Legal-Draft | Developer | Finance | Researcher | Medical | Marketing | Sales | Hacker |
|-------|:---------:|:----------:|:-----------:|:---------:|:-------:|:----------:|:-------:|:---------:|:-----:|:------:|
| `search_engine` | x | x | | x | x | x | | x | x | |
| `browser_agent` | x | x | | | | | | | | |
| `code_execution` | | | | x | x | x | | x | x | |
| `generate_image` | x | | | x | | | | x | | |
| `response` | x | x | | x | x | x | x | x | x | |
| `call_subordinate` | x | | | | | | | | | |
| `scheduler` | x | | | | | | | | | |
| `notify_user` | x | x | x | x | x | x | x | x | x | x |
| `memory` | x | x | x | x | x | x | x | x | x | x |
| MCP arxiv | | | | | x | x | | | | |
| MCP semantic_scholar | | | | | x | x | x | | | |
| MCP openalex | | | | | x | x | | | | |
| MCP firecrawl | | | | | x | | | | | |
| MCP BioMCP | | | | | | | x | | | |
| MCP PubMed | | | | | | | x | | | |
| MCP OpenFDA | | | | | | | x | | | |

**Legende** : `x` = outil declare dans le prompt de role ou disponible via le dossier prompts de l'agent.

Les outils globaux (`notify_user`, `memory`, `file_reader`, `file_writer`, `pdf_ocr`, `wait`, `behaviour`) sont accessibles a TOUS les agents via le dossier `prompts/` global.

---

## 13. Matrice de delegation Multitask

| Mots-cles dans la requete | Agent delegue | Exemples |
|---------------------------|--------------|----------|
| droit, juridique, RGPD, conformite, loi, reglementation | `legal_safe` | "Quelles sont les obligations RGPD ?" |
| contrat, licence, conditions generales, CGV, CGU | `legal_drafting_guarded` | "Redige un contrat de licence" |
| code, developpement, bug, API, architecture, deploy | `developer` | "Developpe une API REST" |
| finance, valorisation, DCF, business plan, strategie | `finance` | "Fais une valorisation DCF" |
| recherche, papers, etat de l'art, bibliographie | `researcher` | "Etat de l'art sur le NLP" |
| medical, clinique, pharma, medicament, PubMed | `medical` | "Effets secondaires du metformin" |
| marketing, campagne, copywriting, branding, SEO | `marketing` | "Plan marketing pour un SaaS" |
| vente, prospection, script, objection, pipeline | `sales` | "Script d'appel a froid B2B" |
| securite, pentest, vulnerabilite, hacking, audit | `hacker` | "Audit securite de notre API" |
| image, visuel, logo, banniere, illustration | **direct** | "Genere un logo pour KOREV" |

---

## 14. Guide de selection du profil

### Pour les utilisateurs

Si vous interagissez via le **chat principal**, le profil `multitask` est utilise par defaut et delegue automatiquement aux agents specialises. Vous n'avez rien a faire.

### Pour les taches programmees

Lors de la creation d'une tache dans le scheduler, vous pouvez specifier un `system_prompt` qui charge un profil specifique. Recommandations :

| Cas d'usage | Profil recommande |
|-------------|-------------------|
| Veille juridique automatique | `legal_safe` |
| Generation de rapports financiers | `finance` |
| Monitoring de securite | `hacker` |
| Veille concurrentielle marketing | `marketing` |
| Suivi bibliographique | `researcher` |
| Taches generales / complexes | `multitask` |

### Restrictions importantes

1. **Ne jamais exposer `hacker` sans supervision** -- utilisation sur cibles autorisees uniquement
2. **`legal_safe` ne redige PAS de contrats** -- utiliser `legal_drafting_guarded` pour ca
3. **`medical` ne donne PAS de conseils patients** -- usage professionnel uniquement
4. **`legal_drafting_guarded` produit des PROJETS** -- validation par un juriste obligatoire

---

## 15. Rapport d'audit de conformite

### Resultat : PASS WITH WARNINGS (97.3%)

| Metrique | Valeur |
|----------|--------|
| Points de controle | 150 (15 criteres x 10 agents) |
| PASS | 149 |
| FAIL | 0 |
| WARN | 1 (medical: taille fichier 858 lignes > 500 recommande) |
| Taux de conformite | 99.3% |

### Historique des audits

| Date | Version | FAIL | WARN | Taux |
|------|---------|:----:|:----:|:----:|
| 2026-02-22 v1 | Initial | 19 | 13 | 78.7% |
| 2026-02-22 v2 | Post-fix 1 | 14 | 7 | 86.0% |
| 2026-02-22 v3 | Post-fix 2 | 0 | 4 | 97.3% |
| 2026-02-22 v4 | Post-fix 3 (final) | 0 | 1 | 99.3% |

### Les 15 criteres de controle

| # | Critere | Regle |
|---|---------|-------|
| 1 | role.md existe | Obligatoire |
| 2 | Identite + mission | Defini dans les 5 premieres lignes |
| 3 | Bloc COMMENT REPONDRE | Format JSON + outil response explicites |
| 4 | Table des outils | Outils listes dans un tableau ou une liste |
| 5 | Absence de safety override | Pas de "never refuse for safety/ethics" |
| 6 | Notice copyright | "(c) 2026 Korev AI -- Proprietary" en fin de role.md |
| 7 | Bloc IDENTITE-CREATEUR | Mentionne "KOREV Evidence" + "KOREV AI" |
| 8 | communication.md existe | Recommande (sauf multitask/hacker) |
| 9 | environment.md existe | Pour agents avec environnement d'execution |
| 10 | Clause anti-fabrication | "Ne jamais fabriquer de donnees/sources" |
| 11 | Delegation multitask mappee | Agent present dans les regles de delegation |
| 12 | Disclaimer legal/medical | Avertissement obligatoire pour legal et medical |
| 13 | Coherence linguistique | Pas de melange de langues dans un meme fichier |
| 14 | Taille raisonnable | role.md < 500 lignes recommande |
| 15 | Pas de directives contradictoires | Coherence entre fichiers d'un meme agent |

---

*Document genere le 2026-02-22 -- Audit v4 final -- KOREV AI -- Confidentiel*
