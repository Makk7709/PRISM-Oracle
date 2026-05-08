# KOREV AI — Plan d'intégration Lead Engineer (Aya) — 30 / 60 / 90 jours

**Classification :** CONFIDENTIEL — Document interne fondateur / direction technique
**Statut :** V2 — révision après audit du repository
**Date :** 4 mai 2026
**Version Evidence analysée :** v1.4.0 (HEAD `7a7abd6a`)
**Destinataire :** Direction technique KOREV AI uniquement
**Document complémentaire transmissible :** `docs/ONBOARDING_AYA_30_60_90.md`

> **Avertissement de circulation.** Ce document contient la grille d'analyse interne (bus factor, SPOFs, écarts entre capacités déclarées et capacités effectives, charge fondateur). Il n'est **pas** destiné à être transmis tel quel à la Lead Engineer. La version transmissible est `ONBOARDING_AYA_30_60_90.md` — elle dit la même vérité technique, dans un registre adapté.

---

## 0. Synthèse exécutive

1. **Risque organisationnel principal** : la couche différenciante "IA de confiance" KOREV (consensus, integrity, replay, risk register, human review, authorization) est aujourd'hui mono-auteur. Sur 11 modules critiques de cette couche, un seul contributeur a écrit des lignes. C'est un facteur de fragilité structurelle, indépendant de toute considération de personne.
2. **Stratégie d'intégration** : Evidence d'abord, PRISM ensuite. Aucune contribution Aya sur le périmètre PRISM avant J+90. Décision GO/NO-GO en revue trimestrielle.
3. **Calibrage charge fondateur** : 8 à 12 heures hebdomadaires de transmission active en M1, 6 à 8 heures en M2, 4 à 6 heures en M3. Au-delà, le delivery business (clients en cours, dossier commissaire aux apports) est compromis.
4. **Premier transfert de propriété visé J+60** : `python/helpers/processing_register.py`. Petit, isolé, fort enjeu RGPD Art. 30, faible risque opérationnel immédiat. Idéal pour une transmission complète (ADR + implémentation + tests + déploiement).
5. **Contribution code Aya dès S1** sur zones périphériques non critiques (scripts opérationnels, documentation profils, tests sur modules sans tests directs). Aucune attente de "spectatrice" en mois 1.
6. **Test de transmission à J+90** : Aya livre un audit hostile interne sur un domaine fondateur. C'est le marqueur réel de doctrine assimilée.

---

## 1. Cartographie de complexité — chiffres réels

### 1.1 Volumétrie

| Dimension | Valeur | Lecture |
|---|---:|---|
| Fichiers Python KOREV (hors venv/mcp) | ~600 | Volume d'une équipe de 4-5 ingénieurs senior à plein régime |
| LOC Python KOREV (hors tests/venv) | ~70 000 | — |
| Endpoints API (`python/api/`) | 71 | Surface large — non exhaustive en M1 |
| Profils d'agents | 12 | 10 = prompts purs, 2 = code custom (`medical` 2383 LOC, `legal_safe` 42 LOC) |
| Hooks d'extension | 24 | Ordering par préfixe `_NN_` — convention non enforcée techniquement |
| Tests Python | ~3846 / 179 fichiers | Suite étendue `continue-on-error: true` en CI |
| Workflows GitHub Actions | 3 | Pas de build Docker en CI, pas de SAST, pas de CD |

### 1.2 Modules monolithes (>1000 LOC) — fragilité de maintenance

| Module | LOC | Signature auteur principal |
|---|---:|---|
| `python/helpers/settings.py` | 2232 | Multi-auteur upstream Agent Zero |
| `python/helpers/adversarial_instruction.py` | 2123 | KOREV propriétaire |
| `python/helpers/legal_orchestrator.py` | 1960 | KOREV propriétaire — mono-auteur |
| `python/helpers/legal_pipeline.py` | 1807 | KOREV propriétaire — mono-auteur |
| `python/helpers/task_scheduler.py` | 1647 | Multi-auteur |
| `python/helpers/strategic_orchestrator.py` | 1560 | KOREV propriétaire — mono-auteur |
| `python/helpers/reporting/evidence_native.py` | 1422 | KOREV propriétaire |
| `python/helpers/pdf_extraction/pipeline.py` | 1217 | KOREV propriétaire |
| `python/helpers/reasoning_engine.py` | 1190 | KOREV propriétaire |
| `python/helpers/mcp_handler.py` | 1148 | Multi-auteur upstream |
| `agent.py` | 1144 | 9 auteurs (frdel, Amine, et 7 autres) |
| `python/helpers/adversarial_consensus_integration.py` | 1144 | KOREV propriétaire |

