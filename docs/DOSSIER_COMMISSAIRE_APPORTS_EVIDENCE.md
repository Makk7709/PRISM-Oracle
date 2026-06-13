<!-- markdownlint-disable MD060 -->

# Dossier de valorisation des apports — KOREV Evidence

**Destinataires :** commissaire aux apports et cabinet d'ingénieurs Diag & Grow.  
**Objet :** Synthèse probatoire et contradictoire destinée à soutenir l'évaluation des apports en nature liés à KOREV Evidence.  
**Date :** 25 avril 2026 — **mise à jour le 5 mai 2026** (3 commits postérieurs : `de8b9c7e`, `b11b4d99`, `0d0a35da`).  
**HEAD Git verifié :** `0d0a35da` au 5 mai 2026 (état au 25 avril : `7a7abd6a`).  
**Périmètre :** dépôt `KOREV_Oracle/KOREV_Oracle`, documentation technique, rapport de valorisation, audit hostile interne, ADR, benchmark de comparables.  
**Apporteur / inventeur :** Amine Mohamed, inventeur de PRISM et de KOREV Evidence.  
**Principe directeur :** aucune affirmation non prouvée ne doit être présentée comme acquise. Les éléments probatoires externes doivent être remis en annexes numérotées afin que le commissaire aux apports et Diag & Grow puissent les vérifier indépendamment.

> Cette mise à jour est documentée en miroir dans `audit-hostile-valorisation/09-mise-a-jour-post-p0-yenoyikz.md`. La section 10 du présent document récapitule l'effet des 3 commits postérieurs au 25 avril 2026 ; les sections 1 à 9 reflètent l'état au 25 avril 2026, préservées comme snapshot historique pour préserver l'audit-trail. **L'audit `08-audit-hostile-dossier-commissaire-apports.md` du 25 avril n'est pas modifié** et est complété par l'addendum `09`.

---

## 1. Position défendable en une page

KOREV Evidence est un actif logiciel propriétaire construit sur une base open-source Agent Zero sous licence MIT. La base upstream fournit une fondation d'orchestration générique ; la valeur valorisable porte sur les couches propriétaires ajoutées : PRISM, Evidence, Legal-Safe, auditabilité, sécurité multi-tenant, workflows de conformité et industrialisation.

Le dossier de valorisation doit éviter deux excès :

- **Sous-valorisation** : réduire KOREV Evidence à un fork d'Agent Zero ou à un wrapper LLM. Cette lecture ignore le volume de code propriétaire, les contrats fail-closed, le pipeline Evidence, les modules métier et les tests.
- **Sur-valorisation** : prétendre que l'actif est une entreprise mature ou transposer mécaniquement des multiples de marché IA. L'actif dispose d'un début de traction facturée, mais pas encore d'un historique client long, d'un revenu récurrent diversifié ni d'un audit externe indépendant.

La position optimale est donc une valorisation par **coût de reproduction**, éclairée par des comparables de marché uniquement pour vérifier la cohérence de l'ordre de grandeur. Le scénario recommandé se situe autour de **958 000 € à 1 054 000 €**, avec un biais vers le haut de fourchette si les factures, preuves de pilotes, pièces R&D et éléments PRISM sont effectivement joints au dossier, sous réserve de maintien des preuves Git, de la documentation d'architecture, des tests et de la transparence sur les limites.

### 1.1 Traction commerciale et terrain

| Élément | Statut probatoire | Impact valorisation |
|---|---|---|
| Revenu récurrent DICA FRANCE | Factures disponibles à annexer : **1 500 €/mois**, soit **18 000 €/an en run-rate annualisé** | Réduit fortement l'objection "actif sans preuve de marché". À annexer : factures, contrat/devis ou bon de commande, preuves de paiement disponibles, périmètre de service. |
| Test terrain Centrale Lille | Pièces disponibles à annexer concernant un test auprès de la Chaire Construction 4.0 à Centrale Lille, autour du Pr **Zoubeir Lafhaj** | Signal de crédibilité métier BTP/construction. À annexer : email, protocole de test, compte rendu, lettre de confirmation ou convention. |
| Incubation / accompagnement Le Tarmac by inovallée | Pièces disponibles à annexer concernant l'écosystème Le Tarmac / inovallée | Signal d'écosystème et d'accompagnement entrepreneurial. À annexer : convention, email d'acceptation, attestation ou fiche incubé. |

