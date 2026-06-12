<!-- cspell:words LEGIARTI echr etat cjue cedh legifrance -->
# Legal Inter-Agent Collaboration

> **P4** — Contrats et permissions pour la collaboration inter-agents dans le pipeline juridique.

---

## Principes Fondamentaux

### 1. Artefacts, Pas de Réponses

Les sous-agents ne produisent **jamais** de réponse finale. Ils produisent uniquement des **artefacts structurés** :

```text
┌─────────────────────────────────────────────────────────────────────────┐
│                        INTERDIT POUR LES SOUS-AGENTS                     │
├─────────────────────────────────────────────────────────────────────────┤
│  ❌ "En conclusion, le contrat est valide."                             │
│  ❌ "Ma réponse est que vous avez raison."                              │
│  ❌ "Final answer: ..."                                                  │
│  ❌ "Pour conclure..."                                                   │
└─────────────────────────────────────────────────────────────────────────┘
```

### 2. Fail-Closed

Toute violation de contrat entraîne un **rejet immédiat** avec log.

---

## Artefacts Autorisés

### 1. FactExtraction

**Producteur** : Extraction Agent  
**Consommateur** : Legal Orchestrator

```json
{
  "_type": "FactExtraction",
  "facts": [
    "Le contrat a été signé le 1er janvier 2024",
    "La société A est le vendeur"
  ],
  "ambiguities": [
    "Date d'effet non précisée"
  ],
  "parties": ["Société A", "Société B"],
  "dates": ["2024-01-01"],
  "context_hints": {
    "domain": "droit_des_contrats"
  },
  "correlation_id": "corr_123"
}
```

**Contraintes** :

- `facts` non vide (minimum 1)
- Aucun texte contenant des patterns de "réponse finale"

---

### 2. SourceNote

**Producteur** : Retrieval Agent, Research Agent  
**Consommateur** : Draft Builder, Judge

```json
{
  "_type": "SourceNote",
  "origin_url": "https://www.legifrance.gouv.fr/codes/article_lc/LEGIARTI000006436298",
  "publisher": "legifrance",
  "jurisdiction": "fr",
  "excerpt": "Les contrats légalement formés tiennent lieu de loi à ceux qui les ont faits.",
  "excerpt_hash": "a1b2c3d4e5f67890",
  "chunk_id": "chunk_001",
  "confidence": 0.95,
  "document_id": "LEGIARTI000006436298",
  "retrieved_at": "2024-01-15T10:30:00Z",
  "content_hash": "sha256_full_hash",
  "license_tag": "Licence Ouverte 2.0",
  "title": "Article 1103 - Force obligatoire des contrats"
}
```

**Contraintes** :

- `publisher` **doit être dans la whitelist** (voir ci-dessous)
- `excerpt_hash` doit correspondre au hash SHA256 de `excerpt`
- `origin_url` doit être une URL valide (http/https)
- `jurisdiction` : `fr`, `eu`, ou `echr`

---

### 3. ClaimProposal

**Producteur** : Draft Builder Agent  
**Consommateur** : Judge, Consensus

```json
{
  "_type": "ClaimProposal",
  "claim_text": "Les contrats doivent être exécutés de bonne foi",
  "claim_type": "cited",
  "citation": "Art. 1104 C. civ.",
  "source_note": { /* SourceNote complet */ },
  "source_chunk_id": "chunk_002"
}
```

**Contraintes** :

- `claim_type` : `cited` ou `hypothesis`
- Si `cited` → `source_note` **obligatoire** avec publisher whitelisted
- Si `hypothesis` → `basis_if_hypothesis` **obligatoire**

---

### 4. Critique

**Producteur** : Judge Agent, Review Agent  
**Consommateur** : Orchestrator

```json
{
  "_type": "Critique",
  "issues": [
    "Absence de citation pour l'affirmation sur la nullité"
  ],
  "missing_info": [
    "Juridiction non précisée"
  ],
  "contradictions": [],
  "severity": "high",
  "recommendation": "Ajouter les sources manquantes"
}
```

**Contraintes** :

- Au moins un élément dans `issues`, `missing_info`, ou `contradictions`
- `severity` : `low`, `medium`, `high`, ou `critical`
- `high`/`critical` = bloquant

---

