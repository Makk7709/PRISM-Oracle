<!-- markdownlint-disable MD060 MD032 MD029 MD014 MD013 MD040 MD036 MD034 -->

# 13 — Reserves Resolution & Disclosure (micro-verrouillage post-push)

**Mission** : micro-verrouillage documentaire final apres push de `2f3eb0e6`, avant transmission externe a Diag & Grow / commissaire aux apports.
**Auteur** : agent Cursor en posture "commissaire aux apports prudent + auditeur documentaire hostile + responsable conformite confidentialite".
**Date** : 15 mai 2026.
**Branche** : `diag-grow/transmission-evidence`.
**HEAD avant cette mission** : `2f3eb0e6` (synchronise local + origin).
**Perimetre strict de cette mission** : documentaire et sanitization. **Aucune modification de code applicatif**.

---

## 1. Etat des lieux

### 1.1 Git

- Branche : `diag-grow/transmission-evidence`
- HEAD local : `2f3eb0e639309f26c53977c5ebd3a8844883a30c`
- HEAD origin : `2f3eb0e639309f26c53977c5ebd3a8844883a30c`
- Synchronisation : 0 commit d'ecart
- Working tree clean (modulo derive submodules `mcp_servers/openalex` et `mcp_servers/semanticscholar`, hors perimetre)

### 1.2 Reserves residuelles heritees de la mission `2f3eb0e6`

Trois reserves residuelles documentees dans `12_EXTERNAL_AUDITOR_READINESS_REPORT.md` (etat 10 mai 2026) :

- **RES-1** : prenoms clients reels dans 4 fichiers trackes hors perimetre initial.
- **RES-2** : mentions clients (DICA, Tarmac, Centrale Lille) dans documents valorisation, sous reserve verification NDA.
- **RES-3** : audit licence interne 2025-02-08 (>14 mois), sans rapport `pip-licenses` annexe.

La presente mission a traite chacune dans la limite de l'autorisation "documentaire / sanitization, sans modification applicative".

---

## 2. RES-1 — Traitement des prenoms clients reels dans fichiers trackes

### 2.1 Inspection precise des 4 fichiers

| Fichier | Type | Nature des prenoms | Volume | Linkage applicatif |
|---|---|---|---|---|
| `deploy/docker-compose.yml` | **Code Docker operationnel** | Utilisateurs Samba reels (`coralie`, `dominique`, `laurianne`, `nicolas`, `luc`, `jeremie`, `sarah`, `amine`) + mots de passe placeholders `CHANGER_CE_MDP_*` | 8 lignes utilisateurs + 7 lignes shares | **Direct** : prenoms = paths Samba runtime `/shared/users/<prenom>/` |
| `docs/GUIDE_DEPLOIEMENT_ENTREPRISE.md` | Documentation deploiement entreprise | Memes prenoms, plus mots de passe d'exemple `MotDePasseCoralie2026!`, `MotDePasseDominique2026!`, etc. | ~47 occurrences (block code yaml, table permissions, ASCII art structure) | **Indirect** : reference croisee massive vers `deploy/docker-compose.yml` |
| `docs/SPEC_MULTI_USER_WORKSPACE.md` | Specification technique | Exemple JSON `users.json` avec `nicolas`, `luc`, `amine` | 3 lignes structurelles | **Faible** : exemple illustratif uniquement |
| `tests/test_organization_canonical.py` | Test applicatif TDD | `nicolas`, `jeremie`, `coralie` comme utilisateurs de test + tenant `DICA France` | ~15 occurrences | **Direct** : assertions d'isolation cross-tenant (`org_match`, `Principal`, registry) |

### 2.2 Decision detaillee par fichier

#### 2.2.1 `docs/SPEC_MULTI_USER_WORKSPACE.md` — **SANITISE**

Modification effectuee dans le commit de micro-verrouillage :

