# 05 — Snapshot qualite code

**Projet** : KOREV Evidence
**Apporteur / inventeur** : Amine Mohamed
**HEAD analyse** : `fab5689a` (5 mai 2026)
**Methode** : analyse factuelle des artefacts du depot, sans modification
**Date** : 9 mai 2026

> Ce document fournit une note qualitative defendable de la qualite du code. Il assume les forces et les faiblesses. Un risque assume vaut mieux qu'un risque decouvert par Diag & Grow.

---

## 1. Tests disponibles

### 1.1 Volume

| Metrique | Valeur | Source |
|---|---:|---|
| Fichiers de test | **183** | `D_volumetrie_code.txt` (28 avril) |
| Lignes de tests | **68 279** | `D_volumetrie_code.txt` |
| Tests collectes (pytest --collect-only) | **3 956** | `A11_pytest_collect_only.txt` |
| Plugins pytest | asyncio, langsmith, typeguard, jaxtyping, zarr, cov | header pytest |
| Tests qualite documentation (PASSED) | 64 / 64 en 4.32s | `B_pytest_doc_quality.txt` |

> **Note post-25 avril** : la capture `A11_pytest_collect_only.txt` date du 28 avril 2026. Les 3 commits posterieurs ancetres de `fab5689a` (`de8b9c7e`, `b11b4d99`, `0d0a35da`, cf. `audit-hostile-valorisation/09-mise-a-jour-post-p0-yenoyikz.md`) ajoutent **+35 tests** : 28 tests `tests/security/test_file_writer_includes_*.py` + 4 tests integration / regression (yENoyKIZ), 6 tests `tests/infra/test_postgres_compose.py` (T1-T6 P0 RDBMS), 1 test `tests/infra/test_dump_restore_pipeline.py` (T7 backup/restore). Une re-execution de `pytest --collect-only -q tests/` sur HEAD `fab5689a` est attendue a **~3 991 tests**. Le chiffre 3 956 est conserve comme reference auditable jusqu'a la nouvelle capture A11.

### 1.2 Categories de tests presentes

| Categorie | Exemples |
|---|---|
| Tests unitaires | `test_consensus_simple.py`, `test_router*.py`, `test_metacognition.py` |
| Tests d'integration | `test_legal_pipeline.py`, `test_adversarial_integration.py` |
| Tests E2E | `test_adversarial_e2e_scenarios.py`, `test_e2e_audit_proof*.py` |
| Tests de proprietes | invariants metacognition (monotonie, no-PII), tests de proprietes consensus |
| Tests adversarial / hostile | `test_adversarial_*.py`, `test_hostile_hardening*.py` (203 lignes dediees) |
| Golden tests | `tests/golden/pdf_extraction/` (tables, words, unicode) ; `tests/golden/legal/` |
| Tests securite | `tests/security/` avec seuil 90% en CI |
| Tests qualite documentation | `test_documentation_quality.py` (64 tests TDD) |

### 1.3 Harness de test (qualite professionnelle)

- **FakeLLMProvider** : simule les reponses LLM sans appel reel
- **FakeMCPHandler** : simule les serveurs MCP
- **Network Guard ACTIVE par defaut** : bloque les appels reseau LLM (preuve du log header pytest)
- **Strict Fixtures** : disabled par defaut (configurable)
- **Record Mode** : disabled par defaut (configurable)
- **Redis multi-worker proof** : tests dedies pour la coherence multi-worker du rate limiter

### 1.4 Limites assumees (tests)

- **Suite etendue non-bloquante en CI** (`continue-on-error: true` sur `extended-tests` dans `main_gate.yml`) — P1-3 ouvert.
- **Couverture globale non mesuree** : `--cov` non active sur la CI principale. Le rapport coverage existe localement (`.coverage`) mais n'est pas publie. P1-4 ouvert.
- **~50 endpoints API sans test dedie** : couverture API partielle.
- **Tests fonctionnels sur LLM reel non automatises** : volontaire (cout, network guard) ; les tests reels sont declenches manuellement ou en CI separee.

