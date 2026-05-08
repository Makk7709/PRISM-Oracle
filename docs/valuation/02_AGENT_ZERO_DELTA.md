# 02 — Delta Agent Zero / KOREV Evidence

**Projet** : KOREV Evidence (oeuvre derivee Agent Zero)
**Apporteur / inventeur** : Amine Mohamed
**HEAD analyse** : `fab5689a` (5 mai 2026)
**Reference upstream** : `9a3a92b6` (10 janvier 2026, dernier commit Agent Zero avant le fork)
**Methode** : analyse comparative basee sur le diff Git et la lecture des modules
**Date** : 9 mai 2026

> Ce document est **critique** pour la valorisation. Il distingue precisement ce qui vient d'Agent Zero (open-source MIT, exclu de la valorisation proprietaire) de ce qui a ete cree par KOREV (valorisable). Il anticipe et neutralise l'objection : *"ce n'est qu'un fork Agent Zero"*.

---

## 1. Cadrage : qu'est-ce qu'Agent Zero ?

| Element | Detail |
|---|---|
| Projet | Agent Zero (framework d'agents IA generique) |
| Auteur original | frdel / Jan Tomasek (Republique tcheque) + 33 contributeurs communautaires |
| Licence | MIT (usage commercial autorise, modification libre, oeuvres derivees proprietaires permises) |
| Premier commit | `8cef5e1e` — 10 juin 2024 (52 fichiers, 854 lignes) |
| Dernier commit avant fork KOREV | `9a3a92b6` — 10 janvier 2026 (1 221 fichiers, 28 403 lignes Python) |
| Volume upstream a la date du fork | 1 221 fichiers, 28 403 lignes Python, 130 fichiers `.md` / 9 426 lignes, 7 fichiers de test |
| Site / depot | `frdel/agent-zero` sur GitHub (public) |

### Ce qu'apporte Agent Zero (fondation)

- Un framework d'**agent conversationnel generique** (boucle agent / outil, gestion de modeles, monologue interne).
- Une **WebUI basique** (chat Alpine.js, settings, profile selector, ~30 643 lignes hors vendor).
- Des **outils generiques** (code execution, memoire vectorielle simple, knowledge ingestion, delegation a sous-agents, browser headless).
- Des **helpers Python** (210 fichiers, 28 403 lignes : LLM wrappers, mcp basique, files, persistence, settings).
- Un **Docker de developpement** (DockerfileLocal, image base Kali — non production-ready).
- Une **documentation communautaire** (130 fichiers `.md`, 9 426 lignes, README, architecture, guides).
- **Un pattern d'extensions** (hooks ordonnes par convention `_NN_*` dans `python/extensions/`).
- **Une architecture MCP basique** (`python/helpers/mcp_*` : proxy MCP dynamique).

### Ce que NE fournit pas Agent Zero (lacunes adressees par KOREV)

- Aucun **mecanisme de consensus multi-LLM** (PRISM-style)
- Aucun **debat adversarial / instruction contradictoire**
- Aucun **routeur deterministe** anti-injection
- Aucun **pipeline metier** (juridique, medical, strategique, financier)
- Aucun **moteur PDF / OCR industriel** (timeouts, circuit breakers, fallback)
- Aucun **framework d'audit Evidence** (rapports canoniques, IntegrityBlock, ComplianceGrid)
- Aucun **pipeline de revue humaine ni replay deterministe**
- Aucun **registre de risques dynamique**
- Aucune **architecture multi-tenant** (Argon2id, RBAC, isolation par principal)
- Aucune **architecture Docker production** (Caddy, multi-stage, healthchecks, healthchecks documente)
- Aucune **suite de tests TDD significative** (7 fichiers rudimentaires)
- Aucune **personnalisation chat** (chat_style avec injection system prompt)
- Aucune **internationalisation FR / EN** complete
- Aucune **conformite AI Act / RGPD** native

---

## 2. Volumetrie comparee

### 2.1 Tableau Avant / Apres

| Metrique | Agent Zero upstream (10 jan. 2026) | KOREV Evidence (HEAD `fab5689a`, 5 mai 2026) | Delta |
|---|---:|---:|---:|
| Fichiers Python | 210 | ~606 (volumetrie 28 avr. : 606 / 189 744 LOC) | **+396** |
| Lignes Python | 28 403 | ~189 744 | **+161 341** |
| Fichiers WebUI (hors vendor) | 182 | 166 | -16 (refonte) |
| Lignes WebUI (hors vendor) | 30 643 | 31 250 | +607 |
| Fichiers documentation `.md` | 130 / 9 426 lignes | 246+ / ~38 100 lignes (etat 17 avril) | **+116 / +28 689** |
| Fichiers de test | 7 | ~183 | **+176** |
| Tests collectes (pytest) | 0 (rudimentaires) | **3 956** (verifie 28 avril) | **+3 956** |

### 2.2 Diff Git verifie

```bash
$ git diff 9a3a92b6..HEAD --shortstat
920 files changed, 217192 insertions(+), 14434 deletions(-)
# Net : +202 758 lignes
```

```bash
$ git log --all --author='Amine' --shortstat
271 commits, +225 477 insertions, -18 030 suppressions
# Net cumule auteur : +207 447 lignes
```

L'ecart entre le diff upstream -> HEAD (+202 758 net) et le cumul des commits Amine (+207 447 net) s'explique par les commits qui touchent des fichiers existants plusieurs fois (les insertions / suppressions intermediaires se cumulent dans le cumul auteur mais sont consolidees dans le diff final).

### 2.3 Decomposition par type de fichier (diff upstream -> HEAD)

| Type | Fichiers modifies | Insertions | Suppressions | Net |
|---|---:|---:|---:|---:|
| `.py` Python | 496 | +161 360 | -2 352 | **+159 008** |
| `.md` Markdown | 148 | +27 675 | -1 003 | **+26 672** |
| Autres (.json, .yml, .sh, .html, .js, .css, fonts...) | 276 | +28 157 | -11 079 | +17 078 |
| **Total** | **920** | **+217 192** | **-14 434** | **+202 758** |

Les fichiers `.md` proprietaires representent +26 672 lignes nettes — coherent avec l'apport O du rapport technique (+28 689 lignes a l'etat audite du 17 avril ; -2 017 lignes correspondent au differentiel mineur entre les etats audites).

