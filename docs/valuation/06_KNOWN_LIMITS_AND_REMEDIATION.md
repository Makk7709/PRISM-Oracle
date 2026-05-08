# 06 — Limites connues et remediation

**Projet** : KOREV Evidence
**Apporteur / inventeur** : Amine Mohamed
**HEAD analyse** : `fab5689a` (5 mai 2026)
**Date** : 9 mai 2026

> Ce document liste les limites connues du depot avant transmission a Diag & Grow. Pour chaque limite : severite, risque de decote, reponse defendable, remediation prevue, priorite. Une limite assumee vaut mieux qu'une limite decouverte par un auditeur hostile.

---

## 1. Tableau synthese des limites

| # | Limite | Severite | Risque de decote | Reponse defendable | Remediation prevue | Priorite |
|---|---|---|---|---|---|---|
| 1 | Dependance Agent Zero (base MIT) | Modere (perception) | 5-10% si delta non documente, **0% sinon** | Delta documente fichier par fichier dans `02_AGENT_ZERO_DELTA.md` ; cout de portage estime ~125-250 j-h | Maintenance regulière du delta + benchmark | P0 atteinte |
| 2 | Bus factor fondateur | Important | 10-15% | 7 ADR + GLOSSARY + C4 + onboarding 1 196 LOC ; estimation onboarding ~1.5-2 semaines | Recrutement / formation lead engineer | Strategique (hors P0/P1/P2) |
| 3 | Suite de tests etendue non-bloquante en CI | Modere | 1-2% | `continue-on-error: true` documente ; security_ci 90% bloquant | Retirer `continue-on-error` apres stabilisation (1-2 jours) | **P1-3** (ouvert) |
| 4 | Couverture globale non mesuree | Modere | 1-2% | `.coverage` existe localement ; rapport non publie en CI | Ajouter `--cov` + publication HTML (2 heures) | **P1-4** (ouvert) |
| 5 | Pas de build Docker en CI | Modere | 1-2% | Validation syntaxe `docker compose config --quiet` exit 0 ; `run_docker_proof.sh` reproductible | Ajouter job `docker-build-test` dans `main_gate.yml` (3 heures) | **P1-5** (ouvert) |
| 6 | Mode sans authentification quand config absente | Modere | 2-3% | Documente dans SECURITY.md comme limite assumee ; ne s'applique qu'au mode dev local | Refuser le demarrage ou ecouter `127.0.0.1` uniquement (3 heures) | **P1-6** (ouvert) |
| 7 | Modules monolithiques (`settings.py` 2 225 LOC, etc.) | Modere | 3-5% | Bus factor critique ; refactoring scope identifie | Scinder `settings.py` en sous-modules (2-3 jours) | **P2-1** (ouvert) |
| 8 | Duplications conceptuelles (2x ArbiterConfig, 3 chemins consensus) | Faible | 1-2% | Identifie dans audit hostile ; chemin actif est `consensus/engine.py` | Deprecier explicitement les chemins alternatifs (1-2 jours) | **P2-2** (ouvert) |
| 9 | Pas d'audit externe de securite ni de penetration | Modere | 2-4% | SECURITY.md atteste les pratiques ; pipeline audit-proof attenue | Audit penetration externe (annexe AE-10) | Strategique |
| 10 | Pas de SAST / Dependabot | Faible | 1-2% | Pratique standard manquante | Ajouter Dependabot + `pip-audit` (3 heures) | **P2-4** (ouvert) |
| 11 | Pas de schema de donnees formel | Modere | 1-2% | ADR-007 livre 5 mai 2026 ; **P0 RDBMS execute runtime** (init SQL `01_extensions.sql` cree 5 schemas `identity / chats / memory / audit / legal` ; aucune table metier en P0) ; P1-P6 planifiees | Produire `docs/data-model.md` (1-2 jours) ; les schemas Postgres P1-P6 fourniront le formalisme | **P2-5** (ouvert) |
| 12 | Pas d'API reference (OpenAPI / Swagger) | Modere | 1-2% | Endpoints presents dans `python/api/` | Generer OpenAPI a partir des handlers (2-3 jours) | Strategique |
| 13 | Code mort (`browser.py`, blocs commentes) | Faible | 0.5-1% | Identifie dans audit hostile | Nettoyage (P2-7, ~1 jour) | **P2-7** (ouvert) |
| 14 | Masquage de secrets fail-open (`except: pass`) | Faible | 0.5-1% | Identifie dans audit hostile | Remplacer par log + blocage (2 heures) | **P2-8** (ouvert) |
| 15 | Dual Docker (deploy/ vs DockerfileLocal+docker/) | Faible | 0.5% | `deploy/Dockerfile.backend` est l'image production | Archiver `DockerfileLocal` et `docker/` si non utilises | **P2-7** (ouvert) |
| 16 | Conformite AI Act auto-evaluee | Modere | 2-4% | ComplianceGrid implemente AI Act + RGPD ; pipeline audit-proof attenue | Audit conformite externe (annexe AE-10) | Strategique |
| 17 | Antériorite PRISM non prouvable par Git seul | Modere | 2-3% | Documentee dans le rapport technique section 5.4 | Annexer pieces datees AE-7 + 4 brevets PRISM AE-5 + chaine de droits AE-6 | **Annexes externes** |
| 18 | Revenus encore concentres (DICA FRANCE 1 500 EUR/mois) | Modere | non-decotant si annexe fournie | Soutient haut de fourchette equilibre | Annexer factures AE-1 + paiements AE-2 | **Annexes externes** |
| 19 | TRL a ne pas sur-vendre | Modere | 0% si position assumee | Position retenue : actif logiciel a maturite "structurant industrialisable" (TRL 6-7) | Pas de remediation necessaire (positionnement assume) | Position |
| 20 | Dependances providers (LLM, MCP) | Faible | 1-2% | LiteLLM abstraction permet le switch (ADR-004) | Maintenance des fallbacks documentes | Maintenance |
| 21 | Modules legacy (instruments/, knowledge/) | Faible | 0.5% | Heritage Agent Zero, peu utilises | Archivage si non utilises | Maintenance |
| 22 | Risques secrets / cles / tokens dans le depot | **Critique theorique** | Eliminatoire si fuite | `.env`, `users.json`, `*.pem` gitignored ; `.env.example` placeholder ; `deploy/users.json.example` **sanitize sur branche de transmission `diag-grow/transmission-evidence`** (3 utilisateurs `admin_example`, `user_example_1`, `user_example_2` ; emails `@example.com` ; organisation `ExampleOrg` ; hashes placeholders explicites avec avertissement "NOT a valid Argon2id output") | **Verification avant transmission** : `git ls-files \| grep -iE '\.(env\|pem\|key)$\|users\.json$'` ; verification anti-secrets J-0 documentee dans `docs/valuation/10_FINAL_TRANSMISSION_CHECKLIST.md` | **CRITIQUE pre-transmission** — **TRAITE le 9 mai 2026** sur la branche de transmission |
| 23 | Documentation manquante (schema donnees, API ref) | Modere | 2-3% | ADR + GLOSSARY + C4 + SECURITY.md presents ; data model et API ref restent | Cf. limite #11 et #12 | P2 |

