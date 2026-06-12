# P0 — Pre-requis infra (Migration RDBMS)

**Date d'execution :** 5 mai 2026
**Reference :** ADR-007
**Pre-conditions :** ADR-006 deploye en prod (commit `de8b9c7e`), 4 containers
prod healthy.

## Objectif

Poser les fondations infrastructurelles de la migration vers PostgreSQL +
pgvector, sans aucun impact sur la prod.

## Hostile audit — defauts critiques pre-P0 leves

| ID  | Severite | Description                                                                 | Statut |
|-----|----------|-----------------------------------------------------------------------------|--------|
| H-1 | Critique | Decision manquante : Postgres managed/self-hosted, staging cloud/local, cadence | **Resolu** : choix par defaut documentes dans ADR-007 (self-hosted, staging sur VPS OVH, cadence sereine 4-6 mois) |
| H-4 | Critique | Verifier que les signatures audit (`replay_engine`, `integrity_block`) ne dependent pas du chemin filesystem | **Resolu** : audit du 5 mai 2026 confirme. Aucun chemin dans les payloads HMAC/RSA-PSS. |

## Realisations P0

### 1. Snapshot pre-P0 (immutable)

**Localisation :** VPS OVH `/home/ubuntu/snapshots/pre-P0-20260505-143731/`
**Git HEAD prod :** `de8b9c7e` (fix `yENoyKIZ`)
**Containers :** 4 healthy (evidence-backend, evidence-backend-demo,
evidence-samba, evidence-caddy)
**Volumes archives (tar.gz) :**

| Volume          | Taille brute | Backup |
|-----------------|--------------|--------|
| evidence-tmp    | 693.6 MB     | OK     |
| evidence-shared | 86.9 MB      | OK     |
| evidence-memory | 86.8 MB      | OK     |
| evidence-data   | 65.5 MB      | OK     |
| evidence-audit  | 4.0 KB       | OK     |
| evidence-logs   | 138.1 MB     | OK (meta only) |

Manifeste SHA-256 : `MANIFEST.sha256` dans le dossier de snapshot. Script
reproductible : `scripts/backup/snapshot_pre_migration.sh`.

### 2. Postgres ajoute au compose principal (gate `profiles: db`)

Fichier : `deploy/docker-compose.yml`

Le service `evidence-postgres` est defini avec :

- image `pgvector/pgvector:pg16`
- volume `evidence-postgres-data`
- healthcheck `pg_isready` (15s interval)
- ressources : 2 CPU, 2 GB RAM par defaut
- **`profiles: ["db"]` — NE DEMARRE PAS avec `docker compose up -d`**

Aucun autre service n'a `depends_on: evidence-postgres`. Garantit que la prod
ne percoit aucun changement quand le compose est applique.

### 3. Compose staging autonome

Fichier : `deploy/docker-compose.staging.yml`

- Reseau separe `evidence-staging-network`
- Volume separe `evidence-postgres-data-staging`
- Mot de passe distinct (`POSTGRES_STAGING_PASSWORD`)
- Bind localhost uniquement (`127.0.0.1:5433`)
- Ressources reduites (1 CPU, 1 GB RAM)

### 4. Init scripts SQL

Fichier : `deploy/postgres/init/01_extensions.sql`

- Extensions : `pgcrypto`, `vector`, `pg_trgm`
- Schemas : `identity`, `chats`, `memory`, `audit`, `legal`
- Marker `public.korev_init_marker` (phase, extensions, schemas)
- **Aucune table metier en P0**

### 5. Backup quotidien + restore

Fichiers :

- `scripts/backup/pg_dump_daily.sh` : dump quotidien
- `scripts/backup/pg_restore_from_dump.sh` : restore depuis dump

Caracteristiques :

- `pg_dump --clean --if-exists --no-owner --no-acl --quote-all-identifiers`
  Le `--clean --if-exists` est OBLIGATOIRE (cf. DEF-8) : sans lui, le restore
  echoue silencieusement sur les conflits de PK avec les tables creees par
  `01_extensions.sql` (init script docker-entrypoint).
- Compression gzip
- Manifeste SHA-256 (`MANIFEST.sha256` dans le dossier de backup)
- Verification d'integrite via `gunzip --test` AVANT toute rotation
- Retention configurable (defaut : 30 jours), rotation appliquee UNIQUEMENT
  apres validation d'integrite du nouveau dump