---

## 3. Tableau analytique par domaine

> Ce tableau est l'element central du document. Il identifie pour chaque domaine fonctionnel ce qu'apporte Agent Zero, ce qu'ajoute KOREV Evidence, les fichiers preuves et la valorisation.

| Domaine | Agent Zero fournit | KOREV Evidence ajoute | Fichiers preuves | Valorisation |
|---|---|---|---|---|
| **Boucle d'orchestration agent** | Boucle `monologue()` generique, gestion outils, budget tokens | Refonte avec garde-fous, integration Evidence (envelopes, audit hooks), gestion fail-closed | `agent.py` (refondu, ~1 144 lignes), `python/extensions/_*` | **Inclus partiellement** : la boucle initiale est exclue (heritage), seules les modifications proprietaires (~30-50% du fichier au prorata du diff) sont valorisees indirectement via les modules consensus / Evidence |
| **Model orchestration** | Wrapper LLM basique | LiteLLM avec retry, streaming controle, browser compat, abstraction multi-LLM | `models.py` (refondu, ~931 lignes), ADR-004 | **Inclus partiellement** : ADR-004 documente le choix LiteLLM, `models.py` est largement refactore |
| **Tools** | code_exec, memory, knowledge, delegation, browser | OCR, PDF, exports strategiques, contract drafting, replay/review APIs | `python/tools/` (~23 modules), `python/api/` (~71 handlers) | **Inclus** pour les nouveaux outils metiers ; **exclu** pour les outils generiques heritage |
| **WebUI** | Chat Alpine.js, settings, profile selector | Refonte branding (Playfair Display, dark/light, welcome screen), i18n FR/EN, scheduler, sub-componentisation | `webui/` (166 fichiers), `webui/i18n/` (FR/EN, ~480 LOC), `webui/index.html` (+1 172 / -6) | **Inclus** : la refonte qualitative est valorisee, pas le volume initial upstream |
| **Memory** | FAISS basique, knowledge ingestion | Reuse de la couche memory upstream | `python/helpers/memory.py`, `python/helpers/knowledge_*.py` | **Exclu** principalement (heritage) sauf adaptations specifiques |
| **Consensus** | Aucun | Pipeline PRISM fail-closed multi-arbitres + adversarial + collaborative | `python/consensus/`, `python/helpers/consensus_*.py`, `adversarial_*.py`, `collaborative_consensus.py` (~10 800 LOC) | **100% INCLUS** — apport A, B (antériorite PRISM) |
| **Audit** | Aucun | Framework Evidence : 10 blocs canoniques, IntegrityBlock HMAC obligatoire + RSA optionnel, ComplianceGrid AI Act/RGPD | `python/helpers/integrity_block.py`, `session_envelope.py`, `evidence.py`, `reporting/evidence_native.py` (1 422 LOC), `reporting/report_*.py`, `evidence_document/` (8 fichiers, 3 472 LOC) | **100% INCLUS** — apports E (PDF Evidence), G (reporting) |
| **Replay** | Aucun | Replay engine deterministe, snapshots, hooks `monologue_end/_35_replay_snapshot.py` | `python/helpers/replay_engine.py` (327 LOC), `python/api/replay.py` (145 LOC), extension snapshot (112 LOC) | **100% INCLUS** — apport P |
| **Human review** | Aucun | Workflow approbation/rejet/escalade, API dediee | `python/helpers/human_review.py` (327 LOC), `python/api/human_review.py` (143 LOC) | **100% INCLUS** — apport P |
| **Risk register** | Aucun | Registre de risques dynamique, scoring temps reel | `python/helpers/dynamic_risk_register.py` (403 LOC), `python/api/risk_dashboard.py` (98 LOC), extension `_36_risk_assessment.py` (137 LOC) | **100% INCLUS** — apport P |
| **Security** | Auth simple basique | Argon2id, rate limiting Redis+memoire, RBAC multi-tenant, path safety, upload validation, shell safety, IP filtering, audit logging | `python/security/` (14 fichiers, ~2 553 LOC), `python/helpers/user_manager.py`, `deploy_config.py`, `health_endpoints.py` | **100% INCLUS** — apport H. SECURITY.md documente les pratiques |
| **Multi-tenant** | Aucun | Isolation par principal/organisation, autorisation par ressource, workspace par tenant | `python/security/authorization.py`, `python/helpers/user_manager.py`, `scripts/provision_*` | **100% INCLUS** — apport H |
| **Legal / compliance** | Aucun | Pipeline Legal-Safe complet : ingestion Legifrance/Judilibre/CNIL, FTS5, citations, contract drafting, Act Leak Guard, conformite AI Act / RGPD | `python/helpers/legal_*.py` (~12 000 LOC), `contract_drafting/` (~2 540 LOC), `python/extensions/legal_safe_mode/` (~1 030 LOC), `python/legal_sources/` | **100% INCLUS** — apport D |
| **Reasoning / metacognition** | Aucun | Reasoning engine baseline tracking, metacognition auto-evaluation, escalade non-diluable | `python/helpers/reasoning_engine.py` (1 190 LOC), `metacognition.py` (1 046 LOC) | **100% INCLUS** — apport F |
| **Reporting** | Aucun | Rapports stratégiques Evidence-grade, generation auto graphiques PRISM, export PDF | `python/helpers/strategic_orchestrator.py`, `strategic_pipeline.py`, `strategic_charts.py` (664 LOC), `reporting/evidence_native.py`, `reporting/report_*.py` | **100% INCLUS** — apport G |
| **Observability** | Logs basiques | Structured logs, security audit log, metriques de routage (divergence_rate, would_block, latency) | `python/observability/`, `python/helpers/router/metrics.py` (316 LOC), `python/security/audit.py` | **100% INCLUS** — apport H et C |
| **Infrastructure (Docker)** | DockerfileLocal dev (Kali base) | Multi-stage production (Python 3.11-slim + Node.js 20), Caddy reverse proxy TLS auto, healthchecks, volumes nommes, non-root user, log rotation | `deploy/Dockerfile.backend` (224 LOC), `deploy/docker-compose.yml` (352 LOC), `deploy/config/Caddyfile` (91 LOC) | **100% INCLUS** — apport L |
| **Tests** | 7 fichiers rudimentaires | 180+ fichiers, 3 956 tests collectes, FakeLLMProvider, FakeMCPHandler, network guard, golden tests OCR / legal, hostile hardening, properties / invariants | `tests/` (180+ fichiers, ~67 200 LOC) | **100% INCLUS** — apport M |
| **Documentation** | 130 fichiers communautaires | 7 ADR, GLOSSARY, ARCHITECTURE C4, SECURITY.md, BENCHMARK comparables, GUIDE_DEPLOIEMENT (1 385 LOC), DEVELOPER_ONBOARDING (1 196 LOC), feuille de route conformite (1 893 LOC), audit hostile interne (8 livrables), preuves d'execution (annexes A11/A12) | `docs/` (75+ fichiers proprietaires), `audit-hostile-valorisation/` (8+1), `docs/preuves-execution/` | **100% INCLUS** — apport O (148 fichiers diff, +27 675 lignes) |
| **MCP integrations** | MCP basique (proxy dynamique, auth token URL) | 11 MCP servers configures (ArXiv, PubMed, Semantic Scholar, OpenAlex, Crossref, EUR-Lex, Tavily, Brave, Playwright, FastA2A, A2A) ; 3 MCP servers locaux avec Dockerfiles propres | `mcp_servers/` (3 servers + Dockerfiles), `mcp_config*.json`, `python/helpers/mcp_*.py` (refondu) | **Inclus partiellement** : la couche basique est heritage, les configurations / specialisations / 3 servers locaux sont KOREV |
| **Routing** | Aucun | Router deterministe v2 hash-based + criticality gate, contrats stricts, anti-injection FR+EN, board-level keywords (40+) | `python/helpers/router/` (~3 100 LOC), `criticality_router.py` (944 LOC), `critical_decision_gate.py` (803 LOC) | **100% INCLUS** — apport C |
| **PDF/OCR** | Aucun | Pipeline avec circuit breakers, timeouts stricts, OCR Tesseract+pdf2image, fallback PyMuPDF/Camelot/Tabula, evidence_pdf_engine WeasyPrint+ReportLab | `python/helpers/pdf_extraction/` (~2 500 LOC), `pdf_generator.py` (926 LOC), `evidence_pdf_engine.py` (1 091 LOC), `evidence_document/` (3 472 LOC), `strategic_charts.py` (664 LOC) | **100% INCLUS** — apport E |

