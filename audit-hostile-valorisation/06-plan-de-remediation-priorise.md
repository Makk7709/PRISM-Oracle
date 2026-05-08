# 06 — Plan de Remediation Priorise

**Projet** : KOREV Evidence  
**Date** : 3 avril 2026 (mise a jour : 17 avril 2026)  
**Statut** : P0 integralement execute. P1-1, P1-2, P2-3, P2-6 executes le 17 avril 2026. P1-3 a P1-6 et P2 restant en cours.  
**Objectif** : reduire la decote potentielle de ~25-40% a ~10-15% avant exposition a un cabinet externe  
**Progression** : decote actuelle estimee ~12-20% (vs 25-40% initial, 15-25% post-P0). Score 69.00/100 (vs 58.75 initial, 65.25 post-P0).

---

## Priorites

- **P0** : Eliminatoire — a traiter avant toute interaction avec un tiers evaluateur
- **P1** : Structurant — renforce significativement la credibilite technique
- **P2** : Consolidation — ameliore la perception globale de maturite

---

## P0 — Eliminatoires (semaine 1)

### P0-1 : ✅ Corriger l'incoherence de licence — FAIT

| | |
|---|---|
| **Constat** | Badge MIT dans README.md vs licence proprietaire dans LICENSE |
| **Action** | ~~Supprimer le badge MIT.~~ |
| **Statut** | **FAIT** — commit `40808223` (3 avril 2026). Badge "License-Proprietary" en rouge. Fichiers coherents. |
| **Effort reel** | < 1 heure |

### P0-2 : ✅ Supprimer la cle HMAC par defaut — FAIT

| | |
|---|---|
| **Constat** | `integrity_block.py` contenait `b"evidence-dev-hmac-key-not-for-production"` |
| **Action** | ~~Supprimer le fallback.~~ |
| **Statut** | **FAIT** — commit `40808223` (3 avril 2026). `_get_hmac_key()` leve `RuntimeError` si `EVIDENCE_HMAC_KEY` absent. Documente dans `.env.example`. |
| **Effort reel** | < 2 heures |

### P0-3 : ✅ Corriger le mot de passe en clair dans les logs — FAIT

| | |
|---|---|
| **Constat** | `run_ui.py` affichait le mot de passe en clair dans les logs |
| **Action** | ~~Remplacer par un message generique.~~ |
| **Statut** | **FAIT** — commit `40808223` (3 avril 2026). Utilise desormais un placeholder `'YOUR_PASSWORD'`. |
| **Effort reel** | < 30 minutes |

### P0-4 : ✅ Corriger le RBAC audit_reports — FAIT

| | |
|---|---|
| **Constat** | `requires_admin` bloquait avant `can_access_audit_reports` |
| **Action** | ~~Remplacer `requires_admin` par la logique fine.~~ |
| **Statut** | **FAIT** — commit `40808223` (3 avril 2026). `requires_admin` retourne `False`. L'acces passe par `can_access_audit_reports(principal, target_org=org)`. |
| **Effort reel** | < 2 heures |

---

## P1 — Structurants (semaines 1-2)

### P1-1 : ✅ Creer un SECURITY.md — FAIT

| | |
|---|---|
| **Action** | Creer un `SECURITY.md` racine : politique de divulgation responsable, perimetre, contacts, pratiques de gestion des secrets, engagement de reponse. |
| **Statut** | **FAIT** — 17 avril 2026. `SECURITY.md` a la racine : perimetre, divulgation responsable (48h), pratiques crypto (Argon2id, HMAC-SHA256, RSA), rate limiting, RBAC, architecture secu, limites connues. Reference dans le guide onboarding. 12 tests TDD. |
| **Effort reel** | 2 heures |

### P1-2 : ✅ Produire les Architecture Decision Records (ADR) cles — FAIT

| | |
|---|---|
| **Action** | Creer `docs/adr/` avec les decisions majeures : ADR-001 (choix PRISM multi-arbitres), ADR-002 (router deterministe), ADR-003 (framework Evidence), ADR-004 (LiteLLM vs appels directs), ADR-005 (extension hooks). Format: contexte, decision, consequences, alternatives rejetees. |
| **Statut** | **FAIT** — 17 avril 2026. 5 ADR dans `docs/adr/`. Chaque ADR contient : date, statut, contexte, decision detaillee, consequences (positives + negatives), alternatives rejetees avec justification. 21 tests TDD. Reference dans le guide onboarding. |
| **Effort reel** | 3 heures |

