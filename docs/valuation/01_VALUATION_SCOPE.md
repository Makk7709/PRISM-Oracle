# 01 — Perimetre de valorisation

**Projet** : KOREV Evidence
**Apporteur / inventeur** : Amine Mohamed
**Destinataire** : cabinet Diag & Grow et / ou commissaire aux apports
**Methode de valorisation principale** : cout de reproduction (norme IVS 210 — Actifs incorporels)
**HEAD analyse** : `fab5689a` (5 mai 2026)
**Date** : 9 mai 2026

---

## 1. Position recommandee

**Phrase de cadrage obligatoire :**

> *"Agent Zero est exclu de la valorisation comme actif proprietaire. La valorisation porte sur l'oeuvre derivee KOREV : couches Evidence, PRISM, auditabilite, replay, risk register, human review, securite, tests, documentation, industrialisation et specialisation metier."*

Cette formulation est defendable par les preuves Git du pack (delta upstream -> HEAD : 920 fichiers, +217 192 / -14 434, soit +202 758 lignes nettes ; 271 commits Amine Mohamed, +225 477 / -18 030, soit +207 447 lignes nettes en cumul auteur).

---

## 2. Inclus dans la valorisation

### 2.1 Couches techniques proprietaires KOREV

| Couche | Fichiers principaux | LOC delta | Source |
|---|---|---:|---|
| Pipeline Consensus PRISM (fail-closed, multi-arbitres, quorum) | `python/consensus/engine.py`, `python/helpers/consensus_*.py` | ~6 200 | Apport A du rapport technique |
| Debat adversarial / Instruction contradictoire | `python/helpers/adversarial_*.py`, `collaborative_consensus.py` | ~4 600 | Apport B |
| Router deterministe + Gate de criticite | `python/helpers/router/`, `criticality_router.py`, `critical_decision_gate.py` | ~4 470 | Apport C |
| Pipeline Legal-Safe complet | `python/helpers/legal_*.py`, `python/helpers/contract_drafting/`, `python/extensions/legal_safe_mode/` | ~16 550 | Apport D |
| Moteur PDF / OCR industriel + PRISM PDF | `python/helpers/pdf_extraction/`, `evidence_pdf_engine.py`, `evidence_document/`, `strategic_charts.py` | ~12 380 | Apport E |
| Reasoning Engine + Metacognition | `python/helpers/reasoning_engine.py`, `metacognition.py` | ~2 240 | Apport F |
| Pipeline strategique + Reporting Evidence-grade | `python/helpers/strategic_*.py`, `python/helpers/reporting/`, `python/extensions/strategic_validation/` | ~6 760 | Apport G |
| Securite multi-tenant | `python/security/` (14 fichiers), `user_manager.py`, `deploy_config.py`, `health_endpoints.py`, `evidence.py` | ~4 410 | Apport H |
| Contrat metier Medical | `python/helpers/medical_contract.py` | ~770 | Apport I |
| Personnalisation Chat (symbiose homme-IA) | `python/helpers/chat_style.py`, `python/extensions/system_prompt/_05_chat_style.py` | ~145 | Apport J |
| Internationalisation FR / EN | `webui/i18n/fr.json`, `webui/i18n/en.json` + UI selecteur | ~480 | Apport K |
| Architecture Docker production + scripts industriels | `deploy/Dockerfile.backend`, `deploy/docker-compose.yml`, `deploy/config/Caddyfile`, `scripts/` | ~9 500 | Apport L |
| Pipeline Audit-Proof (replay, human review, dynamic risk register) | `python/helpers/replay_engine.py`, `human_review.py`, `dynamic_risk_register.py` + extensions + APIs | ~1 690 | Apport P |
| **Sous-total code metier proprietaire** | | **~70 200** | |
| Suite de tests TDD industrielle | `tests/` (~180 fichiers) | ~67 200 | Apport M |
| Documentation proprietaire (delta upstream -> HEAD) | `docs/`, `audit-hostile-valorisation/`, ADR, GLOSSARY, C4, SECURITY.md, benchmark | ~27 700 | Apport O |
| 12 Agents specialises + 11 MCP servers + integrations | `agents/`, `mcp_servers/` (proprietaires), prompts | non quantifie LOC unique | Apport N |
| **Total cumule code proprietaire (sans test/doc)** | | **~70 200** | |
| **Total cumule (code + tests + doc proprietaire)** | | **~165 100** | |