```diff
- Format `users.json` :
+ Format `users.json` (exemple structurel, identifiants fictifs) :
   ```json
   {
     "users": {
-      "nicolas":  {"password_hash": "$argon2id$...", "role": "user"},
-      "luc":      {"password_hash": "$argon2id$...", "role": "user"},
-      "amine":    {"password_hash": "$argon2id$...", "role": "admin"}
+      "user1":  {"password_hash": "$argon2id$...", "role": "user"},
+      "user2":  {"password_hash": "$argon2id$...", "role": "user"},
+      "admin":  {"password_hash": "$argon2id$...", "role": "admin"}
     }
   }
```

Verification post-correction : `grep -nE 'nicolas|luc|amine|coralie|dominique|laurianne|jeremie|sarah' docs/SPEC_MULTI_USER_WORKSPACE.md` retourne **0 occurrence**.

#### 2.2.2 `deploy/docker-compose.yml` — **CONSERVE EN L'ETAT** (raison technique)

Justification :

- Les prenoms cohabitent avec des **placeholders explicites** `CHANGER_CE_MDP_*` (cf. lignes 280-282).
- Les paths Samba `/shared/users/coralie`, `/shared/users/dominique`, `/shared/users/laurianne` referencent des **utilisateurs runtime reels** sur le serveur de production.
- Toute modification ici **casserait les paths Samba** runtime et empecherait les utilisateurs reels d'acceder a leurs partages.
- Cette modification doit faire l'objet d'une **mission applicative dediee** (renommer les utilisateurs cote serveur + mettre a jour compose en synchronisation + reprovisionner les partages + tester).

Risque pour transmission : **MODERE**. Un auditeur prudent verra des prenoms PII dans un fichier de configuration Docker. Aucun secret exploitable n'est associe (placeholders).

#### 2.2.3 `docs/GUIDE_DEPLOIEMENT_ENTREPRISE.md` — **CONSERVE EN L'ETAT** (raison de coherence documentaire)

Justification :

- 47 occurrences referencent explicitement `deploy/docker-compose.yml`. Sanitiser le guide seul creerait une **incoherence systematique** entre le guide et le compose.yml reel.
- Le guide contient en outre des mots de passe d'exemple typo-realistes (`MotDePasseCoralie2026!`, `MotDePasseDominique2026!`, etc.) qui ne sont PAS des mots de passe reels mais des exemples d'**illustration de format**.
- La sanitization devrait etre **synchronisee** avec celle de `deploy/docker-compose.yml` pour preserver la coherence — mission applicative et documentaire couplee, hors perimetre actuel.

Risque pour transmission : **MODERE**. Meme analyse que 2.2.2.

#### 2.2.4 `tests/test_organization_canonical.py` — **CONSERVE EN L'ETAT** (raison applicative + RES-2)

Justification :

- Test applicatif TDD verifiant l'**isolation cross-tenant** entre `DICA France` (slug `dica-france`) et `Korev`. Test critique pour le bug regression "DICA France" vs "dica-france" (commit `yENoyKIZ`).
- Renommer `coralie`, `nicolas`, `jeremie` casserait les assertions specifiques de scenarios d'isolation et necessiterait une re-execution complete TDD.
- `DICA France` est par ailleurs traite dans RES-2 (decision strategique d'apporteur sur les mentions clients valorisation).
- Risque double : applicatif (regression test) + commercial (perte de la mention DICA dans tests = perte d'un signal de validation client).

Risque pour transmission : **FAIBLE** (perimetre tests, lecture par auditeur technique uniquement).

### 2.3 Synthese RES-1

| Action | Fichier | Statut |
|---|---|---|
| Sanitisation | `docs/SPEC_MULTI_USER_WORKSPACE.md` | **Fait** (commit micro-verrouillage) |
| Documentation explicite | `deploy/docker-compose.yml` | Acte ci-dessus, perimetre applicatif |
| Documentation explicite | `docs/GUIDE_DEPLOIEMENT_ENTREPRISE.md` | Acte ci-dessus, perimetre documentaire couple au compose |
| Documentation explicite | `tests/test_organization_canonical.py` | Acte ci-dessus, perimetre tests applicatifs |

**Decision strategique apporteur attendue** : accepter la transmission en l'etat des 3 fichiers conserves OU planifier une **mission de re-anonymisation profonde** (renommer en `user1/user2/...` les utilisateurs Samba ET le guide ET les tests, avec re-execution TDD). Estimation : 4-6h de travail technique + verification.

**Recommandation auditeur hostile interne** : la transmission en l'etat est acceptable des lors que l'apporteur **annonce explicitement a Diag & Grow** la presence de ces references dans le perimetre operationnel (deploy/, GUIDE, tests) en mettant en avant que :

- aucun secret exploitable n'est expose ;
- les utilisateurs concernes sont les **utilisateurs reels du deploiement pilote** et leur mention est coherente avec la presentation de la base installee ;
- une mission de re-anonymisation est planifiable a la demande.

---

## 3. RES-2 — Mentions clients DICA / Tarmac / Centrale Lille

### 3.1 Inventaire

Les mentions clients identifiees dans la presente mission sont **strategiques pour la defense de la borne haute de valorisation** (preuve de base installee et de validation marche). Elles apparaissent dans :

- `docs/RAPPORT_TECHNIQUE_VALORISATION_EVIDENCE.md`
- `docs/DOSSIER_COMMISSAIRE_APPORTS_EVIDENCE.md`
- `docs/valuation/04_HOURS_RECONSTRUCTION_REGISTER.md` (mention indirecte)
- `tests/test_organization_canonical.py` (DICA France comme tenant de test, voir RES-1)

### 3.2 Decision

La verification de **couverture NDA** depasse le perimetre technique d'un agent Cursor : elle releve d'une verification documentaire contractuelle cote apporteur.

**Decision strategique apporteur attendue avant transmission externe** :

| Hypothese | Action |
|---|---|
| NDA / clauses contractuelles avec DICA, Tarmac, Centrale Lille **couvrent** la mention dans un dossier d'apport / valorisation interne | Transmission **en l'etat**. Decision **a documenter explicitement** dans l'email de transmission (cf. modele §6). |
| NDA / clauses **ne couvrent pas** ou doute | **Anonymisation a posteriori** des mentions : `DICA FRANCE -> Client A (PME conseil)`, `Tarmac -> Client B (incubateur public)`, `Centrale Lille / Pr Lafhaj -> Client C (chaire universitaire)`. Operation documentaire de ~1h sur le pack. |

**Recommandation auditeur hostile interne** : conserver les mentions explicites apporte une **forte valeur defensive** sur la valorisation (signal marche). Si NDA non couvrant, l'anonymisation a posteriori n'affaiblit pas significativement la defense de la fourchette **850-1 200 kEUR** car la presence des clients reste documentable via factures / contrats annexes hors pack Git.

### 3.3 Statut

**Action requise apporteur** : verifier NDA AVANT transmission. Si doute, anonymisation a posteriori.

**Cette mission ne modifie pas les mentions clients** dans les documents existants (perimetre strict).

---

## 4. RES-3 — Audit licence externe — **TRAITE COMPLET**

### 4.1 Action realisee

Re-scan `pip-licenses` execute le **2026-05-15** sur le `venv/` local du repo (Python 3.11), avec la commande :

```bash
venv/bin/pip-licenses --format=markdown --order=license --with-urls \
  --output-file=docs/annexes-externes/AE-11_pip-licenses_2026-05-15.md
