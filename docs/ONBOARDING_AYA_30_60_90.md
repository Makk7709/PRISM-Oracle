# Bienvenue chez KOREV AI — Plan d'intégration Lead Engineer

**Pour :** Aya — Lead Engineer
**Statut :** Document opérationnel — premier trimestre
**Date :** 4 mai 2026

---

## 1. Bienvenue

Tu rejoins KOREV AI à un moment précis : nous sortons de la phase "produit qui fonctionne" et nous entrons dans la phase "produit qui se transmet". Ton arrivée fait partie intégrante de cette transition.

Nous ne te demandons pas d'apprendre par cœur un système figé. Nous te demandons d'en devenir progressivement la **co-architecte** — celle avec qui les décisions techniques majeures se prendront à deux à partir de J+90, et celle qui structurera l'équipe d'ingénieurs qui te rejoindra à partir du trimestre suivant.

Ce document n'est pas un onboarding RH. C'est un cadre opérationnel. Il dit ce que nous attendons de toi, ce que nous mettons à ta disposition, et ce qui est volontairement protégé pendant la phase d'apprentissage. Il sera révisé à J+30, J+60 et J+90.

---

## 2. Ce que représente Evidence

KOREV Evidence est une plateforme multi-agents d'IA de confiance pour les environnements professionnels exigeants : cabinets d'avocats, médecins, chercheurs, consultants, finance. Le différenciateur n'est pas le LLM (nous utilisons les modèles du marché via LiteLLM), c'est **l'infrastructure de confiance qui les entoure** :

- Pipeline de **consensus multi-arbitres** avec politique fail-closed (ADR-001).
- **Routeur déterministe** anti-injection (sans LLM dans la boucle de routage — ADR-002).
- **Framework Evidence** avec rapports d'audit signés cryptographiquement, mappés sur AI Act Art. 9/13/14/17 et RGPD Art. 30 (ADR-003).
- **Replay engine** : snapshot complet de chaque session avec vérification d'intégrité.
- **Human review** : workflow de validation humaine traçable.
- **Dynamic risk register** : scoring de risque temps réel sur 6 facteurs pondérés.
- **Multi-tenant strict** : isolation par organisation, rôles OWNER/MEMBER, fail-closed.

Le projet est en production sur OVH avec des clients actifs (DICA France, Centrale Lille, Epoque). Le code de la couche d'infrastructure de confiance représente une doctrine technique propriétaire qui a été développée sur les 18 derniers mois, principalement par Amine. Cette doctrine est partiellement formalisée (5 ADR + un guide d'onboarding technique de 1196 lignes) ; elle reste largement implicite dans le code et les choix d'architecture.

**Une partie de ton rôle, sur les 90 prochains jours, est précisément de t'approprier cette doctrine — pas seulement comme utilisatrice, mais comme contributrice qui peut un jour la faire évoluer.**

---

## 3. Pourquoi Evidence avant PRISM

Tu vas entendre parler de PRISM. Voici la cartographie pour ne pas te perdre :

- **KOREV** = la société.
- **Evidence** = le produit (multi-agents IA de confiance, ce que voient nos clients).
- **PRISM** = le nom historique du protocole de validation par consensus multi-LLM utilisé à l'intérieur d'Evidence (notamment dans le pipeline médical et juridique). Le repo GitHub s'appelle encore `PRISM-Oracle` pour des raisons héritées.

PRISM, en tant que potentiel produit autonome, est un sujet stratégique distinct, sur lequel nous prendrons une décision conjointe à J+90. Il n'est volontairement pas dans ton périmètre de mission initiale. Tu y auras accès en lecture, mais nous te demandons de **ne pas y consacrer d'énergie active jusqu'à cette revue**.

Pourquoi commencer par Evidence :