### P1-3 : Rendre la suite de tests etendue bloquante

| | |
|---|---|
| **Action** | Retirer `continue-on-error: true` du job `extended-tests` dans `main_gate.yml`. Stabiliser les tests qui echouent. |
| **Effort** | 1-2 jours |
| **Impact** | Credibilise la couverture de tests annoncee |

### P1-4 : Activer la mesure de couverture globale

| | |
|---|---|
| **Action** | Ajouter `--cov=python --cov-report=html` dans la CI. Publier le rapport. Pas besoin de seuil bloquant immediatement — le rapport suffit. |
| **Effort** | 2 heures |
| **Impact** | Prouve la couverture a un tiers. Aligne les chiffres doc vs realite. |

### P1-5 : Ajouter un build Docker en CI

| | |
|---|---|
| **Action** | Ajouter un job `docker-build-test` dans `main_gate.yml` : `docker build -f deploy/Dockerfile.backend .` + health check rapide. Pas de push vers registre necessaire immediatement. |
| **Effort** | 3 heures |
| **Impact** | Detecte les regressions Docker avant deploiement, signal d'industrialisation |

### P1-6 : Exiger l'authentification par defaut

| | |
|---|---|
| **Action** | Quand ni `AUTH_LOGIN` ni `users.json` ne sont configures : refuser le demarrage ou limiter l'ecoute a `127.0.0.1`. |
| **Effort** | 3 heures (code + tests + doc) |
| **Impact** | "Secure by default" — aligne avec le positionnement produit |

---

## P2 — Consolidation (semaines 2-4)

### P2-1 : Scinder settings.py

| | |
|---|---|
| **Action** | Reorganiser en sous-modules : `settings/auth.py`, `settings/models.py`, `settings/consensus.py`, `settings/legal.py`, `settings/ui.py`, `settings/defaults.py`. |
| **Effort** | 2-3 jours |
| **Impact** | Reduit la complexite percue, facilite l'onboarding, reduit le bus factor |

### P2-2 : Unifier les chemins de consensus

| | |
|---|---|
| **Action** | Deprecier explicitement l'un des deux `ArbiterConfig`. Documenter le chemin actif. Supprimer ou archiver le chemin alternatif. |
| **Effort** | 1-2 jours |
| **Impact** | Clarifie l'IP PRISM, reduit la confusion |

### P2-3 : ✅ Produire des diagrammes d'architecture (C4) — FAIT

| | |
|---|---|
| **Action** | Creer les 3 premiers niveaux C4 : Contexte (utilisateurs, systemes externes), Containers (Flask, Docker, MCP, LLM providers), Composants (agent, consensus, evidence, legal, security). Utiliser Mermaid ou PlantUML pour la maintenabilite. |
| **Statut** | **FAIT** — 17 avril 2026. `docs/ARCHITECTURE_C4_DIAGRAMS.md` : 3 niveaux C4 + diagramme de sequence en Mermaid. Contexte (acteurs externes), Containers (Docker Compose), Composants (7 sous-systemes), Flux requete (sequence). 10 tests TDD. |
| **Effort reel** | 2 heures |

### P2-4 : Ajouter SAST/scanning de dependances

| | |
|---|---|
| **Action** | Ajouter Dependabot ou Renovate + un job `safety` ou `pip-audit` dans la CI. Optionnel : CodeQL pour SAST. |
| **Effort** | 3 heures |
| **Impact** | Pratique standard attendue par tout investisseur technique |

### P2-5 : Documenter le schema de donnees

| | |
|---|---|
| **Action** | Creer `docs/data-model.md` : structures JSON des chats, sessions, rapports d'audit, configuration, index legal. Diagramme ER pour la persistence. |
| **Effort** | 1-2 jours |
| **Impact** | Rend le modele de donnees evaluable par un tiers |

### P2-6 : ✅ Creer un glossaire technique — FAIT