---

## 2. Limites par categorie

### 2.1 Limites de gouvernance (humaines)

#### 2.1.1 Bus factor = 1

- **Constat** : la totalite de la propriete intellectuelle repose sur Amine Mohamed.
- **Severite** : Important.
- **Risque de decote** : 10-15% (cumul realiste, attenue).
- **Reponse defendable** :
  - 7 ADR documentent les decisions architecturales majeures.
  - GLOSSARY definit 30+ termes proprietaires.
  - Diagrammes C4 (3 niveaux + sequence Mermaid).
  - SECURITY.md politique de securite.
  - Guide onboarding developpeur 1 196 lignes.
  - Estimation onboarding : ~1.5-2 semaines pour un senior Python.
- **Remediation** : recrutement / formation d'un lead engineer (cf. `docs/PLAN_INTEGRATION_LEAD_ENGINEER_30_60_90_INTERNAL.md`).

#### 2.1.2 Pas d'audit externe

- **Constat** : pas d'audit penetration ni d'audit conformite tiers.
- **Severite** : Modere.
- **Risque de decote** : 2-4%.
- **Reponse defendable** :
  - Audit hostile interne complet (8 livrables).
  - Pipeline audit-proof (replay, human review, risk register) attenue l'auto-evaluation.
  - SECURITY.md formalise les pratiques.