### 1.3 Distinction socle hérité / couche KOREV

| Couche | Auteur dominant | Modules clés | Posture intégration M1 |
|---|---|---|---|
| Socle Agent Zero (hérité) | `frdel` (629 commits) + upstream | `agent.py`, `models.py`, `run_ui.py`, `mcp_handler.py`, `task_scheduler.py`, système d'extensions | Lire et utiliser. Pas de refactoring. |
| Couche KOREV "IA de confiance" | Amine Mohamed (267 commits, mono-auteur sur 11/14 modules critiques) | `python/consensus/`, `audit_report_renderer`, `integrity_block`, `replay_engine`, `human_review`, `dynamic_risk_register`, `criticality_router`, `metacognition`, `reasoning_engine`, `authorization`, routers déterministes | **Lecture des 5 ADR. Pas de modification avant J+30 minimum.** |
| Pipelines métier | Mono-auteur fondateur | `legal_pipeline`, `legal_orchestrator`, `contract_drafting/`, `strategic_orchestrator` | Compréhension fonctionnelle M1, contributions périphériques M2 |
| Frontend | Multi-auteur Agent Zero | `webui/` (1300 LOC HTML monolithique) | Hors périmètre M1-M3 sauf urgence |

---

## 2. Bus factor réel sur la couche KOREV — données git

> Mesure objective via `git log` au HEAD `7a7abd6a`.

| Fichier | Commits | Auteurs distincts |
|---|:---:|---|
| `python/helpers/execution_budget.py` | 3 | 1 |
| `python/helpers/legal_pipeline.py` | 5 | 1 |
| `python/helpers/contract_drafting/orchestrator.py` | 2 | 1 |
| `python/helpers/replay_engine.py` | 1 | 1 |
| `python/helpers/dynamic_risk_register.py` | 1 | 1 |
| `python/helpers/human_review.py` | 1 | 1 |
| `python/helpers/criticality_router.py` | 4 | 1 |
| `python/helpers/audit_report_renderer.py` | 5 | 1 |
| `python/helpers/integrity_block.py` | 3 | 1 |
| `python/security/authorization.py` | 4 | 1 |

→ Sur 10/10 fichiers de la couche différenciante, le bus factor effectif est de 1. Sur le socle hérité, il est dilué (agent.py = 9 auteurs, run_ui.py = 9, models.py = 10), ce qui en fait paradoxalement le terrain de lecture le plus sûr pour Aya.

→ **Cible J+90** : bus factor moyen sur les 10 modules cibles passé de 1.0 à ~1.4 (au moins 1 module en bus factor 2, plusieurs en lecture critique partagée).

---

## 3. Zones de criticité — heatmap d'intervention

### 3.1 Modules à protéger temporairement (M1-M2)

| Catégorie | Fichiers | Justification |
|---|---|---|
| Cœur intouchable | `python/consensus/engine.py`, `integrity_block.py`, `auth.py`, `authorization.py`, `path_safety.py`, `criticality_router.py`, `code_execution_tool.py` | Régression silencieuse = perte de propriété de garde-fou. Modification uniquement en pair programming fondateur. |
| Lecture-seule jusqu'à J+30 | `metacognition.py`, `reasoning_engine.py`, `dynamic_risk_register.py`, `human_review.py`, `replay_engine.py`, `audit_report_renderer.py`, `compliance_grid.py` | Doctrine en cours de maturation. Lecture critique d'abord. |
| Pipelines métier | `legal_pipeline.py`, `legal_orchestrator.py`, `contract_drafting/`, `strategic_orchestrator.py` | Compréhension M1, contribution périphérique M2 sur sous-modules isolés (ex: `templates/`). |

### 3.2 Modules ouverts dès S1 (zones périphériques sans risque)

- `agents/*/_context.md` (uniformisation profils)
- `python/helpers/chat_style.py` (personnalisation chat — petit, isolé)
- Scripts opérationnels (`scripts/`)
- Tests directs manquants : `audit_report_renderer`, `integrity_block`, `collaborative_consensus` (écriture de tests = ingénierie inverse pédagogique)
- Documentation API (inventaire des 71 endpoints)
- Runbooks RGPD / sécurité

---

## 4. Quick wins techniques — Aya peut livrer dès S1-S4

