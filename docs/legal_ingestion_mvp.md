# Legal Sources — Guide d'Ingestion MVP

Guide complet pour l'ingestion des données juridiques françaises dans Korev Evidence.

## Prérequis

### Environnement

- Python 3.11+
- Virtual environment activé
- Accès réseau aux APIs

### Credentials API PISTE

Pour accéder aux APIs Légifrance et Judilibre, vous devez :

1. Créer un compte sur https://piste.gouv.fr
2. Accepter les CGU des APIs souhaitées
3. Créer un projet et obtenir vos credentials

```bash
# Configuration .env
PISTE_CLIENT_ID=votre_client_id
PISTE_CLIENT_SECRET=votre_client_secret
```

### Dépendances

```bash
pip install requests
```

---

## Commandes CLI

### Ingestion

```bash
# Ingérer les décisions de la Cour de cassation depuis une date
python -m legal_sources ingest --source cass --since 2025-01-01

# Ingérer les articles du Code civil (limité à 100)
python -m legal_sources ingest --source legi --since 2025-01-01 --limit 100

# Avec logs JSON
python -m legal_sources --log-format json ingest --source cass
```

### Vérification

```bash
# Vérifier l'intégrité des données ingérées
python -m legal_sources verify
```

### Statistiques

```bash
# Afficher les statistiques
python -m legal_sources stats
```

---

## Structure des données

### Répertoires

```
data/legal/
├── raw/           # Fichiers téléchargés bruts (cache)
├── processed/     # Documents normalisés (LegalDoc)
│   ├── legi/
│   └── cass/
├── index/         # Chunks indexables
│   ├── legi/
│   └── cass/
├── cache/         # Cache API
└── reports/       # Rapports d'ingestion
```

### Schéma LegalDoc

```json
{
  "doc_id": "abc123def456",
  "source": "legi",
  "origin_id": "LEGIARTI000006070721",
  "document_type": "code",
  "jurisdiction": "legislative",
  "title": "Article 1134",
  "citation": "Art. 1134 C. civ.",
  "date": "2024-01-01T00:00:00",
  "text": "Les conventions légalement formées...",
  "code_name": "Code civil",
  "article_number": "1134",
  "provenance": {
    "source": "legi",
    "source_name": "DILA",
    "origin_id": "LEGIARTI000006070721",
    "origin_url": "https://legifrance.gouv.fr/...",
    "retrieved_at": "2026-01-26T12:00:00",
    "license": "Licence Ouverte 2.0",
    "content_hash": "sha256..."
  }
}
```

### Schéma LegalChunk

```json
{
  "chunk_id": "chunk_abc123",
  "doc_id": "abc123def456",
  "chunk_index": 0,
  "text": "[Art. 1134 C. civ.]\n\nLes conventions...",
  "source": "legi",
  "document_type": "code",
  "citation": "Art. 1134 C. civ.",
  "pinpoint": "al. 1",
  "provenance": { ... }
}
```

---

## Mise à jour

### Mise à jour incrémentale

```bash
# Récupérer uniquement les documents modifiés depuis la dernière ingestion
python -m legal_sources ingest --source cass --since 2026-01-20
```

### Réingestion complète

```bash
# Supprimer les données existantes et réingérer
rm -rf data/legal/processed/cass data/legal/index/cass
python -m legal_sources ingest --source cass
```

### Planification (cron)

```bash
# Ingestion quotidienne à 3h du matin
0 3 * * * cd /path/to/korev && python -m legal_sources ingest --source cass --since $(date -d 'yesterday' +%Y-%m-%d)
```

---

## Diagnostic

### Vérifier l'intégrité

```bash
python -m legal_sources verify
```

Vérifie :
- Stabilité des doc_id et chunk_id
- Complétude des provenances
- Cohérence des données

### Logs d'erreur

```bash
# Logs JSON pour monitoring
python -m legal_sources --log-format json --log-level DEBUG ingest --source cass
```

### Problèmes courants

| Erreur | Cause | Solution |
|--------|-------|----------|
| `PISTE credentials not configured` | Variables d'environnement manquantes | Configurer PISTE_CLIENT_ID et PISTE_CLIENT_SECRET |
| `401 Unauthorized` | Token expiré | Vérifier les credentials PISTE |
| `429 Too Many Requests` | Quota API dépassé | Attendre ou demander augmentation quota |
| `Empty text for article` | Article sans contenu | Normal pour certains articles (ignoré) |

---

## Utilisation dans Korev Evidence

### Citations

```python
from python.helpers.legal_citations import format_citation, build_audit_trail

# Formater une citation
citation = format_citation(chunk_meta, format="full")
# "Art. 1134 C. civ., version consultée le 25/01/2026 (LEGIARTI000006070721)"

# Construire un audit trail pour une réponse
audit = build_audit_trail(chunks_used)
print(audit["citations"])
# ["Art. 1134 C. civ.", "Cass. civ. 1re, 15 janv. 2024, n° 22-18.456"]
```

### Recherche

Les chunks sont indexés avec :
- Texte pour recherche sémantique (embeddings)
- Métadonnées pour recherche lexicale (source, date, type)
- Citation et pinpoint pour référence précise

---

## Limitations connues

### Sources

- **LEGI**: Nécessite compte PISTE pour l'API (ou contact DILA pour FTPS)
- **CASS (Judilibre)**: Quotas API (à surveiller)
- **JADE**: Non implémenté dans le MVP (P1)
- **CONSTIT**: Non implémenté dans le MVP (P1)

### Performance

- Ingestion complète LEGI: plusieurs heures (73 codes)
- Ingestion CASS depuis 2021: ~30 minutes
- Chunking: <1s par document

### Données

- Pseudonymisation CASS: certaines informations masquées
- Articles abrogés: inclus avec status
- Historique: versions consolidées disponibles

---

## Roadmap

### MVP (Phase 1) ✅

- [x] LEGI via API PISTE
- [x] CASS via Judilibre
- [x] Chunking déterministe
- [x] Citations standardisées
- [x] Tests unitaires (22 tests)

### Phase 2 (P1)

- [ ] JADE (Conseil d'État)
- [ ] CONSTIT (Conseil constitutionnel)
- [ ] Indexation FAISS
- [ ] Recherche hybride (sémantique + lexicale)

### Phase 3 (P2)

- [ ] CAPP/INCA (jurisprudence élargie)
- [ ] Synchronisation temps réel
- [ ] Dashboard de monitoring

---

## Références

- [Sources Open Data FR](./legal_sources_fr.md)
- [API Judilibre](https://www.courdecassation.fr/recherche-judilibre)
- [Portail PISTE](https://piste.gouv.fr)
- [Licence Ouverte 2.0](https://www.etalab.gouv.fr/licence-ouverte-open-licence/)
