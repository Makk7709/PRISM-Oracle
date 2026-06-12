# Sources Open Data Juridiques France — Cartographie Vérifiée

## Vue d'ensemble

Ce document recense les sources officielles de données juridiques françaises, avec **URLs et licences vérifiées**.

**Dernière mise à jour**: 27 janvier 2026  
**Statut**: Production-ready avec traçabilité audit  
**Version**: `legal_sources@v1.0-enterprise`

> **AVERTISSEMENT IMPORTANT**
>
> **Ce module garantit la provenance et la traçabilité des sources, pas l'exhaustivité ni l'interprétation juridique.**
>
> Le droit opposable n'est authentifié que sur les sites officiels (legifrance.gouv.fr, courdecassation.fr, conseil-etat.fr, conseil-constitutionnel.fr).

> **Note**: Toutes les licences et CGU listées sont **vérifiées et sourcées**. Aucune affirmation implicite.

---

## Tableau récapitulatif des sources

| Source | Producteur | Licence | Access Mode | MAJ | Priorité |
|--------|------------|---------|-------------|-----|----------|
| **LEGI** | DILA | Licence Ouverte 2.0 | API_KEY_CGU | Quotidien | P0 |
| **JORF** | DILA | Licence Ouverte 2.0 | API_KEY_CGU | Quotidien | P0 |
| **CASS (Judilibre)** | Cour de cassation | Licence Ouverte 2.0 + CGU | API_KEY_CGU | Quotidien | P0 |
| **JADE** | DILA | Licence Ouverte 2.0 | REQUEST_TO_ADMIN | Hebdo | P1 |
| **CONSTIT** | Conseil constitutionnel | Licence Ouverte 2.0 | API_KEY_CGU | Mensuel | P1 |

---

## Détail par source (Fiche Conformité)

### 1. LEGI — Codes, lois et règlements consolidés

#### Identification