1. **Cycle court vers la valeur business** : Evidence a des clients, des cycles de feedback réels, et une surface technique exploitable dès la première semaine.
2. **Architecture plus accessible** : 12 profils d'agents, 24 hooks d'extension, 71 endpoints API, mais des points d'entrée bien délimités. PRISM est plus dense conceptuellement et nécessite la maîtrise préalable du framework Evidence.
3. **Apprentissage de la doctrine** : tous les invariants techniques de KOREV (fail-closed, déterminisme, auditabilité, anti-injection) se rencontrent dans Evidence. Quand tu les auras vus à l'œuvre dans Evidence, PRISM deviendra une extension naturelle.

---

## 4. Timeline 30 / 60 / 90 — vue synthétique

| Phase | Posture | Mission centrale | Jalon de fin |
|---|---|---|---|
| **30 jours** | Observer | Devenir utilisatrice avancée d'Evidence + lire la doctrine | Critique constructive des 5 ADR remise |
| **60 jours** | Contribuer | Devenir propriétaire d'un module + écrire les tests manquants + premier audit interne | Module transféré + ADR-006 + 1 audit hostile interne |
| **90 jours** | Posséder | Audit hostile autonome + pair programming sur le cœur + décision PRISM | GO/NO-GO PRISM + 2-3 modules co-possédés |

---

## 5. Philosophie : Observer → Contribuer → Posséder

Cette progression n'est pas une concession au "junior" — tu n'es pas junior. C'est la séquence cognitive la plus efficace pour intégrer un système avec une doctrine forte et une dette technique réelle.

**Observer (J0 → J+22)** — tu utilises Evidence comme une cliente, tu lis la doctrine, tu remontes des questions. Tu produis 4 à 6 PR sur des zones périphériques sans risque. Tu identifies les patterns. Tu n'essaies pas de "tout comprendre" — tu construis une carte mentale orientée par la pratique.

**Contribuer (J+22 → J+60)** — tu deviens responsable d'un module ciblé. Tu écris des tests sur des modules critiques pour les comprendre par l'inversion. Tu rédiges ton premier ADR. Tu conduis ton premier audit hostile interne sur un sous-système.

**Posséder (J+60 → J+90)** — tu codécides. Tu audites des choix d'architecture. Tu introduces des invariants formalisés dans le code. Tu deviens contributrice de référence sur 2-3 modules.

À J+90, la conversation change de nature : nous ne discutons plus *comment t'intégrer* mais *comment structurer l'équipe ingénierie qui te rejoindra*.

---

## 6. Les 30 premiers jours — semaine par semaine

### Semaine 1 — Setup et perspective utilisateur

| Jour | Action |
|---|---|
| J1 | 1:1 fondateur (90 min) — vue d'ensemble, accès, vocabulaire, calendrier des revues |
| J2 | Démarrer 3 sessions Evidence en miroir des 3 cas client réels (prospection, fiscalité, recherche LinkedIn) — comprendre le produit en l'utilisant |
| J3 | Setup local : `uv sync`, `.env` minimal, `uv run python run_ui.py`. Lancer la suite tests `pytest tests/ -q` localement. |
| J4-J5 | Lecture intégrale de `docs/DEVELOPER_ONBOARDING_ARCHITECTURE_GUIDE.md` (1196 lignes — environ 6h effectives, à étaler sur 2 jours). Annoter en marge : questions, ambiguïtés, points qui te semblent fragiles. |

### Semaine 2 — Doctrine

