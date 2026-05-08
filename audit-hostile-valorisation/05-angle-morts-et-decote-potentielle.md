# 05 — Angles Morts et Decote Potentielle

**Projet** : KOREV Evidence  
**Date** : 3 avril 2026 (mise a jour : 17 avril 2026)  
**Objectif** : identifier tout ce qui pourrait etre utilise pour decoter la valeur du projet lors d'une due diligence hostile  
**Note** : Les items marques ✅ ont ete corriges. Les decotes ont ete recalculees en consequence.

---

## 1. Dependance apporteur / inventeur

### Constat

Le projet est manifestement l'oeuvre d'un apporteur et inventeur technique principal (sinon unique). Les indices :
- Style de code homogene mais avec des traces de multi-iteration (code commente, chemins alternatifs).
- `helpers/` de 181 fichiers et 77 155 lignes maitrisees par une seule personne.
- Pas de `CODEOWNERS` ni de matrice de responsabilites.
- Pas de contributor guide exploitable.
- ~~Les decisions architecturales ne sont tracees nulle part sous forme d'ADR~~ ✅ **5 ADR crees le 17 avril 2026** (PRISM, router, Evidence, LiteLLM, extensions).
- **Attenuations** : guide d'onboarding v7.1 (1 196 lignes), 5 ADR, GLOSSARY.md (30+ termes), diagrammes C4 a 3 niveaux, SECURITY.md.

### Exploitation par un contradicteur

> *"La totalite de la propriete intellectuelle repose dans la tete d'une seule personne. En cas de depart, l'actif devient un depot de code incomprehensible de 186 865 lignes Python."*

### Decote estimee : 10-15% (precedemment 12-20%)

Les 5 ADR, le glossaire, les diagrammes C4 et le SECURITY.md reduisent le temps d'onboarding estime de 2-3 semaines a ~1.5-2 semaines. Un acquereur appliquera toujours un discount "key-man", mais la documentation structurelle attenue le risque.

---

## 2. ~~Incoherence de licence~~ ✅ CORRIGE

### Constat initial

`README.md` affichait un badge MIT. `LICENSE` declarait un logiciel proprietaire.

### Statut : CORRIGE (3 avril 2026)

Le badge affiche desormais "License-Proprietary". Les fichiers `LICENSE` et `legal/KOREV_LICENSE.txt` sont coherents. La notice MIT tiers est correctement documentee dans `legal/THIRD_PARTY_NOTICES.txt`.

### Decote estimee : 0% (precedemment variable/eliminatoire)

Le risque juridique est neutralise. Un contradicteur ne peut plus exploiter cette incoherence.

---

## 3. Failles de securite vs narratif "IA de confiance"

### Constat

Le positionnement produit repose sur la confiance, l'auditabilite, la conformite AI Act/RGPD. Etat actuel :
- ~~Cle HMAC par defaut en dur~~ ✅ CORRIGE — `RuntimeError` si `EVIDENCE_HMAC_KEY` absent
- Mode sans authentification quand aucune config n'est fournie — **toujours present**
- ~~Mot de passe affiche en clair dans les logs~~ ✅ CORRIGE — placeholder generique
- ~~RBAC incoherent sur les rapports d'audit~~ ✅ CORRIGE — aligne avec la politique
- Masquage de secrets qui echoue silencieusement (`except: pass`) — **toujours present**
- **NOUVEAU** : pipeline audit-proof (replay engine, human review, dynamic risk register) renforce la credibilite

### Exploitation par un contradicteur

> *"Les failles critiques ont ete corrigees, mais le mode sans authentification par defaut et le masquage fail-open subsistent. Le pipeline audit-proof est une avancee significative mais n'a pas encore ete valide par un audit externe."*

### Decote estimee : 5-10% (precedemment 10-20%)

Les corrections P0 reduisent significativement le delta narratif/realite. Le pipeline audit-proof renforce la credibilite.

---

## 4. Absence de CI/CD mature

### Constat

