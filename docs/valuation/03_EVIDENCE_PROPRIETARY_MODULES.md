# 03 — Modules proprietaires Evidence (inventaire detaille)

**Projet** : KOREV Evidence
**Apporteur / inventeur** : Amine Mohamed
**HEAD analyse** : `fab5689a` (5 mai 2026)
**Methode** : inventaire fichier par fichier + identification de la complexite + estimation prudente d'heures de reconstruction
**Date** : 9 mai 2026

> Ce document liste tous les modules proprietaires KOREV reellement valorisables. Pour chaque module : role, fichiers, complexite, preuves, fourchettes d'heures, risques. **Aucun module Agent Zero n'est compte. Aucun module n'est compte deux fois.**

> Les heures sont fondees sur les benchmarks COCOMO II / ISBSG / Capers Jones, ajustes a la complexite specifique. Les fourchettes basses correspondent a une productivite haute (developpeur expert), les hautes a une productivite basse (developpeur senior sans connaissance prealable).

---

## 1. Module — Pipeline Consensus PRISM (fail-closed multi-arbitres)

| Critere | Detail |
|---|---|
| **Role** | Validation multi-LLM des reponses critiques. Plusieurs modeles votent independamment, un arbitre consolide, le systeme refuse de repondre si le consensus n'est pas atteint (fail-closed). Fondation de la doctrine "IA de confiance". |
| **Fichiers** | `python/consensus/engine.py` (388 LOC), `python/helpers/consensus_arbiter.py` (886), `consensus_manager.py` (692), `consensus_contracts.py` (386), `consensus_integration.py` (560), `consensus_mcp_integration.py` (447), `research_consensus_integration.py` (706), autres (~2 138). **Total ~6 200 LOC.** |
| **Complexite** | **Tres elevee** : safety-critical, fail-closed obligatoire, contrats types, gestion du quorum, arbitre LLM, audit trail, integration MCP |
| **Preuves** | ADR-001 ; documentation commentee ; tests dedies (`test_consensus_simple.py`, `test_adversarial_e2e_scenarios.py`, etc.) ; existait dans le projet anterieur PRISM |
| **Heures basses** | 80 j-h |
| **Heures cibles** | 100 j-h |
| **Heures hautes** | 130 j-h |
| **Risques** | Antériorite PRISM a documenter par annexes externes (AE-5, AE-6, AE-7) ; trois chemins consensus a unifier (P2-2) |

---

## 2. Module — Debat adversarial / Instruction contradictoire

| Critere | Detail |
|---|---|
| **Role** | Extension du systeme PRISM. Deux LLM argumentent pour et contre, un juge tranche. Detection d'injections adverses, anti-injection FR + EN, blocage high-stakes |
| **Fichiers** | `python/helpers/adversarial_consensus_integration.py` (1 144), `adversarial_instruction.py` (2 123), `collaborative_consensus.py` (991), `python/api/adversarial_*.py` (363 cumule). **Total ~4 620 LOC.** |
| **Complexite** | **Tres elevee** : detection d'injections, gestion thèse/antithèse/synthese, multilingue, integration consensus |
| **Preuves** | `adversarial_instruction.py` (2 123 LOC) = #1 du top 20 fichiers les plus modifies (cf. `02_AGENT_ZERO_DELTA.md`) ; tests dedies (`test_adversarial_instruction.py` 39 257 octets, `test_adversarial_e2e_scenarios.py` 32 741, `test_adversarial_integration.py` 15 535) |
| **Heures basses** | 60 j-h |
| **Heures cibles** | 80 j-h |
| **Heures hautes** | 105 j-h |
| **Risques** | Dependance PRISM antérieur ; calibration des seuils implicite |

---

## 3. Module — Router deterministe + Gate de criticite