## Publisher Whitelist

| Publisher | Code | Juridiction |
| --- | --- | --- |
| Légifrance | `legifrance` | FR |
| Cour de cassation | `cour_de_cassation` | FR |
| Conseil d'État | `conseil_etat` | FR |
| Conseil constitutionnel | `conseil_constitutionnel` | FR |
| EUR-Lex | `eur-lex` | EU |
| CJUE | `cjue` | EU |
| CEDH | `cedh` | ECHR |

**Tout autre publisher est rejeté.**

---

## Flux de Données

```text
┌──────────────────────────────────────────────────────────────────────────────┐
│                         FLUX INTER-AGENTS                                     │
└──────────────────────────────────────────────────────────────────────────────┘

  User Query
       │
       ▼
  ┌─────────────────────────────────────────────────────────────────────────┐
  │ Extraction Agent                                                         │
  │   Input:  User query (string)                                           │
  │   Output: FactExtraction { facts, ambiguities, parties, dates }         │
  └─────────────────────────────────────────────────────────────────────────┘
       │
       ▼
  ┌─────────────────────────────────────────────────────────────────────────┐
  │ Retrieval Agent                                                          │
  │   Input:  FactExtraction                                                 │
  │   Output: List<SourceNote> (uniquement publishers whitelisted)          │
  └─────────────────────────────────────────────────────────────────────────┘
       │
       ▼
  ┌─────────────────────────────────────────────────────────────────────────┐
  │ Draft Builder Agent                                                      │
  │   Input:  FactExtraction + List<SourceNote>                              │
  │   Output: List<ClaimProposal> (CITED avec SourceNote, ou HYPOTHESIS)    │
  └─────────────────────────────────────────────────────────────────────────┘
       │
       ▼
  ┌─────────────────────────────────────────────────────────────────────────┐
  │ Judge Agent                                                              │
  │   Input:  List<ClaimProposal>                                            │
  │   Output: Critique { issues, missing_info, contradictions }             │
  └─────────────────────────────────────────────────────────────────────────┘
       │
       ▼
  ┌─────────────────────────────────────────────────────────────────────────┐
  │ Legal Orchestrator                                                       │
  │   Input:  All artifacts                                                  │
  │   Output: LegalOutput (APPROVED/SAFE/REFUSAL)  ← SEUL OUTPUT FINAL      │
  └─────────────────────────────────────────────────────────────────────────┘
```

---

## Validation des Artefacts

### Au niveau code

```python
from python.helpers.legal_agent_contracts import (
    FactExtraction,
    SourceNote,
    ClaimProposal,
    Critique,
    parse_artifact,
    ContractValidationError,
    FinalAnswerDetectedError,
    NonWhitelistedPublisherError,
)

# Validation automatique à la création
try:
    fe = FactExtraction(facts=["Fait 1", "Fait 2"])
except ContractValidationError as e:
    print(f"Validation failed: {e}")

# Parsing d'un artifact JSON
data = {"_type": "SourceNote", "origin_url": "...", ...}
artifact = parse_artifact(data["_type"], data)
```

### Détection de réponse finale

```python
from python.helpers.legal_agent_contracts import detect_final_answer

# True si contient un pattern de réponse finale
detect_final_answer("En conclusion, le contrat est valide.")  # True
detect_final_answer("L'article 1103 dispose que...")  # False
```

---

## Erreurs et Logs

### Types d'erreurs

| Exception | Cause | Action |
| --- | --- | --- |
| `ContractValidationError` | Champ manquant/invalide | Log + REFUSAL |
| `FinalAnswerDetectedError` | Sous-agent produit une réponse | Log + REJECT artifact |
| `NonWhitelistedPublisherError` | Publisher non autorisé | Log + REJECT source |

### Format de log

```json
{
  "event": "contract_validation_failed",
  "correlation_id": "corr_123",
  "timestamp": 1705320000.0,
  "artifact_type": "SourceNote",
  "error": "Publisher 'blog_juridique' not in whitelist"
}
```

---

## Changelog

### v1.0.0 (P4)

- Définition des 4 artefacts : FactExtraction, SourceNote, ClaimProposal, Critique
- Publisher whitelist (FR + EU)
- Détection de réponse finale
- Validation excerpt_hash
