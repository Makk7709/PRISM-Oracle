# Notes de version — KOREV Evidence

**Produit** : KOREV Evidence · **Canal** : releases production

Ce document recense les changements notables par version. Pour l'historique technique détaillé, voir aussi `docs/CHANGELOG_AUDIT.md` et les rapports dans `docs/reports/`.

---

## v1.3.1 — 2026-06-13 (production)

**Commit de référence prod** : `2c87b4d0` · **URL** : `https://www.korev-evidence.com`

### Interface utilisateur

- **Page de connexion** refondue (neuromarketing, glassmorphism, animations flux de données violet).
- **Logo unifié** : prisme détouré (`korev-evidence-logo-prism.png`) — sidebar, favicon, manifest PWA.
- **Wordmark** agrandi sur la page login.
- **Note self-service** : rappel du changement de mot de passe après connexion.
- **Sidebar** : correction du bouton hamburger invisible quand la barre est repliée (`backdrop-filter: none` en mode `.hidden`).

### Planificateur de tâches (scheduler)

- **Retry automatique** des tâches cron en état `error` à la prochaine occurrence.
- **TTL stale-RUNNING** porté de 900 s à **3600 s** (`EVIDENCE_SCHEDULER_RUN_TTL_SECONDS`).
- Correction fuseau pour `get_next_run`.
- Purge cohérente de `running_since` à la fin d'exécution.
- **10 tests** ajoutés (`tests/test_scheduler_error_retry.py`).
- **Action ops** : 6 tâches prod remises en `idle` après incident juin 2026.

### Documentation (lot 2026-06-13)

- Création et classement de la documentation utilisateur, opérateur, architecture, API, conformité, onboarding.
- Index central : [INDEX_DOCUMENTATION.md](INDEX_DOCUMENTATION.md).

### Comportement inchangé (clarification)

- **OWNER** voit toutes les conversations de son organisation — comportement voulu, pas un bug.

---

## v1.3.0 — 2026-04-02

- Version taguée dans `VERSION.json` (`d674d01a`).
- Doctrine sortie critique **ADR-010** active (fail-closed, signature v2).
- Multi-tenant strict (OWNER/MEMBER).
- Pipeline consensus PRISM v2 (`run_consensus()`).

---

## v1.2.x — 2026 Q1

- Hardening agent médical, pipelines juridiques FTS5.
- Profil **contradicteur** activé (`agents/contradictor/`).
- Notifications, scheduler UI, personnalisation chat.
- Rapports : `SESSION_REPORT_2026-03-30_MULTI_TENANT_SCHEDULER_NOTIFICATIONS.md`.

---

## Incidents documentés

| Date | Document | Résumé |
|------|----------|--------|
| 2026-06-03 | [reports/INCIDENT_2026-06-03_message_loop_deadlock_fd_leak.md](reports/INCIDENT_2026-06-03_message_loop_deadlock_fd_leak.md) | Fuite FD, deadlock boucle message |
| 2026-06-01 | [GUIDE_OPERATEUR.md](GUIDE_OPERATEUR.md) §4.2 | Scheduler tâches bloquées en `error` |

---

## Versions futures (planifié)

Voir feuilles de route internes :

- Migration Postgres + pgvector (ADR-007, profil Docker `db`)
- Renforcement prompts / délégation agents (standards postes)
- Couverture tests étendue (métriques canoniques : [METRICS_CANONICAL_SOURCE.md](METRICS_CANONICAL_SOURCE.md))

---

*Notes de version — KOREV Evidence. Dernière révision : 2026-06-13.*