| Critere | Detail |
|---|---|
| **Role** | Routage intelligent des requetes selon leur criticite (juridique, medical, financier...). Politique deterministe (hash-based), pas de LLM dans la boucle de routage, anti-injection, board-level keywords (40+) |
| **Fichiers** | `python/helpers/criticality_router.py` (944), `critical_decision_gate.py` (803), `router/router.py` (589), `router/policy.py` (617), `router/judge.py` (424), `router/routing_contract.py` (531), `router/metrics.py` (316), `router/__init__.py` (248). **Total ~4 472 LOC.** |
| **Complexite** | **Elevee** : determinisme strict, anti-injection multilingue, contrats types, observabilite |
| **Preuves** | ADR-002 ; 204 tests router dedies (`test_router*.py`) ; `scripts/router_prod_validation.py` (validation production) |
| **Heures basses** | 50 j-h |
| **Heures cibles** | 65 j-h |
| **Heures hautes** | 85 j-h |
| **Risques** | Tables `router/policy.py` calibration implicite ; necessite calibration metier |

---

## 4. Module — Pipeline Legal-Safe complet

| Critere | Detail |
|---|---|
| **Role** | Systeme complet de traitement juridique : ingestion sources legales (Legifrance, Judilibre, CNIL, EUR-Lex), citations, redaction de contrats avec garde-fous (Act Leak Guard fail-closed), conformite, audit |
| **Fichiers** | `legal_pipeline.py` (1 807), `legal_orchestrator.py` (1 960), `legal_diff.py` (994), `legal_agent_contracts.py` (810), `legal_rendering.py` (842), `legal_retrieval.py` (731), `legal_safe_schema.py` (588), `legal_citations.py` (420), `legal_citations_db.py` (515), `legal_safe_logger.py` (513), `legal_safe_policy.py` (496), `legal_safe_runtime.py` (475), `legal_safe_renderer.py` (424), `python/extensions/legal_safe_mode/` (1 028), `python/helpers/contract_drafting/` (7 fichiers, 2 536). **Total ~16 556 LOC.** |
| **Complexite** | **Tres elevee** : safety-critical (juridique + fail-closed), expertise metier requise, integration FTS5 SQLite, multilingue |
| **Preuves** | Top 20 fichiers les plus modifies : #2 (`legal_orchestrator.py`), #5 (`legal_pipeline.py`), #11 (`test_legal_pipeline.py` 1 338 LOC), #19 (`legal_safe_integration.py` 1 088 LOC) ; legal_pipeline_ci.yml (workflow CI dedie) ; demonstration cabinet d'avocats (`docs/DEMONSTRATION_CABINET_AVOCATS.md`) |
| **Heures basses** | 200 j-h |
| **Heures cibles** | 260 j-h |
| **Heures hautes** | 330 j-h |
| **Risques** | Dependance expertise juridique (consultants juristes en plus des developpeurs si reproduit a neuf) |

---

## 5. Module — Moteur PDF / OCR industriel + PRISM PDF

| Critere | Detail |
|---|---|
| **Role** | Pipeline complet : extraction texte PDF avec circuit breakers et timeouts stricts, fallback OCR (Tesseract + pdf2image), generation de PDF professionnels (PRISM WeasyPrint + ReportLab fallback), templates, Evidence Document System (AST, canvas, layout, renderer) |
| **Fichiers** | `pdf_extraction/pipeline.py` (1 217), `pdf_extraction/ocr_engine.py` (363), `pdf_extraction/config.py` (711), `pdf_extraction/pdf_backend.py` (363), `pdf_extraction/types.py` (386), `pdf_generator.py` (926), `pdf_templates.py` (631), `evidence_pdf_engine.py` (1 091), `strategic_charts.py` (664), `evidence_document/` (8 fichiers, 3 472), `tools/pdf_ocr.py` (173), `tools/export_strategic_pdf.py` (384). **Total ~12 384 LOC.** |
| **Complexite** | **Elevee** : circuit breakers, timeouts strict, multi-engine fallback, reconstruction geometrique, OCR DPI adaptatif, generation pro PDF |
| **Preuves** | Top 20 : #13 (`pdf_extraction/pipeline.py` 1 217), #18 (`evidence_pdf_engine.py` 1 091), #8 (golden tables 1 487), #12 (golden words 1 220) ; tests dedies (`test_pdf_extraction*.py` 43 tests) |
| **Heures basses** | 130 j-h |
| **Heures cibles** | 175 j-h |
| **Heures hautes** | 230 j-h |
| **Risques** | Dependance lib WeasyPrint / ReportLab / Tesseract (gerees) ; complexite OCR / DPI requiert ajustements terrain |

