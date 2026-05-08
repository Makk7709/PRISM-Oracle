# 03 — Audit Qualite Hostile

**Projet** : KOREV Evidence  
**Date** : 3 avril 2026 (mise a jour : 17 avril 2026)  
**Methode** : lecture seule, aucune modification de code  
**Convention** : CRITIQUE > ELEVEE > MOYENNE > FAIBLE  
**Note** : Les items marques ✅ CORRIGE ont ete remedies entre le 3 et le 8 avril 2026

---

## A. Architecture et robustesse

### A-1 | ELEVEE — Modules monolithiques a fort couplage

**Description** : `settings.py` (2 225 lignes), `agent.py` (1 145 lignes), `legal_orchestrator.py` (1 961 lignes) concentrent trop de responsabilites. `Agent.monologue()` a une complexite cyclomatique estimee a 25-40. `settings.py` importe `models` au niveau module, creant un couplage bidirectionnel.

**Pourquoi c'est problematique** : Un nouveau developpeur ne peut pas comprendre le systeme sans maitriser ces modules. Toute modification a un risque de regression eleve. Le merge conflict est frequemment probable.

**Impact valorisation** : Un cabinet hostile identifiera immediatement le risque de "key person dependency" et le cout de maintenance. Decote estimee : -5 a -10% sur la valorisation technique.

**Recommandation** : Scinder `settings.py` en domaines (auth, models, consensus, legal, ui). Extraire la boucle de `monologue()` en sous-fonctions testables independamment.

---

### A-2 | ELEVEE — Duplications conceptuelles dans le consensus

**Description** : Deux classes `ArbiterConfig` existent (`consensus_arbiter.py` et `consensus_integration.py`) avec des champs differents. Trois chemins de code pour le consensus : `engine.py`, `consensus_integration.py` (avec `ResearchPipeline`), et `consensus_arbiter.py` (avec `ArbiterCaller`).

**Pourquoi c'est problematique** : Un audit technique externe demandera "quel est le chemin de consensus actif en production ?". La reponse n'est pas triviale. Risque de divergence silencieuse entre les chemins.

**Impact valorisation** : Reduit la credibilite de l'IP PRISM. L'evaluateur percevra un prototype multi-iterations plutot qu'une architecture unifiee.

**Recommandation** : Unifier les chemins en un seul, deprecier explicitement les alternatives, documenter le flux actif.

---

### A-3 | MOYENNE — `python/helpers/` est un fourre-tout

**Description** : 177 fichiers, ~75 000 lignes sans sous-structure systematique. Melange de domaines : securite, persistence, reporting, legal, consensus, PDF, MCP, memoire, parametrage.

**Pourquoi c'est problematique** : Pas de frontiere de module claire. Un import peut tirer une chaine de dependances inattendue.

**Impact valorisation** : Donne l'impression d'une evolution organique non planifiee. Un CTO externe mettra 2-3 semaines a se reperer.

**Recommandation** : Reorganiser en sous-packages thematiques avec `__init__.py` explicites.

---

### A-4 | MOYENNE — Dual Docker non reconcilie

**Description** : `deploy/Dockerfile.backend` (prod, slim) vs `DockerfileLocal` + `docker/` (dev, base Kali avec SearXNG, SSH, supervisord). Deux histoires de build coexistent.

**Pourquoi c'est problematique** : Confusion sur "quelle image est en production". Le `docker/` semble un vestige du fork initial non nettoye.

**Impact valorisation** : Un auditeur demandera si l'image de production est celle de `deploy/` et devra verifier. Le vestige `docker/` cree un doute sur la maitrise du build.

**Recommandation** : Archiver ou supprimer `docker/` et `DockerfileLocal` si non utilises en production.

---

## B. Securite

### B-1 | ~~CRITIQUE~~ ✅ CORRIGE — Cle HMAC par defaut codee en dur