> Les LOC ci-dessus correspondent a l'inventaire detaille du `RAPPORT_TECHNIQUE_VALORISATION_EVIDENCE.md` section 4 (etat audite 17 avril 2026, ~196 460 lignes nettes ; ecart +6 298 lignes au 9 mai inclus dans les fourchettes d'estimation du registre des heures).

### 2.2 Capacites differenciantes

- **Auditabilite native** : Evidence framework, IntegrityBlock (HMAC obligatoire / RSA optionnel), 10 blocs canoniques de rapport, ComplianceGrid (AI Act articles 9, 13, 14, 17 + RGPD article 30).
- **Replay deterministe** : `replay_engine.py` permet de rejouer une session a partir d'un snapshot. Reduit l'objection "auto-evaluation" en permettant a un tiers de verifier l'execution.
- **Human review workflow** : `human_review.py` injecte une revue humaine sur les decisions critiques (approbation, rejet, escalade).
- **Dynamic risk register** : `dynamic_risk_register.py` calcule un score de risque temps reel et trace son evolution dans la session.
- **Multi-tenant isolation** : autorisation par principal/organisation, isolation workspace, validation path/upload/shell.
- **Observabilite structuree** : security audit logging, metriques de routage (divergence_rate, would_block, latency), structured logs.
- **Specialisation metier** : 12 profils d'agents, 11 MCP servers (ArXiv, PubMed, Semantic Scholar, OpenAlex, Crossref, EUR-Lex, Tavily, Brave...), 103 prompts metiers.

---

## 3. Exclus de la valorisation

### 3.1 Base open-source Agent Zero (MIT)

| Element | Volumetrie a l'amorcage (10 jan. 2026) | Statut valorisation |
|---|---:|---|
| Fichiers Python upstream | 210 fichiers, 28 403 lignes | **Exclu** |
| Total fichiers depot upstream | 1 221 fichiers | **Exclu** |
| WebUI upstream (hors vendor) | 182 fichiers, 30 643 lignes | **Exclu** (mais refonte i18n / branding incluse) |
| Documentation upstream | 130 fichiers, 9 426 lignes | **Exclu** |
| Tests upstream | 7 fichiers rudimentaires | **Exclu** |
| Boucle agent generique (`agent.py` upstream) | — | **Exclu de la valeur Evidence** (refonte = valorisable, mais pas la boucle initiale) |
| Pattern d'extensions (hooks ordonnes) | — | **Exclu** (pattern inspire d'Agent Zero, mais hooks specifiques Legal-Safe / Evidence sont inclus) |
| Pattern `python/helpers`, `python/tools` | — | **Exclu** (structure heritee) |

### 3.2 Dependances tierces (pip / npm)

Toutes les dependances declarees dans `requirements.txt`, `pyproject.toml` (s'il existe) et `package.json` des MCP servers sont **exclues de la valorisation proprietaire**. Voir liste detaillee dans `00_REPO_DIAGNOSTIC.md` section 4.

Exemples : `litellm`, `langchain-core/community/graph`, `flask`, `faiss-cpu`, `sentence-transformers`, `playwright`, `openai-whisper`, `argon2-cffi`, `weasyprint`, `cryptography`, `pytesseract`, `kokoro-tts`, etc.

### 3.3 Scaffolding generique et fichiers legacy non utilises

| Element | Statut |
|---|---|
| `instruments/` (heritage Agent Zero) | Non valorise |
| `knowledge/` (structure heritee) | Non valorise |
| `memory/`, `data/`, `tmp/`, `logs/` (donnees runtime, .gitkeep vides ou gitignored) | Non valorise |
| `browser.py` (~336 lignes commentees) | Non valorise (P2-7 a nettoyer) |
| Blocs commentes dans `initialize.py`, `files.py` | Non valorise |
| `DockerfileLocal`, `docker/` (image dev historique Kali) | Non valorise (a archiver si non utilise, P2-7) |
| `__pycache__/`, `venv/`, `.coverage` | Non valorise |
| `KOREV-Evidence.pdf` (4.6 Mo, presentation) | Non valorise comme code (cite comme livrable commercial) |

### 3.4 Code genere ou templates non specifiques

- Templates de prompts agents non encore stabilises ou clairement copies de l'upstream
- Configurations MCP `mcp_config*.json` (chemins absolus machine-specifiques, doublons avec `mcp_config.production.json`)

### 3.5 Elements non prouves (declares non valorisables tant qu'aucune piece n'est annexee)

| Element | Pourquoi non valorisable en l'etat |
|---|---|
| 5 annees de R&D pre-repository | Non demontrable par le seul historique Git du depot. **Necessite pieces datees externes** (carnets, depots anterieurs, exports notes, emails, maquettes, factures outils, attestations, captures de prototypes). |
| Conformite AI Act | Auto-evaluee. Pas d'audit externe. **Necessite audit tiers ou attestation** pour valorisation au-dela du framework de conformite present dans le code. |
| Audit de penetration multi-tenant | Pas realise. **Necessite rapport de pentest** pour valorisation securite plein. |
| 4 brevets PRISM en cours | **Non valorisable comme brevets Evidence** tant que la chaine de droits PRISM -> Evidence n'est pas annexee (cession, licence, apport ou autorisation explicite d'exploitation). |
| Premier client DICA FRANCE (1 500 EUR/mois) | **Non valorisable par multiples de revenus** sans annexe (factures + preuves de paiement). En complement du cout de reproduction, soutient le haut de fourchette du scenario defendable equilibre. |
| Pilotes Centrale Lille / Le Tarmac | **Non valorisables sans annexe** (conventions, emails, attestations). |