venv/bin/pip-licenses --format=json --with-urls \
  --output-file=docs/annexes-externes/AE-11_pip-licenses_2026-05-15.json
```

Trois fichiers ajoutes :

- `docs/annexes-externes/AE-11_pip-licenses_2026-05-15.md` (rapport markdown brut, 425 lignes)
- `docs/annexes-externes/AE-11_pip-licenses_2026-05-15.json` (meme contenu JSON)
- `docs/annexes-externes/AE-11_pip-licenses_README.md` (analyse synthetique, classification famille par famille, interpretation juridique)

### 4.2 Findings consolides (cf. README annexe pour detail)

| Famille | Compte | Verdict |
|---|---:|---|
| Permissives (MIT, BSD, Apache 2.0, ISC, PSF, Unlicense) | ~350 | Compatible commercial sans contrainte |
| LGPL (chardet, crontab, num2words, paramiko, pi_heif) | 5 | Compatible commercial par linkage dynamique Python |
| MPL 2.0 (certifi, legacy-api-wrap, pathspec, pikepdf, tqdm) | 5 | Compatible commercial (file-level copyleft, packages non modifies) |
| Triple licence (`pyphen` GPLv2+ OR LGPLv2+ OR MPL 1.1) | 1 | Utilise sous **MPL 1.1**, pas de contamination GPL |
| Native GPL via loader Python (`espeakng-loader` -> eSpeak NG GPL v3+) | 1 | **Isolable** : fonctionnalite TTS hors perimetre valorise |
| GPL pur direct | **0** | — |
| AGPL | **0** | — |
| SSPL | **0** | — |
| UNKNOWN (apres verification manuelle `pip show`) | 0 | Tous reclassifies en permissifs (Apache 2.0, BSD-3, MIT) |

### 4.3 Reformulation `legal/THIRD_PARTY_NOTICES.txt` v2

Le fichier `legal/THIRD_PARTY_NOTICES.txt` est reformule pour expliciter :

- L'historique des audits (2025-02-08 puis 2026-05-15).
- La presence et la nature des packages LGPL / MPL 2.0 / `pyphen` / `espeakng-loader`.
- La discipline existante d'exclusion GPL stricte (cf. `requirements.txt` commentaires `ansio` et `html2text`).
- La reference explicite a l'annexe AE-11 livree dans le repo.

L'affirmation precedente "no GPL, AGPL, or SSPL" est **conservee** car techniquement correcte (0 package GPL-only direct, 0 AGPL, 0 SSPL), mais elle est desormais **completee** par la disclosure des LGPL / MPL et du cas `espeakng-loader`.

### 4.4 Validite

Le scan AE-11 est **valide 30 jours**. Re-scan recommande si transmission posterieure au **2026-06-14**.

### 4.5 Statut

**Reserve LEVEE** au 2026-05-15. Annexe AE-11 livree avec le pack Evidence.

---

## 5. Diff final attendu pour le commit de micro-verrouillage

| Fichier | Type modification | Justification |
|---|---|---|
| `docs/SPEC_MULTI_USER_WORKSPACE.md` | Sanitization JSON exemple | RES-1 traite (perimetre minimal) |
| `legal/THIRD_PARTY_NOTICES.txt` | Reformulation v2 avec LGPL/MPL/espeakng | RES-3 traite |
| `docs/annexes-externes/AE-11_pip-licenses_2026-05-15.md` | Creation (rapport brut markdown) | RES-3 traite |
| `docs/annexes-externes/AE-11_pip-licenses_2026-05-15.json` | Creation (rapport brut JSON) | RES-3 traite |
| `docs/annexes-externes/AE-11_pip-licenses_README.md` | Creation (analyse synthetique) | RES-3 traite |
| `docs/valuation/12_EXTERNAL_AUDITOR_READINESS_REPORT.md` | Mise a jour statut RES-1 / RES-2 / RES-3 + HEAD `2f3eb0e6` | Tracabilite |
| `docs/valuation/13_RESERVES_RESOLUTION_AND_DISCLOSURE.md` | Creation (le present document) | Tracabilite des decisions |

Aucun fichier de code applicatif n'est modifie. Aucun test n'est modifie.

---

## 6. Modele d'email de transmission recommande (mise a jour)

Ce modele complete celui propose dans `12_EXTERNAL_AUDITOR_READINESS_REPORT.md` en integrant les ajustements post-micro-verrouillage.

```text
Objet : Transmission Evidence pour evaluation — branche diag-grow/transmission-evidence