**Description** : `python/helpers/integrity_block.py` contenait `b"evidence-dev-hmac-key-not-for-production"` comme fallback.

**Statut** : **CORRIGE** (commit `40808223`, 3 avril 2026). `_get_hmac_key()` leve desormais `RuntimeError` si `EVIDENCE_HMAC_KEY` est absent. Documente dans `.env.example`.

~~**Recommandation** : Supprimer le fallback. Faire echouer le demarrage si `EVIDENCE_HMAC_KEY` est absent en production.~~

---

### B-2 | ~~CRITIQUE~~ ✅ CORRIGE — Incoherence de licence (MIT badge vs proprietaire)

**Description** : `README.md` affichait un badge MIT alors que `LICENSE` declarait un logiciel proprietaire.

**Statut** : **CORRIGE** (commit `40808223`, 3 avril 2026). Badge desormais "License-Proprietary". Fichiers `LICENSE` et `legal/KOREV_LICENSE.txt` coherents. Notice MIT tiers dans `legal/THIRD_PARTY_NOTICES.txt`.

~~**Recommandation** : Corriger le badge README immediatement.~~

---

### B-3 | ELEVEE — Mode sans authentification par defaut

**Description** : Quand `AUTH_LOGIN` n'est pas defini et aucun `users.json` n'existe, `requires_auth()` dans `run_ui.py` autorise l'acces sans login. Toute personne sur le reseau peut utiliser l'application.

**Pourquoi c'est problematique** : En deploiement rapide ou par erreur de configuration, l'application est ouverte. Les outils agent (execution de code, acces fichiers) deviennent accessibles a tous.

**Impact valorisation** : Un auditeur securite qualifiera cela de "secure by opt-in, not by default" — contraire aux bonnes pratiques.

**Recommandation** : Exiger une authentification par defaut. Si aucune config n'est fournie, refuser le demarrage ou limiter a localhost.

---

### B-4 | ~~ELEVEE~~ ✅ CORRIGE — Mot de passe en clair dans les logs de migration

**Description** : `run_ui.py` affichait le mot de passe en clair dans les logs de migration.

**Statut** : **CORRIGE** (commit `40808223`, 3 avril 2026). Le message utilise desormais un placeholder generique `'YOUR_PASSWORD'`, pas la valeur reelle.

~~**Recommandation** : Ne jamais inclure le mot de passe en clair dans un message de log.~~

---

### B-5 | ~~ELEVEE~~ ✅ CORRIGE — RBAC audit_reports incoherent

**Description** : `python/api/audit_reports.py` declarait `requires_admin() -> True` bloquant l'acces DPO/RSSI.

**Statut** : **CORRIGE** (commit `40808223`, 3 avril 2026). `requires_admin` retourne desormais `False`. L'acces passe par `can_access_audit_reports(principal, target_org=org)` — conforme a la politique documentee.

~~**Recommandation** : Aligner le handler sur la politique d'autorisation fine.~~

---

### B-6 | MOYENNE — Comparaison de cle API non constante

**Description** : `run_ui.py` (~506-512) compare la cle API avec `!=` au lieu de `hmac.compare_digest`.

**Impact valorisation** : Faible en pratique mais signale un manque de rigueur cryptographique.

---

### B-7 | MOYENNE — Extensions de masquage qui echouent silencieusement

**Description** : `response_stream_chunk/_10_mask_stream.py` et `reasoning_stream_chunk/_10_mask_stream.py` utilisent `except Exception: pass` sur l'echec de masquage de secrets.

**Pourquoi c'est problematique** : Si le masquage echoue, les secrets sont transmis en clair a l'utilisateur/au LLM sans aucune alerte.

**Impact valorisation** : Contredit le narratif de gestion securisee des secrets.

**Recommandation** : Logger l'erreur et bloquer la transmission en cas d'echec du masquage (fail-closed).

---

### B-8 | MOYENNE — Browser agent avec `disable_security=True`