Ces éléments ne justifient pas à eux seuls une méthode par multiples de chiffre d'affaires : **18 000 € de revenu récurrent annualisé** reste trop faible et trop concentré pour supplanter la méthode par coût de reproduction. En revanche, ils améliorent la défense de la valeur car ils démontrent une exploitabilité commerciale initiale.

---

## 2. Cartographie des actifs valorisables

### 2.1 Actifs techniques propriétaires

| Actif | Valeur défendable | Preuves internes |
|---|---|---|
| PRISM consensus | Validation multi-arbitres et refus fail-closed en cas de consensus insuffisant | `python/consensus/engine.py`, `python/helpers/consensus_arbiter.py`, ADR-001 |
| Débat adversarial | Instruction contradictoire, thèse/antithèse/synthèse | `python/helpers/adversarial_instruction.py`, `python/helpers/adversarial_consensus_integration.py` |
| Router déterministe | Classification de criticité sans LLM dans la boucle de routage | `python/helpers/criticality_router.py`, `python/helpers/router/`, ADR-002 |
| Framework Evidence | Rapports auditables, signatures HMAC/RSA, blocs canoniques | `python/helpers/reporting/evidence_native.py`, `python/helpers/integrity_block.py`, ADR-003 |
| Legal-Safe | Pipeline juridique, citations, contrats de sûreté, leak guard | `python/helpers/legal_pipeline.py`, `python/helpers/legal_orchestrator.py`, `python/helpers/contract_drafting/` |
| Pipeline PDF/OCR | Extraction, fallback OCR, génération PDF professionnelle | `python/helpers/pdf_extraction/`, `python/helpers/evidence_pdf_engine.py` |
| Sécurité et multi-tenant | Argon2id, RBAC, isolation workspace, logs sécurité | `python/security/`, `python/api/audit_reports.py`, `SECURITY.md` |
| Audit-proof pipeline | Replay, revue humaine, registre de risques dynamique | `python/helpers/replay_engine.py`, `python/helpers/human_review.py`, `python/helpers/dynamic_risk_register.py` |
| Tests et documentation | Réduction du risque de reprise, preuve d'intention industrielle | `tests/`, `docs/adr/`, `docs/architecture/C4_DIAGRAMS.md`, `docs/GLOSSARY.md` (à confirmer : absent du dépôt au 2026-06-13) |

### 2.2 Actifs immatériels

| Actif immatériel | Statut probatoire | Traitement recommandé |
|---|---|---|
| Méthodologie PRISM | Prouvée par code, ADR et pièces d'antériorité à annexer | Valoriser comme antériorité technique intégrée au coût de reproduction |
| Portefeuille brevets PRISM en cours | Dossier probatoire disponible à annexer ; concerne PRISM, pas Evidence directement | Présenter en annexe séparée. Renforce la valeur de la brique consensus anti-hallucination si le droit d'usage PRISM -> Evidence est documenté. |
| Savoir-faire métier juridique/médical/conformité | Prouvé par modules, prompts, tests et documentation | Valoriser dans la complexité élevée des modules métier |
| 5 années de R&D pré-repository | Pièces datées disponibles à annexer | Ne pas chiffrer séparément sans revue des pièces ; l'utiliser comme explication de productivité, de savoir-faire et de maturation antérieure |
| Vision d'architecture Evidence | Prouvée par ADR, C4, rapport de valorisation | Valoriser comme capacité de structuration et non comme simple volume de code |

---

## 3. Audit hostile — failles exploitables

