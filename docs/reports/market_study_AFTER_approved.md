# Étude de Marché KOREV Evidence — APPROVED (Evidence-Grade)

> ✅ **Ce document illustre une étude de marché conforme aux standards Evidence**
>
> Chaque affirmation est sourcée, chaque projection est basée sur des données vérifiables.

---

## Decision Governance

| Paramètre | Valeur |
|-----------|--------|
| **Type document** | `MARKET_STUDY` |
| **Criticité** | `HIGH` |
| **Mode** | `CONSENSUS` |
| **Quorum** | 2/3 sur votes effectifs |
| **Agents invoqués** | `[finance, researcher, marketing]` |
| **Statut** | ✅ `APPROVED` |
| **Score Korev-ness** | 9/10 |
| **Corrélation ID** | `660e8400-e29b-41d4-a716-446655440001` |

---

## Executive Summary

| Métrique | Valeur | Confiance | Source |
|----------|--------|-----------|--------|
| **TAM Global AI** | 407 Md$ (2027) | `VERIFIED` | [REF-01] |
| **SAM B2B Professional** | 45 Md$ | `VERIFIED` | [REF-02] |
| **SOM Europe Y3** | 15 M€ | `PARTIAL` | Calcul interne |
| **Décision** | GO Beta | `APPROVED` | Consensus 3/3 |

### Conclusion (Consensus 3/3)

L'opportunité de marché est validée par les données. Le segment B2B professionnel (pharma, juridique, recherche) présente une willingness-to-pay élevée pour des solutions IA avec garanties de fiabilité.

**Recommandation** : Lancer la bêta avec 15-20 testeurs dans les segments pharma et juridique.

---

## 1. Analyse TAM/SAM/SOM

### TAM — Total Addressable Market

| Paramètre | Valeur | Source |
|-----------|--------|--------|
| Marché global IA | 407 Md$ en 2027 | Gartner [REF-01] |
| CAGR 2023-2027 | 35.6% | Gartner [REF-01] |
| Méthodologie | Top-down (rapports sectoriels) | — |

### SAM — Serviceable Available Market

| Paramètre | Valeur | Source |
|-----------|--------|--------|
| Segment B2B Professional AI | ~45 Md$ | IDC [REF-02] |
| Critères de segmentation | B2B, domaines régulés, besoin fiabilité | — |
| % du TAM | ~11% | Calcul |

### SOM — Serviceable Obtainable Market

| Paramètre | Valeur | Calcul |
|-----------|--------|--------|
| Marché Europe B2B AI | ~12 Md$ | 27% du SAM [REF-03] |
| Pénétration Y3 estimée | 0.125% | Benchmark SaaS early-stage |
| **SOM Y3** | **15 M€** | 12 Md$ × 0.125% |

**Hypothèse** : Pénétration conservative basée sur benchmarks SaaS B2B early-stage (0.1-0.2% du SAM addressable en Y3).

---

## 2. Analyse Concurrentielle

### Matrice Concurrentielle

| Concurrent | Positionnement | Pricing public | Sourcing | Consensus | Source |
|------------|---------------|----------------|----------|-----------|--------|
| ChatGPT Enterprise | Généraliste | $60/user/mois | ❌ | ❌ | [REF-04] |
| Claude Pro | Généraliste | $20/mois | ❌ | ❌ | [REF-05] |
| Perplexity Pro | Search-first | $20/mois | ✅ Partiel | ❌ | [REF-06] |
| **KOREV Evidence** | Domain-specific | ~50-100€/mois | ✅ Obligatoire | ✅ 2/3 | — |

### Différenciation KOREV

| Critère | KOREV | ChatGPT | Claude | Perplexity |
|---------|-------|---------|--------|------------|
| Sources obligatoires | ✅ | ❌ | ❌ | ✅ (partiel) |
| Consensus multi-LLM | ✅ | ❌ | ❌ | ❌ |
| Fail-closed | ✅ | ❌ | ❌ | ❌ |
| Agents spécialisés | ✅ | ❌ | ❌ | ❌ |
| Contrats domaines | ✅ | ❌ | ❌ | ❌ |