---

## 4. Top 20 fichiers les plus modifies (preuve quantitative)

Source : `docs/preuves-execution/F_decomposition_diff.txt` (capture 28 avril 2026, HEAD `7a7abd6a`).

| # | Insertions | Suppressions | Fichier | Categorie |
|---:|---:|---:|---|---|
| 1 | +2 123 | 0 | `python/helpers/adversarial_instruction.py` | PRISM (anti-injection) — 100% KOREV |
| 2 | +1 960 | 0 | `python/helpers/legal_orchestrator.py` | Legal Pipeline — 100% KOREV |
| 3 | +1 893 | 0 | `docs/FEUILLE_DE_ROUTE_CONFORMITE_FORMAT_EVIDENCE.md` | Conformite — 100% KOREV |
| 4 | +1 835 | 0 | `webui/js/scheduler.js` | WebUI nouveau — 100% KOREV |
| 5 | +1 807 | 0 | `python/helpers/legal_pipeline.py` | Legal Pipeline — 100% KOREV |
| 6 | +1 705 | -209 | `python/helpers/settings.py` | Configuration — refondue largement |
| 7 | +1 560 | 0 | `python/helpers/strategic_orchestrator.py` | Strategic — 100% KOREV |
| 8 | +1 487 | 0 | `tests/golden/pdf_extraction/tables__mixed_content.json` | Golden tests OCR — 100% KOREV |
| 9 | +1 422 | 0 | `python/helpers/reporting/evidence_native.py` | Evidence Reporting — 100% KOREV |
| 10 | +1 385 | 0 | `docs/GUIDE_DEPLOIEMENT_ENTREPRISE.md` | Documentation — 100% KOREV |
| 11 | +1 338 | 0 | `tests/test_legal_pipeline.py` | Tests legal — 100% KOREV |
| 12 | +1 220 | 0 | `tests/golden/pdf_extraction/words__unicode_content.json` | Golden tests OCR — 100% KOREV |
| 13 | +1 217 | 0 | `python/helpers/pdf_extraction/pipeline.py` | OCR Pipeline — 100% KOREV |
| 14 | +1 194 | 0 | `docs/DEVELOPER_ONBOARDING_ARCHITECTURE_GUIDE.md` | Documentation — 100% KOREV |
| 15 | +1 190 | 0 | `python/helpers/reasoning_engine.py` | Reasoning — 100% KOREV |
| 16 | +1 172 | -6 | `webui/index.html` | WebUI — refonte largement |
| 17 | +1 144 | 0 | `python/helpers/adversarial_consensus_integration.py` | PRISM — 100% KOREV |
| 18 | +1 091 | 0 | `python/helpers/evidence_pdf_engine.py` | Evidence PDF — 100% KOREV |
| 19 | +1 088 | 0 | `python/extensions/legal_safe_mode/_10_legal_safe_integration.py` | Legal-Safe — 100% KOREV |
| 20 | +1 077 | 0 | `tests/test_metacognition.py` | Tests metacognition — 100% KOREV |