---

## 2. Workflows CI

### 2.1 Trois workflows operationnels

| Workflow | Trigger | Periimetre | Statut |
|---|---|---|---|
| `legal_pipeline_ci.yml` | push, PR | Tests pipeline juridique (Legal-Safe) | Operationnel |
| `main_gate.yml` | push, PR | Gate principal : tests core + extended | Operationnel (extended non-bloquant) |
| `security_ci.yml` | push, PR | Tests securite avec seuil de couverture 90% | Operationnel et **bloquant** |

### 2.2 Limites assumees (CI)

- **Pas de build Docker en CI** : l'image est construite directement sur le serveur. P1-5 ouvert.
- **Pas de SAST / scanning de dependances** : ni Dependabot, ni CodeQL, ni `pip-audit`. P2-4 ouvert.
- **Pas de deploiement automatise (CD)** : deploiement manuel via `scripts/install.sh` / `upgrade.sh`.
- **Pas de signature des artefacts CI** : ni cosign, ni in-toto.

---

## 3. Scripts

`scripts/` contient ~41 scripts (~8 834 LOC cumulees) :

- **Installation client** : `install-windows.bat`, `install-mac.sh`
- **Production install / upgrade** : `install.sh`, `upgrade.sh`
- **Provisioning multi-tenant** : `provision_*.py`, `add_*_user.py`
- **Migrations / refactoring** : `migrate_*.py`, scripts P0 corrections
- **Validation production** : `router_prod_validation.py`, `pre_deploy_validation*.py`
- **Smoke tests / diagnostics** : `tools/smoke_test.py`, `tools/diagnostics_*.py`
- **Backup / restore** : scripts dedies dans `scripts/backup_*.sh`, `scripts/restore_*.sh`

### Limites assumees (scripts)

- **Scripts `install.sh` / `upgrade.sh` utilisent `127.0.0.1:5050`** alors que le port 5050 n'est pas publie sur l'hote par defaut (Caddy proxy). Incoherence documentee dans audit hostile (point 4 du chapitre 4.4 de `02-cartographie-technique.md`).
- **Scripts non testes systematiquement** : pas de framework de test bash systematique.

---

## 4. Securite

### 4.1 Forces

| Force | Preuve |
|---|---|
| Argon2id pour les mots de passe | `python/security/auth.py`, SECURITY.md |
| Cle HMAC obligatoire (corrige P0) | `integrity_block.py` leve `RuntimeError` si `EVIDENCE_HMAC_KEY` absent |
| Rate limiting Redis + memoire | `rate_limiter.py`, `python/security/rate_limit.py` |
| Path safety, upload validation, shell safety | `python/security/path_safety.py`, `upload_safety.py`, `shell_safety.py` |
| Autorisation multi-tenant par principal | `python/security/authorization.py` |
| Security audit logging | `python/security/audit.py` |
| CSRF sur API mutantes | implementation dans `python/api/` |
| Isolation workspace | `user_manager.py`, `deploy_config.py` |
| Specifications Gherkin dans `security/__init__.py` | preuve de doctrine |
| SECURITY.md (politique divulgation, pratiques crypto, perimetre) | racine du depot, 6 582 octets |
| 4 failles P0 corrigees (commit `40808223` du 3 avril 2026) | trace Git verifiable |

### 4.2 Faiblesses assumees

| Faiblesse | Decote estimee | Mitigation |
|---|---|---|
| Mode sans authentification quand `AUTH_LOGIN` et `users.json` absents | Modere (P1-6) | Documente dans SECURITY.md ; correction prevue (3h) |
| Masquage de secrets fail-open (`except: pass`) dans certaines extensions | Faible (P2-8) | Correction prevue (2h) |
| Browser agent `disable_security=True` | Faible | Documente, periimetre limite |
| Comparaison cle API non constante (timing attack theorique) | Faible | A corriger en P2 |
| RSA optionnel pour signatures Evidence | Faible | HMAC-SHA256 toujours actif |
| Pas de WORM pour les traces audit | Modere | ADR-007 livre (5 mai 2026) avec P0 RDBMS execute (Postgres + pgvector compose staging actif) ; phases P1-P6 planifiees pour la migration progressive de la persistance |
| Pas d'audit penetration externe | Modere | A annexer (AE-10) si rapport disponible |