| Champ | Valeur |
|-------|--------|
| `source_id` | `legi` |
| `source_home_url` | <https://www.legifrance.gouv.fr> |
| `dataset_url` | <https://www.data.gouv.fr/fr/datasets/legi-codes-lois-et-reglements-consolides/> |
| `api_doc_url` | <https://piste.gouv.fr/api-catalog> (API Légifrance) |
| `producer` | DILA (Direction de l'Information Légale et Administrative) |

#### Licence et CGU

| Champ | Valeur |
|-------|--------|
| `license_name` | Licence Ouverte 2.0 (Etalab) |
| `license_url` | <https://www.etalab.gouv.fr/licence-ouverte-open-licence/> |
| `terms_name` | CGU PISTE + CGU Légifrance |
| `terms_url` | <https://piste.gouv.fr/cgu> |
| `access_mode` | `API_KEY_CGU` |

#### Obligations du réutilisateur

- Mentionner la source: "DILA - Légifrance"
- Mentionner la date de dernière mise à jour
- Ne pas altérer le sens des textes
- Le droit **opposable** n'est authentifié que sur legifrance.gouv.fr

#### Métadonnées techniques

| Champ | Valeur |
|-------|--------|
| `format` | XML (DTD LEGIFRANCE), JSON (API) |
| `update_frequency` | Quotidienne |
| `id_format` | LEGITEXT/LEGIARTI + 18 chiffres |
| `estimated_size` | ~15 Go (dump complet) |

#### Notes

- Accès FTPS: contacter <donnees-dila@dila.gouv.fr>
- API PISTE: inscription gratuite, quotas par jeton
- 73 codes officiels en vigueur + 29 abrogés

---

### 2. JORF — Journal Officiel de la République Française

#### Identification

| Champ | Valeur |
|-------|--------|
| `source_id` | `jorf` |
| `source_home_url` | <https://www.legifrance.gouv.fr/jorf> |
| `dataset_url` | <https://www.data.gouv.fr/fr/datasets/jorf/> |
| `api_doc_url` | <https://piste.gouv.fr/api-catalog> (API Légifrance) |
| `producer` | DILA |

#### Licence et CGU

| Champ | Valeur |
|-------|--------|
| `license_name` | Licence Ouverte 2.0 (Etalab) |
| `license_url` | <https://www.etalab.gouv.fr/licence-ouverte-open-licence/> |
| `terms_name` | CGU PISTE |
| `terms_url` | <https://piste.gouv.fr/cgu> |
| `access_mode` | `API_KEY_CGU` |

#### Métadonnées techniques

| Champ | Valeur |
|-------|--------|
| `format` | XML (DTD LEGIFRANCE) |
| `update_frequency` | Quotidienne |
| `id_format` | JORFTEXT + 18 chiffres |
| `coverage` | Depuis 1869 (numérisé), arrêtés depuis 1990 |

---

### 3. CASS (Judilibre) — Arrêts Cour de cassation

#### Identification

| Champ | Valeur |
|-------|--------|
| `source_id` | `cass` |
| `source_home_url` | <https://www.courdecassation.fr> |
| `dataset_url` | <https://www.data.gouv.fr/fr/dataservices/api-judilibre/> |
| `api_doc_url` | <https://piste.gouv.fr/api-catalog> (API Judilibre) |
| `producer` | Cour de cassation |

#### Licence et CGU

| Champ | Valeur |
|-------|--------|
| `license_name` | Licence Ouverte 2.0 (Etalab) |
| `license_url` | <https://www.etalab.gouv.fr/licence-ouverte-open-licence/> |
| `terms_name` | CGU Réutilisation Cour de cassation |
| `terms_url` | <https://www.courdecassation.fr/conditions-generales-dutilisation-pour-la-reutilisation-des-donnees-issues-des-decisions-de-justice> |
| `access_mode` | `API_KEY_CGU` |

#### Obligations spécifiques

- Respecter la pseudonymisation (données personnelles masquées)
- Respecter les quotas API PISTE
- CGU spécifiques de la Cour de cassation (en plus de la licence)

#### Métadonnées techniques

| Champ | Valeur |
|-------|--------|
| `format` | JSON (API REST) |
| `update_frequency` | Quotidienne |
| `id_format` | ID interne Judilibre, ECLI |
| `availability` | 99.9% |

#### Couverture temporelle

| Juridiction | Depuis |
|-------------|--------|
| Cour de cassation | 30/09/2021 |
| Juridictions 1er degré (contraventionnel/délictuel) | 31/12/2024 |
| Cours d'appel (contraventionnel/délictuel) | 31/12/2025 (prévu) |
| Matière criminelle | 31/12/2025 (prévu) |

#### Contact

- Email: <judilibre.courdecassation@justice.fr>

---

### 4. JADE — Jurisprudence administrative

#### Identification

| Champ | Valeur |
|-------|--------|
| `source_id` | `jade` |
| `source_home_url` | <https://www.conseil-etat.fr> |
| `dataset_url` | <https://www.data.gouv.fr/fr/datasets/jade/> |
| `api_doc_url` | N/A (FTPS uniquement) |
| `producer` | DILA (données Conseil d'État) |

#### Licence et CGU

| Champ | Valeur |
|-------|--------|
| `license_name` | Licence Ouverte 2.0 (Etalab) |
| `license_url` | <https://www.etalab.gouv.fr/licence-ouverte-open-licence/> |
| `terms_name` | Conditions DILA FTPS |
| `terms_url` | <https://echanges.dila.gouv.fr/OPENDATA/AVERTISSEMENT-Donnees_a_caractere_personnel.pdf> |
| `access_mode` | `REQUEST_TO_ADMIN` |

#### Métadonnées techniques

| Champ | Valeur |
|-------|--------|
| `format` | XML (DTD LEGIFRANCE) |
| `update_frequency` | Hebdomadaire |
| `id_format` | CETATEXT + 18 chiffres |

#### Alternative moderne

- Portail: <https://opendata.conseil-etat.fr/>
- Conseil d'État: depuis 30/09/2021
- CAA: depuis 31/03/2022
- TA: depuis 30/06/2022

---

### 5. CONSTIT — Décisions Conseil constitutionnel

#### Identification

| Champ | Valeur |
|-------|--------|
| `source_id` | `constit` |
| `source_home_url` | <https://www.conseil-constitutionnel.fr> |
| `dataset_url` | <https://www.data.gouv.fr/fr/datasets/constit-les-decisions-du-conseil-constitutionnel/> |
| `api_doc_url` | <https://www.conseil-constitutionnel.fr/donnees-ouvertes> |
| `producer` | Conseil constitutionnel |

#### Licence et CGU

| Champ | Valeur |
|-------|--------|
| `license_name` | Licence Ouverte 2.0 (Etalab) |
| `license_url` | <https://www.etalab.gouv.fr/licence-ouverte-open-licence/> |
| `terms_name` | CGU PISTE |
| `terms_url` | <https://piste.gouv.fr/cgu> |
| `access_mode` | `API_KEY_CGU` |

#### Métadonnées techniques

| Champ | Valeur |
|-------|--------|
| `format` | XML (DTD LEGIFRANCE) |
| `update_frequency` | Mensuelle (< 1 mois après publication) |
| `id_format` | CONSTEXT + 18 chiffres |
| `coverage` | Toutes décisions depuis 1958, QPC depuis 2010 |

---

## Access Modes

| Mode | Description | Exemple |
|------|-------------|---------|
| `OPEN_DOWNLOAD` | Téléchargement libre sans authentification | N/A actuellement |
| `API_KEY_CGU` | API avec clé + acceptation CGU | PISTE (LEGI, CASS, CONSTIT) |
| `REQUEST_TO_ADMIN` | Demande préalable à l'administrateur | FTPS DILA (JADE) |
| `PARTNERSHIP` | Partenariat institutionnel requis | N/A |

---

## Licence Ouverte 2.0 (Etalab) — Référence

### URL officielle

<https://www.etalab.gouv.fr/licence-ouverte-open-licence/>

### Droits accordés

- Reproduire, copier, publier, transmettre
- Diffuser, redistribuer
- Adapter, modifier, transformer
- Exploiter commercialement

### Obligations

1. **Mention de la source**: Indiquer la paternité
2. **Date de mise à jour**: Indiquer la date de dernière mise à jour
3. **Non-altération du sens**: Ne pas dénaturer les données

### Compatibilité

- Open Government Licence (UK)
- Open Data Commons Attribution (ODC-BY)
- Creative Commons Attribution (CC-BY 2.0)

---

## API PISTE — Référence

### URLs

| Ressource | URL |
|-----------|-----|
| Portail | <https://piste.gouv.fr> |
| CGU | <https://piste.gouv.fr/cgu> |
| OAuth2 Token | <https://oauth.piste.gouv.fr/api/oauth/token> |
| Catalogue API | <https://piste.gouv.fr/api-catalog> |

### Inscription

1. Créer un compte sur <https://piste.gouv.fr>
2. **Accepter les CGU** de chaque API souhaitée
3. Créer un projet
4. Obtenir client_id + client_secret

### Authentification OAuth2

```python
# Client Credentials Flow
import requests

response = requests.post(
    "https://oauth.piste.gouv.fr/api/oauth/token",
    data={
        "grant_type": "client_credentials",
        "client_id": "YOUR_CLIENT_ID",
        "client_secret": "YOUR_CLIENT_SECRET",
        "scope": "openid"
    }
)
access_token = response.json()["access_token"]
```

---

## Structure des identifiants

| Base | Préfixe | Longueur | Exemple |
|------|---------|----------|---------|
| LEGI (textes) | LEGITEXT | 18 chiffres | LEGITEXT000006070721 |
| LEGI (articles) | LEGIARTI | 18 chiffres | LEGIARTI000006420055 |
| JORF | JORFTEXT | 18 chiffres | JORFTEXT000000886460 |
| CASS | (ID interne) | variable | — |
| JADE | CETATEXT | 18 chiffres | CETATEXT000007630001 |
| CONSTIT | CONSTEXT | 18 chiffres | CONSTEXT000017665978 |

### ECLI (European Case Law Identifier)

Format: `ECLI:FR:[JURIDICTION]:[ANNÉE]:[NUMÉRO]`

| Juridiction | Code | Exemple |
|-------------|------|---------|
| Cour de cassation | CCASS | ECLI:FR:CCASS:2024:C00123 |
| Conseil d'État | CEASS | ECLI:FR:CEASS:2024:123456 |
| Conseil constitutionnel | CC | ECLI:FR:CC:2024:2024-1090.QPC |

---

## Contacts officiels

| Source | Contact | Type |
|--------|---------|------|
| DILA (LEGI, JORF, JADE) | <donnees-dila@dila.gouv.fr> | Email |
| Cour de cassation | <judilibre.courdecassation@justice.fr> | Email |
| Conseil d'État | <opendata@conseil-etat.fr> | Email |
| Conseil constitutionnel | <https://www.conseil-constitutionnel.fr/contact> | Formulaire |

---

## Limitations et avertissements

### Droit opposable

Le droit opposable n'est **authentifié que sur les sites officiels**:

- legifrance.gouv.fr (LEGI, JORF)
- courdecassation.fr (CASS)
- conseil-etat.fr (JADE)
- conseil-constitutionnel.fr (CONSTIT)

### Quotas API

Les APIs PISTE sont soumises à des quotas par jeton. Surveiller les headers:

- `X-RateLimit-Limit`
- `X-RateLimit-Remaining`
- `Retry-After` (sur 429)

### Pseudonymisation

Les décisions de justice (CASS, JADE) sont **pseudonymisées** conformément à la loi. Certaines informations contextuelles peuvent être masquées.

---

## Changelog

| Date | Modification |
|------|--------------|
| 2026-01-27 | Ajout URLs vérifiées, access_mode, terms_url |
| 2026-01-26 | Création document initial |