- Restore avec `psql --set ON_ERROR_STOP=1` (fail-loud strict, ADR-006)
- Verification SHA-256 du manifeste pendant le restore (si present)

Pas active en cron en P0 (le service `evidence-postgres` prod n'est pas
demarre — profile `db` non active). Cron file pre-existant dans
`scripts/backup/korev-pg-backup.cron.disabled` ; activation prevue en P1.

### 6. Tests d'infra

Fichier : `tests/infra/test_postgres_compose.py` (marker `infra`)

| ID  | Test                                       | Critere                                       |
|-----|--------------------------------------------|-----------------------------------------------|
| T1  | `test_T1_postgres_is_reachable`             | `SELECT 1` retourne `1`                        |
| T2  | `test_T2_pgvector_extension_loaded`        | `pg_extension.extname = 'vector'` present       |
| T3  | `test_T3_pgvector_can_create_vector_column`| `CREATE TABLE ... vector(N)` fonctionne        |
| T4  | `test_T4_application_schemas_present`      | identity/chats/memory/audit/legal existent     |
| T5  | `test_T5_init_marker_recorded`             | marker P0 + extensions enregistres             |
| T6  | `test_T6_no_business_table_in_P0`          | aucune table metier dans les schemas applicatifs |

Fichier : `tests/infra/test_dump_restore_pipeline.py` (markers `infra` + `slow`)

| ID  | Test                                       | Critere                                       |
|-----|--------------------------------------------|-----------------------------------------------|
| T7  | `test_T7_dump_then_restore_preserves_all_data` | Cycle complet dump -> down -v -> up -> restore restaure marker post-dump + table avec vector(N) |

Lancement manuel :

```bash
export POSTGRES_STAGING_PASSWORD=korev_staging_test_pwd_P0
pytest -m infra tests/infra/ -v
```

## Critere Go/No-Go P0 -> P1

P0 est valide quand :

1. [x] Snapshot pre-P0 immutable, manifeste SHA-256 verifiable
2. [x] `docker compose -f deploy/docker-compose.staging.yml up -d` healthy en 8s sur VPS
3. [x] 6 tests d'infra T1-T6 passent (validation manuelle equivalente sur VPS)
4. [x] `pg_dump_daily.sh` execute en < 5s sur base vide, `gunzip --test` OK
5. [x] Prod toujours sur `de8b9c7e`, 4 containers healthy
6. [x] Aucun `depends_on: evidence-postgres` dans le compose principal
7. [x] **Test restore complet < 30 min** : pipeline dump -> down -v -> up -> restore
   valide sur VPS, **15 secondes** de bout en bout (15s << 1800s requis), toutes
   les donnees restaurees y compris ligne `korev_init_marker` posterieure a
   l'init script.

P0 est **VALIDE**.

## Pas de P1 sans

- [ ] Job CI dedie qui execute `pytest -m infra` (point H-3 de l'audit
  hostile du plan)
- [ ] Cron `pg_dump_daily.sh` actif sur VPS prod
- [ ] Restauration testee en < 30 min (`pg_dump -> pg_restore` sur staging)
- [ ] Plan de cutover de la phase P1 redige et revue (1 PR, audit hostile
  prealable)

## Post-mortem — incident `--remove-orphans` (5 mai 2026)

**Resume :** lors du test du compose staging sur le VPS OVH, un
`docker compose -f docker-compose.staging.yml down -v --remove-orphans` a
ete execute depuis `/tmp/p0-test`. Cette commande a supprime les containers
prod `evidence-backend` et `evidence-backend-demo` qui ont ete consideres
comme « orphelins » du project Compose courant. Les volumes ont ete
preserves (volumes nommes non lies au project), donc aucune donnee perdue.

**Detection :** vue immediate dans la sortie `docker ps --format ...` qui
ne renvoyait plus aucun container `evidence-*`.

**Resolution (~ 1 min) :**

1. `cd /home/ubuntu/PRISM-Oracle/deploy`
2. `docker compose up -d`
3. Verification healthcheck (`/healthz` interne backend = HTTP 200,
   `caddy /healthz` = OK).

**Cause technique :** `--remove-orphans` opere sur le project Compose courant
(par defaut le nom du dossier de lancement). Lance depuis `/tmp/p0-test`,
le project name etait `p0-test`. Tous les containers exterieurs a ce project
mais visibles par le daemon Docker ont ete consideres comme orphelins.