Bonjour [contact Diag & Grow / commissaire],

Vous trouverez sur la branche `diag-grow/transmission-evidence` du depot KOREV-Oracle
le pack complet de valorisation Evidence (HEAD `2f3eb0e6`, mis a jour le 15 mai 2026).

Documents prioritaires (dans `docs/valuation/`) :
- 00 a 08 : pack original de valorisation (diagnostic, delta Agent Zero, modules, heures, qualite, limites, transmission, auto-audit).
- 09 : corrections post-audit interne (DEF-A1/A2/A3/A7).
- 10 : checklist anti-secrets de transmission.
- 11 : audit factuel total (claim-to-evidence matrix).
- 12 : verdict externe pre-transmission.
- 13 : traitement final des reserves residuelles (RES-1, RES-2, RES-3) — present document.
- CONTROLE_AUDIT_PACK_2026-05-09.md : audit independant.

Documents annexes obligatoires :
- `docs/RAPPORT_TECHNIQUE_VALORISATION_EVIDENCE.md` (rapport technique principal).
- `docs/DOSSIER_COMMISSAIRE_APPORTS_EVIDENCE.md` (dossier commissaire).
- `docs/annexes-externes/AE-11_pip-licenses_2026-05-15.md` + `.json` + `README.md`
  (audit licence complet a J-0).
