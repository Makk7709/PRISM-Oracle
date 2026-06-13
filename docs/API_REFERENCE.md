# Référence API — KOREV Evidence

**Version** : v1.3.1 · **Public** : intégrateurs, développeurs · **Base URL** : `https://<hôte>/`

Les handlers REST sont enregistrés dynamiquement depuis `python/api/` : chaque fichier `*.py` expose une route `/<nom_du_fichier>` (ex. `message.py` → `POST /message`).

---

## 1. Conventions

### 1.1 Authentification

| Mécanisme | Usage |
|-----------|--------|
| **Session web** | Cookie de session Flask après `POST /login` — requis pour la majorité des endpoints UI |
| **CSRF** | Token via `GET /csrf_token`, envoyé en header ou body sur les mutations |
| **Clé API** | Header `X-API-KEY` (ou paramètre selon handler) — endpoints `api_*` et `rfc` |
| **Admin** | Rôle administrateur requis (`settings_*`, `observability_metrics`) |
| **Loopback** | `scheduler_tick` : accessible uniquement depuis localhost |

### 1.2 Format

- Requêtes : JSON (`Content-Type: application/json`) sauf upload fichiers (`multipart/form-data`).
- Réponses : JSON ou flux SSE selon l'endpoint.
- Erreurs : `{"error": "..."}` avec code HTTP 4xx/5xx.

### 1.3 Proxy et middleware

| Chemin | Type | Description |
|--------|------|-------------|
| `/mcp` | ASGI | Proxy MCP dynamique |
| `/a2a` | ASGI | Serveur Agent-to-Agent (FastA2A) |

---

## 2. Routes Flask (hors `python/api/`)

| Méthode | Route | Auth | Description |
|---------|-------|------|-------------|
| GET, POST | `/login` | Non | Page et traitement connexion |
| POST | `/change_password` | Session | Changement mot de passe (multi-user) |
| GET | `/logout` | Session | Déconnexion |
| GET | `/` | Session | Interface WebUI |
| GET | `/healthz` | Non | Liveness (Docker) |
| GET | `/readyz` | Non | Readiness |
| GET | `/metrics` | Non* | Métriques observabilité |

\* `/metrics` peut être restreint selon configuration déploiement.

---

## 3. Catalogue des 71 endpoints API

Légende colonnes : **Auth** = session requise · **Admin** = rôle admin · **API key** = clé API · **CSRF** = protection CSRF · **Loop** = loopback only

### 3.1 Chat et messages

| Endpoint | Méthodes | Auth | Admin | API key | CSRF | Rôle |
|----------|----------|------|-------|---------|------|------|
| `/message` | POST | ✓ | | | ✓ | Envoyer un message (sync) |
| `/message_async` | POST | ✓ | | | ✓ | Message asynchrone |
| `/poll` | POST | ✓ | | | ✓ | Polling réponses / logs |
| `/pause` | POST | ✓ | | | ✓ | Mettre en pause l'agent |
| `/nudge` | POST | ✓ | | | ✓ | Relancer l'agent |
| `/api_message` | POST | | | ✓ | | Message via clé API |
| `/api_reset_chat` | POST | | | ✓ | | Reset chat (API) |
| `/api_terminate_chat` | POST | | | ✓ | | Terminer chat (API) |
| `/api_log_get` | GET, POST | | | ✓ | | Récupérer logs d'un contexte |
| `/api_files_get` | POST | | | ✓ | | Lister fichiers (API) |

### 3.2 Conversations

| Endpoint | Méthodes | Auth | CSRF | Rôle |
|----------|----------|------|------|------|
| `/chat_create` | POST | ✓ | ✓ | Créer une conversation |
| `/chat_load` | POST | ✓ | ✓ | Charger l'historique |
| `/chat_remove` | POST | ✓ | ✓ | Supprimer une conversation |
| `/chat_rename` | POST | ✓ | ✓ | Renommer |
| `/chat_reset` | POST | ✓ | ✓ | Réinitialiser |
| `/chat_export` | POST | ✓ | ✓ | Exporter |
| `/chat_files_path_get` | POST | ✓ | ✓ | Chemin fichiers du chat |
| `/history_get` | POST | ✓ | ✓ | Historique messages |
| `/ctx_window_get` | POST | ✓ | ✓ | Fenêtre de contexte |
| `/projects` | POST | ✓ | ✓ | Gestion projets |

