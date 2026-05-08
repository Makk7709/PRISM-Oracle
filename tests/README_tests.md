<!-- markdownlint-disable MD022 MD031 MD032 MD040 MD058 MD060 -->

# KOREV Evidence — Suite de Tests

## Vue d'ensemble

**État de référence documentaire : 3 910 tests collectés avec paramétrisation** — environ 180 fichiers de tests couvrant sécurité, consensus, pipelines métier, multi-tenant, observabilité, router, audit-proof et non-régression.

> Note du 25 avril 2026 : une collecte locale sous Python 3.9.6 a été interrompue après **3 608 tests collectés** et 19 erreurs de compatibilité de syntaxe/type hints (`|` unions, `dataclass(slots=...)`). Les métriques de référence du dossier de valorisation supposent l'environnement Python supporté par le projet, pas l'interpréteur système macOS 3.9.

```
tests/
├── security/               # 31 fichiers — auth, authorization, rate limiting, multi-tenant, CSRF, path traversal
├── e2e/                    # 2 fichiers — scénarios end-to-end (PRISM, multi-user)
├── property/               # 1 fichier — tests de propriétés/invariants
├── chat_personalization/   # 2 fichiers — style de chat et extensions
├── harness/                # Framework de test déterministe
│   ├── fakes.py           # FakeLLM, FakeTools, FakeMCP, FaultInjector
│   ├── fixtures.py        # Scénarios E2E
│   └── assertions.py      # Assertions spécialisées
└── test_*.py               # 101 fichiers — tests unitaires et intégration
```

## Commandes rapides

### FAST GATE (~5 secondes)
```bash
pytest tests/test_prism_contract.py tests/test_prism_tally_quorum.py -q
```

### SECURITY GATE (~30 secondes)
```bash
pytest tests/security/ -q
```

### FULL GATE (tous les tests)
```bash
python -m pytest tests/ -q
```

## Couverture par domaine

### Sécurité & Multi-Tenant (31 fichiers)
| Fichier | Tests | Description |
|---------|-------|-------------|
| `test_auth.py` | Auth Argon2, sessions | Login, logout, hash validation |
| `test_authorization_policy.py` | AccessPrincipal, scope | Isolation cross-org, rôles OWNER/MEMBER |
| `test_multi_user_auth.py` | Multi-user auth flow | Comptes simultanés, sessions isolées |
| `test_multi_user_flask.py` | Flask integration | API endpoints avec scope multi-user |
| `test_notification_scope.py` | Notifications scoppées | target_username + target_organization |
| `test_scheduler_fail_closed.py` | Scheduler fail-closed | Blocage tâches sans scope |
| `test_session_scope_resolution.py` | Session scope | Résolution organization dans session |
| `test_transactional_stores.py` | Redis/JSON stores | TaskStore, NotificationStore |
| `test_rate_limit*.py` | Rate limiting (4 fichiers) | Mémoire, Redis, coverage, limiter |
| `test_path_safety.py` | Path traversal | Protection `../`, symlinks |
| `test_upload_validation.py` | Upload security | Validation fichiers uploadés |
| `test_user_workspace.py` | Workspace isolation | Isolation par utilisateur |
| `test_shell_safety.py` | Shell injection | Protection commandes shell |
| `test_document_query_injection.py` | Prompt injection | Protection document_query |
| `test_file_writer_path_traversal.py` | File writer safety | Écriture hors workspace bloquée |

### Consensus & PRISM (8 fichiers)
| Fichier | Description |
|---------|-------------|
| `test_prism_contract.py` | Schéma JSON vote strict |
| `test_prism_tally_quorum.py` | Quorum 2/3, calcul tally |
| `test_prism_timeouts.py` | Timeouts déterministes (250-300ms) |
| `test_prism_consensus.py` | Pipeline consensus complet |
| `test_evidence_prism_integration.py` | Intégration Evidence + PRISM |
| `test_consensus_effective_votes.py` | Votes effectifs |
| `test_consensus_fail_soft_envelope.py` | Enveloppe fail-soft |
| `test_consensus_no_simulation_prod.py` | Pas de simulation en prod |

### Pipeline Juridique (14 fichiers)
| Fichier | Description |
|---------|-------------|
| `test_legal_pipeline.py` | Pipeline complet (index FTS5, retrieval, classification) |
| `test_legal_safe.py` | Mode legal_safe (température 0, citations) |
| `test_legal_safe_integration.py` | Intégration legal_safe |
| `test_legal_adversarial_cases.py` | Cas adversariaux juridiques |
| `test_legal_sources.py` | Sources juridiques (PISTE, Judilibre) |
| `test_legal_diff*.py` | 5 fichiers — diffing juridique (golden, fuzz, needle, mutations, properties) |
| `test_legal_orchestrator.py` | Orchestration juridique |
| `test_legal_posture_refusal.py` | Refus de posture |
| `test_legal_tone_invariants.py` | Invariants de ton juridique |
| `test_legal_versioning.py` | Versioning juridique |

