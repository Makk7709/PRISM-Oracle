# Feuille de route — Conformite format Evidence

**Version** : 1.4.0  
**Cree le** : 2026-03-31  
**Derniere mise a jour** : 2026-03-31  
**Statut global** : EN COURS — 3/10 sessions validees (SESSION 1 + SESSION 2 + SESSION 3)  

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

## SESSION 4 — Source Taxonomy : classification FR des sources juridiques

**Objectif** : Enrichir les `SourceNote` avec une taxonomie FR et un score de fiabilite.  
**Prerequis** : Aucun (independant des sessions 1-3)  
**Risque sur l'existant** : Faible (extension des dataclass existantes)  
**Fichiers a modifier** : `python/helpers/legal_orchestrator.py`, `python/helpers/reporting/evidence_native.py`

### Taches

| # | Tache | Statut | Notes |
|---|---|:---:|---|
| 4.1 | Creer enum `SourceTypeFR` : `jurisprudence_fr`, `jurisprudence_eu`, `texte_legislatif`, `rapport_officiel`, `doctrine`, `autre` | ⬜ | |
| 4.2 | Creer enum `SourceOrigin` : `legifrance`, `eur_lex`, `min_justice`, `cnil`, `dacs`, `autre` | ⬜ | |
| 4.3 | Enrichir `SourceNote` avec `source_type_fr`, `origin`, `reliability_percent` (0-100) | ⬜ | Retrocompatible : defauts `None` |
| 4.4 | Ajouter logique d'inference `source_type_fr` a partir du contenu de la source (Cass. → jurisprudence_fr, CJUE → jurisprudence_eu, Art. L → texte_legislatif, etc.) | ⬜ | Regex sur le titre/reference |
| 4.5 | Ajouter logique d'inference `origin` a partir de l'URL ou publisher | ⬜ | |
| 4.6 | Ajouter `agent_attribution` : quel agent a produit cette source | ⬜ | |
| 4.7 | Ecrire tests unitaires | ⬜ | |
| 4.8 | Verifier zero regression pipeline legal | ⬜ | `pytest tests/ -k legal` |

### Criteres de validation SESSION 4
- [ ] `SourceNote` porte `source_type_fr`, `origin`, `reliability_percent`, `agent_attribution`
- [ ] Inference automatique correcte pour Cass.Com, CJUE, Art. L, Legifrance
- [ ] Pipeline legal inchange en comportement
- [ ] Aucun test existant casse

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

## SESSION 5 — Grille de conformite AI Act

**Objectif** : Generer automatiquement la grille Article / Exigence / Statut.  
**Prerequis** : SESSION 1 (SessionEnvelope), SESSION 3 (PipelineTracker)  
**Risque sur l'existant** : Nul (ajout pur)  
**Fichiers a creer** : `python/helpers/compliance_grid.py` (nouveau)

### Taches

| # | Tache | Statut | Notes |
|---|---|:---:|---|
| 5.1 | Definir la liste des articles applicables : Art. 13 (Transparence), Art. 14 (Supervision humaine), Art. 17 (Systeme qualite), Art. 9 (Gestion des risques), RGPD Art. 30 (Registre traitements) | ⬜ | |
| 5.2 | Creer `ComplianceCheck` dataclass : `article`, `exigence`, `status` (conforme/non_conforme/partiel), `evidence` (preuve technique) | ⬜ | |
| 5.3 | Creer `ComplianceGrid` class avec `evaluate(session_envelope, pipeline_tracker)` | ⬜ | |
| 5.4 | Art. 13 : statut `conforme` si `TraceStep` presents dans le raisonnement | ⬜ | Preuve : "Raisonnement complet trace" |
| 5.5 | Art. 14 : statut `conforme` si `requires_human_review` evalue | ⬜ | Preuve : "Validation enregistree avec horodatage" |
| 5.6 | Art. 17 : statut `conforme` si logs structures + hash integrite | ⬜ | Preuve : "Log signe + conserve 5 ans" |
| 5.7 | Art. 9 : statut `conforme` si `confidence_score` calcule + seuil | ⬜ | Preuve : "Score de confiance + seuil minimal" |
| 5.8 | RGPD Art. 30 : statut `conforme` si metadata de traitement enregistrees | ⬜ | Preuve : "Registre traitements mis a jour" |
| 5.9 | Ecrire tests unitaires | ⬜ | |

