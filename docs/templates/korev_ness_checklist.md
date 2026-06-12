# Checklist "Korev-ness" — 10 Critères de Différenciation

> **Version**: 1.0.0  
> **Usage**: Appliquer cette checklist à tout rapport pour évaluer son niveau "Evidence-native".  
> **Score cible**: 8/10 minimum pour un rapport vendable.

---

## Critères obligatoires (Core)

### 1. Decision Governance Block

**Question**: Le rapport contient-il un bloc de gouvernance en en-tête?  
**Vérification**:

- [ ] Criticité explicite (LOW/MEDIUM/HIGH)
- [ ] Mode de validation (SINGLE/DEBATE/CONSENSUS)
- [ ] Quorum spécifié (2/3 votes effectifs)
- [ ] Statut (APPROVED/NO_CONSENSUS/PENDING)
- [ ] Correlation ID traçable

**Score**: 0 si absent, 1 si complet

---

### 2. Registre des Risques (Threat Model)

**Question**: Chaque recommandation est-elle liée à un risque identifié?  
**Vérification**:

- [ ] Table des risques avec ID unique
- [ ] Impact et probabilité pour chaque risque
- [ ] Score de criticité calculé
- [ ] Lien risque → décision → contrôle

**Score**: 0 si absent, 1 si complet

---

### 3. Alternatives Écartées

**Question**: Les décisions structurantes montrent-elles les options rejetées?  
**Vérification**:

- [ ] Au moins 2 alternatives par décision structurante
- [ ] Avantages/inconvénients de chaque option
- [ ] Raison explicite du rejet

**Score**: 0 si absent, 1 si au moins 3 décisions avec alternatives

---

### 4. Hypothèses Explicites

**Question**: Les hypothèses sur lesquelles repose l'analyse sont-elles listées?  
**Vérification**:

- [ ] Table des hypothèses avec ID
- [ ] Impact si l'hypothèse est fausse
- [ ] Indication si vérifiable

**Score**: 0 si absent, 1 si au moins 3 hypothèses documentées

---

### 5. Badges de Confiance

**Question**: Chaque affirmation a-t-elle un badge de confiance?  
**Vérification**:

- [ ] Badges VERIFIED/PARTIAL/UNVERIFIED présents
- [ ] Aucune affirmation critique sans badge
- [ ] Définition des badges en annexe

**Score**: 0 si absent, 1 si systématique

---

## Critères différenciants (Evidence-native)

### 6. Preuves & Vérification

**Question**: Les commandes de vérification sont-elles fournies?  
**Vérification**:

- [ ] Section "Preuves & Vérification" présente
- [ ] Commandes reproductibles (make/pytest)
- [ ] Résultats attendus documentés
- [ ] Points non vérifiés explicitement marqués

**Score**: 0 si absent, 1 si complet

---

### 7. FAIL_CLOSED Appliqué

**Question**: Le rapport refuse-t-il de conclure sur les points incertains?  
**Vérification**:

- [ ] Section "Limites & FAIL_CLOSED" présente
- [ ] Points FAIL_CLOSED listés avec raisons
- [ ] Informations manquantes identifiées
- [ ] Règle: HIGH + UNVERIFIED = pas de recommandation ferme

**Score**: 0 si absent ou si affirmations non prouvées présentées comme vraies

---

### 8. Traçabilité Claims → Sources

**Question**: Chaque claim est-il relié à une source?  
**Vérification**:

- [ ] Table des sources avec fiabilité
- [ ] Lien claim → source ID
- [ ] Claims non sourcés marqués UNVERIFIED

**Score**: 0 si claims sans sources, 1 si traçabilité complète

---

### 9. Plan Actionnable (30/60/90)

**Question**: Le plan de mise en œuvre est-il structuré et priorisé?  
**Vérification**:

- [ ] Phases 30/60/90 jours définies
- [ ] Actions avec responsables
- [ ] Dépendances identifiées
- [ ] Livrables pour chaque action

**Score**: 0 si absent ou vague, 1 si actionnable

---

### 10. Périmètre IN/OUT Explicite

**Question**: Le périmètre est-il clairement délimité?  
**Vérification**:

- [ ] Section "Contexte & Périmètre" présente
- [ ] Liste IN (ce qui est inclus)
- [ ] Liste OUT (ce qui est exclu)
- [ ] Contraintes réglementaires identifiées

**Score**: 0 si absent, 1 si complet

---

## Grille d'évaluation

| Score | Niveau | Signification |
|-------|--------|---------------|
| 10/10 | **Evidence-native** | Rapport vendable, auditabilité maximale |
| 8-9/10 | **Acceptable** | Rapport différenciant avec points mineurs à améliorer |
| 6-7/10 | **Partiel** | Rapport utilisable mais manque de traçabilité |
| <6/10 | **Générique** | Rapport "cabinet-like", pas de différenciation Korev |

---

## Commande de validation automatique

```bash
# Valider un rapport contre la checklist Korev-ness
python -m python.helpers.reporting.evidence_native validate path/to/report.md
```

---

## Anti-patterns à éviter

| Anti-pattern | Pourquoi c'est problématique | Comment corriger |
|--------------|------------------------------|------------------|
| Recommandations sans risques | Impossible de justifier la priorité | Lier chaque reco à un risque |
| "Best practices" sans contexte | Générique, non actionnable | Adapter au contexte client |
| Affirmations non sourcées | Crédibilité nulle | Marquer UNVERIFIED ou sourcer |
| Alternatives absentes | On ne voit pas le raisonnement | Documenter au moins 2 options |
| Périmètre flou | Engagements non maîtrisés | Définir IN/OUT explicitement |
| Plan sans dépendances | Irréaliste | Identifier les dépendances |

---

## Exemple de scoring

```text
Rapport "Architecture SI Plialpes"
────────────────────────────────────
□ Decision Governance Block     [0] - ABSENT
□ Registre des Risques          [0] - ABSENT  
□ Alternatives Écartées         [0] - ABSENT
□ Hypothèses Explicites         [0] - ABSENT
□ Badges de Confiance           [0] - ABSENT
□ Preuves & Vérification        [0] - ABSENT
□ FAIL_CLOSED Appliqué          [0] - ABSENT
□ Traçabilité Claims → Sources  [0] - ABSENT
□ Plan Actionnable (30/60/90)   [1] - PRESENT (partiel)
□ Périmètre IN/OUT Explicite    [1] - PRESENT
────────────────────────────────────
SCORE TOTAL: 2/10 → GÉNÉRIQUE
```

---

*Checklist v1.0.0 — KOREV Evidence*