### Pipeline Rédaction Contractuelle (4 fichiers)
| Fichier | Description |
|---------|-------------|
| `test_contract_drafting.py` | Templates, Act Leak Guard, Gate d'audit |
| `test_contract_drafting_hardened_v2.py` | Version durcie |
| `test_contract_drafting_phase2.py` | Phase 2 (annexes, export control) |
| `test_contract_drafting_tdd_strict.py` | TDD strict |

### Pipeline Stratégique (4 fichiers)
| Fichier | Description |
|---------|-------------|
| `test_strategic_orchestrator.py` | Détection, orchestration 4 agents |
| `test_strategic_contract.py` | Contrat de sortie stratégique |
| `test_strategic_e2e.py` | E2E pipeline complet |
| `test_strategic_pipeline_e2e.py` | Pipeline E2E (agents → consolidation → PDF) |

### Router v2 (4 fichiers)
| Fichier | Description |
|---------|-------------|
| `test_router.py` | Routage policy-driven, keywords, multi-intent |
| `test_router_contract_safety.py` | Safety contracts du router |
| `test_router_determinism.py` | Déterminisme du routage |
| `test_router_metrics.py` | Métriques du router |

### Organisation & Multi-Tenant (3 fichiers)
| Fichier | Description |
|---------|-------------|
| `test_organization_canonical.py` | normalize_org_id(), slugification, collision detection |
| `test_multi_tenant_security.py` | Isolation stricte cross-org |
| `test_chat_rename.py` | Renommage chats (scope multi-tenant) |

### Métacognition & Reasoning (4 fichiers)
| Fichier | Description |
|---------|-------------|
| `test_metacognition.py` | ReasoningEngine |
| `test_metacognition_policy.py` | Politique escalade non-diluable |
| `test_reasoning_engine.py` | Engine complet |
| `test_criticality_router.py` | Routage criticité |

### Médical (2 fichiers)
| Fichier | Description |
|---------|-------------|
| `test_medical_agent_hardening.py` | Durcissement agent médical |
| `test_medical_contract_kill.py` | Kill switch médical |

### PDF & OCR (10 fichiers)
| Fichier | Description |
|---------|-------------|
| `test_ocr_engine.py` | Moteur OCR (Tesseract) |
| `test_ocr_e2e.py` | E2E OCR |
| `test_pdf_extraction_pipeline_timeouts.py` | Timeouts extraction |
| `test_pdf_e2e_new_pipeline.py` | Nouveau pipeline PDF |
| `test_pdf_characterization.py` | Caractérisation PDF |
| `test_pdf_file_reader.py` | Lecteur PDF |
| `test_evidence_document.py` | Système document AST |
| `test_markdown_pdf_shim.py` | Shim Markdown → PDF |
| `test_pdf_migration_parity.py` | Parité migration |
| `test_pdf_ocr_tool.py` | Outil PDF OCR |

### Observabilité (3 fichiers)
| Fichier | Description |
|---------|-------------|
| `test_observability_logs.py` | Logs structurés JSON |
| `security/test_observability_metrics_api.py` | API métriques |
| `security/test_observability_runtime.py` | Runtime observability |

### Divers
| Fichier | Description |
|---------|-------------|
| `test_execution_budget.py` | Garde-fous anti-boucles infinies (34 tests) |
| `test_execution_guard.py` | Guard d'exécution |
| `test_anti_bypass.py` | Anti-contournement |
| `test_identity_branding.py` | Identité et branding Evidence |
| `test_docker_deploy_scripts.py` | Scripts de déploiement Docker |
| `test_image_generation.py` | Génération d'images |
| `test_fasta2a_client.py` | Client A2A |
| `test_task_planner.py` | Planification de tâches |
| `test_scheduler_visibility.py` | Visibilité scheduler |
| `test_document_workload.py` | Workload documents |
| `test_research_tool_policy.py` | Policy outil recherche |

## Invariants testés

### 1. Fail-closed
Toute erreur, timeout, ou incertitude → REJECT. Jamais d'approbation par défaut.

### 2. Isolation multi-tenant
Aucune donnée d'une organisation ne fuit vers une autre. Testé par matrix cross-org.

### 3. Quorum 2/3
Minimum 2/3 des votes valides pour une décision consensus.

### 4. Anti-bypass
Outils interdits non appelés. Sanitization du contenu. Pas d'injection de prompt.

### 5. Déterminisme
temp=0 forcé pour les profils critiques. Mêmes inputs → mêmes outputs.

### 6. Non-dilution (métacognition)
Les signaux d'escalade ne peuvent que durcir, jamais s'adoucir.

## Contraintes qualité

- **100% offline** : aucun appel réseau (sauf tests tagged "integration")
- **Zéro flaky** : pas de sleep réel, seeds fixes
- **Messages explicites** : assertions parlantes
- **Pas de données sensibles** dans les fixtures
- **Typage strict** (si mypy disponible)

## Troubleshooting

### Erreur `unsupported operand type(s) for |: 'type' and 'NoneType'`
Python 3.9 ne supporte pas la syntaxe `X | None`. Solutions :
- Utiliser Python 3.10+
- Ajouter `from __future__ import annotations` en haut du fichier

### Import error (whisper, etc.)
Certains modules lourds (whisper, kokoro) ne sont disponibles que dans Docker.
```bash
pytest tests/ -k "not whisper" -q
```
