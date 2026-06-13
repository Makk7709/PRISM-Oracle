# Onboarding développeur — 30 / 60 / 90 jours

**Version** : v1.3.1 · **Public** : développeurs entrants · **Complète** [DEVELOPER_ONBOARDING_ARCHITECTURE_GUIDE.md](DEVELOPER_ONBOARDING_ARCHITECTURE_GUIDE.md)

Plan structuré pour prendre en main KOREV Evidence en trois phases. Ce document remplace les références historiques absentes (`ONBOARDING_AYA_30_60_90.md`, `PLAN_INTEGRATION_LEAD_ENGINEER_30_60_90_INTERNAL.md`).

---

## Avant de commencer

| Prérequis | Détail |
|-----------|--------|
| Environnement | Python 3.11+, Docker, git |
| Lecture J0 | README racine, [ARCHITECTURE_EVIDENCE.md](ARCHITECTURE_EVIDENCE.md), Partie 2 du guide architecture (**LIRE EN PREMIER**) |
| Index doc | [INDEX_DOCUMENTATION.md](INDEX_DOCUMENTATION.md) |
| Métriques | Ne pas inventer de chiffres — [METRICS_CANONICAL_SOURCE.md](METRICS_CANONICAL_SOURCE.md) |

```bash
# Installation locale rapide
cp deploy/.env.example deploy/.env   # adapter
docker compose -f deploy/docker-compose.yml up -d
# ou
python run_ui.py
```

---

## Phase 1 — Jours 1 à 30 (prise en main)

### Semaine 1 : Cartographie

| Jour | Objectif | Livrable |
|------|----------|----------|
| 1 | Cloner, lancer localement, se connecter | Environnement OK |
| 2 | Lire chemin critique | Notes sur `audit/critical_request_path_map.md` |
| 3 | Tracer un message bout-en-bout | Schéma `POST /message` → `agent.monologue` |
| 4 | Explorer `python/api/` (71 endpoints) | [API_REFERENCE.md](API_REFERENCE.md) parcouru |
| 5 | Mission guidée | [missions/MISSION_AYA_01_cartographie_et_validation_e2e.md](missions/MISSION_AYA_01_cartographie_et_validation_e2e.md) |

**Fichiers clés semaine 1** :

- `run_ui.py` — Flask, auth, enregistrement API
- `agent.py` — `monologue()`, contextes
- `python/helpers/criticality_router.py` — LEVEL 1/2/3
- `python/consensus/engine.py` — `run_consensus()`
- `python/helpers/critical_output.py` — signatures
- `python/security/authorization.py` — multi-tenant

### Semaine 2 : Tests et conventions

| Objectif | Commande |
|----------|----------|
| Collecte tests | `pytest --collect-only -q tests/` |
| Suite rapide | `pytest -q -m fast tests/` (si marqueurs) |
| Tests scheduler | `pytest -q tests/test_scheduler_error_retry.py` |
| Style | Suivre patterns existants — pas de sur-abstraction |

Lire : `docs/development.md`, `docs/contribution.md`, modules `python/security/`.

### Semaine 3 : UI et extensions

| Zone | Chemin |
|------|--------|
| WebUI | `webui/`, Alpine.js stores |
| Sidebar / settings | `webui/components/` |
| Extensions agent | `python/extensions/` |
| Outils | `python/tools/` |
| Prompts runtime | `prompts/`, `agents/*/prompts/` |

Exercice : modifier un libellé UI ou ajouter un test sur un handler API existant (PR petit).

### Semaine 4 : Premier correctif guidé

- Choisir un ticket / bug mineur (docs, test, log).
- Branche `feat/` ou `fix/`.
- Audit hostile sur le diff avant commit (règle `.cursor/rules/pre-commit-audit.mdc`).
- **Livrable J30** : 1 PR mergée ou revue prête + synthèse 1 page du pipeline critique.

---

## Phase 2 — Jours 31 à 60 (contribution autonome)

### Objectifs