---

## 5. Documentation

### 5.1 Forces

| Force | Volume |
|---|---|
| Total documentation proprietaire | 148 fichiers diff, +27 675 lignes (delta upstream -> HEAD) |
| Guide onboarding developpeur | `DEVELOPER_ONBOARDING_ARCHITECTURE_GUIDE.md` (1 196 lignes, mis a jour avril 2026) |
| Guide deploiement entreprise | `GUIDE_DEPLOIEMENT_ENTREPRISE.md` (1 385 lignes) |
| Feuille de route conformite | `FEUILLE_DE_ROUTE_CONFORMITE_FORMAT_EVIDENCE.md` (1 893 lignes) |
| 7 ADR dans `docs/adr/` | PRISM, router, Evidence, LiteLLM, extensions, tool I/O, Postgres |
| GLOSSARY | `docs/GLOSSARY.md` (30+ termes proprietaires definis) |
| Diagrammes C4 (3 niveaux + sequence) | `docs/ARCHITECTURE_C4_DIAGRAMS.md` (Mermaid) |
| SECURITY.md racine | Politique divulgation, perimetre, pratiques crypto |
| Benchmark comparables marche | `docs/BENCHMARK_COMPARABLES_VALORISATION_EVIDENCE.md` (335 lignes) |
| Audit hostile interne | 8 livrables + mise a jour (dossier `audit-hostile-valorisation/`) |
| Preuves d'execution reproductibles | Annexes A11 / A12 dans `docs/preuves-execution/` |
| 64 tests TDD validant la documentation | `tests/test_documentation_quality.py` (PASSED) |
| Rapport technique de valorisation | `docs/RAPPORT_TECHNIQUE_VALORISATION_EVIDENCE.md` (1 100+ lignes) |
| Dossier commissaire d'apports | `docs/DOSSIER_COMMISSAIRE_APPORTS_EVIDENCE.md` |

### 5.2 Faiblesses assumees

| Faiblesse | Decote estimee | Mitigation |
|---|---|---|
| Pas de schema de donnees formel | Modere (P2-5) | A produire (1-2 jours) |
| Pas d'API reference (OpenAPI / Swagger) | Modere | A produire |
| Melange FR / EN | Faible | Acceptable pour un public francais |
| Doublons (`tmp/uploads/` vs `docs/`) | Faible | A nettoyer (P2-7) |
| Pas d'historique d'incidents / postmortems | Faible | A produire si incidents avec valeur |
| Pas de benchmarks de performance | Faible-modere | A produire si pertinent commercialement |

---

## 6. ADR

### 6.1 Etat actuel

| ADR | Sujet | Date |
|---|---|---|
| ADR-001 | Consensus PRISM multi-arbitres | 17 avril 2026 |
| ADR-002 | Router deterministe anti-injection | 17 avril 2026 |
| ADR-003 | Framework Evidence audit / integrite | 17 avril 2026 |
| ADR-004 | LiteLLM abstraction multi-LLM | 17 avril 2026 |
| ADR-005 | Extension hooks cycle de vie | 17 avril 2026 |
| ADR-006 | Tool I/O integrity contract | **Livre 4 mai 2026** (commit `de8b9c7e`) |
| ADR-007 | Postgres pgvector adoption | **Livre 5 mai 2026** (commit `b11b4d99`) — P0 execute runtime, P1-P6 planifiees |

Chaque ADR contient : date, statut, contexte, decision detaillee, consequences (positives + negatives), alternatives rejetees avec justification.

21 tests TDD valident la presence et la coherence des ADR (cf. `tests/test_documentation_quality.py`).

