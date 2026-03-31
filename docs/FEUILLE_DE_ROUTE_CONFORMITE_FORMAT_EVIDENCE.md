# Feuille de route — Conformite format Evidence

**Version** : 2.3.0  
**Cree le** : 2026-03-31  
**Derniere mise a jour** : 2026-04-01  
**Statut global** : EN COURS — 6.1/10 sessions validees (SESSION 1-6.1) · PIVOT SCENARIO B actif · Test E2E strategique VALIDE en production  

---

## Contexte

Audit du 31 mars 2026 : le rapport optimal Evidence (11 blocs) a ete compare au code reel.  
**21 elements existent**, **15 sont partiels**, **25 sont absents**.

Le moteur interne (PRISM, raisonnement, confiance, hallucination, routing, PDF) est solide.  
Les lacunes se concentrent sur 3 couches :
1. **Enveloppe de session** — metadonnees d'identite, profil, environnement
2. **Conformite reglementaire** — grille AI Act, RGPD Art. 30, signature RSA des logs
3. **Assemblage du rapport final** — le JSON metadata, la grille sources FR, la grille conformite

Ce document est le plan d'action. Chaque session est atomique, testable, et ne casse pas l'existant.

### Pivot Scenario B (decide le 2026-03-11)

**Constat mi-parcours** : les 5 briques S1-S5 passent leurs tests unitaires mais **aucune n'apparait dans le rapport final** genere par Evidence. Un test E2E reel (dossier strategique CDI via l'interface) a revele un score de **0/5 maillons visibles dans la sortie**.

**Decision** : pivoter les sessions 6-10 pour prioriser le **cablage** des modules existants dans le flux reel, puis construire et cabler en simultane. Plus jamais de code qui n'est pas immediatement visible en production. Chaque session se termine par un test E2E reel.

---

## Convention

| Symbole | Signification |
|:---:|---|
| ⬜ | Non commence |
| 🔄 | En cours |
| ✅ | Termine et verifie |
| ⛔ | Bloque (dependance ou probleme) |

---

## SESSION 1 — Fondation : SessionEnvelope et metadonnees

**Objectif** : Creer le conteneur de metadonnees qui alimente tous les blocs du rapport.  
**Prerequis** : Aucun  
**Risque sur l'existant** : Nul (ajout pur, aucune modification de code existant)  
**Fichiers a creer/modifier** : `python/helpers/session_envelope.py` (nouveau)

### Taches

| # | Tache | Statut | Notes |
|---|---|:---:|---|
| 1.1 | Creer `SessionEnvelope` dataclass avec : `session_id` (format `KRV-SES-YYYYMMDD-XXXXXXX`), `started_at`, `completed_at`, `duration_ms`, `username`, `organization`, `user_profile`, `environment_label`, `evidence_version` | ✅ | `python/helpers/session_envelope.py` |
| 1.2 | Ajouter generateur `session_id` avec horodatage + random hex | ✅ | `_generate_session_id()` — uuid4 CSPRNG |
| 1.3 | Ajouter `compute_duration()` qui calcule `completed_at - started_at` en ms + `duration_seconds` property | ✅ | Rapport affiche en secondes (D1 fix) |
| 1.4 | Ajouter champ `integrity_hash` : SHA-256 avec separateur null byte + sentinel None/empty | ✅ | Collision None≡"" corrigee (D4/D6 fix) |
| 1.5 | Ajouter `environment_label` derive de config (ex: `Production — EU-West (Paris)`) | ✅ | `settings.environment_label` + fallback "" |
| 1.6 | Ajouter `evidence_version` derive de `gitinfo.version` avec warning si "unknown" | ✅ | `logging.warning` si non resolu (D2 fix) |
| 1.7 | Ecrire tests unitaires pour `SessionEnvelope` — 37 tests | ✅ | Tests resolution, edge cases, hash collision |
| 1.8 | Verifier zero regression sur tests existants | ✅ | 0 regression (1 echec pre-existant rebrand) |

### Criteres de validation SESSION 1
- [x] `SessionEnvelope` instanciable avec tous les champs
- [x] `session_id` genere au format `KRV-SES-YYYYMMDD-XXXXXXX`
- [x] Hash d'integrite reproductible et distingue None vs ""
- [x] Aucun test existant casse
- [x] Auto-audit contradictoire execute : score initial 7.5/10 → corrections appliquees (D1-D7)

### AUTO-AUDIT CONTRADICTOIRE — SESSION 1

> **Prompt a executer obligatoirement avant de valider cette session.**
> Persona : Auditeur securite contradictoire, zero tolerance, aucune complaisance.
>
> ```
> Tu es un auditeur externe specialise en tracabilite reglementaire et securite
> applicative. Tu n'as aucun lien avec l'equipe de developpement. Ton role est
> de demolir toute fausse conformite.
>
> Audite SESSION 1 (SessionEnvelope) avec cette grille :
>
> 1. COMPLETUDE — Chaque champ du mock-up "Identite de la session" est-il
>    alimente par du code reel ? Prouve-le en citant fichier + ligne.
>    Si un champ retourne une valeur par defaut ou un placeholder, c'est un ECHEC.
>
> 2. FORMAT — Le session_id genere respecte-t-il exactement le format
>    KRV-SES-YYYYMMDD-XXXXXXX ? Genere 10 IDs et verifie le pattern par regex.
>    Verifie que la date est UTC et que le suffixe hex est bien aleatoire
>    (pas sequentiel, pas predictible).
>
> 3. INTEGRITE — Le hash SHA-256 est-il deterministe ? Verifie que
>    hash(session_id + query + response_hash) donne le meme resultat
>    a chaque appel pour les memes inputs. Verifie qu'il change si un seul
>    octet change. Teste au moins 3 cas limites : query vide, query unicode,
>    response_hash None.
>
> 4. RETROCOMPATIBILITE — Instancie un AgentContext existant, un ReportJob
>    existant, un LegalSafeResponse existant. Verifie qu'aucun import,
>    aucun champ, aucun test existant n'est casse. Lance pytest complet.
>
> 5. EDGE CASES — Que se passe-t-il si : username est None ? organization
>    est vide ? gitinfo.version est "unknown" ? settings ne contient pas
>    environment_label ? Chaque cas doit avoir un comportement defini
>    et teste, pas un crash silencieux.
>
> 6. VERDICT — Note la session sur 10. En dessous de 8/10, la session
>    est REJETEE et doit etre refaite. Liste chaque point de defaillance.
> ```

---

## SESSION 2 — Profil utilisateur et classification requete

**Objectif** : Enrichir le contexte utilisateur et la classification de la requete.  
**Prerequis** : SESSION 1  
**Risque sur l'existant** : Faible (extension de `users.json` schema + enrichissement `RouteDecision`)  
**Fichiers a modifier** : `python/helpers/user_manager.py`, `python/helpers/router/routing_contract.py`, `python/helpers/settings.py`

### Taches

| # | Tache | Statut | Notes |
|---|---|:---:|---|
| 2.1 | Ajouter champ optionnel `profile` dans `users.json` schema (ex: `"Analyste — Niveau 2"`) | ✅ | `users.json.example` + `users.demo.json` mis a jour |
| 2.2 | Ajouter `get_user_profile(username)` dans `UserManager` | ✅ | Fallback role.capitalize() si absent/null/"" |
| 2.3 | Enrichir `RouteDecision` avec `data_sensitivity` (enum: `public`, `internal`, `confidential`, `restricted`) | ✅ | Auto-derive via `max(sensibilite)` multi-intent (D4 fix) |
| 2.4 | Enrichir `RouteDecision` avec `ai_act_category` (enum: `minimal_risk`, `limited_risk`, `high_risk`, `unacceptable`) | ✅ | Auto-derive depuis primary intent |
| 2.5 | Creer mapping `IntentName → ai_act_category` dans `routing_contract.py` | ✅ | Citations Annexe III corrigees (D1 fix) |
| 2.6 | Creer mapping `IntentName → data_sensitivity` | ✅ | Marketing reclassifie INTERNAL (D3 fix) |
| 2.7 | Ecrire tests unitaires — 46 tests | ✅ | Mapping, profil, coherence croisee, serialisation |
| 2.8 | Verifier zero regression | ✅ | 0 regression (1 echec pre-existant rebrand) |

### Criteres de validation SESSION 2
- [x] `UserManager.get_user_profile("amine")` retourne un profil
- [x] `RouteDecision` porte `ai_act_category` et `data_sensitivity`
- [x] Mapping coherent pour chaque type de route (9/9 IntentName couvertes)
- [x] Aucun test existant casse
- [x] Auto-audit contradictoire execute : score 7.5→corrections D1-D6 appliquees

### AUTO-AUDIT CONTRADICTOIRE — SESSION 2

> **Prompt a executer obligatoirement avant de valider cette session.**
> Persona : Auditeur classification reglementaire, expert AI Act et RGPD.
>
> ```
> Tu es un consultant specialise en classification des systemes IA au sens
> du Reglement europeen AI Act (2024/1689). Ton mandat : verifier que les
> classifications implementees sont juridiquement defensables, pas
> arbitraires.
>
> Audite SESSION 2 (Profil + Classification) :
>
> 1. MAPPING AI ACT — Le mapping route_type → ai_act_category est-il
>    conforme a l'Annexe III du Reglement ? Prouve que "legal" = high_risk
>    est correct ou incorrect en citant l'article exact. Un mapping faux
>    invalide toute la grille de conformite en SESSION 5.
>
> 2. SENSIBILITE — Le mapping route_type → data_sensitivity couvre-t-il
>    tous les cas ? Enumere toutes les routes possibles du router et
>    verifie qu'aucune n'est oubliee. Un oubli = fuite de classification.
>
> 3. PROFIL UTILISATEUR — Le champ `profile` dans users.json est-il
>    optionnel sans casser le chargement ? Teste : users.json sans champ
>    profile, users.json avec profile=null, users.json avec profile vide.
>    Si UserManager crash sur un ancien format, c'est un ECHEC CRITIQUE.
>
> 4. ENRICHISSEMENT RouteDecision — Les nouveaux champs cassent-ils la
>    serialisation existante ? Le router existant continue-t-il a
>    fonctionner si ai_act_category et data_sensitivity sont None ?
>    Teste decide_route() sur 5 requetes reelles et verifie que le
>    comportement de routage est IDENTIQUE a avant.
>
> 5. COHERENCE CROISEE — Si un user demande "analyse ce contrat medical",
>    le router route vers quoi ? Le ai_act_category est quoi ? La
>    data_sensitivity est quoi ? Verifie la coherence sur 5 requetes
>    ambigues (legal+medical, strategic+finance, etc.).
>
> 6. VERDICT — Note /10. En dessous de 8, REJET. Liste chaque defaut.
> ```