**Source** : Sites publics des concurrents consultés le 2026-01-30.

---

## 3. Prévisionnel Financier

### Hypothèses (explicites et sourcées)

| ID | Hypothèse | Valeur | Source | Sensibilité |
|----|-----------|--------|--------|-------------|
| H1 | ARPA | 1 200€/mois | Benchmark SaaS B2B [REF-07] | HIGH |
| H2 | Conversion trial→paid | 15% | OpenView 2024 [REF-08] | HIGH |
| H3 | Churn mensuel | 3% | SaaS benchmarks [REF-08] | MEDIUM |
| H4 | CAC | 2 500€ | Estimation (pas de source) | `UNVERIFIED` |

### P&L Prévisionnel

| Métrique | Base de calcul | Y1 | Y2 | Y3 |
|----------|----------------|-----|-----|-----|
| Leads | Marketing + inbound | 500 | 2 000 | 8 000 |
| Conversion | H2 (15%) | 75 | 300 | 1 200 |
| Clients actifs | -Churn | 10 | 45 | 150 |
| ARPA | H1 | 1 200€ | 1 200€ | 1 250€ |
| **ARR** | Clients × ARPA × 12 | 144k€ | 648k€ | 2.25M€ |

### Hypothèses `UNVERIFIED`

| Hypothèse | Statut | Données nécessaires |
|-----------|--------|---------------------|
| CAC = 2 500€ | `UNVERIFIED` | Données acquisition réelles post-beta |
| Churn 3% | `PARTIAL` | Benchmark sectoriel, pas de data KOREV |

---

## 4. Alternatives Analysées

### Alternative 1 : Focus B2C

| Aspect | Détail |
|--------|--------|
| **Description** | Cibler le marché grand public (étudiants, freelances) |
| **Pour** | Volume élevé, viralité potentielle |
| **Contre** | ARPA faible (~10€), CAC élevé, support intensif |
| **Raison du rejet** | Unit economics défavorables — LTV/CAC < 1 |
| **Sources** | Benchmarks B2C SaaS [REF-07] |

### Alternative 2 : Généraliste multi-secteurs

| Aspect | Détail |
|--------|--------|
| **Description** | Positionner KOREV comme IA généraliste |
| **Pour** | TAM plus large |
| **Contre** | Concurrence directe OpenAI/Anthropic, pas de différenciation |
| **Raison du rejet** | Impossible de rivaliser sans différenciation nette |
| **Sources** | Analyse concurrentielle [REF-04, REF-05] |

### Alternative 3 : API-only (pas d'interface)

| Aspect | Détail |
|--------|--------|
| **Description** | Fournir uniquement une API pour développeurs |
| **Pour** | Coûts réduits, scalabilité |
| **Contre** | Marché restreint, dépendance intégrateurs |
| **Raison du rejet** | Segments cibles (pharma, juridique) préfèrent interfaces clés-en-main |
| **Sources** | Retours prospects (N=12) |

---

## 5. Registre des Risques

| ID | Risque | Probabilité | Impact | Contrôle | Décision liée |
|----|--------|-------------|--------|----------|---------------|
| R1 | Adoption plus lente que prévu | MEDIUM | HIGH | Ajuster funnel, CAC | D1, D2 |
| R2 | Concurrents ajoutent sourcing | MEDIUM | MEDIUM | Renforcer fail-closed | D3 |
| R3 | Coûts LLM augmentent | LOW | HIGH | Multi-provider, négociation | D4 |
| R4 | AI Act impose contraintes | HIGH | MEDIUM | Conformité native | D5 |

---

## 6. Décisions Structurantes

| ID | Décision | Justification | Risques couverts | Alternatives écartées |
|----|----------|---------------|------------------|----------------------|
| D1 | Focus B2B domaines régulés | Unit economics, différenciation | R1 | A1 (B2C) |
| D2 | Beta 15-20 testeurs pharma/juridique | Validation product-market fit | R1 | — |
| D3 | Consensus obligatoire pour CRITIQUE | Différenciation durable | R2 | A2 (généraliste) |
| D4 | Multi-provider LLM | Résilience, négociation | R3 | Single provider |
| D5 | AI Act compliance by design | Anticipation réglementaire | R4 | Compliance réactive |

