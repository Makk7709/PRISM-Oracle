# Sources Open Data Juridiques France

## Vue d'ensemble

Ce document recense les sources officielles de données juridiques françaises disponibles en open data, validées pour intégration dans Korev Evidence.

**Dernière mise à jour**: Janvier 2026

---

## Tableau récapitulatif

| Source | Contenu | Format | Licence | Accès | MAJ | Priorité MVP |
|--------|---------|--------|---------|-------|-----|--------------|
| **LEGI** | Codes, lois, règlements consolidés | XML | Licence Ouverte 2.0 | FTPS / API PISTE | Quotidien | ✅ P0 |
| **JORF** | Journal Officiel (arrêtés, décrets) | XML | Licence Ouverte 2.0 | FTPS / API PISTE | Quotidien | ✅ P0 |
| **CASS (Judilibre)** | Arrêts Cour de cassation | JSON/API | Licence Ouverte 2.0 | API PISTE | Quotidien | ✅ P0 |
| **JADE** | Jurisprudence administrative (CE, CAA) | XML | Licence Ouverte 2.0 | FTPS | Hebdo | P1 |
| **CONSTIT** | Décisions Conseil constitutionnel | XML | Licence Ouverte 2.0 | FTPS / API PISTE | Mensuel | P1 |
| **CAPP** | Jurisprudence cours d'appel | XML | Licence Ouverte 2.0 | FTPS | Variable | P2 |
| **INCA** | Jurisprudence judiciaire diverse | XML | Licence Ouverte 2.0 | FTPS | Variable | P2 |

---

## Détail par source

### 1. LEGI — Codes, lois et règlements consolidés

**URL officielle**: https://www.data.gouv.fr/fr/datasets/legi-codes-lois-et-reglements-consolides/