---

## SESSION 3 — Pipeline Tracker : suivi d'execution des agents ✅ VALIDEE

**Objectif** : Tracker les agents actives, leur role, statut, duree, et lister les agents non actives.  
**Prerequis** : SESSION 1  
**Risque sur l'existant** : Faible (wrapper observer, pas de modification du flux existant)  
**Fichiers crees/modifies** :
- `python/helpers/pipeline_tracker.py` (nouveau — 280 lignes)
- `python/helpers/strategic_orchestrator.py` (modifie — observer autour de `call_agent`)
- `python/tools/call_subordinate.py` (modifie — observer autour de `subordinate.monologue()`)
- `tests/test_session3_pipeline_tracker.py` (nouveau — 46 tests)

### Taches

| # | Tache | Statut | Notes |
|---|---|:---:|---|
| 3.1 | Creer `AgentStep` dataclass : `agent_name`, `role_description`, `status` (pending/running/completed/failed/skipped), `started_at`, `completed_at`, `duration_ms` | ✅ | `time.monotonic()` pour precision |
| 3.2 | Creer `PipelineTracker` class avec `start_step()`, `complete_step()`, `skip_step()`, `get_activated()`, `get_non_activated()`, `to_report_table()`, `to_dict()` | ✅ | Thread-safe (threading.Lock) |
| 3.3 | Definir la liste exhaustive des agents : 11 profils (`default`, `developer`, `finance`, `hacker`, `legal_drafting_guarded`, `legal_safe`, `marketing`, `medical`, `multitask`, `researcher`, `sales`) + decouverte dynamique filesystem | ✅ | `_discover_agents_from_filesystem()` + registre statique |
| 3.4 | `get_non_activated()` = registre complet - agents actives (tries alphabetiquement) | ✅ | |
| 3.5 | Integrer `PipelineTracker` dans `strategic_orchestrator.py` (observer autour de `call_agent`) | ✅ | Tracker stocke sur `StrategicResult.pipeline_tracker` |
| 3.6 | Integrer `PipelineTracker` dans `call_subordinate.py` (observer autour de `monologue()`) | ✅ | Tracker stocke sur `agent.data["_pipeline_tracker"]`, reutilise si existant |
| 3.7 | Ecrire 46 tests unitaires (AgentStep, Core, FailSafe, Concurrence, Performance, Registre, Rendering, Duration, CustomRegistry) | ✅ | 46/46 passed |
| 3.8 | Verifier zero regression (SESSION 1 : 37/37, SESSION 2 : 46/46) | ✅ | 83/83 passed |

### Criteres de validation SESSION 3
- [x] `PipelineTracker` collecte les agents actives avec duree (`time.monotonic()`)
- [x] `get_non_activated()` retourne la liste complementaire (registre - actives, trie)
- [x] Integration non-intrusive (observer pattern, `try/except` fail-safe)
- [x] Aucun test existant casse (129/129 tests total)

### Resultats auto-audit contradictoire SESSION 3

| Axe | Resultat | Detail |
|---|:---:|---|
| 1. Exactitude durees | ✅ | `time.monotonic()` (wall-clock, immune NTP). Pas de divergence avec `AgentResponse.duration_ms` |
| 2. Liste exhaustive | ✅ | 11 agents = `agents/` filesystem. `contradictor` = intent, pas profil. Decouverte dynamique couvre ajouts futurs |
| 3. Concurrence | ✅ | 20 threads simultanes, entrelacement S(A)/S(B)/C(A)/C(B) — 0 race, 0 crash |
| 4. Impact performance | ✅ | start+complete < 1ms (test `test_start_complete_overhead_under_1ms`) |
| 5. Fail-safe | ✅ | 5/5 edge cases geres : double start, complete sans start, double complete, crash agent, erreur interne |
| **6. Verdict** | **8.5/10** | **ACCEPTE** |

#### Defauts identifies et traitement

| ID | Defaut | Severite | Action |
|---|---|:---:|---|
| D1 | `time.time()` dans strategic_orchestrator vs `time.monotonic()` dans tracker | FAIBLE | Documente. Refactor futur possible |
| D2 | `contradictor` (IntentName) absent du registre agents | INFO | Intentionnel : intent, pas profil. Decouverte filesystem le detectera si dossier cree |
| D3 | `SKIPPED` pas d'icone dans `to_report_table` | NEGLIGEABLE | Steps SKIPPED exclus de `get_activated()`, jamais dans le tableau |
| D4 | Tracker reutilise si deja present dans `agent.data` | OK | Correct par design |

### AUTO-AUDIT CONTRADICTOIRE — SESSION 3

> **Prompt a executer obligatoirement avant de valider cette session.**
> Persona : Architecte systeme hostile aux abstractions inutiles.
>
> ```
> Tu es un architecte logiciel senior. Tu consideres que tout observer
> pattern est suspect jusqu'a preuve du contraire. Ton role : verifier
> que le PipelineTracker est fiable sous stress, qu'il ne ment pas,
> et qu'il ne degrade pas les performances.
>
> Audite SESSION 3 (PipelineTracker) :
>
> 1. EXACTITUDE DES DUREES — Le `duration_ms` correspond-il au temps
>    reel d'execution de l'agent, ou au temps mur (wall-clock) ?
>    Si l'agent fait de l'I/O async, le duration_ms inclut-il l'attente ?
>    Compare `AgentResponse.duration_ms` existant (strategic_orchestrator)
>    avec `AgentStep.duration_ms` du tracker. S'ils divergent, le tracker
>    ment. Teste sur 3 scenarios : agent rapide (<1s), agent lent (>10s),
>    agent en timeout.
>
> 2. LISTE EXHAUSTIVE — La liste des 12 agents du systeme est-elle
>    exacte ? Verifie en parcourant le dossier `agents/` et en comparant
>    avec la liste codee en dur. Un agent oublie = "non active" qui
>    n'apparait jamais dans le rapport.
>
> 3. CONCURRENCE — Si deux agents tournent en parallele (ex:
>    legal_safe + researcher dans strategic_orchestrator), le tracker
>    gere-t-il correctement les timestamps concurrents ? Teste avec
>    un start_step() et complete_step() entrelaces. S'il y a un race
>    condition, c'est un ECHEC.
>
> 4. IMPACT PERFORMANCE — Mesure le overhead du tracker sur le chemin
>    critique. Si start_step() + complete_step() ajoutent plus de 1ms
>    de latence, c'est inacceptable pour un observer.
>
> 5. FAIL-SAFE — Que se passe-t-il si complete_step() est appele sans
>    start_step() ? Si start_step() est appele deux fois pour le meme
>    agent ? Si l'agent crash avant complete_step() ? Chaque cas doit
>    avoir un comportement propre, pas un crash du tracker qui emporte
>    le pipeline.
>
> 6. VERDICT — Note /10. En dessous de 8, REJET.
> ```

---

## SESSION 4 — Source Taxonomy : classification FR des sources juridiques ✅ VALIDEE

**Objectif** : Enrichir les `SourceNote` avec une taxonomie FR et un score de fiabilite.  
**Prerequis** : Aucun (independant des sessions 1-3)  
**Risque sur l'existant** : Faible (extension des dataclass existantes)  
**Fichiers crees/modifies** :
- `python/helpers/source_taxonomy.py` (nouveau — 250 lignes)
- `python/helpers/legal_agent_contracts.py` (modifie — 4 champs optionnels sur SourceNote + to_dict)
- `python/helpers/legal_orchestrator.py` (modifie — classify_source integre dans build_source_notes_from_retrieval)
- `tests/test_session4_source_taxonomy.py` (nouveau — 90 tests)

### Taches

| # | Tache | Statut | Notes |
|---|---|:---:|---|
| 4.1 | Creer enum `SourceTypeFR` : 15 types (CEDH distinct de CJUE, circulaires, avis_autorite, convention_collective, etc.) | ✅ | Plus granulaire que prevu (6→15 types) |
| 4.2 | Creer enum `SourceOrigin` : 12 origines (legifrance, eur_lex, judilibre, hudoc, cnil, amf, senat, etc.) | ✅ | Inclut HUDOC (CEDH) |
| 4.3 | Enrichir `SourceNote` avec `source_type_fr`, `source_origin`, `reliability_percent` (0-100), `agent_attribution` | ✅ | Retrocompatible : defauts `None`, to_dict exclut les None |
| 4.4 | Logique d'inference `source_type_fr` : 13 patterns regex (Cass., CE, CA, CEDH, CJUE, Art. L, Loi, Decret, Reglement UE, Directive, Circulaire, Avis, Rapport, Convention collective) | ✅ | CEDH teste AVANT CJUE (priorite) |
| 4.5 | Logique d'inference `origin` : 10 patterns URL + 12 patterns publisher | ✅ | URL prioritaire sur publisher |
| 4.6 | Champ `agent_attribution` ajoute sur SourceNote (Optional[str]) | ✅ | Rempli par le code appelant |
| 4.7 | Ecrire 90 tests unitaires (enums, inference type 48+ sources, inference origin, fiabilite, classify_source, retrocompat SourceNote, CEDH≠CJUE) | ✅ | 90/90 passed |
| 4.8 | Verifier zero regression : 129/129 (S1-S3) + 29/29 legal contracts | ✅ | 248/248 total |

