# KOREV Evidence — Protocole de Validation des Preuves Médicales

## Vue d'Ensemble

```
┌─────────────────────────────────────────────────────────────────────┐
│                         QUERY MÉDICALE                               │
└─────────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────┐
│  ÉTAPE 1: COLLECTE MULTI-SOURCE                                      │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐                    │
│  │ PubMed  │ │ Trials  │ │  FAERS  │ │  FDA    │                    │
│  │ (BioMCP)│ │(CT.gov) │ │(OpenFDA)│ │ Labels  │                    │
│  └────┬────┘ └────┬────┘ └────┬────┘ └────┬────┘                    │
└───────┼──────────┼──────────┼──────────┼────────────────────────────┘
        │          │          │          │
        └──────────┴──────────┴──────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────────────┐
│  ÉTAPE 2: TRIANGULATION DES SOURCES                                  │
│  - Concordance : Sources convergent-elles ?                          │
│  - Divergence : Y a-t-il des contradictions ?                        │
│  - Niveau : Quel niveau de preuve par source ?                       │
└─────────────────────────────────────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────────────┐
│  ÉTAPE 3: SCORING GRADE                                              │
│  - HIGH : Multiple RCTs concordants ou meta-analyses                 │
│  - MODERATE : RCT unique ou cohort studies concordantes              │
│  - LOW : Observational data ou sources divergentes                   │
│  - VERY LOW : Case reports ou expert opinion seul                    │
└─────────────────────────────────────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────────────┐
│  ÉTAPE 4: CONSENSUS PRISM (Multi-LLM)                                │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐                                │
│  │  LLM 1  │ │  LLM 2  │ │  LLM 3  │                                │
│  │ (Vote)  │ │ (Vote)  │ │ (Vote)  │                                │
│  └────┬────┘ └────┬────┘ └────┬────┘                                │
│       │          │          │                                        │
│       └──────────┴──────────┘                                        │
│                  │                                                   │
│       Quorum 2/3 requis pour validation                              │
└─────────────────────────────────────────────────────────────────────┘
                        │
            ┌───────────┴───────────┐
            │                       │
            ▼                       ▼
    ┌──────────────┐        ┌──────────────┐
    │  VALIDATED   │        │ FAIL-CLOSED  │
    │ (+ stamp)    │        │ (pas output) │
    └──────────────┘        └──────────────┘
```

---

## Étape 1 : Collecte Multi-Source

### Sources Obligatoires (minimum 2 sur 4)

| Source | Type | Fiabilité | Utilisation |
|--------|------|-----------|-------------|
| **PubMed/BioMCP** | Littérature peer-reviewed | HIGH | Efficacité, mécanismes |
| **ClinicalTrials.gov** | Registre essais | HIGH | Pipeline, endpoints |
| **FAERS/OpenFDA** | Pharmacovigilance | MEDIUM | Sécurité post-market |
| **FDA Labels/EMA SmPC** | Réglementaire | HIGH | Posologie, CI, warnings |

### Règle de Collecte
```python
# Pseudo-code
sources = []
sources += search_pubmed(query, limit=20)
sources += search_clinicaltrials(query, limit=10)
sources += search_faers(drug_name) if drug_query else []
sources += get_fda_label(drug_name) if drug_query else []

# Minimum requis
if len(sources) < 2:
    return FAIL_CLOSED("Insufficient sources")
```

---

## Étape 2 : Triangulation des Sources

### Matrice de Concordance

Pour chaque claim, vérifier la concordance entre sources :

| Claim | PubMed | Trials | FAERS | Label | Concordance |
|-------|--------|--------|-------|-------|-------------|
| "Drug X efficace" | ✅ RCT+ | ✅ Ph3+ | N/A | ✅ | **STRONG** |
| "Drug X cause Y" | ⚠️ 1 study | ❌ Non trouvé | ✅ Signal | ❌ Non listé | **WEAK** |
| "Drug X > Drug Y" | ✅ H2H | ✅ NMA | N/A | N/A | **MODERATE** |

### Scoring Concordance

```
STRONG   : 3+ sources concordantes, dont ≥1 RCT
MODERATE : 2 sources concordantes, ou meta-analyse seule
WEAK     : 1 source ou sources divergentes
CONFLICT : Sources contradictoires (requiert explanation)
```

### Gestion des Conflits

Si sources divergentes :
1. Identifier la divergence explicitement
2. Évaluer la qualité méthodologique de chaque source
3. Privilégier : RCT > Cohort > Case-control > Case report
4. Mentionner la controverse dans l'output

```markdown
**Note : Données divergentes**
- Source A (RCT, n=500) : effet positif
- Source B (Cohort, n=10000) : pas d'effet
- Explication possible : différence de population, endpoints
```

---

## Étape 3 : Scoring GRADE

### Critères GRADE

| Niveau | Définition | Implication |
|--------|------------|-------------|
| **HIGH** | Très confiant que l'effet réel est proche de l'estimation | "Les données montrent que..." |
| **MODERATE** | Modérément confiant ; effet réel probablement proche | "Les données suggèrent que..." |
| **LOW** | Confiance limitée ; effet réel peut être différent | "Les données indiquent possiblement..." |
| **VERY LOW** | Très peu confiant | "Les données disponibles sont insuffisantes pour..." |

### Facteurs de Downgrade

- Risque de biais élevé (-1)
- Inconsistance entre études (-1)
- Imprécision (larges CI) (-1)
- Indirectness (population différente) (-1)
- Publication bias suspectée (-1)

