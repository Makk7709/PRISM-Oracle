<!-- markdownlint-disable MD056 -- les placeholders {LOW|MEDIUM|HIGH} contiennent des pipes que le linter compte comme des colonnes de tableau -->
# KOREV Evidence — Template Rapport Evidence-Native

> **Version**: 1.0.0  
> **Statut**: Production  
> **Ce document est le template de référence pour tous les rapports Evidence.**

---

## Instructions d'utilisation

Ce template définit le format obligatoire pour les rapports "Evidence-native".  
Chaque section est **obligatoire** sauf mention contraire.  
Les tables marquées `[REQUIRED]` doivent contenir **au moins une entrée**.

---

<!-- ═══════════════════════════════════════════════════════════════════════════ -->
<!-- BLOC A — DECISION GOVERNANCE (EN-TÊTE OBLIGATOIRE)                         -->
<!-- ═══════════════════════════════════════════════════════════════════════════ -->

# {TITRE_DU_RAPPORT}

**Date de génération**: {DATE}  
**Version**: {VERSION}  
**Auteur système**: KOREV Evidence  

---

## Decision Governance

| Attribut | Valeur |
|----------|--------|
| **Criticité** | `{LOW|MEDIUM|HIGH}` |
| **Mode de validation** | `{SINGLE|DEBATE|CONSENSUS}` |
| **Quorum** | 2/3 votes effectifs |
| **Statut** | `{APPROVED|NO_CONSENSUS|INFRA_FAILURE|PENDING}` |
| **Arbitres** | {LISTE_ARBITRES} |
| **Correlation ID** | `{UUID}` |

> **Règle FAIL_CLOSED**: En mode HIGH, si `NO_CONSENSUS` ou `UNVERIFIED` sur un point structurant, aucune recommandation ferme n'est émise.

### Informations manquantes (si applicable)

<!-- Si FAIL_CLOSED, lister ici les informations requises pour conclure -->

- {ITEM_MANQUANT_1}
- {ITEM_MANQUANT_2}

---

<!-- ═══════════════════════════════════════════════════════════════════════════ -->
<!-- BLOC B — EXECUTIVE SUMMARY                                                  -->
<!-- ═══════════════════════════════════════════════════════════════════════════ -->

## A. Executive Summary

> **Conclusion first** — Cette section résume les conclusions et recommandations clés.

### Conclusions principales

1. {CONCLUSION_1}
2. {CONCLUSION_2}
3. {CONCLUSION_3}

### Recommandations prioritaires

| Priorité | Recommandation | Risque couvert | Badge |
|----------|----------------|----------------|-------|
| P1 | {RECO_1} | {RISQUE_ID} | `{VERIFIED|PARTIAL|UNVERIFIED}` |
| P2 | {RECO_2} | {RISQUE_ID} | `{VERIFIED|PARTIAL|UNVERIFIED}` |
| P3 | {RECO_3} | {RISQUE_ID} | `{VERIFIED|PARTIAL|UNVERIFIED}` |

### Décisions structurantes

- **Décision 1**: {RÉSUMÉ} — Statut: `{APPROVED|PENDING}`
- **Décision 2**: {RÉSUMÉ} — Statut: `{APPROVED|PENDING}`

---

<!-- ═══════════════════════════════════════════════════════════════════════════ -->
<!-- BLOC C — CONTEXTE & PÉRIMÈTRE                                              -->
<!-- ═══════════════════════════════════════════════════════════════════════════ -->

## B. Contexte & Périmètre

### Contexte client

| Attribut | Valeur |
|----------|--------|
| **Client** | {NOM_CLIENT} |
| **Secteur** | {SECTEUR} |
| **Sites concernés** | {LISTE_SITES} |
| **Effectif** | {EFFECTIF} |
| **Contraintes réglementaires** | {NIS2|ISO27001|RGPD|...} |

### Périmètre de l'étude

#### IN (inclus dans le périmètre)

- {ELEMENT_IN_1}
- {ELEMENT_IN_2}
- {ELEMENT_IN_3}

#### OUT (exclus du périmètre)

- {ELEMENT_OUT_1}
- {ELEMENT_OUT_2}

### Sources de données utilisées

| Source | Type | Fiabilité | Date collecte |
|--------|------|-----------|---------------|
| {SOURCE_1} | `{PRIMARY|SECONDARY|TERTIARY}` | `{HIGH|MEDIUM|LOW}` | {DATE} |
| {SOURCE_2} | `{PRIMARY|SECONDARY|TERTIARY}` | `{HIGH|MEDIUM|LOW}` | {DATE} |