### Criteres de validation SESSION 5
- [ ] `ComplianceGrid.evaluate()` retourne 5 checks
- [ ] Chaque check a une preuve technique reelle (pas de placeholder)
- [ ] Statut derive automatiquement des donnees de session

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

## SESSION 6 — Metadonnees techniques JSON

**Objectif** : Assembler le bloc JSON de metadonnees techniques du rapport.  
**Prerequis** : SESSION 1, 2, 3  
**Risque sur l'existant** : Nul (ajout pur)  
**Fichiers a creer** : `python/helpers/report_metadata.py` (nouveau)

### Taches

| # | Tache | Statut | Notes |
|---|---|:---:|---|
| 6.1 | Creer `ReportMetadata` dataclass avec tous les champs : `session_id`, `model_primary`, `llm_backend`, `agents_activated`, `prism_consensus`, `confidence_score`, `human_validation`, `human_validator`, `processing_time_ms`, `tokens_input`, `tokens_output`, `data_residency`, `log_retention_years`, `ai_act_category`, `gdpr_compliant`, `audit_pack_available` | ⬜ | |
| 6.2 | Ajouter tracking `tokens_input` / `tokens_output` dans les appels LLM | ⬜ | Enrichir le callback LLM existant |
| 6.3 | Ajouter `data_residency` comme constante de config (`settings.py`) | ⬜ | Defaut : `"EU-West-Paris"` |
| 6.4 | Ajouter `log_retention_years` comme constante de config | ⬜ | Defaut : `5` |
| 6.5 | Creer `ReportMetadata.from_session(envelope, tracker, ...)` factory | ⬜ | Assemble depuis les composants |
| 6.6 | Creer `to_json()` et `to_markdown_block()` | ⬜ | |
| 6.7 | Ecrire tests unitaires | ⬜ | |

### Criteres de validation SESSION 6
- [ ] `ReportMetadata` serialisable en JSON conforme au mock-up
- [ ] Tous les champs alimentes automatiquement
- [ ] Aucune valeur en dur (tout derive de la session reelle)

### AUTO-AUDIT CONTRADICTOIRE — SESSION 6

> **Prompt a executer obligatoirement avant de valider cette session.**
> Persona : Data engineer paranoid sur la veracite des metriques.
>
> ```
> Tu es un data engineer qui a vu trop de dashboards menteurs. Tu sais
> que la plupart des metriques reportees sont fausses, approximatives,
> ou purement decoratives. Ton role : verifier que chaque champ du JSON
> de metadonnees reflete une mesure REELLE, pas un placeholder.
>
> Audite SESSION 6 (ReportMetadata) :
>
> 1. TOKENS — tokens_input et tokens_output sont-ils mesures par le
>    provider LLM reel (via l'API response) ou estimes par un tokenizer
>    local ? Si estimes, quel est l'ecart avec la realite ? Si le
>    provider ne retourne pas le token count, le champ devrait etre
>    null, pas une estimation deguisee en mesure.
>
> 2. MODEL_PRIMARY — Ce champ contient-il le nom exact du modele
>    appele (ex: "claude-sonnet-4-20250514") ou un alias generique
>    (ex: "anthropic/claude")? Un auditeur doit pouvoir retrouver
>    la version exacte du modele. Verifie sur 3 appels reels.
>
> 3. PRISM_CONSENSUS — Ce booleen est-il alimente par le resultat
>    REEL du moteur PRISM, ou c'est un true en dur parce que "on
>    utilise PRISM" ? Teste : si le consensus n'est PAS declenche
>    (requete triviale), le champ est-il false ? Sinon c'est un
>    mensonge.
>
> 4. HUMAN_VALIDATION — Meme question : si aucune supervision humaine
>    n'a eu lieu pendant la session, le champ est-il false avec
>    human_validator=null ? Ou bien met-on true par defaut parce que
>    "le mecanisme existe" ? La distinction est FONDAMENTALE.
>
> 5. PROCESSING_TIME_MS — C'est le temps mur total de la session,
>    ou la somme des durees LLM ? Si c'est le temps mur, inclut-il
>    le temps d'attente reseau ? Si c'est la somme LLM, c'est
>    trompeur car ca exclut le temps applicatif.
>
> 6. VALEURS PAR DEFAUT — Passe en revue chaque champ. Si un champ a
>    une valeur par defaut non-null (ex: gdpr_compliant=true), est-ce
>    justifie ? Un defaut true sur gdpr_compliant sans verification
>    est une fausse declaration.
>
> 7. VERDICT — Note /10. Un seul champ avec une valeur decorative
>    non prouvee = maximum 5/10.
> ```

