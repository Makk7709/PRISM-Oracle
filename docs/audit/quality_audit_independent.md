# Audit qualité indépendant (type Sonar) — KOREV Oracle

> Second avis indépendant produit par analyse statique outillée + revue sémantique.
> Complémentaire au scan SonarQube du cabinet de valorisation, pas un remplacement.
> Date : 2026-06-06. Périmètre : code applicatif (`python/`, `agent.py`, `models.py`).
> Exclus : `venv/`, `mcp_servers/` (tiers), `node_modules/`, `tmp/`, `tests/` (sauf F-rules).

## Outils exécutés

| Outil | Version | Dimension | Équivalent Sonar |
|---|---|---|---|
| ruff | 0.15.16 | Bugs / smells / imports | code smells, bugs |
| bandit | 1.9.4 | SAST sécurité Python | security hotspots |
| semgrep | 1.165 (p/python + p/security-audit) | SAST sémantique | vulnerabilities |
| radon | 6.0.1 | Complexité (CC) + maintenabilité (MI) | S3776 cognitive complexity |
| vulture | 2.16 | Code mort | dead code |
| pip-audit | 2.10 | CVE dépendances | **non couvert par Sonar Community** |

## Tableau de bord (chiffres bruts)

| Dimension | Total | Critique | À noter |
|---|---:|---:|---|
| ruff | 1396 | 1 (F821) | F401 imports inutilisés ×1065, F541 ×147, E722 bare-except ×19 |
| bandit | 142 | 4 HIGH | 13 MEDIUM, 125 LOW |
| semgrep | 7 | 1 ERROR | 6 WARNING |
| radon CC (rang ≥ C) | 232 | 8 rang F | 9 rang E, 44 rang D |
| radon MI (rang ≠ A) | 7 fichiers | 1 (MI=0) | `task_scheduler.py` |
| vulture (conf ≥ 80) | 56 | — | 42 imports, 12 variables |
| **pip-audit (CVE)** | **138** | — | **45 paquets vulnérables** |

## Sécurité — verdict sémantique finding par finding

Bandit/semgrep signalent des *patterns* ; voici le tri vrai-risque / faux-positif après lecture du code.

