# Diagrammes C4 — KOREV Evidence

**Version** : v1.3.1 · **Public** : architectes, auditeurs · **Format** : C4 (Contexte, Conteneurs, Composants)

> Ce document remplace la référence absente `ARCHITECTURE_C4_DIAGRAMS.md` citée dans `PROJECT_DOCUMENTATION_STANDARD.md`. Les diagrammes sont en Mermaid (rendu GitHub / IDE).

---

## Niveau 1 — Contexte système

```mermaid
C4Context
    title KOREV Evidence — Diagramme de contexte

    Person(user, "Utilisateur", "Professionnel réglementé")
    Person(admin, "Administrateur IT", "Déploie et configure")
    Person(owner, "Superviseur OWNER", "Voit toutes les conversations de l'org")
    Person(auditor, "Auditeur / DPO", "Rapports audit, revue humaine")

    System(evidence, "KOREV Evidence", "Plateforme multi-agents IA de confiance")
    System_Ext(llm, "Fournisseurs LLM", "Anthropic, OpenAI, OpenRouter…")
    System_Ext(mcp, "Sources MCP", "PubMed, OpenAlex, Semantic Scholar")
    System_Ext(legal, "Sources juridiques", "Légifrance, Judilibre, CNIL")

    Rel(user, evidence, "Chat, fichiers, tâches", "HTTPS")
    Rel(admin, evidence, "Déploiement, paramètres", "SSH/Docker")
    Rel(owner, evidence, "Supervision org", "HTTPS")
    Rel(auditor, evidence, "Audit, replay", "HTTPS")
    Rel(evidence, llm, "Inférences", "API")
    Rel(evidence, mcp, "Recherche", "MCP")
    Rel(evidence, legal, "Ingestion", "HTTP/API")
```

---

## Niveau 2 — Conteneurs

```mermaid
flowchart TB
    subgraph Internet
        U[Utilisateur navigateur]
    end

    subgraph Serveur["Serveur OVH / Docker Compose"]
        Caddy[Caddy<br/>TLS reverse proxy]
        Backend[evidence-backend<br/>Flask + Agent + Scheduler]
        WebUI[webui/<br/>HTML CSS JS]
        Samba[evidence-samba<br/>Partages SMB]
        Volumes[(Volumes Docker<br/>data audit tmp memory shared)]
    end

    subgraph Externe
        LLM[Fournisseurs LLM]
        MCP[MCP servers]
    end

    U -->|HTTPS 443| Caddy
    Caddy --> Backend
    Caddy --> WebUI
    Backend --> Volumes
    Backend --> Samba
    Backend --> LLM
    Backend --> MCP
    U -.->|SMB M:\| Samba
```

### Table des conteneurs

| Conteneur | Image | Port | Rôle |
|-----------|-------|------|------|
| `evidence-caddy` | `caddy:2-alpine` | 80, 443 | TLS, reverse proxy |
| `evidence-backend` | `korev/evidence-backend:1.0.0` | 5050 (interne) | Application principale |
| `evidence-backend-demo` | idem | 5050 (interne) | Instance démo |
| `evidence-samba` | `dperson/samba` | 445 (localhost) | Workspaces utilisateurs |
| `evidence-postgres` | — | — | Profil `db` optionnel (ADR-007) |

---

## Niveau 3 — Composants backend (simplifié)

```mermaid
flowchart LR
    subgraph Flask["run_ui.py"]
        Auth[Auth + Session]
        Routes[Routes /login /change_password]
        APIReg[Enregistrement python/api/*]
    end

    subgraph AgentCore["agent.py"]
        Monologue[Agent.monologue]
        Context[AgentContext registry]
    end

    subgraph Security["python/security/"]
        AuthZ[authorization.py]
        RateLimit[rate_limit/]
        Audit[security_audit.py]
    end

    subgraph Pipeline["Pipeline critique"]
        CritRouter[criticality_router]
        Delegate[call_subordinate]
        Consensus[consensus/engine]
        CritOut[critical_output]
    end

    subgraph Ops["Opérationnel"]
        Scheduler[task_scheduler]
        Notify[notification]
        Persist[persist_chat]
    end

    APIReg --> Monologue
    Monologue --> CritRouter
    CritRouter --> Delegate
    Delegate --> Consensus
    Consensus --> CritOut
    Monologue --> Persist
    Scheduler --> Monologue
    Auth --> AuthZ
    APIReg --> AuthZ
```

---

## Niveau 4 — Flux critique (séquence)

```mermaid
sequenceDiagram
    participant U as Utilisateur
    participant F as Flask /message
    participant A as Agent.monologue
    participant CR as criticality_router
    participant D as call_subordinate
    participant C as run_consensus
    participant O as critical_output

    U->>F: POST message
    F->>A: monologue()
    A->>CR: assess()
    alt LEVEL 1
        A-->>U: réponse directe
    else LEVEL 2/3
        A->>D: délégation profil métier
        D->>C: consensus si requis
        C->>O: finalize + signature
        O-->>U: sortie signée ou FAIL_CLOSED
    end
```

---

## Niveau 3 — Composants frontend

```mermaid
flowchart TB
    subgraph webui
        Index[index.html]
        Login[login.html]
        Components[components/]
        Stores[js/*-store.js]
    end

    subgraph Components
        Sidebar[sidebar/]
        Settings[settings/]
        Notif[notifications/]
        Account[account/password-modal]
    end

    Index --> Sidebar
    Index --> Settings
    Index --> Notif
    Sidebar --> Account
    Stores -->|POST /poll| Backend
    Stores -->|POST /message| Backend
```

---

## Correspondance fichiers

| Élément C4 | Fichier(s) source |
|------------|-------------------|
| Contexte utilisateur | `webui/`, `run_ui.py` |
| Conteneur backend | `deploy/docker-compose.yml`, `run_ui.py` |
| Criticality router | `python/helpers/criticality_router.py` |
| Consensus | `python/consensus/engine.py` |
| Critical output | `python/helpers/critical_output.py` |
| Scheduler | `python/helpers/task_scheduler.py` |
| Multi-tenant | `python/security/authorization.py`, `python/helpers/user_manager.py` |

---

## Documents liés

- [ARCHITECTURE_EVIDENCE.md](../ARCHITECTURE_EVIDENCE.md) — synthèse narrative
- [EVIDENCE_DELEGATION_ARCHITECTURE_VERIFIED.md](EVIDENCE_DELEGATION_ARCHITECTURE_VERIFIED.md) — délégation vérifiée
- [critical_request_path_map.md](../audit/critical_request_path_map.md) — chemin critique audité

---

*Diagrammes C4 — KOREV Evidence v1.3.1. Dernière révision : 2026-06-13.*