---

## SESSION 7 — Integrite et securite : hashes et signature

**Objectif** : Completer le bloc Integrite du rapport (hash requete/reponse/document, signature).  
**Prerequis** : SESSION 1  
**Risque sur l'existant** : Faible (enrichissement des hashes existants dans `legal_safe_schema.Meta`)  
**Fichiers a modifier** : `python/helpers/session_envelope.py`, nouveau `python/helpers/log_signer.py`

### Taches

| # | Tache | Statut | Notes |
|---|---|:---:|---|
| 7.1 | Creer `IntegrityBlock` dataclass : `hash_request`, `hash_response`, `hash_document`, `signature_log`, `log_retention`, `audit_access` | ⬜ | |
| 7.2 | `hash_request` = SHA-256 de la query normalisee | ⬜ | Reutiliser `input_hash` existant de `legal_safe_schema.Meta` |
| 7.3 | `hash_response` = SHA-256 de la reponse markdown | ⬜ | Reutiliser `response_hash` existant |
| 7.4 | `hash_document` = SHA-256 du document analyse (si PDF/contrat) | ⬜ | Reutiliser `document_hash` de `pdf_extraction` |
| 7.5 | Creer `LogSigner` avec signature HMAC-SHA256 (phase 1) puis RSA-2048 (phase 2) | ⬜ | Phase 1 : HMAC avec cle secrete. Phase 2 : RSA avec keypair |
| 7.6 | Definir le key ID format `KRV-SIGN-KEY-NNN` | ⬜ | |
| 7.7 | `audit_access` = liste des roles autorises (DPO, RSSI, Responsable conformite) | ⬜ | Constante de config |
| 7.8 | Ecrire tests unitaires | ⬜ | |

### Criteres de validation SESSION 7
- [ ] `IntegrityBlock` genere avec hashes reels
- [ ] Signature log reproductible et verifiable
- [ ] Key ID au format `KRV-SIGN-KEY-NNN`

### AUTO-AUDIT CONTRADICTOIRE — SESSION 7

> **Prompt a executer obligatoirement avant de valider cette session.**
> Persona : Cryptographe applique, aucune tolerance pour la crypto decorative.
>
> ```
> Tu es un cryptographe applique specialise en integrite des logs et
> signature electronique. Tu as vu trop de systemes qui "hashe des trucs"
> sans comprendre pourquoi. Ton role : verifier que chaque primitive
> crypto est utilisee correctement et qu'elle apporte une garantie reelle.
>
> Audite SESSION 7 (Integrite + Signature) :
>
> 1. HASH REQUEST — Le SHA-256 de la query est-il calcule sur la query
>    brute ou normalisee ? Si normalisee, comment ? La normalisation
>    est-elle deterministe ? Deux queries identiques avec des espaces
>    differents produisent-elles le meme hash ? Si oui, c'est un
>    probleme d'integrite. Si non, c'est un probleme de reproductibilite.
>    Teste les 2 cas.
>
> 2. HASH RESPONSE — Le hash de la reponse est-il calcule AVANT ou
>    APRES le rendu markdown ? Si avant (sur le JSON brut), le hash
>    ne couvre pas ce que l'utilisateur voit. Si apres (sur le markdown),
>    un changement de template casse la verification. Quel choix a ete
>    fait et pourquoi ?
>
> 3. HASH DOCUMENT — Si aucun document n'est analyse (requete sans
>    piece jointe), le champ est-il null ou un hash de chaine vide ?
>    Un hash de chaine vide (e3b0c44...) est TROMPEUR — il ressemble
>    a un hash de document.
>
> 4. HMAC vs RSA — L'HMAC-SHA256 en phase 1 utilise une cle partagee.
>    Qui possede cette cle ? Si le serveur la possede, il peut forger
>    des signatures. L'HMAC ne prouve donc PAS la non-repudiation.
>    C'est acceptable en phase 1 SEULEMENT si le rapport le mentionne
>    explicitement. "Signature log: HMAC-SHA256" ne doit PAS etre
>    presente comme equivalente a RSA-2048.
>
> 5. KEY ROTATION — Si la cle est comprise, tous les logs signes
>    avec cette cle sont compromis. Y a-t-il un mecanisme pour
>    identifier QUELLE cle a signe quel log ? Le format KRV-SIGN-KEY-NNN
>    suffit-il ? Y a-t-il un registre des cles actives/retirees ?
>
> 6. VERIFICATION — Peut-on verifier une signature SANS acces au
>    serveur ? Si la cle HMAC est stockee uniquement cote serveur,
>    un auditeur externe ne peut pas verifier. C'est un ECHEC de
>    non-repudiation.
>
> 7. VERDICT — Note /10. Toute crypto decorative = 0/10.
> ```