- **Remediation** : annexer rapports d'audit externe si disponibles (AE-10) ; sinon, planifier audit en P3.

### 2.2 Limites techniques (CI / industrialisation)

#### 2.2.1 Suite etendue non-bloquante (P1-3)

- **Constat** : `continue-on-error: true` sur le job `extended-tests` dans `main_gate.yml`.
- **Severite** : Modere.
- **Risque de decote** : 1-2%.
- **Reponse defendable** : `security_ci.yml` est bloquant avec un seuil 90% ; `legal_pipeline_ci.yml` est bloquant.
- **Remediation** : retirer `continue-on-error: true` apres stabilisation des tests qui echouent (1-2 jours).

#### 2.2.2 Couverture globale non mesuree (P1-4)

- **Constat** : `--cov` non active dans la CI principale ; `.coverage` existe localement.
- **Severite** : Modere.
- **Risque de decote** : 1-2%.
- **Reponse defendable** : `pytest-cov` est dans les plugins charges ; couverture mesurable localement.
- **Remediation** : ajouter `--cov=python --cov-report=html` dans la CI et publier le rapport (2 heures).

#### 2.2.3 Pas de build Docker en CI (P1-5)

- **Constat** : l'image est construite directement sur le serveur de production.
- **Severite** : Modere.
- **Risque de decote** : 1-2%.
- **Reponse defendable** : validation syntaxe `docker compose config --quiet` exit 0 (annexe A12). Image multi-stage Python 3.11-slim + Node.js 20 fonctionnelle.
- **Remediation** : ajouter un job `docker-build-test` dans `main_gate.yml` qui construit l'image et run un health check (3 heures).

#### 2.2.4 Pas de SAST / Dependabot (P2-4)

- **Constat** : pas de scanning automatique des dependances.
- **Severite** : Faible.
- **Risque de decote** : 1-2%.
- **Reponse defendable** : pratique standard manquante mais aucune CVE active connue dans les dependances pinees.
- **Remediation** : ajouter Dependabot + job `safety` ou `pip-audit` dans la CI (3 heures).

### 2.3 Limites de securite (residuelles)

#### 2.3.1 Mode sans authentification par defaut (P1-6)

- **Constat** : si `AUTH_LOGIN` et `users.json` absents, le serveur demarre sans authentification.
- **Severite** : Modere.
- **Risque de decote** : 2-3%.
- **Reponse defendable** : documente dans SECURITY.md comme "limite assumee, mode dev local". Ne s'applique pas a la production avec config standard.
- **Remediation** : refuser le demarrage ou limiter l'ecoute a `127.0.0.1` en l'absence de config (3 heures).

#### 2.3.2 Masquage de secrets fail-open (P2-8)

- **Constat** : `except Exception: pass` dans certaines extensions de masquage.
- **Severite** : Faible.
- **Risque de decote** : 0.5-1%.
- **Reponse defendable** : identifie dans l'audit hostile interne.
- **Remediation** : remplacer par `log + blocage de la transmission` (2 heures).

### 2.4 Limites architecturales (dette technique)

#### 2.4.1 Modules monolithiques (P2-1)

- **Constat** : `settings.py` 2 225 LOC, `legal_orchestrator.py` 1 960, `adversarial_instruction.py` 2 123, etc.
- **Severite** : Modere.
- **Risque de decote** : 3-5%.
- **Reponse defendable** : chaque module a une responsabilite identifiable ; refactoring scope identifie (sous-modules par domaine).
- **Remediation** : scinder `settings.py` en `settings/auth.py`, `settings/models.py`, `settings/consensus.py`, etc. (2-3 jours).

#### 2.4.2 Duplications conceptuelles (P2-2)

- **Constat** : 2x `ArbiterConfig` dans des modules differents ; 3 chemins consensus (`consensus/engine.py`, `consensus_arbiter.py`, `consensus_integration.py`).
- **Severite** : Faible.
- **Risque de decote** : 1-2%.
- **Reponse defendable** : chemin actif clairement identifiable (`consensus/engine.py`).
- **Remediation** : deprecier explicitement les chemins alternatifs avec `DeprecationWarning` (1-2 jours).

#### 2.4.3 Code mort (P2-7)

