# Réponse à l'audit SonarQube — cabinet de valorisation (2026-06-04)

**Périmètre** : findings transmis par le cabinet sur le dépôt `PRISM-Oracle` (KOREV Evidence).
**Méthode** : triage sur pièce de chaque finding (vrai positif / faux positif), correction des
vrais positifs en TDD, neutralisation tracée et justifiée des faux positifs, puis audit hostile.

---

## 1. Synthèse exécutive

| Catégorie | Findings | Vrais positifs corrigés | Faux positifs neutralisés (tracés) |
|---|---:|---:|---:|
| `python:S2068` / `javascript:S2068` (credentials hard-coded) | ~30 | 1 (hash sorti du code) | ~29 (fixtures de test, placeholder UI, exemples) |
| `python:S6779` (Flask secret keys disclosed) — **BLOCKER** | 2 | 2 (corrigés à la source, secret éphémère) | 0 |
| `python:S2612` (file permissions world-accessible) | 2 | 2 | 0 |
| `Web:S5725` (remote artifacts sans intégrité) | 2 | 2 (+ 2 hors-liste corrigés) | 0 |

**Aucun secret réel n'était exposé** dans le code applicatif : le seul S2068 « réel » portait sur un
**hash** argon2id (non réversible), désormais sorti du code. Les S2612 et S5725 étaient de vrais
durcissements, corrigés.

---

## 2. Détail finding → verdict → action → preuve

### 2.1 `python:S2612` — File permissions should not be world-accessible (MAJOR) — **VRAI POSITIF**

| Emplacement | Verdict | Action | Preuve |
|---|---|---|---|
| `python/helpers/files.py:345,348` | Vrai positif (modéré) : `os.chmod(.., 0o777)` dans le fallback de suppression forcée → world-writable transitoire | `0o777` → **`0o700`** (droits propriétaire suffisants pour supprimer) | Test `tests/test_files_delete_perms.py` (force la branche, espionne `os.chmod`, exige `mode & 0o022 == 0`) — RED→GREEN |

### 2.2 `Web:S5725` — Remote artifacts without integrity (MINOR) — **VRAI POSITIF**

| Emplacement | Verdict | Action | Preuve |
|---|---|---|---|
| `webui/index.html:12`, `webui/login.html:11` | Vrai positif (mineur) : Google Fonts chargé sans contrôle d'intégrité (SRI impraticable sur `css2`, contenu variable) | **Auto-hébergement** des polices : woff2 latin/latin-ext téléchargés dans `webui/public/fonts/`, `@font-face` local (`korev-fonts.css`), `<link>` Google supprimés | Plus aucun `<link>` vers `fonts.googleapis.com` dans l'UI (grep) |
| *(hors liste, corrigés par cohérence)* `webui/components/welcome/welcome-screen.html:8`, `@import` dans `webui/index.css:1` (Rubik + Roboto Mono) | Mêmes dépendances externes | Localisées également (Rubik + Roboto Mono vendorisées) | grep : 0 appel Google Fonts dans l'UI servie |

> Bénéfice complémentaire : suppression de tout appel tiers au chargement de l'UI → **argument RGPD**
> (aucune fuite d'IP/UA vers Google au rendu). Provenance reproductible : `scripts/_vendor_fonts.py`.

### 2.2bis `python:S6779` — Flask secret keys should not be disclosed (BLOCKER)

| Emplacement | Verdict | Action | Preuve |
|---|---|---|---|
| `tests/test_scheduler_visibility.py:61,160` → `app.secret_key = "test-secret"` | Faux positif (secret FACTICE d'un Flask de **test**, aucune divulgation réelle) — mais sévérité BLOCKER | Corrigé **à la source** : `app.secret_key = os.urandom(16)` (secret éphémère, plus aucun littéral) | 3 tests verts ; grep confirme **aucun** `secret_key = "..."` hors `tests/`, donc **aucun secret Flask en dur en code de prod** |

> Choix : suppression du littéral à la source plutôt qu'exclusion Sonar — un BLOCKER doit
> disparaître, pas être masqué. Les autres tests passent le secret via `create_app(secret_key=...)`
> (non flaggé par S6779) ; ils restent couverts par la règle S2068 ci-dessous.

### 2.3 `python:S2068` / `javascript:S2068` — Credentials hard-coded (MAJOR)

#### a) Vrai positif (corrigé)

| Emplacement | Verdict | Action | Preuve |
|---|---|---|---|
| `scripts/add_tarmac_user.py:17` | Hash **argon2id** (non réversible) d'un compte réel, codé en dur | Hash lu depuis l'env `TARMAC_PASSWORD_HASH` ; **fail-closed** si absent ou si ce n'est pas un hash argon2 | `tests/test_add_tarmac_user_no_hardcoded_secret.py` (4 cas : absence de hash en dur, fail si absent, rejet du clair, accepte argon2) |

#### b) Faux positifs (neutralisés, tracés dans `sonar-project.properties`)

| Emplacement | Pourquoi faux positif |
|---|---|
| `python/helpers/settings.py:198` | `PASSWORD_PLACEHOLDER = "****PSWD****"` — masque d'affichage UI, pas un secret |
| `python/helpers/settings.py:1393` | Exemple `EMAIL_PASSWORD="..."` dans un **libellé d'aide** de l'UI |
| `webui/components/settings/secrets/example-secrets.html` | Fichier d'**exemple** de la doc UI |
| `tests/**` (plusieurs fichiers : `test_multi_user_auth`, `test_login_rate_limit_e2e`, `test_multi_tenant_security`, `test_multi_user_e2e`, `test_multi_user_flask`, `test_dump_restore_pipeline`, `infra/test_postgres_compose`, `security/test_session_scope_resolution`) | **Fixtures de test** avec valeurs FACTICES (ex. `"plaintext_not_hashed"`, `secret_key="test-secret"`), requises par les tests d'authentification |

> Neutralisation **non silencieuse** : règles `sonar.issue.ignore.multicriteria` documentées avec motif
> dans `sonar-project.properties`. Les fichiers de test restent analysés pour toutes les autres règles.

---

## 3. Fichiers livrés / modifiés

| Fichier | Nature |
|---|---|
| `tests/test_scheduler_visibility.py` | fix S6779 BLOCKER (secret Flask éphémère) |
| `python/helpers/files.py` | fix S2612 (0o700) |
| `tests/test_files_delete_perms.py` | test régression S2612 (créé) |
| `scripts/add_tarmac_user.py` | fix S2068 (hash via env) |
| `tests/test_add_tarmac_user_no_hardcoded_secret.py` | test régression S2068 (créé) |
| `webui/index.html`, `webui/login.html`, `webui/components/welcome/welcome-screen.html`, `webui/index.css` | fix S5725 (polices locales) |
| `webui/public/fonts/*.woff2` + `korev-fonts.css` | polices auto-hébergées (créé) |
| `scripts/_vendor_fonts.py` | outil de provenance/regénération des polices (créé) |
| `sonar-project.properties` | neutralisation tracée des faux positifs (créé) |

---

## 4. Vérification post-correction recommandée

1. Re-lancer le scan SonarQube : attendu **0 finding non traité** (vrais positifs corrigés, FP ignorés avec motif).
2. Contrôle visuel UI (login + chat) : typographie inchangée (polices locales).
3. CI tests verts (dont les 2 nouveaux fichiers de régression).