- `legal/THIRD_PARTY_NOTICES.txt` (v2 reformule 15 mai 2026).

Reserves residuelles signalees explicitement :
1. Prenoms operationnels utilises dans `deploy/docker-compose.yml`,
   `docs/GUIDE_DEPLOIEMENT_ENTREPRISE.md` et `tests/test_organization_canonical.py` :
   utilisateurs du deploiement pilote. Sanitization synchronisee planifiable a la demande.
2. Mentions clients (DICA, Tarmac, Centrale Lille / Pr Lafhaj) : strategiques pour
   la defense de la borne haute, conservees apres verification interne NDA.
   [A confirmer par l'apporteur avant envoi.]
3. Audit licence : annexe AE-11 a jour 2026-05-15. 0 GPL/AGPL/SSPL direct.
   5 LGPL et 5 MPL 2.0 disclosed. Cas `espeakng-loader` (loader natif eSpeak NG GPL)
   isolable hors perimetre valorise.

Fourchette de valorisation defendue : 850-1 200 kEUR (cible 850 kEUR equilibre,
modele de prudence COCOMO/IVS 210, decote 13.6% appliquee).

Restant a disposition pour tout questionnement contradictoire.

Cordialement,
[Apporteur]
```

---

## 7. Verdict de la mission micro-verrouillage

| Critere | Verdict |
|---|---|
| Reserve RES-1 | **Traitee partiellement** (SPEC sanitise ; 3 autres fichiers explicitement documentes pour decision apporteur) |
| Reserve RES-2 | **Documentee** (decision strategique formalisee, action requise apporteur sur NDA) |
| Reserve RES-3 | **Traitee complete** (annexe AE-11 livree, THIRD_PARTY_NOTICES v2 reformule) |
| Modification de code applicatif | **0** (perimetre strict respecte) |
| Modification de tests | **0** |
| Modification de licence ou de la fourchette de valorisation | **0** |
| Coherence post-commit | A verifier via re-audit phase 1-4 post-modifications avant push |

**Verdict global de la mission** : **PRET POUR COMMIT LOCAL ET PUSH** apres re-audit phase 1-4 (relecture contradictoire du diff, checklist defauts, re-audit total si Critique/Important corrige, commit avec mention audit).

Cette mission constitue un **enrichissement defensif** du pack Evidence avant transmission externe. Aucune aspering substantielle ne devrait subsister pour un auditeur prudent qui lirait dans l'ordre `12_*.md` -> `13_*.md` -> `AE-11_*.md`.
