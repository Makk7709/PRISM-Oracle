# Guide opérateur — KOREV Evidence

**Version** : v1.3.1 · **Public** : ops, SRE, administrateurs système · **Langue** : français

Complète [deploy/RUNBOOK.md](../deploy/RUNBOOK.md) avec des procédures orientées production OVH/Docker : surveillance, incidents, scheduler, backup.

---

## 1. Prérequis opérateur

- Accès SSH au serveur (clé ED25519)
- Docker + Docker Compose v2
- Répertoire déploiement : `/home/ubuntu/PRISM-Oracle`
- Script de déploiement : `./scripts/deploy_prod.sh` (estampille `VERSION.json`)

---

## 2. Surveillance

### 2.1 Healthchecks

| Endpoint | Attendu | Usage |
|----------|---------|-------|
| `GET /healthz` | `{"status":"ok"}` | Liveness Docker, load balancer |
| `GET /readyz` | ready | Readiness (si configuré) |
| `GET /metrics` | métriques Prometheus-like | Observabilité (admin) |
| `GET /health` | `{"status":"ok"}` | Health API interne |

```bash
curl -s https://www.korev-evidence.com/healthz
curl -s http://127.0.0.1:5050/metrics   # depuis le serveur
```

### 2.2 État des conteneurs

```bash
cd /home/ubuntu/PRISM-Oracle
docker compose -f deploy/docker-compose.yml ps
```

Attendu : `evidence-backend`, `evidence-caddy`, `evidence-samba` en **healthy**.

### 2.3 Logs

```bash
# Backend (agent, scheduler, erreurs)
docker logs evidence-backend --since 1h 2>&1 | tail -100

# Filtrer scheduler
docker logs evidence-backend 2>&1 | grep -iE "JobLoop|Scheduler Task|task_stale"

# Caddy (TLS, routing)
docker logs evidence-caddy --since 1h
```

Fichiers volumes : `evidence-logs`, `evidence-audit` (selon montage).

### 2.4 Vérifier la version déployée

```bash
docker exec evidence-backend cat /app/VERSION.json
```

Champs clés : `tag`, `build_commit`, `build_date`.

---

## 3. Déploiement et mise à jour

### 3.1 Procédure standard

```bash
cd /home/ubuntu/PRISM-Oracle
git pull --ff-only origin main
./scripts/deploy_prod.sh
```

Le script exporte `GIT_COMMIT`, `GIT_BRANCH`, `BUILD_DATE` pour estampiller l'image.

### 3.2 Post-déploiement

```bash
./scripts/post_deploy_validate.sh --base-url https://www.korev-evidence.com
python3 scripts/observability_alert_check.py --base-url https://www.korev-evidence.com
```

### 3.3 Rollback

```bash
./deploy/scripts/rollback.sh --list
./deploy/scripts/rollback.sh --version <tag>
```

---

## 4. Incidents courants

### 4.1 Backend unhealthy / 502

1. `docker compose -f deploy/docker-compose.yml ps`
2. `docker logs evidence-backend --tail 50`
3. Redémarrage ciblé : `docker compose -f deploy/docker-compose.yml restart evidence-backend`
4. Si échec : `./scripts/deploy_prod.sh`

### 4.2 Scheduler — tâches bloquées en `error`

**Symptôme** : tâches cron n'ont pas tourné depuis des jours, état `error`, marqueur `RECOVERED_STALE_RUNNING` ou `ttl_exceeded_*`.

**Cause historique (corrigée v1.3.1)** : TTL 900 s trop court + tâches ERROR non réessayées.

**Actions** :

```bash
# Inspecter les tâches
docker exec evidence-backend python3 -c "
import json
d=json.load(open('/app/tmp/scheduler/tasks.json'))
for t in d['tasks']:
    print(t['state'], t['name'][:50], t.get('last_run','')[:19])
"

# Remettre en idle (sous verrou flock — via script Python dans le conteneur)
# Voir procédure incident 2026-06-01 : reset state error → idle
```

Depuis v1.3.1 : les tâches cron en `error` sont **réessayées automatiquement** à la prochaine occurrence cron.