### Facteurs d'Upgrade

- Large effect size (+1)
- Dose-response (+1)
- Confounders auraient réduit l'effet (+1)

---

## Étape 4 : Consensus PRISM

### Architecture Multi-LLM

```
                    ┌─────────────────┐
                    │ Evidence Pack   │
                    │ - Sources       │
                    │ - Claims        │
                    │ - Concordance   │
                    └────────┬────────┘
                             │
         ┌───────────────────┼───────────────────┐
         ▼                   ▼                   ▼
    ┌─────────┐        ┌─────────┐        ┌─────────┐
    │Arbitre 1│        │Arbitre 2│        │Arbitre 3│
    │(Claude) │        │  (GPT)  │        │(Gemini) │
    └────┬────┘        └────┬────┘        └────┬────┘
         │                  │                  │
         ▼                  ▼                  ▼
    ┌─────────┐        ┌─────────┐        ┌─────────┐
    │APPROVE/ │        │APPROVE/ │        │APPROVE/ │
    │REJECT/  │        │REJECT/  │        │REJECT/  │
    │ABSTAIN  │        │ABSTAIN  │        │ABSTAIN  │
    └────┬────┘        └────┬────┘        └────┬────┘
         │                  │                  │
         └──────────────────┴──────────────────┘
                            │
                            ▼
                    ┌─────────────────┐
                    │ Quorum Check    │
                    │ 2/3 APPROVE ?   │
                    └────────┬────────┘
                             │
              ┌──────────────┴──────────────┐
              │                             │
              ▼                             ▼
       ┌──────────┐                  ┌──────────┐
       │VALIDATED │                  │ REJECTED │
       └──────────┘                  └──────────┘
```

### Critères de Vote des Arbitres

Chaque arbitre évalue :

1. **Evidence suffisante ?**
   - ≥2 sources identifiées
   - Sources de qualité acceptable

2. **Claims supportés ?**
   - Chaque affirmation a une source
   - Pas d'extrapolation non justifiée

3. **Cohérence logique ?**
   - Conclusions découlent des données
   - Pas de contradiction interne

4. **Limitations mentionnées ?**
   - Biais identifiés
   - Gaps reconnus

### Décision Finale

```python
votes = [arbiter1.vote, arbiter2.vote, arbiter3.vote]
approvals = sum(1 for v in votes if v == "APPROVE")

if approvals >= 2:  # Quorum 2/3
    return VALIDATED(output + prism_stamp)
else:
    return FAIL_CLOSED("Consensus not reached")
```

---

## Implémentation dans les Outils

### evidence_synthesis.py

```python
def synthesize(query, keywords, disease, drug):
    # 1. Collecte multi-source
    pubmed_data = search_pubmed(keywords, disease)
    trials_data = search_clinicaltrials(disease, drug)
    faers_data = search_faers(drug) if drug else []
    
    # 2. Triangulation
    concordance = check_concordance(pubmed_data, trials_data, faers_data)
    
    # 3. GRADE scoring
    grade = calculate_grade(all_evidence, concordance)
    
    # 4. Build evidence pack
    evidence_pack = build_pack(all_evidence, concordance, grade)
    
    # 5. PRISM consensus
    result = await validate_with_prism(query, output, evidence_pack)
    
    return result
```

### faers_signal_detection.py

```python
def detect_signal(drug, event):
    # 1. FAERS data
    faers_signal = query_faers(drug, event)
    
    # 2. Cross-validate with trials
    trial_safety = search_trials_safety(drug, event)
    
    # 3. Check label
    label_status = check_fda_label(drug, event)
    
    # 4. Concordance
    # FAERS signal + trial signal + not in label = STRONG signal
    # FAERS signal + no trial signal + not in label = INVESTIGATE
    # FAERS signal + no trial signal + in label = KNOWN
    
    # 5. PRISM validation
    result = await validate_with_prism(...)
```

---

## Output Format avec Validation

```markdown
## Analyse : [Query]

### Sources Consultées
- PubMed : 15 articles (3 RCT, 2 meta-analyses, 10 observational)
- ClinicalTrials.gov : 8 trials (2 Phase 3, 4 Phase 2)
- FAERS : 234 reports (Q1 2023 - Q4 2024)
- FDA Label : Version 2024-03

### Concordance des Sources
| Finding | PubMed | Trials | FAERS | Label | Score |
|---------|--------|--------|-------|-------|-------|
| Efficacy | ✅ | ✅ | N/A | ✅ | STRONG |
| Safety X | ⚠️ | ✅ | ✅ | ✅ | MODERATE |

### GRADE Assessment : MODERATE
- Downgrade : Some inconsistency between trials (-1)
- No upgrade factors

### Résultats
[Analysis with inline citations]

### Limitations
- [Listed explicitly]

---
✅ **PRISM Validated** | ID: `abc123` | Sources: 4 | Concordance: STRONG
```

---

## Cas Particuliers

### Aucune Source Trouvée
```
→ FAIL_CLOSED
→ Message : "Aucune donnée publiée identifiée sur ce sujet. 
   Recommandation : élargir la recherche ou consulter un expert."
```

### Sources Contradictoires
```
→ WARN + Continue
→ Mentionner explicitement la controverse
→ Donner plus de poids aux sources de meilleure qualité méthodologique
```

### Signal FAERS sans Confirmation Trial
```
→ Qualifier comme "signal à investiguer"
→ Mentionner les limites de FAERS (reporting bias, no causality)
→ Recommander surveillance
```