| Risque | Sévérité | Exploitation probable par un commissaire hostile | Réponse défendable |
|---|:---:|---|---|
| Métriques Git hétérogènes entre 8, 17 et 24 avril | Important | "Les chiffres changent selon les sections, donc le dossier n'est pas fiable." | Le rapport distingue désormais diff upstream -> HEAD, cumul de commits auteur et état audité. Les commandes de vérification sont fournies. |
| 5 ans de R&D non visibles dans le dépôt | Important | "La R&D antérieure ne peut pas être prise en compte sans pièces externes." | Des pièces R&D datées doivent être annexées. Elles renforcent le scénario haut après revue par le commissaire et Diag & Grow, sans être ajoutées mécaniquement à la valeur cible. |
| Brevets PRISM mal rattachés | Important | "Les brevets concernent PRISM, pas Evidence ; ils ne peuvent pas être valorisés dans Evidence sans chaîne de droits." | Les brevets doivent être présentés comme annexe PRISM distincte. Amine Mohamed est inventeur de PRISM et d'Evidence ; l'effet sur Evidence dépend d'une licence, cession, apport ou droit d'usage documenté. |
| Dépendance à Agent Zero | Important | "La valeur vient du fork open-source, pas de l'apporteur." | Agent Zero est identifié comme base MIT. Les couches PRISM/Evidence/Legal-Safe/sécurité/tests sont isolées comme créations propriétaires. |
| Mode sans authentification par défaut | Élevée | "Le produit de confiance n'est pas secure by default." | Risque ouvert documenté ; remédiation P1-6 prioritaire avant audit externe si possible. |
| Suite étendue non bloquante en CI | Élevée | "Les tests annoncés ne protègent pas la branche principale." | Volume de tests réel mais rigueur CI incomplète ; remédiation P1-3/P1-4 à prioriser. |
| Pas de build Docker/SAST en CI | Élevée | "Industrialisation encore artisanale." | Déploiement Docker existe, mais CI supply-chain à renforcer avant exposition externe. |
| Monolithes et duplications consensus | Moyenne à élevée | "Bus factor et dette technique." | ADR/C4/onboarding réduisent le risque, sans le supprimer. Décote résiduelle justifiée. |
| Sources de marché à vérifier | Moyenne | "Benchmark potentiellement orienté apporteur." | Les comparables ne fondent pas la valeur ; ils éclairent seulement la cohérence du coût de reproduction. |
| Traction mal indexée | Moyenne | "Les revenus et pilotes existent, mais les preuves sont difficiles à rapprocher du dossier." | Annexer et numéroter les factures DICA FRANCE, preuves de paiement, échanges Centrale Lille et éléments Le Tarmac avant transmission. |

---

## 4. Indépendance technologique et substituabilité

### 4.1 Ce que fournit Agent Zero

Agent Zero fournit une base générique : boucle agent, outils génériques, gestion de modèles, WebUI de départ, Docker de développement, documentation communautaire. Ces éléments sont disponibles sous licence MIT et ne doivent pas être valorisés comme création propriétaire.

### 4.2 Ce que KOREV Evidence ajoute

KOREV Evidence ajoute des couches non présentes dans la base upstream : consensus PRISM, Evidence layer, pipelines métier, sécurité multi-tenant, audit reports signés, replay engine, revue humaine, registre de risques dynamique, ADR, C4, glossaire, tests industriels et documentation de déploiement.

### 4.3 Position juridique

La licence MIT autorise l'usage commercial et la création d'oeuvres dérivées propriétaires, sous réserve de conservation des notices. La valorisation doit donc porter sur l'oeuvre dérivée, pas sur Agent Zero lui-même.

### 4.4 Argument de substituabilité

Agent Zero est une dépendance d'amorçage, non un verrou de valeur. Une autre base d'orchestration pourrait être substituée au prix d'un effort de portage. En revanche, substituer PRISM, Evidence, Legal-Safe et les workflows d'audit reviendrait à reconstruire l'actif propriétaire central.

---

## 5. R&D antérieure au dépôt

### 5.1 Position prudente

L'affirmation "5 années de R&D précèdent le premier repository" est potentiellement valorisante, mais elle ne peut pas être prouvée par le seul dépôt actuel. Elle doit donc être formulée avec renvoi aux annexes :

> Amine Mohamed, inventeur de PRISM et de KOREV Evidence, indique que la méthodologie PRISM, les principes de validation contradictoire et l'architecture de confiance résultent d'un travail de R&D antérieur au dépôt Evidence. Le code actuel matérialise une partie de ce savoir-faire ; les pièces d'antériorité sont à remettre en annexes afin de permettre leur revue par le commissaire aux apports et Diag & Grow.

### 5.2 Pièces à produire

