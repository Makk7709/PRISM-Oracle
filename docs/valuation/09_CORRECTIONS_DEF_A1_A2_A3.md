<!-- markdownlint-disable MD060 MD032 MD029 MD014 -->

# 09 — Corrections post-audit de controle DEF-A1 / DEF-A2 / DEF-A3

**Projet** : KOREV Evidence
**Apporteur / inventeur** : Amine Mohamed
**Branche** : `valuation/diag-grow-evidence-pack`
**HEAD analyse** : `fab5689a` (5 mai 2026)
**Date des corrections** : 9 mai 2026
**Conformite** : protocole `.cursor/rules/pre-commit-audit.mdc` (phases 1-4)
**Source de declenchement** : `docs/valuation/CONTROLE_AUDIT_PACK_2026-05-09.md` (audit de controle hostile independant)

> Cette note documente les corrections apportees au pack de valorisation suite a l'audit de controle independant. Aucune modification du code applicatif, des licences, ni suppression de fichier legacy n'a ete effectuee. Les fourchettes de valorisation **ne sont pas modifiees**.

---

## 1. Resume des defauts adresses

L'audit de controle independant (`CONTROLE_AUDIT_PACK_2026-05-09.md`, statut initial : **PRET AVEC RESERVES MAITRISEES**) a identifie 9 defauts :

| Severite | Nombre | Action |
|---|---:|---|
| Critique | 0 | n/a |
| Important | 0 | n/a |
| **Modere** | **3** | **Corriges (DEF-A1, DEF-A2, DEF-A3)** |
| Mineur | 4 | Adresses (DEF-A4, DEF-A5, DEF-A6, DEF-A7) |
| Faible | 2 | Notes informatives (DEF-A8, DEF-A9) |

Les 3 defauts moderes (DEF-A1, DEF-A2, DEF-A3) sont tous lies au meme angle mort : la non-integration des **3 commits post-25 avril 2026** dans le pack, alors qu'ils sont ancetres du HEAD `fab5689a` annonce et qu'ils renforcent materiellement la defense.

**Re-audit total selon `pre-commit-audit.mdc`** : non declenche (aucun defaut Critique ou Important).

---

## 2. Commits posterieurs au snapshot du 25 avril 2026

Les 3 commits ci-dessous sont confirmes ancetres de `fab5689a` par `git merge-base --is-ancestor`. Ils sont documentes dans `audit-hostile-valorisation/09-mise-a-jour-post-p0-yenoyikz.md` (addendum auditable du 5 mai 2026, joint au dossier commissaire `docs/DOSSIER_COMMISSAIRE_APPORTS_EVIDENCE.md` section 10).

| Commit | Date | Perimetre | Defense renforcee |
|---|---|---|---|
| `de8b9c7e` | 4 mai 2026 | Fix `file_writer` fail-hard sur `§§include` non resolus + ADR-006 (Tool I/O integrity contract) + 28 tests dedies + post-mortem session yENoyKIZ | Verrouille le pattern fail-silent revele par yENoyKIZ : un PDF de 25 KB avait ete produit avec `Response.message = "✅ File created successfully!"` alors que son contenu utile etait `§§include(/app/tmp/...)` non resolu. Reponse defendable a l'attaque "vos tools peuvent pretendre avoir reussi alors qu'ils ont ecrit un fichier corrompu". |
| `b11b4d99` | 5 mai 2026 | P0 migration RDBMS : Postgres 16 + pgvector gated + ADR-007 (Postgres pgvector adoption) + compose staging + 6 tests d'infra T1-T6 + scripts backup/snapshot + journal P0 | Expose explicitement la dette `filesystem-first` (jusqu'alors implicite) et publie une roadmap structuree en 7 phases sur 4-6 mois (P0 livre runtime, P1-P6 planifiees). P0 = compose staging autonome, init SQL 5 schemas (`identity`, `chats`, `memory`, `audit`, `legal`), aucun service applicatif n'a `depends_on` Postgres (zero-impact prod). Snapshot prod pre-P0 immutable conserve (505 MB, manifeste SHA-256 verifie). |
| `0d0a35da` | 5 mai 2026 | Fix DEF-8 `pg_dump --clean --if-exists` + script `pg_restore_from_dump.sh` fail-loud + test T7 | Verrouille un risque de restore fail-silent introduit par P0 lui-meme, detecte AVANT tout cron actif en prod (cron file livre avec suffixe `.disabled`). Cycle complet `dump → down -v → up → restore` chronometre a 15 secondes (sous le seuil Go/No-Go P0 → P1 de 30 minutes). |

