# Étude de Marché KOREV Evidence — FAIL_CLOSED (APRÈS)

> ✅ **Ce document illustre le comportement correct de KOREV Evidence**
> 
> Face à une demande d'étude de marché sans données sourcées, le système refuse de conclure.

---

## Decision Governance

| Paramètre | Valeur |
|-----------|--------|
| **Type document** | `MARKET_STUDY` |
| **Criticité** | `HIGH` |
| **Mode** | `CONSENSUS` |
| **Quorum** | 2/3 sur votes effectifs |
| **Agents requis** | `[finance, researcher, marketing]` |
| **Statut** | ⛔ `FAIL_CLOSED` |
| **Corrélation ID** | `550e8400-e29b-41d4-a716-446655440000` |
| **Raison** | Sourcing requirements not met |

---

## ⚠️ DOCUMENT NON GÉNÉRABLE — FAIL_CLOSED

### Raison

**Les exigences de sourcing pour un document Evidence-grade ne sont pas remplies.**

Ce document stratégique ne peut pas être généré en mode Evidence car les données nécessaires ne sont pas disponibles ou vérifiables.

---

### Exigences non remplies

| Critère | Requis | Fourni | Statut |
|---------|--------|--------|--------|
| Sources totales | 5+ | 0 | ❌ |
| Sources publiques | 3+ | 0 | ❌ |
| TAM/SAM/SOM | Oui | Non | ❌ |
| Analyse concurrentielle sourcée | Oui | Non | ❌ |
| Alternatives écartées | Oui | Non | ❌ |
| Hypothèses explicites | Oui | Non | ❌ |

---

### Données manquantes pour générer ce document

1. **Sources publiques sur la taille du marché IA**
   - Eurostat, Gartner, Forrester, Statista
   - Rapports sectoriels avec TAM chiffré

2. **Données de benchmarking pricing**
   - Pricing public des concurrents (OpenAI, Anthropic, etc.)
   - Grilles tarifaires vérifiables

3. **Base de calcul pour le prévisionnel**
   - Benchmarks de conversion SaaS B2B
   - CAC par canal (source obligatoire)
   - Churn rates sectoriels

4. **Analyse concurrentielle sourcée**
   - Fonctionnalités comparées (sources publiques)
   - Parts de marché estimées (rapports)

5. **Réglementation**
   - Texte AI Act avec articles précis
   - Dates d'application

---

### Pourquoi ce refus ?

KOREV Evidence refuse de générer un document stratégique non sourcé car :

1. **Traçabilité** — Chaque affirmation doit être liée à une source vérifiable
2. **Auditabilité** — Un investisseur/board doit pouvoir vérifier les chiffres
3. **Intégrité** — Mieux vaut refuser que produire du "pitch non fondé"
4. **Responsabilité** — Un prévisionnel non sourcé peut mener à des décisions erronées

---

### Prochaines étapes pour obtenir un document APPROVED

Pour générer cette étude de marché en mode Evidence :

#### Sources à fournir

| Type | Exemples | Minimum |
|------|----------|---------|
| `public_stats` | Eurostat, INSEE, BLS | 2 |
| `industry_report` | Gartner, McKinsey, Forrester | 1 |
| `market_data` | Statista, CB Insights | 1 |
| `competitor_public` | Sites pricing, rapports annuels | 1 |

#### Données à collecter

```
□ TAM marché IA conversationnelle (source: rapport récent)
□ SAM segment B2B professionnel (méthodologie de segmentation)
□ Pricing concurrents (URLs publiques)
□ Benchmarks SaaS : CAC, LTV, Churn (source sectorielle)
□ Texte AI Act articles pertinents
```

#### Commande pour relancer avec données

```bash
# Fournir les sources dans le contexte de la requête
# Exemple de structure attendue :

{
  "request": "Étude de marché KOREV Evidence",
  "sources": [
    {"type": "industry_report", "ref": "Gartner AI Market 2024", "url": "..."},
    {"type": "public_stats", "ref": "Eurostat ICT 2024", "dataset": "..."},
    ...
  ],
  "tam_data": {
    "value": 500000000000,
    "source": "Gartner",
    "methodology": "..."
  }
}
```

---

### Agents consultés

| Agent | Statut | Avis |
|-------|--------|------|
| `finance` | ⚠️ | Impossible de valider sans base de calcul |
| `researcher` | ⚠️ | Aucune source fournie |
| `marketing` | ⚠️ | Positionnement non étayé |

**Consensus** : `NO_DATA` → `FAIL_CLOSED`

---

## Comparaison avec un chatbot classique

| Aspect | Chatbot classique | KOREV Evidence |
|--------|-------------------|----------------|
| Réponse | Génère du contenu plausible | Refuse si non sourcé |
| Sourcing | Optionnel | Obligatoire |
| Chiffres | Inventés ou approximés | Sourcés ou `UNVERIFIED` |
| Décision | Toujours une recommandation | `FAIL_CLOSED` si insuffisant |
| Risque | Décisions basées sur du faux | Décisions éclairées ou refus |

---

## Meta

| Champ | Valeur |
|-------|--------|
| **Document type** | `MARKET_STUDY` |
| **Criticality** | `HIGH` |
| **Evidence grade** | `INSUFFICIENT` |
| **Consensus status** | `fail_closed` |
| **Generated at** | 2026-01-30T20:30:00Z |
| **Template** | `evidence_native_strategic.md` v1.0.0 |

---

*KOREV Evidence — Refus explicite plutôt que contenu non vérifiable.*

---

## 💡 Ce que ce FAIL_CLOSED démontre

1. **Discipline** — Evidence ne cède pas à la pression de "produire quelque chose"
2. **Transparence** — Les lacunes sont listées explicitement
3. **Guidance** — Le chemin vers un document valide est clair
4. **Différenciation** — C'est exactement ce qui distingue Korev d'un chatbot

> **La valeur n'est pas dans le refus, mais dans ce qui vient après :**
> Un document sourcé, auditable, défendable.
