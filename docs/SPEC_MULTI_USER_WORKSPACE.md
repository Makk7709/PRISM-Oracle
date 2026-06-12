# PROMPT DE CONTRÔLE STRICT — Multi-User Workspace & Dossiers Partagés

## Classification : SPÉCIFICATION TECHNIQUE CONTRAIGNANTE

## Statut : À VÉRIFIER PAR TESTS AUTOMATISÉS

---

## RÈGLES ABSOLUES (violation = test RED = build cassé)

### R1 — MULTI-AUTH OBLIGATOIRE

- Le système DOIT supporter N utilisateurs avec chacun son login/password
- Les utilisateurs sont définis dans `deploy/users.json` (pas dans .env)
- Chaque mot de passe DOIT être un hash Argon2id ($argon2id$...)
- Un plaintext password en production DOIT être REFUSÉ (erreur 500)
- Format `users.json` :

  ```json
  {
    "users": {
      "nicolas":  {"password_hash": "$argon2id$...", "role": "user"},
      "luc":      {"password_hash": "$argon2id$...", "role": "user"},
      "amine":    {"password_hash": "$argon2id$...", "role": "admin"}
    }
  }
  ```

- Rétro-compatibilité : si `users.json` n'existe pas, fallback sur AUTH_LOGIN/AUTH_PASSWORD (mode mono-user)

### R2 — SESSION IDENTIFIÉE

- Après login, `session['username']` DOIT contenir le nom d'utilisateur
- `session['role']` DOIT contenir le rôle (`user` ou `admin`)
- `session['workspace']` DOIT contenir le chemin absolu du workspace utilisateur
- Un accès API sans session valide DOIT retourner 401/redirect

### R3 — ISOLATION STRICTE DES WORKSPACES

- Chaque utilisateur a un répertoire : `{SHARED_ROOT}/users/{username}/`
- Structure par utilisateur :

  ```json
  {SHARED_ROOT}/users/{username}/
  ├── documents/     ← l'utilisateur dépose ses fichiers ici
  ├── rapports/      ← Evidence dépose les résultats ici
  └── tmp/           ← fichiers temporaires Evidence
  ```

- Un dossier commun existe : `{SHARED_ROOT}/commun/`
- `SHARED_ROOT` est configurable via `EVIDENCE_SHARED_DIR` (défaut : `/app/shared`)

### R4 — INTERDICTION DE TRAVERSÉE

- Un utilisateur NE PEUT JAMAIS lire/écrire en dehors de :
  1. Son propre workspace `{SHARED_ROOT}/users/{username}/`
  2. Le dossier commun `{SHARED_ROOT}/commun/` (lecture + écriture)
- Toute tentative de path traversal (`../`, symlinks, etc.) DOIT être REJETÉE
- Même si l'IA le demande via code_execution_tool, le système REFUSE

### R5 — FILE WRITER SCOPÉ

- `file_writer` DOIT écrire dans `{workspace}/rapports/` par défaut
- Le chemin de sortie DOIT être validé contre R4
- Le fichier résultant DOIT être accessible via l'URL de téléchargement

### R6 — CODE EXECUTION SCOPÉ

- `code_execution_tool` DOIT avoir son CWD dans `{workspace}/`
- Les scripts Python ont accès en lecture à `{workspace}/` et `{SHARED_ROOT}/commun/`
- Les scripts Python ont accès en écriture à `{workspace}/` uniquement
- Le tool NE DOIT PAS pouvoir exécuter `os.chdir()` vers un dossier hors workspace

### R7 — ADMIN VOIT TOUT

- Un utilisateur avec `role: admin` PEUT accéder à tous les workspaces
- L'admin PEUT lister les utilisateurs et leurs fichiers
- L'admin PEUT créer/supprimer des utilisateurs

### R8 — AUDIT TRAIL

- Toute opération fichier (lecture/écriture/suppression) DOIT être loguée avec :
  - `timestamp`, `username`, `operation`, `path`, `success/failure`
- Le log est dans `{SHARED_ROOT}/audit/file_operations.jsonl`

### R9 — DOCKER & SMB

- Le docker-compose DOIT monter `EVIDENCE_SHARED_DIR` comme volume
- Un container Samba DOIT exposer le volume en SMB avec :
  - Authentification par utilisateur (mêmes logins que Evidence)
  - Isolation : chaque utilisateur ne voit que son dossier + commun
  - Port 445 exposé sur le LAN

### R10 — RÉTRO-COMPATIBILITÉ

- Si `users.json` n'existe pas → mode mono-user (AUTH_LOGIN/AUTH_PASSWORD)
- Si `EVIDENCE_SHARED_DIR` n'est pas défini → pas de workspace, comportement actuel
- Aucune fonctionnalité existante ne doit être cassée

---

## MATRICE DE TESTS OBLIGATOIRES

| ID | Test | Type | Règle |
|----|------|------|-------|
| T01 | Login avec user valide → session contient username | Unit | R1, R2 |
| T02 | Login avec user invalide → rejeté | Unit | R1 |
| T03 | Login avec plaintext password en prod → erreur 500 | Unit | R1 |
| T04 | Fallback mono-user si pas de users.json | Unit | R10 |
| T05 | Workspace créé au premier login | Unit | R3 |
| T06 | Workspace contient documents/ rapports/ tmp/ | Unit | R3 |
| T07 | User ne peut pas lire hors de son workspace | Unit | R4 |
| T08 | User ne peut pas écrire hors de son workspace | Unit | R4 |
| T09 | Path traversal `../` rejeté | Unit | R4 |
| T10 | Symlink vers dossier externe rejeté | Unit | R4 |
| T11 | User peut lire/écrire dans commun/ | Unit | R3, R4 |
| T12 | file_writer écrit dans {workspace}/rapports/ | Unit | R5 |
| T13 | code_execution CWD = workspace | Unit | R6 |
| T14 | code_execution ne peut pas os.chdir() hors workspace | Unit | R6 |
| T15 | Admin peut accéder à tous les workspaces | Unit | R7 |
| T16 | Opération fichier loguée dans audit | Unit | R8 |
| T17 | Volume Docker monté correctement | Integ | R9 |
| T18 | 2 users simultanés, workspaces isolés | E2E | R3, R4 |
| T19 | User upload fichier → Evidence le lit → génère rapport | E2E | R3, R5 |
| T20 | Rétro-compatibilité mono-user préservée | E2E | R10 |

---

## CRITÈRE DE VALIDATION FINALE

Tous les tests T01-T20 DOIVENT être GREEN.
Un seul test RED = livraison REFUSÉE.