| | |
|---|---|
| **Action** | Creer `docs/GLOSSARY.md` : PRISM, Evidence, SessionEnvelope, RouteDecision, IntegrityBlock, ComplianceGrid, etc. |
| **Statut** | **FAIT** — 17 avril 2026. `docs/GLOSSARY.md` : 30+ termes proprietaires definis avec fichier source et contexte technique. Organise par categorie (Architecture, Conformite, Decision, Evidence, Fiabilite, Hooks, Integrite, Legal-Safe, MCP, Profils, Reporting, Sessions, Validation). 16 tests TDD. |
| **Effort reel** | 2 heures |

### P2-7 : Nettoyer le code mort

| | |
|---|---|
| **Action** | Supprimer `browser.py` (336 lignes commentees), blocs commentes dans `initialize.py`, `files.py`, execution guard mort dans `agent.py`. Supprimer ou archiver `docker/` et `DockerfileLocal` si non utilises. |
| **Effort** | 1 jour |
| **Impact** | Reduit le bruit, ameliore la lisibilite |

### P2-8 : Fail-closed sur le masquage de secrets

| | |
|---|---|
| **Action** | Remplacer `except Exception: pass` dans les extensions de masquage par un log + blocage de la transmission. |
| **Effort** | 2 heures |
| **Impact** | Aligne le masquage avec la politique de securite |

---

## Calendrier optimal

```
Semaine 1 (P0 + debut P1) — ✅ P0 FAIT le 3 avril 2026
├── Jour 1  : ✅ P0-1 (licence) + ✅ P0-2 (HMAC) + ✅ P0-3 (logs) — FAIT
├── Jour 2  : ✅ P0-4 (RBAC) + P1-1 (SECURITY.md) + P1-6 (auth defaut)
├── Jour 3-4: P1-2 (ADR) + P1-5 (Docker CI)
└── Jour 5  : P1-3 (tests bloquants) + P1-4 (couverture)

Semaine 2 (P1 + debut P2)
├── Jour 1-2: P2-1 (scinder settings) + P2-2 (unifier consensus)
├── Jour 3  : P2-3 (diagrammes C4) + P2-6 (glossaire)
└── Jour 4-5: P2-4 (SAST) + P2-5 (schema donnees) + P2-7 (code mort)

Semaine 3 (P2 + polish)
├── P2-8 (masquage fail-closed)
├── Relecture croisee de toute la doc mise a jour
├── Verification des references croisees doc/code
└── Preparation du dossier de valorisation consolide
```

---

## Matrice impact/effort

| Chantier | Effort | Impact valorisation | ROI | Statut |
|---|---|---|---|---|
| P0-1 Licence | 1h | ★★★★★ | **Maximal** | ✅ FAIT |
| P0-2 HMAC | 2h | ★★★★ | Tres eleve | ✅ FAIT |
| P0-3 Logs mdp | 30min | ★★★ | Eleve | ✅ FAIT |
| P0-4 RBAC | 2h | ★★★ | Eleve | ✅ FAIT |
| P1-1 SECURITY.md | 2h | ★★★★ | Tres eleve | ✅ FAIT |
| P1-2 ADR | 3h | ★★★★★ | Tres eleve | ✅ FAIT |
| P1-3 Tests bloquants | 1-2j | ★★★★ | Eleve |
| P1-4 Couverture | 2h | ★★★ | Eleve |
| P1-5 Docker CI | 3h | ★★★ | Eleve |
| P1-6 Auth defaut | 3h | ★★★ | Eleve |
| P2-1 Scinder settings | 2-3j | ★★★ | Moyen |
| P2-2 Unifier consensus | 1-2j | ★★★ | Moyen |
| P2-3 Diagrammes C4 | 2h | ★★★★ | Eleve | ✅ FAIT |
| P2-4 SAST | 3h | ★★★ | Eleve |
| P2-5 Schema donnees | 1-2j | ★★★ | Moyen |
| P2-6 Glossaire | 2h | ★★ | Moyen | ✅ FAIT |
| P2-7 Code mort | 1j | ★★ | Moyen |
| P2-8 Masquage | 2h | ★★ | Moyen |