**ADR-006 — Tool I/O integrity contract (4 mai 2026)** : formalise le contrat d'integrite I/O des tools applicatifs. Tout tool qui ecrit un artefact sur disque DOIT respecter : atomicite des transformations, fail-loud sur entree corrompue, message d'erreur exploitable par l'agent, reflet exact du systeme de fichiers, observabilite. Il acte la correction du pattern fail-silent revele par la session yENoyKIZ (4 mai 2026), ou un PDF de 25 KB avait ete produit avec succes apparent alors que son contenu utile etait la chaine litterale `§§include(/app/tmp/...)` non resolue. La correction verrouille `python/tools/file_writer.py` en resolution atomique des directives `§§include` AVANT toute ecriture, et est garantie par 28 tests dedies (`tests/security/test_file_writer_includes_*.py`, `tests/integration/test_file_writer_pdf_integrity.py`, `tests/regression/test_session_yenoyikz_repro.py`). Source : `audit-hostile-valorisation/09-mise-a-jour-post-p0-yenoyikz.md` section 3.

**ADR-007 — Postgres + pgvector adoption (5 mai 2026)** : acte l'adoption de PostgreSQL 16 + pgvector comme socle de persistance metier en remplacement progressif du schema `filesystem-first` (`users.json`, `tmp/chats/`, `memory/users/<user>/default/index.faiss`, `data/legal/index/legal_index.sqlite`, `audit/<...>/`). Roadmap structuree en 7 phases sur 4-6 mois ; **P0 deja livre runtime le 5 mai 2026** : compose staging autonome (`deploy/docker-compose.staging.yml`, project name verrouille `evidence-staging`, port 5433 localhost), service `evidence-postgres` derriere `profiles: ["db"]` dans le compose de prod (zero-impact, aucun service applicatif n'a `depends_on` Postgres en P0), 5 schemas `identity / chats / memory / audit / legal`, 7 tests d'infra (T1-T6 + T7), scripts `snapshot_pre_migration.sh`, `pg_dump_daily.sh` et `pg_restore_from_dump.sh` (fail-loud), snapshot prod pre-P0 immutable conserve sur le VPS OVH. Phases P1-P6 (Repository, sessions chat, memoire vectorielle, artefacts audit, legal, decommissioning) **planifiees**, non encore executees. La preoccupation H-4 (signatures audit invalidees par migration) a ete levee par audit cible : le payload signe par `replay_engine.compute_integrity()` et `integrity_block._build_sign_payload()` ne contient que des hashes de contenus, jamais de chemin filesystem. Source : `audit-hostile-valorisation/09-mise-a-jour-post-p0-yenoyikz.md` section 4.

---

## 7. Type checking et lint

### 7.1 Type checking

- **typeguard** est present dans la suite pytest (cf. plugins charges au header).
- **typing** standard utilise dans la majorite des modules critiques (consensus, evidence, security).
- Pas de `mypy --strict` en CI a date (peut etre considere comme P2).

### 7.2 Lint

- Pas de `ruff` ou `flake8` en CI bloquant a date (peut etre considere comme P2).
- `cspell.json` present a la racine pour le spellcheck.

### 7.3 Limites assumees

| Faiblesse | Decote estimee | Mitigation |
|---|---|---|
| Pas de `mypy --strict` en CI | Modere | A activer en P2 |
| Pas de `ruff` / `flake8` bloquant | Faible | A activer en P2 |
| Lint cosmetique heterogene (emojis dans certains logs, code commente non nettoye) | Faible | P2-7 |

---

## 8. Docker

### 8.1 Forces

- **Multi-stage build** Python 3.11-slim + Node.js 20 (`deploy/Dockerfile.backend`, 224 LOC)
- **Image autonome** (pas de base image externe specifique sauf python:3.11-slim official)
- **Healthchecks** Docker (180s start, 30s interval)
- **Non-root user** dans le container
- **Log rotation Docker** configuree
- **Volumes nommes** avec labels de backup
- **Caddy reverse proxy** avec TLS automatique (`deploy/config/Caddyfile`, 91 LOC)
- **Validation syntaxe** : `docker compose config --quiet` exit code 0 (warnings non bloquants sur `$` dans hashes Argon2id)
- **PRISM PDF engine reecrit** : WeasyPrint + ReportLab (avril 2026)
- **Docker Playwright/Chromium ameliore** pour Debian trixie