**Total des commits post-25 avril** : 3 commits, 24 fichiers modifies / crees, +3 048 / -42 (net +3 006).

---

## 3. Corrections apportees aux fichiers du pack

### 3.1 `05_CODE_QUALITY_SNAPSHOT.md`

| Section | Modification | Defaut adresse |
|---|---|---|
| Section 1.1 (Tests volume) | Note "post-25 avril" ajoutee : les 3 commits posterieurs ajoutent +35 tests (28 yENoyKIZ + 6 P0 RDBMS T1-T6 + 1 T7). Le HEAD `fab5689a` est attendu a ~3 991 tests (vs 3 956 capture du 28 avril). | DEF-A4 |
| Section 4.2 (Securite — faiblesses) | "Pas de WORM... Roadmap Postgres / pgvector (ADR-007)" → "ADR-007 livre (5 mai 2026) avec P0 RDBMS execute (Postgres + pgvector compose staging actif) ; phases P1-P6 planifiees" | DEF-A1, DEF-A3 |
| Section 6.1 (ADR — etat actuel) | ADR-006 et ADR-007 reformules en "Livre 4 mai 2026 (commit `de8b9c7e`)" et "Livre 5 mai 2026 (commit `b11b4d99`) — P0 execute runtime, P1-P6 planifiees". Description detaillee de chaque ADR ajoutee. | DEF-A1, DEF-A2 |
| Section 11.2 (Audit trail — faiblesses) | "migration non encore executee" → "P0 execute runtime (compose staging actif sur VPS, 5 schemas crees, 7 tests d'infra T1-T6 + T7 verts) ; P1-P6 planifiees sur 4-6 mois" | DEF-A3 |
| **Section 11.3 (NEW)** | Section ajoutee : "Doctrine fail-loud / fail-hard renforcee (4-5 mai 2026)" decrivant les deux extensions de la doctrine fail-loud (Tools applicatifs + Pipeline backup/restore) avec details probatoires et citations Git. | DEF-A2 |
| Section 14.1 (Score global) | Note de transparence ajoutee : "Le doc `audit-hostile-valorisation/09` propose un reajustement interne a ~72/100 ; estime non audite, score canonique 69/100 conserve dans le pack" | DEF-A5 |

### 3.2 `06_KNOWN_LIMITS_AND_REMEDIATION.md`

| Section | Modification | Defaut adresse |
|---|---|---|
| Section 1 (table synthese, ligne 11) | "ADR-007 trace l'orientation Postgres / pgvector" → "ADR-007 livre 5 mai 2026 ; P0 RDBMS execute runtime (init SQL `01_extensions.sql` cree 5 schemas) ; P1-P6 planifiees" | DEF-A3 |
| Section 2.5.1 (Pas de schema de donnees formel) | Reponse defendable detaillee avec mention P0 livre runtime, init SQL 5 schemas, 6 tests T1-T6 + T7, scripts backup, et reference a la source `audit-hostile-valorisation/09`. | DEF-A3 |
| Section 3.4 (Strategique) | "Migration Postgres / pgvector (ADR-007)" → "Migration Postgres / pgvector (ADR-007) — phases P1 a P6 (P0 deja livre 5 mai 2026)" | DEF-A3 |

### 3.3 `04_HOURS_RECONSTRUCTION_REGISTER.md`

| Section | Modification | Defaut adresse |
|---|---|---|
| Section 6 (table par lot, lot 22) | "Migration RDBMS / Postgres / pgvector roadmap" → "Migration RDBMS / Postgres / pgvector (P0 livre, P1-P6 planifiees)". Preuves enrichies : "ADR-007 + commit `b11b4d99` (5 mai 2026), `deploy/docker-compose.staging.yml`, init SQL 5 schemas, 6 tests T1-T6 + test T7, scripts `pg_dump_daily.sh` + `pg_restore_from_dump.sh` fail-loud". **Heures inchangees** (8/12/16 j-h) car le perimetre P1-P6 reste a executer. | DEF-A3 |

### 3.4 `00_REPO_DIAGNOSTIC.md`