**Description** : `python/tools/browser_agent.py` configure le navigateur avec `disable_security=True` et `allowed_domains=["*"]`.

**Pourquoi c'est problematique** : Toute la surface web est accessible sans restriction. En cas de compromission de prompt, le navigateur est un vecteur d'exfiltration.

**Recommandation** : Documenter le risque accepte ou restreindre les domaines par profil.

---

## C. Qualite de code

### C-1 | ~~ELEVEE~~ ✅ PARTIELLEMENT CORRIGE — `asyncio.run()` dans un event loop existant

**Description** : `agent.py` appelait `asyncio.run()` dans un contexte potentiellement async.

**Statut** : Le crash `asyncio.run()` dans `SchedulerTaskList.get()` a ete corrige (commit `ec1de215`, 4 avril 2026). Le pattern dans `agent.py` subsiste mais n'a pas ete signale comme source de crash en production.

**Recommandation residuelle** : Migrer progressivement les appels restants vers un pattern async-safe.

---

### C-2 | MOYENNE — Code mort et blocs commentes

**Description** : `initialize.py` (~20 lignes commentees pour MCP), `files.py` (~50 lignes importlib), `agent.py` (execution guard desactivee), `browser.py` (entierement commente — 336 lignes mortes).

**Impact valorisation** : Signale du code exploratoire non nettoye. Un auditeur questionnera "pourquoi c'est la si c'est mort ?".

---

### C-3 | MOYENNE — Etat global mutable

**Description** : `AgentContext._contexts` (dict global), `Memory.index` (cache global), dicts de rate limiter. L'isolation multi-tenant repose sur des conventions (sous-dossiers) non verifiees statiquement.

**Pourquoi c'est problematique** : Race conditions potentielles sous charge. Pas de preuve formelle d'isolation.

---

### C-4 | MOYENNE — Inconstance stylistique

**Description** : Bannieres françaises + docstrings anglaises. Emojis dans certains logs. Nommage variable (snake_case majoritaire, mais `LoopData`, `AgentConfig` en PascalCase — normal pour les classes). Imports dupliques (`dirty_json` importe deux fois dans `models.py`).

**Impact valorisation** : Donne une impression de code multi-auteur non uniforme — meme si c'est principalement mono-auteur.

---

### C-5 | FAIBLE — Tables de mots-cles hardcodees

**Description** : `router/policy.py` contient de grandes tables de mots-cles pour la classification des intentions. La calibration est implicite, avec des TODOs sur la criticite du profil `RESEARCHER`.

**Recommandation** : Externaliser dans un fichier de configuration versionne et teste.

---

## D. Tests

### D-1 | ELEVEE — Suite etendue non-bloquante en CI

**Description** : Le job `extended-tests` dans `main_gate.yml` a `continue-on-error: true`. Seuls `smoke-test`, `security-gate`, `redis-multi-worker` et `core-tests` sont bloquants.

**Pourquoi c'est problematique** : Des regressions dans la majorite des tests passent silencieusement en CI.

**Impact valorisation** : Un auditeur QA dira "vos tests ne protegent pas votre main branch".

**Recommandation** : Rendre la suite etendue bloquante ou expliquer formellement les exclusions.

---

### D-2 | MOYENNE — Couverture globale non mesuree

**Description** : Seuls `rate_limit` + `ip` ont un seuil (`--cov-fail-under=90`). Pas de mesure globale. Le README et CI mentionnent 95% mais le seuil reel est 90%.

**Impact valorisation** : Impossible de prouver la couverture a un tiers.

**Recommandation** : Activer la mesure de couverture globale, meme sans seuil bloquant, pour produire un rapport.

---

### D-3 | MOYENNE — Endpoints API partiellement testes

**Description** : Sur ~68 handlers API, seuls ~15-20 sont testes directement (securite, multi-user, observabilite, image_get). Les handlers de chat, fichiers, scheduler, MCP, tunnel n'ont pas de tests d'endpoint dedies.

