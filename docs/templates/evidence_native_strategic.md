# Template Evidence-Native — Document Stratégique

> **Version**: 1.0.0  
> **Types couverts**: Étude de marché, Prévisionnel, Pricing, GTM, Business Plan  
> **Règle**: Tout document stratégique sans sourcing = FAIL_CLOSED

---

## 📋 En-tête Decision Governance (OBLIGATOIRE)

```markdown
| Paramètre | Valeur |
|-----------|--------|
| **Type document** | `MARKET_STUDY` / `FINANCIAL_FORECAST` / `PRICING` / `GTM` |
| **Criticité** | `HIGH` (défaut pour stratégique) |
| **Mode** | `CONSENSUS` |
| **Quorum** | 2/3 sur votes effectifs |
| **Agents requis** | `[finance, researcher, marketing, ...]` |
| **Statut** | `APPROVED` / `FAIL_CLOSED` / `NEEDS_MORE_DATA` |
| **Corrélation ID** | `{uuid}` |
| **FAIL_CLOSED si** | Sources < minimum OU TAM/SAM/SOM absent OU pas d'alternatives |
```

---

## 1. Executive Summary

> **Règle**: Conclusion first. Pas de pitch — des faits.

### Format obligatoire

- **Opportunité marché**: [Chiffre sourcé] — Source: [REF-ID]
- **Position concurrentielle**: [Analyse factuelle]
- **Décision recommandée**: [GO / NO-GO / NEED_MORE_DATA]
- **Confiance**: [VERIFIED / PARTIAL / UNVERIFIED]

---

## 2. Analyse TAM/SAM/SOM (OBLIGATOIRE pour Market Study)

> **Règle**: Chaque chiffre doit avoir une source et une méthodologie.

| Niveau | Valeur | Méthodologie | Source |
|--------|--------|--------------|--------|
| **TAM** | X €/$ | [Top-down / Bottom-up] | [REF-ID] |
| **SAM** | Y €/$ (Z% du TAM) | [Critères de segmentation] | [REF-ID] |
| **SOM** | W €/$ (V% du SAM) | [Hypothèses de pénétration] | [REF-ID] |

### Hypothèses TAM/SAM/SOM

| ID | Hypothèse | Impact | Vérifiable |
|----|-----------|--------|------------|
| H1 | [Texte] | HIGH/MED/LOW | Oui/Non |

---

## 3. Analyse Concurrentielle (OBLIGATOIRE si require_competitor_data)

> **Règle**: Sources publiques obligatoires (sites, pricing, rapports)

### Matrice Concurrentielle

| Concurrent | Positionnement | Pricing public | Forces | Faiblesses | Source |
|------------|---------------|----------------|--------|------------|--------|
| [Nom] | [Description] | [€/$/Free] | [...] | [...] | [REF-ID] |

### Différenciation KOREV

| Critère | KOREV | Concurrent A | Concurrent B |
|---------|-------|--------------|--------------|
| [Feature] | [✓/✗] | [✓/✗] | [✓/✗] |

---

## 4. Prévisionnel Financier

> **Règle**: Chaque ligne doit avoir une base de calcul traçable.

### P&L Prévisionnel

| Métrique | Base de calcul | Y1 | Y2 | Y3 | Source |
|----------|----------------|-----|-----|-----|--------|
| Revenus | [ARPA × Clients] | | | | [REF-ID] |
| Clients | [Funnel × Conv%] | | | | [REF-ID] |
| ARPA | [Benchmark] | | | | [REF-ID] |
| CAC | [Source] | | | | [REF-ID] |
| Coûts | [Détail] | | | | |

### Hypothèses Financières

| ID | Hypothèse | Valeur | Source | Sensibilité |
|----|-----------|--------|--------|-------------|
| HF1 | Taux de conversion | X% | [REF-ID] | HIGH |
| HF2 | ARPA | Y€ | [REF-ID] | HIGH |
| HF3 | Churn | Z% | [Benchmark] | MEDIUM |