| Section | Modification | Defaut adresse |
|---|---|---|
| Section 2.3 (Etat working tree) | "8 livrables d'audit hostile" → "9 livrables d'audit hostile, dont l'addendum `09-mise-a-jour-post-p0-yenoyikz.md`" ; "5 ADR" → "7 ADR (ADR-001 a ADR-007)" | DEF-A1 |
| **Section 2.4 (NEW)** | Section ajoutee : "Commits posterieurs au snapshot du 25 avril 2026 — defenses renforcees" avec table detaillee des 3 commits et phrase de cadrage recommandee pour la note de remise a Diag & Grow. | DEF-A1, DEF-A2, DEF-A3 |
| Section 3.1 (Arborescence) | "5 ADR" → "7 ADR (ADR-001 a ADR-007)" ; "8 livrables" → "9 livrables (dont addendum 09 post-25 avril)" ; ajout du fichier de controle dans `valuation/` | DEF-A1 |

### 3.5 `07_DIAG_GROW_TRANSMISSION_NOTE.md`

| Section | Modification | Defaut adresse |
|---|---|---|
| Section 4.2 (Priorite 2 — Validation technique) | Ajout ligne 14 : `audit-hostile-valorisation/09-mise-a-jour-post-p0-yenoyikz.md` avec mention explicite "Defenses renforcees, fourchettes inchangees" | DEF-A1, DEF-A2, DEF-A3 |
| Section 5 (Fichiers du pack) | Ajout des 3 entrees : `09_CORRECTIONS_DEF_A1_A2_A3.md` (le present fichier), `CONTROLE_AUDIT_PACK_2026-05-09.md` (audit de controle), `PROMPT_CURSOR_CONTROLE.md` (prompt utilise). | Trace |
| Section 9 (Position finale) | Paragraphe ajoute : phrase de cadrage explicite des commits post-25 avril (fourchettes inchangees, defenses renforcees) avec renvoi explicite au doc 09. | DEF-A1, DEF-A2, DEF-A3 |

### 3.6 `08_AUDIT_HOSTILE_VALUATION_PACK.md`

| Section | Modification |
|---|---|
| **Section 9 (NEW)** | Section ajoutee : "Corrections post-audit de controle — DEF-A1 / DEF-A2 / DEF-A3" avec contexte, defauts adresses, effet sur la valorisation (inchangee), statut final propose, conformite `pre-commit-audit.mdc`. |

---

## 4. Elements post-25 avril integres au pack

| Element | Provenance | Lieu d'integration |
|---|---|---|
| ADR-006 — Tool I/O integrity contract | `docs/adr/ADR-006-tool-io-integrity-contract.md` | `05_*.md` § 6.1, 11.3 ; `00_*.md` § 2.4 ; `08_*.md` § 9 |
| ADR-007 — Postgres pgvector adoption | `docs/adr/ADR-007-postgres-pgvector-adoption.md` | `05_*.md` § 4.2, 6.1, 11.2 ; `06_*.md` § 1, 2.5.1, 3.4 ; `04_*.md` lot 22 ; `00_*.md` § 2.4 ; `08_*.md` § 9 |
| Session yENoyKIZ + post-mortem | `audit-hostile-valorisation/09` § 3 | `05_*.md` § 6.1, 11.3 ; `00_*.md` § 2.4 |
| Fail-hard `file_writer` + 28 tests | `python/tools/file_writer.py` + `tests/security/test_file_writer_includes_*.py` | `05_*.md` § 6.1, 11.3 ; `00_*.md` § 2.4 |
| P0 RDBMS execute runtime | `audit-hostile-valorisation/09` § 4 + `docs/migration-rdbms/P0_PRE_REQUIS_INFRA.md` | `05_*.md` § 4.2, 6.1, 11.2 ; `06_*.md` § 1, 2.5.1, 3.4 ; `04_*.md` lot 22 ; `00_*.md` § 2.4 |
| Postgres + pgvector compose staging | `deploy/docker-compose.staging.yml` + `deploy/postgres/init/01_extensions.sql` | `05_*.md` § 6.1, 11.2 ; `06_*.md` § 2.5.1 |
| Backup / restore fail-loud (test T7) | `scripts/backup/pg_dump_daily.sh`, `scripts/backup/pg_restore_from_dump.sh`, `tests/infra/test_dump_restore_pipeline.py` | `05_*.md` § 11.3 ; `00_*.md` § 2.4 ; `04_*.md` lot 22 |
| Test T7 + 6 tests d'infra T1-T6 | `tests/infra/test_postgres_compose.py` + `tests/infra/test_dump_restore_pipeline.py` | `05_*.md` § 1.1, 11.3 ; `06_*.md` § 2.5.1 |
| 2 incidents runtime documentes | `audit-hostile-valorisation/09` § 6 | Mentionnes en `09_*.md` § 2 (le present document, table commits) |
| Score 72/100 estime interne | `audit-hostile-valorisation/09` § 8 | Note de transparence dans `05_*.md` § 14.1, **non integre comme score canonique** |
| Doctrine pre-commit-audit comme actif | `audit-hostile-valorisation/09` § 7 | Mentionne dans `00_*.md` § 2.4 ; **non integre aux heures du `04_*.md`** pour ne pas augmenter artificiellement les fourchettes |