### 8.2 Faiblesses assumees

| Faiblesse | Decote estimee | Mitigation |
|---|---|---|
| Pas de build Docker en CI | Modere (P1-5) | A activer (3h) |
| Dual Docker non reconcilie (`deploy/` vs `DockerfileLocal`+`docker/`) | Faible | A archiver (P2-7) |
| Build manuel sur le serveur de production | Modere | A automatiser via CI/CD |
| Pas de registre d'images versionne | Modere | A configurer (private registry ou GHCR) |

---

## 9. Deploiement

### 9.1 Forces

- Docker Compose production fonctionnel
- Caddy reverse proxy avec TLS auto
- Scripts de rollback documentes (`scripts/rollback_*.sh`)
- Polices professionnelles integrees (Inter, Playfair Display)
- Healthcheck endpoints (`healthz`, `readyz`)
- Provisioning multi-tenant (`scripts/provision_*`)

### 9.2 Faiblesses assumees

- Scripts `install.sh` / `upgrade.sh` incoherents avec la config par defaut (port 5050)
- Pas de CD (deploiement manuel)
- Pas de monitoring / alerting integre au repo (Prometheus / Grafana / Sentry absents)
- Deux `.env.example` (a unifier)

---

## 10. Logs / observability

### 10.1 Forces

- **Structured logs** dans les modules critiques
- **Security audit log** structure (`python/security/audit.py`)
- **Metriques de routage** (`router/metrics.py`, 316 LOC) : divergence_rate, would_block, latency
- **Error rate-limiting** (60s cooldown)
- **Log EXECUTION_ABORTED_BY_ROUTER** explicite

### 10.2 Faiblesses assumees

- Pas de Prometheus / Grafana / OpenTelemetry integre au repo
- Pas de tracing distribuee
- Logs locaux uniquement (pas de push vers SIEM)

---

## 11. Audit trail

### 11.1 Forces

- **IntegrityBlock** : SHA-256 + HMAC obligatoire + RSA optionnel
- **SessionEnvelope** avec metadonnees completes
- **ComplianceGrid** : AI Act articles 9, 13, 14, 17 + RGPD article 30
- **Evidence reports** : 10 blocs canoniques
- **Replay engine** : rejeu deterministe de sessions (avril 2026)
- **Human review workflow** : approbation/rejet/escalade (avril 2026)
- **Dynamic Risk Register** : scoring temps reel (avril 2026)

### 11.2 Faiblesses assumees