| # | Finding | Emplacement | Verdict | Action |
|---|---|---|---|---|
| S-1 | MD5 (B324) | `knowledge_import.py:26` | **FAUX POSITIF** — checksum de détection de changement, non cryptographique | `usedforsecurity=False` (silence + intention) |
| S-2 | MD5 (B324) | `router/routing_contract.py:300` | **FAUX POSITIF** — hash stable d'ID de contrat | `usedforsecurity=False` |
| S-3 | MD5 (B324) | `strategic_charts.py:586` | **FAUX POSITIF** — hash de nom de fichier de graphique | `usedforsecurity=False` |
| S-4 | Paramiko `AutoAddPolicy` (B507) | `shell_ssh.py:25` | **RÉEL (by-design)** — auto-trust hôte inconnu → MITM au 1ᵉʳ connect | décision : `RejectPolicy` + known_hosts, ou documenter le risque assumé |
| S-5 | SQLi (B608) | `legal_sources/indexing.py:458` | **FAUX POSITIF** — placeholders `?` paramétrés, valeurs liées (`chunk_ids`) | aucune (pattern sûr) |
| S-6 | `os.execv` args tainted (semgrep ERROR) | `process.py:32` | **FAUX POSITIF** — self-restart avec `sys.argv` propre (pas d'entrée externe) | aucune / `# nosemgrep` documenté |
| S-7 | Logger credential disclosure | `critical_output.py:483` | **FAUX POSITIF** — log "secret absent" (fail-soft), ne logge PAS le secret | aucune |
| S-8 | File perms `0o700` | `files.py:347,350` | **FAUX POSITIF** — `0o700` = owner-only (c'est justement le *durcissement* A1) | aucune (règle semgrep trop stricte) |
| S-9 | `requests` sans timeout (B113) | `api/tunnel_proxy.py:22,31` | **RÉEL (mineur)** — risque de blocage indéfini | ajouter `timeout=` |

**Bilan sécurité applicative** : 0 vulnérabilité exploitable confirmée. 4 HIGH bandit = 3 MD5 non-crypto (faux positifs, fix cosmétique 1 ligne) + 1 Paramiko (risque by-design à arbitrer). 1 vrai défaut mineur (timeout HTTP).

## Risque réel n°1 — Dépendances vulnérables (CVE)

C'est l'axe le plus actionnable et **non couvert par SonarQube Community**. 138 CVE/avis sur 45 paquets. Prioriser :

| Paquet | Version | CVE | Fix |
|---|---|---:|---|
| aiohttp | 3.13.3 | 12 | 3.14.0 |
| authlib | 1.6.6 | 6 | 1.6.12 |
| cryptography | 46.0.3 | 5 | 46.0.7 |
| fastmcp | 2.3.4 | 6 | 3.2.0 |
| gitpython | 3.1.43 | 4 | 3.1.50 |
| flask | 3.0.3 | 1 | 3.1.3 |
| langchain-core | 0.3.49 | 2 | 0.3.81 |

> Attention : certains bumps (langchain, fastmcp) sont des montées majeures → tester. Détail complet : `tmp/audit/pipaudit.json`.

### Remédiation CVE — état

> Note d'exactitude : le scan `pipaudit.json` a été capturé alors que `pypdf` avait été
> temporairement rétrogradé à 4.3.1 par l'install de semgrep (22 CVE). `pypdf` a été
> rétabli à `6.0.0` (pin d'origine) → ces 22 CVE sont déjà fermées. Baseline réelle ≈ 116.

**Batch 1 (FAIT)** — fix minimal same-major, 0 conflit runtime (validé) :

| Paquet | Avant → Après | CVE fermées |
|---|---|---:|
| aiohttp | 3.13.3 → 3.14.0 | 12 |
| nltk | 3.9.2 → 3.9.4 | 7 |
| pillow | 12.1.0 → 12.2.0 | 6 |
| authlib | 1.6.6 → 1.6.12 | 6 |
| cryptography | 46.0.3 → 46.0.7 | 5 |
| pyjwt | 2.12.1 → 2.13.0 | 4 (validation JWT) |
| gitpython | 3.1.43 → 3.1.50 | 4 |
| urllib3 | 2.6.3 → 2.7.0 | 2 |
| requests | 2.32.5 → 2.33.0 | 1 |
| idna | 3.11 → 3.15 | 1 |
| simpleeval | 1.0.3 → 1.0.5 | 1 |
| pypdf | (4.3.1→) 6.0.0 | 22 (rétabli) |

Total batch 1 + pypdf ≈ **71 CVE fermées**. Figé dans `requirements.txt` (pins directs + section
sécurité pour les transitifs). Conflits pip résiduels = cosmétiques (`arxiv` orphelin non importé,
`semgrep`/`browser-use`/`mcp-server-fetch` = outils dev / sous-modules tiers).

**Preuve de non-régression** : suite `run_tests.sh local` rejouée → **3426 passés** (identique au
baseline), **84 échecs tous dans des suites environnementales** (PDF/OCR/Docker/rebrand ; filtre
hors-environnement = vide). Tests crypto/RSA 63/63, consensus 44/44, gate/router OK. Le delta
82→84 = `test_dockerfile_backend_ocr` (daemon Docker arrêté sur la machine d'audit), pas une
régression de dépendance.

**Différé (bumps MAJEURS — intégration/tests dédiés requis avant prod)** :
`fastmcp` 2.3→3.2, `langchain-core` 0.3→1.x, `starlette` 0.52→1.0, `transformers` 4.57→5.0rc,
`pyopenssl` 25→26, `twisted` 25→26, `lxml` 5→6, `flask` 3.0→3.1 (compat werkzeug 3.1), `litellm`,
`langsmith`, `protobuf`. À traiter dans une fenêtre dédiée avec rebuild Docker + smoke prod.

**Sans correctif disponible (à surveiller)** : `torch`, `paramiko`, `markdown`, `diskcache`.

> ⚠️ Toute modif de `requirements.txt` impose un **rebuild Docker + smoke test staging** avant
> déploiement prod (le venv local ne valide pas la chaîne PDF/OCR/Docker).

## Maintenabilité / complexité (= Sonar S3776)

8 fonctions en **rang F** (CC > 40), à refactorer en priorité :

| CC | Fonction | Fichier |
|---:|---|---|
| 55 | `decide_route` | `router/router.py:85` |
| 49 | `execute` | `tools/call_subordinate.py:92` |
| 49 | `monologue_start` | `extensions/legal_safe_mode/_10_legal_safe_integration.py:583` |
| 48 | `parse` | `pdf_generator.py:451` |
| 46 | `get_file_info` | `api/file_info.py:33` |
| 44 | `file_tree` | `helpers/file_tree.py:25` |
| 43 | `judge_legal_draft` | `legal_pipeline.py:639` |
| 42 | `build_legal_output` | `legal_pipeline.py:1563` |

Fichier le moins maintenable : `task_scheduler.py` (MI = 0.0).

## Hygiène (volume, faible risque)

- **ruff F401** (1065 imports inutilisés) : gros volume mais quasi tous auto-corrigeables (`ruff --fix`), à faire par batch audité comme S1481.
- **ruff F541** (147 f-strings sans placeholder) : auto-corrigeable.
- **ruff E722 / bandit B110-B112** (bare `except` / `except: pass`) : ~99 occurrences — masquent potentiellement des erreurs ; à revoir au cas par cas.
- **F811** (14 redéfinitions) : 2 candidats réels en prod (`api/ctx_window_get.py:16`, `helpers/api.py:74,77`).

## Reproductibilité

Tous les rapports bruts sont dans `tmp/audit/` : `ruff_repocfg.txt`, `bandit.json`, `semgrep.json`,
`radon_cc.json`, `radon_mi.json`, `vulture.txt`, `pipaudit.json`.

## Ce que cet audit fait / ne fait pas vs Sonar

- **Mieux que Sonar** : tri sémantique vrai-risque/faux-positif (6 des 7 findings sécurité critiques = faux positifs justifiés), + scan CVE des dépendances.
- **Comme Sonar** : couverture déterministe via outils (ruff/bandit/semgrep/radon/vulture).
- **Pas garanti** : reproductibilité bit-à-bit du Quality Gate propriétaire Sonar ; exhaustivité par lecture humaine seule sur tout le repo.