| Jour | Action |
|---|---|
| J6 | ADR-001 (Consensus PRISM fail-closed). Rédiger 1 page de critique constructive. |
| J7 | ADR-002 (Router déterministe anti-injection). Tester sur 5 prompts d'injection et observer le routage. |
| J8 | ADR-003 (Framework Evidence — 10 blocs canoniques). Ouvrir un `audit_report.pdf` réel sur le serveur (ex: session beatrice ou benj) et identifier les 10 blocs en vivant. |
| J9 | ADR-004 (LiteLLM) + ADR-005 (Système d'extensions par hooks). |
| J10 | Premier livrable : pre-commit hook (cf. §10 Quick wins) + monitoring file descriptors. |

### Semaine 3 — Premières contributions

| Jour | Action |
|---|---|
| J11-J12 | Lecture du profil `legal_safe` (prompts dans `agents/legal_safe/prompts/` — 744 lignes de markdown) et de l'extension `_10_legal_safe_pipeline.py`. Dessiner un schéma de flux personnel. |
| J13 | Tracer une chaîne de délégation complète sur une session existante (cf. guide d'onboarding §2.3). Identifier le consensus PRISM dans les logs Docker. |
| J14 | Smoke test post-déploiement + pre-flight check des variables d'environnement critiques. |
| J15 | Logging structuré JSON sur les erreurs 500. |

### Semaine 4 — Consolidation

| Jour | Action |
|---|---|
| J16-J18 | Inventaire des 71 endpoints API (table : owner / authentification / scope) — pair programming fondateur sur les 10 premiers, autonome ensuite. |
| J19 | Runbook purge RGPD reproductible. |
| J20 | Uniformisation des `_context.md` des 12 profils d'agents (template commun : description, cas d'usage, températures, outils, garde-fous spécifiques). |
| J21 | Lecture des livrables d'audit interne `audit-hostile-valorisation/01-executive-summary.md` et `05-angle-morts-et-decote-potentielle.md`. |
| J22 | **Revue 30 jours** — 1:1 fondateur, KPIs, décision sur passage à la phase Contribuer. |

---

## 7. Ce qui sera progressivement transféré

### Au plus tard à J+60

- **Propriété pleine** d'un premier module : `python/helpers/processing_register.py`. Ce module concerne le registre des activités de traitement (RGPD Art. 30). Il est aujourd'hui un template statique enrichi ; ton travail consiste à le faire évoluer vers un registre dynamique avec analyse runtime des données traitées par session. Ce sera ton premier ADR (ADR-006), ta première implémentation de bout en bout, ton premier déploiement supervisé.

- **Tests directs** sur 3 modules de la couche audit-proof aujourd'hui couverts uniquement de manière indirecte : `audit_report_renderer.py` (assembleur des 10 blocs), `integrity_block.py` (signatures HMAC/RSA-PSS), `collaborative_consensus.py` (moteur de débat 3 rounds). Écrire les tests directs est la meilleure façon de comprendre la doctrine en l'instrumentant.

- **Premier audit hostile interne** sur un module fondateur (suggestion : `criticality_router.py`) — sur le modèle des livrables existants dans `audit-hostile-valorisation/`. C'est un exercice de mise en posture critique, pas un exercice de critique pour la critique.

### Entre J+60 et J+90

- **Co-propriété** d'un second module (probablement `risk_register.py` ou `compliance_grid.py`, qui sont conceptuellement proches du Processing Register).
- **Pair programming intensif** sur un module du cœur (suggestion : `criticality_router.py`) avec rédaction d'ADR-007 et tests de propriété.
- **Audit hostile complet** d'un domaine choisi : tu décideras lequel parmi (a) métacognition + reasoning_engine + dynamic_risk_register, (b) tout `python/security/`, (c) tout `contract_drafting/`.

À partir de J+90, la matrice de responsabilités est révisée conjointement, et certains modules basculent en codécision.

---

## 8. Zones temporairement protégées

Pendant les 30 à 60 premiers jours, certains modules restent en lecture seule ou en review-only. Ce n'est pas une question de confiance — c'est une question de séquence d'apprentissage. La doctrine sur ces modules est dense, leurs invariants ne sont pas tous encore formalisés en ADR, et toute modification non-contextualisée a un effet en cascade.

| Catégorie | Modules concernés | Posture |
|---|---|---|
| Cœur d'orchestration et sécurité | `python/consensus/engine.py`, `integrity_block.py`, `auth.py`, `authorization.py`, `path_safety.py`, `criticality_router.py`, `code_execution_tool.py` | Lecture critique. Modification uniquement en pair programming. |
| Doctrine en cours de maturation | `metacognition.py`, `reasoning_engine.py`, `dynamic_risk_register.py`, `human_review.py`, `replay_engine.py`, `audit_report_renderer.py`, `compliance_grid.py` | Lecture seule M1, contributions tests M2, contributions code M3+. |
| Pipelines métier volumineux | `legal_pipeline.py`, `legal_orchestrator.py`, `contract_drafting/`, `strategic_orchestrator.py` | Compréhension fonctionnelle M1, contributions périphériques M2 (sous-modules isolés type `templates/`). |
| Frontend monolithique | `webui/` (1300 lignes d'`index.html`, polling fragile) | Hors périmètre M1-M3 sauf urgence client. Refactoring planifié au trimestre suivant. |

À J+90, cette liste est revue et plusieurs catégories s'ouvrent.

---

## 9. Standards engineering KOREV

Quelques règles non négociables, indépendantes de la séniorité :

- **Aucune modification de la couche cœur sans pair programming**. C'est un principe de protection mutuelle — on ne touche pas seul aux modules qui peuvent compromettre l'auditabilité ou la sécurité multi-tenant.
- **Pre-commit hook installé sur ton poste dès la première semaine** (cf. `.cursor/rules/pre-commit-audit.mdc`). La règle d'audit hostile sur chaque commit est non négociable.
- **Vocabulaire imposé** : KOREV (société) / Evidence (produit) / PRISM (protocole). Cette discipline lexicale évite des confusions structurelles, particulièrement dans les communications externes.
- **Pas de `git push --force` sur `main`**. Standard.
- **Branche `main` = production**. Le déploiement passe par `git pull` puis `docker compose up -d --build` sur le serveur OVH. Pas d'environnement de staging actuellement — chaque modification sur main impacte directement les utilisateurs.
- **Nouvelle fonctionnalité majeure → ADR ou refus**. À partir de M2 (S5), tu rédiges les ADR de tes nouvelles contributions structurelles. C'est un livrable normal, pas un effort exceptionnel.
- **Toute citation de capacité produit auprès d'un client ou d'un tiers externe doit refléter le code réel**. Si tu rencontres un écart entre ce qui est écrit dans la documentation utilisateur et ce que fait le code (par exemple sur les seuils de blocage, les rounds de consensus, ou les mécanismes de sandbox), tu remontes — c'est un sujet de gouvernance technique, pas une critique.

---

## 10. Quick wins initiaux

Voici les contributions ciblées des 4 premières semaines. Toutes sont périphériques au cœur — tu les pilotes en autonomie après cadrage rapide.

| # | Quick win | Effort | Semaine |
|---|---|:---:|:---:|
| QW1 | Pre-commit hook git appliquant la règle d'audit hostile | 1 jour | S1 |
| QW2 | Monitoring file descriptors prod (cron horaire + alerte) | 2 heures | S1 |
| QW3 | Logging structuré JSON sur erreurs 500 + correlation_id | 4 heures | S2 |
| QW4 | Uniformisation des `_context.md` des 12 profils d'agents | 1 jour | S2 |
| QW5 | Tests directs sur `audit_report_renderer`, `integrity_block`, `collaborative_consensus` | 3-4 jours | S5-S7 |
| QW6 | Build Docker en CI (non bloquant en première itération) | 1 jour | M2 |
| QW7 | Smoke test post-déploiement automatisé | 4 heures | S2 |
| QW8 | Inventaire des 71 endpoints API | 2-3 jours | S3 |
| QW9 | Pre-flight check des variables d'environnement critiques | 4 heures | S2 |
| QW10 | Runbook purge RGPD reproductible | 1 jour | S4 |

Aucun de ces quick wins ne demande d'autorisation préalable au-delà du cadrage en 1:1. Ils sont tous documentés en backlog et tu choisis l'ordre.

---

## 11. Critères de réussite

### À J+30

- 3 sessions Evidence générées en utilisation réelle (avec audit_reports persistés sur le serveur).
- 5 ADR + onboarding v7.1 + 2 livrables d'audit interne lus, commentés en écrit.
- 4 à 6 PR mergées sur quick wins périphériques.
- Capacité à expliquer en 5 minutes la distinction Evidence / PRISM / KOREV à un tiers technique.
- Document de critique constructive des 5 ADR remis en revue mensuelle.

### À J+60

- Propriété documentée d'au minimum 1 module de la couche KOREV (Processing Register).
- 30 tests ou plus écrits sur 3 modules critiques précédemment non testés directement.
- ADR-006 rédigée et mergée dans `docs/adr/`.
- 1 audit hostile interne livré, niveau de qualité comparable aux audits internes existants.
- Build Docker en CI vert et bloquant sur main.

### À J+90

- 2 à 3 modules co-possédés.
- 1 audit hostile complet livré sur un domaine choisi.
- Capacité, sans accès au code, à expliquer à un tiers technique externe :
  - Pourquoi le routeur est déterministe et pas LLM-driven.
  - Pourquoi le consensus est fail-closed et pas fail-soft.
  - Comment les 10 blocs canoniques cartographient AI Act + RGPD.
  - Pourquoi `EVIDENCE_HMAC_KEY` lève RuntimeError plutôt que de basculer en HMAC dégradé.
- Décision GO/NO-GO PRISM prise conjointement.

---

## 12. Ce que tu peux attendre du fondateur et de l'organisation

### Engagements opérationnels

- **1:1 hebdomadaire de 60 minutes** en M1 (45 min en M2-M3), non négociable. Si une semaine est ratée, elle est rattrapée la semaine suivante avec un slot doublé.
- **Slot quotidien fixe (1 à 2 heures, créneau 10h-12h ou équivalent)** pendant les 4 premières semaines, pour les questions ouvertes, le pair programming et la revue PR.
- **Revue PR sous 24h** sur tout PR ouvert — sauf urgence client, auquel cas un délai est annoncé explicitement.
- **Accès complet au repo, à la prod (lecture), aux comptes admin, aux audits internes**. La transparence est totale dans le périmètre technique.
- **Disponibilité asynchrone** sur Slack pour les questions courtes, avec une norme de réponse sous 4h en horaires ouvrés.

### Sur la doctrine

- Tout choix d'architecture qui te semble étrange, contre-intuitif ou non documenté est une question légitime — pas une critique. La plupart des choix non écrits ont une raison technique précise (souvent liée à l'AI Act, au RGPD ou à un incident antérieur). On les écrira ensemble en ADR.
- Tu peux contredire le fondateur en revue technique. Ce n'est pas un sujet de hiérarchie, c'est un sujet de robustesse de la doctrine. Les modules les plus solides sont ceux qui ont été contestés tôt.

### Sur ton autonomie

- **Décision unilatérale** sur les 10 quick wins listés en §10.
- **Décision unilatérale** sur l'ordre de lecture, la profondeur d'annotation, le rythme d'apprentissage — dans la limite des jalons mensuels.
- **Codécision** progressive à partir de M2 sur les choix techniques structurels.
- **Veto** explicite sur 7 modules cœur (cf. §8) jusqu'à J+90 — c'est temporaire, et c'est documenté.

### Cadre de revue

- Revue mensuelle (J+30, J+60, J+90) avec compte-rendu écrit et décision documentée sur le passage à la phase suivante. Ces revues sont structurées sur les KPIs partagés et sur le test de transmission qualitatif.

---

## Annexe — Documents de référence

- Guide technique d'architecture : `docs/DEVELOPER_ONBOARDING_ARCHITECTURE_GUIDE.md` (1196 lignes — à lire en entier sur S1-S2).
- ADR existants : `docs/adr/ADR-001` à `ADR-005`.
- Audits internes : `audit-hostile-valorisation/` (8 livrables).
- Glossaire technique : `docs/GLOSSARY.md`.
- Diagrammes C4 : `docs/ARCHITECTURE_C4_DIAGRAMS.md`.
- Politique de sécurité : `SECURITY.md`.
- Règle pre-commit : `.cursor/rules/pre-commit-audit.mdc`.
- Infrastructure serveur : `docs/INFRA_SERVEUR_OVH.md`.

---

*Document opérationnel. Révisé conjointement à J+30, J+60 et J+90. La source de vérité ultime sur le système est toujours le code et l'historique git.*