- **Constat** : `browser.py` ~336 lignes commentees ; blocs commentes dans `initialize.py`, `files.py`.
- **Severite** : Faible.
- **Risque de decote** : 0.5-1%.
- **Reponse defendable** : identifie dans audit hostile, en plan de nettoyage.
- **Remediation** : nettoyage (1 jour).

#### 2.4.4 Dual Docker (P2-7)

- **Constat** : `deploy/Dockerfile.backend` (production) coexiste avec `DockerfileLocal` + `docker/` (dev historique).
- **Severite** : Faible.
- **Risque de decote** : 0.5%.
- **Reponse defendable** : la version production est claire (`deploy/`).
- **Remediation** : archiver `DockerfileLocal` et `docker/` si non utilises ; sinon, documenter l'usage de chacun.

### 2.5 Limites documentaires

#### 2.5.1 Pas de schema de donnees formel (P2-5)

- **Constat** : structures JSON des chats, sessions, rapports d'audit, configuration, index legal **non documentees** dans un schema formel.
- **Severite** : Modere.
- **Risque de decote** : 1-2%.
- **Reponse defendable** : ADR-007 livre le 5 mai 2026 (commit `b11b4d99`) ; **P0 execute runtime** (compose staging autonome `deploy/docker-compose.staging.yml`, project name verrouille `evidence-staging`, port 5433 localhost ; init SQL `deploy/postgres/init/01_extensions.sql` cree extensions `pgcrypto`, `vector`, `pg_trgm` + 5 schemas `identity`, `chats`, `memory`, `audit`, `legal` ; 6 tests d'infra T1-T6 marker `infra` + test T7 backup/restore) ; **P1-P6 planifiees** (Repository, sessions chat, FAISS -> pgvector, artefacts audit, legal SQLite -> Postgres, decommissioning) sur 4-6 mois ; aucun service applicatif n'a `depends_on` Postgres en P0 (zero-impact prod). Source : `audit-hostile-valorisation/09-mise-a-jour-post-p0-yenoyikz.md` section 4.
- **Remediation** : produire `docs/data-model.md` avec diagramme ER (1-2 jours) ; les schemas Postgres P1-P6 fourniront le formalisme structurel definitif.

#### 2.5.2 Pas d'API reference (OpenAPI / Swagger)

- **Constat** : ~71 handlers HTTP dans `python/api/`, sans specification OpenAPI generee.
- **Severite** : Modere.
- **Risque de decote** : 1-2%.
- **Reponse defendable** : les handlers sont auto-documentants ; tests d'integration couvrent une partie.
- **Remediation** : generer OpenAPI a partir des handlers (apispec / flasgger) (2-3 jours).

### 2.6 Limites probatoires (depot Git insuffisant seul)

#### 2.6.1 Antériorite PRISM (5 ans de R&D)

- **Constat** : non demontrable par le seul historique Git (qui commence le 15 janvier 2026).
- **Severite** : Modere.
- **Risque de decote** : 2-3%.
- **Reponse defendable** : explicitement adressee dans le rapport technique section 5.4.
- **Remediation** : annexer **AE-7** (pieces datees pre-repository : carnets, exports notes, emails, prototypes, captures, factures outils, depots anterieurs eventuels) et **AE-5 + AE-6** (4 brevets PRISM + chaine de droits PRISM -> Evidence).

#### 2.6.2 Conformite AI Act / RGPD auto-evaluee

- **Constat** : la ComplianceGrid implemente AI Act articles 9, 13, 14, 17 + RGPD article 30, **mais sans audit externe**.
- **Severite** : Modere.
- **Risque de decote** : 2-4%.
- **Reponse defendable** : pipeline audit-proof (replay, human review, risk register) attenue l'auto-evaluation. Tests valident la presence du framework.
- **Remediation** : audit conformite externe (annexe AE-10) ; ou attestation tiers documentee.

### 2.7 Limites commerciales

#### 2.7.1 Revenus encore concentres

- **Constat** : DICA FRANCE 1 500 EUR/mois (~18 KEUR/an run-rate).
- **Severite** : Modere.
- **Risque de decote** : non-decotant si annexes fournies ; sinon, ne soutient pas le haut de fourchette.
- **Reponse defendable** : volume de revenu reel mais limite ; n'autorise pas une approche par multiples de revenus, mais reduit l'objection "pre-revenue" et soutient le haut du scenario equilibre.
- **Remediation** : annexer **AE-1** (factures DICA) et **AE-2** (preuves de paiement). Annexer **AE-3 + AE-4** (Centrale Lille, Le Tarmac) et **AE-8** (echanges clients).

#### 2.7.2 TRL maturite

- **Constat** : actif logiciel a maturite "structurant industrialisable" (TRL 6-7), pas TRL 9.
- **Severite** : Modere.
- **Risque de decote** : 0% si position assumee.
- **Reponse defendable** : position retenue dans le pack ; pas de sur-vente.

### 2.8 Limites de securite operationnelle (pre-transmission)

#### 2.8.1 Risques secrets / cles / tokens (CRITIQUE pre-transmission)

- **Constat** : le depot peut contenir accidentellement des credentials reels.
- **Severite** : **Critique theorique** (eliminatoire si fuite).
- **Risque de decote** : eliminatoire si fuite reelle.
- **Reponse defendable** : `.env`, `users.json`, `*.pem` declares dans `.gitignore`.
- **Remediation OBLIGATOIRE avant transmission** :
  ```bash
  # Verification 1 : aucun fichier sensible n'est tracke
  git ls-files | grep -iE '\.(env|pem|key)$|users\.json$|secrets?\.json$'
  # Doit retourner vide

  # Verification 2 : aucune cle reelle n'a fuite dans l'historique
  git log --all -p -- '.env' '.env.production' 'users.json' 'deploy/users.json' 2>&1 | head -50
  # Doit montrer uniquement des placeholders / hashes Argon2id de demo

  # Verification 3 : entropy scan
  command -v rg >/dev/null && rg -uu --no-messages -i '(api[_-]?key|password|token|secret)\s*=\s*["\x27][A-Za-z0-9/_+-]{20,}' . --max-count 1
  # Doit retourner vide ou seulement des references non sensibles

  # Verification 4 : .env.example ne contient que des placeholders
  cat .env.example | grep -E '^[A-Z_]+=' | grep -v 'YOUR_\|<.*>\|example\|placeholder' | head -10
  # Doit retourner vide ou uniquement des valeurs non sensibles
  ```

---

## 3. Plan de remediation priorise

### 3.1 Avant transmission a Diag & Grow (CRITIQUE)

| # | Action | Effort | Statut |
|---|---|---|---|
| 1 | Verification absence de secrets dans le depot | 30 min | A executer |
| 2 | Verification `git status` propre (commit ou stash en cours) | 15 min | Cf. status branche |
| 3 | Verification coherence des chiffres entre rapport technique et pack valuation | 1 heure | Cf. pack `08_AUDIT_HOSTILE_VALUATION_PACK.md` |
| 4 | Preparation des annexes externes (AE-1 a AE-9) | Variable | A organiser par l'apporteur |

### 3.2 1-2 semaines apres transmission (P1 restants)

| # | Action | Effort | Impact decote |
|---|---|---|---|
| P1-3 | Rendre la suite etendue bloquante en CI | 1-2 jours | -1 a -2% |
| P1-4 | Activer la mesure de couverture globale | 2 heures | -1 a -2% |
| P1-5 | Ajouter un build Docker en CI | 3 heures | -1 a -2% |
| P1-6 | Exiger l'authentification par defaut | 3 heures | -2 a -3% |
| **Total P1 restants** | **~3 jours effort** | **-5 a -9% decote** |

### 3.3 2-4 semaines apres transmission (P2 restants)

| # | Action | Effort | Impact decote |
|---|---|---|---|
| P2-1 | Scinder `settings.py` | 2-3 jours | -2 a -3% |
| P2-2 | Unifier les chemins de consensus | 1-2 jours | -1 a -2% |
| P2-4 | SAST + Dependabot | 3 heures | -1 a -2% |
| P2-5 | Documenter le schema de donnees | 1-2 jours | -1 a -2% |
| P2-7 | Nettoyer le code mort | 1 jour | -0.5 a -1% |
| P2-8 | Fail-closed sur le masquage de secrets | 2 heures | -0.5 a -1% |
| **Total P2 restants** | **~6-9 jours effort** | **-6 a -11% decote** |

### 3.4 Strategique (mois apres transmission)

| # | Action | Effort | Impact decote |
|---|---|---|---|
| Audit penetration externe | 2-4 semaines (tiers) | -2 a -4% |
| Audit conformite AI Act tiers | 2-4 semaines (tiers) | -2 a -4% |
| Migration Postgres / pgvector (ADR-007) — phases P1 a P6 | 4-8 semaines (P0 deja livre 5 mai 2026) | -3 a -5% (transformation, +5/+10% en valeur ajoutee) |
| API Reference (OpenAPI) | 2-3 jours | -1 a -2% |
| Recrutement / formation lead engineer | 2-3 mois | -10 a -15% (bus factor) |

---

## 4. Effet cumule de la remediation

| Etape | Score qualite | Decote technique | Coefficient qualite |
|---|---:|---|---:|
| Etat actuel (5 mai 2026, HEAD `fab5689a`) | 69/100 | 12-20% | 0.95 |
| Apres P1 restants (1-2 semaines) | ~73/100 | 9-15% | 0.97-0.98 |
| Apres P1 + P2 restants (3-4 semaines) | ~76/100 | 8-12% | 0.98-1.00 |
| Apres P1 + P2 + audit externes + lead engineer | ~80-83/100 | 5-8% | 1.00-1.05 |

**Effet sur la valeur defendable (sur la base de 958 KEUR a 1 054 KEUR equilibre actuel)** :

| Etape | Valeur defendable equilibre |
|---|---|
| Etat actuel | 958 000 EUR a 1 054 000 EUR |
| Apres P1 restants | ~1 000 000 EUR a 1 100 000 EUR |
| Apres P1 + P2 restants | ~1 050 000 EUR a 1 180 000 EUR |
| Apres P1 + P2 + audit externes + lead engineer | ~1 150 000 EUR a 1 300 000 EUR |

---

## 5. Limites assumees explicitement

> Ces limites sont **declarees au commissaire et a Diag & Grow** dans le pack de transmission (`07_DIAG_GROW_TRANSMISSION_NOTE.md`). Aucune limite n'est dissimulee.

1. Le projet est une oeuvre derivee Agent Zero (MIT). Le delta proprietaire est documente fichier par fichier.
2. Le bus factor est = 1 ; la documentation structurelle attenue le risque mais ne l'elimine pas.
3. La CI presente des limites assumees (P1-3, P1-4, P1-5) en cours de remediation.
4. Le mode sans authentification par defaut existe pour le mode dev local ; la remediation P1-6 est planifiee.
5. Les modules monolithiques sont identifies (P2-1) ; le refactoring est planifie.
6. La conformite AI Act / RGPD est auto-evaluee ; un audit externe est recommande.
7. L'antériorite PRISM (5 ans de R&D) ne se prouve pas par le seul depot ; les annexes AE-7 sont necessaires.
8. Les revenus sont encore concentres (DICA FRANCE 1 500 EUR/mois) ; les annexes AE-1 a AE-4 et AE-8 soutiennent le haut de fourchette.
9. Aucun audit externe de penetration n'a ete realise (AE-10 si disponible).

---

## 6. Conclusion

Les **23 limites** identifiees dans ce document sont :

- **2 critiques theoriques** (secrets / cles dans le depot) : verifiables en quelques commandes avant transmission.
- **9 moderees** : 7 corrigeables en 1-2 semaines (P1 + P2 restants), 2 strategiques (audits externes, bus factor).
- **8 faibles** : corrigeables en quelques jours (P2 restants).
- **4 contextuelles** (TRL, dependances providers, modules legacy, dual Docker) : positionnees comme assumees.

**Aucune limite ne constitue un eliminatoire** sous reserve de la verification anti-secrets pre-transmission.

**Aucune limite n'est dissimulee** : toutes sont integrees au pack de transmission.

**La remediation P1 + P2 restantes (~10 jours d'effort) ferait passer le score de 69/100 a ~76/100 et reduirait la decote technique residuelle de 12-20% a ~8-12%**, ce qui justifierait une revalorisation a la hausse de ~5-10% du scenario equilibre.

---

*Document etabli le 9 mai 2026. Toutes les limites sont sourcees a l'audit hostile interne (`audit-hostile-valorisation/`) ou a l'analyse directe du depot. Le plan de remediation est aligne avec `audit-hostile-valorisation/06-plan-de-remediation-priorise.md`.*