### 3.3 Fichiers et workspace

| Endpoint | Méthodes | Auth | CSRF | Rôle |
|----------|----------|------|------|------|
| `/upload` | POST | ✓ | ✓ | Upload pièce jointe |
| `/upload_work_dir_files` | POST | ✓ | ✓ | Upload workspace |
| `/get_work_dir_files` | GET | ✓ | | Lister workspace |
| `/download_work_dir_file` | GET | ✓ | ✓ | Télécharger fichier |
| `/delete_work_dir_file` | POST | ✓ | ✓ | Supprimer fichier |
| `/file_info` | POST | ✓ | ✓ | Métadonnées fichier |
| `/image_get` | GET | ✓ | | Servir image générée |

### 3.4 Connaissance (knowledge)

| Endpoint | Méthodes | Auth | CSRF | Rôle |
|----------|----------|------|------|------|
| `/import_knowledge` | POST | ✓ | ✓ | Importer documents |
| `/knowledge_reindex` | POST | ✓ | ✓ | Réindexer |
| `/knowledge_path_get` | POST | ✓ | ✓ | Chemin knowledge base |
| `/memory_dashboard` | POST | ✓ | ✓ | Tableau mémoire agents |

### 3.5 Planificateur (scheduler)

| Endpoint | Méthodes | Auth | CSRF | Loop | Rôle |
|----------|----------|------|------|------|------|
| `/scheduler_tasks_list` | POST | ✓ | ✓ | | Lister tâches |
| `/scheduler_task_create` | POST | ✓ | ✓ | | Créer tâche |
| `/scheduler_task_update` | POST | ✓ | ✓ | | Modifier tâche |
| `/scheduler_task_delete` | POST | ✓ | ✓ | | Supprimer tâche |
| `/scheduler_task_run` | POST | ✓ | ✓ | | Exécuter maintenant |
| `/scheduler_tick` | POST | | | ✓ | Tick interne (cron loopback) |

### 3.6 Paramètres et administration

| Endpoint | Méthodes | Auth | Admin | CSRF | Rôle |
|----------|----------|------|-------|------|------|
| `/settings_get` | GET, POST | ✓ | ✓ | ✓ | Lire paramètres |
| `/settings_set` | POST | ✓ | ✓ | ✓ | Modifier paramètres |
| `/restart` | POST | ✓ | | ✓ | Redémarrer framework |
| `/observability_metrics` | GET, POST | ✓ | ✓ | ✓ | Métriques runtime |
| `/csrf_token` | GET | ✓ | | | Obtenir token CSRF |

### 3.7 Backup & restore

| Endpoint | Méthodes | Auth | CSRF | Rôle |
|----------|----------|------|------|------|
| `/backup_create` | POST | ✓ | ✓ | Créer sauvegarde |
| `/backup_restore` | POST | ✓ | ✓ | Restaurer |
| `/backup_restore_preview` | POST | ✓ | ✓ | Aperçu restauration |
| `/backup_preview_grouped` | POST | ✓ | ✓ | Aperçu groupé |
| `/backup_inspect` | POST | ✓ | ✓ | Inspecter archive |
| `/backup_get_defaults` | POST | ✓ | ✓ | Valeurs par défaut |
| `/backup_test` | POST | ✓ | ✓ | Test intégrité backup |

### 3.8 MCP

| Endpoint | Méthodes | Auth | CSRF | Rôle |
|----------|----------|------|------|------|
| `/mcp_servers_status` | POST | ✓ | ✓ | État serveurs MCP |
| `/mcp_servers_apply` | POST | ✓ | ✓ | Appliquer config MCP |
| `/mcp_server_get_detail` | POST | ✓ | ✓ | Détail serveur |
| `/mcp_server_get_log` | POST | ✓ | ✓ | Logs serveur MCP |

### 3.9 Notifications

| Endpoint | Méthodes | Auth | CSRF | Rôle |
|----------|----------|------|------|------|
| `/notifications_history` | POST | ✓ | ✓ | Historique |
| `/notifications_mark_read` | POST | ✓ | ✓ | Marquer lu |
| `/notifications_clear` | POST | ✓ | ✓ | Effacer |
| `/notification_create` | POST | ✓ | ✓ | Créer notification |

