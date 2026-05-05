# Postgres + pgvector — Migration RDBMS (P0)

Ce répertoire contient les scripts d'initialisation et la configuration du SGBD
Postgres 16 + pgvector adopté à partir de la phase P0 de la migration RDBMS
(cf. `docs/adr/ADR-007-postgres-pgvector-adoption.md`).

## Statut P0 — POSE DES FONDATIONS, AUCUN IMPACT PROD

À la fin de la phase P0 :

- Le service `evidence-postgres` existe dans `deploy/docker-compose.yml` mais
  derrière le **profil `db`**. `docker compose up -d` standard NE le démarre PAS.
- Le service `evidence-postgres-staging` est **défini** dans
  `deploy/docker-compose.staging.yml` (compose autonome, ports et volumes
  séparés). Il n'est pas demarre en continu en P0 — il est instancie a la
  demande, le temps des tests d'infra (`pytest -m infra`), puis arrete via
  `docker compose -f docker-compose.staging.yml down -v`. P1 introduira un
  staging permanent en parallele de la prod.
- Aucun service applicatif (backend, demo, caddy, samba) ne dépend de Postgres.
- Aucune donnée métier n'est écrite. Seuls les extensions et schémas vides sont
  créés par `init/01_extensions.sql`.

## Lancer Postgres en staging (sur OVH ou en local)

Le project name `evidence-staging` est verrouillé par la directive `name:` du
compose (cf. `deploy/docker-compose.staging.yml`). Il est donc transparent
pour `up` et `down`. Vous pouvez aussi le passer explicitement avec `-p` :

```bash
cd deploy
docker compose -f docker-compose.staging.yml up -d evidence-postgres-staging
docker compose -f docker-compose.staging.yml exec evidence-postgres-staging \
    psql -U evidence_staging -d evidence_staging -c "SELECT * FROM korev_init_marker;"
docker compose -f docker-compose.staging.yml down -v
```

### ⚠️ Règle absolue : jamais `--remove-orphans` sans `-p` explicite

`docker compose down --remove-orphans` supprime les containers que **Docker
Compose considère** comme orphelins du project en cours. Si vous lancez la
commande depuis un répertoire dont le nom collide avec un autre project
(typique : un dossier `deploy/` où tournent à la fois la prod et le staging),
les containers de l'autre project seront détruits.

**Symptôme constaté en P0 (5 mai 2026) :** un `down -v --remove-orphans`
lancé depuis `/tmp/p0-test` sur le VPS OVH a tué les containers prod
`evidence-backend` et `evidence-backend-demo`. Les volumes ont été préservés
(volumes nommés non liés au project), donc la prod a pu être restaurée en
1 minute via un simple `docker compose up -d` depuis le dossier prod.

**Mesures de protection en place :**

1. `name: evidence-staging` est explicite dans le compose staging.
2. Les tests d'infra `tests/infra/test_postgres_compose.py` utilisent
   systématiquement `-p evidence-staging` ET n'invoquent JAMAIS
   `--remove-orphans`.
3. Cette règle est documentée ici et dans la docstring du test d'infra.

## Activer Postgres en prod (NE PAS FAIRE EN P0)

```bash
# Ne sera fait qu'en P1 après validation complète en staging
cd deploy
docker compose --profile db up -d evidence-postgres
```

## Backups

Voir `scripts/backup/pg_dump_daily.sh` (cron quotidien, rétention 30 j locale,
copie chiffrée vers stockage externe à configurer en P1).

## Variables d'environnement (à définir dans `.env`)

| Variable                       | Défaut              | Rôle                                                  |
|--------------------------------|---------------------|-------------------------------------------------------|
| `POSTGRES_USER`                | `evidence`          | Utilisateur applicatif principal (prod)               |
| `POSTGRES_PASSWORD`            | (obligatoire)       | Mot de passe prod — JAMAIS commit, JAMAIS log         |
| `POSTGRES_DB`                  | `evidence`          | Base de données par défaut (prod)                     |
| `PG_CPU_LIMIT`                 | `2.0`               | Limite CPU container prod                             |
| `PG_MEMORY_LIMIT`              | `2G`                | Limite mémoire container prod                         |
| `POSTGRES_STAGING_USER`        | `evidence_staging`  | Utilisateur staging                                   |
| `POSTGRES_STAGING_PASSWORD`    | (obligatoire)       | Mot de passe staging — DIFFÉRENT de la prod           |
| `POSTGRES_STAGING_DB`          | `evidence_staging`  | Base de données staging                               |
| `POSTGRES_STAGING_HOST`        | `127.0.0.1`         | Bind staging — localhost uniquement par défaut        |
| `POSTGRES_STAGING_PORT`        | `5433`              | Port host staging (différent du 5432 prod)            |
| `PG_STAGING_CPU_LIMIT`         | `1.0`               | Limite CPU container staging                          |
| `PG_STAGING_MEMORY_LIMIT`      | `1G`                | Limite mémoire container staging                      |
| `KOREV_PG_BACKUP_DIR`          | `/home/ubuntu/backups/pg` | Dossier des dumps `pg_dump_daily.sh`              |
| `KOREV_PG_RETENTION_DAYS`      | `30`                | Rétention locale des dumps (jours)                    |