---

<!-- ═══════════════════════════════════════════════════════════════════════════ -->
<!-- BLOC D — HYPOTHÈSES                                                        -->
<!-- ═══════════════════════════════════════════════════════════════════════════ -->

## C. Hypothèses

> **Explicite > Implicite** — Liste des hypothèses sur lesquelles repose l'analyse.

| ID | Hypothèse | Impact si fausse | Vérifiable? |
|----|-----------|------------------|-------------|
| H-001 | {HYPOTHESE_1} | {IMPACT} | `{YES|NO|PARTIAL}` |
| H-002 | {HYPOTHESE_2} | {IMPACT} | `{YES|NO|PARTIAL}` |
| H-003 | {HYPOTHESE_3} | {IMPACT} | `{YES|NO|PARTIAL}` |

---

<!-- ═══════════════════════════════════════════════════════════════════════════ -->
<!-- BLOC E — REGISTRE DES RISQUES                                              -->
<!-- ═══════════════════════════════════════════════════════════════════════════ -->

## D. Registre des Risques [REQUIRED]

> **Threat model** — Identification et évaluation des risques.

| ID | Risque | Impact | Probabilité | Score | Contrôles existants | Contrôles proposés |
|----|--------|--------|-------------|-------|---------------------|---------------------|
| R-001 | {RISQUE_1} | `{CRITICAL|HIGH|MEDIUM|LOW}` | `{CERTAIN|LIKELY|POSSIBLE|UNLIKELY}` | {1-25} | {CONTROLES} | {PROPOSITIONS} |
| R-002 | {RISQUE_2} | `{CRITICAL|HIGH|MEDIUM|LOW}` | `{CERTAIN|LIKELY|POSSIBLE|UNLIKELY}` | {1-25} | {CONTROLES} | {PROPOSITIONS} |
| R-003 | {RISQUE_3} | `{CRITICAL|HIGH|MEDIUM|LOW}` | `{CERTAIN|LIKELY|POSSIBLE|UNLIKELY}` | {1-25} | {CONTROLES} | {PROPOSITIONS} |

### Matrice de criticité

```text
                        IMPACT
                LOW    MEDIUM    HIGH    CRITICAL
PROBABILITÉ  ┌─────────────────────────────────────┐
  CERTAIN    │   M   │    H    │   C   │    C     │
  LIKELY     │   L   │    M    │   H   │    C     │
  POSSIBLE   │   L   │    M    │   M   │    H     │
  UNLIKELY   │   L   │    L    │   M   │    M     │
             └─────────────────────────────────────┘
L=Low, M=Medium, H=High, C=Critical
```

---

<!-- ═══════════════════════════════════════════════════════════════════════════ -->
<!-- BLOC F — DÉCISIONS D'ARCHITECTURE                                          -->
<!-- ═══════════════════════════════════════════════════════════════════════════ -->

## E. Décisions d'Architecture [REQUIRED]

> **Arbitrages explicites** — Chaque décision structurante avec justification et alternatives.

### Table des décisions

| ID | Décision | Justification | Risques couverts | Trade-offs | Statut |
|----|----------|---------------|------------------|------------|--------|
| D-001 | {DECISION_1} | {JUSTIFICATION} | R-001, R-002 | {TRADEOFFS} | `{VERIFIED|PARTIAL|UNVERIFIED}` |
| D-002 | {DECISION_2} | {JUSTIFICATION} | R-003 | {TRADEOFFS} | `{VERIFIED|PARTIAL|UNVERIFIED}` |

### Alternatives écartées [REQUIRED]

> **Montrer le raisonnement** — Pour chaque décision structurante, les options non retenues.

#### D-001: {TITRE_DECISION}

| Alternative | Avantages | Inconvénients | Raison du rejet |
|-------------|-----------|---------------|-----------------|
| Option A (retenue) | {AVANTAGES} | {INCONVÉNIENTS} | **Retenue** |
| Option B | {AVANTAGES} | {INCONVÉNIENTS} | {RAISON_REJET} |
| Option C | {AVANTAGES} | {INCONVÉNIENTS} | {RAISON_REJET} |

#### D-002: {TITRE_DECISION}

| Alternative | Avantages | Inconvénients | Raison du rejet |
|-------------|-----------|---------------|-----------------|
| Option A (retenue) | {AVANTAGES} | {INCONVÉNIENTS} | **Retenue** |
| Option B | {AVANTAGES} | {INCONVÉNIENTS} | {RAISON_REJET} |