---

## 7. Preuves & Vérification

### Sources Citées

| ID | Type | Référence | URL | Accès |
|----|------|-----------|-----|-------|
| REF-01 | `industry_report` | Gartner, "AI Software Market Forecast 2027" | gartner.com/reports/ai-2027 | 2026-01-15 |
| REF-02 | `industry_report` | IDC, "Worldwide AI Software Forecast" | idc.com/ai-forecast | 2026-01-20 |
| REF-03 | `public_stats` | Eurostat, "Digital Economy Report 2025" | ec.europa.eu/eurostat | 2026-01-25 |
| REF-04 | `competitor_public` | OpenAI Enterprise Pricing | openai.com/enterprise | 2026-01-30 |
| REF-05 | `competitor_public` | Anthropic Claude Pricing | anthropic.com/pricing | 2026-01-30 |
| REF-06 | `competitor_public` | Perplexity Pro | perplexity.ai/pro | 2026-01-30 |
| REF-07 | `industry_report` | OpenView, "SaaS Benchmarks 2025" | openviewpartners.com | 2026-01-10 |
| REF-08 | `market_data` | SaaS Capital, "Churn Benchmarks" | saas-capital.com | 2026-01-12 |

### Points Non Vérifiés (`UNVERIFIED`)

| Claim | Raison | Données nécessaires |
|-------|--------|---------------------|
| CAC = 2 500€ | Estimation sans données réelles | Tracking acquisition post-beta |
| Conversion 15% | Benchmark sectoriel, pas de data KOREV | A/B testing beta |

---

## 8. Limites & FAIL_CLOSED

### Limites du document

| Limite | Impact | Mitigation |
|--------|--------|------------|
| CAC non validé | Projection Y1-Y3 incertaine | Réviser post-beta |
| Churn estimé | Impact sur LTV | Mesurer dès M3 |
| Pas de primary research N>50 | Représentativité | Étude quali Q2 |

### Ce document aurait été FAIL_CLOSED si

- [ ] ~~Sources totales < 5~~ → 8 sources ✅
- [ ] ~~Sources publiques < 3~~ → 6 sources publiques ✅
- [ ] ~~TAM/SAM/SOM absent~~ → Présent et sourcé ✅
- [ ] ~~Aucune alternative analysée~~ → 3 alternatives ✅

---

## 9. Meta

| Champ | Valeur |
|-------|--------|
| **Template** | `evidence_native_strategic.md` v1.0.0 |
| **Generated at** | 2026-01-30T20:35:00Z |
| **Correlation ID** | `660e8400-e29b-41d4-a716-446655440001` |
| **Evidence grade** | `PARTIAL` (2 claims UNVERIFIED) |
| **Consensus** | `APPROVED` (3/3 agents) |

### Agents invoqués

| Agent | Contribution | Verdict |
|-------|--------------|---------|
| `finance` | Validation P&L, unit economics | APPROVE |
| `researcher` | Sourcing TAM/SAM/SOM, concurrence | APPROVE |
| `marketing` | Positionnement, segments | APPROVE |

---

## Badges de Confiance

| Section | Badge |
|---------|-------|
| TAM/SAM | 🟢 `VERIFIED` |
| SOM | 🟡 `PARTIAL` |
| Concurrence | 🟢 `VERIFIED` |
| P&L Y1 | 🟡 `PARTIAL` |
| CAC | 🔴 `UNVERIFIED` |

---

*KOREV Evidence — Document stratégique Evidence-grade.*

---

## 💡 Ce que ce document APPROVED démontre

1. **Traçabilité** — Chaque chiffre est lié à une source [REF-XX]
2. **Honnêteté** — Les points UNVERIFIED sont explicites
3. **Rigueur** — Alternatives analysées, risques identifiés
4. **Auditabilité** — Un investisseur peut vérifier chaque claim
5. **Discipline** — Le système a exigé les données avant de conclure

> **La différence avec le "BEFORE" :**
> Même conclusion (GO Beta), mais défendable et auditable.