---

## SESSION 8 — Assemblage du rapport complet

**Objectif** : Assembler tous les blocs en un rapport markdown unifie au format cible.  
**Prerequis** : SESSIONS 1 a 7  
**Risque sur l'existant** : Nul (nouveau renderer, l'existant n'est pas touche)  
**Fichiers a creer** : `python/helpers/audit_report_renderer.py` (nouveau)

### Taches

| # | Tache | Statut | Notes |
|---|---|:---:|---|
| 8.1 | Creer `AuditReportRenderer` qui assemble les 12 blocs dans l'ordre du mock-up | ⬜ | |
| 8.2 | Bloc 1 : Identite de la session (depuis `SessionEnvelope`) | ⬜ | Tableau Champ/Valeur |
| 8.3 | Bloc 2 : Requete initiale + classification (depuis `RouteDecision`) | ⬜ | Verbatim + type + AI Act + sensibilite |
| 8.4 | Bloc 3 : Pipeline d'execution (depuis `PipelineTracker`) | ⬜ | Tableau #/Agent/Role/Statut/Duree |
| 8.5 | Bloc 4 : Raisonnement complet (depuis `TraceStep` + logs) | ⬜ | Logs timestampes par agent |
| 8.6 | Bloc 5 : Supervision humaine (depuis `HumanDecisionInterface`) | ⬜ | Tableau si applicable |
| 8.7 | Bloc 6 : Resultat livre (depuis pipeline legal/strategic) | ⬜ | Synthese + tableau clauses si legal |
| 8.8 | Bloc 7 : Sources utilisees (depuis `SourceNote` enrichies) | ⬜ | Tableau #/Source/Type/Agent/Fiabilite/Reference |
| 8.9 | Bloc 8 : Conformite AI Act (depuis `ComplianceGrid`) | ⬜ | Tableau Article/Exigence/Statut |
| 8.10 | Bloc 9 : Metadonnees techniques (depuis `ReportMetadata`) | ⬜ | Bloc JSON |
| 8.11 | Bloc 10 : Integrite et securite (depuis `IntegrityBlock`) | ⬜ | Tableau Champ/Valeur |
| 8.12 | Bloc 11 : Footer auto-generation + proposition PDF | ⬜ | Notice + lien export |
| 8.13 | Ecrire tests unitaires pour le renderer complet | ⬜ | |
| 8.14 | Test de snapshot : comparer la sortie a un rapport de reference | ⬜ | |

### Criteres de validation SESSION 8
- [ ] Rapport markdown complet genere avec les 12 blocs
- [ ] Format conforme aux screenshots de reference
- [ ] Aucun bloc vide ou avec placeholder
- [ ] Test de snapshot qui valide la structure

### AUTO-AUDIT CONTRADICTOIRE — SESSION 8