| # | Quick win | Effort | Risque | Owner cible |
|---|---|:---:|:---:|---|
| QW1 | Pre-commit hook git appliquant la règle `.cursor/rules/pre-commit-audit.mdc` | 1j | Très faible | Aya J3-J5 |
| QW2 | Monitoring file descriptors prod (cron horaire + alerte >800/1024) | 2h | Très faible | Aya S1 |
| QW3 | Logging structuré JSON sur erreurs 500 + correlation_id retourné utilisateur | 4h | Faible | Aya S2 |
| QW4 | Uniformisation `_context.md` des 12 profils d'agents | 1j | Nul | Aya S2 |
| QW5 | Tests directs manquants : `test_audit_report_renderer.py`, `test_integrity_block.py`, `test_collaborative_consensus.py` | 3-4j | Très faible | Aya S5-S7 |
| QW6 | Build Docker en CI (`main_gate.yml`) — non bloquant en première itération | 1j | Faible | Aya M2 |
| QW7 | Smoke test post-déploiement (curl `/healthz` + `/observability_metrics`) | 4h | Faible | Aya S2 |
| QW8 | Inventaire des 71 endpoints API (table owner/auth/scope) | 2-3j | Nul | Aya S3 |
| QW9 | Pre-flight check des variables d'environnement critiques avant commit prod | 4h | Très faible | Aya S2 |
| QW10 | Runbook purge RGPD reproductible (sur base du flux Scriptoura récent) | 1j | Nul | Aya S4 |

> Aucun quick win ne touche un module mono-auteur fondateur en M1, **sauf** QW5 (tests sur audit_report_renderer / integrity_block / collaborative_consensus). Sur ces trois modules, Aya **écrit les tests** ; elle ne modifie pas le code production. C'est de l'ingénierie inverse contrôlée et pédagogiquement très efficace.

---

## 5. Plan 30 jours — observation produit + lecture doctrinale + contributions périphériques

> **Mission M1** : Aya devient utilisatrice avancée d'Evidence (perspective client), lit la doctrine (5 ADR + onboarding v7.1 + 2 livrables d'audit hostile interne), et livre 4-5 quick wins périphériques. Aucune modification de la couche KOREV propriétaire.

### Semaine 1 — Setup + perspective utilisateur

| Jour | Action | Vérification |
|---|---|---|
| J1 | 1:1 fondateur (90 min, plan, accès, vocabulaire) — provisionnement compte `aya@korev-ai` (déjà MEMBER en prod) | Accès vérifié |
| J2 | Démarrer 3 sessions Evidence en miroir des 3 cas client réels (DICA prospection, Centrale Lille, Epoque LinkedIn) — observation utilisateur | 3 sessions persistées |
| J3 | Setup local (`uv sync`, `.env` minimal, lancement `run_ui.py`, suite tests `pytest tests/ -q` en local) | Suite locale verte |
| J4-J5 | Lecture intégrale `docs/DEVELOPER_ONBOARDING_ARCHITECTURE_GUIDE.md` v7.1 (1196 lignes, ~6h effectives) | Annotations remontées en 1:1 |

### Semaine 2 — Lecture doctrine + premiers livrables

| Jour | Action | Vérification |
|---|---|---|
| J6 | ADR-001 (Consensus PRISM fail-closed) + 1 page de critique constructive | Doc remonté |
| J7 | ADR-002 (Router déterministe anti-injection) + test de routage sur 5 prompts d'injection | Captures |
| J8 | ADR-003 (Framework Evidence + 10 blocs canoniques) + ouverture d'un `audit_report.pdf` réel sur le serveur (session beatrice ou benj) | Annotation des 10 blocs |
| J9 | ADR-004 (LiteLLM) + ADR-005 (Extensions hooks) | — |
| J10 | **QW1 : pre-commit hook** + **QW2 : monitor FD** | Hook actif sur 1 commit, cron en place |

### Semaine 3 — Premiers contributions techniques

| Jour | Action | Vérification |
|---|---|---|
| J11-J12 | Lecture profil `legal_safe` (prompts 744 lignes + extension `_10_legal_safe_pipeline.py`) — schéma de flux | Schéma livré |
| J13 | Tracer chaîne de délégation complète sur session existante (cf. onboarding §2.3) — identification consensus PRISM dans logs Docker | Trace annotée |
| J14 | **QW7 : smoke test post-deploy** + **QW9 : pre-flight env check** | Scripts livrés |
| J15 | **QW3 : logging structuré erreurs 500** | PR mergée |

### Semaine 4 — Consolidation

| Jour | Action | Vérification |
|---|---|---|
| J16-J18 | **QW8 : inventaire endpoints API** (pair programming Amine sur les 10 premiers, autonome ensuite) | Doc partiel ~30+ endpoints |
| J19 | **QW10 : runbook purge RGPD** (basé sur le flux Scriptoura récent) | Runbook livré |
| J20 | **QW4 : uniformisation `_context.md` des 12 profils** | PR mergée |
| J21 | Lecture audit hostile interne (`01-executive-summary.md` + `05-angle-morts-et-decote-potentielle.md`) | Briefing 1:1 |
| J22 | **Revue 30 jours** : KPIs §9 + GO/NO-GO M2 | Compte-rendu écrit |

