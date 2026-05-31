<!-- markdownlint-disable MD060 MD032 MD029 MD014 MD013 MD040 MD036 MD034 -->

# Notes d'audit complementaires — KOREV Evidence

Document complementaire a `PROJECT_DOCUMENTATION_STANDARD.md`. Il consigne :

- la methode appliquee ;
- les commandes shell utilisees pour les mesures ;
- les references aux documents internes deja existants dans le repo ;
- les zones non auditees ;
- les recommandations pour un cabinet externe qui souhaiterait approfondir.

---

## 1. Methode

### 1.1 Perimetre

- Branche : `diag-grow/transmission-evidence`.
- HEAD : `641b2c44`.
- Date d'analyse : 20 mai 2026.
- Mode : lecture statique du code et des artefacts documentaires versionnes. Aucune execution runtime, aucun appel reseau.

### 1.2 Principes appliques

- Toute affirmation rattachee soit a un fichier directement lu, soit a une commande shell rejouable.
- En cas d'absence d'information : mention explicite "Non documente dans le perimetre audite" ou "A confirmer avec le porteur".
- Aucune extrapolation produit ni revendication marketing.
- Coexistence dans le document standard de la mention `Constate dans le code`, `Deduit raisonnablement` (implicite par le contexte structurel), et `A confirmer par le porteur du projet` (section 12).

### 1.3 Commandes de mesure utilisees

Volumetrie globale :

```bash
find . -name "*.py" -not -path "./venv/*" -not -path "./node_modules/*" \
  -not -path "./.git/*" -not -path "*/__pycache__/*" | wc -l
# 613 fichiers Python

find . -name "*.py" -not -path "./venv/*" -not -path "./node_modules/*" \
  -not -path "./.git/*" -not -path "*/__pycache__/*" -exec cat {} + | wc -l
# 191 467 lignes Python

find . -name "*.md" -not -path "./venv/*" -not -path "./node_modules/*" \
  -not -path "./.git/*" | wc -l
# 865 fichiers Markdown

find tests -name "test_*.py" | wc -l
# 170 fichiers de tests
```

Inventaire structurel :

```bash
ls agents/          # 12 dossiers (11 profils + _example)
ls python/api/      # 72 endpoints REST
ls python/helpers/  # ~149 modules
ls python/extensions/  # 24 dossiers d'extensions
ls python/security/   # 9 sous-modules securite
ls docs/adr/          # 7 ADR
ls .github/workflows/ # 3 workflows CI
ls mcp_servers/       # 3 serveurs MCP (openalex, pubmed, semanticscholar)
```

Frameworks et dependances :

```bash
head -60 requirements.txt
# Flask 3.0.3, LiteLLM (Dockerfile), LangChain 0.3.49,
# sentence-transformers 3.0.1, faiss-cpu 1.11.0, pydantic 2.11.7,
# MCP 1.13.1, browser-use 0.5.11, playwright 1.52.0, etc.

cat VERSION.json
# {"version": "Evidence v1.3.0", "commit_hash": "d674d01a", ...}
```

Routes Flask :

```bash
grep -rE "@app\.(route|get|post)" run_ui.py python/helpers/health_endpoints.py
# /login, /logout, /healthz, /, /readyz, /metrics
# (autres endpoints enregistres dynamiquement via python/api/)
```

Services Docker :

```bash
grep -E "^  [a-zA-Z]" deploy/docker-compose.yml
# evidence-backend, evidence-backend-demo, evidence-postgres,
# evidence-caddy, evidence-samba, plus volumes persistents
```

---

## 2. Reference aux documents internes deja existants

Le repository contient deja une production documentaire substantielle. Les documents listes ci-dessous sont mentionnes ici en reference pour eviter la duplication.

