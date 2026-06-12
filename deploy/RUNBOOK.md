# PRISM + Evidence — Runbook Opérationnel

## Vue d'ensemble

Ce runbook couvre les procédures opérationnelles pour le déploiement DICA de PRISM + Evidence.

```yaml
Version: 1.0.0
Mode: Offline-first
Support: ops@korev.ai
```

---

## 1. Installation

### 1.1 Prérequis

| Composant | Version minimale | Notes |
|-----------|------------------|-------|
| Docker | 20.10+ | Ou Docker Desktop |
| Docker Compose | 2.0+ | Intégré à Docker Desktop |
| Python | 3.11+ | Pour mode portable |
| RAM | 4 GB | 8 GB recommandé |
| Disque | 10 GB | Hors données |

### 1.2 Installation Docker (Recommandé)

```bash
# 1. Cloner le repo
git clone https://github.com/Makk7709/PRISM-Oracle.git
cd PRISM-Oracle

# 2. Configurer l'environnement
cp deploy/.env.example deploy/.env
# Éditer .env avec les clés API

# 3. Installer
chmod +x scripts/install-server.sh
./scripts/install-server.sh
```

### 1.3 Installation Portable (Sans Docker)

```bash
# Unix/macOS
cd deploy/portable
chmod +x *.sh
./start.sh

# Windows PowerShell
cd deploy\portable
.\start.ps1
```

---

## 2. Vérification Post-Installation

### 2.1 Health Check

```bash
# Vérifier que le service est up
curl http://localhost/healthz

# Réponse attendue:
# {"status":"ok"}
```

### 2.2 Readiness Check

```bash
curl http://localhost/healthz

# Si 200 est stable, reverse proxy + backend sont opérationnels
```

### 2.3 Smoke Test

```bash
python tools/smoke_test.py

# Doit afficher: SMOKE TEST PASSED
```

---

## 3. Opérations Courantes

### 3.1 Démarrer / Arrêter

```bash
# Docker
cd deploy
docker compose up -d      # Démarrer
docker compose down       # Arrêter
docker compose restart    # Redémarrer

# Portable
./start.sh               # Démarrer
./stop.sh                # Arrêter
```

### 3.2 Voir les Logs

```bash
# Docker
docker compose logs -f evidence-backend

# Portable
tail -f logs/evidence.log

# Logs spécifiques
tail -f logs/audit.log
tail -f logs/consensus.log
```

### 3.3 Mise à Jour

```bash
# Avec rollback automatique si échec
./scripts/upgrade.sh --version 1.1.0

# Le script:
# 1. Sauvegarde la version actuelle
# 2. Installe la nouvelle version
# 3. Lance les smoke tests
# 4. Rollback auto si échec
```

### 3.5 Validation post-déploiement (scheduler + notifications)

```bash
# Smoke test multi-user + concurrence (bloquant)
export SMOKE_USER_A="admin_user_a"
export SMOKE_PASS_A="***"
export SMOKE_USER_B="admin_user_b"
export SMOKE_PASS_B="***"
./scripts/post_deploy_validate.sh --base-url https://www.korev-evidence.com

# Vérification alertes observabilité (bloquant si seuil dépassé)
python3 scripts/observability_alert_check.py --base-url https://www.korev-evidence.com
```

### 3.4 Rollback Manuel

```bash
# Lister les backups disponibles
./scripts/rollback.sh --list

# Rollback vers une version spécifique
./scripts/rollback.sh --version 1.0.0

# Rollback vers le dernier backup
./scripts/rollback.sh --latest
```

---

## 4. Diagnostic

### 4.0 Triage rapide OVH (3 commandes)

```bash
cd PRISM-Oracle/deploy
docker compose ps
docker compose logs --tail=200 evidence-backend
docker compose logs --tail=100 evidence-caddy
```

### 4.1 Générer un Bundle de Diagnostic

```bash
python tools/diagnostics_bundle.py

# Génère: evidence_diagnostics_YYYYMMDD_HHMMSS.zip
# Contient: config (sans secrets), logs, métriques, infos système
```

### 4.2 Vérifier l'État du Système

```bash
# Health check complet
python -m python.helpers.health_endpoints

# Métriques
curl http://127.0.0.1:5050/metrics
```

### 4.3 Problèmes Courants

#### Service ne démarre pas