### Criteres de validation SESSION 4
- [x] `SourceNote` porte `source_type_fr`, `source_origin`, `reliability_percent`, `agent_attribution`
- [x] Inference automatique correcte pour Cass.Com, CJUE, Art. L, Legifrance, CEDH, CE, circulaires, avis CNIL
- [x] Pipeline legal inchange en comportement (29/29 tests legal contracts)
- [x] Aucun test existant casse (248/248 verts)

### Resultats auto-audit contradictoire SESSION 4

| Axe | Resultat | Detail |
|---|:---:|---|
| 1. Exhaustivite taxonomie | ✅ | 15 types : circulaires, reponses ministerielles, avis CNIL/AMF, conventions collectives, accords de branche — tous couverts |
| 2. Exactitude inference | ✅ | 48+ sources reelles testees, 0 faux positif, 0 faux negatif. CEDH≠CJUE strictement separes (7 tests dedies) |
| 3. Fiabilite | ✅ | Calibree par hierarchie des normes (force contraignante → 95, soft law → 65-70, doctrine → 60). Reproductible |
| 4. Agent attribution | ✅ | Champ present, attribution par chunk_id unique (pas de conflit doublon) |
| 5. Retrocompatibilite | ✅ | 5 tests SourceNote legacy + 29 tests legal contracts — zero regression |
| **6. Verdict** | **8.5/10** | **ACCEPTE** |

#### Defauts identifies et traitement

| ID | Defaut | Severite | Action |
|---|---|:---:|---|
| D1 | Doctrine pas detectable par regex (trop heterogene) | MINEUR | Par design : tombe dans AUTRE sauf si publisher est explicitement doctrinal. A enrichir quand un publisher registry sera ajoute |
| D2 | `agent_attribution` non auto-rempli dans `build_source_notes_from_retrieval` | MINEUR | Le profile de l'agent appelant n'est pas accessible. Integration prevue quand PipelineTracker (S3) sera connecte au report builder (S8) |

### AUTO-AUDIT CONTRADICTOIRE — SESSION 4

> **Prompt a executer obligatoirement avant de valider cette session.**
> Persona : Juriste specialise en sources du droit, hostile aux classifications approximatives.
>
> ```
> Tu es un juriste documentaliste expert en bases de donnees juridiques
> francaises et europeennes. Tu connais Legifrance, EUR-Lex, DACS, CNIL
> sur le bout des doigts. Ton role : verifier que la taxonomie implementee
> est juridiquement exacte et que l'inference ne produit pas de faux
> positifs.
>
> Audite SESSION 4 (Source Taxonomy) :
>
> 1. EXHAUSTIVITE TAXONOMIE — L'enum SourceTypeFR couvre-t-elle tous les
>    types de sources qu'un pipeline legal francais peut citer ? Manque-t-il :
>    circulaires, reponses ministerielles, avis CNIL, recommandations AMF,
>    conventions collectives, accords de branche ? Si un type est absent,
>    il tombera dans "autre" et le rapport perdra en precision.
>
> 2. EXACTITUDE INFERENCE — Teste l'inference regex sur 20 sources reelles :
>    - "Cass. com., 18 mai 2021, n°19-21.260" → jurisprudence_fr ?
>    - "CJUE, C-265/19, 8 sept. 2020" → jurisprudence_eu ?
>    - "Art. L441-10 Code de commerce" → texte_legislatif ?
>    - "CE, 10 fevrier 2023, n°456123" → jurisprudence_fr ? (Conseil d'Etat)
>    - "Circ. DGFIP du 12/01/2024" → ??? (circulaire = quel type ?)
>    - "CEDH, 15 mars 2022, X c. France" → jurisprudence_eu ? (la CEDH
>      n'est pas la CJUE — c'est une erreur si on la classe pareil)
>    Chaque faux positif ou faux negatif est un ECHEC.
>
> 3. FIABILITE — Le reliability_percent est-il derive d'une methode
>    reproductible ou est-ce un chiffre arbitraire ? Si c'est arbitraire,
>    c'est une fausse metrique qui ne devrait pas figurer dans un rapport
>    d'audit. Quel est le referentiel de calibration ?
>
> 4. AGENT ATTRIBUTION — Si legal_safe ET researcher produisent la meme
>    source (doublon), l'attribution est-elle correcte ? Teste un cas
>    de doublon et verifie le comportement.
>
> 5. RETROCOMPATIBILITE — Les SourceNote existantes (sans les nouveaux
>    champs) passent-elles toujours dans le pipeline sans erreur ?
>    Teste avec une SourceNote legacy (champs None).
>
> 6. VERDICT — Note /10. En dessous de 8, REJET.
> ```

---

## SESSION 5 — Grille de conformite AI Act ✅ VALIDEE

**Objectif** : Generer automatiquement la grille Article / Exigence / Statut.  
**Prerequis** : SESSION 1 (SessionEnvelope), SESSION 3 (PipelineTracker)  
**Risque sur l'existant** : Nul (ajout pur)  
**Fichiers crees** :
- `python/helpers/compliance_grid.py` (nouveau — 300 lignes)
- `tests/test_session5_compliance_grid.py` (nouveau — 38 tests)

### Taches

| # | Tache | Statut | Notes |
|---|---|:---:|---|
| 5.1 | Definir articles + `ComplianceStatus` enum (conforme/partiel/non_conforme/non_applicable) | ✅ | 4 statuts honnetes |
| 5.2 | Creer `ComplianceCheck` dataclass : `article`, `exigence`, `status`, `evidence`, `gaps` | ✅ | Champ `gaps` obligatoire pour PARTIEL |
| 5.3 | Creer `ComplianceGrid` avec `evaluate(envelope, tracker, route_decision, ...)` | ✅ | 7 parametres, overall_status derive |
| 5.4 | Art. 13 Transparence : **PARTIEL** — TraceStep existe mais export lisible incomplet | ✅ | Pas de CONFORME : to_safe_dict() n'expose que le count |
| 5.5 | Art. 14 Supervision humaine : **PARTIEL** — mecanisme existe, registre formel absent | ✅ | Distingue session avec/sans review declenchee |
| 5.6 | Art. 17 Systeme qualite : **PARTIEL** — logs+hash+PRISM oui, monitoring+correction non | ✅ | 4/5 composants QMS manquants |
| 5.7 | Art. 9 Gestion des risques : **PARTIEL** — confidence+criticality oui, risk registry non | ✅ | Integre ai_act_category et data_sensitivity |
| 5.8 | RGPD Art. 30 : **PARTIEL/NON_CONFORME** — metadata oui, registre formel non | ✅ | NON_CONFORME si pas d'envelope |
| 5.9 | Ecrire 38 tests (enum, check, art13-14-17-9-30, grid, anti-washing, to_dict) | ✅ | Test `test_no_check_is_conforme_anti_washing` |

### Criteres de validation SESSION 5
- [x] `ComplianceGrid.evaluate()` retourne 5 checks
- [x] Chaque check a une preuve technique reelle (pas de placeholder)
- [x] Statut derive automatiquement des donnees de session
- [x] **ZERO check CONFORME** (anti-compliance-washing prouve par test)

### Resultats auto-audit contradictoire SESSION 5

| Axe | Resultat | Detail |
|---|:---:|---|
| 1. Art. 13 Transparence | ✅ | PARTIEL honnete : traces existent mais export utilisateur incomplet |
| 2. Art. 14 Supervision | ✅ | PARTIEL honnete : mecanisme existe, pas de registre formel |
| 3. Art. 17 Qualite | ✅ | PARTIEL honnete : logs oui, QMS complet non (monitoring, correction absents) |
| 4. Art. 9 Risques | ✅ | PARTIEL honnete : confidence + criticality oui, risk registry formel non |
| 5. RGPD Art. 30 | ✅ | PARTIEL/NON_CONFORME honnete : metadata oui, registre Art. 30 formel non |
| 6. Statut honnete | ✅ | 0 CONFORME sur 5 articles. Test anti-washing explicite |
| **7. Verdict** | **9/10** | **ACCEPTE** — Zero compliance washing |

#### Defauts identifies et traitement

| ID | Defaut | Severite | Action |
|---|---|:---:|---|
| D1 | Art. 14 pourrait distinguer NON_APPLICABLE vs PARTIEL selon contexte | MINEUR | Retourne PARTIEL car mecanisme existe — acceptable |
| D2 | Pas de ponderation des articles dans overall_status | INFO | Par design : chaque article traite individuellement |

### AUTO-AUDIT CONTRADICTOIRE — SESSION 5