| Document interne | Localisation | Contenu |
|---|---|---|
| Pack de valorisation Evidence | `docs/valuation/00_*.md` a `13_*.md`, `CONTROLE_AUDIT_PACK_2026-05-09.md` | Pack complet pour Diag & Grow / commissaire aux apports : diagnostic, delta Agent Zero, modules proprietaires, heures de reconstruction, qualite, limites, transmission, audit hostile, audit factuel, readiness report, reserves resolues. |
| Annexe AE-11 (audit licence) | `docs/annexes-externes/AE-11_pip-licenses_2026-05-15.md` + JSON + README | Scan `pip-licenses` complet a J-0 (15 mai 2026), analyse synthetique des familles de licences, verdict 0 GPL/AGPL/SSPL direct. |
| Architecture verifiee de la delegation | `docs/architecture/EVIDENCE_DELEGATION_ARCHITECTURE_VERIFIED.md` | Schema Mermaid de la delegation multi-agents, matrice claim-to-evidence, prompt de controle anti-hallucination. |
| ADR formels | `docs/adr/ADR-001` a `ADR-007` | Decisions d'architecture documentees : consensus PRISM multi-arbitres, router determinste anti-injection, framework Evidence audit-integrite, abstraction LiteLLM, hooks d'extensions, contrat IO integrite outils, adoption Postgres + pgvector. |
| Onboarding | `docs/DEVELOPER_ONBOARDING_ARCHITECTURE_GUIDE.md`, `docs/missions/MISSION_AYA_01_cartographie_et_validation_e2e.md` | Guide d'onboarding architecture + 1re mission. (À confirmer : `docs/ONBOARDING_AYA_30_60_90.md` et `docs/PLAN_INTEGRATION_LEAD_ENGINEER_30_60_90_INTERNAL.md` référencés historiquement mais **absents du dépôt** au 2026-05-31.) |
| Guides operationnels | `docs/GUIDE_DEPLOIEMENT_ENTREPRISE.md`, `docs/MANUEL_INSTALLATION_CLIENT.md`, `docs/GUIDE_RAPIDE_INSTALLATION.md` | Procedures de deploiement et d'installation. (Note : `docs/INFRA_SERVEUR_OVH.md` n'est plus versionne — topologie infra retiree du depot public, conserve en local uniquement.) |
| Runbook | `deploy/RUNBOOK.md` | Procedure operationnelle de production. |
| Audit pre-deploiement | `docs/archive/historical/AUDIT_PRE_DEPLOIEMENT_2026-02-11.md`, `docs/archive/historical/AUDIT_OCR_2026-02-11.md` | Audits internes ponctuels (archives historiques, 2026-02-11). |
| Demonstration cabinet avocats | `docs/DEMONSTRATION_CABINET_AVOCATS.md` + PDF | Plaquette de demonstration metier. |
| Securite | `SECURITY.md` (racine) | Politique de securite. |
| Glossaire | `docs/GLOSSARY.md` | Vocabulaire metier et technique du projet. |
| Profils agents reference | `docs/PROFILS_AGENTS_REFERENCE.md` | Liste de reference des profils agents. |
| Specifications | `docs/SPEC_MULTI_USER_WORKSPACE.md`, `docs/SPEC_CHAT_PERSONALIZATION.md` | Specifications fonctionnelles strictes. |
| Manuels installation | `docs/MANUEL_INSTALLATION_CLIENT.md` | Manuel client. |
| Rapport hardening medical | `docs/MEDICAL_AGENT_HARDENING_REPORT.md` | Rapport de durcissement de l'agent medical. |

---

## 3. Zones non auditees dans la presente mission

Cette liste est explicite afin que toute analyse contradictoire connaisse les angles non couverts.

| Zone | Raison de la non-couverture | Recommandation |
|---|---|---|
| Tests runtime (`pytest`) | Aucune execution dans cette mission. | Lancer `pytest --collect-only -q tests/` puis `pytest -q -m fast tests/` pour mesure de gate ; ensuite `pytest -q tests/`. |
| Couverture de tests (coverage.py) | Pas mesuree. | Lancer `pytest --cov=python --cov=agents --cov-report=term-missing` pour produire un rapport. |
| Performance LLM en debat collaboratif | Pas observe. | Benchmark dedie sur cas reels de chacun des 11 profils. |
| Resilience aux pannes reseau et aux timeouts LLM | Pas observe. | Tests chaos avec timeouts artificiels sur arbitres. |
| Effet runtime du router determinste en enforcement soft (`DETERMINISTIC_ROUTER_V2=2`) | Pas observe. | Activer la variable, executer un cas high-stakes et observer le blocage. |
| Etat reel de la migration Postgres + pgvector | Pas verifie ligne par ligne. | Re-lire `python/helpers/db_connection.py`, `python/helpers/database.py`, et la couche d'embeddings ; verifier presence de schemas pgvector. |
| Audit ligne par ligne des 191 467 lignes Python | Hors perimetre. | Echantillonnage sectoriel par cabinet externe. |
| Volume de code reellement utile vs commentaires / docstrings | Pas separe. | Lancer `cloc --by-file --include-lang=Python` pour scinder code / commentaires / blanc. |
| Logs production reels | Hors perimetre. | Inspection sur l'infrastructure du porteur. |
| Audit reseau et configuration TLS Caddy | Hors perimetre. | Verification de la configuration Caddyfile sur le serveur de deploiement. |
| Configuration newrelic / APM | `newrelic_agent.log` present, configuration non lue. | Verifier `newrelic.ini` ou variables d'environnement. |
| Audit submodules (`mcp_servers/openalex/`, `mcp_servers/semanticscholar/`) | Drives constates dans `git status`. | Pinning explicite et conformite licences. |
| Sandboxing Playwright / browser-use | Surface d'attaque potentielle non mesuree. | Audit dedie sandboxing navigateur. |
| Schemas de donnees Postgres reels | Pas inspectes. | Lecture des migrations + dump du schema en environnement de demo. |
| Volume reel des dossiers `memory/`, `logs/`, `data/`, `tmp/` | Hors perimetre. | Verification a chaud sur infrastructure du porteur. |

---

## 4. Faiblesses methodologiques de la documentation existante