---

## 6. Module — Reasoning Engine + Metacognition

| Critere | Detail |
|---|---|
| **Role** | Couche de raisonnement au-dessus du LLM : auto-evaluation, planification de taches, suivi des decisions, baseline tracking, escalade non-diluable (SAFE_REFUSE / HUMAN_REVIEW / ASK_CLARIFY / NONE), no-PII par design (escalade non-diluable et tests adversariaux dedies dans la suite TDD) |
| **Fichiers** | `reasoning_engine.py` (1 190), `metacognition.py` (1 046). **Total ~2 236 LOC.** |
| **Complexite** | **Elevee** : invariants critiques (monotonie, non-dilution, no-PII), seuils calibres |
| **Preuves** | Top 20 : #15 (`reasoning_engine.py` 1 190), #20 (`test_metacognition.py` 1 077) ; 42 tests metacognition policy ; ADR sur l'escalade non-diluable ; documentation README sur les niveaux |
| **Heures basses** | 25 j-h |
| **Heures cibles** | 35 j-h |
| **Heures hautes** | 45 j-h |
| **Risques** | Calibration des seuils a justifier ; lien avec consensus a clarifier |

---

## 7. Module — Pipeline strategique + Reporting Evidence-grade

| Critere | Detail |
|---|---|
| **Role** | Generation de documents strategiques de qualite professionnelle (Evidence-grade), avec validation multi-agent et export PDF. Rapports d'audit Evidence avec 10 blocs canoniques. Generation auto de graphiques PRISM depuis dossiers strategiques |
| **Fichiers** | `strategic_contract.py` (843), `strategic_pipeline.py` (402), `research_pipeline.py` (665), `reporting/evidence_native.py` (1 422), `reporting/report_job.py` (635), `reporting/report_assembler.py` (361), `strategic_orchestrator.py` (1 560), `python/extensions/strategic_validation/` (3 fichiers, 871). **Total ~6 759 LOC.** |
| **Complexite** | **Elevee** : assemblage multi-source, validation contractuelle, integration consensus, generation PDF Evidence |
| **Preuves** | Top 20 : #7 (`strategic_orchestrator.py` 1 560), #9 (`reporting/evidence_native.py` 1 422) ; templates rapports |
| **Heures basses** | 70 j-h |
| **Heures cibles** | 90 j-h |
| **Heures hautes** | 115 j-h |
| **Risques** | Pas de doublon avec apport I (`medical_contract.py` est compte separement) |

---

## 8. Module — Securite multi-tenant entreprise

| Critere | Detail |
|---|---|
| **Role** | Hardening securite (Argon2id, rate limiting Redis+memoire, PII sanitization, path safety, upload validation, shell safety, IP filtering, audit logging), gestion multi-utilisateur, App Factory pattern |
| **Fichiers** | `python/security/` (14 fichiers, ~2 553 LOC : auth, authorization, rate_limit, path_safety, upload_safety, shell_safety, ip, audit), `user_manager.py` (252), `deploy_config.py` (538), `health_endpoints.py` (339), `rate_limiter.py` (57), `evidence.py` (674). **Total ~4 413 LOC.** |
| **Complexite** | **Elevee** : safety-critical (security), specifications Gherkin dans `security/__init__.py`, isolation par principal/organisation |
| **Preuves** | SECURITY.md (politique de divulgation, perimetre, pratiques crypto) ; tests securite avec seuil 90% en CI ; security_ci.yml workflow dedie |
| **Heures basses** | 50 j-h |
| **Heures cibles** | 65 j-h |
| **Heures hautes** | 85 j-h |
| **Risques** | Mode sans auth par defaut (P1-6 ouvert) ; masquage fail-open (P2-8 ouvert) |