---

## 5. Alternatives Analysées (OBLIGATOIRE)

> **Règle**: Montrer le raisonnement, pas juste la conclusion.

### Alternative 1: [Nom]

| Aspect | Détail |
|--------|--------|
| **Description** | [Texte] |
| **Pour** | [Liste] |
| **Contre** | [Liste] |
| **Raison du rejet** | [Texte explicite] |
| **Sources** | [REF-IDs] |

### Alternative 2: [Nom]

[Même structure]

---

## 6. Registre des Risques

| ID | Risque | Probabilité | Impact | Contrôle | Décision liée |
|----|--------|-------------|--------|----------|---------------|
| R1 | [Texte] | H/M/L | H/M/L | [Texte] | [D1] |

---

## 7. Décisions Structurantes

| ID | Décision | Justification | Risques couverts | Alternatives écartées |
|----|----------|---------------|------------------|----------------------|
| D1 | [Texte] | [Texte] | [R1, R2] | [A1, A2] |

---

## 8. Preuves & Vérification

### Sources Citées

| ID | Type | Référence | URL | Accès |
|----|------|-----------|-----|-------|
| REF-01 | `public_stats` | [Texte] | [URL] | [Date] |
| REF-02 | `industry_report` | [Texte] | [URL] | [Date] |

### Points Non Vérifiés (UNVERIFIED)

> **Règle**: Tout point sans source doit être listé ici.

| Claim | Raison UNVERIFIED | Données nécessaires |
|-------|-------------------|---------------------|
| [Texte] | [Pas de source publique] | [Ce qu'il faudrait] |

---

## 9. Limites & FAIL_CLOSED

### Conditions de FAIL_CLOSED

Ce document passe en FAIL_CLOSED si :

- [ ] Sources totales < [minimum requis]
- [ ] Sources publiques < [minimum requis]
- [ ] TAM/SAM/SOM absent (pour market study)
- [ ] Aucune alternative analysée
- [ ] Affirmation quantitative non sourcée

### Limites du document

| Limite | Impact |
|--------|--------|
| [Texte] | [HIGH/MED/LOW] |

---

## 10. Annexe

### Glossaire

| Terme | Définition |
|-------|------------|
| TAM | Total Addressable Market |
| SAM | Serviceable Available Market |
| SOM | Serviceable Obtainable Market |
| ARPA | Average Revenue Per Account |
| CAC | Customer Acquisition Cost |

### Métadonnées

| Champ | Valeur |
|-------|--------|
| Généré par | KOREV Evidence |
| Template | `evidence_native_strategic.md` v1.0.0 |
| Date | [ISO-8601] |
| Correlation ID | [UUID] |

### Badges de Confiance

| Badge | Signification | Couleur |
|-------|---------------|---------|
| `VERIFIED` | Preuves publiques vérifiables | 🟢 |
| `PARTIAL` | Sources partielles ou extrapolation | 🟡 |
| `ESTIMATED` | Estimation basée sur proxies | 🟠 |
| `UNVERIFIED` | Aucune source — listé dans section 8 | 🔴 |
| `FAIL_CLOSED` | Refus de conclure — sourcing insuffisant | ⛔ |

---

## Exigences de Sourcing par Type

| Type Document | Sources min | Sources publiques min | TAM/SAM/SOM | Concurrence | Alternatives |
|---------------|-------------|----------------------|-------------|-------------|--------------|
| Market Study | 5 | 3 | ✓ | ✓ | ✓ |
| Financial Forecast | 4 | 2 | - | - | ✓ |
| Pricing | 3 | 2 | - | ✓ | ✓ |
| GTM | 4 | 2 | - | - | ✓ |
| Business Plan | 6 | 4 | ✓ | - | ✓ |
| Due Diligence | 8 | 5 | - | - | ✓ |

---

*KOREV Evidence — Documents stratégiques Evidence-grade ou FAIL_CLOSED.*