**Producteur**: DILA (Direction de l'Information Légale et Administrative)

**Contenu**:
- 73 codes officiels en vigueur consolidés (+ 29 abrogés)
- Lois, décrets-lois, ordonnances, décrets depuis 1945
- Versions consolidées (historique des modifications conservé)

**Format**: XML (DTD LEGIFRANCE)

**Licence**: **Licence Ouverte 2.0 (Etalab)**
- Réutilisation libre, y compris commerciale
- Obligation: mentionner la source et la date de mise à jour

**Accès**:
- **FTPS**: Contacter donnees-dila@dila.gouv.fr
- **API PISTE**: https://piste.gouv.fr (inscription gratuite)

**Fréquence MAJ**: Quotidienne

**Taille estimée**: ~15 Go (dump complet XML)

**⚠️ Note légale**: Le droit opposable n'est authentifié que sur legifrance.gouv.fr

---

### 2. JORF — Journal Officiel de la République Française

**URL officielle**: https://www.data.gouv.fr/fr/datasets/jorf/

**Producteur**: DILA

**Contenu**:
- Textes publiés au JO depuis 1869 (numérisé)
- Arrêtés consolidés sélectionnés
- Arrêtés en version originale depuis 1990

**Format**: XML (DTD LEGIFRANCE)

**Licence**: **Licence Ouverte 2.0 (Etalab)**

**Accès**: FTPS / API PISTE

**Fréquence MAJ**: Quotidienne

**Taille estimée**: ~8 Go

---

### 3. CASS (Judilibre) — Arrêts Cour de cassation

**URL officielle**: https://www.data.gouv.fr/fr/dataservices/api-judilibre/

**Producteur**: Cour de cassation

**Contenu**:
- Décisions Cour de cassation depuis 30/09/2021
- Décisions juridictions 1er degré (contraventionnel/délictuel) depuis 31/12/2024
- Cours d'appel (contraventionnel/délictuel) prévu 31/12/2025
- Matière criminelle prévue 31/12/2025

**Métadonnées disponibles**:
- Date, numéros de pourvoi, juridiction, chambre, formation
- ECLI, niveau de publication, solution
- Titrage, sommaires
- Références textes appliqués
- Rapprochements jurisprudence
- Rapports/avis avocats généraux (si disponibles)

**Format**: JSON (API REST)

**Licence**: 
- **Licence Ouverte 2.0**
- CGU spécifiques Cour de cassation pour réutilisation
- Quotas API (via PISTE)

**Accès**: 
- **API PISTE** uniquement: https://piste.gouv.fr
- Documentation: https://www.courdecassation.fr/recherche-judilibre

**Contact**: judilibre.courdecassation@justice.fr

**Fréquence MAJ**: Quotidienne

**Taux disponibilité**: 99.9%

**⚠️ Pseudonymisation**: Décisions pseudonymisées (données personnelles masquées)

---

### 4. JADE — Jurisprudence administrative

**URL officielle**: https://www.data.gouv.fr/fr/datasets/jade/

**Producteur**: DILA (données Conseil d'État)

**Contenu**:
- **Conseil d'État**: 
  - "Grands arrêts" fondateurs du droit administratif
  - Recueil Lebon depuis 1965
  - Sélection décisions inédites depuis 1975 (élargie depuis 1986)
- **Cours administratives d'appel (CAA)**: Sélection d'arrêts depuis 1989
- **Tribunal des conflits**

**Format**: XML (DTD LEGIFRANCE)

**Licence**: **Licence Ouverte 2.0**

**Accès**: FTPS (donnees-dila@dila.gouv.fr)

**Fréquence MAJ**: Hebdomadaire

**⚠️ Alternative moderne**: https://opendata.conseil-etat.fr/ (portail dédié justice administrative)
- Conseil d'État: depuis 30/09/2021
- CAA: depuis 31/03/2022
- TA: depuis 30/06/2022

---

### 5. CONSTIT — Décisions Conseil constitutionnel

**URL officielle**: https://www.data.gouv.fr/fr/datasets/constit-les-decisions-du-conseil-constitutionnel/

**Producteur**: Conseil constitutionnel

**Contenu**:
- Toutes les décisions depuis 1958
- QPC (Questions Prioritaires de Constitutionnalité) depuis 2010
- DC, LP, L, FNR, etc.

**Format**: XML (DTD LEGIFRANCE)

**Licence**: **Licence Ouverte 2.0**

**Accès**: 
- FTPS
- API Légifrance (PISTE)

**Fréquence MAJ**: Mensuelle (< 1 mois après publication)

**Documentation**: https://www.conseil-constitutionnel.fr/donnees-ouvertes

---

## Accès API PISTE

### Inscription

1. Créer un compte sur https://piste.gouv.fr
2. Accepter les CGU de l'API souhaitée
3. Créer un projet
4. Obtenir un jeton d'accès (OAuth2)

### APIs disponibles

| API | Endpoint | Quotas |
|-----|----------|--------|
| Légifrance (LEGI, JORF, CONSTIT) | Via PISTE | Par jeton |
| Judilibre (CASS) | Via PISTE | Par jeton |

### Authentification

```python
# OAuth2 Client Credentials Flow
import requests

token_url = "https://oauth.piste.gouv.fr/api/oauth/token"
response = requests.post(token_url, data={
    "grant_type": "client_credentials",
    "client_id": "YOUR_CLIENT_ID",
    "client_secret": "YOUR_CLIENT_SECRET",
    "scope": "openid"
})
access_token = response.json()["access_token"]
```

---

## Licence Ouverte 2.0 (Etalab)

### Droits accordés

- ✅ Reproduire, copier, publier, transmettre
- ✅ Diffuser, redistribuer
- ✅ Adapter, modifier, transformer
- ✅ Exploiter commercialement

### Obligations

- **Mention de la source**: Indiquer la paternité (DILA, Cour de cassation, etc.)
- **Date de mise à jour**: Indiquer la date de dernière mise à jour des données
- **Non-altération du sens**: Ne pas dénaturer les données

### Compatibilité

Compatible avec:
- Open Government Licence (UK)
- Open Data Commons Attribution (ODC-BY)
- Creative Commons Attribution (CC-BY 2.0)

---

## Structure des données (DTD LEGIFRANCE)

### Identifiants

| Base | Format ID | Exemple |
|------|-----------|---------|
| LEGI | LEGITEXT + 18 chiffres | LEGITEXT000006070721 |
| JORF | JORFTEXT + 18 chiffres | JORFTEXT000000886460 |
| CASS | JURITEXT + 18 chiffres | JURITEXT000007024188 |
| JADE | CETATEXT + 18 chiffres | CETATEXT000007630001 |
| CONSTIT | CONSTEXT + 18 chiffres | CONSTEXT000017665978 |

### ECLI (European Case Law Identifier)

Format: `ECLI:FR:[JURIDICTION]:[ANNÉE]:[NUMÉRO]`

Exemples:
- `ECLI:FR:CCASS:2024:C00123` (Cour de cassation)
- `ECLI:FR:CEASS:2024:123456` (Conseil d'État)
- `ECLI:FR:CC:2024:2024-1090.QPC` (Conseil constitutionnel)

---

## Limitations connues

### LEGI/JORF
- Accès FTPS nécessite demande préalable à DILA
- Dump complet volumineux (~15 Go)
- Certains textes anciens (< 1987) ont des NOR techniques

### Judilibre (CASS)
- Pseudonymisation peut masquer des informations contextuelles
- Quotas API (à surveiller)
- Couverture progressive (pas encore criminelle)

### JADE
- Sélection non exhaustive pour CAA
- Pas d'API REST native (FTPS uniquement)

### CONSTIT
- Mise à jour mensuelle (moins réactif)

---

## Roadmap d'intégration Korev Evidence

### Phase 1 (MVP) — P0
- [x] LEGI: Codes principaux (Civil, Pénal, Commerce, Travail)
- [x] CASS (Judilibre): Arrêts depuis 2021

### Phase 2 — P1
- [ ] JADE: Grands arrêts Conseil d'État
- [ ] CONSTIT: QPC depuis 2010
- [ ] JORF: Sélection arrêtés récents

### Phase 3 — P2
- [ ] CAPP/INCA: Jurisprudence judiciaire élargie
- [ ] Couverture historique étendue

---

## Contacts

| Source | Contact |
|--------|---------|
| DILA (LEGI, JORF, JADE) | donnees-dila@dila.gouv.fr |
| Cour de cassation (Judilibre) | judilibre.courdecassation@justice.fr |
| Conseil d'État | opendata@conseil-etat.fr |
| Conseil constitutionnel | https://www.conseil-constitutionnel.fr/contact |

---

## Références

- [data.gouv.fr](https://www.data.gouv.fr)
- [Licence Ouverte 2.0](https://www.etalab.gouv.fr/licence-ouverte-open-licence/)
- [Portail PISTE](https://piste.gouv.fr)
- [Légifrance](https://www.legifrance.gouv.fr)
- [Judilibre](https://www.courdecassation.fr/recherche-judilibre)
- [Open Data Justice Administrative](https://opendata.conseil-etat.fr/)
