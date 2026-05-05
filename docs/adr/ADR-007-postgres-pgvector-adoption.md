# ADR-007 — Adoption de Postgres + pgvector pour la persistance metier

**Date :** 5 mai 2026
**Statut :** Accepte (phase P0 amorcee, P1+ a venir)
**Auteur :** Amine Mohamed
**Lien :** P0 de la migration RDBMS — cf. `docs/migration-rdbms/`

## Contexte

L'audit du serveur de production OVH (5 mai 2026) a confirme que la persistance
metier de KOREV Evidence repose aujourd'hui sur un schema *filesystem-first* :

| Donnee metier                        | Stockage actuel                                      |
|--------------------------------------|------------------------------------------------------|
| Comptes utilisateurs / orgs          | `deploy/users.json` (fichier mont\u00e9 read-only)         |
| Sessions de chat (`ctxid`)           | `tmp/chats/{ctxid}/chat.json` + `messages/*.txt`     |
| Memoire vectorielle (par user)       | `memory/users/<user>/default/index.faiss`            |
| Index legal (FTS)                    | `data/legal/index/legal_index.sqlite` (66 MB)        |
| Artefacts generes (PDF, MD, ...)      | `shared/users/<user>/generated/`                     |
| Rapports d'audit signes              | `audit/<...>/audit_report.md` + `replay_snapshot.json` |
| Uploads utilisateurs                  | `tmp/uploads/<user>/`                                |

Cette architecture a tenu jusqu'a la phase actuelle mais expose plusieurs dettes
techniques lourdes :

1. **Pas de transactionnalite multi-fichier.** Si une mise a jour metier doit
   modifier `users.json` puis ecrire un fichier d'audit, et que le processus
   crash entre les deux, l'etat sur disque est incoherent.
2. **Pas de requete relationnelle.** Pour repondre a "lister tous les chats du
   compte X cree dans les 30 derniers jours", il faut iterer sur le filesystem.
   Acceptable pour 7 utilisateurs, ingerable a 100+.
3. **Pas de RBAC granulaire au niveau donnee.** L'isolation actuelle est
   physique (un fichier par user), ce qui empeche les analyses transverses
   gouverneur-de-donnees (organisation > departement > membre).
4. **Sauvegarde non triviale.** La sauvegarde actuelle est un tar de volume
   Docker. Aucun PITR, aucune politique de retention selective.
5. **Aucun mecanisme natif de verrouillage concurrent.** Deux requetes paralleles
   sur le meme `users.json` peuvent provoquer un *lost update* si le processus
   d'ecriture n'est pas atomique (et il n'a aucune raison de l'etre puisque
   `users.json` est aussi versionne dans le repo).

L'incident `yENoyKIZ` (cf. `ADR-006`) a egalement revele que le suivi des
artefacts produits par les tools souffre d'un cloisonnement faible : les
fichiers atterrissent dans `tmp/` ou `shared/` selon des conventions
implicites. Une couche relationnelle permettrait de tracer chaque artefact
(`(user_id, ctxid, tool, sha256, created_at)`) sans dependre du chemin
filesystem qui peut bouger.

## Decision

KOREV Evidence adopte **PostgreSQL 16 + extension pgvector** comme socle de
persistance metier. L'adoption se fait en 7 phases (P0 a P6) sur 4 a 6 mois,
sans interruption de service ni perte de donnee. Le filesystem reste utilise
pour les blobs volumineux (PDF, uploads, modeles ML), mais les metadonnees
associees migrent en base.

### Phase P0 — Pre-requis infra (objet du present ADR)

P0 pose les fondations sans aucun impact sur la prod :

1. **Snapshot pre-migration** de la prod (volumes Docker + `users.json`
   + git HEAD), conserve en `/home/ubuntu/snapshots/pre-P0-*` avec manifeste
   SHA-256 (`scripts/backup/snapshot_pre_migration.sh`).
2. **Service `evidence-postgres`** ajoute a `deploy/docker-compose.yml`
   derriere le profil `db`. Ce profil n'est PAS active par defaut : un
   `docker compose up -d` en prod NE demarre PAS Postgres.
3. **Compose staging autonome** `deploy/docker-compose.staging.yml` qui peut
   tourner en parallele de la prod (containers nommes `-staging`, volumes et
   reseau separes, ports differents) ou en local sur poste developpeur.