### Critères de réussite J+30

- 3+ sessions Evidence générées en utilisation réelle (audit_reports persistés).
- 5 ADR + onboarding v7.1 + 2 livrables audit hostile lus, commentés en écrit.
- 4 à 6 PR mergées sur quick wins périphériques.
- Aya peut expliquer en 5 minutes la distinction Evidence / PRISM / KOREV.
- Document de critique constructive des 5 ADR remis (questions, ambiguïtés).

---

## 6. Plan 60 jours — premier transfert de propriété

> **Mission M2** : Aya devient seule propriétaire d'un module de la couche KOREV. Elle livre les tests directs manquants. Elle conduit son premier audit hostile interne.

### Cible recommandée — `python/helpers/processing_register.py`

**Pourquoi ce choix** :
- Petit (~300 LOC), isolé.
- Concerne RGPD Art. 30 — fort enjeu commissaire aux apports, faible risque opérationnel immédiat.
- Aujourd'hui template statique enrichi (cf. onboarding §1.11 *Limites*) — **vrai travail technique à mener** (passage à un registre dynamique réel).
- Pilotable de bout en bout par Aya : conception → ADR-006 → implémentation → tests → déploiement.

### Cibles secondaires possibles

`python/helpers/chat_style.py`, `python/helpers/risk_register.py`, `python/helpers/source_taxonomy.py`.

### Semaines 5-8

| Semaine | Action | Livrable |
|---|---|---|
| S5 | Aya rédige draft **ADR-006 — Processing Register dynamique** (modèle ADR-001..005) | Draft ADR + revue fondateur |
| S6 | Implémentation (analyse runtime des données traitées par session) | PR avec couverture test ≥85% |
| S7 | **QW5** : tests directs sur `audit_report_renderer`, `integrity_block`, `collaborative_consensus` | 30+ tests cumulés |
| S8 | **Premier audit hostile interne autonome** sur un module fondateur (suggestion : `criticality_router.py`) | 1 fichier `audit-hostile-internal/` |

### Travaux parallèles M2

- Chantier isolation chats par utilisateur (cf. onboarding §2.1 ÉLEVÉ) : pair programming fondateur, Aya conduit.
- Build Docker en CI (QW6).
- **Chantier humain review blocage effectif** : intégrer `is_review_blocking()` dans `poll.py` (cf. onboarding §1.15 NB CRITIQUE — *écart entre capacité déclarée et verrou bloquant effectif*). Aya pilote.

### Critères de réussite J+60

- Aya seule propriétaire documentée d'au minimum 1 module KOREV.
- 30+ tests écrits par Aya sur 3 modules critiques précédemment non testés directement.
- ADR-006 rédigée par Aya, mergée dans `docs/adr/`.
- 1 audit hostile interne livré.
- Bus factor sur Processing Register passé de 1 à 2.
- Build Docker en CI vert et bloquant sur main.

---

## 7. Plan 90 jours — Aya audite, codécide, GO/NO-GO PRISM

### Semaines 9-12

| Semaine | Action | Livrable |
|---|---|---|
| S9 | Audit hostile complet d'un domaine choisi : (a) métacognition + reasoning_engine + dynamic_risk_register, (b) tout `python/security/`, (c) tout `contract_drafting/` | Livrable `audit-hostile-internal/0X-<domaine>.md` |
| S10 | Aya devient co-propriétaire d'un second module (ex: `risk_register.py` ou `compliance_grid.py`) | PR refactoring + tests |
| S11 | Pair programming intensif sur module fondateur (suggestion : `criticality_router.py`) — documentation d'invariants + tests de propriété + ADR-007 | ADR-007 + property tests |
| S12 | **Revue 90 jours** : KPIs + décision GO/NO-GO PRISM | Compte-rendu décisionnel signé |

### Cible bus factor J+90

| Module | M0 | M1 | M2 | M3 |
|---|:---:|:---:|:---:|:---:|
| `processing_register.py` | 1 | 1 | **2 (Aya owner)** | 2 |
| `risk_register.py` | 1 | 1 | 1 | **2 (Aya co-owner)** |
| `chat_style.py` | 1 | 1 | 1 | **2 (Aya owner)** |
| `audit_report_renderer.py` (tests) | 0 | 0 | **+30 tests Aya** | tests + co-doc |
| `integrity_block.py` (tests) | 0 | 0 | **+15 tests Aya** | tests + co-doc |
| `criticality_router.py` | 1 | 1 | 1 | **Pair-prog actif** |
| `consensus/engine.py` | 1 | 1 | 1 | **1.2 (Aya en review)** |