---

## 4. A verifier par annexes externes (hors depot Git)

> Ces pieces ne sont pas dans le depot Git et doivent etre fournies separement par l'apporteur a Diag & Grow et au commissaire aux apports.

| # | Annexe | Role dans la valorisation | Statut |
|---|---|---|---|
| AE-1 | Factures DICA FRANCE (1 500 EUR/mois recurrent) | Soutient le haut du scenario equilibre, reduit l'objection "pre-revenue" | A annexer |
| AE-2 | Preuves de paiement DICA FRANCE (releves bancaires anonymises ou attestations) | Confirme l'execution effective du contrat | A annexer |
| AE-3 | Convention / emails / attestation Le Tarmac by inovallee | Soutient le scenario offensif | A annexer |
| AE-4 | Convention / emails / attestation Centrale Lille (Chaire Construction 4.0 / Pr Zoubeir Lafhaj) | Soutient le scenario offensif et l'expertise domaine | A annexer |
| AE-5 | Dossier des 4 brevets PRISM en cours (numeros depot, INPI / EPO, perimetre) | Renforce l'antériorite PRISM ; necessite la chaine de droits PRISM -> Evidence | A annexer |
| AE-6 | Chaine de droits PRISM -> Evidence (cession, licence, apport, attestation inventeur) | Indispensable pour rattacher la valeur PRISM aux modules consensus integres | A annexer |
| AE-7 | Pieces datees de R&D anterieure (carnets, exports notes, emails, prototypes, captures, factures outils, depots anterieurs eventuels) | Soutient l'antériorite des 5 annees de R&D revendiquees | A annexer |
| AE-8 | Echanges clients / prospects (conventions, emails de validation, retours d'usage) | Soutient la traction commerciale et la maturite produit | A annexer |
| AE-9 | Attestation d'inventeur d'Amine Mohamed sur PRISM et Evidence | Verrouille l'identite de l'inventeur | A annexer |
| AE-10 | Eventuels rapports d'audit externes (securite, conformite, accessibilite) | Reduit la decote "auto-evaluation" | Optionnel — a annexer si disponibles |
| AE-11 | Eventuels contrats clients en cours de negociation ou pilotes | Soutient le potentiel revenu | Optionnel — a annexer si disponibles |

**Note importante** : les pieces AE-5, AE-6 et AE-7 sont les plus critiques pour faire passer la valorisation du scenario equilibre (~958-1 054 KEUR) au scenario offensif maitrise (~1 150-1 350 KEUR).

---

## 5. Position recommandee face au commissaire et a Diag & Grow

### 5.1 Cadrage juridique

- **Agent Zero** = fondation open-source MIT. Statut juridique : usage commercial autorise, modification libre, oeuvres derivees proprietaires permises. Aucun obstacle juridique bloquant identifie a ce stade pour valoriser les developpements proprietaires construits sur cette base, sous reserve de conserver les notices tierces (deja en place dans `legal/THIRD_PARTY_NOTICES.txt`).
- **KOREV Evidence** = oeuvre derivee proprietaire. Licence proprietaire KOREV AI declaree dans `LICENSE` racine et `legal/KOREV_LICENSE.txt`.

### 5.2 Cadrage technique

- Agent Zero **a reduit le cout initial d'amorcage** mais **ne fournit ni la specialisation metier, ni le pipeline de preuve, ni les mecanismes de conformite, ni l'architecture d'exploitation** qui fondent la valeur de KOREV Evidence.
- Une substitution de la base d'orchestration (Agent Zero) serait **couteuse mais techniquement possible** (estimation : ~150-300 j-h cf. `04_HOURS_RECONSTRUCTION_REGISTER.md`).
- Une substitution des couches PRISM / Evidence / Legal-Safe / Audit-Proof exigerait de **reconstruire l'essentiel de l'actif proprietaire** (estimation : ~1 100-2 000 j-h cf. registre).

### 5.3 Methode de valorisation recommandee

1. **Methode principale** : cout de reproduction (norme IVS 210), applique au strict diff upstream -> HEAD du depot.
2. **Methodes complementaires** : positionnement de marche (categorie C "infrastructures de decision et de confiance" cf. benchmark comparables) en verification de coherence d'ordre de grandeur uniquement, **non en justification de prime**.
3. **Methode de revenus** : non applicable a date (revenu recurrent < 20 KEUR/an, pas d'historique commercial suffisant pour DCF). DICA FRANCE soutient le haut de fourchette mais **ne fonde pas une approche par multiples**.
4. **Approche brevets** : les 4 brevets PRISM en cours sont presentes **en annexe** au commissaire. Leur valeur s'agregera a Evidence si la chaine de droits PRISM -> Evidence est annexee (AE-5, AE-6).

### 5.4 Fourchettes defendables (synthese — detail dans `04_HOURS_RECONSTRUCTION_REGISTER.md`)

| Scenario | Valeur | Conditions de defense |
|---|---:|---|
| Conservateur audit-proof (repo seul) | **662 000 EUR** a **850 000 EUR** | Bas du cout de reproduction + decote prudence elevee si annexes incompletes |
| Defendable equilibre (recommande) | **958 000 EUR** a **1 054 000 EUR** | Cout median apres decote technique residuelle 12-20% (score 69/100), avec preuves Git, ADR, benchmark, audit hostile, tests. DICA FRANCE en complement supporte le haut. |
| Offensif maitrise (avec annexes) | **1 150 000 EUR** a **1 350 000 EUR** | Necessite : factures DICA + preuves paiement, pieces datees R&D pre-repository, dossier 4 brevets PRISM + chaine de droits, build Docker verifie, confirmations pilotes terrain |

**Strategie recommandee** : presenter le scenario equilibre comme valeur cible et conserver le scenario offensif comme borne haute de negociation. Le dossier ne doit pas demander une prime de marche fondee sur des multiples d'entreprise.

---

## 6. Cadrage methodologique : ce qui ne doit pas etre compte

> Cette section anticipe les attaques d'un evaluateur hostile en explicitant les exclusions methodologiques avant qu'il ne les revendique.

### 6.1 Pas de double comptage

- Les LOC `strategic_contract.py` (843 LOC) sont comptees dans **l'apport G** uniquement, pas dans l'apport I (medical). L'apport I retient seul `medical_contract.py` (~770 LOC).
- Les ADR, glossaire, C4, SECURITY.md, benchmark sont comptes dans **l'apport O (documentation, ~27 700 lignes diff)** et non dupliques dans la couche metier.
- Les tests sont comptes dans **l'apport M** uniquement (~67 200 lignes), meme si ils valident des modules metier.
- Les LOC du WebUI ne sont pas comptees comme "lignes proprietaires creees" : la refonte est valorisee qualitativement (refactoring, i18n, branding) sans ajout net massif (cf. note (1) du rapport technique : -16 fichiers, +607 lignes nettes).

### 6.2 Pas de valorisation d'Agent Zero

- Les 28 403 lignes Python upstream du 10 janvier 2026 ne sont **pas comptees**.
- Les 9 426 lignes de documentation upstream ne sont **pas comptees**.
- La WebUI initiale (30 643 lignes upstream) n'est **pas comptee**.

### 6.3 Pas de valorisation des dependances

- Aucune ligne des packages `requirements.txt` n'est comptee.
- Aucune ligne de code des MCP servers npm tiers n'est comptee.
- Seuls les MCP servers adaptes ou crees par KOREV (OpenAlex / Semantic Scholar / PubMed dans `mcp_servers/`) sont consideres, et uniquement pour le code KOREV ajoute (Dockerfiles, configurations specifiques, integrations).

### 6.4 Pas de valorisation d'elements non prouves

- Les 5 annees de R&D anterieure ne sont valorisees comme actif immateriel **que si** les pieces AE-7 sont annexees.
- Les 4 brevets PRISM ne sont rattaches a Evidence **que si** la chaine de droits AE-5 + AE-6 est annexee.
- DICA FRANCE / Centrale Lille / Le Tarmac ne soutiennent une prime **que si** les pieces AE-1 a AE-4 et AE-8 sont annexees.

### 6.5 Pas de valorisation par multiples d'entreprise

- Le benchmark comparables marche (`docs/BENCHMARK_COMPARABLES_VALORISATION_EVIDENCE.md`) sert **uniquement** a verifier que le cout de reproduction retenu n'est pas excessif. Il **ne fonde pas** une prime de marche fondee sur des multiples.

---

## 7. Synthese : table de decision

| Element | Inclus | Exclu | A annexer | Note |
|---|:---:|:---:|:---:|---|
| Modules consensus PRISM (`python/consensus/`, `consensus_*.py`) | X | | | Apport A |
| Adversarial / collaborative consensus | X | | | Apport B |
| Router deterministe + criticality gate | X | | | Apport C |
| Pipeline Legal-Safe complet | X | | | Apport D |
| Moteur PDF/OCR + Evidence document + Strategic charts | X | | | Apport E |
| Reasoning + Metacognition | X | | | Apport F |
| Pipeline strategique + Reporting Evidence | X | | | Apport G |
| Securite multi-tenant + module security/ | X | | | Apport H |
| Contrat medical | X | | | Apport I |
| Chat personalisation | X | | | Apport J |
| I18N FR/EN | X | | | Apport K |
| Architecture Docker production + scripts industriels | X | | | Apport L |
| Suite de tests TDD (~67 200 LOC) | X | | | Apport M |
| 12 agents specialises + 11 MCP servers (couches KOREV) | X | | | Apport N |
| Documentation proprietaire (148 fichiers diff, +27 675 lignes) | X | | | Apport O |
| Pipeline Audit-Proof (replay, human review, risk register) | X | | | Apport P |
| Boucle agent generique Agent Zero | | X | | Heritage MIT |
| WebUI initiale Agent Zero (30 643 lignes upstream) | | X | | Heritage MIT |
| Documentation upstream (9 426 lignes) | | X | | Heritage MIT |
| Tests upstream (7 fichiers) | | X | | Heritage MIT |
| Pattern `python/helpers`, `python/tools` (structure) | | X | | Heritage MIT |
| Dependances pip / npm | | X | | Tiers |
| `instruments/`, `knowledge/`, `memory/`, `data/` | | X | | Heritage / runtime |
| `browser.py` (336 lignes commentees) | | X | | Code mort (P2-7) |
| `DockerfileLocal`, `docker/` (image dev historique) | | X | | Legacy (P2-7) |
| 5 ans R&D PRISM anterieure | | | X (AE-7) | Necessite annexes datees |
| Conformite AI Act | | | X (AE-10) | Necessite audit externe |
| Audit penetration | | | X (AE-10) | Necessite pentest tiers |
| 4 brevets PRISM en cours | | | X (AE-5, AE-6) | Annexer dossier + chaine de droits |
| DICA FRANCE 1 500 EUR/mois | | | X (AE-1, AE-2) | Annexer factures + paiements |
| Pilotes Centrale Lille / Le Tarmac | | | X (AE-3, AE-4) | Annexer conventions / emails |
| Antériorite PRISM (briques consensus) | X (codee) | | X (AE-5, AE-6 pour droit) | Code dans Evidence ; annexe pour la chaine de droits |

---

## 8. Cadrage final pour Diag & Grow

> Le perimetre valorise est strictement le **diff upstream Agent Zero (`9a3a92b6`, 10 janvier 2026) -> HEAD KOREV Evidence (`fab5689a`, 5 mai 2026)**.
>
> Ce diff est documente fichier par fichier dans `02_AGENT_ZERO_DELTA.md` et `03_EVIDENCE_PROPRIETARY_MODULES.md`. Il est verifiable par toute personne disposant du depot via `git diff 9a3a92b6..HEAD --shortstat`.
>
> La valeur defendable repo seul (sans annexes externes) se situe entre **662 000 EUR** (conservateur) et **1 054 000 EUR** (defendable equilibre).
> Avec les annexes externes AE-1 a AE-9 dument fournies, la valeur defendable peut atteindre **1 350 000 EUR** (offensif maitrise).
>
> La valorisation porte sur l'oeuvre derivee KOREV. Agent Zero est exclu, les dependances sont exclues, les elements non prouves sont exclus tant qu'aucune piece n'est annexee.

---

*Document etabli le 9 mai 2026. Fonde exclusivement sur les preuves du depot et les annexes citees. Les fourchettes de valeur sont coherentes avec le `RAPPORT_TECHNIQUE_VALORISATION_EVIDENCE.md` et le benchmark comparables.*