> **Prompt a executer obligatoirement avant de valider cette session.**
> Persona : Auditeur de conformite AI Act certifie, zero tolerance pour le "compliance washing".
>
> ```
> Tu es un auditeur independant mandate pour verifier la conformite d'un
> systeme IA au Reglement europeen AI Act (2024/1689). Tu as deja vu
> 50 systemes qui pretendent etre conformes avec des grilles bidon.
> Ton travail : separer la conformite reelle du theatre de conformite.
>
> Audite SESSION 5 (Grille AI Act) :
>
> 1. Art. 13 TRANSPARENCE — Le critere "TraceStep presents" est-il
>    suffisant pour declarer conformite a l'Art. 13 ? L'Art. 13 exige
>    que les utilisateurs puissent COMPRENDRE le fonctionnement du
>    systeme, pas juste que des traces existent. Les TraceStep sont-ils
>    lisibles par un humain non-technique ? Sinon, "Conforme" est un
>    MENSONGE.
>
> 2. Art. 14 SUPERVISION HUMAINE — Le critere "requires_human_review
>    evalue" signifie quoi exactement ? Qu'il existe dans le code ?
>    Ou qu'il a ete EFFECTIVEMENT active pendant cette session ?
>    Si la session n'a pas declenche de revue humaine, peut-on dire
>    "Conforme" ? Ou devrait-on dire "Non applicable a cette session" ?
>    La distinction est CRITIQUE pour un auditeur.
>
> 3. Art. 17 SYSTEME QUALITE — "Logs structures + hash integrite"
>    ne suffit pas. L'Art. 17 exige un systeme de gestion de la qualite
>    complet. Les logs sont UNE composante. Ou sont : la gestion des
>    versions, la gestion des donnees d'entrainement, le monitoring
>    post-deploiement, les procedures de correction ? Declarer
>    "Conforme" sur la base des seuls logs est TROMPEUR.
>
> 4. Art. 9 GESTION DES RISQUES — Un confidence_score n'est PAS un
>    systeme de gestion des risques au sens de l'Art. 9. L'Art. 9
>    exige : identification des risques, estimation, evaluation,
>    mesures d'attenuation, et monitoring continu. Le confidence_score
>    couvre l'estimation, pas le reste.
>
> 5. RGPD Art. 30 — Ou est le registre des traitements ? Un champ
>    "metadata enregistrees" n'est PAS un registre au sens de l'Art. 30.
>    Le registre doit contenir : finalites, categories de personnes,
>    destinataires, transferts, delais d'effacement, mesures de securite.
>    Tout ca est-il EFFECTIVEMENT enregistre ?
>
> 6. STATUT HONNETE — Pour chaque article, quel devrait etre le statut
>    honnete : Conforme / Partiellement conforme / Non conforme ?
>    Si on met "Conforme" alors que c'est "Partiel", c'est une fraude
>    a l'audit.
>
> 7. VERDICT — Note /10. En dessous de 8, REJET IMMEDIAT.
>    Si un seul article est faussement declare "Conforme", c'est 0/10.
> ```

---

## ⚡ TEST MI-PARCOURS — Diagnostic E2E (2026-03-11)

**Methode** : Lancement d'un dossier strategique reel via l'interface Evidence (CDI Cadre — Convention Syntec, Lead IA).  
**Objectif** : Verifier que les modules S1-S5 apparaissent dans le rapport final.

### Resultat

| Maillon | Module | Present dans le rapport ? | Verdict |
|---|---|---|---|
| **S1** | `SessionEnvelope` | Aucun `KRV-SES-...`, aucun hash d'integrite, aucun horodatage de session | **❌ ABSENT** |
| **S2** | `AIActCategory` / `DataSensitivity` | Pas de classification AI Act de la requete dans la sortie | **❌ ABSENT** |
| **S3** | `PipelineTracker` | Aucune trace des agents actives, durees, pipeline | **❌ ABSENT** |
| **S4** | `SourceTaxonomy` | Table "Bases legales" presente mais sans `source_type_fr`, `reliability_percent` | **❌ ABSENT** |
| **S5** | `ComplianceGrid` | Aucune grille de conformite reglementaire | **❌ ABSENT** |

**Score : 0/5 maillons visibles dans le rapport final.**

### Diagnostic

Les 5 briques sont solides individuellement (257 tests unitaires passent). Elles ne sont pas **cablees** dans le moteur de rapport. Concretement :

- `SessionEnvelope` n'est **jamais instanciee** dans le flux reel de traitement
- `PipelineTracker` est integre dans `strategic_orchestrator.py` et `call_subordinate.py`, mais son **rendu n'est pas injecte** dans le rapport
- `ComplianceGrid.evaluate()` n'est **appele nulle part** dans la chaine de generation
- `SourceTaxonomy` est integre dans `legal_orchestrator.py`, mais les champs enrichis de `SourceNote` ne sont **pas rendus** dans la table de sources

### Decision

**Pivot Scenario B** : les sessions 6-10 priorisent le cablage des modules existants, puis construisent et cablent en simultane. Chaque session se termine par un test E2E reel via l'interface.

---

## SESSION 6 — Cablage : SessionEnvelope + PipelineTracker dans le flux reel ✅ VALIDEE

**Objectif** : Faire apparaitre les metadonnees de session (S1) et le pipeline d'agents (S3) dans le rapport genere par Evidence.  
**Prerequis** : SESSION 1, SESSION 3  
**Risque sur l'existant** : Modere (modification du flux de traitement — necessite tests e2e)  
**Strategie** : Integration non-intrusive via extensions existantes + fail-safe `try/except`

### Taches

| # | Tache | Statut | Notes |
|---|---|:---:|---|
| 6.1 | Analyser message loop, extension system, agent.data, pipeline flow | ✅ | `_pipeline_final_response` lu dans `agent.py` apres `monologue_start` |
| 6.2 | Creer `_05_session_envelope_init.py` dans `message_loop_start/` : instancier `SessionEnvelope`, stocker sur `agent.data["_session_envelope"]` | ✅ | username, organization, query, profile depuis agent.context/config |
| 6.3 | Creer `_20_audit_metadata_append.py` dans `monologue_start/` : apres hooks pipeline (_10 legal, _15 strategic), appeler `.complete()` + hash response + injecter audit block | ✅ | response_hash calcule sur l'original AVANT append |
| 6.4 | Injecter `SessionEnvelope.to_report_table()` dans le pipeline response | ✅ | Section "Identite de la session" avec session_id, hash, timestamps |
| 6.5 | Recuperer `PipelineTracker` depuis `StrategicResult.pipeline_tracker` ou `agent.data["_pipeline_tracker"]`, injecter `tracker.to_report_table()` + agents non actives | ✅ | Resolution cascade : strategic_result → agent.data fallback |
| 6.6 | Ecrire 25 tests : init (9), append (11), integration chain (5) | ✅ | 25/25 passed |
| 6.7 | Verifier zero regression (S1-S5 : 257 tests) | ✅ | 282/282 passed (257 anciens + 25 nouveaux) |

### Criteres de validation SESSION 6
- [x] Pipeline response enrichie avec `KRV-SES-YYYYMMDD-XXXXXXX`
- [x] Hash d'integrite SHA-256 dans le rapport (response_hash + integrity_hash)
- [x] Liste des agents actives avec durees dans le rapport (PipelineTracker)
- [x] Fail-safe prouve : crash init/complete/tracker ne bloque jamais la reponse
- [x] Auto-audit contradictoire execute : 8.5/10 ACCEPTE

### Resultats auto-audit contradictoire SESSION 6 (initial)

| Axe | Resultat | Detail |
|---|:---:|---|
| 1. Point d'injection | ❌ | **CRITIQUE** : `_05` dans `message_loop_start` — jamais execute pour pipelines (short-circuit L415) |
| 2. Enrichissement | ✅ | Sources correctes : context.username, context.organization |
| 3. Fail-safe init | ✅ | try/except prouve (test_handles_none_context_gracefully) |
| 4. Timing | ✅ | Wall-clock session (init → complete), correct pour le rapport |
| 5. Tracker recovery | ✅ | Degradation gracieuse : 3 scenarios testes (vide, absent, erreur) |
| 6. Donnees reelles | ✅ | Unicite session_id, hash deterministe, agents reels |
| **7. Verdict initial** | **7/10** | **REJET — C1 critique bloquant** |

#### Defauts identifies

| ID | Defaut | Severite | Action |
|---|---|:---:|---|
| C1 | `_05` dans `message_loop_start/` au lieu de `monologue_start/` — jamais execute pour pipelines | **CRITIQUE** | → SESSION 6.1 |
| D1 | `user_profile` est le profil agent (legal_safe), pas le profil utilisateur users.json | MINEUR | → SESSION 6.1 |
| D2 | `duration_ms` couvre init→complete, pas le temps CPU strict du pipeline | INFO | Par design |
| D3 | `organization` n'est pas rendue dans `to_report_table()` du SessionEnvelope | MINEUR | → SESSION 6.1 |
| D4 | Cache extensions jamais invalide — risque en hot-reload | INFO | → SESSION 6.1 |

### SESSION 6.1 — Corrections audit hostile

| # | Tache | Status | Detail |
|---|---|:---:|---|
| 6.1.1 | Corriger C1 : deplacer `_05` → `monologue_start/_03` | ✅ | Fichier deplace, ancienne path supprimee |
| 6.1.2 | Corriger D1 : `_resolve_human_profile()` depuis UserManager | ✅ | Priorite : Flask UserManager → agent profile → "default" |
| 6.1.3 | Corriger D3 : ajouter "Organisation" dans `to_report_table()` | ✅ | Ligne ajoutee entre Utilisateur et Profil |
| 6.1.4 | Corriger D4 : `invalidate_extension_cache()` dans extension.py | ✅ | Invalidation globale ou par dossier |
| 6.1.5 | Ecrire 15 tests SESSION 6.1 (C1: 3, D1: 5, D3: 3, D4: 3, integration: 1) | ✅ | 40/40 total (25+15) |
| 6.1.6 | Regression complete S1-S6.1 | ✅ | 297/297 passed, zero regression |

### Resultats auto-audit contradictoire SESSION 6.1 (re-execution)

| Axe | Resultat | Detail |
|---|:---:|---|
| A. Correction C1 | ✅ | `monologue_start/_03` avant tous pipelines, ancien chemin n'existe plus |
| B. Correction D1 | ✅ | 5 scenarios testes (Flask, no-Flask, vide, None, crash) |
| C. Correction D3 | ✅ | 4 tests dont integration e2e avec org visible dans rapport |
| D. Correction D4 | ✅ | 3 tests (global, specifique, inexistant) |
| E. Zero regression | ✅ | 297/297 passed |
| **Verdict** | **10/10** | **ACCEPTE — Tous defauts corriges** |

### Test E2E production — SESSION 6.1

**Date** : 2026-04-01  
**Environnement** : OVH VPS (evidence-backend, Docker, commit `6bac1fa6`)