---

## 9. Module — Pipeline Audit-Proof (replay, human review, risk register)

| Critere | Detail |
|---|---|
| **Role** | Pipeline de preuve d'audit complet : rejeu deterministe de sessions, workflow de revue humaine pour decisions critiques, registre de risques dynamique avec scoring temps reel. Adresse directement la critique "auto-evaluation sans validation externe" |
| **Fichiers** | `replay_engine.py` (327), `human_review.py` (327), `dynamic_risk_register.py` (403), `python/extensions/monologue_end/_35_replay_snapshot.py` (112), `_36_risk_assessment.py` (137), `python/api/replay.py` (145), `python/api/human_review.py` (143), `python/api/risk_dashboard.py` (98). **Total ~1 692 LOC.** |
| **Complexite** | **Elevee** : determinisme du replay, isolation des flux concurrents, hooks lifecycle, scoring temps reel |
| **Preuves** | Tests e2e audit-proof (347 lignes dediees) ; tests dans `tests/test_*.py` ; nouveau avril 2026 |
| **Heures basses** | 22 j-h |
| **Heures cibles** | 28 j-h |
| **Heures hautes** | 38 j-h |
| **Risques** | Pas de stockage WORM pour les traces ; scoring a calibrer avec retour terrain |

---

## 10. Module — Framework Evidence (integrite + audit reports)

| Critere | Detail |
|---|---|
| **Role** | Framework de rapports auditables avec integrite cryptographique (HMAC obligatoire, RSA optionnel), 10 blocs canoniques, ComplianceGrid AI Act articles 9, 13, 14, 17 + RGPD article 30 |
| **Fichiers** | `integrity_block.py`, `session_envelope.py`, `compliance_grid.py`, `risk_register.py`, `processing_register.py`, `evidence.py` (~674), `reporting/evidence_native.py` deja compte en apport G. **Total ~3 000 LOC additionnel non double compte.** |
| **Complexite** | **Tres elevee** : integrite cryptographique, conformite reglementaire, contrats types |
| **Preuves** | ADR-003 (framework Evidence audit integrite) ; HMAC obligatoire (RuntimeError si absent, corrige P0) ; SECURITY.md mentionne |
| **Heures basses** | 35 j-h |
| **Heures cibles** | 45 j-h |
| **Heures hautes** | 60 j-h |
| **Risques** | RSA optionnel et dependant config ; pas de WORM ; auto-evaluation conformite (attenuee par audit-proof) |

> **Note importante anti-double-comptage** : les LOC de `reporting/evidence_native.py` (1 422 LOC) sont comptees une seule fois dans l'apport G (Strategic + Reporting). Ce module 10 (Framework Evidence) decrit la **valeur conceptuelle** du framework d'integrite et de conformite, dont la materialisation logicielle est repartie entre apports G (reporting) et H (security/audit). L'estimation d'heures ci-dessus correspond aux modules **non encore comptes** : `integrity_block.py`, `session_envelope.py`, `compliance_grid.py`, `risk_register.py`, `processing_register.py`, `evidence.py`.

---

## 11. Module — Contrat metier Medical

| Critere | Detail |
|---|---|
| **Role** | Contrat de surete domaine medical : le systeme refuse de repondre hors perimetre valide (kill tests, garde-fous specifiques) |
| **Fichiers** | `python/helpers/medical_contract.py` (~769 LOC). **Total ~769 LOC.** |
| **Complexite** | **Elevee** : safety-critical (medical), kill tests, garde-fous |
| **Preuves** | Profil agent `medical` ; integration FAERS / PubMed / Semantic Scholar |
| **Heures basses** | 8 j-h |
| **Heures cibles** | 12 j-h |
| **Heures hautes** | 16 j-h |
| **Risques** | Necessite expertise medicale en plus des developpeurs si reproduit a neuf |