---

<!-- ═══════════════════════════════════════════════════════════════════════════ -->
<!-- BLOC G — ARCHITECTURE CIBLE                                                -->
<!-- ═══════════════════════════════════════════════════════════════════════════ -->

## F. Architecture Cible

### Vue d'ensemble

```json
{SCHÉMA_ARCHITECTURE_ASCII}
```

### Annotations critiques

| Zone | Composant | Criticité | SPOF? | PRA? | Notes |
|------|-----------|-----------|-------|------|-------|
| {ZONE} | {COMPOSANT_1} | `{HIGH|MEDIUM|LOW}` | `{YES|NO}` | `{YES|NO}` | {NOTES} |
| {ZONE} | {COMPOSANT_2} | `{HIGH|MEDIUM|LOW}` | `{YES|NO}` | `{YES|NO}` | {NOTES} |

### Points de bascule PRA

| Scénario | Composant source | Composant cible | RTO | RPO |
|----------|------------------|-----------------|-----|-----|
| {SCENARIO_1} | {SOURCE} | {CIBLE} | {RTO} | {RPO} |
| {SCENARIO_2} | {SOURCE} | {CIBLE} | {RTO} | {RPO} |

### Zones IT/OT (si applicable)

| Zone | Type | Isolation | Flux autorisés |
|------|------|-----------|----------------|
| {ZONE_1} | `{IT|OT|DMZ}` | {ISOLATION} | {FLUX} |
| {ZONE_2} | `{IT|OT|DMZ}` | {ISOLATION} | {FLUX} |

---

<!-- ═══════════════════════════════════════════════════════════════════════════ -->
<!-- BLOC H — PLAN DE MISE EN ŒUVRE                                             -->
<!-- ═══════════════════════════════════════════════════════════════════════════ -->

## G. Plan de Mise en Œuvre

### Vision 30/60/90 jours

#### Phase 1 — 30 premiers jours (Quick Wins)

| Action | Responsable | Dépendances | Livrable | Badge |
|--------|-------------|-------------|----------|-------|
| {ACTION_1} | {RESP} | {DEPS} | {LIVRABLE} | `{VERIFIED|PARTIAL|UNVERIFIED}` |
| {ACTION_2} | {RESP} | {DEPS} | {LIVRABLE} | `{VERIFIED|PARTIAL|UNVERIFIED}` |

#### Phase 2 — 60 jours (Fondations)

| Action | Responsable | Dépendances | Livrable | Badge |
|--------|-------------|-------------|----------|-------|
| {ACTION_3} | {RESP} | {DEPS} | {LIVRABLE} | `{VERIFIED|PARTIAL|UNVERIFIED}` |
| {ACTION_4} | {RESP} | {DEPS} | {LIVRABLE} | `{VERIFIED|PARTIAL|UNVERIFIED}` |

#### Phase 3 — 90 jours (Consolidation)

| Action | Responsable | Dépendances | Livrable | Badge |
|--------|-------------|-------------|----------|-------|
| {ACTION_5} | {RESP} | {DEPS} | {LIVRABLE} | `{VERIFIED|PARTIAL|UNVERIFIED}` |
| {ACTION_6} | {RESP} | {DEPS} | {LIVRABLE} | `{VERIFIED|PARTIAL|UNVERIFIED}` |

### Diagramme de Gantt simplifié

```text
Semaine     1  2  3  4  5  6  7  8  9  10 11 12
Phase 1     ████████████
Phase 2                 ████████████
Phase 3                             ████████████
```

### Dépendances critiques

```json
{ACTION_1} ──► {ACTION_3} ──► {ACTION_5}
    │              │
    └──► {ACTION_2}├──► {ACTION_4} ──► {ACTION_6}
```

---

<!-- ═══════════════════════════════════════════════════════════════════════════ -->
<!-- BLOC I — PREUVES & VÉRIFICATION                                            -->
<!-- ═══════════════════════════════════════════════════════════════════════════ -->

## H. Preuves & Vérification

> **Show your work** — Commandes, tests, logs pour reproduire les vérifications.

### Commandes de vérification

| Test | Commande | Preuve attendue | Statut |
|------|----------|-----------------|--------|
| Consensus PRISM | `make audit-verify` | `[PASS] Audit verification` | `{VERIFIED|UNVERIFIED}` |
| Routeur déterministe | `python -m pytest tests/test_router_determinism.py -v` | Tests PASS | `{VERIFIED|UNVERIFIED}` |
| Pipeline légal | `python -m pytest tests/test_legal_orchestrator.py -v` | Tests PASS | `{VERIFIED|UNVERIFIED}` |
| Contrat médical | `python -m pytest tests/test_medical_agent_hardening.py -v` | Tests PASS | `{VERIFIED|UNVERIFIED}` |

