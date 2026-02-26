# Audit pré-déploiement — Guide de Déploiement Entreprise v2.0

**Date :** 2026-02-11  
**Document audité :** `docs/GUIDE_DEPLOIEMENT_ENTREPRISE.md`  
**Référentiel :** Codebase KOREV Evidence (deploy/, python/, run_ui.py)

---

## 1. Résumé exécutif

| Critère | Statut |
|---------|--------|
| Cohérence guide ↔ codebase | ✅ Conforme après corrections |
| Docker Compose | ✅ Valide (3 services : backend, caddy, samba) |
| Multi-utilisateurs (7 users) | ✅ Aligné (docker-compose, .env.example, users.json.example) |
| Ordre de déploiement (users.json) | ✅ Correct (copie AVANT premier docker compose up) |
| Script de backup | ✅ Chemins corrects (deploy/.env, deploy/users.json) |
| Tests de sécurité | ✅ 330 passed |

---

## 2. Points vérifiés

### 2.1. Architecture & Docker

| Élément | Guide | Codebase | Statut |
|---------|-------|----------|--------|
| Services Docker | 3 (backend, caddy, samba) | docker-compose.yml | ✅ |
| Volume evidence-shared | Monté backend + samba | docker-compose.yml L49, L129 | ✅ |
| users.json bind mount | deploy/users.json | L53 | ✅ |
| EVIDENCE_SHARED_DIR | /app/shared | run_ui.py L155, docker-compose L42 | ✅ |
| Ports exposés | 80, 443, 445 | docker-compose L88-89, L126 | ✅ |

### 2.2. Multi-utilisateurs

| Élément | Guide | Codebase | Statut |
|---------|-------|----------|--------|
| Nombre d'utilisateurs | 7 (6 users + admin) | docker-compose L136-150 | ✅ |
| Utilisateurs | marie, jean, pierre, sophie, thomas, claire, admin | users.json.example, .env.example | ✅ |
| Structure workspace | users/{user}/documents, rapports, tmp | user_workspace.py L29 | ✅ |
| Dossier commun | commun/ | user_workspace.py L44 | ✅ |
| Audit trail | audit/file_operations.jsonl | user_workspace.py L297 | ✅ |

### 2.3. Configuration & chemins

| Élément | Guide | Codebase | Statut |
|---------|-------|----------|--------|
| users.json path | deploy/users.json | run_ui.py L144 | ✅ |
| UserManager | users_json strict en prod | run_ui.py L149-151 | ✅ |
| WorkspaceManager | Si EVIDENCE_SHARED_DIR | run_ui.py L155-158 | ✅ |

### 2.4. Script de backup

| Élément | Guide | Statut |
|---------|-------|--------|
| deploy/.env | L1112 | ✅ Correct |
| deploy/users.json | L1113 | ✅ Correct |
| Volume evidence-shared | L1107 | ✅ Inclus |

### 2.5. Caddyfile

| Élément | Guide | deploy/config/Caddyfile | Statut |
|---------|-------|-------------------------|--------|
| Port 80 | :80 | L14 | ✅ |
| reverse_proxy | evidence-backend:5050 | L16 | ✅ |
| /healthz | handle | L34-36 | ✅ |

---

## 3. Corrections appliquées lors de l'audit

### 3.1. Section 7.3 — shell_interface (CRITIQUE)

**Problème :** Le guide indiquait :
- Docker → `ssh`
- Installation locale → `local`

**Code réel :** `settings.py` L1885 :
```python
shell_interface="local" if runtime.is_dockerized() else "ssh"
```

**Correction :** Le guide a été mis à jour pour indiquer que Docker utilise `local` par défaut. L’erreur "Unable to connect to port 55022" survient quand `ssh` est sélectionné par erreur en Docker.

### 3.2. Diagramme d’architecture

**Problème :** Le diagramme ne montrait que 3 utilisateurs (marie, jean, admin).

**Correction :** Ajout de la mention « ... (pierre, sophie, thomas, claire) » pour refléter les 7 utilisateurs.

---

## 4. Points déjà conformes (audit précédent)

- Ordre des phases : copie `users.json` AVANT premier `docker compose up`
- Port 445 dans les checklists firewall / antivirus
- Comptage des containers : 3 (evidence-backend, evidence-caddy, evidence-samba)
- Fichier favicon : `webui/public/favicon.svg` (convertir en .ico pour raccourcis Windows)

---

## 5. Recommandations

1. **Fichier .env** : Créer `deploy/.env` à partir de `deploy/.env.example` avant tout `docker compose up`.
2. **users.json** : Toujours copier `users.json.example` vers `users.json` avant le premier lancement (évite le bug du bind mount Docker).
3. **shell_interface** : Ne pas modifier en Docker sauf erreur ; la valeur par défaut `local` est correcte.

---

## 6. Validation finale

| Test | Résultat |
|------|----------|
| Tests sécurité (330) | ✅ Passed |
| Syntaxe docker-compose | ✅ Valide (nécessite .env présent) |
| Cohérence des chemins | ✅ Vérifiée |

**Verdict :** Le guide est prêt pour le déploiement. Les corrections mineures ont été appliquées.

---

*Audit réalisé par contrôle automatisé du codebase contre le guide v2.0.*