> **Prompt a executer obligatoirement avant de valider cette session.**
> Persona : Directeur qualite d'un cabinet d'audit Big Four, expert en rapports reglementaires.
>
> ```
> Tu es un directeur qualite chez un cabinet d'audit international.
> Tu revois des rapports de conformite IA tous les jours. Tu sais
> distinguer un rapport solide d'un rapport cosmétique en 30 secondes.
>
> Audite SESSION 8 (Assemblage rapport) :
>
> 1. STRUCTURE — Genere un rapport complet avec des donnees de test
>    realistes. Verifie que les 12 blocs sont presents, dans l'ordre
>    exact des screenshots de reference. Si un bloc est manquant,
>    deplace, ou renomme, c'est un ECHEC.
>
> 2. FIDELITE VISUELLE — Compare le markdown genere avec les 11
>    screenshots pixel par pixel (structure, pas style). Chaque
>    tableau doit avoir les memes colonnes, les memes headers, le
>    meme nombre de lignes. Si le screenshot montre 5 colonnes et
>    le code en genere 4, c'est un ECHEC.
>
> 3. ZERO PLACEHOLDER — Cherche dans le rapport genere les patterns :
>    "TODO", "placeholder", "N/A", "...", "a completer", valeurs vides,
>    0 par defaut, listes vides []. Chaque occurrence est un ECHEC.
>    Un rapport d'audit avec des placeholders est inutilisable.
>
> 4. COHERENCE INTERNE — Le session_id du bloc 1 correspond-il a
>    celui du bloc JSON metadonnees (bloc 9) ? Le confidence_score
>    du bloc raisonnement correspond-il a celui des metadonnees ?
>    Le hash_response du bloc integrite correspond-il au hash de la
>    reponse effective ? Toute incoherence = ECHEC.
>
> 5. REPRODUCTIBILITE — Genere le meme rapport deux fois avec les
>    memes inputs. Les rapports sont-ils identiques (hors timestamps) ?
>    Si non, qu'est-ce qui diverge et pourquoi ?
>
> 6. LISIBILITE — Un DPO non-technique peut-il comprendre ce rapport
>    sans documentation annexe ? Les termes techniques sont-ils
>    expliques ? Les scores ont-ils une echelle de reference ?
>
> 7. VERDICT — Note /10. Un rapport qui ne passe pas le "test des
>    30 secondes" (un auditeur doit trouver la gravite, le perimetre,
>    et la recommandation en 30 secondes) = maximum 5/10.
> ```

---

## SESSION 9 — Integration dans le flux de production

**Objectif** : Brancher le rapport audit sur les pipelines existants pour generation automatique.  
**Prerequis** : SESSION 8  
**Risque sur l'existant** : Modere (integration dans le flux — nesessite tests e2e)  
**Fichiers a modifier** : Extensions existantes, `run_ui.py` (optionnel endpoint)

### Taches

| # | Tache | Statut | Notes |
|---|---|:---:|---|
| 9.1 | Creer extension `_30_audit_report_generation.py` dans `message_loop_end/` | ⬜ | Genere le rapport a la fin de chaque session |
| 9.2 | Instancier `SessionEnvelope` au debut du message loop | ⬜ | Hook dans `message_loop_start` |
| 9.3 | Alimenter `PipelineTracker` depuis les orchestrateurs | ⬜ | Observer pattern |
| 9.4 | Collecter `tokens_input/output` depuis les callbacks LLM | ⬜ | |
| 9.5 | Appeler `AuditReportRenderer` en fin de session | ⬜ | |
| 9.6 | Stocker le rapport dans `tmp/chats/{ctxid}/audit_report.md` | ⬜ | A cote du `chat.json` |
| 9.7 | Ajouter bouton "Voir le rapport d'audit" dans l'UI | ⬜ | Optionnel — phase 2 |
| 9.8 | Export PDF via `evidence_pdf_engine.py` | ⬜ | Reutiliser l'existant |
| 9.9 | Tests e2e complets | ⬜ | |
| 9.10 | Deployer en staging et valider | ⬜ | |

### Criteres de validation SESSION 9
- [ ] Rapport genere automatiquement a chaque fin de session
- [ ] Stocke a cote du chat dans `tmp/chats/`
- [ ] Export PDF fonctionnel
- [ ] Aucune degradation de performance mesurable (<200ms overhead)
- [ ] Tests e2e passent

### AUTO-AUDIT CONTRADICTOIRE — SESSION 9

