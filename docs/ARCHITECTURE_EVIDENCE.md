# Architecture KOREV Evidence — Vue synthèse

**Version** : v1.3.1 · **Public** : architectes, développeurs, auditeurs · **Langue** : français

Ce document synthétise l'architecture **propre à KOREV Evidence**. Pour le framework générique hérité d'Agent Zero, voir [architecture.md](architecture.md). Pour les diagrammes C4, voir [architecture/C4_DIAGRAMS.md](architecture/C4_DIAGRAMS.md).

---

## 1. Positionnement

KOREV Evidence est un fork du framework open-source **Agent Zero** (MIT) enrichi de couches propriétaires pour les professions réglementées :

| Couche | Rôle |
|--------|------|
| **Evidence** | Sorties critiques signées, chaîne de preuve, fail-closed |
| **PRISM** | Consensus multi-LLM (API `run_consensus`) |
| **Legal-Safe** | Pipeline juridique (sources officielles, Act Leak Guard) |
| **Multi-tenant** | Isolation par organisation et workspace utilisateur |

---

## 2. Vue conteneurs (déploiement)

```text
                    Internet
                       │
              ┌────────▼────────┐
              │  Caddy (TLS)    │  evidence-caddy :80/:443
              └────────┬────────┘
                       │
         ┌─────────────┴─────────────┐
         ▼                           ▼
┌─────────────────┐         ┌─────────────────┐
│ Flask backend   │         │  Static webui   │
│ evidence-backend│         │  (HTML/CSS/JS)  │
│ run_ui.py :5050 │         └─────────────────┘
└────────┬────────┘
         │
    ┌────┴────┬──────────┬──────────┐
    ▼         ▼          ▼          ▼
┌────────┐ ┌──────┐ ┌───────┐ ┌───────┐
│Volumes │ │Samba │ │  MCP  │ │ LLM   │
│ Docker │ │shared│ │servers│ │providers│
│data/   │ │users/│ │       │ │LiteLLM│
│tmp/    │ └──────┘ └───────┘ └───────┘
│audit/  │
│memory/ │
└────────┘
```

Postgres (ADR-007) est prévu via profil Docker `db` — état d'adoption à confirmer par déploiement.

---

## 3. Pipeline requête → sortie (chemin critique)

```text
Requête utilisateur (POST /message)
        │
        ▼
Agent.monologue()
        │
        ▼
criticality_router.assess()     ← LEVEL 1 / 2 / 3
        │
        ├─ LEVEL 1 ──────────────────► réponse directe
        │
        └─ LEVEL 2/3 (consensus requis)
                │
                ▼
        call_subordinate (délégation)
                │  profils : legal_safe, medical, finance, …
                ▼
        run_consensus() [PRISM v2]   ← quorum 2/3
                │
                ▼
        critical_output.finalize_critical_output()
                │  signature v2 (RSA-PSS ou HMAC)
                ▼
        Sortie signée ou FAIL_CLOSED explicite
```

Références vérifiées :

- [audit/critical_request_path_map.md](audit/critical_request_path_map.md)
- [architecture/EVIDENCE_DELEGATION_ARCHITECTURE_VERIFIED.md](architecture/EVIDENCE_DELEGATION_ARCHITECTURE_VERIFIED.md)
- [adr/ADR-010-critical-output-doctrine.md](adr/ADR-010-critical-output-doctrine.md)

---

## 4. Composants backend principaux

| Module | Chemin | Rôle |
|--------|--------|------|
| Application Flask | `run_ui.py` | Routes login, session, enregistrement API |
| Agent | `agent.py` | Boucle monologue, contextes, délégation |
| Criticality router | `python/helpers/criticality_router.py` | Classification LEVEL 1/2/3 |
| Consensus engine | `python/consensus/engine.py` | `run_consensus()` — API canonique |
| Critical output | `python/helpers/critical_output.py` | Finalisation + signature |
| Délégation | `python/tools/call_subordinate.py` | Appel agents subordonnés |
| Task scheduler | `python/helpers/task_scheduler.py` | Tâches cron + retry auto ERROR |
| User manager | `python/helpers/user_manager.py` | Auth Argon2, overlay mots de passe |
| Authorization | `python/security/authorization.py` | RBAC, org OWNER/MEMBER |
| Persist chat | `python/helpers/persist_chat.py` | `tmp/chats/{id}/chat.json` |

---

## 5. Profils agents (11 + gabarit)