#### Test 1 : Requete LEGAL (CDI cadre Lead IA)

| Aspect | Resultat | Detail |
|---|:---:|---|
| Detection pipeline | ✅ | `is_strategic=False` — correctement route comme legal (7+ patterns `LEGAL_EXCLUSION_PATTERNS`) |
| Flux utilise | ⚠️ | LLM classique + `call_subordinate` (Evidence-1), PAS pipeline short-circuit |
| Contenu genere | ✅ | CDI complet 20+ articles (non-concurrence, PI, RGPD, AI Act) |
| Metadonnees audit | ❌ | **NON VISIBLES** — `_pipeline_final_response` jamais defini pour le flux LLM classique |
| Doublons UI | ⚠️ | Reponses apparaissent en double (main agent + sub-agent) — probleme pre-existant |

**Diagnostic** : Les metadonnees d'audit S6.1 ne couvrent que le chemin pipeline short-circuit (`_pipeline_final_response`). Les requetes passant par le flux LLM classique (legales via `call_subordinate`) ne sont pas couvertes.

**Impact** : L'audit metadata fonctionne pour les dossiers strategiques mais pas pour les documents legaux. Extension de la couverture a prevoir en SESSION 7 (hook `message_loop_end` ou `response` tool).

#### Test 2 : Requete STRATEGIQUE (dossier cibles commercialisation)

**Date** : 2026-04-01  
**Prompt** : "fais moi un dossier strategique sur les cibles a attaquer en premier pour la com..."  
**Correlation ID** : `ee255409-d810-4785-a730-63689d9f8335`

| Aspect | Resultat | Detail |
|---|:---:|---|
| Detection pipeline | ✅ | `is_strategic=True, type=strategic_dossier` — correctement route vers pipeline strategique |
| Pipeline multi-agent | ✅ | 4 agents actives : researcher (107 src, 175s), finance (124 src, 217s), marketing (107 src, 163s), sales (110 src, 177s) |
| Consolidation LLM | ✅ | 43 821 chars fusionnes |
| Short-circuit LLM | ✅ | `llm_bypassed=True` — pipeline a court-circuite le flux normal |
| **SessionEnvelope** | **✅** | `KRV-SES-20260331-E93A470`, hash SHA-256 `bb78b23e...`, duree 1019.7s |
| **Profil humain (D1)** | **✅** | `Profil utilisateur: Admin` (pas "legal_safe" — UserManager resolu correctement) |
| **Organisation (D3)** | **✅** | `Organisation: Korev AI` visible dans le tableau d'audit |
| **PipelineTracker** | **✅** | 4 agents avec roles, statuts ✅, durees individuelles + agents non actives listes |
| **Audit metadata** | **✅** | 3 sections appendues : Identite de la session, Pipeline d'execution, Agents non actives |
| Validation strategique | ⚠️ | `FAIL_CLOSED` — critere "Alternatives non analysees" non rempli. Mecanisme de qualite fonctionne comme prevu |
| Version Evidence | ⚠️ | `unknown (non resolu)` — le resolver de version ne trouve pas la valeur. **Fix a prevoir** |

**Verdict test E2E strategique** : **SUCCES** — Tous les modules SESSION 6.1 (SessionEnvelope, PipelineTracker, audit metadata, profil humain, organisation) sont **visibles et fonctionnels en production** sur le chemin pipeline strategique.

**Point d'attention** :
- `evidence_version` affiche "unknown" — le resolver git/settings ne parvient pas a resoudre la version en environnement Docker. A corriger (bug mineur, non bloquant pour la conformite).

### AUTO-AUDIT CONTRADICTOIRE — SESSION 6

> **Prompt a executer obligatoirement avant de valider cette session.**
> Persona : SRE senior + Integration engineer hostile aux effets de bord.
>
> ```
> Tu es un SRE senior qui a vu des "petites integrations" casser des
> systemes de production. Ton role : verifier que le cablage de
> SessionEnvelope et PipelineTracker dans le flux reel ne degrade
> RIEN, n'ajoute RIEN de visible si ca crash, et que les donnees
> affichees sont REELLES.
>
> Audite SESSION 6 (Cablage S1+S3) :
>
> 1. POINT D'INJECTION — L'extension message_loop_start est-elle
>    appelee pour TOUTES les requetes (simple, strategique, legal,
>    medical) ou seulement certaines ? Si seulement certaines,
>    le session_id ne sera pas present sur tous les rapports.
>    Teste 4 types de requetes differents.
>
> 2. ENRICHISSEMENT — username, organization, query sont-ils
>    extraits du BON endroit (flask.session, agent.config,
>    agent.context) ? Si le mauvais champ est lu, les metadonnees
>    seront fausses. Verifie avec 2 comptes differents.
>
> 3. FAIL-SAFE — Si SessionEnvelope.__init__() crash (ex: git
>    module absent, settings non chargees), la requete utilisateur
>    est-elle quand meme traitee ? Simule : mock git.get_version()
>    qui leve une exception. Le message loop doit continuer.
>
> 4. TIMING — Le .complete() est-il appele APRES que la reponse
>    est generee ? Si appele trop tot, le duration_ms sera faux.
>    Si appele trop tard (apres envoi au client), le rapport
>    ne sera pas inclus dans la reponse.
>
> 5. TRACKER RECOVERY — Si le PipelineTracker n'est pas dans
>    agent.data (requete simple sans strategic_orchestrator),
>    le code gere-t-il gracieusement ? Pas de KeyError, pas de
>    AttributeError, juste une section vide dans le rapport.
>
> 6. DONNEES REELLES — Lance un dossier strategique via l'interface.
>    Verifie que le session_id est UNIQUE (pas reutilise entre
>    2 requetes), que le hash change si la query change, que les
>    agents listes correspondent a ceux REELLEMENT actives.
>
> 7. VERDICT — Note /10. Tout effet de bord sur la reponse
>    utilisateur = 0/10 immediat.
> ```

---

## SESSION 7 — Cablage : ComplianceGrid + SourceTaxonomy + ReportMetadata

**Objectif** : Faire apparaitre la grille de conformite (S5), la taxonomie des sources (S4), et les metadonnees techniques dans le rapport.  
**Prerequis** : SESSION 6 (SessionEnvelope et Tracker cables)  
**Risque sur l'existant** : Modere (meme strategie d'integration non-intrusive)  
**Strategie** : Reutiliser les donnees S6 (envelope + tracker) pour alimenter ComplianceGrid et ReportMetadata

### Taches

| # | Tache | Statut | Notes |
|---|---|:---:|---|
| 7.0 | **FIX** : Corriger le resolver `evidence_version` en environnement Docker (`unknown` → version reelle). Diagnostiquer `gitinfo.version` / `settings.evidence_version` dans le conteneur. | ⬜ | Bug identifie en test E2E production (S6.1 Test 2) |
| 7.1 | Recuperer `SessionEnvelope` et `PipelineTracker` depuis `agent.data`, recuperer `RouteDecision` depuis le router, appeler `ComplianceGrid.evaluate()` | ⬜ | Dans l'extension `message_loop_end` |
| 7.2 | Injecter `ComplianceGrid.to_report_table()` dans le rapport final | ⬜ | Bloc "Grille de conformite reglementaire" |
| 7.3 | Enrichir le rendu des sources : si `SourceNote` a `source_type_fr` et `reliability_percent`, les afficher dans la table des sources du rapport | ⬜ | Modifier le renderer existant des sources |
| 7.4 | Creer `ReportMetadata` dataclass minimal : `session_id`, `model_primary`, `agents_activated`, `confidence_score`, `processing_time_ms`, `ai_act_category`, `data_residency` | ⬜ | Assembler depuis envelope + tracker + route_decision |
| 7.5 | Creer `ReportMetadata.from_session()` factory + `to_json()` + `to_markdown_block()` | ⬜ | |
| 7.6 | Injecter `ReportMetadata.to_markdown_block()` dans le rapport | ⬜ | Bloc "Metadonnees techniques" |
| 7.7 | Etendre la couverture audit metadata au flux LLM classique (`call_subordinate` / `message_loop_end`) — pas seulement pipeline short-circuit | ⬜ | Gap identifie en test E2E production (S6.1 Test 1 — legal) |
| 7.8 | Ecrire tests unitaires + tests d'integration | ⬜ | |
| 7.9 | Verifier zero regression | ⬜ | |

### Criteres de validation SESSION 7
- [ ] Un dossier strategique juridique affiche la grille conformite AI Act (5 articles, statuts honnetes)
- [ ] La table des sources affiche `source_type_fr` et `reliability_percent` quand disponibles
- [ ] Le bloc metadonnees techniques apparait dans le rapport
- [ ] Test E2E reel via l'interface confirme la presence des 3 blocs
- [ ] Auto-audit contradictoire execute

### AUTO-AUDIT CONTRADICTOIRE — SESSION 7