4. **Init scripts** `deploy/postgres/init/01_extensions.sql` :
   - extensions : `pgcrypto`, `vector`, `pg_trgm`
   - schemas applicatifs : `identity`, `chats`, `memory`, `audit`, `legal`
   - aucune table metier (P1+)
5. **Backup quotidien** `scripts/backup/pg_dump_daily.sh` pret a etre
   cron-ne sur le VPS prod a partir de l'activation P1.
6. **Tests d'infra** `tests/infra/test_postgres_compose.py` (marker `infra`,
   skipped par defaut, lancable manuellement ou en CI dediee). Couvrent :
   reachability, pgvector charge, schemas crees, marker d'init pose, aucune
   table metier en P0.

### Phases P1 a P6 (planifiees, non encore commitees)

| Phase | Objet                                            | Duree estim. |
|-------|--------------------------------------------------|--------------|
| P1    | Couche Repository (`UserRepository`) + dual-write `users.json` ↔ Postgres | 3-4 sem |
| P2    | Migration sessions de chat (`ChatRepository`)    | 4-5 sem      |
| P3    | Migration memoire vectorielle FAISS → pgvector   | 3-4 sem      |
| P4    | Indexation des artefacts d'audit (metadonnees)   | 2 sem        |
| P5    | Migration `legal_index.sqlite` → schema `legal`  | 2 sem        |
| P6    | Decommissioning des fichiers source de verite    | 1-2 sem      |

Chaque phase respecte le pattern :
**(a) Repository feature-flag → (b) dual-write → (c) backfill → (d) dual-read
verification → (e) cutover read primary DB → (f) cutover write primary DB →
(g) decommissioning**.

Aucune phase ne supprime un fichier source de verite avant que le test de
non-regression sur staging ait montre 7 jours de stabilite.

## Garanties contractuelles de la decision

1. **Aucune perte de donnee.** Tant qu'une phase n'est pas finalisee (g), le
   filesystem reste source de verite. Le rollback consiste a desactiver le
   feature flag et continuer a lire/ecrire le filesystem.
2. **Aucune invalidation des signatures d'audit existantes.** L'audit
   `H-4` (5 mai 2026) confirme que `replay_engine.compute_integrity()` et
   `integrity_block._build_sign_payload()` ne signent **que** des contenus
   (hashes SHA-256 de query/response/document), jamais des chemins
   filesystem. Migrer le stockage des `replay_snapshot.json` ne casse donc
   pas les signatures HMAC/RSA-PSS deja emises.
3. **Reversibilite a chaque phase.** Chaque PR introduisant une phase doit
   livrer un script de rollback teste sur staging.
4. **Isolation prod / staging stricte.**
   - Reseau Docker : `evidence-network` (prod) vs `evidence-staging-network`
   - Volumes : `evidence-postgres-data` (prod) vs `evidence-postgres-data-staging`
   - Mots de passe : `POSTGRES_PASSWORD` ≠ `POSTGRES_STAGING_PASSWORD`
   - Aucun montage des cles RSA de prod en staging
5. **Pas d'exposition publique du SGBD.** Postgres n'est jamais bind sur
   `0.0.0.0`. En prod : non expose. En staging : `127.0.0.1:5433` uniquement.
6. **Backup verifiable.** Chaque dump est accompagne d'un SHA-256 dans
   `MANIFEST.sha256`, et le script `pg_dump_daily.sh` execute `gunzip --test`
   apres chaque dump.

## Decisions par defaut documentees (H-1)

L'audit hostile du plan de migration avait laisse 3 questions strategiques
ouvertes. Les choix retenus en P0, justifies, sont :

