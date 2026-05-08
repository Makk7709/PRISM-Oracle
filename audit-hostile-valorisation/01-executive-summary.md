# 01 — Executive Summary : Audit Hostile de Valorisation

**Projet** : KOREV Evidence  
**Date d'audit initial** : 3 avril 2026  
**Mise a jour** : 17 avril 2026 ; verification de coherence Git complementaire au 25 avril 2026  
**Version auditee** : commit `7a77fdb6` (branche `main`) au 17 avril 2026 ; HEAD verifie `7a7abd6a` au 24 avril 2026  
**Auditeur** : audit interne effectue par l'apporteur en posture hostile (persona CTO / due diligence)  
**Perimetre** : codebase complet, documentation, CI/CD, deploiement, securite, tests  
**Methode** : lecture seule — zero modification de code  
**Note** : Cette version integre les corrections P0 (3-8 avril 2026) et les livrables P1/P2 partiels (17 avril 2026 : SECURITY.md, 5 ADR, GLOSSARY.md, diagrammes C4, 64 tests TDD). Les elements probatoires commerciaux (factures DICA FRANCE, pilotes Centrale Lille / Le Tarmac), le rattachement explicite de PRISM et d'Evidence a leur inventeur Amine Mohamed et le portefeuille de 4 brevets PRISM en cours sont traites en complement dans `docs/DOSSIER_COMMISSAIRE_APPORTS_EVIDENCE.md` et `audit-hostile-valorisation/08-audit-hostile-dossier-commissaire-apports.md`.

---

## Verdict global

**KOREV Evidence est un actif technologique reellement fonctionnel, dont le niveau de maturite se situe entre le "prototype avance industrialise" et le "produit logiciel en structuration".**

Le projet presente des couches d'ingenierie serieuses (securite multi-tenant, pipeline de consensus deterministe, orchestration d'agents LLM, audit de conformite AI Act/RGPD, integrite cryptographique des rapports) qui le distinguent d'un simple wrapper autour d'APIs LLM. Cependant, plusieurs axes fragiliseraient sa position face a un examen externe hostile :

- **Dette technique concentree** dans des modules volumineux et un couplage fort autour du noyau d'orchestration.
- **Documentation abondante mais heterogene** — melange de docs operationnelles, de marketing interne, de specifications techniques et de traces de session, sans organisation hierarchique claire pour un lecteur externe.
- **Couverture de tests elevee mais inegale** — reference documentaire a 3 910 tests collectes avec parametrisation (audit initial : ~3 846 tests / 179 fichiers), mais la suite etendue est non-bloquante en CI, et les endpoints API sont partiellement couverts.
- ~~**Securite globalement serieuse mais avec des failles ponctuelles**~~ — **Les 4 failles critiques/elevees P0 ont ete corrigees** (licence, HMAC, logs, RBAC). Des failles ponctuelles de severite moindre subsistent (mode sans auth par defaut, masquage fail-open).
- **Dependance apporteur / inventeur elevee** — la connaissance implicite est concentree dans des modules monolithiques, mais le guide d'onboarding (v7.1, 1 196 lignes) reduit partiellement ce risque.

---

## Niveau de maturite percu

| Critere | Evaluation |
|---|---|
| Architecture | Structuree avec intention, mais a consolider |
| Qualite de code | Professionnelle par endroits, prototypage sophistique ailleurs |
| Securite | Fondations solides, failles P0 corrigees, implementation a consolider |
| Tests | Volume impressionnant (3 846), rigueur inegale |
| Documentation | Volumineuse, desormais structuree (ADR, glossaire, C4, SECURITY.md) |
| Industrialisation | Deploiement Docker fonctionnel, CI partielle |
| Auditabilite | Framework d'audit Evidence + replay engine + human review workflow |
| Reprise par tiers | Amelioree par ADR, glossaire, C4 — reste couteuse mais estimee a 1.5-2 semaines d'onboarding |

**Score global : 69/100** (detail en livrable 07) — en hausse par rapport au 58/100 initial (3 avril) et 65/100 post-P0, grace aux livrables documentaires P1/P2

---

## Principales forces

