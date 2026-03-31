# KOREV Evidence — Scripts utilitaires et d'audit

## Vue d'ensemble

24 scripts couvrant l'audit, le déploiement, la migration, l'observabilité et la validation.

## Scripts d'audit et validation

| Script | Description | Commande |
|--------|-------------|----------|
| `audit_lint.py` | Vérifie que chaque brique d'audit a BrickID, Statut, Preuves, Validation, Limites, ClaimID | `python3 scripts/audit_lint.py` |
| `audit_verify.sh` | Vérification complète du rapport d'audit | `bash scripts/audit_verify.sh` |
| `mcp_functional_check.py` | Test fonctionnel des serveurs MCP (ArXiv, PubMed, Tavily, etc.) | `python3 scripts/mcp_functional_check.py` |
| `router_prod_validation.py` | Validation du router v2 en conditions production | `python3 scripts/router_prod_validation.py` |
| `router_validation.py` | Validation complète du router (déterminisme, anti-injection, multi-intent) | `python3 scripts/router_validation.py` |
| `validate_legal_sources.py` | Validation des sources juridiques (Légifrance, PISTE) | `python3 scripts/validate_legal_sources.py` |
| `validate_strategic_dossier.py` | Validation qualité d'un dossier stratégique (longueur, sources, structure) | `python3 scripts/validate_strategic_dossier.py` |

## Scripts de déploiement

| Script | Description | Commande |
|--------|-------------|----------|
| `deploy-docker.sh` | Déploiement Docker one-click (dev/test) | `./scripts/deploy-docker.sh` |
| `docker-entrypoint.sh` | Point d'entrée du container Docker (backend) | Appelé automatiquement par Docker |
| `install-mac.sh` | Installation locale sur macOS | `./scripts/install-mac.sh` |
| `install-server.sh` | Installation serveur Linux | `./scripts/install-server.sh` |
| `post_deploy_validate.sh` | Validation post-déploiement (healthcheck, smoke tests) | `bash scripts/post_deploy_validate.sh` |

## Scripts de migration

| Script | Description | Commande |
|--------|-------------|----------|
| `normalize_org_migration.py` | Migration des organisations vers le modèle canonique (case-insensitive slug) | `python3 scripts/normalize_org_migration.py` |
| `migrate_multi_tenant.py` | Migration multi-tenant (ajout organization_id aux chats/tâches) | `python3 scripts/migrate_multi_tenant.py` |
| `migrate_scheduler_notifications_to_store.py` | Migration scheduler/notifications vers les stores abstraits (JSON → Redis) | `python3 scripts/migrate_scheduler_notifications_to_store.py` |

## Scripts d'observabilité

| Script | Description | Commande |
|--------|-------------|----------|
| `smoke_test_multi_user.py` | Smoke test post-déploiement multi-user + concurrence (Amine/Jérémie) | `python3 scripts/smoke_test_multi_user.py` |
| `observability_alert_check.py` | Vérifie les seuils d'alerte (cross-tenant denied, claim conflicts, failed tasks) | `python3 scripts/observability_alert_check.py` |

## Scripts de génération

| Script | Description | Commande |
|--------|-------------|----------|
| `evidence_pdf.py` | Moteur de génération PDF Evidence/PRISM | `python3 scripts/evidence_pdf.py` |
| `generate_cover_and_pdf.py` | Génération couverture + PDF complet | `python3 scripts/generate_cover_and_pdf.py` |
| `generate_strategic_dossier.py` | Génération d'un dossier stratégique standalone | `python3 scripts/generate_strategic_dossier.py` |
| `hash_password.py` | Génération de hash Argon2 pour users.json | `python3 scripts/hash_password.py "MonMotDePasse"` |

## Scripts de données

| Script | Description | Commande |
|--------|-------------|----------|
| `build_legal_index_official.py` | Construction de l'index juridique FTS5 depuis les sources PISTE/Judilibre | `python3 scripts/build_legal_index_official.py` |
| `build_legal_index_test.py` | Construction d'un index juridique de test | `python3 scripts/build_legal_index_test.py` |
| `index_rgpd.py` | Indexation des textes RGPD | `python3 scripts/index_rgpd.py` |

## Utilisation en Makefile

```bash
# Lint documentaire
make audit-lint

# Vérification complète
make audit-verify

# Avec tests
AUDIT_RUN_TESTS=1 make audit-verify
```