- Exports de notes datées, schémas, carnets de conception ou documents PRISM antérieurs au 15 janvier 2026.
- Dépôts Git, archives ZIP, prototypes, captures d'écran ou fichiers portant des métadonnées antérieures.
- Emails, échanges prestataires, tickets, factures d'outils, noms de domaines ou dépôts de marque liés à PRISM/KOREV.
- Dossier des **4 brevets PRISM en cours**, avec récépissés ou preuves de dépôt, dates, inventeurs, titulaires, revendications synthétiques et mention du brevet couvrant le consensus anti-hallucination.
- Document juridique indiquant le droit d'usage de ces actifs PRISM par Evidence : cession, licence, apport ou autorisation formalisée.
- Attestation de l'apporteur / inventeur décrivant les phases de R&D, avec chronologie et pièces jointes.
- Si possible, attestation de tiers ayant vu les prototypes ou documents avant le dépôt actuel.

### 5.3 Effet valorisation

Avec pièces datées, la R&D antérieure explique la productivité exceptionnelle, soutient la crédibilité du savoir-faire et peut justifier un scénario offensif maîtrisé, notamment une prime qualitative sur les modules PRISM intégrés à Evidence. Les brevets en cours ne doivent pas être présentés comme brevets Evidence : ils doivent être rattachés à PRISM et reliés à Evidence par une chaîne de droits explicite.

---

## 6. Scénarios de valorisation

| Scénario | Fourchette | Usage recommandé |
|---|---:|---|
| Conservateur | 662 000 € à 850 000 € | Cas où le commissaire applique une forte prudence sur CI, sécurité résiduelle ou revue incomplète des annexes R&D. |
| Défendable équilibré | 958 000 € à 1 054 000 € | Scénario recommandé : coût de reproduction médian, décote résiduelle 12–20 %, preuves techniques disponibles. Les factures DICA FRANCE et preuves terrain permettent de défendre le haut de fourchette. |
| Offensif maîtrisé | 1 150 000 € à 1 350 000 € | À n'utiliser qu'avec factures DICA FRANCE, preuves de paiement disponibles, annexes R&D, dossier brevets PRISM et droit d'usage PRISM -> Evidence, preuve d'exécutabilité tests/build, confirmations de pilotes et clarification des dépendances. |

La stratégie optimale consiste à présenter le scénario équilibré comme valeur cible, le conservateur comme plancher de sécurité et l'offensif comme marge de négociation. La fourchette haute ne doit pas être présentée comme acquise.

---

## 7. Points de négociation à anticiper

1. **"Pourquoi ne pas appliquer une décote plus forte ?"**  
   Réponse : les risques sont documentés, les P0 sont corrigés, la décote résiduelle 12–20 % couvre CI, bus factor, auth défaut et absence d'audit externe.

2. **"Pourquoi valoriser un fork ?"**  
   Réponse : le fork est une fondation MIT ; la valeur porte sur l'oeuvre dérivée, les modules propriétaires et la spécialisation métier.

3. **"Les comparables IA ne sont pas pertinents pour un actif isolé."**  
   Réponse : ils ne servent pas à calculer la valeur, seulement à vérifier que le coût de reproduction n'est pas hors marché.

4. **"La conformité AI Act est auto-évaluée."**  
   Réponse : exact ; le dossier doit parler de pipeline de conformité et d'auditabilité, pas de certification externe.

5. **"La R&D antérieure n'est pas visible dans le dépôt Git."**  
   Réponse : exact ; elle doit être vérifiée au moyen des pièces datées annexées. Elle ne doit pas être comptée deux fois, mais elle renforce la lecture de l'effort de conception et de la brique PRISM.

6. **"Les brevets sont PRISM, pas Evidence."**  
   Réponse : exact ; ils doivent être présentés comme actifs PRISM en cours. Amine Mohamed étant inventeur de PRISM et d'Evidence, ils renforcent Evidence pour la partie PRISM intégrée si la chaîne de droits PRISM -> Evidence est annexée.

---

## 8. Checklist avant transmission