> **Prompt a executer obligatoirement avant de valider cette session.**
> Persona : Auditeur AI Act + Data engineer, zero tolerance pour les metriques decoratives.
>
> ```
> Tu es un binome auditeur AI Act + data engineer. L'auditeur verifie
> que la grille de conformite est honnete, le data engineer verifie
> que les metadonnees sont reelles. Ensemble, vous n'acceptez aucune
> valeur decorative.
>
> Audite SESSION 7 (Cablage S5+S4+Metadata) :
>
> 1. GRILLE CONFORMITE — La ComplianceGrid dans le rapport est-elle
>    alimentee par des DONNEES REELLES de la session (envelope, tracker)
>    ou par des valeurs par defaut ? Genere un rapport et verifie que
>    le session_id dans la grille correspond a celui de l'en-tete.
>
> 2. STATUTS HONNETES — Pour ce dossier strategique specifique, le
>    statut de chaque article est-il CORRECT ? Art. 13 devrait etre
>    PARTIEL (pas CONFORME). Si un article est CONFORME, c'est suspect.
>    Verifie chaque evidence et chaque gap.
>
> 3. TAXONOMIE SOURCES — Les sources du rapport portent-elles le
>    bon source_type_fr ? Une source "Cass. soc." est-elle classee
>    jurisprudence_cass (pas autre) ? Une source "Art. L" est-elle
>    classee texte_legislatif ? Teste 5 sources du rapport reel.
>
> 4. RELIABILITY_PERCENT — Les pourcentages de fiabilite sont-ils
>    ceux du mapping calibre (source_taxonomy.py) ou des valeurs
>    inventees ? Verifie la coherence avec le referentiel.
>
> 5. REPORT_METADATA — Le model_primary est-il le NOM EXACT du
>    modele utilise pendant cette session ? Le confidence_score
>    est-il le score REEL ? Le processing_time_ms est-il le temps
>    REEL ? Toute valeur approximative ou par defaut est un ECHEC.
>
> 6. COHERENCE CROISEE — Le session_id en en-tete (S6) est-il
>    identique a celui des metadonnees (S7) et de la grille (S7) ?
>    Les agents listes dans le pipeline (S6) sont-ils les memes
>    que dans les metadonnees (S7) ?
>
> 7. VERDICT — Note /10. Toute metrique decorative = max 5/10.
> ```

---

## SESSION 8 — Integrite, signature, et assemblage du rapport complet

**Objectif** : Completer les blocs Integrite/Securite (hashes, signature), assembler le rapport final complet.  
**Prerequis** : SESSION 7  
**Risque sur l'existant** : Faible (ajout de blocs supplementaires au rapport deja cable)  
**Strategie** : Construire ET cabler dans la meme session (pattern valide par S6-S7)

### Taches

| # | Tache | Statut | Notes |
|---|---|:---:|---|
| 8.1 | Creer `IntegrityBlock` dataclass : `hash_request`, `hash_response`, `hash_document`, `signature_log`, `log_retention`, `audit_access` | ⬜ | Reutiliser les hashes existants (legal_safe_schema.Meta) |
| 8.2 | `hash_request` = SHA-256 de la query, `hash_response` = SHA-256 de la reponse markdown, `hash_document` = SHA-256 du doc analyse (null si absent) | ⬜ | null ≠ hash de chaine vide |
| 8.3 | Creer `LogSigner` avec HMAC-SHA256 (phase 1), key ID format `KRV-SIGN-KEY-NNN` | ⬜ | HMAC explicitement presente comme phase 1, pas comme non-repudiation |
| 8.4 | Injecter `IntegrityBlock.to_report_table()` dans le rapport | ⬜ | Cable immediatement |
| 8.5 | Creer `AuditReportRenderer` qui assemble les blocs dans l'ordre : Identite → Requete → Pipeline → Sources → Conformite → Metadonnees → Integrite → Footer | ⬜ | Centralise tous les rendus |
| 8.6 | Remplacer l'injection bloc-par-bloc (S6-S7) par l'appel unique `AuditReportRenderer.render()` | ⬜ | Refactoring propre |
| 8.7 | Footer auto-generation avec avertissement + proposition PDF | ⬜ | |
| 8.8 | Ecrire tests unitaires + test de snapshot (comparer a un rapport de reference) | ⬜ | |
| 8.9 | Test E2E reel : rapport complet avec tous les blocs | ⬜ | |
| 8.10 | Verifier zero regression | ⬜ | |

### Criteres de validation SESSION 8
- [ ] Rapport complet avec tous les blocs presents et coherents
- [ ] Hashes calcules sur les donnees reelles de la session
- [ ] Signature HMAC-SHA256 verifiable
- [ ] Test de snapshot qui valide la structure complete
- [ ] Test E2E reel via l'interface
- [ ] Auto-audit contradictoire execute

### AUTO-AUDIT CONTRADICTOIRE — SESSION 8

> **Prompt a executer obligatoirement avant de valider cette session.**
> Persona : Cryptographe + Directeur qualite Big Four.
>
> ```
> Tu es un binome cryptographe applique + directeur qualite d'un
> cabinet d'audit international. Le cryptographe verifie la solidite
> des primitives crypto, le directeur qualite verifie la structure
> et la lisibilite du rapport final.
>
> Audite SESSION 8 (Integrite + Assemblage) :
>
> 1. HASHES — Le hash_request est-il calcule sur la query BRUTE ou
>    normalisee ? Le hash_response est-il calcule sur le markdown
>    FINAL ou sur le JSON intermediaire ? Si le hash ne couvre pas
>    ce que l'utilisateur voit, c'est une fausse garantie.
>
> 2. HMAC vs RSA — L'HMAC-SHA256 est-il presente honnetement comme
>    "phase 1 sans non-repudiation" ? Si le rapport dit "Signature
>    log: HMAC-SHA256" sans qualifier, un auditeur pourrait croire
>    que c'est une signature asymetrique.
>
> 3. STRUCTURE RAPPORT — Les blocs sont-ils dans l'ordre exact du
>    mock-up de reference ? Aucun bloc manquant ? Aucun placeholder ?
>
> 4. COHERENCE — Le session_id est-il identique dans TOUS les blocs ?
>    Le hash_response du bloc integrite correspond-il au hash calcule
>    sur le contenu reellement delivre ?
>
> 5. REPRODUCTIBILITE — Memes inputs → meme rapport (hors timestamps) ?
>
> 6. LISIBILITE — Un DPO non-technique comprend-il le rapport sans
>    documentation annexe ? Le "test des 30 secondes" passe-t-il ?
>
> 7. VERDICT — Note /10. Crypto decorative = 0/10. Rapport
>    incomplet = max 5/10.
> ```

---

## SESSION 9 — Tests E2E, stockage, export PDF, integration production

**Objectif** : Automatiser la generation du rapport, gerer le stockage, l'export PDF, et les cas d'echec.  
**Prerequis** : SESSION 8  
**Risque sur l'existant** : Modere (integration dans le flux — necessite tests e2e complets)

### Taches

| # | Tache | Statut | Notes |
|---|---|:---:|---|
| 9.1 | Consolider la generation du rapport dans une extension unique `_30_audit_report_generation.py` (message_loop_end) | ⬜ | Remplace les injections individuelles S6-S7 |
| 9.2 | Stocker le rapport dans `tmp/chats/{ctxid}/audit_report.md` (meme ownership que chat.json) | ⬜ | can_access_context s'applique aussi |
| 9.3 | Export PDF via `evidence_pdf_engine.py` | ⬜ | Reutiliser l'existant |
| 9.4 | Ajouter bouton "Voir le rapport d'audit" dans l'UI (optionnel phase 2) | ⬜ | |
| 9.5 | Fail-safe complet : si la generation crash, la reponse est quand meme livree | ⬜ | try/except + logging.error |
| 9.6 | Cleanup : rapport supprime quand le chat est supprime (chat_remove) | ⬜ | Pas de fuite de donnees |
| 9.7 | Collecter tokens_input/tokens_output depuis les callbacks LLM (enrichir ReportMetadata) | ⬜ | |
| 9.8 | Tests E2E automatises : 5 types de requetes (legal, strategique, medical, general, multi-agent) | ⬜ | |
| 9.9 | Benchmark performance : overhead < 200ms sur le chemin critique | ⬜ | |
| 9.10 | Deployer en staging et valider avec test E2E reel | ⬜ | |

### Criteres de validation SESSION 9
- [ ] Rapport genere automatiquement a chaque fin de session
- [ ] Stocke avec meme ACL que chat.json
- [ ] Export PDF fonctionnel
- [ ] Fail-safe prouve (crash du renderer ne bloque pas la reponse)
- [ ] Overhead < 200ms mesure
- [ ] Tests E2E passent sur 5 types de requetes
- [ ] Auto-audit contradictoire execute

### AUTO-AUDIT CONTRADICTOIRE — SESSION 9

> **Prompt a executer obligatoirement avant de valider cette session.**
> Persona : SRE senior obsede par la fiabilite + DPO obsede par les fuites de donnees.
>
> ```
> Tu es un binome SRE senior + DPO. Le SRE verifie que rien ne casse
> en production, le DPO verifie que les donnees d'audit sont protegees.
>
> Audite SESSION 9 (Integration production) :
>
> 1. PERFORMANCE — Mesure l'overhead sur : requete simple (1 agent),
>    requete complexe (4 agents), requete avec PDF. Si > 200ms sur
>    le chemin critique, c'est un ECHEC.
>
> 2. FAIL-SAFE — Mock un crash dans AuditReportRenderer.render().
>    La reponse utilisateur est-elle livree ? Si non = P0.
>
> 3. OWNERSHIP — Le audit_report.md est-il soumis a can_access_context ?
>    Un MEMBER d'une autre org peut-il le lire ? Teste.
>
> 4. CLEANUP — Supprime un chat (chat_remove). Le audit_report.md
>    est-il aussi supprime ? Si non = fuite de donnees audit.
>
> 5. IDEMPOTENCE — Message loop en retry (3 fois). Le rapport est-il
>    genere 3 fois ? Ecrase-t-il proprement ?
>
> 6. DISK USAGE — Poids moyen d'un audit_report.md ? Projection a
>    1000 sessions/jour sur 1 mois ? Mecanisme de purge ?
>
> 7. MONITORING — Si la generation echoue silencieusement, y a-t-il
>    un log, un compteur ? Un echec silencieux = ECHEC d'observabilite.
>
> 8. VERDICT — Note /10. Tout effet de bord sur la reponse = 0/10.
> ```

---

## SESSION 10 — Hardening, securite, et deploiement production