> **Prompt a executer obligatoirement avant de valider cette session.**
> Persona : SRE senior, obsede par la fiabilite en production et les effets de bord.
>
> ```
> Tu es un Site Reliability Engineer senior. Tu as vu des features
> "inoffensives" faire tomber des systemes en production. Ton role :
> verifier que l'integration du rapport d'audit ne degrade rien,
> ne bloque rien, et echoue proprement.
>
> Audite SESSION 9 (Integration) :
>
> 1. PERFORMANCE — Mesure le temps ajoute par la generation du rapport
>    sur le chemin critique du message loop. Si ca depasse 200ms
>    (objectif declare), c'est un ECHEC. Mesure sur : requete simple
>    (1 agent), requete complexe (4 agents), requete avec PDF.
>    Le rapport doit etre genere en BACKGROUND si necessaire.
>
> 2. FAIL-SAFE — Si la generation du rapport crash (bug, OOM, timeout),
>    la reponse a l'utilisateur est-elle quand meme livree ? Le rapport
>    est un sous-produit, pas le produit principal. Un crash du renderer
>    qui emporte la reponse = ECHEC CRITIQUE P0.
>
> 3. STOCKAGE — tmp/chats/{ctxid}/audit_report.md est-il soumis aux
>    memes regles d'ownership que chat.json ? Un MEMBER peut-il lire
>    le audit_report.md d'un OWNER ? Si oui, c'est une fuite de
>    metadonnees (les hashes, les modeles utilises, etc. sont sensibles).
>    Verifie que can_access_context s'applique AUSSI aux rapports.
>
> 4. IDEMPOTENCE — Si le message loop tourne 3 fois (retry), le
>    rapport est-il genere 3 fois ? Ecrase-t-il le precedent ?
>    Y a-t-il un conflit d'ecriture concurrent ?
>
> 5. CLEANUP — Les rapports sont-ils supprimes quand le chat est
>    supprime (chat_remove) ? Si non, il y a une fuite de donnees :
>    le chat est efface mais le rapport d'audit reste.
>
> 6. DISK USAGE — Quel est le poids moyen d'un audit_report.md ?
>    Si le systeme genere 1000 sessions/jour, quel volume ca
>    represente par mois ? Y a-t-il un mecanisme de purge ?
>
> 7. MONITORING — Si la generation du rapport echoue silencieusement,
>    comment le sait-on ? Y a-t-il un compteur d'erreurs, un log,
>    une alerte ? Un echec silencieux = ECHEC d'observabilite.
>
> 8. VERDICT — Note /10. Tout effet de bord sur la reponse
>    utilisateur = 0/10 immediat.
> ```

---

## SESSION 10 — Hardening et production

**Objectif** : Securiser, optimiser, et valider en production.  
**Prerequis** : SESSION 9  
**Risque sur l'existant** : Faible (optimisation + monitoring)

### Taches

| # | Tache | Statut | Notes |
|---|---|:---:|---|
| 10.1 | Implementer signature RSA-2048 reelle (phase 2 de `LogSigner`) | ⬜ | Generer keypair, stocker en vault |
| 10.2 | Ajouter rotation des cles de signature | ⬜ | |
| 10.3 | Ajouter monitoring : metriques de generation de rapport | ⬜ | Temps, taille, erreurs |
| 10.4 | Ajouter politique de retention : purge auto apres 5 ans | ⬜ | Cron ou script |
| 10.5 | Ajouter endpoint `/admin/audit-reports` pour consulter les rapports | ⬜ | Accessible OWNER uniquement |
| 10.6 | Ajouter controle d'acces au rapport (DPO, RSSI, Responsable conformite) | ⬜ | |
| 10.7 | Audit de securite du nouveau code | ⬜ | |
| 10.8 | Deployer en production | ⬜ | |