**Recommandation** : Ajouter un smoke test par endpoint (status code + auth requirement verification).

---

## E. Deploiement et CI/CD

### E-1 | ELEVEE — Pas de build Docker en CI

**Description** : Aucun workflow GitHub Actions ne build `deploy/Dockerfile.backend`. L'image est construite directement sur le serveur de production.

**Pourquoi c'est problematique** : Les regressions Docker (packages absents, erreurs de COPY) ne sont detectees qu'au deploiement. Pas de registre d'images versionne.

**Impact valorisation** : Un investisseur technique s'attendra a du CI/CD complet pour un produit en production.

---

### E-2 | ELEVEE — Pas de SAST ni de scanning de dependances

**Description** : Aucun CodeQL, Snyk, Dependabot, Trivy, ou equivalent dans les workflows CI.

**Impact valorisation** : Non-conforme aux pratiques standard de securite de la supply chain.

---

### E-3 | MOYENNE — Scripts de deploiement incoherents

**Description** : `deploy/scripts/install.sh` utilise `127.0.0.1:5050` pour le health check, mais le port 5050 n'est pas publie dans le docker-compose par defaut. Les scripts utilisent `docker-compose` (v1) au lieu de `docker compose` (v2).

---

### E-4 | MOYENNE — Deux fichiers `.env.example`

**Description** : `/.env.example` (oriente Oracle) et `/deploy/.env.example` (oriente deploy) coexistent avec des scopes differents.

**Recommandation** : Unifier en un seul fichier avec des commentaires de section.

---

## Tableau recapitulatif

| ID | Theme | Severite | Resume | Statut |
|---|---|---|---|---|
| B-1 | Securite | ~~CRITIQUE~~ | Cle HMAC par defaut en dur | ✅ CORRIGE |
| B-2 | Securite/IP | ~~CRITIQUE~~ | Badge MIT vs licence proprietaire | ✅ CORRIGE |
| A-1 | Architecture | ELEVEE | Modules monolithiques >1000 lignes | Ouvert |
| A-2 | Architecture | ELEVEE | Duplications consensus | Ouvert |
| B-3 | Securite | ELEVEE | Mode sans auth par defaut | Ouvert |
| B-4 | Securite | ~~ELEVEE~~ | Mot de passe en clair dans logs | ✅ CORRIGE |
| B-5 | Securite | ~~ELEVEE~~ | RBAC audit_reports incoherent | ✅ CORRIGE |
| C-1 | Code | ~~ELEVEE~~ | asyncio.run dans loop existant | ✅ Partiellement corrige |
| D-1 | Tests | ELEVEE | Suite etendue non-bloquante | Ouvert |
| E-1 | CI/CD | ELEVEE | Pas de build Docker en CI | Ouvert |
| E-2 | CI/CD | ELEVEE | Pas de SAST/scanning | Ouvert |
| A-3 | Architecture | MOYENNE | helpers/ fourre-tout |
| A-4 | Architecture | MOYENNE | Dual Docker |
| B-6 | Securite | MOYENNE | Comparaison cle API non constante |
| B-7 | Securite | MOYENNE | Masquage secrets fail-open |
| B-8 | Securite | MOYENNE | Browser disable_security |
| C-2 | Code | MOYENNE | Code mort/commente |
| C-3 | Code | MOYENNE | Etat global mutable |
| C-4 | Code | MOYENNE | Inconstance stylistique |
| D-2 | Tests | MOYENNE | Couverture non mesuree |
| D-3 | Tests | MOYENNE | APIs partiellement testees |
| E-3 | CI/CD | MOYENNE | Scripts deploy incoherents |
| E-4 | CI/CD | MOYENNE | Double .env.example |
| C-5 | Code | FAIBLE | Tables hardcodees policy.py |