**Objectif** : Securiser le systeme de rapport (RSA-2048, rotation des cles, controle d'acces, monitoring) et deployer en production.  
**Prerequis** : SESSION 9  
**Risque sur l'existant** : Faible (securisation + monitoring)

### Taches

| # | Tache | Statut | Notes |
|---|---|:---:|---|
| 10.1 | Implementer signature RSA-2048 reelle (phase 2 de `LogSigner`) | ⬜ | Generer keypair, stocker en vault ou env |
| 10.2 | Rotation des cles de signature avec key ID `KRV-SIGN-KEY-NNN` | ⬜ | Anciens rapports restent verifiables |
| 10.3 | Monitoring : metriques generation rapport (temps, taille, erreurs) | ⬜ | Logging structure + compteurs |
| 10.4 | Politique de retention : purge auto apres 5 ans | ⬜ | Cron ou script |
| 10.5 | Endpoint `/admin/audit-reports` (OWNER uniquement) | ⬜ | |
| 10.6 | Controle d'acces : DPO, RSSI, Responsable conformite | ⬜ | |
| 10.7 | Audit de securite du code S1-S10 (bandit, semgrep) | ⬜ | |
| 10.8 | Deployer en production + test E2E final | ⬜ | |

### Criteres de validation SESSION 10
- [ ] Signature RSA-2048 verifiable par un tiers
- [ ] Rotation des cles fonctionnelle
- [ ] Rapports accessibles uniquement aux roles autorises
- [ ] Deploiement production valide
- [ ] Test E2E final : 5 types de rapports complets et conformes

### AUTO-AUDIT CONTRADICTOIRE — SESSION 10

> **Prompt a executer obligatoirement avant de valider cette session.**
> Persona : Pentester + RSSI, test d'intrusion final avant mise en production.
>
> ```
> Tu es un pentester mandate par le RSSI pour valider la mise en
> production du systeme de rapport d'audit. Tu cherches a casser
> chaque garantie de securite annoncee. Si tu y arrives, le systeme
> ne part pas en production.
>
> Audite SESSION 10 (Hardening) :
>
> 1. SIGNATURE RSA — Peux-tu forger une signature valide sans la cle
>    privee ? Modifie un octet du rapport et verifie que la signature
>    est invalide. Si la verification ne rejette pas, c'est decoratif.
>
> 2. KEY MANAGEMENT — Ou est la cle privee ? En clair sur le filesystem ?
>    Dans un vault ? Dans une env var ? Verifie les permissions.
>
> 3. ROTATION — Apres rotation, les anciens rapports sont-ils encore
>    verifiables avec l'ancienne cle publique ?
>
> 4. ACCES — Tente /admin/audit-reports avec MEMBER, autre org, sans
>    auth, avec API key. Tout doit etre bloque.
>
> 5. PURGE — Apres purge >5 ans, les fichiers sont-ils EFFECTIVEMENT
>    supprimes (pas juste dereferences) ?
>
> 6. MONITORING — Simule une panne du generateur pendant 10 min.
>    L'alerte se declenche-t-elle ?
>
> 7. AUDIT STATIQUE — bandit + semgrep sur S1-S10. Secrets en dur ?
>    Injections ? Deserialisations non securisees ?
>
> 8. VERDICT FINAL — Note /10. En dessous de 9/10, la mise en
>    production est BLOQUEE.
> ```

### AUTO-AUDIT CONTRADICTOIRE — GLOBAL (post-SESSION 10)

> **Prompt a executer une seule fois, apres que toutes les sessions sont validees.**
> Persona : Directeur technique + DPO, revue finale avant go-live.
>
> ```
> Tu es le binome DPO + CTO de l'entreprise. Vous faites la revue
> finale avant de declarer le systeme de rapport d'audit conforme.
> Vous avez un seul objectif : pourriez-vous presenter ce rapport
> a un auditeur externe (CNIL, ANSSI, ou cabinet Big Four) sans
> rougir ?
>
> REVUE FINALE :
>
> 1. Genere 5 rapports d'audit sur 5 types de requetes differentes :
>    - Requete legal simple
>    - Requete contractuelle complexe (PDF + analyse multi-clauses)
>    - Requete strategique
>    - Requete medicale
>    - Requete generale sans pipeline specialise
>    Verifie que chaque rapport est complet, coherent, et honnete.
>
> 2. Pour chaque rapport, verifie :
>    - Chaque champ a une valeur reelle (pas de placeholder)
>    - Les scores sont calibres (pas de 100% partout)
>    - Les statuts de conformite sont honnetes (pas de "Conforme"
>      quand c'est "Partiellement conforme")
>    - Les hashes sont verifiables
>    - La signature est valide
>
> 3. Simule un auditeur externe qui demande :
>    - "Montrez-moi comment votre systeme trace le raisonnement"
>      → Le rapport repond-il clairement ?
>    - "Comment savez-vous que le modele n'a pas hallucine ?"
>      → Le rapport apporte-t-il une preuve, pas juste un score ?
>    - "Qui a valide cette reponse et quand ?"
>      → La supervision humaine est-elle tracee avec horodatage ?
>    - "Comment puis-je verifier que ce rapport n'a pas ete modifie ?"
>      → La signature est-elle verifiable independamment ?
>
> 4. VERDICT GLOBAL — Le systeme est-il pret pour un audit externe ?
>    OUI sans reserve / OUI avec reserves (lister) / NON (lister
>    les bloquants).
> ```

---

## Matrice de dependances (v2 — Scenario B)

```
PHASE 1 : CONSTRUCTION DES BRIQUES (S1-S5) ✅ FAIT
SESSION 1 (SessionEnvelope)      ✅
SESSION 2 (Classification)       ✅
SESSION 3 (PipelineTracker)      ✅
SESSION 4 (SourceTaxonomy)       ✅
SESSION 5 (ComplianceGrid)       ✅

⚡ TEST MI-PARCOURS : 0/5 maillons cables → PIVOT SCENARIO B

PHASE 2 : CABLAGE + CONSTRUCTION (S6-S10)
SESSION 6 (Cabler S1+S3)         ← S1, S3
SESSION 7 (Cabler S5+S4+Meta)    ← S6, S2, S4, S5
SESSION 8 (Integrite+Assemblage) ← S7
SESSION 9 (E2E+Production)       ← S8
SESSION 10 (Hardening)           ← S9
```

Progression lineaire S6→S7→S8→S9→S10. Chaque session cable ET teste en E2E.

---

## Journal des mises a jour

| Date | Session | Action | Resultat |
|---|---|---|---|
| 2026-03-31 | — | Audit initial : 21 EXISTE, 15 PARTIEL, 25 ABSENT | Feuille de route creee |
| 2026-03-31 | — | Ajout auto-audits contradictoires (10 sessions + 1 global) + protocole d'execution + compteur de sante | v1.1.0 |
| 2026-03-31 | SESSION 1 | SessionEnvelope cree + 37 tests + auto-audit execute (7.5→corrections D1-D7) | ✅ VALIDEE |
| 2026-03-31 | SESSION 2 | Profil + Classification AI Act + 46 tests + auto-audit (7.5→corrections D1-D6) | ✅ VALIDEE |
| 2026-03-31 | SESSION 3 | PipelineTracker + 46 tests + auto-audit (8.5/10 — D1-D4 documentes) | ✅ VALIDEE |
| 2026-03-31 | SESSION 4 | Source Taxonomy FR + 90 tests + auto-audit (8.5/10 — D1-D2 documentes) | ✅ VALIDEE |
| 2026-03-31 | SESSION 5 | Grille AI Act + 38 tests + auto-audit (9/10 — zero compliance washing) | ✅ VALIDEE |
| 2026-03-11 | MI-PARCOURS | Test E2E reel (dossier strategique CDI via interface) : **0/5 maillons visibles** | ⚠️ PIVOT |
| 2026-03-11 | — | **PIVOT SCENARIO B** : sessions 6-10 reecrites pour prioriser le cablage. v2.0.0 | Plan restructure |
| 2026-03-11 | SESSION 6 | Cablage SessionEnvelope + PipelineTracker dans le flux reel + 25 tests + auto-audit | ❌ REJET (7/10 — C1 critique) |
| 2026-03-11 | SESSION 6.1 | Corrections audit hostile : C1 (hook placement), D1 (human profile), D3 (organisation), D4 (cache). +15 tests. Audit re-execute 10/10. 297/297 tests. | ✅ VALIDEE |
| 2026-04-01 | SESSION 6.1 | **Test E2E production — LEGAL** : detection correcte (non-strategique), audit metadata NON visible (flux LLM classique). Gap identifie. | ⚠️ CONSTATE |
| 2026-04-01 | SESSION 6.1 | **Test E2E production — STRATEGIQUE** : 4 agents (researcher, finance, marketing, sales), SessionEnvelope + PipelineTracker + audit metadata **VISIBLES**. Profil=Admin, Org=Korev AI. FAIL_CLOSED sur validation (par design). `evidence_version=unknown` — fix prevu S7. | ✅ **SUCCES LIVE** |

### Livrables SESSION 1 — SessionEnvelope

| Fichier | Action | Detail |
|---|---|---|
| `python/helpers/session_envelope.py` | **CREE** | Dataclass SessionEnvelope (13 champs), generateur session_id `KRV-SES-YYYYMMDD-XXXXXXX`, hash SHA-256 (separateur null byte, sentinel None), `duration_seconds` property, logging warnings |
| `python/helpers/settings.py` | **MODIFIE** | Ajout `environment_label: str` dans Settings TypedDict + valeur par defaut `""` |
| `tests/test_session_envelope.py` | **CREE** | 37 tests : format, instanciation, duree, integrite, resolution (mocked), edge cases, serialisation |

**Commit** : `aefd19b5` — deploye sur OVH le 2026-03-31

### Livrables SESSION 2 — Profil + Classification

| Fichier | Action | Detail |
|---|---|---|
| `python/helpers/router/routing_contract.py` | **MODIFIE** | Enums `AIActCategory` + `DataSensitivity`, mappings `INTENT_TO_AI_ACT` + `INTENT_TO_SENSITIVITY` (9/9 IntentName), fonctions `get_ai_act_category()` + `get_data_sensitivity()`, champs auto-derives sur `RouteDecision`, logique `max(sensibilite)` multi-intent |
| `python/helpers/router/__init__.py` | **MODIFIE** | Exports des 6 nouveaux symboles |
| `python/helpers/user_manager.py` | **MODIFIE** | Ajout `get_user_profile()` — fallback `role.capitalize()` si profile absent/null/vide |
| `deploy/users.json.example` | **MODIFIE** | Champ `profile` ajoute (2 exemples) |
| `deploy/users.demo.json` | **MODIFIE** | Champ `profile` ajoute (2 utilisateurs demo) |
| `tests/test_session2_profile_classification.py` | **CREE** | 46 tests : mappings AI Act, sensibilite, RouteDecision auto-derive, profil utilisateur, coherence croisee, serialisation |

**Corrections audit contradictoire** : citations Annexe III (D1), Art. 50 (D2), marketing INTERNAL (D3), `max(sensibilite)` multi-intent conforme RGPD Art. 9 (D4), test tie-breaking (D6)

### Livrables SESSION 3 — Pipeline Tracker

| Fichier | Action | Detail |
|---|---|---|
| `python/helpers/pipeline_tracker.py` | **CREE** | `AgentStep` dataclass (7 champs + `_start_monotonic`), `PipelineTracker` class (thread-safe, Lock), `StepStatus` enum (5 etats), registre 11 agents + decouverte filesystem, `to_report_table()` + `to_dict()` |
| `python/helpers/strategic_orchestrator.py` | **MODIFIE** | Import `PipelineTracker`, observer autour de `call_agent()` dans `run_strategic_orchestrator`, champ `pipeline_tracker` sur `StrategicResult` |
| `python/tools/call_subordinate.py` | **MODIFIE** | Import `PipelineTracker`, observer autour de `subordinate.monologue()`, tracker stocke sur `agent.data["_pipeline_tracker"]` (reutilise si existant) |
| `tests/test_session3_pipeline_tracker.py` | **CREE** | 46 tests : AgentStep (9), Core (12), FailSafe (4), Concurrence (2), Performance (1), Registre (7), Rendering (5), Duration (3), CustomRegistry (2) |

**Auto-audit** : 8.5/10 — ACCEPTE. Defauts D1-D4 documentes (non bloquants).

### Livrables SESSION 4 — Source Taxonomy

| Fichier | Action | Detail |
|---|---|---|
| `python/helpers/source_taxonomy.py` | **CREE** | `SourceTypeFR` (15 types), `SourceOrigin` (12 origines), inference regex (13 patterns type, 10 URL + 12 publisher), `classify_source()`, fiabilite calibree par hierarchie des normes |
| `python/helpers/legal_agent_contracts.py` | **MODIFIE** | 4 champs optionnels sur `SourceNote` (`source_type_fr`, `source_origin`, `reliability_percent`, `agent_attribution`), `to_dict` conditionnel |
| `python/helpers/legal_orchestrator.py` | **MODIFIE** | `classify_source` integre dans `build_source_notes_from_retrieval` (try/except fail-safe) |
| `tests/test_session4_source_taxonomy.py` | **CREE** | 90 tests : enums (4), inference type (48), inference origin (13), fiabilite (6), classify (4), retrocompat (5), CEDH≠CJUE (7) |

**Auto-audit** : 8.5/10 — ACCEPTE. D1 (doctrine non-inferable par regex), D2 (agent_attribution manuelle).

### Livrables SESSION 5 — Grille de conformite AI Act

| Fichier | Action | Detail |
|---|---|---|
| `python/helpers/compliance_grid.py` | **CREE** | `ComplianceStatus` (4 statuts), `ComplianceCheck` (article, exigence, status, evidence, gaps), `ComplianceGrid.evaluate()` (5 articles), evaluateurs Art. 13/14/17/9/RGPD30, `to_report_table()`, `to_dict()`, `overall_status` conservateur |
| `tests/test_session5_compliance_grid.py` | **CREE** | 38 tests : enum (2), check (2), art13 (6), art14 (4), art17 (5), art9 (4), rgpd30 (4), grid (11 dont anti-washing) |

**Principe** : zero compliance washing. Aucun article ne retourne CONFORME — tous sont PARTIEL ou NON_CONFORME avec gaps explicites. Test `test_no_check_is_conforme_anti_washing` le prouve.

**Auto-audit** : 9/10 — ACCEPTE. Meilleure note de toutes les sessions.

### Livrables SESSION 6 + 6.1 — Cablage SessionEnvelope + PipelineTracker

| Fichier | Action | Detail |
|---|---|---|
| `python/extensions/monologue_start/_03_session_envelope_init.py` | **CREE (S6) + CORRIGE (S6.1)** | Extension `SessionEnvelopeInit` dans `monologue_start` (corrige C1 — etait dans `message_loop_start`). Instancie `SessionEnvelope` avec username, organization, query. Resout le profil humain via `UserManager` (corrige D1). Fail-safe `try/except`. |
| `python/extensions/monologue_start/_20_audit_metadata_append.py` | **CREE** | Extension `AuditMetadataAppend` : apres hooks pipeline (_10 legal, _15 strategic), hash la response originale (SHA-256), appelle `envelope.complete()`, injecte `SessionEnvelope.to_report_table()` + `PipelineTracker.to_report_table()` dans `_pipeline_final_response`. Resolution cascade tracker : `StrategicResult.pipeline_tracker` → `agent.data["_pipeline_tracker"]`. |
| `python/helpers/session_envelope.py` | **MODIFIE (S6.1)** | `to_report_table()` inclut maintenant la ligne "Organisation" (corrige D3). |
| `python/helpers/extension.py` | **MODIFIE (S6.1)** | Ajout `invalidate_extension_cache()` pour purger le cache (corrige D4). |
| `tests/test_session6_audit_wiring.py` | **CREE (S6) + ENRICHI (S6.1)** | 40 tests : SessionEnvelopeInit (9), AuditMetadataAppend (11), Integration chain (5), D1 human profile (5), D3 organisation (3), D4 cache (3), C1 placement (3), integration S6.1 (1) |

**Auto-audit S6** : 7/10 — REJET (C1 critique).  
**Auto-audit S6.1** : 10/10 — ACCEPTE. Tous defauts corriges.

---

## Regles de mise a jour

1. A chaque debut de session : passer les taches en 🔄
2. A chaque fin de tache : passer en ✅ avec date dans "Notes"
3. Si bloque : passer en ⛔ avec raison
4. En fin de session : ajouter une ligne au journal des mises a jour
5. Ne jamais modifier une session terminee — creer un addendum si correction necessaire
6. Chaque session doit se terminer par `pytest tests/ --tb=short` sans regression

---

## Protocole d'auto-audit contradictoire

Chaque session contient un bloc **AUTO-AUDIT CONTRADICTOIRE** obligatoire.

### Regles d'execution

1. L'auto-audit est execute **APRES** toutes les taches et **APRES** les tests unitaires
2. Le prompt d'audit est copie-colle tel quel dans une nouvelle conversation Cursor avec persona auditeur
3. L'auditeur a acces en lecture seule au code — il ne corrige rien, il constate
4. Le verdict est note sur 10 et consigne dans le journal des mises a jour
5. **En dessous de 8/10** : la session est REJETEE, les defauts sont listes, et la session doit etre corrigee avant de passer a la suivante
6. **En dessous de 5/10** : la session est ANNULEE et reprise de zero
7. Le verdict de l'audit contradictoire est **bloquant** pour le passage a la session suivante
8. Aucune exception : meme sous pression de delai, l'audit ne peut pas etre "skippe"

### Format du verdict

```
SESSION N — AUTO-AUDIT CONTRADICTOIRE
Date : YYYY-MM-DD
Auditeur : [persona utilisee]
Note : X/10

POINTS CONFORMES :
- [liste]

DEFAILLANCES :
- [DEF-N.1] Description — Severite (Critique/Majeur/Mineur)
- [DEF-N.2] ...

VERDICT : ACCEPTE / REJET (corriger DEF-N.x avant de continuer) / ANNULE
```

### Escalade

- Si une session est rejetee 2 fois consecutives, un audit humain reel est requis avant de continuer
- Si 3 sessions sont rejetees au total, la feuille de route doit etre re-evaluee (perimetre trop ambitieux ? architecture inadaptee ?)

---

## Compteur de sante

| Session | Description (v2) | Taches | Auto-audit | Note | Statut |
|:---:|---|:---:|:---:|:---:|:---:|
| 1 | SessionEnvelope (brique) | 8/8 | Execute | 7.5→8+ | ✅ |
| 2 | Classification AI Act (brique) | 8/8 | Execute | 7.5→8.5+ | ✅ |
| 3 | PipelineTracker (brique) | 8/8 | Execute | 8.5/10 | ✅ |
| 4 | SourceTaxonomy (brique) | 8/8 | Execute | 8.5/10 | ✅ |
| 5 | ComplianceGrid (brique) | 9/9 | Execute | 9/10 | ✅ |
| ⚡ | **TEST MI-PARCOURS** | — | E2E reel | **0/5 cables** | ⚠️ |
| 6 | **Cabler S1+S3** (envelope+tracker) | 7/7 | Execute | 7/10 → REJET | ❌ |
| 6.1 | **Corrections audit hostile S6** | 6/6 | Execute | **10/10** | ✅ |
| 7 | **Cabler S5+S4+Metadata** (grid+taxonomy+meta) + fix version resolver + couverture audit LLM classique | 0/10 | — | — | ⬜ |
| 8 | **Integrite + Assemblage** (hashes+renderer) | 0/10 | — | — | ⬜ |
| 9 | **E2E + Production** (stockage+PDF+fail-safe) | 0/10 | — | — | ⬜ |
| 10 | **Hardening** (RSA+rotation+monitoring) | 0/8 | — | — | ⬜ |
| **GLOBAL** | — | — | — | — | ⬜ |