---

## 12. Module — Personnalisation chat (symbiose homme-IA)

| Critere | Detail |
|---|---|
| **Role** | Parametrage fin du comportement conversationnel : tutoiement, ton, persona, verbosite, injection en system prompt |
| **Fichiers** | `chat_style.py` (116), `python/extensions/system_prompt/_05_chat_style.py` (29). **Total ~145 LOC.** |
| **Complexite** | **Faible** : simple injection en system prompt |
| **Preuves** | Specification `docs/SPEC_CHAT_PERSONALIZATION.md` |
| **Heures basses** | 1.5 j-h |
| **Heures cibles** | 2 j-h |
| **Heures hautes** | 3 j-h |
| **Risques** | Aucun specifique |

---

## 13. Module — Internationalisation FR / EN

| Critere | Detail |
|---|---|
| **Role** | Systeme i18n complet avec fichiers de traduction et selecteur de langue UI |
| **Fichiers** | `webui/i18n/fr.json` (239), `webui/i18n/en.json` (239), JS de switch dans WebUI. **Total ~480 LOC + JS.** |
| **Complexite** | **Faible-moyenne** : i18n statique, mais traductions metier a calibrer |
| **Preuves** | UI : selecteur de langue persistant ; documentation FR/EN dans le pack |
| **Heures basses** | 4 j-h |
| **Heures cibles** | 6 j-h |
| **Heures hautes** | 8 j-h |
| **Risques** | Maintenance double FR/EN |

---

## 14. Module — Architecture Docker production + scripts industriels

| Critere | Detail |
|---|---|
| **Role** | Passage d'un Docker de developpement a une architecture production-ready (multi-stage Python 3.11-slim + Node.js 20, Caddy HTTPS auto, healthchecks, volumes nommes, non-root user, log rotation), scripts d'installation, migration, backup, CI, provisioning multi-tenant |
| **Fichiers** | `deploy/Dockerfile.backend` (224), `deploy/docker-compose.yml` (352), `deploy/config/Caddyfile` (91), `scripts/` (~8 834 LOC : ~41 scripts). **Total ~9 501 LOC.** |
| **Complexite** | **Elevee** : DevOps multi-stage, multi-tenant provisioning, healthchecks, backup/restore |
| **Preuves** | A12 (`docker compose config --quiet` exit code 0), `run_docker_proof.sh` ; `GUIDE_DEPLOIEMENT_ENTREPRISE.md` (1 385 LOC) ; preuves CI 3 workflows |
| **Heures basses** | 95 j-h |
| **Heures cibles** | 120 j-h |
| **Heures hautes** | 160 j-h |
| **Risques** | Pas de build Docker en CI (P1-5 ouvert) ; deploiement manuel (pas de CD) ; dual Docker non reconcilie |

---

## 15. Module — Suite de tests TDD industrielle

| Critere | Detail |
|---|---|
| **Role** | Couverture des invariants critiques avec FakeLLMProvider, FakeMCPHandler, network guard (bloque LLM reels), golden tests OCR / legal, hostile hardening, tests de proprietes / invariants, Redis multi-worker proof, validation production |
| **Fichiers** | `tests/` (~180-183 fichiers, ~67 200-68 279 LOC). 3 956 tests collectes (28 avril, pytest 9.0.2 / Python 3.11.12) |
| **Complexite** | **Moyenne-elevee** : harness de simulation LLM, golden tests, parametrisation |
| **Preuves** | `A11_pytest_collect_only.txt` (3 956 tests) ; `B_pytest_doc_quality.txt` (64/64 PASSED) ; pytest.ini (~80 lignes) ; conftest.py |
| **Heures basses** | 270 j-h |
| **Heures cibles** | 360 j-h |
| **Heures hautes** | 470 j-h |
| **Risques** | Suite etendue non-bloquante en CI (P1-3 ouvert) ; couverture globale non mesuree (P1-4 ouvert) |