**Causes humaines :**

- Sous-estimation de l'effet de `--remove-orphans` hors du repertoire prod.
- Absence de project name explicite dans le compose staging au moment du
  test.

**Actions correctives appliquees AVANT le commit P0 :**

| Action | Fichier | Effet |
|--------|---------|-------|
| Ajout `name: evidence-staging` au top du compose staging | `deploy/docker-compose.staging.yml` | Project name verrouille, independant du dossier de lancement |
| Suppression de tous les `--remove-orphans` du test d'infra | `tests/infra/test_postgres_compose.py` | Plus aucune commande dangereuse |
| Ajout `-p evidence-staging` explicite a tous les `docker compose` du test | `tests/infra/test_postgres_compose.py` | Isolation explicite du project |
| Section "Pourquoi PAS `--remove-orphans`" dans le README Postgres | `deploy/postgres/README.md` | Doctrine ecrite pour les futurs operateurs |

**Verification post-correction :**

- Apres restart, prod healthy 4/4 containers en moins de 90 secondes.
- `evidence-backend /healthz` interne = HTTP 200.
- `evidence-caddy /healthz` interne = OK.
- Aucune perte de donnee (les volumes nommes ne sont jamais supprimes par
  `down -v` lorsqu'ils n'appartiennent pas au project courant).

**Leçon :** ce type d'incident n'est PAS prevenu par les tests d'infra ;
c'est une regle d'utilisation. Elle est desormais ecrite dans deux endroits
visibles (README Postgres + docstring du compose) et automatisee dans le
test (project name explicite, jamais de `--remove-orphans`).

## Post-mortem — DEF-8 (5 mai 2026, decouvert pendant le test restore)

**Resume :** le premier test de restore complet a leve une `ERROR: multiple
primary keys for table "korev_init_marker" are not allowed`. Le restore est
apparu termine, mais en realite la table `korev_init_marker` n'a PAS ete
mise a jour avec les donnees du dump (la ligne `TEST_T7_BEFORE_DUMP` insere
avant le dump etait absente apres restore). C'est exactement le pattern
**fail-silent** interdit par ADR-006.

**Cause technique :** `pg_dump_daily.sh` produisait un dump `--format=plain`
sans `--clean --if-exists`. Le restore tentait `CREATE TABLE` sans `DROP`
prealable, ce qui echouait sur les tables deja creees par le init script
`01_extensions.sql` au boot du nouveau container. Sans `ON_ERROR_STOP=1`
cote restore, psql poursuivait l'execution apres l'erreur, donnant
l'apparence d'un succes.

**Detection :** verification manuelle des donnees apres restore — la ligne
posterieure au init script etait absente. Le test T7 avait ete redige des
le depart pour piéger ce cas (insertion d'une ligne posterieure au init
script + assertion sur sa presence apres restore).

**Actions correctives appliquees AVANT le commit P0 final :**

| Action | Fichier | Effet |
|--------|---------|-------|
| Ajout `--clean --if-exists` au pg_dump | `scripts/backup/pg_dump_daily.sh` | Le dump prefixe chaque CREATE par DROP IF EXISTS |
| Creation `pg_restore_from_dump.sh` | `scripts/backup/pg_restore_from_dump.sh` | Restore standardise avec `ON_ERROR_STOP=1`, fail-loud, verif SHA-256 |
| Test T7 dans `test_dump_restore_pipeline.py` | `tests/infra/test_dump_restore_pipeline.py` | Verrouille le pipeline en CI |
| DEF-9 (mineur, code mort) corrige | `pg_restore_from_dump.sh` | Pattern `RC=0; ... \|\| RC=$?` au lieu de `$?` apres pipeline avec `set -e` |
| Mise a jour de cette section + § Realisations | ce document | Trace d'audit |

**Verification post-correction :** test pipeline complet sur VPS — toutes
les donnees temoins restaurees (marker `TEST_T7_BEFORE_DUMP` present,
table `chats.test_t7_table` avec ses 3 payloads et la colonne `vector(3)`
intacte). Duree totale : 15 secondes.

**Leçon :** un test de pipeline qui se contente de regarder le code de
retour du restore est insuffisant. Il faut verifier que les donnees
*posterieures* a l'init script sont restaurees, parce que c'est exactement
la difference entre un restore reussi et un restore fail-silent.