- **RSA optionnel** : depend de la configuration
- **Pas de stockage WORM** pour les traces
- **Auto-evaluation conformite** : pas de validation externe (attenuee par audit-proof, mais subsiste)
- **Migration Postgres / pgvector partielle** : ADR-007 livre 5 mai 2026 ; **P0 execute runtime** (compose staging actif sur VPS, 5 schemas crees, 7 tests d'infra T1-T6 + T7 verts) ; **P1-P6 planifiees** (Repository, sessions chat, memoire vectorielle, artefacts audit, legal, decommissioning) sur 4-6 mois. Aucun service applicatif ne depend de Postgres en P0 (zero-impact prod).

### 11.3 Doctrine fail-loud / fail-hard renforcee (4-5 mai 2026)

ADR-006 (Tool I/O integrity contract) et le fix DEF-8 (`pg_restore_from_dump.sh` avec `psql --set ON_ERROR_STOP=1`, `pg_dump --clean --if-exists`, verification SHA-256 contre `MANIFEST.sha256`) etendent la doctrine fail-loud / fail-hard a deux nouvelles surfaces :

- **Tools applicatifs ecrivant sur disque** (file_writer, pipeline PDF) : resolution atomique avant ecriture, levee d'`IncludeResolutionError` si une directive `§§include` ne peut etre resolue, message d'erreur exploitable par l'agent (cf. `python/tools/file_writer.py`).
- **Pipeline backup / restore Postgres** : test T7 `tests/infra/test_dump_restore_pipeline.py` pose un marker APRES l'init script du conteneur, dump, `down -v`, `up` neuf, restore, et **verifie que le marker post-init est present**. Cycle complet chronometre a 15 secondes (sous le seuil Go/No-Go P0 → P1 de 30 minutes).

Les deux corrections sont des **defenses renforcees** contre le pattern fail-silent identifie dans la session yENoyKIZ (PDF de 25 KB avec contenu non resolu) et dans le test runtime DEF-8 (restore semblant termine alors qu'une ligne `korev_init_marker` post-init n'avait pas ete restauree). **Aucune perte de donnees reelle dans aucun des deux cas** (yENoyKIZ : PDF regenere a 259 KB, ratio recovery 126.7% ; DEF-8 : detecte avant tout cron actif en prod, le cron file etant livre avec suffixe `.disabled`).

---

## 12. Backup / restore

### 12.1 Forces

- Volumes nommes Docker avec labels de backup
- Scripts `backup_*.sh` / `restore_*.sh` documentes
- Doctrine fail-loud sur les operations de backup critiques

### 12.2 Faiblesses assumees

- Pas de validation automatique de restauration
- Pas de test de "disaster recovery" automatise
- Pas de chiffrement automatique des backups

---

## 13. Limites actuelles (synthese)

> Cf. `06_KNOWN_LIMITS_AND_REMEDIATION.md` pour le detail complet et le plan de remediation par limite.

| # | Limite | Severite | P0/P1/P2 | Statut |
|---|---|---|---|---|
| 1 | Suite etendue non-bloquante en CI | Modere | P1-3 | Ouvert |
| 2 | Couverture globale non mesuree | Modere | P1-4 | Ouvert |
| 3 | Pas de build Docker en CI | Modere | P1-5 | Ouvert |
| 4 | Mode sans authentification par defaut | Modere | P1-6 | Ouvert |
| 5 | Modules monolithiques (settings.py, etc.) | Modere | P2-1 | Ouvert |
| 6 | Duplications conceptuelles (consensus 3 chemins) | Faible | P2-2 | Ouvert |
| 7 | Pas de SAST / Dependabot | Faible | P2-4 | Ouvert |
| 8 | Pas de schema de donnees formel | Modere | P2-5 | Ouvert |
| 9 | Code mort (`browser.py`, blocs commentes) | Faible | P2-7 | Ouvert |
| 10 | Masquage secrets fail-open | Faible | P2-8 | Ouvert |
| 11 | Bus factor = 1 | Important | non-codable | Attenue |
| 12 | Auto-evaluation conformite (pas d'audit externe) | Modere | non-codable | Attenue |
| 13 | Pas d'audit penetration externe | Modere | non-codable | A annexer |

---

## 14. Note qualitative globale

### 14.1 Score global

**Score 69/100** (post-P0 + P1/P2 partiel, 17 avril 2026).
**Potentiel post-P1+P2 complets : ~76/100**.

Source : `audit-hostile-valorisation/07-scorecard-valorisation.md`.

> **Note post-25 avril (estimation interne)** : le doc `audit-hostile-valorisation/09-mise-a-jour-post-p0-yenoyikz.md` section 8 propose un **reajustement interne a ~72/100** apres les commits posterieurs (35 tests supplementaires, 2 ADR livres, P0 RDBMS execute, doctrine pre-commit-audit appliquee systematiquement). Cette reevaluation est **interne et non auditee**. Le score canonique 69/100 est conserve dans le pack tant que la source `07-scorecard-valorisation.md` n'est pas elle-meme mise a jour. Ce point de transparence est integre pour eviter qu'un auditeur hostile ne le presente comme une omission.

### 14.2 Detail par dimension

| Dimension | Score | Note |
|---|---:|---|
| Architecture | 6.5/10 | Intention claire, mais monolithes a scinder |
| Lisibilite | 6.0/10 | Nommage coherent, mais code mort residuel |
| Maintenabilite | 6.5/10 | Hooks + ADR + glossaire ; bus factor reste |
| Securite percue | **7.5/10** | P0 corriges, SECURITY.md present |
| Testabilite | **7.5/10** | 3 956 tests, mais suite etendue non-bloquante |
| Documentation | 7.0/10 | Volumineuse, structuree, attenue le bus factor |
| Auditabilite | **8.5/10** | Differenciateur reel, framework Evidence + audit-proof |
| Industrialisation | 6.0/10 | Docker production fonctionnel, CI partielle |
| Reprise par tiers | 6.5/10 | Onboarding ~1.5-2 semaines |
| **Score global** | **69/100** | **Base technique valorisable** |

---

## 15. Coefficient qualite recommande

### 15.1 Recommandation : **0.95**

| Argument | Justification |
|---|---|
| Score 69/100 | Code structurant industrialisable, ni prototype, ni production premium |
| Auditabilite 8.5 | Differenciateur fort qui meriterait 1.0+, mais pondere par les autres dimensions a 6.0-6.5 |
| Securite 7.5 | P0 corriges, SECURITY.md, mais P1-6 + P2-8 ouverts |
| Testabilite 7.5 | 3 956 tests, mais P1-3 + P1-4 ouverts |
| Architecture 6.5 | Monolithes residuels, P2-1 ouvert |
| Industrialisation 6.0 | CI partielle, P1-5 + P2-4 ouverts |

### 15.2 Ce qui peut faire monter le coefficient (vers 1.0)

- Cloturer P1-3, P1-4, P1-5 (1-2 semaines)
- Activer le `--cov` global et publier le rapport
- Ajouter Dependabot + `pip-audit` en CI
- Cloturer P1-6 (auth par defaut)
- Scinder `settings.py` (P2-1) — plus long
- Audit penetration externe (annexe AE-10)

### 15.3 Ce qui peut faire baisser le coefficient (vers 0.85 ou moins)

- Apparition de regressions sur la suite de tests
- Decouverte d'une faille de securite non documentee
- Constatation d'un audit hostile externe que les P1/P2 restants ne sont pas suffisants
- Absence de couverture mesurable
- Detection d'un risque de licence non identifie

---

## 16. Conclusion

KOREV Evidence est dans la **zone "base technique valorisable"** (score 69/100). Le code presente :

- **Forces marquees** : auditabilite (8.5), securite percue (7.5), testabilite (7.5), documentation (7.0)
- **Points neutres** : architecture (6.5), maintenabilite (6.5), industrialisation (6.0), reprise par tiers (6.5)
- **Faiblesse residuelle** : lisibilite (6.0)

**Coefficient qualite defendable : 0.95**, applique sur le cout brut de reproduction pour produire la valeur cible.

**Decote technique residuelle : 12-20%**, deja integree dans les fourchettes du `04_HOURS_RECONSTRUCTION_REGISTER.md` et du rapport technique.

**Recommandation** : 1 a 2 semaines de remediation ciblee sur les P1-3 a P1-6 + P2-4 + P2-7 + P2-8 pour passer le score a ~73-76/100 et reduire la decote a ~8-12%, ce qui pourrait justifier un coefficient qualite 1.0-1.05.

**Position assumee :** le code est suffisamment mur pour la transmission a Diag & Grow et au commissaire aux apports en l'etat. Les limites sont identifiees, documentees, et leur remediation est planifiee. Aucune limite ne constitue un eliminatoire.

---

*Document etabli le 9 mai 2026. Toutes les forces et faiblesses sont sourcees a des fichiers reels du depot. Le coefficient qualite 0.95 est defendable face a un evaluateur hostile.*