### 3.10 Audit, conformité, revue humaine

| Endpoint | Méthodes | Auth | CSRF | Rôle |
|----------|----------|------|------|------|
| `/audit_reports` | GET, POST | ✓ | ✓ | Rapports d'audit |
| `/human_review` | GET, POST | ✓ | ✓ | Workflow revue humaine |
| `/replay` | GET, POST | ✓ | ✓ | Rejouer une requête |
| `/risk_dashboard` | GET, POST | ✓ | ✓ | Registre des risques |
| `/adversarial_list` | POST | ✓ | ✓ | Liste analyses adversariales |
| `/adversarial_analyze` | POST | ✓ | ✓ | Lancer analyse |
| `/adversarial_decide` | POST | ✓ | ✓ | Décision adversariale |
| `/adversarial_dossier` | POST | ✓ | ✓ | Dossier adversarial |

### 3.11 Divers

| Endpoint | Méthodes | Auth | API key | CSRF | Rôle |
|----------|----------|------|---------|------|------|
| `/health` | GET, POST | | | | Health API interne |
| `/synthesize` | POST | ✓ | | ✓ | Synthèse vocale |
| `/transcribe` | POST | ✓ | | ✓ | Transcription audio |
| `/tunnel` | POST | ✓ | | ✓ | Tunnel externe |
| `/tunnel_proxy` | POST | ✓ | | ✓ | Proxy tunnel |
| `/rfc` | POST | ✓ | ✓ | | RFC interne (désactivé en prod `KOREV_PRODUCTION=true`) |

---

## 4. Exemples

### 4.1 Connexion puis message

```bash
# 1. Connexion (cookie jar)
curl -c cookies.txt -X POST https://example.com/login \
  -d "username=user&password=secret"

# 2. Token CSRF
CSRF=$(curl -b cookies.txt -s https://example.com/csrf_token | jq -r .token)

# 3. Envoyer message
curl -b cookies.txt -X POST https://example.com/message \
  -H "Content-Type: application/json" \
  -H "X-CSRF-Token: $CSRF" \
  -d '{"text":"Bonjour","context_id":"<uuid>"}'
```

### 4.2 API key (intégration headless)

```bash
curl -X POST https://example.com/api_message \
  -H "X-API-KEY: $EVIDENCE_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"text":"Requête automatisée","context_id":"<uuid>"}'
```

### 4.3 Lister tâches scheduler

```bash
curl -b cookies.txt -X POST https://example.com/scheduler_tasks_list \
  -H "Content-Type: application/json" \
  -H "X-CSRF-Token: $CSRF" \
  -d '{}'
```

---

## 5. Autorisation multi-tenant

Les handlers héritant de `ApiHandler` appliquent `can_access_context()`, `can_access_task()` et `can_access_workspace()` (`python/security/authorization.py`) :

- **OWNER** : accès à tous les contextes de son organisation.
- **MEMBER** : accès uniquement à ses propres contextes.
- Isolation **inter-organisations** : étanche.

---

## 6. Rate limiting

Les routes API passent par `api_rate_limit` (`run_ui.py`). En cas de dépassement : HTTP 429. Voir variables `RATE_LIMIT_*` dans `deploy/.env`.

---

## 7. Implémentation

| Élément | Fichier |
|---------|---------|
| Enregistrement routes | `run_ui.py` → `register_api_handler()` |
| Classe de base | `python/helpers/api.py` → `ApiHandler` |
| Handlers | `python/api/*.py` (71 fichiers) |
| Auth session | `run_ui.py` + `python/security/` |

---

## Documents liés

- [GUIDE_CONFORMITE_CLIENT.md](GUIDE_CONFORMITE_CLIENT.md) — traçabilité côté client
- [connectivity.md](connectivity.md) — connexion externe (héritage Agent Zero)
- [INDEX_DOCUMENTATION.md](INDEX_DOCUMENTATION.md) — carte documentation
- [audit/critical_request_path_map.md](audit/critical_request_path_map.md) — chemin critique

---

*Référence API — KOREV Evidence v1.3.1. Dernière révision : 2026-06-13. Comptage vérifié : 71 handlers `python/api/`.*