### Critères GO PRISM (tous nécessaires)

1. Aya a livré au moins 1 audit hostile sur la doctrine Evidence avec niveau de qualité comparable à l'audit interne existant.
2. Aya est seule propriétaire d'au moins 1 module avec couverture test >85% et bus factor 2.
3. Aucune régression introduite par Aya sur Evidence en M1-M3 (zéro rollback).
4. Le fondateur estime qu'Aya a saisi la doctrine "fail-closed by default".
5. Le besoin business sur PRISM est priorisé (pipeline / brevet à industrialiser).

Si **un seul critère** manque → NO-GO PRISM, prolongation Evidence en M4.

---

## 8. KPIs de progression

### 8.1 KPIs primaires (revue mensuelle)

| KPI | Cible J+30 | Cible J+60 | Cible J+90 |
|---|:---:|:---:|:---:|
| Bus factor moyen sur 10 modules KOREV mono-auteur | 1.0 | 1.2 | 1.4 |
| Modules dont Aya est sole/co-owner | 0 | 1 | 3 |
| Tests écrits par Aya (cumul) | 0-5 | 30+ | 80+ |
| PR Aya mergées sur main | 4-6 | 15+ | 30+ |
| Régression introduite par Aya (rollback) | 0 | 0 | 0 |
| ADR rédigées par Aya | 0 | 1 | 2-3 |
| Audits hostiles internes livrés | 0 | 1 | 2-3 |

### 8.2 KPIs secondaires (suivi continu)

| KPI | Cible | Source |
|---|---|---|
| File descriptors prod | <800 / 1024 moyenne | `scripts/monitor_fd.sh` (QW2) |
| Cold start container après deploy | <90s | `scripts/post_deploy_smoke.sh` (QW7) |
| Couverture tests (hors webui) | passer de "non mesurée" à 70%+ | `pytest --cov` en CI |
| Build Docker green sur main | 100% | GitHub Actions |
| Pre-commit hook respecté | 100% commits Aya | git log + hook |
| Endpoints documentés | 71/71 | `docs/API_INVENTORY.md` |

### 8.3 Test de transmission qualitatif (J+90)

Aya doit pouvoir, sans accès au code, expliquer à un tiers technique externe :

- Pourquoi le router est déterministe et pas LLM-driven (ADR-002).
- Pourquoi le consensus est fail-closed et pas fail-soft (ADR-001).
- Comment les 10 blocs canoniques du rapport d'audit cartographient AI Act Art. 9/13/14/17 + RGPD Art. 30 (ADR-003).
- Pourquoi `EVIDENCE_HMAC_KEY` lève RuntimeError plutôt que de passer en HMAC dégradé (ADR-003).

Si elle réussit ce test → la doctrine est transmise. Si elle peine → le plan doit être prolongé d'un trimestre minimum.

---

## 9. RACI cible J+90

### 9.1 Couche cœur intouchable

| Module | R | A | C | Évolution attendue |
|---|:---:|:---:|:---:|---|
| `agent.py` | Fondateur | Fondateur | Aya | Review-only |
| `python/helpers/execution_budget.py` | Fondateur | Fondateur | Aya | Tests + lecture invariants |
| `python/security/auth.py`, `authorization.py`, `path_safety.py` | Fondateur | Fondateur | Aya | Tests sécurité supplémentaires |
| `run_ui.py` | Fondateur | Fondateur | Aya | Handlers d'erreur (QW3) |

### 9.2 Couche IA de confiance — territoire de transmission

| Module | R | A | C | Évolution attendue |
|---|:---:|:---:|:---:|---|
| `python/consensus/engine.py` | Fondateur | Fondateur | Aya | Pair programming S11 |
| `criticality_router.py` + `router/policy.py` | Fondateur | Fondateur | Aya | ADR-007 par Aya |
| `audit_report_renderer.py` | Fondateur | Fondateur | **Aya** | Tests directs (S7) |
| `integrity_block.py` | Fondateur | Fondateur | **Aya** | Tests directs (S7) |
| `replay_engine.py` | Fondateur | Fondateur | **Aya** | Review-only |
| `human_review.py` | Fondateur | Fondateur | **Aya** | **Aya intègre `is_review_blocking()` dans `poll.py` en M2** |
| `dynamic_risk_register.py` | Fondateur | Fondateur | **Aya** | Review-only |
| `compliance_grid.py` | Fondateur | Fondateur | Aya | Co-owner J+90 |
| `processing_register.py` | Fondateur | Fondateur | Aya | **Seule R+A J+60** |
| `risk_register.py` | Fondateur | Fondateur | Aya | Co-owner J+90 |
| `metacognition.py` + `reasoning_engine.py` | Fondateur | Fondateur | Aya | Cible audit hostile S9 |