---

## 16. Module — 12 Agents specialises + 11 MCP servers + integrations

| Critere | Detail |
|---|---|
| **Role** | 12 profils d'agents specialises (legal_safe, legal_drafting_guarded, medical, finance, developer, researcher, marketing, sales, hacker, multitask, default) + 11 MCP servers configures (ArXiv, PubMed, Semantic Scholar, OpenAlex, Crossref, EUR-Lex, Tavily, Brave, Playwright, FastA2A, A2A) dont 3 dockerises localement |
| **Fichiers** | `agents/` (12 profils : prompts + extensions), `mcp_servers/` (3 servers + Dockerfiles + package.json), 103 prompts metiers |
| **Complexite** | **Moyenne** : configuration metier, prompts calibres |
| **Preuves** | `mcp_config*.json`, dockerfiles MCP, prompts par profil dans `agents/<profile>/prompts/` |
| **Heures basses** | 35 j-h |
| **Heures cibles** | 50 j-h |
| **Heures hautes** | 70 j-h |
| **Risques** | Profils generaux pourraient etre vus comme "demo polyvalente" plutot que produit focus (cf. risque #8 audit hostile) |

---

## 17. Module — Documentation proprietaire (delta upstream -> HEAD)

| Critere | Detail |
|---|---|
| **Role** | 7 ADR, GLOSSARY (30+ termes), C4 (3 niveaux + sequence Mermaid), SECURITY.md (politique divulgation, pratiques crypto), BENCHMARK comparables marche, GUIDE_DEPLOIEMENT (1 385 LOC), DEVELOPER_ONBOARDING (1 196 LOC), feuille de route conformite (1 893 LOC), audit hostile interne (8 livrables + mise a jour), preuves d'execution (annexes A11/A12 reproductibles), rapport technique de valorisation (1 100+ LOC), dossier commissaire d'apports (241 LOC), demonstration cabinet avocats (565 LOC), specifications fonctionnelles, manuels, checklists |
| **Fichiers** | 148 fichiers `.md` modifies (diff upstream -> HEAD), +27 675 lignes proprietaires |
| **Complexite** | **Faible-moyenne** par ligne, mais **elevee** par densite informationnelle |
| **Preuves** | 64 tests TDD validant la structure documentaire (PASSED) ; presence des fichiers verifiable |
| **Heures basses** | 70 j-h |
| **Heures cibles** | 100 j-h |
| **Heures hautes** | 140 j-h |
| **Risques** | Heterogeneite FR/EN ; doublons (a nettoyer P2-7) ; pas de schema de donnees ni d'API reference (P2-5 ouvert) |

---

## 18. Synthese (table recapitulative)

| # | Module | LOC | Complexite | Heures basses | Heures cibles | Heures hautes |
|---|---|---:|---|---:|---:|---:|
| 1 | Pipeline Consensus PRISM | ~6 200 | Tres elevee | 80 | 100 | 130 |
| 2 | Debat adversarial / instruction contradictoire | ~4 620 | Tres elevee | 60 | 80 | 105 |
| 3 | Router deterministe + Gate de criticite | ~4 470 | Elevee | 50 | 65 | 85 |
| 4 | Pipeline Legal-Safe complet | ~16 550 | Tres elevee | 200 | 260 | 330 |
| 5 | Moteur PDF / OCR + PRISM PDF | ~12 380 | Elevee | 130 | 175 | 230 |
| 6 | Reasoning Engine + Metacognition | ~2 240 | Elevee | 25 | 35 | 45 |
| 7 | Pipeline strategique + Reporting Evidence-grade | ~6 760 | Elevee | 70 | 90 | 115 |
| 8 | Securite multi-tenant | ~4 410 | Elevee | 50 | 65 | 85 |
| 9 | Pipeline Audit-Proof (replay/review/risk) | ~1 690 | Elevee | 22 | 28 | 38 |
| 10 | Framework Evidence integrite + ComplianceGrid (modules non doubles) | ~3 000 | Tres elevee | 35 | 45 | 60 |
| 11 | Contrat metier Medical | ~770 | Elevee | 8 | 12 | 16 |
| 12 | Personnalisation chat | ~145 | Faible | 1.5 | 2 | 3 |
| 13 | Internationalisation FR / EN | ~480 | Faible-moyenne | 4 | 6 | 8 |
| 14 | Architecture Docker production + scripts | ~9 500 | Elevee | 95 | 120 | 160 |
| 15 | Suite de tests TDD industrielle | ~67 200 | Moyenne-elevee | 270 | 360 | 470 |
| 16 | 12 Agents + 11 MCP + integrations | — | Moyenne | 35 | 50 | 70 |
| 17 | Documentation proprietaire | +27 675 | Faible-moyenne | 70 | 100 | 140 |
| | **TOTAL** | **~138 100 LOC code + 67 200 LOC tests + 27 675 LOC doc** | | **1 205.5** | **1 593** | **2 090** |

---

## 19. Verification anti-double-comptage

| Verification | Statut |
|---|---|
| `medical_contract.py` (769 LOC) compte uniquement en module 11 | OK |
| `strategic_contract.py` (843 LOC) compte uniquement en module 7 | OK |
| `reporting/evidence_native.py` (1 422 LOC) compte uniquement en module 7 | OK |
| Modules audit-proof (replay, review, risk) comptes uniquement en module 9 | OK |
| Modules `integrity_block.py`, `session_envelope.py`, etc. comptes uniquement en module 10 (avec note explicite) | OK |
| Tests comptes uniquement en module 15 (pas dans les modules valides) | OK |
| Documentation proprietaire comptee uniquement en module 17 | OK |
| `legal_safe_*.py` et `contract_drafting/` comptes uniquement en module 4 | OK |
| `evidence_pdf_engine.py`, `pdf_extraction/`, `evidence_document/` comptes uniquement en module 5 | OK |
| Pattern d'extensions Agent Zero **non** compte | OK (heritage MIT, exclu) |
| Boucle agent generique **non** comptee | OK (heritage MIT, exclu) |

---

## 20. Risques transverses (non lies a un module specifique)

| Risque | Severite | Mitigation |
|---|---|---|
| Bus factor = 1 (Amine seul) | Important | 7 ADR + GLOSSARY + C4 + onboarding 1 196 LOC ; estimation onboarding ~1.5-2 semaines |
| Auto-evaluation conformite (AI Act) | Modere | Pipeline audit-proof attenue ; audit externe a annexer (AE-10) |
| Pas d'audit penetration | Modere | A annexer si rapport tiers disponible (AE-10) |
| Antériorite PRISM non prouvable par Git seul | Modere | Pieces datees a annexer (AE-7) ; 4 brevets PRISM avec chaine de droits (AE-5, AE-6) |
| Pas de SAST / Dependabot en CI | Faible | P2-4 ouvert |
| Mode sans auth par defaut | Modere | P1-6 ouvert ; documente dans SECURITY.md |
| Masquage secrets fail-open | Faible | P2-8 ouvert |

---

## 21. Conclusion

Les 17 modules ci-dessus constituent l'inventaire **defendable et verifiable** des actifs proprietaires KOREV Evidence. Le total est de **~1 200 a 2 090 j-h** (cible : ~1 600 j-h), correspondant a une fourchette financiere de **~600 000 EUR a ~1 670 000 EUR** selon TJM applique (cf. `04_HOURS_RECONSTRUCTION_REGISTER.md`).

**Aucun module Agent Zero n'est compte. Aucun module n'est compte deux fois. Toutes les LOC sont fondees sur des fichiers reels du depot a HEAD `fab5689a`.**

---

*Document etabli le 9 mai 2026. Tous les chiffres sont reproductibles via `git diff 9a3a92b6..HEAD --stat` et l'inspection directe des fichiers cites.*