### Preuves collectées

| ID | Claim | Source | Type preuve | Statut |
|----|-------|--------|-------------|--------|
| P-001 | {CLAIM_1} | {SOURCE} | `{TEST|LOG|DOC}` | `{VERIFIED|PARTIAL|UNVERIFIED}` |
| P-002 | {CLAIM_2} | {SOURCE} | `{TEST|LOG|DOC}` | `{VERIFIED|PARTIAL|UNVERIFIED}` |

### Points non vérifiés

> **Honnêteté intellectuelle** — Ce que nous n'avons pas pu prouver.

| Point | Raison non vérifiable | Impact | Action requise |
|-------|----------------------|--------|----------------|
| {POINT_1} | {RAISON} | `{HIGH|MEDIUM|LOW}` | {ACTION} |
| {POINT_2} | {RAISON} | `{HIGH|MEDIUM|LOW}` | {ACTION} |

---

<!-- ═══════════════════════════════════════════════════════════════════════════ -->
<!-- BLOC J — LIMITES & FAIL-CLOSED                                             -->
<!-- ═══════════════════════════════════════════════════════════════════════════ -->

## I. Limites & FAIL_CLOSED

> **Quand Evidence refuse de conclure** — Transparence sur les limites du système.

### Limites de l'analyse

| Limite | Impact sur conclusions | Mitigation |
|--------|----------------------|------------|
| {LIMITE_1} | {IMPACT} | {MITIGATION} |
| {LIMITE_2} | {IMPACT} | {MITIGATION} |

### Points FAIL_CLOSED

> **En criticité HIGH, les points suivants empêchent une recommandation ferme.**

| ID | Point | Raison FAIL_CLOSED | Information manquante |
|----|-------|-------------------|----------------------|
| FC-001 | {POINT} | {RAISON} | {INFO_REQUISE} |
| FC-002 | {POINT} | {RAISON} | {INFO_REQUISE} |

### Avertissements

⚠️ **Ce rapport ne constitue pas** :

- Un audit de conformité certifié
- Un conseil juridique
- Une garantie de sécurité

⚠️ **Conditions de validité** :

- Les hypothèses listées en section C doivent rester vraies
- Le contexte client doit correspondre au périmètre défini
- Les informations fournies doivent être exactes et à jour

---

<!-- ═══════════════════════════════════════════════════════════════════════════ -->
<!-- BLOC K — ANNEXES                                                           -->
<!-- ═══════════════════════════════════════════════════════════════════════════ -->

## J. Annexes

### Glossaire

| Terme | Définition |
|-------|------------|
| **Fail-closed** | Comportement où le système refuse en cas de doute plutôt que d'approuver |
| **Quorum** | Nombre minimum de votes requis pour une décision (2/3 des votes effectifs) |
| **PRISM** | Moteur de consensus multi-LLM de KOREV Evidence |
| **SPOF** | Single Point of Failure — composant dont la défaillance entraîne l'arrêt du système |
| **RTO** | Recovery Time Objective — temps maximal pour restaurer un service |
| **RPO** | Recovery Point Objective — perte de données maximale acceptable |

### Références

| ID | Titre | URL/Chemin | Type |
|----|-------|-----------|------|
| REF-001 | {TITRE} | {URL} | `{DOC|CODE|TEST}` |
| REF-002 | {TITRE} | {URL} | `{DOC|CODE|TEST}` |

### Métadonnées du rapport

| Attribut | Valeur |
|----------|--------|
| **Template version** | 1.0.0 |
| **Généré par** | KOREV Evidence |
| **Date génération** | {DATE_ISO} |
| **Hash du contenu** | `{SHA256}` |
| **Correlation ID** | `{UUID}` |

---

## Badges de confiance

| Badge | Signification |
|-------|---------------|
| `VERIFIED` | Preuves code/tests/logs reproductibles disponibles |
| `PARTIAL` | Preuves partielles ou wiring non prouvé |
| `UNVERIFIED` | Aucune preuve technique disponible |
| `FAIL_CLOSED` | Criticité HIGH + UNVERIFIED sur point structurant ⇒ pas de recommandation |

---

*Document généré par KOREV Evidence — Toutes les affirmations sont basées sur des preuves ou marquées UNVERIFIED.*