```bash
# Vérifier les logs
docker compose logs evidence-backend

# Vérifier les ports
netstat -tlnp | grep 5050

# Vérifier la config
python -c "from python.helpers.deploy_config import validate_config; validate_config()"
```

#### Consensus échoue

```bash
# Vérifier le mode offline
grep OFFLINE_MODE .env

# Vérifier les clés API (si online)
grep API_KEY .env  # Ne doit pas être vide
```

#### Problèmes de performance

```bash
# Vérifier les ressources
docker stats

# Vérifier les métriques
curl http://127.0.0.1:5050/metrics | grep latency
```

---

## 5. Sécurité

### 5.1 Mode Offline (Par Défaut)

```ini
# Dans .env
OFFLINE_MODE=true
```

En mode offline:

- Aucun appel réseau externe
- LLMs utilisent des réponses en cache
- Recherche limitée aux données locales

### 5.2 Mode Online Restreint

```ini
# Dans .env
OFFLINE_MODE=false
NETWORK_ALLOWLIST=api.openai.com,api.anthropic.com,openrouter.ai
```

Seuls les domaines listés sont autorisés.

### 5.3 Gestion des Secrets

- **NE JAMAIS** commiter le fichier `.env`
- Stocker les clés API dans un gestionnaire de secrets
- Rotation des clés recommandée tous les 90 jours

### 5.4 Audit Log

Les logs d'audit sont stockés séparément:

```bash
ls -la audit/

# Format: JSON Lines, append-only
# Rétention: 90 jours (configurable)
```

---

## 6. Backup & Restauration

### 6.1 Données à Sauvegarder

| Répertoire | Description | Priorité |
|------------|-------------|----------|
| `data/` | Données persistantes | Critique |
| `audit/` | Logs d'audit | Haute |
| `.env` | Configuration | Haute |
| `logs/` | Logs application | Basse |

### 6.2 Backup Manuel

```bash
# Créer un backup complet
tar -czvf evidence_backup_$(date +%Y%m%d).tar.gz \
    data/ audit/ deploy/.env

# Volumes Docker
docker run --rm -v evidence-data:/data -v $(pwd):/backup \
    alpine tar cvf /backup/data_backup.tar /data
```

### 6.3 Restauration

```bash
# Arrêter Evidence
docker compose down

# Restaurer les données
tar -xzvf evidence_backup_YYYYMMDD.tar.gz

# Redémarrer
docker compose up -d
```

---

## 7. Monitoring

### 7.1 Endpoints de Monitoring

| Endpoint | Usage |
|----------|-------|
| `/healthz` | Liveness probe |
| `/readyz` | Readiness probe |
| `/metrics` | Métriques Prometheus |

### 7.2 Alertes Recommandées

```yaml
# Exemple pour monitoring externe
alerts:
  - name: EvidenceDown
    condition: healthz != 200 for 2m
    severity: critical
    
  - name: EvidenceNotReady
    condition: readyz != 200 for 5m
    severity: warning
    
  - name: HighLatency
    condition: p95_latency > 5s
    severity: warning
```

---

## 8. Contacts & Escalade

### Niveau 1: Support Utilisateur

- Vérifier les logs
- Redémarrer le service
- Consulter ce runbook

### Niveau 2: Support Technique

- Générer un bundle diagnostic
- Contacter: <ops@korev.ai>

### Niveau 3: Escalade Critique

- Incidents de sécurité
- Perte de données
- Contacter: <security@korev.ai>

---

## 9. Checklist de Déploiement DICA

### Avant Déploiement

- [ ] Vérifier les prérequis (Docker, RAM, disque)
- [ ] Récupérer les clés API nécessaires
- [ ] Vérifier la politique réseau DICA
- [ ] Préparer le fichier .env

### Pendant Déploiement

- [ ] Exécuter `scripts/install-server.sh` (OVH Linux) ou `scripts/install-windows.bat` (Windows)
- [ ] Vérifier `/healthz` via Caddy (`curl http://localhost/healthz`)
- [ ] Exécuter smoke_test.py
- [ ] Vérifier les logs

### Après Déploiement

- [ ] Configurer les backups
- [ ] Documenter l'instance (IP, version)
- [ ] Tester un cas d'usage réel
- [ ] Former les utilisateurs

---

*Dernière mise à jour: Janvier 2026*
