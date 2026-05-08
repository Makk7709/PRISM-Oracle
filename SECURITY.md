# Politique de securite — KOREV Evidence

## Perimetre

Cette politique couvre l'ensemble des composants du depot KOREV Evidence :
- Backend Python (Flask, agents, helpers, extensions, API)
- Module `python/security/` (authentification, autorisation, rate limiting, validation)
- Infrastructure de deploiement (Docker, Caddy, scripts)
- Pipeline d'integrite (HMAC, RSA, SessionEnvelope)
- Serveurs MCP integres

## Signalement de vulnerabilites (divulgation responsable)

Si vous decouvrez une vulnerabilite de securite dans KOREV Evidence, merci de la signaler de maniere responsable.

**Contact :** security@korev.ai

**Processus :**
1. Envoyez un rapport detaille a l'adresse ci-dessus.
2. Incluez : description de la vulnerabilite, etapes de reproduction, impact potentiel.
3. Ne publiez pas la vulnerabilite avant resolution.

**Engagement de reponse :**
- Accuse de reception sous 48 heures ouvrees.
- Evaluation de severite sous 5 jours ouvres.
- Correctif ou plan de remediation sous 15 jours ouvres pour les severites critiques et elevees.

Nous ne poursuivrons pas les chercheurs en securite agissant de bonne foi dans le cadre de cette politique.

## Pratiques de securite implementees

### Authentification

- Hachage des mots de passe avec **Argon2id** (variante recommandee par OWASP).
- Parametres : `time_cost=3`, `memory_cost=65536` (64 Mo), `parallelism=4`.
- Verification en temps constant (protection contre les attaques par timing).
- La fonction `verify_password()` effectue une operation factice meme en cas d'echec precoce pour maintenir un temps d'execution constant.
- Variables d'environnement : `AUTH_LOGIN`, `AUTH_PASSWORD`.

### Gestion des secrets

Aucun secret par defaut n'est embarque dans le code. L'absence de la variable `EVIDENCE_HMAC_KEY` provoque un `RuntimeError` au demarrage, empechant toute signature d'integrite avec une cle non configuree.

Variables sensibles requises :
- `EVIDENCE_HMAC_KEY` — Cle HMAC pour la signature des rapports d'audit (minimum 32 caracteres recommandes). Son absence provoque une erreur fatale (`RuntimeError`).
- `FLASK_SECRET_KEY` — Cle de session Flask.
- `API_KEY_*` — Cles des fournisseurs LLM (OpenRouter, OpenAI, Anthropic, Google).

Toutes les variables sensibles sont documentees dans `.env.example` et `deploy/.env.example`.

### Integrite cryptographique

- Rapports d'audit signes avec **HMAC-SHA256** (obligatoire) ou **RSA-PSS-SHA256** (optionnel).
- Chaque document produit un `IntegrityBlock` contenant : hash de la requete (SHA-256), hash de la reponse (SHA-256), hash du document, signature HMAC ou RSA, horodatage UTC.
- Versionnement de la cle HMAC via `EVIDENCE_HMAC_KEY_VERSION`.

### Protection contre les attaques par force brute (rate limiting)

- Rate limiting configurable avec deux backends : memoire locale et Redis distribue.
- Points d'application : `/login` (authentification) et API generales.
- Mode de degradation configurable (`KOREV_RATE_LIMIT_FAIL_MODE`) : `fail-open` ou `fail-closed`.
- Backoff exponentiel configurable sur les tentatives de connexion.
- Variables : `RATE_LIMIT_LOGIN_MAX`, `RATE_LIMIT_LOGIN_WINDOW`, `RATE_LIMIT_API_MAX`, `RATE_LIMIT_API_WINDOW`.

### Validation des entrees

- **Chemins** : `safe_path_join()` bloque les traversees de repertoire (`..`), les liens symboliques sortants et les chemins hors du repertoire de base.
- **Uploads** : validation de l'extension (liste blanche), de la taille (`MAX_UPLOAD_SIZE`), et du type MIME.
- **Commandes shell** : liste blanche de commandes autorisees, interdiction des metacaracteres shell, execution par liste d'arguments (jamais `shell=True`).

### Autorisation multi-tenant

- Modele base sur `AccessPrincipal` : utilisateur, organisation, role, workspace.
- Isolation stricte entre organisations (`normalize_org_id()` pour les comparaisons).
- Acces aux rapports d'audit (`audit_reports`) restreint aux roles : `OWNER`, `DPO`, `RSSI`, `COMPLIANCE_OFFICER`.
- Protection CSRF sur les endpoints mutatifs.

### Specification formelle

Le module `python/security/__init__.py` contient une specification Gherkin (Given/When/Then) couvrant :
- Hachage et verification de mots de passe
- Rate limiting
- Validation de chemins (traversal)
- Validation d'uploads
- Securite des commandes shell

Cette specification sert de contrat verifie par la suite de tests (`tests/test_security_*.py`).

## Architecture de securite

```
Internet → Caddy (TLS auto) → Flask (5050, non expose)
                                  ├── Rate Limiter (Redis/memoire)
                                  ├── Auth (Argon2id)
                                  ├── RBAC (AccessPrincipal)
                                  ├── Path/Upload/Shell validation
                                  └── IntegrityBlock (HMAC/RSA)
```

- Le port Flask (5050) n'est pas publie directement sur l'hote.
- Caddy gere le TLS automatique et le reverse proxy.
- L'utilisateur dans le conteneur Docker est non-root.
- Les volumes Docker sont nommes avec labels de backup.

## Limites connues et axes d'amelioration

- **Mode sans authentification** : lorsqu'aucune configuration d'authentification n'est fournie (`AUTH_LOGIN` absent, pas de `users.json`), le serveur demarre sans protection. Ce comportement est documente mais constitue un risque en deploiement non surveille.
- **Masquage de secrets fail-open** : les extensions de masquage (`_10_mask_secrets.py`) utilisent `except Exception: pass`, ce qui peut laisser passer des secrets en cas d'erreur dans le masquage.
- **Comparaison de cle API** : la comparaison de cle API dans certains endpoints n'utilise pas `hmac.compare_digest()`.
- **Browser agent** : l'agent navigateur utilise `disable_security=True` pour Playwright.

Ces points sont documentes dans l'audit hostile interne (livrable 03) et font l'objet du plan de remediation P1-P2 (livrable 06).

## Versions et mises a jour

| Date | Version | Changements |
|------|---------|-------------|
| 3 avril 2026 | 1.0 | Corrections P0 : licence, HMAC RuntimeError, logs, RBAC |
| 17 avril 2026 | 1.1 | Creation de cette politique de securite |