**Lecture** : 18 des 20 fichiers les plus modifies sont **100% KOREV** (creations proprietaires d'Amine Mohamed). Un (settings.py) est une refonte profonde (+1 705 / -209). Un (webui/index.html) est une refonte UI substantielle (+1 172 / -6). **Aucun de ces 20 fichiers n'existait dans Agent Zero a l'identique au commit `9a3a92b6`**.

Cumul du top 20 : **+28 908 insertions** (~13.6% du diff complet de +213 250 lignes au 24 avril). Le reste (~+184 342 lignes) est reparti sur les ~880 autres fichiers du diff.

---

## 5. Estimation du cout de portage si Agent Zero etait remplace

> Question hostile typique : *"Si Agent Zero disparaissait demain, combien couterait son remplacement ?"*

| Element a remplacer | Effort estime | Justification |
|---|---:|---|
| Boucle d'orchestration agent generique (monologue, tool loop, budget) | 30-60 j-h | Reproduire un equivalent generique demande une expertise solide LLM ; la boucle KOREV est integree dans Evidence donc une partie est deja proprietaire |
| WebUI Alpine.js initiale (chat, settings, profile, panneau) | 25-50 j-h | Frontend simple mais structurant ; plus court avec un framework moderne (React/Vue) |
| Helpers basiques (~28 000 lignes upstream : files, persistence, mcp basique, settings...) | 60-120 j-h | Reproduire les utilitaires de base (LLM wrapper, mcp proxy, settings registry) |
| Pattern d'extensions (hooks ordonnes) | 5-10 j-h | Pattern simple a reimplementer |
| Documentation upstream | 5-10 j-h | Documentation communautaire reproduisable rapidement |
| **Total cout de portage Agent Zero** | **~125-250 j-h** | **~1.5 a 3 mois pour une equipe de 2 developpeurs senior** |

A un TJM moyen de 650 EUR (cf. `04_HOURS_RECONSTRUCTION_REGISTER.md`), le cout de portage Agent Zero est estime a **~80 000 EUR a 165 000 EUR**.

**Conclusion** : Agent Zero est une fondation **substituable**. Sa disparition impose un cout reel mais **ne remet pas en cause la valeur de l'oeuvre derivee KOREV** qui represente l'essentiel de l'effort consenti (~1 100-2 000 j-h pour la couche proprietaire).

---

## 6. Risques de decote lies a la base Agent Zero

| Risque | Severite | Decote estimee | Reponse defendable |
|---|---|---|---|
| "Ce n'est qu'un fork" | Important | 5-10% | Le delta proprietaire (920 fichiers / +217 192 lignes) est largement superieur a la base upstream (1 221 fichiers / 28 403 lignes). Le top 20 fichiers les plus modifies est 100% KOREV |
| "Vous n'avez pas le droit de valoriser" | Faible (juridique) | 0-5% si annexe juridique fournie | MIT autorise explicitement la creation d'oeuvres derivees proprietaires. Notice tierce conservee dans `legal/THIRD_PARTY_NOTICES.txt`. Ce risque est neutralise |
| "Si Agent Zero arrete, vous etes bloques" | Modere | 2-5% | Le cout de portage est ~125-250 j-h. Agent Zero est une fondation substituable. Les couches metier ne dependent pas du framework |
| "Vos modules consensus sont copies d'Agent Zero" | Important si revendiquee | 0% | Faux. Les modules consensus sont **100% KOREV** (apport A, B). Le diff Git le prouve fichier par fichier |
| "Vous gonflez votre delta avec du code copie" | Important | 0% | Le diff `git diff 9a3a92b6..HEAD` est par definition exclusivement le travail post-fork. Aucune ligne d'Agent Zero n'est valorisee |

---

## 7. Reponse a l'objection finale : "ce n'est qu'un fork Agent Zero"

### 7.1 Reponse factuelle

1. Agent Zero a contribue **28 403 lignes Python** au depot (+9 426 lignes documentation + ~30 643 lignes WebUI).
2. KOREV Evidence ajoute **+161 360 lignes Python proprietaires** (5.7x le volume upstream), +27 675 lignes documentation proprietaires, +67 200 lignes de tests.
3. La **part proprietaire represente 85% du code Python actuel** (158 462 / 186 865 lignes a l'etat 17 avril). En diff strict upstream -> HEAD, **~75% du depot final est proprietaire**.
4. Les **modules de valeur** (consensus PRISM, framework Evidence, pipeline Legal-Safe, audit-proof, securite multi-tenant) sont **100% KOREV** : aucun de ces modules n'existe dans Agent Zero.

### 7.2 Reponse comparative

L'argument "ce n'est qu'un fork" appliquerait, par symetrie :
- Red Hat Enterprise Linux est "qu'un fork de Linux" (open-source GPL).
- Databricks est "qu'un wrapper autour d'Apache Spark" (open-source Apache 2.0).
- GitHub Enterprise est "qu'un wrapper autour de Git" (open-source GPL).

Ces argumentations sont rejetees par tous les comites d'evaluation serieux : la valeur d'une plateforme commerciale construite sur une fondation open-source reside dans **la specialisation, l'integration, la securisation, l'industrialisation et la conformite** apportees au-dessus de la base. C'est exactement le periimetre de KOREV Evidence par rapport a Agent Zero.

### 7.3 Reponse mesurable

| Critere | Agent Zero (10 jan. 2026) | KOREV Evidence (5 mai 2026) | Multiplicateur |
|---|---:|---:|---:|
| Lignes Python | 28 403 | ~189 744 | **6.7x** |
| Tests collectes | 0 | 3 956 | **infini** |
| MCP servers integres | basique generique | 11 configures + 3 dockerises | — |
| Modules safety-critical | 0 | ~10 (consensus, adversarial, legal, audit-proof, criticality gate) | — |
| Profils metiers | 1 (default) | 12 specialises | **12x** |
| Documentation `.md` | 130 fichiers / 9 426 lignes | 246+ / ~38 100 lignes | **4x** |
| Pipeline production | DockerfileLocal dev | Docker production multi-stage + Caddy + healthchecks + scripts | — |
| Conformite | Aucune | AI Act + RGPD framework + audit-proof | — |

---

## 8. Synthese : ce qui doit etre exclu vs inclus

### 8.1 EXCLU de la valorisation (Agent Zero)

- Boucle agent generique au sens upstream (`agent.py` initial, ~700 lignes upstream avant refonte)
- WebUI initiale Alpine.js (sans branding KOREV, sans i18n)
- Pattern d'extensions (hooks ordonnes par convention)
- Pattern `python/helpers`, `python/tools`, `python/api`
- Memory FAISS basique upstream
- Knowledge ingestion basique upstream
- DockerfileLocal historique (image dev Kali)
- Documentation upstream (`docs/architecture.md`, `docs/troubleshooting.md` heritage, etc.)
- Profil agent `default` initial
- 7 fichiers de test rudimentaires upstream

### 8.2 INCLUS dans la valorisation (KOREV Evidence)

- Tous les apports A a P du `RAPPORT_TECHNIQUE_VALORISATION_EVIDENCE.md` (cf. tableau de la section 3 ci-dessus et `03_EVIDENCE_PROPRIETARY_MODULES.md`).
- L'integralite du diff `git diff 9a3a92b6..HEAD` (920 fichiers, +217 192 / -14 434, net +202 758 lignes) **moins** :
  - les modifications mineures et ponctuelles dans des fichiers qui restent fondamentalement upstream (a juger au cas par cas si necessaire),
  - les modifications dans `instruments/`, `knowledge/`, `memory/`, `data/` (donnees et exemples).

### 8.3 Verification automatique disponible

Pour verifier la separation upstream / proprietaire, executer :

```bash
# 1. Volume diff total
git diff 9a3a92b6..HEAD --shortstat
# Resultat attendu : ~920 files, ~+217 192 / ~-14 434

# 2. Top fichiers proprietaires
git diff 9a3a92b6..HEAD --numstat | sort -k1 -n -r | head -20

# 3. Verifier qu'un fichier specifique n'existe pas dans upstream
git show 9a3a92b6:python/helpers/legal_orchestrator.py 2>&1
# Resultat attendu : "fatal: path 'python/helpers/legal_orchestrator.py' does not exist in '9a3a92b6'"

# 4. Idem pour les modules audit-proof
git show 9a3a92b6:python/helpers/replay_engine.py 2>&1
git show 9a3a92b6:python/helpers/human_review.py 2>&1
git show 9a3a92b6:python/helpers/dynamic_risk_register.py 2>&1
# Resultat attendu : 3 erreurs "does not exist"
```

---

## 9. Conclusion

La distinction Agent Zero / KOREV Evidence est **claire**, **documentee** et **verifiable par diff Git**. La valeur defendable porte exclusivement sur l'oeuvre derivee KOREV.

**A annexer pour neutralite juridique totale** :

- Texte de la licence MIT d'Agent Zero (deja dans `legal/THIRD_PARTY_NOTICES.txt`).
- Capture du dernier commit upstream `9a3a92b6` avec son etat (1 221 fichiers, 28 403 lignes Python).
- Captures `git diff 9a3a92b6..HEAD --shortstat` et `git log --all --author='Amine' --shortstat` regenerees a la date de transmission.

**Reponse aux objections hostiles :** anticipee dans le pack (sections 7.1 a 7.3 ci-dessus). En particulier, l'argument "ce n'est qu'un fork" est neutralise par : (a) le multiplicateur 6.7x sur le code Python, (b) le fait que les modules de valeur sont 100% KOREV, (c) l'analogie comparative (Red Hat / Linux, Databricks / Spark).

---

*Document etabli le 9 mai 2026. Toutes les metriques Git sont reproductibles via les commandes indiquees. Le diff fichier par fichier est disponible via `git diff 9a3a92b6..HEAD --stat > delta_files.txt`.*