1. **Pipeline de consensus PRISM** — architecture multi-arbitres avec fail-closed, quorum, contrats types, validation stricte. C'est un differenciateur technique reel.
2. **Framework de conformite Evidence** — generation automatique de rapports d'audit avec integrite cryptographique (HMAC/RSA), taxonomie des sources, grille de conformite AI Act. IP defensible.
3. **Securite multi-tenant** — Argon2id, autorisation par principal/organisation, rate limiting Redis+memoire, isolation workspace, validation path/upload/shell. Les fondations sont la.
4. **Volume de tests** — reference documentaire a 3 910 tests collectes avec parametrisation (audit initial : ~3 846 tests / 179 fichiers), harness de simulation LLM (FakeLLMProvider, FakeMCPHandler), tests de securite avec seuil de couverture en CI.
5. **Systeme d'extensions** — architecture de hooks ordonnee couvrant le cycle de vie complet de l'agent (init, prompt, execution, stream, audit). Permet la specialisation par profil.

---

## Principales faiblesses

1. **Modules monolithiques** — `settings.py` (2 225 lignes), `agent.py` (1 144 lignes), `legal_orchestrator.py` (1 960 lignes) concentrent trop de logique. Bus factor critique.
2. ~~**Failles de securite ponctuelles**~~ — **Les 4 failles P0 ont ete corrigees** (cle HMAC : RuntimeError si absente, badge licence proprietaire, logs nettoyes, RBAC aligne). **Restent** : mode sans authentification quand config absente, masquage secrets fail-open.
3. **Documentation en structuration** — 65+ fichiers dans `docs/`, melange de langues. ~~Pas d'ADR ni de SECURITY.md~~ — **5 ADR, SECURITY.md, GLOSSARY.md et diagrammes C4 crees le 17 avril 2026.** Restent : pas de schema de donnees, pas d'API reference.
4. **CI incomplete** — pas de build Docker en CI, pas de SAST/scanning de dependances, suite etendue non-bloquante, pas d'automatisation de deploiement.
5. **Duplications conceptuelles** — deux classes `ArbiterConfig` dans des modules differents, deux chemins d'integration consensus, masquage de secrets duplique entre extensions avec `except: pass`.

---

## Niveau de risque en revue externe

| Scenario | Risque |
|---|---|
| Cabinet d'ingenierie valorisateur | **MOYEN-ELEVE** — Les forces sont reelles mais les failles documentaires et de gouvernance technique seront identifiees rapidement |
| Investisseur technique | **MOYEN** — Le differenciateur PRISM/Evidence est credible, mais la dependance apporteur / inventeur et l'absence de CI complete inquieteront |
| Commissaire aux apports | **MOYEN-FAIBLE** — Licence corrigee, SECURITY.md et 5 ADR crees, benchmark de comparables integre. Restent : schema de donnees, API reference |
| Acquéreur potentiel | **MOYEN-ELEVE** — La reprise par une equipe externe est couteuse sans refactoring prealable |
| Audit securite/conformite | **MOYEN-FAIBLE** — Les fondations sont la, les failles P0 sont corrigees, le pipeline audit-proof (replay, human review, risk register) renforce la credibilite. Restent le mode open et le masquage fail-open |

---

## Capacite actuelle du code + doc a soutenir une valorisation technique

**Le projet peut desormais soutenir un narratif de valorisation solide.** Les corrections P0 (licence, HMAC, logs, RBAC) ont elimine les red flags immediats. Le pipeline audit-proof (replay engine, human review, dynamic risk register) renforce significativement la credibilite de l'approche "IA de confiance". La documentation structurelle est desormais en place : 5 ADR justifiant les decisions architecturales, un SECURITY.md professionnel, un glossaire technique (30+ termes), des diagrammes C4 a 3 niveaux en Mermaid, le tout valide par 64 tests TDD. Le benchmark de references de marche (integre au rapport technique) situe Evidence dans la categorie des infrastructures de decision, pour laquelle les niveaux de valeur sont structurellement superieurs a ceux d'un SaaS standard. Les angles morts restants (monolithes, CI, schema de donnees) pourraient etre exploites pour decoter la valeur de 12 a 20%.

**Recommandation** : 1 a 2 semaines de remediation ciblee sur les P1-P2 restants (tests bloquants, couverture, Docker CI, auth par defaut, scindage settings) pour maximiser la position avant exposition a un cabinet externe. Le projet est desormais presentable dans son etat actuel avec une decote estimee de 12-20%.