| Profil | Dossier | Domaine |
|--------|---------|---------|
| default | `agents/default/` | Agent générique |
| multitask | `agents/multitask/` | Orchestrateur principal |
| legal_safe | `agents/legal_safe/` | Analyse juridique |
| legal_drafting_guarded | `agents/legal_drafting_guarded/` | Rédaction contractuelle |
| medical | `agents/medical/` | Santé / FAERS |
| finance | `agents/finance/` | Finance |
| researcher | `agents/researcher/` | Recherche académique |
| developer | `agents/developer/` | Développement |
| marketing | `agents/marketing/` | Marketing |
| sales | `agents/sales/` | Commercial |
| hacker | `agents/hacker/` | Cybersécurité |
| contradictor | `agents/contradictor/` | Contradicteur / adversarial |

Référence interne : [PROFILS_AGENTS_REFERENCE.md](PROFILS_AGENTS_REFERENCE.md).

---

## 6. Persistance des données

| Donnée | Emplacement | Isolation |
|--------|-------------|-----------|
| Chats | `tmp/chats/{ctxid}/chat.json` | Filtrage API par org + owner (pas de sous-dossier par user) |
| Tâches scheduler | `tmp/scheduler/tasks.json` | Champs `username`, `organization` |
| Workspaces fichiers | `shared/users/{username}/` | Samba + path safety |
| Mémoire agents | `memory/` (volume Docker) | Par contexte |
| Audit | `audit/` (volume Docker) | Logs sécurité |
| Users | `deploy/users.json` (:ro) + `data/users.local.json` (overlay mots de passe) | Multi-tenant |

> **Dette connue** : stockage chats global — isolation uniquement à la couche API. Voir [DEVELOPER_ONBOARDING_ARCHITECTURE_GUIDE.md](DEVELOPER_ONBOARDING_ARCHITECTURE_GUIDE.md).

---

## 7. Sécurité

| Mécanisme | Implémentation |
|-----------|----------------|
| Authentification | Argon2id (`python/security/auth.py`) |
| Session | Flask cookie HttpOnly, SameSite=Strict, 24 h |
| CSRF | Token session + header `X-CSRF-Token` |
| Rate limiting | Bucket login + API (`python/security/rate_limit/`) |
| RBAC | `role` (admin/user) + `org_role` (OWNER/MEMBER) |
| Path safety | Anti-traversal (`python/security/path_safety.py`) |
| Audit log | `python/security/security_audit.py` |

Spécification multi-user fichiers : [SPEC_MULTI_USER_WORKSPACE.md](SPEC_MULTI_USER_WORKSPACE.md).

---

## 8. API & intégration

~71 endpoints REST sous `python/api/`, montés automatiquement à `/{nom_fichier}`.

- Auth session + CSRF par défaut.
- Endpoints admin : `settings_*`, `observability_metrics`.
- API externe (clé) : `api_message`, `api_log_get`, etc.
- Catalogue complet : [API_REFERENCE.md](API_REFERENCE.md).

---

## 9. ADR (décisions d'architecture)

| ADR | Sujet |
|-----|-------|
| [ADR-006](adr/ADR-006-tool-io-integrity-contract.md) | Intégrité I/O outils |
| [ADR-007](adr/ADR-007-postgres-pgvector-adoption.md) | Postgres + pgvector |
| [ADR-008](adr/ADR-008-consensus-v1-to-v2-migration.md) | Migration consensus v1→v2 |
| [ADR-009](adr/ADR-009-response-gate-disabled.md) | Gate désactivé (historique) |
| [ADR-010](adr/ADR-010-critical-output-doctrine.md) | **Doctrine courante** — fail-closed signé |

---

## 10. Modules legacy (ne pas présenter comme actifs)

| Module | Statut |
|--------|--------|
| `collaborative_consensus` | Réserve P1 — non aligné doctrine signée |
| `research_consensus_integration` | Déprécié |
| `research_pipeline` | Déprécié |
| `consensus_integration.py` | Supprimé |

Voir README racine § Modules legacy.

---

## 11. Documents complémentaires

| Besoin | Document |
|--------|----------|
| Délégation détaillée | [EVIDENCE_DELEGATION_ARCHITECTURE_VERIFIED.md](architecture/EVIDENCE_DELEGATION_ARCHITECTURE_VERIFIED.md) |
| Pipeline chat | [CHAT_DELEGATION_PIPELINE_MAP.md](architecture/CHAT_DELEGATION_PIPELINE_MAP.md) |
| Diagrammes C4 | [C4_DIAGRAMS.md](architecture/C4_DIAGRAMS.md) |
| Chemin critique audité | [critical_request_path_map.md](audit/critical_request_path_map.md) |
| Standard doc technique | [PROJECT_DOCUMENTATION_STANDARD.md](audit/PROJECT_DOCUMENTATION_STANDARD.md) |
| Métriques tests | [METRICS_CANONICAL_SOURCE.md](METRICS_CANONICAL_SOURCE.md) |

---

*Synthèse architecture — KOREV Evidence v1.3.1. Dernière révision : 2026-06-13.*