- Recalculer les métriques Git à la date de transmission et figer le commit HEAD dans le rapport.
- Exécuter ou collecter un `pytest --collect-only` et, si possible, un échantillon de tests bloquants.
- Produire les annexes R&D datées et les indexer dans un sommaire d'annexes.
- Annexer le dossier des 4 brevets PRISM en cours et le document juridique reliant PRISM à Evidence.
- Annexer les factures DICA FRANCE établissant le revenu récurrent de 1 500 €/mois, ainsi que les preuves de paiement disponibles.
- Annexer les preuves de tests terrain : Centrale Lille / Chaire Construction 4.0 / Pr Zoubeir Lafhaj, et Le Tarmac by inovallée.
- Vérifier la présence de la notice MIT et la cohérence `LICENSE`, `legal/THIRD_PARTY_NOTICES.txt`, `README.md`.
- Ajouter, si le délai le permet, build Docker CI, SAST/dependency scan, auth par défaut et fail-closed sur masquage secrets.
- Préparer une annexe "limites connues" assumée : pas d'audit externe, revenu récurrent encore concentré sur un client, CI incomplète, bus factor.

---

## 9. Verdict hostile final

Le dossier est **défendable avec réserves maîtrisées** si la valeur retenue reste ancrée sur le coût de reproduction net de décote. La ligne rouge à ne pas franchir consiste à valoriser deux fois les mêmes apports, ou à appliquer des multiples d'entreprise sans historique commercial suffisant. La marge d'optimisation la plus sûre n'est pas une hausse rhétorique de la valeur, mais la remise d'annexes probatoires complètes au commissaire aux apports et à Diag & Grow, ainsi que la correction des P1 sécurité/CI encore ouvertes.

---

## 10. Mise à jour technique post-25 avril 2026

Cette section synthétise l'effet des trois commits poussés entre le 25 avril et le 5 mai 2026. Le détail probatoire complet est consigné dans `audit-hostile-valorisation/09-mise-a-jour-post-p0-yenoyikz.md`.

### 10.1 Commits couverts

| Commit | Date | Périmètre |
|---|---|---|
| `de8b9c7e` | 4 mai 2026 | Fix `file_writer` fail-hard sur `§§include` non résolus + ADR-006 + 28 tests + post-mortem session yENoyKIZ |
| `b11b4d99` | 5 mai 2026 | P0 migration RDBMS : Postgres + pgvector (gated, zero-impact prod) + ADR-007 + 6 tests d'infra + scripts backup/snapshot + journal P0 |
| `0d0a35da` | 5 mai 2026 | Fix DEF-8 `pg_dump --clean --if-exists` + script `pg_restore_from_dump.sh` fail-loud + test T7 |

### 10.2 Effet sur les risques identifiés en section 3

| Risque section 3 | Évolution post-25 avril |
|---|---|
| (nouveau) Risque "fail-silent tool" non explicité au 25 avril | **Verrouillé** par ADR-006 + 28 tests + post-mortem yENoyKIZ. Argumentaire de défense renforcé face à une attaque `"vos tools peuvent prétendre avoir réussi alors qu'ils ont écrit un fichier corrompu"`. |
| (nouveau) Dette technique `filesystem-first` sur la persistance métier (`users.json`, sessions chat, FAISS, SQLite légal, artefacts) | **Exposée et adressée**. ADR-007 publie une roadmap structurée en 7 phases (P0 livré, P1-P6 planifiées). Aucune perte de fonctionnalité ; aucun service applicatif `depends_on` Postgres en P0. |
| Bus factor / dette technique (section 3, lignes monolithes & duplications consensus) | Inchangé. ADR-006 et ADR-007 ajoutent 2 décisions architecturales formalisées au corpus existant (5 ADR au 25 avril, 7 ADR au 5 mai). |
| Pas de build Docker/SAST en CI (section 3) | Inchangé sur le périmètre CI. Cependant, un service Postgres profile-gated et un compose staging autonome ont été ajoutés à `deploy/`, validés runtime sur le VPS OVH. |

### 10.3 Capacité opérationnelle démontrée

Pendant la phase P0, **deux incidents runtime ont été déclenchés et résolus en moins d'une minute chacun**, documentés en post-mortem dans `docs/migration-rdbms/P0_PRE_REQUIS_INFRA.md` :