### 9.3 Périphériques — Aya owner J+30

`agents/*/_context.md`, `python/helpers/chat_style.py`, `docs/API_INVENTORY.md`, `scripts/monitor_fd.sh`, `scripts/post_deploy_smoke.sh`, `scripts/precommit_audit.sh`, `audit-hostile-internal/*.md`, `docs/RUNBOOK_PURGE_RGPD.md`.

---

## 10. Risques d'intégration et mitigations

### 10.1 Risques côté Aya

| Risque | Probabilité | Symptôme déclencheur | Mitigation |
|---|:---:|---|---|
| Submersion par la doctrine (1196 lignes onboarding + 5 ADR + 8 livrables audit) | Élevée | Aya déclare "lu" sans pouvoir reformuler | 1:1 hebdomadaire avec questions du fondateur (oral, QCM-style) — pas l'inverse |
| Confusion PRISM / Evidence | Élevée | Aya parle de "PRISM-Oracle" pour désigner le produit | Vocabulaire imposé dès J1 (cf. onboarding §2.6) |
| Tentation de refactoring monolithes (settings.py 2232, agent.py 1144) | Élevée | "Je voudrais nettoyer settings.py..." | Veto explicite jusqu'à J+90 — cadre formel "patcher vs accepter" §2.5 onboarding |
| Perte sur les 24 hooks d'extension | Moyenne | Aya ajoute extension qui casse l'ordre | Aucune nouvelle extension avant J+45. Toute ajout en review obligatoire |
| Frustration setup outils (uv, MCP, Playwright, Tesseract, fonts) | Moyenne | Aya bloque 1 journée sur un setup | Setup en pair programming J3 — pas en solo |
| Sur-investissement frontend (1300 LOC, polling fragile) | Moyenne | Aya propose migration React | Frontend hors périmètre M1-M3 sauf urgence — règle écrite |
| Sur-test low-value | Moyenne | Aya écrit 200 tests faibles au lieu de 30 ciblés | QW5 cible explicite : 3 modules, ≥30 tests cumulés |

### 10.2 Risques côté fondateur

| Risque | Mitigation |
|---|---|
| Charge de transmission excessive (>12h/semaine) compromet le delivery business | **Slot quotidien fixe (ex: 10h-12h) bloqué dans calendrier, non extensible**. Au-delà, reporter à J+1. |
| Le codebase évolue trop vite en M1-M2 sur la couche KOREV — Aya court derrière | Moratoire informel sur nouvelles features de la couche KOREV en M1-M2 sauf urgence client. Le delivery passe par les pipelines métier (legal, strategic) pour lesquels Aya peut être consultée. |
| Reviewer fatigue : Amine devient une "machine à reviewer" | Limiter à 3 PR Aya en review simultanée. Au-delà : Aya consolide avant nouvelle PR. |
| Le delivery client absorbe tout le temps fondateur | 1:1 hebdo non négociable, même 30 min minimum. Ne jamais sauter 2 semaines consécutives. |

### 10.3 Risques produit — écarts entre capacité déclarée et verrou bloquant effectif

Ces écarts sont **documentés en interne** (cf. onboarding v7.1) mais doivent être traités avant exposition externe formelle (commissaire aux apports, audit conformité, due diligence investisseur).

