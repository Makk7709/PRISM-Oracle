# KOREV Evidence — Developer Onboarding & Architecture Guide

**Classification :** CONFIDENTIEL — Usage interne KOREV AI  
**Version :** 7.1 (Evidence v1.4.0 — replay engine, human review workflow, dynamic risk register, audit-proof pipeline, +107 tests)  
**Date :** 2026-04-04  
**Auteur :** Direction Technique KOREV AI  
**Destinataire :** Lead Engineer entrant(e)  
**Licence :** Proprietaire KOREV AI — voir `LICENSE` a la racine du depot  
**Note au lecteur :** Ce document est long. C'est volontaire. Lis-le de bout en bout pendant ta premiere semaine, puis utilise-le comme reference. Les sections les plus urgentes a lire en priorite sont marquees d'un signe (**LIRE EN PREMIER**).

---

## Table des matières

1. [Partie 1 : L'Hélicoptère — Vision et Architecture Globale](#partie-1--lhélicoptère)
2. [Partie 2 : Audit Critique et Red Teaming — Les Zones de Danger](#partie-2--audit-critique-et-red-teaming) (**LIRE EN PREMIER**)
3. [Partie 3 : Guide de Survie Opérationnel](#partie-3--guide-de-survie-opérationnel)
4. [Partie 4 : Feuille de Route — 30 Premiers Jours](#partie-4--feuille-de-route--30-premiers-jours) (**LIRE EN PREMIER**)

---

# Partie 1 : L'Hélicoptère

## 1.1 Ce que fait KOREV Evidence

KOREV Evidence est une plateforme multi-agents d'IA de confiance, conçue pour des environnements professionnels exigeants (cabinets d'avocats, médecins, chercheurs, consultants, finance). L'idée directrice : un utilisateur interagit avec un agent principal qui peut **déléguer** à des agents spécialisés (juridique, médical, recherche, sécurité, finance, stratégie, marketing, cybersécurité...), orchestrer des **consensus** entre agents, et produire des livrables traçables (rapports PDF, contrats, dossiers stratégiques, images, analyses).

Les différenciants par rapport à un ChatGPT-like :
- **Auditabilité** : chaque action d'agent est loggée, les sources sont tracées, et les réponses critiques passent par un pipeline de validation multi-agents
- **Multi-tenant strict** : isolation par organisation (UUID canonique), rôles OWNER/MEMBER, fail-closed
- **Pipelines métier spécialisés** : juridique (FTS5 Légifrance), médical (PRISM consensus + FAERS), stratégique (4 agents + consolidation LLM), rédaction contractuelle (Act Leak Guard fail-closed)
- **Protocole A2A** : communication agent-to-agent via FastA2A (client + serveur)
- **~3 956 tests collectés** (snapshot probatoire 28 avril 2026 ; 3 846 lors d'un snapshot antérieur début avril ; source canonique : [`docs/METRICS_CANONICAL_SOURCE.md`](./METRICS_CANONICAL_SOURCE.md)), 179 fichiers de tests, 71 endpoints API

## 1.2 Architecture Macro

```
┌─────────────────────────────────────────────────────────────────┐
│                        COUCHE RÉSEAU                            │
│  Internet → Caddy (HTTPS :443) → Flask Backend (:5050)          │
│                                    ├── WebUI (Alpine.js)        │
│                                    ├── MCP Proxy (/mcp)         │
│                                    └── A2A Server (/a2a)        │
│  Réseau interne → Samba (:445) → Dossiers partagés Windows      │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                     COUCHE APPLICATIVE                           │
│                                                                 │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐      │
│  │  Agent #0     │───▶│  Agent #1     │───▶│  Agent #2     │    │
│  │  (principal)  │◀───│  (subordinate)│◀───│  (sub-sub)    │    │
│  │  multitask    │    │  legal_safe   │    │  researcher   │    │
│  └──────┬───────┘    └──────────────┘    └──────────────┘      │
│         │                                                       │
│  ┌──────▼───────────────────────────────────────────┐          │
│  │              TOOLS (23 outils)                    │          │
│  │  code_execution │ generate_image │ search_engine  │          │
│  │  memory_save    │ file_reader    │ browser_agent  │          │
│  │  export_strategic_pdf │ document_query │ scheduler │          │
│  │  call_subordinate │ ...                           │          │
│  └──────────────────────────────────────────────────┘          │
│                                                                 │
│  ┌──────────────────────────────────────────────────┐          │
│  │         EXTENSIONS (48 fichiers, 24 hooks)       │          │
│  │  system_prompt │ recall_memories │ legal_pipeline │          │
│  │  strategic_validation │ memorize_fragments │ ...    │          │
│  └──────────────────────────────────────────────────┘          │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                    COUCHE PERSISTANCE                            │
│                                                                 │
│  Filesystem (Volumes Docker)                                    │
│  ├── evidence-tmp     → Chats, settings, images, scheduler     │
│  ├── evidence-shared  → Workspaces utilisateurs, commun        │
│  ├── evidence-memory  → FAISS indexes, embeddings cache        │
│  ├── evidence-data    → Legal index (SQLite FTS5)              │
│  ├── evidence-logs    → Application logs                       │
│  └── evidence-audit   → Audit trails                           │
│                                                                 │
│  Pas de SGBD traditionnel. Tout est fichier.                    │
└─────────────────────────────────────────────────────────────────┘
```

## 1.3 Anatomie d'une Requête Utilisateur (Data Flow)

Voici le parcours complet d'un message utilisateur, du clic au résultat :

```
1. FRONTEND (Alpine.js)
   └─ sendMessage() → POST /message_async {text, context, message_id}
       └─ Avec X-CSRF-Token dans le header

2. FLASK BACKEND (run_ui.py)
   └─ @_requires_auth → vérifie session
   └─ ApiHandler.process() → crée/récupère AgentContext
   └─ context.communicate(UserMessage) → lance monologue dans DeferredTask

3. AGENT MONOLOGUE (agent.py)
   └─ Extensions: monologue_start → message_loop_start
   └─ prepare_prompt():
       ├─ System prompt (role + environment + tools + project context)
       ├─ Memory recall (FAISS similarity search)
       └─ History (messages précédents)
   └─ call_chat_model() → LLM API (OpenAI, Anthropic, Google via LiteLLM)
   └─ process_tools():
       ├─ Parse JSON dans la réponse LLM
       ├─ Résolution: MCP tool → Profile tool → Default tool → Unknown
       └─ tool.execute() → Response(message, break_loop)
   └─ Si break_loop=False → boucle (✅ bornée par ExecutionBudget : max_iterations, max_llm_calls, max_tool_calls, deadline)
   └─ Extensions: message_loop_end → monologue_end

4. CAS SPÉCIAL : DÉLÉGATION
   └─ Tool "call_subordinate" → crée Agent #1 avec profil spécialisé
   └─ ExecutionBudget: check_delegation() → cycle detection, max_depth, max_delegations
   └─ propagate_budget() → même état partagé entre supérieur et subordonné
   └─ CriticalityRouter → consensus nécessaire ? (LEVEL 3 critique ou force_consensus)
   └─ Si oui : validation multi-LLM (3 rounds de débat collaboratif)
   └─ Résultat remonté à l'Agent #0

5. FRONTEND POLLING
   └─ poll() toutes les 25-250ms (adaptatif)
   └─ Récupère logs, contextes, streamed tokens
   └─ Rendu: messages.js → marked.parse() → DOM updates
```

## 1.4 Profils d'Agents et Spécialisations

Le système supporte **12 profils**. Chaque profil est un répertoire sous `agents/` avec ses propres prompts, outils, extensions et settings.

| Profil | Rôle | Spécificités |
|--------|------|-------------|
| **default** | Prompts de base | Hérité par tous les profils, contient les prompts et settings par défaut |
| **multitask** | Orchestrateur principal (Agent #0) | Délégation intelligente via `call_subordinate`, `search_engine`, `browser_agent`, `generate_image`, memory |
| **legal_safe** | Mode juridique sécurisé | Température=0, citations obligatoires, classification 3 niveaux de confiance, consensus multi-agents, index FTS5 Légifrance |
| **legal_drafting_guarded** | Rédaction contractuelle automatisée | Pipeline fail-closed : templates CP/CG + 6 annexes, Act Leak Guard (16 patterns P0 bloquants + 9 P1), Gate d'audit avec veto absolu legal_safe, export control |
| **medical** | Intelligence médicale | BioMCP (23+ outils), PubMed MCP, FAERS pharmacovigilance (PRR, ROR, IC), ClinicalTrials.gov, consensus PRISM multi-LLM, synthèse GRADE |
| **researcher** | Recherche approfondie | ArXiv, Semantic Scholar, OpenAlex, Tavily, code_execution, orchestration de sous-agents |
| **hacker** | Analyste cybersécurité | Red/blue team, Kali-oriented `code_execution`, scoring de sévérité, conformité scope |
| **developer** | Développeur logiciel | Architecture, `code_execution`, `search_engine`, génération d'images |
| **finance** | Analyse financière et stratégie | Modélisation MECE, Tavily, Firecrawl, market tools, KPIs, conseil fiscal |
| **sales** | Support commercial | Scripts de vente, objections tables, CRM, prospection |
| **marketing** | Marketing et croissance | Stratégie marketing, `generate_image` obligatoire pour visuels |
| **_example** | Template | Illustre la structure pour créer de nouveaux profils |

**Profils avec extensions propres :**
- `legal_safe/extensions/monologue_start/_10_legal_safe_pipeline.py` — pipeline juridique complet
- `medical/extensions/agent_init/_10_medical_tools.py` — outils médicaux (evidence synthesis, FAERS, trials)
- `medical/tools/` — 5 outils spécialisés : `evidence_synthesis.py`, `faers_signal_detection.py`, `clinical_trials_intel.py`, `prism_integration.py`, `response.py`

**Analogie** : Imagine une entreprise. L'Agent #0 (multitask) est le chef de projet. Quand il reçoit une question juridique, il "appelle" l'Agent #1 (legal_safe) qui est l'avocat spécialisé. Si la question est critique, l'avocat convoque un "comité" (consensus) avec plusieurs LLMs qui débattent avant de valider la réponse. Le chef de projet ne renvoie jamais une réponse juridique non validée.

## 1.5 Mécanismes d'IA de Confiance

### Traçabilité
- Chaque action d'agent est loggée dans `context.log` (type, heading, content, kvps)
- Les logs sont persistés dans les fichiers de chat (`tmp/chats/{ctxid}/chat.json`)
- **Evidence Pack** (`python/helpers/evidence.py`) : objet structuré qui encapsule les sources, citations et métadonnées de confiance pour chaque réponse validée par le consensus
- Audit des opérations fichier dans `shared/audit/file_operations.jsonl` (via `WorkspaceManager`)
- Logs applicatifs structurés JSON dans le volume `evidence-logs`
- Métriques d'observabilité exposées via `/observability_metrics`
- Security audit logging (`python/security/security_audit.py`) — logs structurés sans PII

### Garde-fous
- **Température forcée à 0** pour les profils critiques (legal_safe, legal_drafting_guarded) — pas d'improvisation
- **CriticalityRouter** (`python/helpers/criticality_router.py`) : détecte automatiquement les sujets nécessitant un consensus (basé sur des patterns LEVEL 3 critiques ou `force_consensus=True`, pas sur le profil agent)
- **Validation multi-LLM a 2-3 tours** : Round 1 (analyse independante par 3 LLMs en parallele via `asyncio.gather`), Round 2 (debat croise — **saute si unanimite** au Round 1, unanimite = `confidence >= 0.8` + zero hallucinations), Round 3 (synthese et verdict par **un seul LLM** — l'arbitre principal `arbiters[0]`, temperature=0.1). En pratique, les sessions unanimes ne passent que par 2 rounds. Le verdict final est la decision de Round 3, pas un vote a quorum (`quorum_ratio` est defini dans `DebateConfig` mais n'est pas utilise pour la decision). En cas d'echec de Round 3, un verdict heuristique est calcule depuis Round 1 (confidence moyenne + comptage hallucinations). Si non approuve : fail-closed (reponse originale non retournee). **NB :** `temperature=0.1` s'applique a tous les rounds, pas seulement Round 3 — ce n'est pas temperature=0, donc une marge d'indeterminisme subsiste.
- **Extension pipeline** : 24 hook points avec 48 extensions permettant d'intercepter et modifier le comportement a chaque etape
- **Deterministic Router v2** (`python/helpers/router/`) : routage policy-driven sans jugement LLM, multi-intent (finance + legal + sales simultanés), 40+ keywords board-level (M&A, IPO, LBO, COMEX), anti-injection FR+EN, blocage high-stakes automatique
- **ReasoningEngine** (`python/helpers/metacognition.py`) : metacognition avec politique d'escalade non-diluable (SAFE_REFUSE, HUMAN_REVIEW, ASK_CLARIFY, NONE). Invariants : monotonie (signaux ne peuvent que durcir), non-dilution, no-PII. `HUMAN_REVIEW` est une **classification de risque** (flag metadata) dans la ReasoningEngine. Le **workflow de review** est implemente par `python/helpers/human_review.py` (voir §1.15) et declenche automatiquement par le Dynamic Risk Register sur HIGH/CRITICAL. **NB :** Le blocage effectif de la reponse dans la chaine de livraison n'est pas encore integre (voir §1.15 NB CRITIQUE).
- **Critical Decision Gate** (`python/helpers/critical_decision_gate.py`) : gate séparée pour les décisions à haut risque
- **Adversarial Analysis** : 4 endpoints API + intégration dans le consensus juridique et la validation
- **ExecutionBudget** (`python/helpers/execution_budget.py`) : ✅ garde-fou central anti-boucles infinies. Chaque exécution transporte un budget partagé qui borne :
  - `max_iterations` (défaut 25) — itérations du message loop
  - `max_depth` (défaut 5) — profondeur de récursion `_process_chain`
  - `max_delegations` (défaut 8) — nombre de délégations inter-agents
  - `max_tool_calls` (défaut 50) — nombre d'exécutions d'outils
  - `max_llm_calls` (défaut 30) — nombre d'appels LLM
  - `max_consensus_rounds` (défaut 3) — rounds de consensus
  - `deadline_seconds` (défaut 300s) — timeout global
  - Détection de cycles de délégation (A→B→A) et self-delegation
  - Tous les seuils sont configurables via variables d'environnement `EVIDENCE_*`
  - Arrêt immédiat avec `LOOP_GUARD_TRIGGERED` et log structuré en cas de dépassement
- **Exécution gardée** : `ExecutionGuard` (désactivé actuellement — remplacé par le prompt-based execution policy)

### Isolation multi-tenant (v5.0)
- **Organisation canonique** (`python/helpers/organization.py`) : chaque tenant est identifié par `organization_uuid` + `organization_id` (slug normalisé) + `organization_display` (affichage UI)
- **Normalisation** : `normalize_org_id()` assure une comparaison case-insensitive et slug-safe ("DICA France" → "dica-france")
- **Isolation stricte** : `python/security/authorization.py` — `AccessPrincipal` avec scoping org/workspace/user, `can_access_context()`, `can_access_task()`, `can_access_workspace()`
- **Rôles** : OWNER (accès à tous les chats de l'org) / MEMBER (accès uniquement à ses propres chats)
- Projets : champ `owner` + `organization_id` + filtrage API
- Images générées : sous-dossiers par utilisateur
- Mémoire : index FAISS séparés par utilisateur
- Workspaces : `shared/users/{username}/` avec documents, rapports, tmp
- Notifications scoppées : `target_username` + `target_organization` sur chaque notification
- Scheduler fail-closed : tâches sans `username` ou `organization` ne s'exécutent jamais

## 1.6 Pipelines Métier Spécialisés

### Pipeline Juridique (`legal_safe`)
- **Index SQLite FTS5** : ~5000+ décisions de la Cour de cassation dans `data/legal/index/legal_index.sqlite`
- **Ingestion** : `python/legal_sources/` — connecteurs PISTE / Judilibre / Légifrance (APIs officielles françaises)
- **Pipeline** : `python/helpers/legal_pipeline.py` (1807 lignes) — recherche → retrieval → classification → judge → consensus
- **Température forcée à 0** — zéro improvisation pour les réponses juridiques
- **Classification 3 niveaux** : NIVEAU 1 (source vérifiée), NIVEAU 2 (probable), NIVEAU 3 (incertain)
- **124 tests** dédiés au pipeline juridique

### Pipeline Rédaction Contractuelle (`legal_drafting_guarded`)
- **Module** : `python/helpers/contract_drafting/` (7 fichiers : orchestrator, gate, leak_guard, governance, export_control, templates, models)
- **Templates** : Conditions Particulières + Conditions Générales + 6 Annexes (SLA, DPA RGPD art.28, réversibilité, grille tarifaire)
- **Act Leak Guard** : 16 patterns P0 bloquants (cession code source, transfert IP, garanties absolues) + 9 patterns P1
- **Gate d'audit fail-closed** : veto absolu `legal_safe`, export PDF impossible sans PASS
- **Séparation des rôles** : `legal_drafting_guarded` = RÉDACTEUR, `legal_safe` = JUGE

### Pipeline Stratégique (`strategic_orchestrator`)
- **Module** : `python/helpers/strategic_orchestrator.py` (v2.0)
- **Détection** : `detect_strategic_document()` identifie les requêtes de dossiers stratégiques
- **4 agents spécialisés** : researcher, finance, marketing, legal (exécution séquentielle avec contexte inter-agents enrichi via `_extract_key_content()`)
- **Consolidation LLM dynamique** : `_consolidate_via_llm()` — persona Senior Partner, minimum 3000 mots
- **Routing modèle** : `_call_chat_model()` route explicitement vers le `chat_model` (pas le `utility_model`)
- **Export PDF** : `export_strategic_pdf_for_context()` — génération automatique de dossiers PDF premium
- **Hook** : `python/extensions/monologue_start/_15_strategic_enforcement.py` — court-circuite le LLM principal

### Pipeline Médical (`medical`)
- **Outils dédiés** dans `agents/medical/tools/` : evidence_synthesis, faers_signal_detection, clinical_trials_intel, prism_integration
- **BioMCP** : 23+ outils (PubMed, ClinicalTrials.gov, OpenFDA, Genomics)
- **Pharmacovigilance FAERS** : signal detection avec PRR, ROR, IC
- **Synthèse GRADE** : scoring evidence (HIGH/MODERATE/LOW/VERY LOW)
- **Consensus PRISM** : validation multi-LLM fail-closed (voir `PROTOCOL_EVIDENCE_VALIDATION.md`)

## 1.7 Protocole A2A (Agent-to-Agent)

Evidence implémente le protocole Agent-to-Agent pour la communication inter-agents distante :
- **Serveur** : `python/helpers/fasta2a_server.py` — `AgentZeroWorker` + `DynamicA2AProxy`, monté à `/a2a`
- **Client** : `python/helpers/fasta2a_client.py` — `AgentConnection`, bearer/A2A_TOKEN, découverte via `/.well-known/agent.json`
- **Outil** : `python/tools/a2a_chat.py` — `A2AChatTool` pour les interactions agent-to-agent depuis le chat
- **UI** : `webui/components/settings/a2a/a2a-connection.html` — configuration des connexions A2A
- **Tests** : aucun test automatise en CI. `tests/test_fasta2a_client.py` est un helper manuel (print/curl). Dependance optionnelle `fasta2a`.

## 1.8 Observabilité et Monitoring

- **Logs JSON structurés** : événements scheduler, notifications, sécurité multi-tenant
- **Metriques** : `/observability_metrics` (requiert **authentification admin**) — 26 compteurs (`*_total` : tasks_created/claimed/completed/failed/quarantined, notifications_created/read/denied, cross_tenant_denied, audit_reports_generated/failed/size_bytes/generation_ms, replay_snapshots_captured/integrity_checks/integrity_failures, human_reviews_created/approved/rejected, risk_assessments/low/medium/high/critical, risk_human_review_triggered) + 5 taux derives (claim_conflict_rate, task_fail_rate, denied_scope_rate, notification_read_gap, cross_tenant_denied_rate)
- **Smoke tests** : `scripts/smoke_test_multi_user.py` — test post-déploiement multi-user + concurrence
- **Health endpoints** : `/healthz` — readiness check
- **Security audit** : `python/security/security_audit.py` — logs structurés sans données sensibles

## 1.9 Speech & Multimodal

- **Speech-to-Text** : Whisper via `python/helpers/whisper.py`, endpoint `/transcribe`
- **Text-to-Speech** : Kokoro TTS via `python/helpers/kokoro_tts.py`, endpoint `/synthesize`
- **Vision** : `python/tools/vision_load.py` — chargement/compression d'images pour le contexte modèle
- **Browser Automation** : `python/tools/browser_agent.py` — Playwright + browser_use

## 1.10 Backup & Restore

- APIs natives : `/backup_create`, `/backup_inspect`, `/backup_restore`, `/backup_preview_grouped`, `/backup_test`
- Backup complet des volumes Docker (données, audit, workspaces partagés)
- Prévisualisation groupée avant restauration

## 1.11 Rapports d'Audit Evidence (Sessions 8-16) (**LIRE EN PREMIER**)

Le systeme genere automatiquement un rapport d'audit structure pour chaque session strategique. Ce rapport constitue la piece de conformite AI Act / RGPD. Il est assemble par `AuditReportRenderer` (486 lignes) et contient **10 blocs canoniques** :

| Bloc | Module | Contenu |
|------|--------|---------|
| 1. Identite session | `SessionEnvelope` | ID session, utilisateur, organisation, horodatage |
| 2. Pipeline execution | `PipelineTracker` | Agents mobilises, durees, statuts |
| 3. Grille de conformite | `ComplianceGrid` | Evaluation Art. 9, 13, 14, 17 AI Act + RGPD Art. 30 |
| 4. Transparence raisonnement | `ReasoningOutcome.to_safe_narrative()` | Narratif non-technique Art. 13 |
| 5. Registre des risques | `RiskRegister` | Risques identifies (Art. 9 AI Act) |
| 6. Registre des traitements | `ProcessingRegister` | Activites de traitement (RGPD Art. 30) |
| 7. Taxonomie des sources | `SourceTaxonomy` | Classification et tracabilite des sources |
| 8. Metadonnees techniques | `ReportMetadata` | Modeles utilises, tokens, latences |
| 9. Integrite et securite | `IntegrityBlock` | Hashes SHA-256, signature HMAC/RSA-PSS |
| 10. Footer | — | Avertissement, branding Evidence |

**Signature d'integrite :** Le bloc 9 signe cryptographiquement le rapport. En production, RSA-PSS-SHA256 est utilise (non-repudiation via cles dans `/evidence/keys/`). En dev, HMAC-SHA256 sert de fallback si les cles RSA ne sont pas configurees. La variable `EVIDENCE_HMAC_KEY` est **obligatoire** — l'application leve `RuntimeError` si elle est absente.

**Stockage :** Les rapports sont persistes dans `tmp/chats/{ctxid}/audit_report.md` (et optionnellement `.pdf`) via `audit_report_storage.py`. Retention par defaut : **1825 jours** (5 ans), configurable via `EVIDENCE_RETENTION_DAYS`. Purge automatique via `purge_expired_reports()`. L'endpoint `/audit_reports` (GET/POST) permet leur consultation avec controle d'acces fin (`can_access_audit_reports` — OWNER, DPO, RSSI, COMPLIANCE_OFFICER).

**Limites actuelles (honnetete) :**
- Le `RiskRegister` statique (7 risques types) est desormais **complete par le Dynamic Risk Register** (`python/helpers/dynamic_risk_register.py`) qui calcule un score de risque dynamique par session a partir de 6 facteurs ponderes. Le registre statique reste present pour le rapport d'audit formel.
- Le `ProcessingRegister` est un **template statique** enrichi par le username et l'organisation de la session. Pas d'analyse dynamique des traitements reels.
- La `ComplianceGrid` couvre 5 articles : Art. 9, 13, 14, 17 AI Act + RGPD Art. 30. Les autres articles AI Act ne sont pas evalues.
- Le **Replay Engine** (§1.14) capture un snapshot complet (query, config, response, hashes) et permet la **comparaison post-hoc** via similarite Jaccard et verification d'integrite SHA-256. **Il ne re-execute pas** la decision via LLM — c'est du snapshot + comparaison, pas du replay au sens strict. Le non-determinisme inherent aux LLMs (meme a temperature=0) rend une re-execution exacte techniquement impraticable pour v1.

**Fichiers cles :**
- `python/helpers/audit_report_renderer.py` — assembleur des 10 blocs
- `python/helpers/integrity_block.py` — hashes + signatures
- `python/helpers/session_envelope.py` — metadonnees session
- `python/helpers/compliance_grid.py` — evaluation conformite
- `python/helpers/risk_register.py` — registre des risques Art. 9
- `python/helpers/processing_register.py` — registre des traitements RGPD Art. 30
- `python/helpers/report_metadata.py` — metadonnees techniques
- `python/helpers/audit_report_storage.py` — persistance + purge retention
- `python/api/audit_reports.py` — endpoint REST

**Tests :** `test_session8_integrity_renderer.py`, `test_session9_storage_tokens.py`, `test_session10_hardening.py` (RSA, benchmarks, RBAC), `test_session12_query_flags.py`, `test_session13_document_hash_rsa.py`, `test_session14_transparency_narrative.py`, `test_session15_registers.py`, `test_session16_e2e_final.py`.

## 1.12 Personnalisation du Chat

Le systeme supporte une personnalisation fine de l'interaction via `python/helpers/chat_style.py` :
- **Adresse** : tutoiement / vouvoiement
- **Ton** : formel, cordial, direct, bienveillant
- **Humanisation** : minimal, modere, eleve
- **Verbosite** : concise, equilibre, detaille
- **Persona** : homme, femme, IA
- **Nom d'IA** : configurable (ex: "Selene")

L'extension `python/extensions/system_prompt/_05_chat_style.py` injecte les instructions de style en tete du system prompt. Configuration via l'UI (Settings > Personnalisation).

## 1.13 Rate Limiting

Un systeme de rate limiting protege les endpoints critiques :
- **Backend memory** (`python/security/rate_limit/memory_backend.py`) — pour les deployements mono-instance
- **Backend Redis** (`python/security/rate_limit/redis_backend.py`) — pour les deployements multi-workers
- **Limiter** (`python/security/rate_limit/limiter.py`) — facade unifiee, backoff exponentiel, LRU eviction
- **Compat** (`python/security/rate_limit/compat.py`) — API legacy : `check_login_rate_limit()`, `check_api_rate_limit()`

Le rate limiting est applique sur `/login` (anti-brute-force) et les endpoints API. En mode `FAIL_CLOSED` quand Redis est indisponible.

## 1.14 Replay Engine — Snapshot, Comparaison & Verification d'Integrite (**LIRE EN PREMIER**)

Le systeme capture un **snapshot complet** de chaque session pour permettre la **comparaison post-hoc** et la **verification d'integrite**. C'est la brique centrale de preuve pour l'auditabilite AI Act Art. 13 (transparence) et Art. 17 (tracabilite). **NB :** Le moteur ne re-execute pas la decision via LLM (re-execution deterministe non implementee en v1 — voir §1.11 Limites). Il compare des snapshots et detecte les alterations.

**Architecture :**
- **`python/helpers/replay_engine.py`** — Moteur de capture, persistance, comparaison
- **`python/extensions/monologue_end/_35_replay_snapshot.py`** — Capture automatique apres chaque monologue
- **`python/api/replay.py`** — API : consultation snapshot, verification integrite, comparaison

**Contenu d'un snapshot (`SessionSnapshot`) :**
- `query` (requete utilisateur)
- `system_prompt_hash` (SHA-256 du prompt systeme)
- `history_hash` (SHA-256 de l'historique)
- `memory_snapshot_hash` (SHA-256 de l'etat FAISS)
- `model_config` (provider, model, temperature, kwargs)
- `response` + `response_hash`
- `tool_calls`, `delegation_chain`, `execution_budget`
- `tokens_input`, `tokens_output`
- `correlation_id`, `session_id`, `context_id`
- `snapshot_version`, `captured_at`, `started_at`, `completed_at`, `duration_ms`
- `username`, `organization`, `agent_profile`
- `integrity_hash` (SHA-256 des champs critiques — tamper detection)

**Comparaison de divergence :**
- `NONE` (hash identique)
- `MINOR` (>95% similarite Jaccard)
- `SIGNIFICANT` (70-95%, ou ratio de longueur <0.5)
- `CRITICAL` (<70%)

**NB :** La similarite Jaccard est une heuristique sur les mots (sensible au vocabulaire, insensible a l'ordre). Ce n'est pas une comparaison semantique — deux phrases de sens identique mais de vocabulaire different seront classees comme divergence significative. Limite acceptee en v1.

**Stockage :** `tmp/chats/{ctxid}/replay_snapshot.json`

**Verification :** Double controle — 1) hash d'integrite global, 2) hash de la reponse vs contenu reel. Toute alteration est detectee.

**Tests :** `tests/test_replay_engine.py` (29 tests — capture, persistance, integrite, comparaison, determinisme, edge cases, property tests).

## 1.15 Human Review Workflow — Validation Humaine Tracable

Le systeme implemente un workflow de validation humaine conforme AI Act Art. 14 (controle humain). Chaque decision critique peut etre soumise a un reviewer humain. **NB v1 :** Le workflow est entierement fonctionnel (creation, decision, audit trail), mais le **blocage effectif de la reponse** dans la chaine de livraison n'est pas encore integre au runtime (voir NB CRITIQUE ci-dessous). L'integration dans `poll.py` est un chantier prioritaire.

**Architecture :**
- **`python/helpers/human_review.py`** — Logique metier : creation, soumission, blocage
- **`python/api/human_review.py`** — API : liste, detail, decision
- **`python/extensions/monologue_end/_36_risk_assessment.py`** — Declenchement automatique via Risk Engine

**Etats du workflow :**
```
PENDING_REVIEW → APPROVED (deblocage)
               → REJECTED (blocage maintenu)
               → EXPIRED  (non utilise en v1 — reserve pour TTL futur)
```

**Chaque decision est journalisee avec :**
- `reviewer_id` + `reviewer_name`
- `decided_at` (timestamp ISO 8601)
- `justification` (texte libre obligatoire)
- `override_original` (flag si le reviewer modifie la reponse)
- `override_response` (reponse corrigee)

**Declenchement :**
- `RISK_ENGINE` — automatique si le risk score atteint HIGH ou CRITICAL
- `MANUAL` — declenchement explicite via API
- `POLICY` — regle de politique configurable
- `CONSENSUS_FAILURE` — echec de consensus multi-agents

**Blocage :** `is_review_blocking(context_id)` retourne le review en attente le cas echeant.

**NB CRITIQUE :** En v1, la fonction `is_review_blocking()` est implementee dans le helper mais **n'est PAS appelee dans la chaine de livraison** (`poll.py`, `agent.py`, `run_ui.py`). L'extension `_36_risk_assessment.py` cree le review et pose `_human_review_pending` sur le contexte, mais aucun code de livraison ne lit cette donnee pour bloquer la reponse. **Le blocage reel de la reponse n'est donc pas enforce a l'execution.** L'integration dans `poll.py` ou un middleware de livraison est un chantier necessaire pour que la garantie de blocage soit effective. En l'etat, le controle humain est un **registre consultatif**, pas un verrou bloquant.

**Securite :** Double soumission interdite (ValueError si deja resolu). Acces restreint OWNER / DPO / RSSI / COMPLIANCE_OFFICER via `can_access_audit_reports`. Justification obligatoire au niveau API (rejet 400 si vide).

**Stockage :** `tmp/reviews/{review_id}.json`

**Tests :** `tests/test_human_review.py` (25 tests — creation, blocage, decision, audit trail, serialization, property tests).

## 1.16 Dynamic Risk Register — Scoring de Risque Temps Reel

Le systeme calcule un **score de risque dynamique** par session a partir de 6 facteurs ponderes. Il **complete** le `RiskRegister` statique (qui reste present pour les rapports d'audit formels) par un moteur de scoring en temps reel.

**Architecture :**
- **`python/helpers/dynamic_risk_register.py`** — Moteur de scoring, dashboard, historisation
- **`python/api/risk_dashboard.py`** — API : dashboard agrege, evaluation manuelle
- **`python/extensions/monologue_end/_36_risk_assessment.py`** — Evaluation automatique + declenchement human review

**6 facteurs de scoring :**

| Facteur | Poids | Description |
|---|:---:|---|
| `consensus_failure` | 30% | Echec de consensus multi-agents (0.8 si echec, 1.0 si 3+ rounds) |
| `low_confidence` | 25% | Score de confiance bas (1.0 si <0.3, 0.7 si <0.5, 0.4 si <0.7) |
| `errors_timeouts` | 20% | Erreurs et timeouts cumules (0.3/erreur + 0.4/timeout, cap 1.0) |
| `delegation_depth` | 10% | Profondeur de delegation (>3 = risque croissant) |
| `execution_time` | 10% | Temps d'execution anormal (>120s = 1.0) |
| `tool_call_volume` | 5% | Volume d'appels outils (>20 = 0.8) |

**Classification :**
- `LOW` : score < 0.30
- `MEDIUM` : score >= 0.30
- `HIGH` : score >= 0.60 → **declenche HUMAN_REVIEW automatiquement**
- `CRITICAL` : score >= 0.85 → **declenche HUMAN_REVIEW automatiquement**

**Dashboard systeme (`/risk_dashboard`) :**
- Total sessions evaluees
- Distribution par niveau de risque
- Score moyen et max
- Nombre de reviews humains declenches
- Historique des evaluations recentes

**Historisation :** Log append-only `tmp/audit/risk_register.jsonl` — chaque entree contient l'assessment complet avec tous les facteurs.

**Tests :** `tests/test_dynamic_risk_register.py` (28 tests — classification, seuils, coherence, dashboard, historisation, scenarios d'echec, property tests).

## 1.17 Tests A2A — Preuve d'Integrite End-to-End

Les trois briques (Replay + Human Review + Risk Engine) sont couvertes par une suite de tests E2E dans `tests/test_audit_proof_e2e.py` (12 tests) verifiant :

- **Pipeline complet** : session → risk → review → decision → deblocage
- **Low risk bypass** : sessions a faible risque ne declenchent pas de review
- **Replay apres validation** : comparaison post-approbation + detection de tampering
- **Tracabilite correlation_id** : propagation a travers tous les artefacts
- **Scenarios de cascade** : consensus failure → HIGH risk → review → rejection
- **Invariants systeme** : immutabilite des snapshots, impossibilite de double-soumission, determinisme du scoring, symetrie de la comparaison de divergence

**Total briques audit-proof : 107 tests (5 fichiers, incluant 13 tests de hardening post-audit hostile).**

---

# Partie 2 : Audit Critique et Red Teaming

> *"Zéro complaisance. Si le système devait s'effondrer, voici par où ça commencerait."*

## 2.1 Vulnérabilités Critiques

### ~~CRITIQUE : Path Traversal dans `file_info` et `download_work_dir_file`~~ — CORRIGE (mars 2026)

> **Statut : CORRIGE.** Les trois fichiers utilisent desormais `safe_path_join()`. Commit de reference : pre-v1.3.0.

**Fichiers corriges :** `python/api/file_info.py`, `python/api/download_work_dir_file.py`, `python/api/api_files_get.py`

**Historique de la faille :** Le chemin fourni par l'utilisateur etait passe directement a `files.get_abs_path(path)` sans validation (`os.path.join` sans resolution). Un attaquant pouvait lire n'importe quel fichier du systeme via `../../etc/passwd`.

**Correction appliquee :** `safe_path_join(root, normalized, allow_symlinks=False)` est desormais appele dans les trois fichiers. `api_files_get` restreint aussi le scope a `tmp/uploads/` et `tmp/chats/` uniquement.

**Risque residuel :** `api_files_get` autorise l'acces aux fichiers dans `tmp/chats/` pour les detenteurs d'API key — si la cle fuit, tous les chats sont lisibles. Ce n'est plus du path traversal mais un probleme de scope d'API key.

### 🟠 ÉLEVÉ : Pas de sandbox pour l'exécution de code

`code_execution_tool.py` exécute du Python/Node/shell avec les privilèges du processus backend. En production Docker, c'est l'utilisateur `evidence` dans le container. Mais :
- Pas de container séparé, pas de seccomp, pas de cgroups dédiés
- Le code peut lire/écrire tout ce que le processus backend peut lire/écrire
- Un agent hallucinant pourrait exécuter `rm -rf /app/tmp/` et détruire toutes les données

### ELEVE : Chats sans isolation utilisateur au stockage

Tous les chats sont dans `tmp/chats/<ctxid>/` (un dossier par context, **pas** de sous-dossier par utilisateur). L'ownership est un champ `username` dans le JSON.

**Mitigations existantes (partielles) :**
- `can_access_context()` est appele dans `use_context()` et `poll.py` — l'isolation est **enforcie au niveau API**
- Un utilisateur ne peut pas lister/charger les chats d'un autre via l'interface web

**Risques restants :**
- Un acces direct au volume Docker contourne cette protection (pas d'isolation filesystem)
- Au startup, TOUS les chats sont charges en memoire (`load_tmp_chats()`) — ne scale pas
- L'import de chat (`chat_load`) re-attribue le contexte au compte importateur (design intentionnel, mais a documenter en politique d'usage)

### 🟠 ÉLEVÉ : Fuite de file descriptors (observée en production)

Le backend a été trouvé avec 1023/1024 file descriptors ouverts, causant un crash complet. La cause probable : les sessions aiohttp, les connexions LLM, ou les index FAISS ne sont pas correctement fermés. Le `ulimits` a été monté à 65536, mais c'est un pansement — la fuite existe toujours.

## 2.2 Risques Multi-Agents

### Boucles infinies — ✅ NEUTRALISÉES (v4.0, mars 2026)

> **Patch appliqué** : `python/helpers/execution_budget.py` + modifications de `agent.py` et `python/tools/call_subordinate.py`. Voir tests : `tests/test_execution_budget.py` (34 tests).

Les deux vecteurs historiques de boucles infinies sont désormais bornés par le système **ExecutionBudget** :

1. **Profondeur de délégation** : ✅ `check_depth()` est appelé dans `_process_chain()` avant chaque récursion. Limite : `max_depth=5` (configurable via `EVIDENCE_MAX_DEPTH`). `check_delegation()` dans `call_subordinate.py` borne le nombre total de délégations (`max_delegations=8`) et détecte les cycles (A→B→A) via `delegation_visit_counts`.

2. **Boucle monologue** : ✅ `check_iteration()` est appelé avant chaque itération du message loop. Limite : `max_iterations=25` (configurable via `EVIDENCE_MAX_ITERATIONS`). `check_llm_call()` borne le nombre total d'appels LLM (`max_llm_calls=30`). `check_tool_call()` borne le nombre d'exécutions d'outils (`max_tool_calls=50`). Un `deadline_seconds=300` borne le temps total.

3. **Budget partagé** : L'état d'exécution (`ExecutionState`) est **propagé** du supérieur au subordonné via `propagate_budget()`. Les compteurs ne se réinitialisent jamais lors d'une délégation — un subordonné consomme le budget de son supérieur.

4. **Arrêt explicite** : Quand une limite est atteinte, une `BudgetExceededError` est levée et capturée dans les deux niveaux de la monologue. Le système retourne un message structuré `LOOP_GUARD_TRIGGERED` avec la raison exacte, les compteurs, et la chaîne de délégation.

**Scénario historique #1 (neutralisé) :** L'agent researcher délègue à medical, qui redélègue → `check_delegation()` détecte le cycle ou atteint `max_delegations`.

**Scénario historique #2 (neutralisé) :** Un agent boucle sur un tool partiel → `check_iteration()` + `check_tool_calls()` stoppent l'exécution.

**Risques résiduels :**
- Les appels `call_utility_model()` (hors monologue) ne décomptent pas du budget LLM global — risque faible, impact limité
- Les extensions `monologue_start` s'exécutent avant le check d'itération — ne peuvent pas contourner le garde mais ralentissent la détection d'un cycle de 1 itération

### Hallucinations croisées

Le consensus multi-agents (3 rounds) est un excellent garde-fou, MAIS :
- Les agents partagent le même `AgentContext` (mémoire, projet, config)
- Un agent qui écrit dans la mémoire FAISS peut influencer un autre qui la lit
- La consolidation mémoire utilise un LLM — un LLM qui hallucine pendant la consolidation corrompt la mémoire pour tous les agents suivants

### Perte de contexte

Le subordinate a sa propre `History` mais partage le `AgentContext`. Quand il retourne son résultat, le main agent ne reçoit qu'une string (le `tool_result`). Si le subordinate a produit 3 pages d'analyse, le main agent n'en voit qu'un résumé. L'information se dégrade à chaque niveau de délégation.

### Flags implicites de pipeline

Le mécanisme de coordination utilise des flags mutables sur l'objet Agent :
- `_pipeline_final_response`
- `_pipeline_validated_response`
- `_consensus_result`
- `_skip_llm`

Pas d'état machine explicite, pas de cleanup en cas d'erreur. Un crash au milieu d'un consensus laisse ces flags dans un état incohérent.

## 2.3 Guide de Débogage Multi-Agents (Focus IA de Confiance)

> *Tu vas être amené(e) à investiguer des cas où un agent a produit une réponse douteuse, où un consensus a validé une hallucination, ou où une chaîne de délégation s'est perdue. Voici comment enquêter.*

### Où sont les logs du consensus (les "3 rounds de débat") ?

Le consensus multi-agents est implémenté dans `python/tools/call_subordinate.py`, méthode `_validate_with_consensus()`. Chaque round de débat est loggé dans le `context.log` de l'`AgentContext` courant. Concrètement, voici comment remonter la trace :

1. **Dans l'interface web** : Ouvre le chat concerné. Les messages de type `tool` dans la timeline affichent les appels à `call_subordinate`. Le résultat inclut les métadonnées du consensus (provider, rounds, décision).

2. **Dans les fichiers de chat** : Le fichier `tmp/chats/{ctxid}/chat.json` contient l'intégralité du log structuré. Cherche les entrées de type `"tool"` avec `heading` contenant `"Consensus"` ou `"Subordinate"`. Le champ `kvps` contient les clés-valeurs de diagnostic (provider, latence, nombre de rounds, résultat du vote).

3. **Dans les logs Docker** : En production, lance `docker logs evidence-backend 2>&1 | grep -i "consensus\|CriticalityRouter\|subordinate"`. Les `PrintStyle` du module `call_subordinate.py` émettent des lignes colorées pour chaque étape : choix du routeur, lancement du consensus, résultat de chaque round, décision finale.

4. **En debogage local** : Place un breakpoint dans `_validate_with_consensus()` (ligne ~423 de `call_subordinate.py`). Les variables `debate_result`, `round1_analyses` contiennent l'etat complet du debat. Attention : le verdict final est dans `debate_result.approved` et `debate_result.synthesis.final_verdict`, pas dans un comptage de votes.

### Comment vérifier qu'un agent `legal_safe` n'hallucine pas des jurisprudences ?

C'est le risque le plus dangereux du système. Un LLM qui invente une référence juridique (arrêt de Cour de cassation, article de loi) peut induire un professionnel du droit en erreur. Voici les garde-fous en place et leurs limites :

**Garde-fous actifs :**
- Le profil `legal_safe` force `temperature=0` (via `agents/legal_safe/extensions/monologue_start/_10_legal_safe_pipeline.py` qui appelle `python/extensions/legal_safe_mode/_10_legal_safe_integration.py`, ligne 534). Cela réduit la créativité du LLM et favorise les réponses factuelles.
- Le prompt système de `legal_safe` exige des citations explicites et une classification en 3 niveaux de confiance (NIVEAU 1 = source vérifiée, NIVEAU 2 = probable, NIVEAU 3 = incertain).
- L'index juridique SQLite FTS5 (`data/legal/index/legal_index.sqlite`) sert de source de vérité. La recherche FTS5 est effectuée par `python/helpers/legal_orchestrator.py` et `python/helpers/legal_retrieval.py`. Le pipeline dans `python/helpers/legal_pipeline.py` consomme les résultats (via `source_chunk_ids`) pour la validation et le jugement (`judge_legal_draft()`).

**Limites actuelles (honnêteté) :**
- Le LLM peut citer un arrêt avec un numéro légèrement modifié (ex: "Cass. civ. 1, 12 mars 2019, n°18-12.345" au lieu de "18-12.346"). L'index FTS5 ne fait pas de vérification automatique de numéros de pourvoi.
- Le consensus valide la cohérence de la réponse entre agents, pas la véracité des sources. Deux LLMs qui hallucinent le même arrêt se valideront mutuellement.
- Il n'existe pas de pipeline automatique de "fact-checking juridique" (cross-reference avec Légifrance ou Jurica en temps réel). C'est un chantier futur.

**Procédure de vérification manuelle :**
1. Dans le chat, identifie les citations juridiques (format "Cass.", "CE", "Art. L.", "Art. R.").
2. Recherche dans l'index : `docker exec evidence-backend python3 -c "import sqlite3; conn = sqlite3.connect('/app/data/legal/index/legal_index.sqlite'); print(conn.execute('SELECT doc_id, title FROM docs WHERE title LIKE \"%mot-clé%\"').fetchall())"`.
3. Si la référence n'est pas dans l'index, elle est potentiellement hallucinée. Flag le chat et remonte l'information.

### Comment tracer une chaîne de délégation complète

Quand un agent délègue puis que le subordinate redélègue, la trace se dilue. Pour reconstruire la chaîne :

1. Ouvre `tmp/chats/{ctxid}/chat.json`.
2. Cherche tous les `tool_name: "call_subordinate"` dans les agents (champ `agents` → chaque agent a son `history`).
3. L'Agent #0 (index 0) est le principal. L'Agent #1 (index 1) est le premier subordinate. Et ainsi de suite.
4. Chaque agent a sa propre `history` sérialisée. Tu peux reconstituer le "dialogue interne" complet.

**Attention :** Le subordinate partage le même `AgentContext` que le principal. Donc ses écritures mémoire (FAISS) affectent le principal. Si tu suspectes une contamination mémoire, inspecte `memory/users/{username}/{memory_subdir}/` — les fichiers `index.faiss` et `index.pkl` contiennent les vecteurs et les documents associés.

## 2.4 Single Points of Failure (SPOF)

| SPOF | Impact si défaillant | Probabilité | Mitigation existante |
|------|---------------------|-------------|----------------------|
| **Flask process unique** | Tout le backend tombe | Moyenne (observé avec ulimits) | `restart: unless-stopped` dans Docker Compose, healthcheck toutes les 30s |
| **`files.get_base_dir()`** | Toute résolution de path casse, sécurité compromise | Faible mais catastrophique | Aucune. Le système entier repose sur cette valeur. |
| **`settings.json`** | Config perdue, MCP token invalidé, settings UI perdus | Faible | Volume Docker persistant (`evidence-tmp`) |
| **SQLite legal_index** | Recherche juridique KO, pas de réplica | Moyenne | WAL activé pour la concurrence, mais pas de backup automatique |
| **FAISS in-memory** | Mémoire agent perdue au crash si pas persistée à temps | Moyenne | Persistance sur disque (`index.faiss`), mais pas de réplication |
| **Volume Docker `evidence-tmp`** | Tous les chats, settings, images perdus | Faible (sauf disque plein) | Docker volume nommé, mais pas de backup automatique |

## 2.5 Dette Technique Immédiate

### Ce qui a été fait "vite et bien" mais qui craquera

| Élément | Pourquoi c'est fait comme ça | Pourquoi ça va poser problème |
|---------|------------------------------|-------------------------------|
| **Polling HTTP au lieu de WebSocket** | Simple à implémenter, pas de gestion de connexion persistante | 25-250ms de latence, charge réseau inutile, ne scale pas au-delà de ~20 utilisateurs simultanés |
| **Tout en filesystem (JSON)** | Pas de dépendance SGBD, déploiement simple | Pas de requêtes complexes, pas de transactions, race conditions sur écritures concurrentes, tout en mémoire au startup |
| **`asyncio.run()` dans `__init__`** | Besoin d'appeler des extensions async à l'init de l'agent | Peut casser la boucle événementielle, incompatible avec certains serveurs ASGI |
| **Temperature en string `"1"`** | Hérité de la config JSON | Conversions fragiles, mutation directe de la config pour legal_safe |
| **Pas de build frontend** | Pas besoin avec Alpine.js + CDN | Pas de minification, pas de tree-shaking, CSP nécessite `unsafe-inline` et `unsafe-eval` |
| **Extension ordering par filename** | `_10_`, `_20_`, `_30_`... | Fragile, pas documenté, un mauvais nommage casse l'ordre |
| **MCP token recalculé à chaque normalisation** | Déterministe (hash de runtime_id + credentials), stable si credentials inchangés | Recalculé dans `normalize_settings()` à chaque appel de `get_settings()`. Pas de vraie rotation, mais recomputation coûteuse |
| **`mcp_config.json` avec chemins hardcodés** | Config développeur locale | `/Users/aminemohamed/Desktop` en production = fuite d'information |
| **index.html de 1300 lignes** | Tout-en-un, pas de composants | Maintenance cauchemardesque |
| **Pas de tests frontend** | Alpine.js rend le testing non-trivial | Régressions silencieuses sur chaque changement UI |

### Cadre de gestion de la dette : Patcher vs. Accepter (Anti-Panique)

> **Message direct au Lead Engineer :** Cette liste peut donner le vertige. C'est normal. La tentation sera forte de "tout refaire proprement". **Résiste.** Voici le cadre de décision qui te dit quoi traiter en urgence et quoi laisser tranquille.

**PATCHER IMMÉDIATEMENT (Semaine 1-2) — Sécurité :**
- ~~Les failles de path traversal dans `file_info.py`, `download_work_dir_file.py`, `api_files_get.py`.~~ **FAIT (mars 2026)** — corrige via `safe_path_join()` (voir §2.1).
- L'isolation des chats (`persist_chat.py`). Le pattern existe déjà pour les projets et les images : sous-dossiers par utilisateur + contrôle d'accès dans l'API. C'est du copier-adapter.

**ACCEPTER PROVISOIREMENT (Mois 1-3) — Architecture :**
- **L'architecture filesystem (JSON au lieu de SQL).** Ne tente PAS de migrer vers PostgreSQL ou SQLite pour les chats et settings dans les 3 premiers mois. Raisons : (a) ça fonctionne pour le volume actuel (~11 utilisateurs, ~50-100 chats), (b) une migration SGBD touche TOUT le code (persist_chat, projects, settings, file_browser), (c) le risque de régression est énorme tant que tu ne maîtrises pas la codebase. Planifie cette migration quand le volume atteindra 500+ chats ou 50+ utilisateurs simultanés, avec des benchmarks réels.
- **Le polling HTTP.** Inélégant mais fonctionnel. La migration WebSocket est un Chantier de Fond (Semaine 3-4), pas une urgence de Semaine 1.
- **Le frontend monolithique (`index.html` 1300 lignes).** Ça fait mal aux yeux, mais ça ne génère pas de bugs tant que les changements sont localisés. Un refactoring frontend complet est un projet de 2-3 semaines à planifier au trimestre suivant.
- **`asyncio.run()` dans `__init__`.** Anti-pattern connu, mais le corriger nécessite de repenser l'initialisation des agents. À planifier quand tu migreras vers un framework ASGI.

**SURVEILLER ACTIVEMENT (Monitoring) :**
- La fuite de file descriptors. Le `ulimits` à 65536 est un pansement. Mets en place un monitoring (`docker exec evidence-backend bash -c "ls /proc/1/fd | wc -l"` dans un cron toutes les heures). Quand les FD remontent vers 1000+, un `docker compose restart evidence-backend` règle le problème temporairement. La cause racine (connexions aiohttp non fermées, index FAISS non libérés) est un chantier d'investigation pour le mois 2.

## 2.6 Confusion de nommage : PRISM / Evidence / KOREV

> *Tu vas rencontrer 3 noms différents dans le code. Voici la cartographie pour ne pas te perdre.*

| Nom | Signification | Où tu le verras |
|-----|---------------|-----------------|
| **KOREV** | Nom de la société/marque | Variables d'env (`KOREV_PRODUCTION`, `KOREV_BEHIND_PROXY`), branding UI, docs |
| **Evidence** | Nom du produit | Containers Docker (`evidence-backend`), volumes (`evidence-data`), noms de classes (`EvidencePack`), documentation |
| **PRISM** | Nom historique du protocole de consensus multi-LLM | Repo GitHub (`PRISM-Oracle`), `criticality_router.py` ("consensus PRISM"), agents medical/legal ("arbitres PRISM"), certains tests (`test_prism_*`) |

**Attention :** Le repo GitHub s'appelle `PRISM-Oracle`. Ce n'est PAS le nom du produit. C'est un héritage de la phase R&D initiale. Le produit s'appelle **KOREV Evidence**.

**Clarification PRISM :** Dans le code medical, "PRISM" désigne le protocole de validation par consensus multi-LLM (3 rounds de débat). Ce n'est pas un produit distinct — c'est une fonctionnalité interne d'Evidence.

## 2.7 Montée en charge — Pires scénarios

**Scénario 1 : 50 utilisateurs simultanés**
- Le polling HTTP (25-250ms par user) génère 200-2000 requêtes/seconde juste pour le poll
- Flask en mode synchrone (Werkzeug) ne supporte pas cette charge
- Les chats sont tous chargés en mémoire — avec 50 users actifs et 20 chats chacun, c'est 1000 `AgentContext` en RAM

**Scénario 2 : Agent en boucle** ✅ (mitigé par ExecutionBudget v4.0)
- ~~Un agent qui itère 50 fois dans sa monologue (pas de hard limit) accumule du contexte à chaque tour~~ → Borné à `max_iterations=25` par défaut
- ~~Le context window du LLM explose → erreurs API → retry → plus d'itérations → plus de mémoire~~ → Borné à `max_llm_calls=30` et `deadline_seconds=300`
- Le file descriptor leak s'accélère (chaque appel LLM ouvre des connexions) — ⚠ ce risque persiste indépendamment du budget

**Scénario 3 : Indexation légale massive**
- L'index SQLite FTS5 est un fichier unique, pas de sharding
- WAL aide la concurrence lecture/écriture mais pas la performance brute
- 100K documents → requêtes de plusieurs secondes

---

# Partie 3 : Guide de Survie Opérationnel

## 3.1 Setup Environnement de Développement

### Prerequis

```bash
# Python 3.11+ (3.12 non teste)
python3 --version

# uv (gestionnaire de paquets rapide — remplace pip)
# Installation : curl -LsSf https://astral.sh/uv/install.sh | sh
uv --version

# Node.js 18+ (pour les MCP servers)
node --version

# Docker + Docker Compose (pour le deploiement)
docker --version && docker compose version

# Tesseract OCR (pour pdf_ocr et document_query)
tesseract --version

# Playwright (pour browser_agent — installe automatiquement dans Docker)
# En local : uv run python -m playwright install chromium
```

### Installation locale

```bash
# 1. Cloner le repo
git clone https://github.com/Makk7709/PRISM-Oracle.git
cd PRISM-Oracle

# 2. Installer les dependances (uv cree automatiquement le venv)
uv sync

# 3. Configuration
cp .env.example .env
# Editer .env : au minimum API_KEY_OPENROUTER (recommande) ou API_KEY_OPENAI

# 4. Lancer
uv run python run_ui.py
# → http://localhost:5050

# 5. Lancer les tests
uv run pytest tests/ -q
```

### Configuration minimale `.env`

```env
# LLM API (au moins un — OpenRouter recommande pour acces multi-modeles)
API_KEY_OPENROUTER=sk-or-...
# ou API_KEY_OPENAI=sk-...
# ou API_KEY_ANTHROPIC=sk-ant-...

# Auth (OBLIGATOIRE — sans auth, l'app demarre sans protection)
AUTH_LOGIN=dev
AUTH_PASSWORD=un-mot-de-passe-fort

# Mode dev (active la simulation du consensus, desactive les gardes production)
EVIDENCE_ENV=development

# Cle HMAC pour la signature des rapports d'audit (OBLIGATOIRE)
# Generer : python -c "import secrets; print(secrets.token_hex(32))"
EVIDENCE_HMAC_KEY=votre-cle-hmac-ici
```

### Garde-fous d'exécution (optionnel, `.env`)

Les limites du système `ExecutionBudget` sont configurables via variables d'environnement. Les défauts sont conservateurs — ne les augmenter qu'en connaissance de cause.

```env
# Anti-boucle infinie (défauts sûrs, augmenter uniquement si nécessaire)
EVIDENCE_MAX_ITERATIONS=25        # Itérations max du message loop par exécution
EVIDENCE_MAX_DEPTH=5              # Profondeur max de récursion (_process_chain)
EVIDENCE_MAX_DELEGATIONS=8        # Délégations max inter-agents
EVIDENCE_MAX_TOOL_CALLS=50        # Appels d'outils max par exécution
EVIDENCE_MAX_LLM_CALLS=30         # Appels LLM max par exécution
EVIDENCE_MAX_CONSENSUS_ROUNDS=3   # Rounds de consensus max
EVIDENCE_DEADLINE_SECONDS=300     # Timeout global en secondes
EVIDENCE_MAX_DELEGATION_REVISITS=1 # Revisites autorisées par profil (0 = strict no-cycle)
```

### Mode Production (Docker)

```bash
cd deploy
cp .env.example .env
# Editer .env avec les vrais API keys et mots de passe :
#   - API_KEY_OPENROUTER (obligatoire)
#   - AUTH_LOGIN + AUTH_PASSWORD (hash Argon2 recommande)
#   - EVIDENCE_HMAC_KEY (obligatoire — generer avec secrets.token_hex(32))
#   - KOREV_PRODUCTION=true (active les gardes production)

# Si users.json existe : mode multi-utilisateur
cp users.json.example users.json
# Editer users.json avec les comptes (hasher avec argon2)

# Build et lancer
docker compose build
docker compose up -d

# Verifier
docker compose ps
docker logs -f evidence-backend
curl -s https://<DOMAINE>/healthz
```

**Variables d'environnement critiques en production :**

| Variable | Obligatoire | Description |
|----------|:-----------:|-------------|
| `API_KEY_OPENROUTER` | Oui | Cle API pour les modeles LLM |
| `AUTH_LOGIN` / `AUTH_PASSWORD` | Oui | Identifiants (hash Argon2id recommande) |
| `EVIDENCE_HMAC_KEY` | Oui | Cle HMAC pour signature des rapports d'audit |
| `KOREV_PRODUCTION` | Recommande | `true` → refuse plaintext passwords, cookies securises |
| `EVIDENCE_RSA_PRIVATE_KEY_PATH` | Recommande | Chemin vers la cle RSA pour signatures non-repudiables |
| `EVIDENCE_RSA_KEY_ID` | Recommande | ID de la cle RSA active (ex: `001`) |

## 3.2 Arborescence des Fichiers Critiques

```
.
├── agent.py                 # ⭐ Cœur : AgentContext, Agent, monologue loop
├── models.py                # Configuration LLM (ModelConfig, providers)
├── initialize.py            # Bootstrap (agent config, job loop)
├── run_ui.py                # ⭐ Flask app, routes, auth, middleware
│
├── python/
│   ├── api/                 # ⭐ Endpoints REST (un fichier = un endpoint)
│   │   ├── projects.py      # CRUD projets + isolation owner
│   │   ├── image_get.py     # Servir images/fichiers
│   │   ├── message.py       # Recevoir messages utilisateur
│   │   └── ...
│   │
│   ├── helpers/             # ⭐ Logique métier
│   │   ├── projects.py      # Gestion projets filesystem
│   │   ├── memory.py        # FAISS vector store
│   │   ├── persist_chat.py  # Sérialisation/chargement chats
│   │   ├── settings.py      # Gestion settings (2225 lignes)
│   │   ├── user_manager.py  # Auth multi-utilisateur
│   │   ├── runtime.py       # Détection Docker, environment
│   │   ├── files.py         # I/O fichiers, templates, placeholders
│   │   ├── legal_pipeline.py # Pipeline juridique (1807 lignes)
│   │   ├── legal_orchestrator.py # Orchestration recherche juridique + FTS5
│   │   ├── legal_retrieval.py   # Récupération dans l'index juridique
│   │   ├── collaborative_consensus.py # Moteur de débat 3 rounds
│   │   ├── criticality_router.py     # Évaluation criticité (LEVEL 1-3)
│   │   ├── execution_budget.py  # Garde-fou anti-boucles infinies (budget, limites, cycles)
│   │   ├── evidence.py         # EvidencePack — tracabilite des sources
│   │   ├── audit_report_renderer.py # Assembleur des 10 blocs du rapport d'audit
│   │   ├── integrity_block.py  # SHA-256 + signatures HMAC/RSA-PSS
│   │   ├── session_envelope.py # Metadonnees session pour audit
│   │   ├── compliance_grid.py  # Grille conformite AI Act / RGPD
│   │   ├── risk_register.py    # Registre des risques Art. 9
│   │   ├── processing_register.py # Registre des traitements RGPD Art. 30
│   │   ├── report_metadata.py  # Metadonnees techniques du rapport
│   │   ├── audit_report_storage.py # Persistance + purge retention
│   │   ├── chat_style.py       # Personnalisation du chat (ton, persona, nom IA)
│   │   ├── replay_engine.py    # Replay Engine : snapshot, comparaison, integrite
│   │   ├── human_review.py     # Human Review : workflow tracable PENDING/APPROVED/REJECTED (blocage non integre en v1)
│   │   ├── dynamic_risk_register.py # Risk Engine : scoring 6 facteurs, dashboard, historisation
│   │   └── user_workspace.py   # Isolation workspaces par utilisateur
│   │
│   ├── tools/               # ⭐ Outils disponibles pour les agents
│   │   ├── call_subordinate.py  # Delegation (703 lignes)
│   │   ├── code_execution_tool.py # Execution code (555 lignes)
│   │   ├── generate_image.py    # Génération images
│   │   └── ... (23 outils)
│   │
│   ├── extensions/          # ⭐ Hooks du pipeline agent
│   │   ├── monologue_start/
│   │   ├── message_loop_prompts_before/
│   │   └── ... (24 points d'extension)
│   │
│   └── security/            # Auth, path safety, CSRF, rate limit, upload validation
│       ├── auth.py          # Argon2id, verify_password, hash_password
│       ├── authorization.py # AccessPrincipal, can_access_*, RBAC fin
│       ├── path_safety.py   # safe_path_join (anti path-traversal)
│       ├── security_audit.py # log_security_event (audit JSON structure)
│       ├── ip.py            # Extraction IP client
│       ├── shell_safety.py  # Sanitization commandes shell
│       ├── upload_validation.py # Validation fichiers uploades
│       └── rate_limit/      # Rate limiting (memory + Redis backends)
│
├── agents/                  # Profils d'agents
│   ├── default/prompts/     # Prompts de base (hérités par tous)
│   ├── multitask/           # Agent par défaut
│   ├── legal_safe/          # Mode juridique
│   └── ... (12 profils)
│
├── prompts/                 # System prompts par défaut
│   ├── agent.system.main.md # Point d'entrée (includes)
│   └── agent.system.main.*.md
│
├── webui/                   # Frontend
│   ├── index.html           # Page principale (1300 lignes)
│   ├── index.js             # Polling, sendMessage, startPolling (710 lignes)
│   ├── js/                  # Logique (messages, settings, scheduler...)
│   └── components/          # Composants Alpine.js (sidebar, modals...)
│
├── deploy/                  # Déploiement production
│   ├── docker-compose.yml   # Orchestration (backend, Caddy, Samba)
│   ├── Dockerfile.backend   # Image Docker backend
│   ├── config/Caddyfile     # Reverse proxy
│   └── scripts/             # install.sh, upgrade.sh, rollback.sh
│
└── tests/                   # Tests
    ├── security/            # Tests sécurité (auth, path traversal)
    ├── e2e/                 # Tests end-to-end
    └── harness/             # Fixtures, fakes, assertions
```

## 3.3 Tests et Déploiement

### Tests existants (~3 956 cas collectés au 28 avril 2026, 179 fichiers ; voir [`METRICS_CANONICAL_SOURCE.md`](./METRICS_CANONICAL_SOURCE.md))

```bash
# Tests securite (26 fichiers)
uv run pytest tests/security/ -v

# Tests e2e
uv run pytest tests/e2e/ -v

# Tests garde-fous anti-boucles infinies (34 tests)
uv run pytest tests/test_execution_budget.py -v

# Tests consensus / PRISM
uv run pytest tests/test_prism_consensus.py tests/test_prism_tally_quorum.py tests/test_prism_timeouts.py -v

# Tests pipeline juridique
uv run pytest tests/test_legal_pipeline.py tests/test_legal_safe.py tests/test_legal_adversarial_cases.py -v

# Tests redaction contractuelle (124 tests)
uv run pytest tests/test_contract_drafting.py tests/test_contract_drafting_phase2.py tests/test_control_prompt_ultra_strict.py -v

# Tests pipeline strategique
uv run pytest tests/test_strategic_orchestrator.py tests/test_strategic_contract.py tests/test_strategic_e2e.py -v

# Tests multi-tenant / organisation
uv run pytest tests/test_organization_canonical.py tests/test_multi_tenant_security.py -v

# Tests rapports d'audit Evidence (integrite, RSA, RBAC, registres, E2E)
uv run pytest tests/test_session8_integrity_renderer.py tests/test_session10_hardening.py tests/test_session13_document_hash_rsa.py tests/test_session15_registers.py tests/test_session16_e2e_final.py -v

# Tests router v2 (204 tests)
uv run pytest tests/test_router.py tests/test_router_contract_safety.py tests/test_router_determinism.py -v

# Tests metacognition
uv run pytest tests/test_metacognition.py tests/test_metacognition_policy.py -v

# Tests personnalisation chat
uv run pytest tests/chat_personalization/ -v

# Tests audit-proof (replay, human review, risk engine, E2E, hardening) — 107 tests
uv run pytest tests/test_replay_engine.py tests/test_human_review.py tests/test_dynamic_risk_register.py tests/test_audit_proof_e2e.py tests/test_hostile_hardening.py -v

# Tous les tests
uv run pytest tests/ -v
```

### CI/CD (GitHub Actions)

| Workflow | Trigger | Tests |
|----------|---------|-------|
| `main_gate.yml` | Pull Request vers main + workflow_dispatch | Smoke, security, Redis, core, extended |
| `security_ci.yml` | Changements dans `python/security/`, `tests/security/`, `run_ui.py` | Tests sécurité uniquement |
| `legal_pipeline_ci.yml` | Changements dans `python/legal_sources/`, `python/helpers/legal_*.py`, `python/extensions/legal_safe_mode/`, `tests/test_legal_*.py` | Pipeline juridique |

**Point critique :** Les tests "extended" ont `continue-on-error: true`. Des echecs sont silencieusement ignores. Pas de deploiement automatique (pas de CD — le deploiement est manuel via SSH + `git pull` + `docker compose build`).

**Garde-fou reseau des tests :** Le `tests/conftest.py` contient un fixture `_network_guard` (autouse) qui **bloque tous les appels LLM reels** sauf si `A0_ALLOW_REAL_LLM=1`. Cela signifie que `uv run pytest` fonctionne sans API key configuree — mais les tests verifient la logique, pas les appels reels aux LLMs.

### Procedure de deploiement actuelle

```bash
# 1. Sur la machine locale — commit avec audit hostile (protocole interne de pre-commit-audit, 3 phases)
git add <fichiers> && git commit -m "description" && git push origin main

# 2. Sur le serveur (SSH en tant que evidence)
ssh evidence@<IP_SERVEUR>
cd /home/evidence/app

# 3. Pull + rebuild + restart
git pull origin main
docker compose build evidence-backend     # ~5-15 min selon le cache
docker compose up -d evidence-backend

# 4. Verification post-deploiement
docker compose ps                          # Tous les services UP
docker logs -f evidence-backend --tail=50  # Pas d'erreur au demarrage
curl -s https://<DOMAINE>/healthz           # Doit retourner 200
```

**Important :** Ne PAS utiliser `docker cp` pour injecter des fichiers — c'est une pratique obsolete. Toutes les modifications passent par `git push` + `docker compose build`.

## 3.4 Conventions de Code et Règles Non Négociables

### Sécurité — JAMAIS faire

| Interdit | Pourquoi | Faire plutôt |
|----------|----------|--------------|
| `os.path.join(base, user_path)` sans validation | Path traversal | `safe_path_join(base, path)` de `python/security/path_safety.py` |
| Lire `.env` avec `open()` | Peut exposer des secrets | Utiliser `os.environ.get()` ou `settings.get_settings()` |
| `eval()` ou `exec()` avec input utilisateur | Injection de code | Utiliser `code_execution_tool` (⚠ pas de vrai sandbox actuellement — voir section 2.1) |
| Stocker des mots de passe en clair | Exposition | `hash_password()` de `python/security/auth.py` (Argon2id) |
| Creer un endpoint sans `@_requires_auth` | Auth bypass | Toujours utiliser le decorateur sauf pour `/healthz` et `/login` |
| Modifier `mcp_config.json` avec des chemins locaux | Fuite d'info en prod | Utiliser `mcp_config.production.json` |
| Desactiver le CSRF sans raison | CSRF attack | Protection active : `csrf_protect()` + `X-CSRF-Token` header + cookie. Ne surcharger `requires_csrf() -> False` que pour les endpoints API-key-only |

### Conventions de code

- **API handlers** : 1 fichier par endpoint dans `python/api/`, classe héritant de `ApiHandler`
- **Extensions** : fichiers préfixés `_NN_` pour l'ordre d'exécution (ex: `_10_system_prompt.py`)
- **Profils d'agents** : un répertoire sous `agents/` avec `_context.md`, `prompts/`, optionnel `tools/`, `extensions/`, `settings.json`
- **Prompts** : Markdown avec placeholders `{{variable}}` et includes `{{ include "file.md" }}`
- **Settings** : Les clés sensibles vont dans `.env`, le reste dans `tmp/settings.json`

### Architecture décisionnelle

Quand tu veux ajouter une fonctionnalité, demande-toi :
1. **C'est un outil ?** → `python/tools/nom_tool.py` + prompt dans `prompts/agent.system.tool.nom_tool.md`
2. **C'est un hook sur le pipeline ?** → Extension dans `python/extensions/<point>/`
3. **C'est un nouveau type d'agent ?** → Nouveau profil dans `agents/`
4. **C'est une API pour le frontend ?** → Handler dans `python/api/` + fetch dans `webui/js/`
5. **C'est un setting ?** → Ajouter dans `settings.py` avec les bonnes catégories

---

# Partie 4 : Feuille de Route — 30 Premiers Jours

## Semaine 1-2 : Quick Wins (Familiarisation)

### ~~Quick Win #1 : Corriger le path traversal dans `file_info.py`~~ — FAIT (mars 2026)

**Fichier :** `python/api/file_info.py`  
**Effort :** 30 minutes  
**Impact :** Ferme une vulnérabilité critique exploitable immédiatement

**Le principe de sécurité à comprendre :**

Un path traversal, c'est quand un utilisateur envoie un chemin comme `../../etc/passwd` et que le serveur le concatène naïvement avec son répertoire de base :

```python
# DANGEREUX — ne fais JAMAIS ça
path = user_input                          # "../../etc/passwd"
abs_path = os.path.join("/app", path)      # "/app/../../etc/passwd"
# os.path.join ne vérifie rien. Le résultat résolu est "/etc/passwd".
```

La fonction `safe_path_join()` (dans `python/security/path_safety.py`) corrige ça en 3 étapes :
1. **Résolution** : elle appelle `Path.resolve()` (équivalent pathlib de `os.path.realpath()`) pour résoudre tous les `..`, symlinks et chemins relatifs en un chemin absolu canonique.
2. **Vérification de confinement** : elle vérifie que le chemin résolu commence bien par le répertoire de base (`/app/`). Si le résultat est `/etc/passwd`, il ne commence pas par `/app/` → rejeté.
3. **Rejet des symlinks** (optionnel en production) : pour empêcher un attaquant qui aurait créé un symlink `/app/data/lien → /etc/`.

```python
# SÛR — le pattern à suivre
from python.security.path_safety import safe_path_join, SecurityError
try:
    resolved = safe_path_join(base_dir, user_path, allow_symlinks=False)
except SecurityError:
    raise ValueError("Path is outside of allowed directory")
```

**Correction deja appliquee :** `safe_path_join()` est utilise directement dans `file_info.py` et `api_files_get.py`. `download_work_dir_file.py` est protege indirectement via `file_info.get_file_info()` qui appelle `safe_path_join()`. Verifier avec : `grep -rn "safe_path_join" python/api/file_info.py python/api/api_files_get.py`.

### Quick Win #2 : Ajouter du logging structuré sur les erreurs 500

**Fichier :** `run_ui.py`  
**Effort :** 1 heure  
**Impact :** Diagnostiquer les crashes en production sans fouiller les logs Docker

Actuellement, les erreurs 500 retournent un message générique côté utilisateur et un traceback dans les logs Docker. Ajouter un `@app.errorhandler(500)` qui logue dans un fichier structuré (JSON) avec timestamp, username, endpoint, traceback, et retourne un ID de corrélation à l'utilisateur.

### Quick Win #3 : Documenter les profils d'agents existants

**Répertoire :** `agents/*/`  
**Effort :** 2 heures  
**Impact :** Permet à toute l'équipe de comprendre quel profil utiliser quand

Chaque profil a un `_context.md` mais ils sont inégaux en qualité. Uniformiser avec : description, cas d'usage, temperature, outils activés, garde-fous spécifiques. C'est de la documentation, pas du code — zéro risque de casser quoi que ce soit.

## Semaine 3-4 : Chantiers de Fond

### Chantier #1 : Isolation des chats par utilisateur (PRIORITÉ HAUTE)

**État actuel :** Tous les chats dans `tmp/chats/`, ownership via un champ JSON.  
**Cible :** `tmp/chats/{username}/` avec contrôle d'accès dans l'API.  

**Pourquoi c'est prioritaire :**
- Un utilisateur peut théoriquement accéder aux chats d'un autre
- Au startup, tous les chats sont chargés en mémoire (ne scale pas)
- C'est le même pattern que ce qui a été fait pour les images et les projets

**Plan d'attaque :**
1. Modifier `persist_chat.py` : `save_tmp_chat()` et `load_tmp_chats()` pour utiliser des sous-dossiers par user
2. Migrer les chats existants (script one-shot, comme pour les images)
3. Ajouter un contrôle d'accès dans `chat_load.py` (vérifier `session['username']` vs chat owner)
4. Modifier `load_tmp_chats()` pour ne charger que les chats du user connecté (lazy loading)
5. Tests dans `tests/security/test_chat_isolation.py`

### Chantier #2 : Remplacer le polling HTTP par des WebSockets (PRIORITÉ MOYENNE)

**État actuel :** Long polling 25-250ms via POST `/poll`.  
**Cible :** WebSocket (ou SSE) pour le streaming temps réel.

**Pourquoi :**
- Le polling génère une charge réseau et serveur disproportionnée
- La latence perçue est mauvaise (250ms entre le moment où l'agent répond et l'affichage)
- Flask supporte les WebSockets via `flask-sock` ou migration vers ASGI avec `quart`

**Plan d'attaque :**
1. Évaluer `flask-sock` vs migration Quart (ASGI natif)
2. Implémenter un endpoint `/ws` qui stream les logs du contexte en temps réel
3. Adapter `webui/index.js` : remplacer `startPolling()` par un `WebSocket`
4. Garder le polling comme fallback (proxies d'entreprise bloquent parfois les WS)
5. Benchmark : mesurer le nombre de requêtes/seconde avant/après

---

## Annexe A : Inventaire complet des fichiers cles

| Fichier | Lignes | Criticite | Commentaire |
|---------|--------|-----------|-------------|
| `agent.py` | ~1144 | Critique | Coeur du systeme, a comprendre en premier |
| `run_ui.py` | ~744 | Critique | Point d'entree Flask, auth, routing, middleware securite |
| `python/helpers/settings.py` | ~2225 | Eleve | Monstre : gere toute la config, les secrets, le MCP |
| `python/helpers/legal_pipeline.py` | ~1807 | Eleve | Pipeline juridique complet |
| `python/tools/call_subordinate.py` | ~703 | Critique | Delegation + consensus — orchestration multi-agents |
| `python/helpers/execution_budget.py` | ~388 | Critique | Garde-fou anti-boucles : budget, limites, cycles, deadline |
| `python/helpers/audit_report_renderer.py` | ~486 | Critique | Assembleur des 10 blocs du rapport d'audit Evidence |
| `python/helpers/integrity_block.py` | ~252 | Critique | Hashes SHA-256 + signatures HMAC/RSA-PSS |
| `python/helpers/replay_engine.py` | ~327 | Critique | Replay Engine : snapshot, comparaison, integrite |
| `python/helpers/human_review.py` | ~327 | Critique | Human Review : workflow tracable, audit trail (blocage non integre en v1) |
| `python/helpers/dynamic_risk_register.py` | ~403 | Critique | Risk Engine : 6 facteurs, scoring, dashboard |
| `python/tools/code_execution_tool.py` | ~555 | Eleve | Execution de code — surface d'attaque |
| `python/helpers/memory.py` | ~581 | Eleve | FAISS, embeddings, memoire agent |
| `python/helpers/persist_chat.py` | ~300 | Moyen | Serialisation chats — pas d'isolation user |
| `python/helpers/projects.py` | ~389 | Moyen | CRUD projets + isolation owner |
| `python/api/image_get.py` | ~237 | Moyen | Securite (safe_path_join + authz per-user) |
| `python/api/audit_reports.py` | ~129 | Moyen | Endpoint rapports d'audit RBAC (OWNER/DPO/RSSI) |
| `webui/js/messages.js` | ~1077 | Moyen | Rendu des messages — complexe |
| `webui/js/scheduler.js` | ~1835 | Moyen | Planificateur de taches |
| `models.py` | ~930 | Moyen | Providers LLM |


## Annexe B : Glossaire

| Terme | Définition |
|-------|-----------|
| **AgentContext** | Conteneur d'état pour une conversation (user, agents, log, config) |
| **Monologue** | Boucle interne d'un agent : prompt → LLM → tool → repeat |
| **Subordinate** | Agent créé par un autre via `call_subordinate` |
| **ExecutionBudget** | Système centralisé de garde-fous (`python/helpers/execution_budget.py`). Chaque exécution transporte un `ExecutionState` partagé et des `BudgetLimits`. Borne : itérations, profondeur, délégations, tool calls, LLM calls, consensus rounds, deadline. Configurable via env `EVIDENCE_*`. |
| **Extension** | Hook Python exécuté à un point précis du pipeline agent |
| **Profile** | Configuration complète d'un type d'agent (prompts, tools, extensions) |
| **CriticalityRouter** | Évalue la criticité d'une requête (LEVEL 1-3). Seuls les LEVEL 3 ou `force_consensus` déclenchent un consensus |
| **Consensus** | Débat collaboratif entre plusieurs LLMs pour valider une réponse (3 rounds : analyse indépendante → débat → synthèse) |
| **PRISM** | Nom historique du protocole de consensus multi-LLM. Utilisé dans le medical et le juridique. Le repo GitHub s'appelle encore `PRISM-Oracle` (héritage) |
| **Evidence Pack** | Objet structuré (`python/helpers/evidence.py`) qui encapsule sources, citations et métadonnées de confiance pour une réponse validée |
| **MCP** | Model Context Protocol — standard pour connecter des outils externes aux LLMs |
| **A2A** | Agent-to-Agent — protocole de communication inter-agents |
| **FAISS** | Facebook AI Similarity Search — index vectoriel pour la mémoire sémantique |
| **FTS5** | Full-Text Search 5 — module SQLite pour la recherche textuelle (index juridique) |
| **LiteLLM** | Proxy unifié pour appeler différents providers LLM (OpenAI, Anthropic, Google...) |
| **WorkspaceManager** | Gestionnaire d'espaces de travail par utilisateur (`python/helpers/user_workspace.py`) |
| **DeferredTask** | Wrapper asyncio pour exécuter la monologue agent dans un thread séparé (`python/helpers/defer.py`) |
| **SessionEnvelope** | Conteneur de metadonnees pour les rapports d'audit (ID session, user, org, horodatage) — `python/helpers/session_envelope.py` |
| **IntegrityBlock** | Bloc d'integrite cryptographique : SHA-256 + HMAC ou RSA-PSS pour les rapports d'audit — `python/helpers/integrity_block.py` |
| **ComplianceGrid** | Grille d'evaluation de conformite AI Act (Art. 9, 13, 14, 17) + RGPD Art. 30 — `python/helpers/compliance_grid.py` |
| **AuditReportRenderer** | Assembleur des 10 blocs canoniques du rapport d'audit Evidence — `python/helpers/audit_report_renderer.py` |
| **RouteDecision** | Objet de routage persiste : categorie AI Act, force du routage, profil cible — `python/helpers/router/routing_contract.py` |
| **RiskRegister** | Registre formel des risques (Art. 9 AI Act) genere automatiquement pour chaque session strategique |
| **ProcessingRegister** | Registre des activites de traitement (RGPD Art. 30) genere automatiquement |
| **AccessPrincipal** | Identite d'acces avec scoping org/workspace/user/compliance_role — `python/security/authorization.py` |
| **RateLimiter** | Systeme anti-brute-force avec backend memory ou Redis, backoff exponentiel — `python/security/rate_limit/` |
| **SessionSnapshot** | Snapshot complet d'une session pour replay deterministe : query, config modele, reponse, hashes, budget, correlation_id — `python/helpers/replay_engine.py` |
| **DivergenceReport** | Resultat de comparaison entre deux executions (NONE / MINOR / SIGNIFICANT / CRITICAL) — `python/helpers/replay_engine.py` |
| **ReviewRequest** | Demande de validation humaine avec etats PENDING_REVIEW / APPROVED / REJECTED — `python/helpers/human_review.py` |
| **ReviewDecision** | Decision d'un reviewer humain : identifiant, timestamp, justification, override — `python/helpers/human_review.py` |
| **SessionRiskAssessment** | Evaluation de risque par session : 6 facteurs ponderes, classification LOW/MEDIUM/HIGH/CRITICAL — `python/helpers/dynamic_risk_register.py` |
| **SystemRiskDashboard** | Tableau de bord agrege des risques systeme — `python/helpers/dynamic_risk_register.py` |

## Annexe C : Contacts et Ressources

| Ressource | Emplacement |
|-----------|-------------|
| Repo GitHub | `https://github.com/Makk7709/PRISM-Oracle` |
| Serveur Production | OVH VPS (`evidence@<IP>`), Docker Compose |
| Documentation existante | `docs/` (46 fichiers — architecture, installation, legal, consensus, audit, deploiement) |
| CI/CD | `.github/workflows/` (main_gate, security_ci, legal_pipeline_ci) |
| Logs production | `docker logs evidence-backend` ou volume `evidence-logs` |
| Audit hostile | `audit-hostile-valorisation/` (7 livrables d'audit qualite) |
| Societe | KOREV AI — licence proprietaire |

## Annexe D : Matrice de Priorité (Vue Synthétique)

| Action | Urgence | Effort | Risque si ignoré |
|--------|---------|--------|------------------|
| ~~Patcher path traversal (`file_info`, `download_work_dir_file`, `api_files_get`)~~ | FAIT (mars 2026) | — | ~~Lecture arbitraire de fichiers~~ → Corrige via `safe_path_join()` |
| ~~Ajouter `max_iterations` à la monologue~~ | ✅ FAIT (v4.0) | — | ~~Agent en boucle infinie~~ → Borné par `ExecutionBudget.max_iterations=25` + `max_llm_calls=30` + `deadline=300s` |
| ~~Ajouter `max_depth` à la délégation~~ | ✅ FAIT (v4.0) | — | ~~Stack overflow, délégation récursive infinie~~ → Borné par `ExecutionBudget.max_depth=5` + `max_delegations=8` + cycle detection |
| Monitoring file descriptors | Semaine 1 | 1 heure (cron) | Crash backend en production (déjà observé) |
| Logging structuré des erreurs 500 | Semaine 1-2 | 1 heure | Diagnostics aveugles en production |
| Isoler les chats par utilisateur | Semaine 2-3 | 2-3 jours | Un utilisateur accède aux conversations d'un autre |
| Documenter les profils agents | Semaine 2 | 2 heures | Équipe ne sait pas quel profil utiliser |
| Remplacer polling par WebSocket | Mois 1-2 | 1 semaine | Latence élevée, charge serveur, ne scale pas |
| Sandbox code execution | Mois 2-3 | 1-2 semaines | Agent hallucinant peut détruire des données |
| Migrer filesystem vers SGBD | Mois 4+ | 3-4 semaines | Race conditions, pas de transactions (acceptable court terme) |
| Refactoring frontend | Mois 4+ | 2-3 semaines | Maintenance difficile (acceptable court terme) |

## Annexe E : Checklist "Premier Jour"

- [ ] Cloner le repo et lancer le backend en local (`uv sync && uv run python run_ui.py`)
- [ ] Se connecter a l'interface web, creer un chat, envoyer un message
- [ ] Lire `agent.py` en entier (1144 lignes — compte 2 heures)
- [ ] Lire `python/tools/call_subordinate.py` (703 lignes — le coeur multi-agents)
- [ ] Lire `python/helpers/audit_report_renderer.py` (486 lignes — le systeme de rapports d'audit)
- [ ] Lire `python/helpers/replay_engine.py` (~327 lignes — snapshot, comparaison, integrite)
- [ ] Lire `python/helpers/human_review.py` (~327 lignes — workflow tracable PENDING/APPROVED/REJECTED, blocage non integre en v1)
- [ ] Lire `python/helpers/dynamic_risk_register.py` (~403 lignes — scoring 6 facteurs, dashboard)
- [ ] Ouvrir un chat en mode `legal_safe`, poser une question juridique, observer la delegation et la validation multi-LLM dans les logs
- [ ] Se connecter au serveur production en SSH, verifier `docker compose ps`, lire les derniers logs
- [ ] Lancer `uv run pytest tests/ -q` et verifier la collecte (snapshot canonique : ~3 956 cas au 28 avril 2026 ; voir [`METRICS_CANONICAL_SOURCE.md`](./METRICS_CANONICAL_SOURCE.md)). Le network guard bloque les appels reels sans API key.
- [ ] Lancer `uv run pytest tests/test_replay_engine.py tests/test_human_review.py tests/test_dynamic_risk_register.py tests/test_audit_proof_e2e.py tests/test_hostile_hardening.py -v` pour verifier les 107 tests audit-proof
- [ ] Verifier la section securite de `python/security/` et lire `image_get.py` comme modele de bonne pratique (safe_path_join + authz)

---

*Ce document est un instantane au 2026-04-04 (Evidence v1.4.0 — replay engine, human review workflow, dynamic risk register, audit-proof pipeline, +107 tests). Audit de conformite document/code effectue le 2026-04-04 (v7.1). Il doit etre mis a jour a chaque changement architectural majeur. En cas de doute sur une information, la source de verite est toujours le code, pas ce document.*