A signaler au porteur pour eventuelle correction documentaire :

| Element | Faiblesse observee | Correction suggeree |
|---|---|---|
| `call_subordinate.py:13` (header docstring) | Annonce "Duree: ~30-40 secondes" alors que le code declare 60 s max (`DebateConfig.total_timeout_ms`). | Mettre a jour le commentaire pour refleter le contrat reel. |
| `routing_contract.py:19-24` vs documentation interne | Les verdicts reels sont `PROCEED` / `NEEDS_CLARIFICATION` / `NO_ROUTE` / `REFUSE`. Plusieurs documents externes mentionnent un verdict `ALLOW` qui n'existe pas. | Aligner toute documentation sur les enums du code. |
| `IntentName.CONTRADICTOR` (`routing_contract.py:37`) | Initialement, cet intent existait dans le router mais aucun dossier `agents/contradictor/` ne lui correspondait. | **RESOLU** (2026-05-27) : profil `agents/contradictor/` cree, module `python/helpers/contradictor/` cree (schema strict, invoker, orchestration, profile_mapping), consommation reelle dans `python/tools/call_subordinate.py` apres consensus, mapping applicatif `"contradictor" -> "contradictor"` (jamais `default`), 19 tests verts (`tests/test_contradictor_agent.py`). Le Contradictor Agent est desormais actif pour les decisions board-level multi-intent et les documents strategiques necessitant une revue contradictoire. Son invocation est conditionnee par `requires_contradictor=True`, validee par schema strict, tracee dans les logs d'audit, et peut declencher une revue humaine en cas de risque high/critical, timeout ou echec de validation. Voir `docs/audits/CONTRADICTOR_AGENT_HOSTILE_AUDIT.md` et `docs/reports/CONTRADICTOR_AGENT_IMPLEMENTATION_REPORT.md`. |
| Mention "PRISM" dans plusieurs docstrings | Le terme est utilise sans definition claire. Il designe collectivement un ecosysteme de modules consensus. | Definir explicitement dans le glossaire (`docs/GLOSSARY.md`) et eviter la confusion entre `collaborative_consensus.py` (legacy) et le pipeline adversarial. |
| Fichiers `test_*.py` a la racine du repo | 4 fichiers de tests hors `tests/`. | Soit deplacer sous `tests/`, soit documenter explicitement leur statut (drafts, prototypes, non integres CI). |
| `newrelic_agent.log` versionne a la racine | Log d'agent New Relic est un artefact runtime, ne devrait pas etre dans le repo. | Ajouter au `.gitignore` et le retirer du suivi. |
| Drives submodules MCP | Etat `m` constant. | Pinner explicitement ou actualiser. |

---

## 5. Recommandations pour un cabinet d'audit externe

Si un cabinet souhaitait approfondir l'audit, l'ordre de priorite suggere serait :

1. **Re-execution complete des tests** : `pytest --collect-only -q` + `pytest -q tests/` + `pytest --cov`. Mesurer la couverture globale.
2. **Audit IP fichier par fichier** : `git diff <fork-base>..HEAD --stat` puis verification echantillonnaire des 30 plus gros fichiers proprietaires.
3. **Audit securite runtime** : penetration test sur l'instance de demo, audit Caddy / TLS, audit Samba multi-tenant.
4. **Audit performance** : benchmark sur les 11 profils agents, mesure des temps de delegation et de consensus.
5. **Audit conformite licence externe** : verification independante du scan AE-11 par un tiers (commande `pip-licenses --output-file ...` sur un environnement reproductible).
6. **Audit reglementaire** : revue par un cabinet juridique de la prise en charge AI Act (categories de risque, marquage CE pour IA haut risque) et RGPD (registre des traitements, base legale, DPIA si applicable).
7. **Audit financier** : compatible avec la lecture du pack `docs/valuation/`.

---

## 6. Donnees manquantes signalees au porteur

Liste a confirmer avec Amine (porteur du projet) avant transmission externe :

- [ ] Valeurs reelles des variables d'environnement en production (`DETERMINISTIC_ROUTER_V2`, `EVIDENCE_MAX_*`, `reasoning_pipeline_enabled`).
- [ ] Confirmation du statut des 4 fichiers `test_*.py` a la racine.
- [ ] Etat reel de la migration Postgres + pgvector (acheve / en cours / planifie).
- [ ] Coverage globale de la suite de tests (et non uniquement `python/security/`).
- [ ] Couverture NDA des mentions clients (DICA, Tarmac, Centrale Lille) dans le pack documentaire.
- [ ] Validite de la configuration newrelic ou de l'APM en production.
- [ ] Date du dernier passage vert des 3 workflows GitHub Actions.
- [ ] Eventuelle certification ISO 27001 / SOC 2 en cours (le code seul ne renseigne pas).
- [ ] Statut de versionnement des `mcp_servers/openalex/` et `mcp_servers/semanticscholar/` (drives constates).

---

*Fin des notes complementaires.*