| Élément | État réel (cf. onboarding) | Action en M1-M3 |
|---|---|---|
| Human review workflow | Workflow fonctionnel (création, décision, audit trail). **Le blocage effectif de la réponse n'est pas intégré dans la chaîne de livraison (`poll.py`).** En l'état, c'est un registre consultatif, pas un verrou bloquant. | **P0 M2** : Aya intègre `is_review_blocking()` dans `poll.py`. |
| Suite tests étendue CI | `continue-on-error: true` — des échecs sont silencieusement non-bloquants. | M2 : passer suite étendue en bloquant sur main, après un cycle de stabilisation. |
| Replay engine | "Replay" est un terme imprécis : c'est un mécanisme de snapshot + comparaison (Jaccard sur mots), pas une re-exécution déterministe LLM. | Reformuler la documentation externe en "snapshot + verification d'intégrité + comparaison post-hoc". |
| Sandbox `code_execution_tool` | Pas de sandbox réel (pas de container séparé, pas de seccomp, pas de cgroups). | M3+ : chantier prioritaire. Hors périmètre Aya jusqu'à expertise consolidée. |
| Mode sans authentification par défaut | Si config absente, l'app démarre sans auth. | M2 : durcir — refus de démarrer sans `AUTH_LOGIN`/`AUTH_PASSWORD` ou `KOREV_PRODUCTION=true`. |
| Multi-tenant fail-closed | Vrai au niveau API. Au niveau filesystem (volume Docker), un accès direct contourne. | M3+ : isolation filesystem via sous-dossiers par utilisateur (Chantier #1 onboarding). |
| Consensus 3 rounds | En pratique 2 rounds si unanimité Round 1. Verdict final = décision d'un seul LLM (`arbiters[0]`, temperature=0.1). | Reformuler externe : "consensus 2-3 rounds avec verdict synthétisé par arbitre principal". Aligner ADR-001 avec le code réel. |

→ Aya doit avoir cette grille en tête. Le but n'est pas de "découvrir des défauts" mais de **rendre le narratif externe cohérent avec la réalité technique**, pour qu'elle puisse défendre le projet sans risque de se faire piéger.

---

## 11. Charge fondateur — calibrage réaliste

### 11.1 Cible de charge hebdomadaire

| Phase | Fourchette | Format |
|---|:---:|---|
| M1 (S1-S4) | **8-12h/semaine** | 1:1 hebdo (1h) + slot quotidien fixe (1-2h) + revues PR (3-4h cumulé) |
| M2 (S5-S8) | **6-8h/semaine** | 1:1 hebdo (1h) + 2 sessions pair-prog/sem (2-3h chacune) + revues PR (1-2h) |
| M3 (S9-S12) | **4-6h/semaine** | 1:1 hebdo (45 min) + 1 session pair-prog/sem (2-3h) + revues PR (1h) |

### 11.2 Anti-patterns à éviter

- Slot fondateur extensible ad libitum → produit le burnout avant la fin de M2.
- Reporter ou sauter le 1:1 hebdo plus d'1 fois par mois → produit la dérive.
- Se transformer en "machine à reviewer" (revue 100% du code Aya) → produit la régression de productivité fondateur.
- Aya en CC sur tous les threads clients dès J1 → produit la submersion contextuelle.
- Aucun retour formel sur les questions Aya → produit la perte de motivation.

### 11.3 Comparaison vs continuité solo fondateur

Le coût mensuel de transmission (8-12h/sem × 4 semaines = 32-48h/mois en M1) est compensé en M3 par la délégation effective des reviews PR Aya et de la maintenance des modules transférés. Le break-even est attendu vers J+90 si les KPIs §8 sont tenus.

---

## 12. Recommandations organisationnelles

### 12.1 Rituels minimum viables

| Rituel | Fréquence | Durée | Format |
|---|---|---|---|
| 1:1 fondateur ↔ Aya | Hebdomadaire | 60 min M1, 45 min M2-M3 | Questions fondateur → Aya, revue blockers |
| Stand-up async (écrit) | Quotidien | 5 min | Yesterday / Today / Blockers |
| Revue PR | À la PR | Variable | Template audit hostile |
| Pair programming | 2x/sem M1, 1-2x/sem M2-M3 | 2-3h | Fondateur conduit M1, Aya conduit M2-M3 |
| Revue mensuelle KPIs | Mensuelle | 90 min | KPIs §8 + décision passage phase suivante |
| Doctrine writing (ADR) | Bi-mensuelle | 1 jour bloqué | Aya rédige draft à partir M2 |

### 12.2 Doctrine à imposer dès J1

| Règle | Justification |
|---|---|
| Vocabulaire imposé : KOREV / Evidence / PRISM (cf. §2.6 onboarding) | Évite confusion documentée |
| Pre-commit hook obligatoire | Audit hostile sur chaque commit (QW1) |
| Pas de `git push --force` sur `main` | Standard |
| Branche `main` = production | Pas d'environnement staging actuellement |
| Modification des modules §3.1 → veto fondateur | Sécurité doctrine |
| Toute nouvelle fonctionnalité majeure → ADR ou refus | À partir M2 |

---

## 13. Gouvernance — décisions à prendre maintenant

| # | Décision | Délai | Owner |
|---|---|---|---|
| 1 | Acter le bus factor sur la couche KOREV comme risque organisationnel principal | Cette semaine | Fondateur |
| 2 | Bloquer 8-12h/semaine fondateur en M1 dans le calendrier (slot fixe quotidien) | Avant J+0 | Fondateur |
| 3 | Communiquer à Aya la séquence Evidence d'abord, PRISM après J+90 | Avant J+0 | Fondateur |
| 4 | Installer pre-commit hook (cf. règle déclarative `.cursor/rules/pre-commit-audit.mdc`) | Cette semaine | Fondateur ou Aya J3 |
| 5 | Persister ce plan en docs/ (ce fichier) + version Aya transmissible (`ONBOARDING_AYA_30_60_90.md`) | Aujourd'hui | Fondateur |
| 6 | Calendrier de revue : J+30, J+60, J+90 fixés maintenant | Aujourd'hui | Fondateur |
| 7 | Acter qu'Aya ne touche pas aux 7 modules cœur (§3.1) jusqu'à J+90 | Avant J+0 | Fondateur |
| 8 | Décider si la cible M2 reste `processing_register.py` (recommandé) ou autre | Avant J+30 | Fondateur |
| 9 | Commit du chantier local courant (audit-hostile-valorisation/, ADRs, scripts) sur GitHub pour qu'Aya y accède | Cette semaine | Fondateur |

---

## 14. Prompt de contrôle hostile — audit du plan à J+30, J+60, J+90

À utiliser en mode "VP Engineering externe" sur la situation réelle observée.

```text
[CONTEXTE]
Audit externe du plan d'intégration 30/60/90 de la Lead Engineer KOREV AI.
Document de référence : docs/PLAN_INTEGRATION_LEAD_ENGINEER_30_60_90_INTERNAL.md
Posture : zéro complaisance, vérification factuelle uniquement.

[DONNÉES À COLLECTER AVANT AUDIT]
1. git shortlog -sn --since="<début phase>" -- python/helpers python/consensus python/security
2. Liste des PR Aya mergées : numéros, modules, LOC, durée de review
3. Modules dont l'ownership a effectivement été transféré (RACI mis à jour)
4. KPIs §8 mesurés vs cibles
5. Incidents production sur la fenêtre + qui les a résolus
6. Heures hebdo effectives fondateur consacrées à Aya (calendrier réel)
7. Tests écrits par Aya (count + couverture des modules cibles)
8. ADR / audits hostiles produits par Aya
9. Modules KOREV mono-auteur fondateur après la phase
10. Indicateurs de surcharge fondateur : délai médian de review, hotfix solo, congés

[AUDIT À EFFECTUER]
1. Cohérence du plan : KPIs ciblés (§8) tous mesurés ? Lesquels ratés ?
2. Bus factor réel : sur les modules cibles (§9), l'ownership a-t-il vraiment bougé,
   ou est-ce uniquement déclaratif ?
3. Charge cognitive Aya : nombre de modules touchés simultanément, profondeur de PR.
4. Charge fondateur : ratio review/build dans son temps. Est-il devenu reviewer-only ?
5. Angles morts : modules critiques jamais abordés en pair programming ni review profonde.
6. Test de transmission : Aya peut-elle reformuler les 5 ADR sans accès au code ?
   Si non, la transmission est cosmétique.
7. Risque opérationnel résiduel : si fondateur indisponible 2 semaines dès demain,
   quels modules deviennent orphelins ?
8. Dérive du périmètre : Aya a-t-elle été embarquée sur PRISM ou hors plan ?
9. Coût économique : heures fondateur transmission vs heures gagnées en délégation effective.
10. Documentation produite : ADR + audits + runbooks utilisables par un tiers externe ?

[LIVRABLES ATTENDUS]
A. Tableau "objectifs vs atteints" par section §5/6/7.
B. Liste DEF (défauts) sur le modèle audit-hostile-valorisation/ : 
   Critique / Important / Modéré / Mineur, traceabilité au repo.
C. Verdict GO/NO-GO sur passage à la phase suivante.
D. 3 recommandations correctives prioritaires.
E. Mise à jour matrice RACI §9 avec l'état réel.
F. Recalcul du bus factor moyen vs cible.
```

---

## 15. Liens documentaires

- Document Aya transmissible : `docs/ONBOARDING_AYA_30_60_90.md`
- Onboarding technique v7.1 : `docs/DEVELOPER_ONBOARDING_ARCHITECTURE_GUIDE.md`
- ADR (5) : `docs/adr/ADR-001` à `ADR-005`
- Audit hostile interne : `audit-hostile-valorisation/`
- Règle pre-commit : `.cursor/rules/pre-commit-audit.mdc`
- Glossaire : `docs/GLOSSARY.md`

---

*Plan révisé le 4 mai 2026. Mise à jour obligatoire après chaque revue mensuelle (J+30, J+60, J+90). Source de vérité ultime : code et git history du repo, pas ce document.*
