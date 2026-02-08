# KOREV Evidence — Protocole de Demonstration Cabinet d'Avocats

**Document confidentiel — Version 1.0**
**Date : 8 fevrier 2026**
**Destinataire : Direction juridique / Comite d'evaluation technologique**

---

## Table des matieres

1. [Resume executif](#1-resume-executif)
2. [Description complete des fonctionnalites juridiques](#2-description-complete-des-fonctionnalites-juridiques)
3. [Architecture de securite](#3-architecture-de-securite)
4. [Protocole de test — 5 axes d'audit](#4-protocole-de-test--5-axes-daudit)
5. [Resultats d'execution](#5-resultats-dexecution)
6. [Analyse des resultats](#6-analyse-des-resultats)
7. [Limites connues et transparence](#7-limites-connues-et-transparence)
8. [Recommandations](#8-recommandations)

---

## 1. Resume executif

KOREV Evidence est un systeme d'assistance juridique base sur l'IA, concu pour les professionnels du droit. Il ne remplace pas un avocat : il fournit des **analyses structurees, sourcees et tracables** dans un cadre de securite strict.

**Principes fondamentaux :**
- **Fail-closed** : le systeme refuse plutot que de deviner
- **Zero affirmation sans source** : toute assertion doit etre citee ou marquee hypothese
- **Temperature 0** : sorties deterministes, reproductibles
- **Separation des roles** : le redacteur ne juge pas, le juge ne redige pas
- **Veto absolu** : le module de controle juridique a un veto irrevocable

**Suite de certification :** 41 tests couvrant 5 axes d'audit — **100% PASS**.

---

## 2. Description complete des fonctionnalites juridiques

### 2.1 Analyse juridique structuree (Legal-Safe Mode)

Le mode Legal-Safe produit des analyses au format **FIRAC** :

| Section | Description |
|---------|-------------|
| **Facts** | Faits presentes par l'utilisateur (separes du droit) |
| **Issue** | Question juridique identifiee |
| **Rules** | Articles de loi, jurisprudence applicable (avec citations) |
| **Application** | Comment les regles s'appliquent aux faits |
| **Conclusion** | Synthese avec niveau de confiance |

**Controles integres :**

| Controle | Description | Seuil |
|----------|-------------|-------|
| Temperature | Forcee a 0 (determinisme) | Exact |
| Confiance minimale | Escalade si < 0.75 | 75% |
| Sources obligatoires | OPERATIONAL/BOARD requiert des citations | Binaire |
| Claims UNSUPPORTED | Rejet automatique si assertion sans source | Binaire |
| Juridiction | BOARD + UNKNOWN = rejet (pas de presumption FR) | Binaire |

### 2.2 Classification des risques

| Niveau | Exemples | Consensus requis |
|--------|----------|-----------------|
| **LOW** | Definitions, explications | Non |
| **MEDIUM** | Clauses, contrats, RGPD | Oui (2/3) |
| **HIGH** | M&A, IPO, restructuration, contentieux | Oui (unanimite) |

**Detection automatique par patterns :**
- HIGH : M&A (5.0), IPO (5.0), due diligence (5.0), cession d'entreprise (5.0), cassation (4.0)
- MEDIUM : contrat (2.0), clause (2.0), RGPD (2.5), propriete intellectuelle (2.5)

### 2.3 Portees de decision

| Portee | Description | Exigences |
|--------|-------------|-----------|
| **INFO** | Information pure | Aucune |
| **OPERATIONAL** | Conseil operationnel | Sources + Claims |
| **BOARD** | Decision strategique | Sources + Claims + Consensus + Juridiction explicite |

### 2.4 Juge binaire (7 controles)

Le juge binaire est un systeme de validation automatique qui applique 7 controles :

1. **SOURCES_PRESENT** — Rules avec citations obligatoires (OPERATIONAL/BOARD)
2. **FACTS_SEPARATED** — Liste de faits non vide
3. **APPLICATION_PRESENT** — Analyse > 50 caracteres
4. **CLAIMS_REQUIRED** — Claims obligatoires (OPERATIONAL/BOARD)
5. **NO_UNSUPPORTED_CLAIMS** — Zero claim sans source
6. **JURISDICTION_CLEAR** — Juridiction explicite (BOARD : UNKNOWN = FAIL)
7. **ABROGATION_HANDLED** — References abrogees signalees

**Verdicts :**
- `APPROVE` : tous les controles passent
- `REJECT` : controle critique echoue
- `REQUEST_INFO` : information manquante

### 2.5 Consensus multi-LLM

KOREV Evidence utilise un systeme de consensus a 3 arbitres IA independants :

| Parametre | Valeur |
|-----------|--------|
| Nombre d'arbitres | 3 (GPT-4o, Claude 3.5, Gemini Pro) |
| Quorum | 2/3 (66.7%) |
| Timeout global | 10 secondes |
| Timeout par arbitre | 5 secondes |
| Temperature | 0 (deterministe) |
| Simulation en production | **INTERDITE** |

**Criteres d'evaluation par chaque arbitre :**
1. L'action est-elle reversible ?
2. Y a-t-il un risque de perte de donnees ou d'information erronee ?
3. L'action respecte-t-elle les principes ethiques et scientifiques ?
4. Les sources sont-elles verifiables et fiables ?
5. Le contexte justifie-t-il cette conclusion ?
6. Y a-t-il des biais potentiels dans le raisonnement ?

### 2.6 Pipeline de redaction contractuelle (Fail-Closed)

```
REQUETE → ROUTER → LEGAL_DRAFTING_GUARDED → ACT LEAK GUARD → LEGAL_SAFE GATE
                                                                    |
                                                             PASS ← → FAIL
                                                              |          |
                                                           Export    Corrections
                                                           autorise  requises
```

**Structure de sortie :**
- Conditions Particulieres (CP) — prevalence sur CG
- Conditions Generales (CG) — responsabilite plafonnee
- Annexe 1 : Description du logiciel
- Annexe 2 : Support/maintenance + SLA
- Annexe 3 : Securite (acces encadre, journalisation)
- Annexe 4 : DPA RGPD (conditionnelle si acces distant)
- Annexe 5 : Reversibilite (sans remise de code)
- Annexe 6 : Grille tarifaire

### 2.7 Act Leak Guard (Detection de clauses dangereuses)

**16 patterns P0 (BLOQUANTS — 1 seul = contrat bloque) :**

| # | Pattern | Risque |
|---|---------|--------|
| 1 | Remise du code source | Perte de l'actif principal |
| 2 | Livraison du code source | Idem |
| 3 | Code source transfere/transmis/fourni | Idem |
| 4 | Acces au repository Git/SVN | Exposition du code |
| 5 | Sources du logiciel transferees | Perte IP |
| 6 | Cession de droits/propriete/code | Cession IP |
| 7 | Transfert de savoir-faire | Perte de know-how |
| 8 | Garantie zero risque | Promesse irrealiste |
| 9 | Logiciel sans faille | Idem |
| 10 | Conformite totale | Idem |
| 11 | Zero bug/erreur/interruption | Idem |
| 12 | Acces au depot de code | Exposition du code |
| 13 | Garantit la conformite | Garantie absolue |
| 14 | Transfert irrevocable de droits | Cession definitive |
| 15 | Acces libre/illimite aux systemes | Risque securite |
| 16 | Escrow/depot de code source chez tiers | Exposition IP |

**9 patterns P1 (WARNINGS — signales, non bloquants) :**

| # | Pattern | Risque |
|---|---------|--------|
| 1 | SLA 24/7 non encadre | Engagement disproportionne |
| 2 | Disponibilite 99.99%+ | Irrealiste en ON-PREM |
| 3 | Garantie de resultat | Obligation excessive |
| 4 | Obligation de resultat | Art. 1231-1 C. civ. |
| 5 | SLA 99.9% garanti | Sans moyens associes |
| 6 | Traitement de donnees sans role RGPD | Art. 28 RGPD |
| 7 | Indexation ambigue | Art. 1164 C. civ. |
| 8 | Penalites illimitees | Art. 1231-5 C. civ. |
| 9 | Responsabilite sans plafond | Art. 1170, 1231-5 C. civ. |

### 2.8 Controle d'export

| Condition | Export autorise |
|-----------|----------------|
| Gate PASS + can_release = True | OUI |
| Gate REJECT ou P0 present | **NON** |
| Pas de verdict | **NON** |
| Contrat vide | **NON** |

**Stamp d'export :** Chaque contrat exporte porte la mention :
```
VALIDE PAR LEGAL_SAFE GATE — PASS
Date: YYYY-MM-DD HH:MM
Correlation ID: [UUID]
PROJET — A VALIDER PAR UN JURISTE QUALIFIE
```

### 2.9 Gouvernance

| Regle | Valeur | Justification |
|-------|--------|---------------|
| Decision.type | `legal_contract` | Jamais `pricing` ou `strategy` |
| Veto legal_safe | **ABSOLU** | Aucun mecanisme de contournement |
| MULTI_AGENT_CONSENSUS | Ne peut PAS overrider le veto | Separation des roles |
| Export sans PASS | **IMPOSSIBLE** | Fail-closed strict |

### 2.10 Domaines supportes et non supportes

**Supportes (FR/EU) :**
- Droit du travail (licenciement, harcelement, contrats)
- Droit fiscal (TVA, redressement, optimisation)
- RGPD / Protection des donnees (CNIL, DPO, violations)
- Droit des societes (statuts, gouvernance)
- Droit des contrats (clauses, resiliation, force majeure)
- Droit de la consommation
- Propriete intellectuelle

**Non supportes (refus poli) :**
- Droit penal → "Consultez un avocat penaliste"
- Droit de l'immigration
- Droit de la famille
- Juridictions hors FR/EU

**Actes interdits :**
- Redaction d'actes juridiques (sauf via legal_drafting_guarded)
- Representation juridique
- Depot de plainte ou assignation

### 2.11 Disclaimers obligatoires

Chaque sortie juridique contient :

> Cette analyse ne constitue pas un conseil juridique. Elle est fournie a titre informatif uniquement. Pour toute decision importante, consultez un avocat ou un professionnel du droit qualifie. KOREV Evidence decline toute responsabilite quant aux consequences de l'utilisation de ces informations.

Chaque projet de contrat porte :

> PROJET — A VALIDER PAR UN JURISTE QUALIFIE AVANT TOUTE SIGNATURE

### 2.12 Securite applicative

| Mesure | Implementation |
|--------|----------------|
| Authentification | Argon2id, timing-safe |
| Rate limiting | 5 req/min login, 60 req/min API |
| Injection de chemin | `..` bloque, symlinks bloques |
| Injection de commande | Allowlist, metacaracteres bloques |
| Upload | Extensions executables bloquees, MIME verifie, 10MB max |
| Network guard (tests) | Appels LLM reels bloques en test |

---

## 3. Architecture de securite

### 3.1 Pipeline fail-closed

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│   REDACTION   │ ──→ │  LEAK GUARD   │ ──→ │  GATE AUDIT  │
│  (drafting)   │     │  (16 P0, 9 P1)│     │ (fail-closed)│
└──────────────┘     └──────────────┘     └──────┬───────┘
                                                  │
                                           ┌──────┴──────┐
                                           │             │
                                        PASS          REJECT
                                           │             │
                                      ┌────┴────┐   ┌───┴────┐
                                      │ Export   │   │ Liste  │
                                      │ autorise │   │ correc-│
                                      │ + stamp  │   │ tions  │
                                      └─────────┘   └────────┘
```

### 3.2 Consensus multi-LLM

```
┌─────────────────┐
│ Proposition      │
│ juridique        │
└────────┬────────┘
         │
    ┌────┴────┐
    │         │
┌───┴──┐ ┌───┴──┐ ┌──────┐
│GPT-4o│ │Claude│ │Gemini│
│      │ │ 3.5  │ │ Pro  │
└───┬──┘ └───┬──┘ └──┬───┘
    │        │       │
    └────┬───┘───────┘
         │
    ┌────┴────┐
    │ Quorum  │
    │  2/3    │
    └────┬────┘
         │
   ┌─────┴─────┐
   │           │
APPROVE    REJECT
```

### 3.3 Invariants de securite (non negociables)

1. `P0 detecte` → `REJECT` (aucune exception)
2. `Disclaimer absent` → `REJECT`
3. `can_release = True` ⟺ `verdict = APPROVE`
4. `MULTI_AGENT_CONSENSUS` ne peut JAMAIS overrider `legal_safe`
5. `legal_safe` a un veto **ABSOLU**
6. `Temperature = 0` en mode juridique (exception = erreur fatale)
7. `UNSUPPORTED claims` → `REJECT`
8. `BOARD + UNKNOWN jurisdiction` → `REJECT`

---

## 4. Protocole de test — 5 axes d'audit

### 4.1 AXE 1 — Fiabilite juridique (8 tests)

*"Le systeme ne ment-il jamais ?"*

| ID | Test | Verification |
|----|------|-------------|
| AXE1-01 | Claims UNSUPPORTED rejetees | Le juge binaire rejette toute affirmation sans source |
| AXE1-02 | Temperature forcee a 0 | Exception levee si temperature != 0 |
| AXE1-03 | Disclaimer toujours present | `not_legal_advice = True`, texte FR verifie |
| AXE1-04 | Confiance basse → escalade | Seuil 0.75 verifie |
| AXE1-05 | Domaine penal → escalade | `DOMAIN_PENAL` declenche toujours une escalade |
| AXE1-06 | Actes juridiques interdits | Detection de representation, redaction d'actes, depot de plainte |
| AXE1-07 | BOARD + UNKNOWN → REJECT | Pas de presumption FR pour decisions strategiques |
| AXE1-08 | Sources obligatoires (OPERATIONAL) | Pas d'approbation sans sources |

### 4.2 AXE 2 — Securite contractuelle (12 tests)

*"Le systeme protege-t-il les actifs ?"*

| ID | Test | Verification |
|----|------|-------------|
| AXE2-01 | Remise code source → P0 | 4 variantes testees, toutes detectees |
| AXE2-02 | Cession IP → P0 | 3 variantes testees |
| AXE2-03 | Garanties absolues → detectees | 4 variantes testees |
| AXE2-04 | P0 = pas de contrat | Fail-closed strict verifie |
| AXE2-05 | Export bloque sans PASS | `is_export_allowed = False` |
| AXE2-06 | Consensus ne peut pas overrider | `can_consensus_override = False` |
| AXE2-07 | Veto legal_safe absolu | `is_legal_safe_veto_absolute = True` |
| AXE2-08 | Templates 0 fuite IP | Tous les templates scannes, 0 P0 |
| AXE2-09 | Stamp export certifie | Mention LEGAL_SAFE dans le stamp |
| AXE2-10 | Responsabilite plafonnee | Plafond present dans les CG |
| AXE2-11 | DPA conditionnelle | NON APPLICABLE sans acces distant, active avec |
| AXE2-12 | Reversibilite sans code | Annexe 5 sans remise de code source |

### 4.3 AXE 3 — Conformite RGPD / Deontologie (6 tests)

*"Le systeme respecte-t-il les obligations reglementaires ?"*

| ID | Test | Verification |
|----|------|-------------|
| AXE3-01 | Domaine RGPD reconnu | Keywords RGPD, CNIL, donnees personnelles |
| AXE3-02 | Conflit d'interet → escalade | Trigger `CONFLICT_OF_INTEREST` existe |
| AXE3-03 | Hors perimetre → refus | Trigger `OUT_OF_SCOPE` existe |
| AXE3-04 | RGPD sans DPA → detecte | Traitement de donnees sans role RGPD detecte |
| AXE3-05 | No PII in logs | Provenance et tracabilite sans donnees personnelles |
| AXE3-06 | Certitude demandee → refusee | Patterns de certitude detectes |

### 4.4 AXE 4 — Robustesse / Fail-closed (7 tests)

*"Que se passe-t-il quand le systeme est sous stress ?"*

| ID | Test | Verification |
|----|------|-------------|
| AXE4-01 | Disclaimer absent → REJECT | Gate rejette sans disclaimer |
| AXE4-02 | Pas de quorum → pas d'approbation | Aucun mecanisme d'auto-approbation |
| AXE4-03 | Simulation interdite en production | `simulation_enabled = False` par defaut |
| AXE4-04 | Network guard actif | Appels LLM reels bloques en test |
| AXE4-05 | Timeouts configures | `global_timeout_ms` et `per_arbiter_timeout_ms` presents |
| AXE4-06 | Rapport d'audit structure | Contient verdict, P0/P1, sections AUDIT CONTRACTUEL |
| AXE4-07 | Pipeline E2E integre | Contrat complet genere, 0 fuite, export autorise |

### 4.5 AXE 5 — Tracabilite / Auditabilite (8 tests)

*"Peut-on reconstituer le raisonnement devant un juge ?"*

| ID | Test | Verification |
|----|------|-------------|
| AXE5-01 | Correlation ID unique | UUID valide, different a chaque generation |
| AXE5-02 | Verdict reproductible | Memes inputs → meme verdict |
| AXE5-03 | Findings detailles | Severity, pattern, context, recommendation, section |
| AXE5-04 | Rapport d'audit exportable | String structure > 100 caracteres |
| AXE5-05 | Variables manquantes tracees | `[A COMPLETER: ...]` dans le texte |
| AXE5-06 | Decision.type correct | `legal_contract` (jamais pricing/strategy) |
| AXE5-07 | Documentation existe | README.md avec diagramme pipeline |
| AXE5-08 | Leak Guard exhaustif | ≥16 P0 + ≥9 P1 patterns |

---

## 5. Resultats d'execution

### 5.1 Commande d'execution

```bash
KOREV_ENV=development python3 -m pytest tests/test_demo_cabinet_avocats.py -v
```

### 5.2 Resultats

```
AXE 1 — FIABILITE JURIDIQUE
  [AXE1-01] Claims UNSUPPORTED rejetees ................... PASS
  [AXE1-02] Temperature forcee a 0 ........................ PASS
  [AXE1-03] Disclaimer toujours present ................... PASS
  [AXE1-04] Confiance basse → escalade .................... PASS
  [AXE1-05] Domaine penal → escalade ...................... PASS
  [AXE1-06] Actes juridiques interdits .................... PASS
  [AXE1-07] BOARD + UNKNOWN → REJECT ...................... PASS
  [AXE1-08] Sources obligatoires (OPERATIONAL) ............ PASS

AXE 2 — SECURITE CONTRACTUELLE
  [AXE2-01] Remise code source → P0 ....................... PASS
  [AXE2-02] Cession IP → P0 .............................. PASS
  [AXE2-03] Garanties absolues → detectees ................ PASS
  [AXE2-04] P0 = pas de contrat ........................... PASS
  [AXE2-05] Export bloque sans PASS ....................... PASS
  [AXE2-06] Consensus ne peut pas overrider ............... PASS
  [AXE2-07] Veto legal_safe absolu ........................ PASS
  [AXE2-08] Templates 0 fuite IP .......................... PASS
  [AXE2-09] Stamp export certifie ......................... PASS
  [AXE2-10] Responsabilite plafonnee ...................... PASS
  [AXE2-11] DPA conditionnelle ............................ PASS
  [AXE2-12] Reversibilite sans code ....................... PASS

AXE 3 — CONFORMITE RGPD / DEONTOLOGIE
  [AXE3-01] Domaine RGPD reconnu .......................... PASS
  [AXE3-02] Conflit d'interet → escalade .................. PASS
  [AXE3-03] Hors perimetre → refus ........................ PASS
  [AXE3-04] RGPD sans DPA → detecte ....................... PASS
  [AXE3-05] No PII in logs ................................ PASS
  [AXE3-06] Certitude demandee → refusee .................. PASS

AXE 4 — ROBUSTESSE / FAIL-CLOSED
  [AXE4-01] Disclaimer absent → REJECT .................... PASS
  [AXE4-02] Pas de quorum → pas d'approbation ............. PASS
  [AXE4-03] Simulation interdite en production ............ PASS
  [AXE4-04] Network guard actif ........................... PASS
  [AXE4-05] Timeouts configures ........................... PASS
  [AXE4-06] Rapport d'audit structure ..................... PASS
  [AXE4-07] Pipeline E2E integre .......................... PASS

AXE 5 — TRACABILITE / AUDITABILITE
  [AXE5-01] Correlation ID unique ......................... PASS
  [AXE5-02] Verdict reproductible ......................... PASS
  [AXE5-03] Findings detailles ............................ PASS
  [AXE5-04] Rapport d'audit exportable .................... PASS
  [AXE5-05] Variables manquantes tracees .................. PASS
  [AXE5-06] Decision.type correct ......................... PASS
  [AXE5-07] Documentation existe .......................... PASS
  [AXE5-08] Leak Guard exhaustif .......................... PASS

──────────────────────────────────────────────────────
RESULTAT FINAL : 41 PASS / 41 TESTS — 100% REUSSITE
──────────────────────────────────────────────────────
```

---

## 6. Analyse des resultats

### 6.1 Synthese par axe

| Axe | Tests | PASS | Taux |
|-----|-------|------|------|
| AXE 1 — Fiabilite juridique | 8 | 8 | 100% |
| AXE 2 — Securite contractuelle | 12 | 12 | 100% |
| AXE 3 — Conformite RGPD | 6 | 6 | 100% |
| AXE 4 — Robustesse | 7 | 7 | 100% |
| AXE 5 — Tracabilite | 8 | 8 | 100% |
| **TOTAL** | **41** | **41** | **100%** |

### 6.2 Points forts identifies

1. **Fail-closed systemique** — Le systeme refuse dans TOUS les cas de doute. Aucun mecanisme de contournement n'existe. Un P0 bloque TOUJOURS l'export, meme si les 3 arbitres LLM approuvent.

2. **Separation des roles** — `legal_drafting_guarded` (redacteur) et `legal_safe` (juge/gate) sont strictement separes. Le juge a un veto absolu que le consensus multi-agent ne peut pas overrider.

3. **Detection de clauses dangereuses** — 16 patterns P0 + 9 patterns P1 couvrent les fuites de code source, les cessions de PI, les garanties absolues, les violations RGPD, les penalites disproportionnees.

4. **Tracabilite complete** — Chaque contrat a un UUID, chaque finding a severity + pattern + context + recommendation + section + reference legale.

5. **DPA conditionnelle** — L'annexe DPA RGPD n'est activee que si l'editeur a un acces distant aux systemes du client, evitant les obligations RGPD inutiles.

### 6.3 Coverage des risques juridiques

| Risque | Couvert | Mecanisme |
|--------|---------|-----------|
| Fuite de code source | OUI | 5 patterns P0 |
| Cession de PI | OUI | 2 patterns P0 |
| Transfert de savoir-faire | OUI | 1 pattern P0 |
| Garanties absolues | OUI | 4 patterns P0 |
| Responsabilite illimitee | OUI | 1 pattern P1 + CG |
| RGPD sans DPA | OUI | 1 pattern P1 + DPA conditionnelle |
| SLA irrealiste | OUI | 3 patterns P1 |
| Penalites disproportionnees | OUI | 1 pattern P1 |
| Indexation ambigue | OUI | 1 pattern P1 |

---

## 7. Limites connues et transparence

### 7.1 Ce que KOREV Evidence ne fait PAS

| Limitation | Detail |
|------------|--------|
| Verification de jurisprudence | Le systeme ne verifie pas qu'un numero d'arret existe sur Legifrance |
| Conseil juridique | Toute sortie porte un disclaimer explicite |
| Droit penal | Domaine refuse avec escalade automatique |
| Juridictions hors FR/EU | Refus explicite |
| Redaction d'actes | Seuls des PROJETS sont produits (sauf legal_drafting_guarded) |

### 7.2 Dependance aux LLM cloud

Les analyses juridiques passent par des LLM cloud (OpenRouter → OpenAI, Anthropic, Google). Cela implique :

- Les documents injectes transitent par des serveurs tiers
- Le secret professionnel n'est garanti que si un DPA est signe avec chaque provider
- Un deploiement ON-PREM est recommande pour les dossiers confidentiels

### 7.3 Risque residuel

- **Hallucination de references** : le systeme peut citer un article qui n'existe pas. Attenuation : le juge binaire exige des sources, mais ne verifie pas leur existence reelle.
- **Biais des modeles** : les LLM ont des biais inherents. Attenuation : consensus multi-LLM (3 modeles differents).

---

## 8. Recommandations

### Pour un cabinet d'avocats evaluant KOREV Evidence :

1. **Usage recommande** : analyses preliminaires, veille juridique, structuration de dossiers
2. **Usage deconseille** : production de documents finaux sans relecture humaine
3. **Prerequis** : DPA signe avec les providers LLM si donnees confidentielles
4. **Deploiement** : ON-PREM pour les dossiers sous secret professionnel
5. **Formation** : les utilisateurs doivent comprendre les disclaimers et les limites

### Pour executer la suite de certification :

```bash
# Suite complete demonstration cabinet (41 tests)
KOREV_ENV=development python3 -m pytest tests/test_demo_cabinet_avocats.py -v

# Suite contractuelle complete (152 tests)
python3 -m pytest tests/test_contract_drafting.py tests/test_contract_drafting_phase2.py \
  tests/test_control_prompt_ultra_strict.py tests/test_final_control_prompt.py -v

# Suite juridique complete (393 tests)
KOREV_ENV=development python3 -m pytest tests/test_contract_drafting.py \
  tests/test_contract_drafting_phase2.py tests/test_control_prompt_ultra_strict.py \
  tests/test_final_control_prompt.py tests/test_demo_cabinet_avocats.py \
  tests/test_legal_pipeline.py tests/test_legal_safe.py \
  tests/test_harness_integrity.py tests/test_user_entry_gate.py -v
```

---

**Document produit par KOREV AI — (c) 2026 Proprietary & Confidential**
**Suite de tests : `tests/test_demo_cabinet_avocats.py` — 41 tests, 5 axes, 100% PASS**