1. Un `docker compose down -v --remove-orphans` exécuté hors du dossier prod a détruit deux containers (volumes préservés) ; remontage en ~1 minute, et correctifs de sûreté appliqués (project name verrouillé, retrait de `--remove-orphans` des tests, documentation explicite).
2. Le pipeline restore Postgres a été détecté en mode fail-silent (DEF-8) lors d'un test runtime ; correction par `--clean --if-exists` côté dump et `psql --set ON_ERROR_STOP=1` côté restore, avec test T7 qui aurait piégé le défaut en CI.

Pour un commissaire, l'exposition tracée d'incidents et leur résolution rapide sont un **signal positif** : un projet qui n'expose aucun incident opérationnel est généralement un projet qui les masque.

### 10.4 Garantie d'invariance des signatures audit (préoccupation H-4)

L'audit hostile du plan RDBMS avait identifié un risque critique : *si la migration change l'emplacement des `replay_snapshot.json` et des `audit_report.md`, les signatures HMAC-SHA256 / RSA-PSS-SHA256 émises avant la migration deviennent-elles invalides ?*

L'audit ciblé des fonctions `replay_engine.compute_integrity()` et `integrity_block._build_sign_payload()` confirme que **le payload signé contient uniquement des hashes de contenus** (`hash_request`, `hash_response`, `hash_document`, `signed_at`, `system_prompt_hash`, `history_hash`, `memory_snapshot_hash`). **Aucun chemin filesystem n'entre dans le payload.** La migration RDBMS ne peut donc pas invalider les signatures audit déjà émises. Cette garantie est documentée dans ADR-007 § "Garanties contractuelles" point 2.

### 10.5 Doctrine pre-commit-audit appliquée systématiquement

Le protocole interne de pre-commit-audit impose un protocole obligatoire en 3 phases avant tout `git commit` ou `git push` (relecture contradictoire du diff, checklist de défauts, re-audit total déclenché par tout défaut Critique/Important corrigé). Ce protocole a été appliqué sur les 3 commits post-25 avril : 9 défauts (1 Important + 2 Modérés + 6 Mineurs) cumulés, tous corrigés avant push, **0 défaut résiduel**. Les messages de commit Git portent une mention explicite de l'audit conformément à la phase 4 du protocole. Cet artefact constitue un actif valorisable au titre de la qualité processus.

### 10.6 Score de maturité technique — réévaluation interne

L'audit `07-scorecard-valorisation.md` (25 avril) chiffrait la maturité à 69/100. L'estimation interne post-5 mai (35 tests supplémentaires, 2 ADR supplémentaires, roadmap RDBMS livrée à 14 % avec P0 validé runtime, doctrine pre-commit-audit appliquée) place la maturité à **~72/100**. Cette réévaluation est un **estimé interne**, non un audit externe indépendant ; elle est proposée pour discussion. Le score 69/100 reste la valeur citée par la source canonique tant qu'elle n'est pas elle-même mise à jour.

### 10.7 Effet sur les fourchettes de valorisation

**Aucune modification**. Les fourchettes annoncées en section 6 (plancher 662 000 — 850 000 € ; cible 958 000 — 1 054 000 € ; offensif 1 150 000 — 1 350 000 €) restent inchangées. La borne haute du scénario défendable équilibré est toutefois **mieux défendue** par la fermeture du risque fail-silent (yENoyKIZ → ADR-006) et par la publication de la roadmap RDBMS (ADR-007).

### 10.8 Documents complémentaires à joindre

| Document | Rôle |
|---|---|
| `audit-hostile-valorisation/09-mise-a-jour-post-p0-yenoyikz.md` | Addendum auditable détaillant la mise à jour |
| `docs/adr/ADR-006-tool-io-integrity-contract.md` | Contrat I/O des tools |
| `docs/adr/ADR-007-postgres-pgvector-adoption.md` | Décision Postgres + pgvector |
| `docs/migration-rdbms/P0_PRE_REQUIS_INFRA.md` | Journal d'exécution P0 + 2 post-mortem |

Trois annexes optionnelles A13-A15 (captures `pytest`, manifeste SHA-256 du snapshot pré-P0) sont prêtes à être produites si Diag & Grow attaque le pipeline de tests ou la robustesse du processus de migration.
