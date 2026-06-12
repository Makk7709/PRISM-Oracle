# Legal Sources — Sources Officielles

> **P4** — Gestion des sources juridiques officielles pour le pipeline KOREV Evidence.

---

## Principes

### 1. Whitelist Stricte

Seules les sources provenant de **publishers autorisés** peuvent être utilisées pour des citations `CITED`.

### 2. Provenance Complète

Chaque source doit avoir une **provenance traçable** avec tous les champs requis.

### 3. Intégrité Vérifiable

Les excerpts sont hashés pour garantir l'intégrité (`excerpt_hash`).

---

## Publishers Autorisés

### France (FR)

| Publisher | Code | URL Base | Licence |
|-----------|------|----------|---------|
| **Légifrance** | `legifrance` | `legifrance.gouv.fr` | Licence Ouverte 2.0 |
| Cour de cassation | `cour_de_cassation` | `courdecassation.fr` | Licence Ouverte 2.0 |
| Conseil d'État | `conseil_etat` | `conseil-etat.fr` | Licence Ouverte 2.0 |
| Conseil constitutionnel | `conseil_constitutionnel` | `conseil-constitutionnel.fr` | Licence Ouverte 2.0 |

**Priorité** : Légifrance est la source primaire pour le droit français.

### Union Européenne (EU)

| Publisher | Code | URL Base | Licence |
|-----------|------|----------|---------|
| **EUR-Lex** | `eur-lex` | `eur-lex.europa.eu` | CC BY 4.0 |
| CJUE | `cjue` | `curia.europa.eu` | Public |
| CEDH | `cedh` | `hudoc.echr.coe.int` | Public |

---

## Provenance — Champs Requis

### Obligatoires (P4)

| Champ | Description | Exemple |
|-------|-------------|---------|
| `source` | Code du publisher | `legifrance` |
| `source_name` | Nom lisible | `Légifrance` |
| `origin_url` | URL de la source | `https://www.legifrance.gouv.fr/...` |
| `license_name` | Nom de la licence | `Licence Ouverte 2.0` |

### Recommandés

| Champ | Description | Exemple |
|-------|-------------|---------|
| `jurisdiction` | Juridiction | `fr`, `eu`, `echr` |
| `document_id` | ID unique du document | `LEGIARTI000006436298` |
| `retrieved_at` | Date de récupération | `2024-01-15T10:30:00Z` |
| `content_hash` | Hash SHA256 du contenu complet | `abc123...` |
| `version_date` | Date de la version | `2024-01-01` |

### Exemple complet

```json
{
  "provenance": {
    "source": "legifrance",
    "source_name": "Légifrance",
    "origin_id": "LEGIARTI000006436298",
    "origin_url": "https://www.legifrance.gouv.fr/codes/article_lc/LEGIARTI000006436298",
    "license_name": "Licence Ouverte 2.0",
    "license_url": "https://www.etalab.gouv.fr/licence-ouverte-open-licence",
    "access_mode": "api",
    "jurisdiction": "fr",
    "retrieved_at": "2024-01-15T10:30:00Z",
    "content_hash": "sha256:abc123...",
    "version_date": "2016-10-01"
  }
}
```

---

## Ingestion

### Script d'ingestion officielle

```bash
# Build index avec validation whitelist
python scripts/build_legal_index_official.py \
  --use-fixture \
  --output data/legal_index_official \
  --verbose
```

### Script de validation

```bash
# Valider le corpus fixture
python scripts/validate_legal_sources.py --corpus

# Valider un fichier JSON
python scripts/validate_legal_sources.py --input sources.json

# Valider un index existant
python scripts/validate_legal_sources.py --index data/legal_index
```

### Rapport de validation

```json
{
  "timestamp": "2024-01-15T10:30:00Z",
  "total": 20,
  "valid": 20,
  "invalid": 0,
  "error_count": 0,
  "warning_count": 5,
  "duplicate_count": 0,
  "publishers": {
    "legifrance": 13,
    "cour_de_cassation": 7
  },
  "jurisdictions": {
    "fr": 20
  }
}
```

---

## Vérification d'Intégrité

### Excerpt Hash

Chaque `SourceNote` contient un `excerpt_hash` calculé ainsi :

```python
import hashlib

def compute_excerpt_hash(excerpt: str) -> str:
    return hashlib.sha256(excerpt.encode("utf-8")).hexdigest()[:16]

# Vérification
expected_hash = compute_excerpt_hash(source_note.excerpt)
assert source_note.excerpt_hash == expected_hash
```

### Content Hash

Pour les documents complets :

```python
def compute_content_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()
```

---

## Fréquence de Mise à Jour

| Source | Fréquence recommandée | Notes |
|--------|----------------------|-------|
| Légifrance | Hebdomadaire | Codes et lois |
| Jurisprudence Cass | Mensuelle | Nouveaux arrêts |
| EUR-Lex | Mensuelle | Réglements EU |

### Processus de mise à jour

1. **Télécharger** les nouvelles sources via API
2. **Valider** avec `validate_legal_sources.py`
3. **Indexer** avec `build_legal_index_official.py`
4. **Vérifier** les hashes de l'index
5. **Déployer** le nouvel index

---

## Dépannage

### Source non whitelisted

```text
NonWhitelistedPublisherError: Publisher 'blog_juridique' not in whitelist
```

**Cause** : La source provient d'un publisher non autorisé.

**Solution** :

- Utiliser uniquement des sources officielles
- Ou demander l'ajout du publisher à la whitelist (avec justification)

### Hash mismatch

```text
ContractValidationError: SourceNote.excerpt_hash: Hash mismatch: expected abc123, got xyz789
```

**Cause** : L'excerpt a été modifié après création de la SourceNote.

**Solution** :

- Recalculer le hash avec l'excerpt actuel
- Ou recharger l'excerpt depuis la source originale

### Provenance incomplète

```text
ContractValidationError: Missing provenance fields: origin_url, license_name
```

**Cause** : La provenance n'a pas tous les champs requis.

**Solution** :

- Ajouter les champs manquants
- Vérifier que la source originale fournit ces informations

---

## API Légifrance

### Accès

- **URL** : `https://api.legifrance.gouv.fr`
- **Auth** : OAuth2 (PISTE)
- **Documentation** : [piste.gouv.fr](https://piste.gouv.fr)

### Endpoints utiles

| Endpoint | Description |
|----------|-------------|
| `/consult/code/article/{id}` | Article de code |
| `/search/codeLoda` | Recherche dans les codes |
| `/consult/juri` | Jurisprudence |

### Exemple de requête

```python
import requests

response = requests.get(
    "https://api.legifrance.gouv.fr/consult/code/article/LEGIARTI000006436298",
    headers={"Authorization": f"Bearer {token}"},
)

article = response.json()
```

---

## Changelog

### v1.0.0 (P4)

- Définition de la whitelist publishers (FR + EU)
- Schéma de provenance étendu
- Scripts d'ingestion et validation
- Documentation des champs requis