### 4.3 Scheduler — tâche bloquée en `running` > 1 h

Le mécanisme `_recover_stale_running_tasks` passe en `error` après TTL **3600 s** (configurable via `EVIDENCE_SCHEDULER_RUN_TTL_SECONDS`).

Vérifier : `running_since` dans `tasks.json`. Si bloqué, attendre le TTL ou reset manuel.

### 4.4 Fuite de descripteurs (FD leak)

Incident documenté : [reports/INCIDENT_2026-06-03_message_loop_deadlock_fd_leak.md](reports/INCIDENT_2026-06-03_message_loop_deadlock_fd_leak.md).

Symptôme : serveur lent, connexions refusées. Action : redémarrage `evidence-backend`, analyse logs.

### 4.5 Rate limiting login

Variable `RATE_LIMIT_API_MAX` (défaut augmenté en local). Si utilisateurs bloqués : vérifier logs rate limit, ajuster env, redémarrer.

---

## 5. Backup et restauration

### 5.1 Répertoires critiques

| Chemin (volume) | Contenu |
|-----------------|---------|
| `data/` | Données applicatives |
| `audit/` | Logs d'audit sécurité |
| `tmp/scheduler/tasks.json` | Tâches planifiées |
| `tmp/chats/` | Conversations |
| `shared/` | Workspaces utilisateurs |
| `memory/` | Mémoire agents |
| `deploy/users.json` | Comptes (hors git public) |
| `deploy/.env` | Secrets (jamais dans git) |

### 5.2 Backup manuel

```bash
# Exemple archive volumes
sudo tar czf /backup/evidence-$(date +%Y%m%d).tar.gz \
  /var/lib/docker/volumes/evidence-data/_data \
  /var/lib/docker/volumes/evidence-audit/_data \
  /var/lib/docker/volumes/evidence-tmp/_data \
  /var/lib/docker/volumes/evidence-shared/_data
```

### 5.3 Backup via UI

Admin → Paramètres → **Backup & Restore** (endpoints `/backup_*`, loopback requis pour certaines opérations).

---

## 6. Multi-utilisateur

### 6.1 Fichier comptes

- Production : `deploy/users.json` (monté `:ro` dans le conteneur)
- Overlay mots de passe : `data/users.local.json` (writable, permissions `0600`)

### 6.2 Ajouter un utilisateur

1. Générer hash Argon2 : `python scripts/hash_password.py`
2. Ajouter entrée dans `users.json` (role, organization, org_role)
3. Configurer partage Samba correspondant dans `docker-compose.yml`
4. Redémarrer si nécessaire

### 6.3 Isolation

- **OWNER** voit toutes les conversations de son organisation (comportement prévu).
- **MEMBER** voit uniquement les siennes.
- Isolation inter-organisations : étanche via `authorization.py`.

---

## 7. Sécurité opérationnelle

| Règle | Détail |
|-------|--------|
| Secrets | Uniquement dans `deploy/.env` — jamais commités |
| TLS | Caddy — renouvellement automatique |
| Audit | Logs dans volume `evidence-audit`, rétention ~90 jours |
| Offline | `OFFLINE_MODE` pour environnements air-gapped |
| Postgres | Profil `db` — ne pas activer sauf besoin explicite |

---

## 8. Escalade

| Niveau | Contact | Cas |
|--------|---------|-----|
| L1 | Auto-diagnostic (ce guide + RUNBOOK) | Health, logs, restart |
| L2 | ops@korev.ai | Incident persistant, déploiement |
| L3 | security@korev.ai | Fuite données, compromission |

---

## 9. Checklist post-incident

- [ ] Cause identifiée et documentée dans `docs/reports/`
- [ ] Correctif déployé ou contournement appliqué
- [ ] `VERSION.json` vérifié
- [ ] Healthcheck OK
- [ ] Tâches scheduler état cohérent
- [ ] Utilisateurs notifiés si impact visible

---

*Guide opérateur — KOREV Evidence v1.3.1. Dernière révision : 2026-06-13.*