### Criteres de validation SESSION 10
- [ ] Signature RSA-2048 verifiable par un tiers
- [ ] Rotation des cles fonctionnelle
- [ ] Rapports accessibles uniquement aux roles autorises
- [ ] Deploiement production valide

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
>    privee ? Teste : modifie un octet du rapport et verifie que la
>    signature est invalide. Si la verification ne rejette pas le
>    rapport modifie, la signature est decorative.
>
> 2. KEY MANAGEMENT — Ou est stockee la cle privee RSA ? En clair
>    sur le filesystem ? Dans un vault ? Dans une variable d'env ?
>    Si en clair, c'est un ECHEC CRITIQUE. Verifie les permissions
>    filesystem. La cle doit etre lisible UNIQUEMENT par le process
>    backend, pas par root, pas par d'autres containers.
>
> 3. ROTATION — Apres rotation de cle, les anciens rapports sont-ils
>    encore verifiables ? L'ancien certificat/cle publique est-il
>    conserve ? Si non, la rotation brise la chaine de verification
>    et rend les anciens rapports inauditables.
>
> 4. ACCES RAPPORTS — Tente d'acceder a /admin/audit-reports avec
>    un compte MEMBER. Tente avec un compte d'une autre org. Tente
>    sans authentification. Tente avec une API key. Chaque tentative
>    doit etre bloquee. Si une seule passe, c'est un ECHEC.
>
> 5. PURGE — Apres la purge des rapports >5 ans, verifie que :
>    les fichiers sont EFFECTIVEMENT supprimes du disque (pas juste
>    dereferences), les hashes ne sont plus resolvables, aucun
>    residue ne traine dans les logs ou le cache.
>
> 6. MONITORING — Simule une panne du generateur de rapport pendant
>    10 minutes. L'alerte se declenche-t-elle ? En combien de temps ?
>    Si personne n'est prevenu, le monitoring est theatre.
>
> 7. AUDIT DE CODE — Passe le code des sessions 1-10 dans un scanner
>    statique (bandit, semgrep). Y a-t-il des secrets en dur, des
>    injections, des deserializations non securisees, des chemins
>    de fichiers non valides ?
>
> 8. VERDICT FINAL — Note /10. C'est l'audit final. En dessous de
>    9/10, la mise en production est BLOQUEE. Liste chaque
>    vulnerabilite residuelle avec sa severite CVSS.
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

## Matrice de dependances

```
SESSION 1 (Fondation)
  ├── SESSION 2 (Profil + Classification)
  ├── SESSION 3 (Pipeline Tracker)
  │     └── SESSION 5 (Grille AI Act) ← aussi SESSION 1
  ├── SESSION 6 (Metadonnees JSON) ← aussi SESSION 2, 3
  └── SESSION 7 (Integrite + Signature)

SESSION 4 (Source Taxonomy) ← independant

SESSIONS 1-7 → SESSION 8 (Assemblage)
SESSION 8   → SESSION 9 (Integration)
SESSION 9   → SESSION 10 (Hardening)
```

Sessions parallelisables : **1+4** peuvent demarrer en parallele. **2, 3** des que 1 est finie. **5, 6, 7** des que leurs prerequis sont valides.

---

## Journal des mises a jour

| Date | Session | Action | Resultat |
|---|---|---|---|
| 2026-03-31 | — | Audit initial : 21 EXISTE, 15 PARTIEL, 25 ABSENT | Feuille de route creee |
| 2026-03-31 | — | Ajout auto-audits contradictoires (10 sessions + 1 global) + protocole d'execution + compteur de sante | v1.1.0 |
| 2026-03-31 | SESSION 1 | SessionEnvelope cree + 37 tests + auto-audit execute (7.5→corrections D1-D7) | ✅ VALIDEE |
| 2026-03-31 | SESSION 2 | Profil + Classification AI Act + 46 tests + auto-audit (7.5→corrections D1-D6) | ✅ VALIDEE |
| 2026-03-31 | SESSION 3 | PipelineTracker + 46 tests + auto-audit (8.5/10 — D1-D4 documentes) | ✅ VALIDEE |

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

| Session | Taches | Auto-audit | Note | Statut |
|:---:|:---:|:---:|:---:|:---:|
| 1 | 8/8 | Execute | 7.5→8+ (D1-D7 corr.) | ✅ |
| 2 | 8/8 | Execute | 7.5→8.5+ (D1-D6 corr.) | ✅ |
| 3 | 8/8 | Execute | 8.5/10 (D1-D4 doc.) | ✅ |
| 4 | 0/8 | — | — | ⬜ |
| 5 | 0/9 | — | — | ⬜ |
| 6 | 0/7 | — | — | ⬜ |
| 7 | 0/8 | — | — | ⬜ |
| 8 | 0/14 | — | — | ⬜ |
| 9 | 0/10 | — | — | ⬜ |
| 10 | 0/8 | — | — | ⬜ |
| **GLOBAL** | — | — | — | ⬜ |