- Pas de build Docker en CI (l'image est construite sur le serveur de production)
- Pas de SAST, scanning de dependances, Dependabot
- Suite de tests etendue non-bloquante
- Pas de deploiement automatise
- Pas de registre d'images versionnees

### Exploitation par un contradicteur

> *"Le deploiement repose sur un build manuel sur le serveur de production. Il n'y a pas de pipeline CI/CD complete, pas de scanning de securite des dependances. C'est un processus artisanal, pas industriel."*

### Decote estimee : 5-10%

L'absence de CI/CD complete est un signal de maturite operationnelle insuffisante pour un produit commercial.

---

## 5. Zones non prouvables

### Constat

Plusieurs affirmations implicites du projet ne sont pas prouvables par un tiers :

| Affirmation | Preuve dans le depot |
|---|---|
| "3 910 tests" | Reference documentaire avec parametrisation. La collecte locale Python 3.9 du 25 avril a ete interrompue apres 3 608 tests collectes et 19 erreurs de compatibilite ; la suite etendue reste non-bloquante. |
| "Conformite AI Act" | La grille de conformite est auto-evaluee. Pas d'audit externe. |
| "Integrite cryptographique" | ✅ HMAC desormais obligatoire (`RuntimeError` si cle absente). RSA optionnel et dependant de la config. |
| "Pipeline deterministe" | Le router est deterministe par construction (hash-based), mais le consensus depend des LLMs — inheritement non-deterministe. |
| "11/11 ecarts corriges" | La feuille de route documente les corrections, mais pas de test de regression specifique par ecart. |
| "Multi-tenant securise" | Les tests couvrent l'autorisation, mais pas d'audit de penetration. |
| "Pipeline audit-proof" | ✅ Replay engine, human review workflow et dynamic risk register existent dans le code. Tests e2e presents (347 lignes). |

### Exploitation par un contradicteur

> *"Les affirmations de conformite et de securite sont auto-certifiees. L'audit hostile interne et les corrections P0 sont un bon signal, mais aucun audit externe, certificat ni rapport de penetration ne sont disponibles."*

### Decote estimee : 3-10% (precedemment 5-15%)

---

## 6. Documentation absente pour valorisation

### Constat

Documents manquants qui sont attendus dans un dossier de valorisation technique :

| Document | Impact | Statut |
|---|---|---|
| ~~Architecture Decision Records (ADR)~~ | ~~Impossible de justifier les choix techniques~~ | ✅ FAIT (17 avril 2026) — 5 ADR dans `docs/adr/` |
| Schema de donnees formel | Impossible d'evaluer la complexite du modele | |
| API Reference (OpenAPI) | Impossible d'evaluer la surface d'integration | |
| ~~SECURITY.md~~ | ~~Pas de politique de securite visible~~ | ✅ FAIT (17 avril 2026) |
| Benchmarks de performance | Pas de metriques de latence, throughput, fiabilite | |
| ~~Comparaison concurrentielle~~ | ~~Pas de positionnement technique vs alternatives~~ | ✅ FAIT (17 avril 2026) — benchmark dans section 6bis |
| Historique des incidents | Pas de post-mortem, pas de resilience documentee | |

### Exploitation par un contradicteur

> *"Les ADR, SECURITY.md et le benchmark de comparables sont desormais en place, mais il manque toujours un schema de donnees, une API reference et des benchmarks de performance pour completer le dossier."*

### Decote estimee : 3-5% (precedemment 8-12%)

---

## 7. ~~Architecture pas assez explicitee~~ — PARTIELLEMENT CORRIGE

### Constat initial

- ~~Pas de diagramme C4~~ ✅ **3 niveaux C4 + diagramme de sequence en Mermaid** crees le 17 avril 2026 (`docs/ARCHITECTURE_C4_DIAGRAMS.md`)
- `docs/architecture.md` (307 lignes) est un melange de contenu upstream et fork-specifique — **toujours present**
- ~~Le flux de donnees entre agent → consensus → Evidence → persistence n'est documente dans aucun diagramme~~ ✅ **Diagramme de sequence dans le C4**
- Les frontieres entre modules ne sont pas formalisees (pas d'interface explicite entre helpers) — **attenue par le C4 composants et les ADR**

### Exploitation par un contradicteur

> *"Les diagrammes C4 et les ADR rendent l'architecture explicite. Le temps de comprehension est reduit de 2-3 semaines a ~1.5-2 semaines. Cependant, les frontieres entre les 181 fichiers de helpers ne sont toujours pas formalisees par des interfaces."*

### Decote estimee : 2-5% (precedemment 5-10%)

---

## 8. Risques de perception

### "Fork sophistique" vs "creation originale"

Le depot contient des traces de son origine fork :
- `DockerfileLocal` et `docker/` avec base image `korevai/korev-oracle-base` (Kali-based)
- Certains docs mentionnent des concepts upstream (Agent Zero)
- La structure `knowledge/`, `instruments/`, `prompts/` suit un pattern pre-existant

Un contradicteur pourrait argumenter que la valeur ajoutee reelle (Evidence, PRISM, legal pipeline, conformite) est une surcouche sur un framework open source, et non un actif cree from scratch.

### "Produit" vs "demo sophistiquee"

La coexistence de profils comme `hacker`, `marketing`, `sales`, `medical`, `legal_safe`, `researcher` peut etre lue positivement (polyvalence) ou negativement (dispersion, manque de focus produit).

### Decote estimee : 5-10%

---

## 9. Tableau recapitulatif des risques de decote

| Risque | Decote actuelle (17 avr.) | Decote post-P0 | Decote initiale (3 avr.) | Neutralisable ? |
|---|---|---|---|---|
| Dependance apporteur / inventeur | **10-15%** | 12-20% | 15-25% | ✅ Attenue (5 ADR, glossaire, C4, onboarding) |
| ~~Incoherence de licence~~ | ✅ 0% | ✅ 0% | Variable/eliminatoire | **FAIT** |
| Failles secu vs narratif confiance | 5-10% | 5-10% | 10-20% | Partiellement (P0 + SECURITY.md) |
| CI/CD immature | 5-10% | 5-10% | 5-10% | Oui (1-2 semaines) |
| Zones non prouvables | 3-10% | 3-10% | 5-15% | Partiellement (audit-proof pipeline) |
| Documentation absente | **3-5%** | 8-12% | 10-15% | ✅ Largement attenue (ADR, SECURITY.md, glossaire, C4, benchmark) |
| Architecture implicite | **2-5%** | 5-10% | 5-10% | ✅ Largement attenue (C4, ADR, glossaire) |
| Perception fork/demo | 5-10% | 5-10% | 5-10% | Partiellement (documentation de valeur ajoutee) |
| **Cumul maximal theorique** | **~33-65%** | ~43-82% | ~60-115% | — |
| **Cumul realiste** | **~12-20%** | ~15-25% | ~25-40% | **Reducible a 8-12% apres P1-P2 restants** |

> **Note** : Les decotes ne sont pas strictement additives. Un cabinet appliquera un jugement global en ponderant les risques. L'estimation "cumul realiste" tient compte des correlations entre risques.