| Question (H-1)              | Choix retenu                                         | Justification                                                  |
|-----------------------------|------------------------------------------------------|----------------------------------------------------------------|
| Postgres managé ou self-hosted ? | **Self-hosted via image upstream `pgvector/pgvector:pg16` (Postgres 16 officiel + extension pgvector pre-installee par l'equipe pgvector)** | Cout 0 €, controle total, deja experimente avec Docker. Migration vers managed (OVH Cloud Database) reste possible en P3+ via `pg_dump`. |
| Ou heberger le staging ?    | **VPS OVH actuel, en parallele de la prod**          | Cout 0 €, latence reseau identique a la prod (test realiste), budget projet 0 € en P0. |
| Cadence de migration ?      | **Sereine (4-6 mois)**                                | 7 utilisateurs en prod, pas d'urgence business. Une cadence plus lente reduit le risque d'erreur. |

Ces choix sont reversibles : passer a un Postgres managed se fait par un
`pg_dump` -> `pg_restore`. Bouger le staging vers un VPS dedie se fait en
recreant le compose sur un autre host.

## Critere de transition P0 → P1

P0 est valide quand TOUS les criteres suivants sont remplis :

1. Snapshot pre-P0 existant et integre (manifeste SHA-256 verifiable).
2. `docker compose -f deploy/docker-compose.staging.yml up -d` demarre Postgres
   staging healthy en moins de 30 secondes.
3. Les 6 tests d'infra `tests/infra/test_postgres_compose.py` passent
   (T1 a T6).
4. Le script `scripts/backup/pg_dump_daily.sh` execute un dump complet d'une
   base vide en moins de 5 secondes, et `gunzip --test` valide.
5. La prod tourne toujours sur le commit `de8b9c7e` (fix `yENoyKIZ`) avec ses
   4 containers healthy.
6. Aucune dependance applicative (`depends_on`) ne reference le service
   `evidence-postgres` dans le compose principal.

Si l'un de ces criteres n'est pas rempli, P1 ne demarre pas. Le passage a P1
exige par ailleurs la mise en place :
- d'un dump/restore de production teste (point H-1 de l'audit hostile)
- d'un job CI dedie qui exectue `pytest -m infra` sur Postgres staging

## Ce que P0 ne fait PAS (a verifier avant tout commit)

- P0 ne modifie aucun fichier dans `python/`. Le code applicatif est
  strictement non touche en P0.
- P0 ne modifie pas `Dockerfile.backend`. Aucune nouvelle dependance Python.
- P0 ne supprime aucun fichier de prod. Tout est additif.
- P0 n'expose pas Postgres sur le reseau public.
- P0 n'introduit aucune dependance Python ajoutee a `requirements.txt`.

## Consequences

**Positives :**

- Possibilite, des P1, de remplacer `deploy/users.json` (10 lignes editees a
  la main) par une vraie table `identity.users` avec migrations gitees.
- pgvector remplace a terme FAISS pour la memoire agent : un vrai backup
  multi-utilisateur, des requetes hybrides (vector + filtre relationnel),
  et la possibilite de faire de l'analytique transverse.
- Les artefacts d'audit gagnent une tracabilite relationnelle qui completera
  le replay_snapshot existant : `(user_id, ctxid, artefact_path, sha256,
  signed_at)` indexable et requetable.
- Dette technique adressee de maniere progressive et reversible.

**Negatives :**

- Surcoût RAM ~1 GB par instance Postgres (negligeable sur le VPS actuel
  8 GB). Le compose staging consomme 1 GB de plus, soit 2 GB total.
- Operations DB-aware a integrer au runbook (cron pg_dump, surveillance disque,
  PITR a configurer en P2).
- Dependance forte au socle pgvector. Si l'image officielle disparait, il
  faudrait reconstruire (peu probable, c'est l'image de reference).
- Les tests d'infra exigent Docker disponible, ce qui les rend difficiles a
  executer dans la CI standard. Decision : un job CI dedie installe Docker
  sur le runner et execute `pytest -m infra`.

## Alternatives rejetees

- **Continuer sur SQLite.** Limite a 1 ecrivain a la fois (locks), pas de
  pgvector natif (extension `sqlite-vss` immature), pas de RBAC. Reserve aux
  donnees auxiliaires comme `legal_index.sqlite`.
- **MongoDB.** Pas de transactionnalite forte multi-document jusqu'a recemment,
  pas adapte aux donnees fortement relationnelles (memberships, roles).
- **Supabase / Firestore (managed).** Couplage cloud, latence variable, prix
  non lineaire avec la croissance. Possible plus tard pour une instance
  dediee aux gros clients.

## Liens

- ADR-006 : Tool I/O Integrity Contract (`docs/adr/ADR-006-tool-io-integrity-contract.md`)
- Plan de migration RDBMS : `docs/migration-rdbms/` (a publier en P1)
- Snapshot pre-P0 : sur le VPS OVH `/home/ubuntu/snapshots/pre-P0-20260505-143731/`
- Compose staging : `deploy/docker-compose.staging.yml`
- Tests d'infra : `tests/infra/test_postgres_compose.py`
