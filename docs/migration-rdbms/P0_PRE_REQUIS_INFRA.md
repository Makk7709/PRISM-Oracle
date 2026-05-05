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

### 5. Backup quotidien

Fichier : `scripts/backup/pg_dump_daily.sh`

- `pg_dump --format=plain --no-owner --no-acl --quote-all-identifiers`
- Compression gzip
- Manifeste SHA-256 (`MANIFEST.sha256` dans le dossier de backup)
- Retention configurable (defaut : 30 jours)
- Verification d'integrite via `gunzip --test`

A activer en cron sur VPS OVH lors du passage en P1 (pas avant — pas de DB
active en prod).

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

Lancement manuel :

```bash
export POSTGRES_STAGING_PASSWORD=korev_staging_test_pwd_P0
pytest -m infra tests/infra/ -v
```

## Critere Go/No-Go P0 -> P1

P0 est valide quand :

1. [x] Snapshot pre-P0 immutable, manifeste SHA-256 verifiable
2. [ ] `docker compose -f deploy/docker-compose.staging.yml up -d` healthy < 30s
3. [ ] 6 tests d'infra T1-T6 passent
4. [ ] `pg_dump_daily.sh` execute en < 5s sur base vide, `gunzip --test` OK
5. [x] Prod toujours sur `de8b9c7e`, 4 containers healthy
6. [x] Aucun `depends_on: evidence-postgres` dans le compose principal

Les points 2/3/4 seront valides au prochain passage docker (en local sur
poste developpeur ou sur VPS OVH).

## Pas de P1 sans :

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