| Domaine | Actions |
|---------|---------|
| **Agents** | Lire [PROFILS_AGENTS_REFERENCE.md](PROFILS_AGENTS_REFERENCE.md), modifier un prompt métier sous revue |
| **Délégation** | [architecture/EVIDENCE_DELEGATION_ARCHITECTURE_VERIFIED.md](architecture/EVIDENCE_DELEGATION_ARCHITECTURE_VERIFIED.md) |
| **Scheduler** | `python/helpers/task_scheduler.py`, UI scheduler |
| **Sécurité** | `python/security/`, tests authz |
| **MCP** | `mcp_servers/`, `docs/mcp_setup.md` |

### Projets types (60j)

1. **Endpoint ou extension** : feature isolée + tests.
2. **Hardening** : cas fail-closed manquant sur chemin LEVEL 3.
3. **Observabilité** : métrique ou log structuré (`python/observability/`).

### Revue de code

- Vérifier `can_access_context()` sur tout nouvel endpoint touchant un chat.
- Pas de secret dans le repo.
- ADR si décision structurante (`docs/adr/`).

**Livrable J60** : 2 à 3 PRs significatives + participation revue pairs.

---

## Phase 3 — Jours 61 à 90 (autonomie ops + design)

### Objectifs

| Domaine | Actions |
|---------|---------|
| **Déploiement** | [GUIDE_DEPLOIEMENT_ENTREPRISE.md](GUIDE_DEPLOIEMENT_ENTREPRISE.md), [GUIDE_OPERATEUR.md](GUIDE_OPERATEUR.md), `scripts/deploy_prod.sh` |
| **Incidents** | Lire rapports `docs/reports/INCIDENT_*` |
| **Conformité** | [GUIDE_CONFORMITE_CLIENT.md](GUIDE_CONFORMITE_CLIENT.md), ADR-010 |
| **Architecture** | [architecture/C4_DIAGRAMS.md](architecture/C4_DIAGRAMS.md) — proposer mise à jour si changement |

### Exercice ops (staging ou local)

```bash
./scripts/post_deploy_validate.sh --base-url http://localhost:5050
curl -s http://localhost:5050/healthz
```

### Design / ADR

- Rédiger 1 ADR brouillon si tu introduces un choix technique durable.
- Participer à la roadmap conformité : [FEUILLE_DE_ROUTE_CONFORMITE_FORMAT_EVIDENCE.md](FEUILLE_DE_ROUTE_CONFORMITE_FORMAT_EVIDENCE.md).

**Livrable J90** :

- Capable de déployer, diagnostiquer scheduler, expliquer LEVEL 3 à un client.
- Proposition roadmap personnelle (3 items) validée par lead.

---

## Références par thème

| Thème | Document |
|-------|----------|
| Pipeline pas à pas | [architecture/PIPELINE_PAS_A_PAS_pour_Aya.md](architecture/PIPELINE_PAS_A_PAS_pour_Aya.md) |
| Chat délégation | [architecture/CHAT_DELEGATION_PIPELINE_MAP.md](architecture/CHAT_DELEGATION_PIPELINE_MAP.md) |
| Multi-user | [SPEC_MULTI_USER_WORKSPACE.md](SPEC_MULTI_USER_WORKSPACE.md) |
| Contradicteur | [audits/CONTRADICTOR_AGENT_HOSTILE_AUDIT.md](audits/CONTRADICTOR_AGENT_HOSTILE_AUDIT.md) |
| Release | [RELEASE_NOTES.md](RELEASE_NOTES.md) |

---

## Anti-patterns à éviter

| ❌ | ✅ |
|----|-----|
| Contourner fail-closed sur LEVEL 3 | Respecter ADR-010 |
| OWNER par défaut pour tous | MEMBER sauf superviseurs |
| Chiffres de tests non sourcés | METRICS_CANONICAL_SOURCE |
| Gros refactor sans ADR | PR petites, incrémentales |
| Prompts secrets dans git public | Variables env / vault |

---

*Onboarding développeur 30/60/90 — KOREV Evidence v1.3.1. Dernière révision : 2026-06-13.*