---

## 5. Decision DEF-A7 — `deploy/users.json.example`

### 5.1 Constat

Le fichier `deploy/users.json.example` (modifie au statut Git au moment de l'audit) contient :

- **12 prenoms reels** : `amine`, `nicolas`, `luc`, `jeremie`, `coralie`, `dominique`, `laurianne`, `sarah`, `christopher`, `louis`, `mathias`, `benj`
- **2 profils descriptifs** : `Administrateur — Direction` (amine), `Analyste — Niveau 2` (nicolas)
- **1 organisation client explicite** : `Epoque` (rattachee a `benj` avec role `OWNER` et profil `Benjamin — Epoque`)
- **Hashes Argon2id** : tous explicitement `$argon2id$v=19$m=65536,t=3,p=4$REMPLACEZ_PAR_HASH_REEL` (placeholders sans valeur cryptographique reelle)

### 5.2 Analyse de risque

| Element | Risque | Severite |
|---|---|---|
| Hashes Argon2id placeholders | **Aucun** : `REMPLACEZ_PAR_HASH_REEL` n'est pas un hash valide ; aucune authentification possible avec ce fichier en l'etat | Nul |
| Prenoms reels (12 occurrences) | Expose la **structure de l'equipe interne KOREV** a un evaluateur externe. Pas de noms complets ; pas de coordonnees ; pas de mots de passe. | Faible (PII partielle) |
| Mention organisation client `Epoque` + role `OWNER` + profil `Benjamin — Epoque` | Expose un **client identifie nominativement** (raison sociale et utilisateur). Si l'organisation Epoque n'a pas autorise cette divulgation a un tiers (Diag & Grow / commissaire), risque de manquement contractuel ou RGPD. | Modere |

### 5.3 Decision documentee

**Decision validee par l'apporteur le 9 mai 2026** : **OPTION C — branche dediee de transmission `diag-grow/transmission-evidence`** avec sanitization complete de `deploy/users.json.example`.

**Justification** :

1. Le fichier est un **modele de configuration** destine au deploiement reel. La version actuelle (avec 12 prenoms reels d'utilisateurs internes + organisation client `Epoque`) est **preservee** sur la branche `valuation/diag-grow-evidence-pack` (et indirectement sur `main`).
2. Les hashes Argon2id etaient deja des placeholders ; **aucun risque cryptographique**.
3. Le risque de PII partielle (12 prenoms internes : `amine`, `nicolas`, `luc`, `jeremie`, `coralie`, `dominique`, `laurianne`, `sarah`, `christopher`, `louis`, `mathias`, `benj`) et de divulgation client (`Epoque` avec role `OWNER`) **est elimine** sur la branche de transmission.

**Options envisagees** (tracees pour audit) :

| Option | Description | Decision |
|---|---|---|
| A | Transmettre le depot tel quel (incluant 12 prenoms + client Epoque) | Rejetee (risque PII / divulgation client non maitrise) |
| B | Creer un fichier d'exemple sanitize separe (`deploy/users.json.example.sanitized`) | Rejetee (demande une discipline de lecture cote Diag & Grow) |
| **C** | **Branche dediee de transmission avec sanitization complete** | **RETENUE** |
| D | Obtenir une autorisation ecrite d'Epoque + consentement employes | Rejetee (effort hors delai, decision strategique de transmission) |

**Execution de l'option C** (branche `diag-grow/transmission-evidence`, HEAD `fab5689a` au depart) :

| Avant sanitization (preserve sur `valuation/diag-grow-evidence-pack`) | Apres sanitization (sur `diag-grow/transmission-evidence`) |
|---|---|
| 12 prenoms reels (`amine`, `nicolas`, `luc`, `jeremie`, `coralie`, `dominique`, `laurianne`, `sarah`, `christopher`, `louis`, `mathias`, `benj`) | 3 utilisateurs fictifs (`admin_example`, `user_example_1`, `user_example_2`) |
| Profils descriptifs internes ("Administrateur — Direction", "Analyste — Niveau 2", "Benjamin — Epoque") | Profils generiques ("Example administrator profile (fictitious, documentation only)") |
| Organisation client `Epoque` avec role `OWNER` | Organisation fictive `ExampleOrg` |
| Pas de champs `email` | Emails `@example.com` (RFC 2606 reserved domain) |
| Hashes `REMPLACEZ_PAR_HASH_REEL` | Hashes `PLACEHOLDER_NOT_A_REAL_HASH_REGENERATE_BEFORE_USE` |
| Pas de meta-fields | 3 meta-fields ajoutes : `_comment`, `_format_version`, `_warning` (avertissement explicite "DO NOT COPY ... NOT a valid Argon2id output ... Generate real hashes via scripts/provision_user.py before deployment") |

Le fichier sanitize est **JSON valide** (verifie par `python3 -m json.tool`).

La version originale du fichier reste intacte sur la branche `valuation/diag-grow-evidence-pack`. Si la branche de transmission `diag-grow/transmission-evidence` est mergee dans `main` apres transmission, l'apporteur devra decider :

- soit de **garder la version sanitizee** (recommande pour la securite long terme) ;
- soit de **revenir a la version interne** (preservation operationnelle pour l'equipe technique).

---

## 6. Effet sur le statut du pack et la valorisation

### 6.1 Statut du pack

| Etape | Statut |
|---|---|
| Avant audit de controle | PRET AVEC RESERVES |
| Apres audit de controle (initial) | PRET AVEC RESERVES MAITRISEES |
| Apres corrections DEF-A1/A2/A3 | PRET (sous reserve decision DEF-A7 + anti-secrets J-0) |
| **Apres execution option C (branche `diag-grow/transmission-evidence`) + anti-secrets J-0** | **PRET POUR TRANSMISSION** (sous reserve de validation humaine finale avant push / partage d'acces) |

### 6.2 Fourchettes de valorisation

**Inchangees**. Les 3 commits posterieurs au 25 avril 2026 ne modifient pas les fourchettes :

| Scenario | Fourchette (inchangee) | Effet des commits post-25 avril |
|---|---|---|
| Conservateur | 662 000 EUR a 850 000 EUR | Aucun |
| Defendable equilibre (recommande) | **958 000 EUR a 1 054 000 EUR** | Borne haute **mieux defendue** (yENoyKIZ verrouille + ADR-007 publie) |
| Offensif maitrise (avec annexes) | 1 150 000 EUR a 1 350 000 EUR | Inchangee, conditionnee aux annexes AE-1 a AE-9 |

### 6.3 Risque de decote

| Etape | Risque de decote |
|---|---|
| Avant corrections | MOYEN-FAIBLE |
| Apres corrections | **FAIBLE** (consolidation par commits techniques verifiables et ADR structurants) |

---

## 7. Recommandation de transmission

### 7.1 Phrase de transmission proposee a Diag & Grow

> *"Veuillez trouver ci-joint l'acces au depot KOREV-Oracle / Evidence sur la branche `valuation/diag-grow-evidence-pack`, HEAD `fab5689a`. Le pack de valorisation est dans `docs/valuation/` (10 documents). La fourchette retenue est de 958 000 EUR a 1 054 000 EUR (mediane ~1 006 000 EUR), fondee sur la methode de cout de reproduction (norme IVS 210), avec coefficient qualite 0.95 (score 69/100) et decote technique residuelle 12-20%. Les commits posterieurs au snapshot du 25 avril 2026 (`de8b9c7e`, `b11b4d99`, `0d0a35da`) ne modifient pas les fourchettes ; ils sont documentes dans `audit-hostile-valorisation/09-mise-a-jour-post-p0-yenoyikz.md`. Les annexes externes AE-1 a AE-9 (factures DICA FRANCE, pieces R&D pre-repo, dossier 4 brevets PRISM, chaine de droits PRISM → Evidence, pilotes terrain) sont disponibles sur demande pour une revue du scenario offensif maitrise (1 150 000 EUR a 1 350 000 EUR)."*

### 7.2 Checklist finale avant transmission

| # | Action | Responsable | Statut |
|---|---|---|---|
| 1 | Valider la decision DEF-A7 (option A / B / C / D pour `deploy/users.json.example`) | Apporteur Amine Mohamed | A faire |
| 2 | Re-executer la verification anti-secrets a J-0 (commandes section 4.1 du `08_*.md`) | Apporteur | A faire |
| 3 | Re-executer `pytest --collect-only -q tests/` sur HEAD `fab5689a` pour confirmer le compte de tests reel (~3 991 attendu) | Apporteur (optionnel) | A faire |
| 4 | Mettre a jour `docs/preuves-execution/A11_pytest_collect_only.txt` avec le nouveau compte si re-execution | Apporteur (optionnel) | A faire |
| 5 | Decider si les annexes AE-1 a AE-9 sont jointes (ouvre le scenario offensif) ou reservees (scenario equilibre) | Apporteur | A faire |
| 6 | Generer un token GitHub de lecture seule (PAT `read:repo`) ou accorder un acces collaborateur read-only au depot prive | Apporteur | A faire |
| 7 | Transmettre la note de remise (cf. `07_DIAG_GROW_TRANSMISSION_NOTE.md`) avec le lien d'acces au depot | Apporteur | A faire |
| 8 | Si annexes externes envoyees : utiliser un canal securise (AR-USPS, drive partage avec controle d'acces, ou WeTransfer avec mot de passe) | Apporteur | Si applicable |
| 9 | Conserver une trace ecrite des elements transmis (date, fichiers, destinataire, canal) | Apporteur | A faire |

---

## 8. Conformite `pre-commit-audit.mdc`

### 8.1 Phase 1 — Relecture contradictoire du diff cumule

Effectuee le 9 mai 2026 sur l'integralite des fichiers modifies du pack :

- `00_REPO_DIAGNOSTIC.md` : section 2.3 (working tree), section 2.4 (NEW), section 3.1 (arborescence)
- `04_HOURS_RECONSTRUCTION_REGISTER.md` : lot 22
- `05_CODE_QUALITY_SNAPSHOT.md` : sections 1.1, 4.2, 6.1, 11.2, 11.3 (NEW), 14.1
- `06_KNOWN_LIMITS_AND_REMEDIATION.md` : sections 1, 2.5.1, 3.4
- `07_DIAG_GROW_TRANSMISSION_NOTE.md` : sections 4.2, 5, 9
- `08_AUDIT_HOSTILE_VALUATION_PACK.md` : section 9 (NEW)
- `09_CORRECTIONS_DEF_A1_A2_A3.md` : present document (NEW)

Verifications croisees :
- Tous les commits cites (`de8b9c7e`, `b11b4d99`, `0d0a35da`) sont confirmes ancetres de `fab5689a` par `git merge-base --is-ancestor`.
- Toutes les references aux ADR (ADR-006, ADR-007) sont confirmees presentes dans `docs/adr/`.
- Tous les renvois a `audit-hostile-valorisation/09-mise-a-jour-post-p0-yenoyikz.md` sont valides (fichier existe, sections referencees presentes).
- Les fourchettes 662-850 / 958-1 054 / 1 150-1 350 KEUR sont **identiques** dans tous les fichiers modifies (pas de divergence introduite).
- Le coefficient qualite 0.95, le TJM 650 EUR cible, la decote 12-20% sont **inchanges**.
- Le score 69/100 reste la valeur canonique (le 72/100 est explicitement marque "estime interne, non audite").

### 8.2 Phase 2 — Checklist de defauts

| Defaut introduit | Severite | Statut |
|---|---|---|
| Aucun defaut introduit | n/a | n/a |

Verifications effectuees :
- Aucune nouvelle contradiction de chiffres (verifie par grep sur les valeurs-cles).
- Aucune nouvelle incoherence de fourchettes.
- Agent Zero reste **explicitement exclu** de la valorisation comme actif proprietaire.
- Aucun double comptage introduit (les commits post-25 avril ne sont pas integres aux heures du `04_*.md`).
- Aucune affirmation non prouvee introduite (toutes les nouvelles mentions sont sourcees a des fichiers existants verifiables).
- Aucune modification applicative (zero changement dans `python/`, `tests/`, `deploy/`, `scripts/` au titre du present pack).

### 8.3 Phase 3 — Re-audit total

**Non requis** (aucun defaut Critique ou Important detecte ni introduit).

### 8.4 Phase 4 — Trace pour commit

Si l'apporteur decide de commiter ces corrections, le message recommande est :

```text
docs(valuation): correction DEF-A1/A2/A3 — integration commits post-25 avril

Suite audit de controle independant (CONTROLE_AUDIT_PACK_2026-05-09.md),
correction des 3 defauts moderes lies aux 3 commits post-25 avril 2026
(de8b9c7e yENoyKIZ + ADR-006, b11b4d99 P0 RDBMS execute + ADR-007,
0d0a35da fix DEF-8) deja ancetres de fab5689a mais sous-utilises dans le pack.

Fichiers modifies : 00_REPO_DIAGNOSTIC.md, 04_HOURS_RECONSTRUCTION_REGISTER.md,
05_CODE_QUALITY_SNAPSHOT.md, 06_KNOWN_LIMITS_AND_REMEDIATION.md,
07_DIAG_GROW_TRANSMISSION_NOTE.md, 08_AUDIT_HOSTILE_VALUATION_PACK.md.
Fichier cree : 09_CORRECTIONS_DEF_A1_A2_A3.md.

Decision DEF-A7 (deploy/users.json.example) documentee, non executee.
Aucune modification applicative. Aucune modification de licence.
Fourchettes de valorisation INCHANGEES (958-1 054 KEUR equilibre).

Audit hostile post-correction : 0 defaut Critique, 0 defaut Important
introduits ou residuels. Re-audit total non declenche.

Statut final : PRET pour transmission Diag & Grow apres validation
explicite apporteur (decision DEF-A7 + verification anti-secrets J-0).
```

---

## 9. Conclusion

Les 3 defauts moderes (DEF-A1, DEF-A2, DEF-A3) detectes par l'audit de controle independant sont **integralement corriges** par les modifications detaillees en section 3. Les 4 defauts mineurs sont **adresses** par des notes de transparence ou des decisions documentees. Les 2 defauts faibles sont **informatifs** (pas de correction requise du pack).

La position de valorisation est **renforcee dans la defense** sans modification des fourchettes. Le pack est **PRET** pour transmission a Diag & Grow et / ou au commissaire aux apports, sous reserve :

1. de la validation explicite par l'apporteur de la decision DEF-A7 (`deploy/users.json.example`) ;
2. de la re-execution de la verification anti-secrets a J-0 (commandes du `08_*.md` section 4.1) ;
3. de la decision sur la fourniture (ou non) des annexes externes AE-1 a AE-9.

**Aucune modification applicative n'a ete effectuee.**
**Aucune modification de licence n'a ete effectuee.**
**Aucun fichier legacy n'a ete supprime.**
**Aucun commit ni push n'a ete realise par le present pack.**

---

## 10. Addendum verrouillage final pre-push (10 mai 2026)

Une mission complementaire de verrouillage final a ete executee le 10 mai 2026 sur la branche `diag-grow/transmission-evidence` (HEAD parent `aad0c102`). Elle adresse les recommandations restantes de la section 6 (DEF-A7 option C) et du checklist `10_*.md` §7.4 / §3.5 (hashes Argon2id complets sur fichiers heritages, fichiers untracked sensibles).

### 10.1 Fichiers untracked sensibles deplaces hors Git (DEF-CRITIQUE-1 verrouille)

Les 3 fichiers untracked detectes en Phase 1 d'audit hostile pre-commit (cf. `10_*.md` §3.5) ont ete physiquement deplaces hors du working tree git :

| Fichier source | Destination (hors Git) |
|---|---|
| `scripts/add_beatrice_user.py` | `~/KOREV_PRIVATE_NON_GIT/evidence-sensitive-excluded-2026-05-09/scripts/` |
| `scripts/add_epoque_user.py` | `~/KOREV_PRIVATE_NON_GIT/evidence-sensitive-excluded-2026-05-09/scripts/` |
| `docs/preuves-execution/check_server_activity.sh` | `~/KOREV_PRIVATE_NON_GIT/evidence-sensitive-excluded-2026-05-09/docs/preuves-execution/` |

Un `README.md` de provenance traceable est cree dans le coffre. La verification `git status --short` ne mentionne plus aucun de ces fichiers en untracked. Tout risque de fuite par `git add .` ulterieur est elimine.

### 10.2 Fichiers trackes herites de main : sanitization complete (artefacts auth)

Le checklist `10_*.md` §7.4 signalait deux fichiers herites de `main` contenant des hashes Argon2id complets reels (hors perimetre transmission DEF-A7 a la date du 9 mai). Pour le verrouillage avant push externe, **ces deux fichiers sont desormais sanitises sur la branche `diag-grow/transmission-evidence`** :

| Fichier | Avant sanitization | Apres sanitization |
|---|---|---|
| `deploy/users.demo.json` | 2 hashes Argon2id complets reels (`$argon2id$v=19$m=65536,...$<salt>$<hash>`) | 2 hashes places `$argon2id$PLACEHOLDER_NOT_A_VALID_HASH` + champ top-level `_warning` (ignore par le loader `user_manager.py` qui ne lit que `data.get("users")`) |
| `scripts/add_tarmac_user.py` | Hash Argon2id complet reel + organisation `TARMAC` + username `tarmac` + profile `TARMAC — Utilisateur` + constante `TARMAC_USER` | Hash placeholder + organisation `ExampleOrg` + username `demo_user` + profile `Demo User — Example` + constante `DEMO_USER` + docstring explicit avec note historique |

JSON valide pour `users.demo.json` (verifie `python3 -m json.tool`). Syntaxe Python valide pour `add_tarmac_user.py` (verifie `ast.parse`). Le nom du fichier `add_tarmac_user.py` est preserve (le contenu sanitise est explicite quant au caractere historique du nom ; aucun rename pour rester aligne avec la contrainte "ne pas supprimer de fichiers legacy trackes sans justification explicite").

**Impact operationnel** : si quelqu'un tente d'utiliser `users.demo.json` ou `add_tarmac_user.py` post-push pour deployer un service de demo reel, l'authentification echouera (hash invalide). C'est **le comportement attendu** : ces fichiers sont desormais transparents quant a leur statut "demo non-fonctionnel par defaut, regenerer avec `scripts/hash_password.py` avant tout deploiement".

### 10.3 Fichier `deploy/users.json.example` (DEF-A7 option C)

Re-verifie en Phase 4 : conforme. Aucune correction requise. JSON valide, 0 PII, 0 organisation reelle, hashes placeholders explicites, emails `@example.com`, 3 meta-fields d'avertissement.

### 10.4 Effet sur la valorisation

**INCHANGE.** Aucune fourchette n'est modifiee. La sanitization des artefacts d'authentification est une mesure de securite avant transmission externe, sans impact sur les heures de reconstruction, les TJM, les coefficients qualite ou les decotes. Le pack defend la meme valeur ; il elimine simplement un risque residuel signale dans `10_*.md` §7.4.

### 10.5 Statut consolide post-verrouillage

| Item | Statut |
|---|---|
| DEF-A1 / DEF-A2 / DEF-A3 | CORRIGES (cf. section 3) |
| DEF-A4 / DEF-A5 / DEF-A6 | DOCUMENTES (cf. section 4) |
| DEF-A7 option C | EXECUTEE le 9 mai 2026 (sanitization `deploy/users.json.example`) |
| DEF-CRITIQUE-1 (3 fichiers untracked sensibles) | DEPLACES hors Git le 10 mai 2026 |
| Hashes Argon2id reels herites (`users.demo.json`, `add_tarmac_user.py`) | SANITISES le 10 mai 2026 |
| Anti-secrets J-0 final | RELANCE en Phase 6 (cf. `10_*.md`) |
| Fourchettes valorisation | INCHANGEES |
| Code applicatif | INCHANGE |
| Licences | INCHANGEES |

---

*Note de correction etablie le 9 mai 2026 sur la branche `valuation/diag-grow-evidence-pack`, HEAD `fab5689a`. Conforme au protocole `pre-commit-audit.mdc` (phases 1-4). Les decisions de transmission externe (commit, push, envoi a Diag & Grow) restent a la main exclusive de l'apporteur Amine Mohamed.*
