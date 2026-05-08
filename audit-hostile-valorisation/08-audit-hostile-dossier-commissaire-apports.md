<!-- markdownlint-disable MD060 -->

# 08 — Audit hostile du dossier commissaire aux apports

**Projet :** KOREV Evidence  
**Date :** 25 avril 2026  
**Objet :** relecture contradictoire du dossier destiné au commissaire aux apports et au cabinet d'ingénieurs Diag & Grow.  
**Documents relus :**

- `docs/DOSSIER_COMMISSAIRE_APPORTS_EVIDENCE.md`
- `docs/RAPPORT_TECHNIQUE_VALORISATION_EVIDENCE.md`
- `docs/BENCHMARK_COMPARABLES_VALORISATION_EVIDENCE.md`
- `audit-hostile-valorisation/01` à `07`
- `tests/README_tests.md`

---

## 1. Verdict hostile

Le dossier est **présentable au commissaire aux apports et à Diag & Grow sous réserve d'annexes probatoires effectivement jointes**. La structure est maintenant défendable : elle distingue l'actif logiciel de l'entreprise, identifie la base open-source Agent Zero, privilégie la méthode par coût de reproduction, rattache PRISM et Evidence à leur inventeur Amine Mohamed, et reconnaît les limites de maturité.

Le risque principal n'est plus la cohérence narrative ; il est **probatoire**. Les affirmations qui renforcent le plus la valorisation — factures DICA FRANCE, pilotes Centrale Lille, accompagnement Le Tarmac, 5 ans de R&D, et 4 brevets PRISM en cours — doivent être annexées et indexées. Avec ces pièces, le haut de fourchette défendable devient beaucoup plus solide ; sans index clair, Diag & Grow devra retraiter les preuves manuellement et pourra appliquer une décote de prudence.

---

## 2. Défauts trouvés et traitement

| DEF | Sévérité | Constat hostile | Correction / statut |
|---|:---:|---|---|
| DEF-1 | Important | Le dossier utilisait `ARR` alors qu'un seul client facturé à 1 500 €/mois ne suffit pas à qualifier un ARR diversifié et audité. | Corrigé : remplacement par `revenu récurrent annualisé` / `run-rate annualisé`. |
| DEF-2 | Important | Les factures DICA FRANCE étaient présentées comme traction, mais sans lister précisément les pièces attendues. | Corrigé : exigence d'annexer factures, contrat/devis ou bon de commande, preuves de paiement disponibles, périmètre de service. |
| DEF-3 | Important | Le scénario offensif pouvait être lu comme une hausse automatique liée au revenu DICA. | Corrigé : le scénario offensif reste conditionnel, non automatique, et dépend d'un pack probatoire renforcé. |
| DEF-4 | Modéré | La ligne PRISM parlait encore de réduction d'hallucination, formulation attaquable sans métrique d'erreur. | Corrigé : reformulation en validation multi-arbitres et refus fail-closed en cas de consensus insuffisant. |
| DEF-5 | Modéré | Les pilotes Centrale Lille / Le Tarmac étaient des signaux crédibles mais devaient être rattachés à des pièces. | Corrigé : statut probatoire explicitement conditionné à emails, protocole de test, compte rendu, convention ou attestation à annexer. |
| DEF-6 | Modéré | Le benchmark parlait d'absence d'ARR mesurable alors que la traction DICA existe. | Corrigé : mention du run-rate annualisé de 18 000 €/an, tout en refusant une transposition mécanique des multiples. |
| DEF-7 | Mineur | Orthographe publique du professeur : risque `Lahfaj` vs `Lafhaj`. | Corrigé dans les documents exposés : `Zoubeir Lafhaj`. |
| DEF-8 | Important | Risque de présenter les 4 brevets PRISM comme des brevets Evidence. | Corrigé : les documents indiquent que les brevets concernent PRISM ; Amine Mohamed est présenté comme inventeur de PRISM et d'Evidence ; leur effet sur Evidence dépend d'une chaîne de droits PRISM -> Evidence. |
| DEF-9 | Important | Le dossier pouvait être lu comme une note adressée à l'apporteur plutôt qu'aux évaluateurs. | Corrigé : ajout des destinataires `commissaire aux apports` et `Diag & Grow`, et reformulation du principe directeur autour de la vérification indépendante. |

**Défauts critiques résiduels :** aucun dans les documents corrigés.  
**Défauts importants résiduels :** aucun dans la rédaction, sous réserve que les annexes annoncées comme disponibles soient effectivement jointes, numérotées et cohérentes avec les montants et dates cités.

---

## 3. Annexes indispensables avant transmission

| Annexe | Priorité | Pourquoi c'est indispensable |
|---|:---:|---|
| A1 — Factures DICA FRANCE | P0 | Prouve le revenu récurrent de 1 500 €/mois. Sans cette pièce, la traction redevient déclarative. |
| A2 — Preuves de paiement DICA FRANCE disponibles | P0/P1 | Transforme la facturation en revenu encaissé. Si certaines échéances ne sont pas encore encaissées, le préciser clairement. |
| A3 — Contrat, devis signé, bon de commande ou email de commande DICA FRANCE | P0 | Démontre que la facturation repose sur une relation commerciale réelle et non sur une facture isolée. |
| A4 — Périmètre de service DICA FRANCE | P1 | Permet à Diag & Grow de comprendre ce qui est vendu : licence, service, intégration, maintenance, accès plateforme. |
| A5 — Email ou attestation Centrale Lille / Chaire Construction 4.0 / Pr Zoubeir Lafhaj | P0 | Prouve le test terrain et évite l'attaque "nom prestigieux cité sans preuve". |
| A6 — Protocole ou compte rendu de test Centrale Lille | P1 | Transforme un signal relationnel en preuve d'usage. |
| A7 — Preuve Le Tarmac by inovallée | P0/P1 | Convention, email d'acceptation, fiche incubé ou attestation. |
| A8 — Pièces R&D pré-repository | P1 | Rend défendable la thèse des 5 ans de R&D et l'antériorité de conception PRISM/Evidence. |
| A9 — Dossier des 4 brevets PRISM en cours | P0/P1 | Récépissés ou preuves de dépôt, dates, inventeurs, titulaires, titres provisoires, revendications synthétiques ; préciser le brevet couvrant le consensus anti-hallucination. |
| A10 — Chaîne de droits PRISM -> Evidence | P0 | Cession, licence, apport ou autorisation d'exploitation. Sans cette pièce, les brevets PRISM ne peuvent pas renforcer directement la valorisation d'Evidence. |
| A11 — Collecte tests dans l'environnement Python cible | P1 | Le `pytest --collect-only` local Python 3.9 échoue partiellement ; il faut une collecte propre dans l'environnement supporté. |
| A12 — Build Docker ou capture CI | P1 | Réduit l'objection d'industrialisation incomplète. |

---

## 4. Attaques probables de Diag & Grow et réponses

### Attaque 1 — "1 500 €/mois ne justifie pas 1 M€ de valorisation"

**Réponse :** exact si la méthode retenue était un multiple de revenus. Ce n'est pas le cas. La valeur principale repose sur le coût de reproduction d'un actif logiciel complexe. Le revenu DICA n'est pas le moteur du chiffre ; il réduit le risque commercial et soutient le haut de fourchette.

### Attaque 2 — "Vous citez Centrale Lille et Le Tarmac sans preuve"

**Réponse :** ces éléments doivent être utilisés avec annexe. Le dossier les classe comme pilotes/signaux terrain à documenter par emails, attestations, conventions, protocole ou compte rendu. Leur effet est probatoire, pas une base de calcul par multiples.

### Attaque 3 — "Agent Zero open-source porte l'essentiel de la valeur"

**Réponse :** la base Agent Zero est reconnue et exclue de la valeur propriétaire. La valeur repose sur les couches différenciantes : PRISM, Evidence, Legal-Safe, sécurité multi-tenant, audit-proof pipeline, tests, documentation et industrialisation.

### Attaque 4 — "La conformité AI Act est auto-évaluée"

**Réponse :** exact. Le dossier ne doit jamais prétendre à une certification AI Act. Il parle d'un pipeline d'auditabilité, de traçabilité et de grilles de conformité auto-évaluées. La limite est explicitement assumée.

### Attaque 5 — "Le scénario offensif est trop haut"

**Réponse :** ne pas le présenter comme valeur retenue. Le scénario offensif est une borne de négociation conditionnelle : factures, pilotes, R&D, tests/build et dépendances documentées. La valeur cible reste le scénario défendable équilibré.

### Attaque 6 — "Les brevets sont PRISM, pas Evidence"

**Réponse :** exact. Ils doivent être présentés comme portefeuille PRISM en cours, pas comme brevets Evidence. Amine Mohamed est inventeur de PRISM et d'Evidence ; les brevets renforcent la valorisation Evidence pour la brique PRISM intégrée si le droit d'usage PRISM -> Evidence est annexé.

---

## 5. Position de valorisation recommandée

| Position | Valeur | Usage |
|---|---:|---|
| Plancher prudent | 662 000 € à 850 000 € | Si les annexes commerciales et R&D sont jugées insuffisantes après revue. |
| Valeur cible défendable | 958 000 € à 1 054 000 € | À présenter comme référence principale. Bas de fourchette en posture neutre, haut de fourchette défendable si factures DICA, preuves pilotes et preuves techniques sont annexées. |
| Borne offensive | 1 150 000 € à 1 350 000 € | À garder pour négociation, avec dossier brevets PRISM + chaîne de droits, pas comme valeur principale sans rapport d'expert complémentaire. |

---

## 6. Red flags à ne pas laisser dans la version remise

- Ne pas employer `ARR` pour DICA FRANCE sauf si un contrat d'abonnement annuel ou mensuel récurrent est annexé et que le terme est défini.
- Ne pas écrire que Centrale Lille, la Chaire Construction 4.0, le Pr Zoubeir Lafhaj ou Le Tarmac "valident" Evidence sans attestation explicite.
- Ne pas présenter les comparables de marché comme base de calcul. Ils ne sont qu'un test de cohérence.
- Ne pas dire "conformité AI Act certifiée". Dire "pipeline de conformité et auditabilité".
- Ne pas chiffrer séparément les 5 ans de R&D sans revue des pièces datées annexées.
- Ne pas présenter les 4 brevets PRISM comme des brevets Evidence. Dire : "portefeuille PRISM en cours, lié à la brique consensus intégrée, sous réserve de chaîne de droits".
- Ne pas livrer le dossier sans un tableau d'annexes numérotées.

---

## 7. Checklist de verrouillage avant envoi

1. Ajouter un sommaire d'annexes avec identifiants A1 à A12.
2. Joindre les factures DICA FRANCE et les preuves d'encaissement disponibles.
3. Joindre au moins un écrit externe pour Centrale Lille / Chaire Construction 4.0.
4. Joindre au moins un écrit externe pour Le Tarmac by inovallée.
5. Joindre les récépissés ou preuves de dépôt des 4 brevets PRISM en cours.
6. Joindre la chaîne de droits PRISM -> Evidence.
7. Recalculer les métriques Git au commit final transmis.
8. Faire une collecte tests dans l'environnement Python cible ou documenter explicitement l'échec Python 3.9.
9. Vérifier que toutes les valeurs financières sont cohérentes : coût brut, décote, valeur nette, scénario cible.
10. Ajouter une page "Limites connues" plutôt que laisser le commissaire les découvrir.

---

## 8. Conclusion hostile

Le dossier est désormais **sérieux et défendable**, mais il ne doit pas être transmis comme simple narration. Il doit être transmis comme **dossier probatoire** : rapport + audit + annexes numérotées, destiné au commissaire aux apports et à Diag & Grow. La meilleure stratégie n'est pas de pousser immédiatement la borne offensive ; c'est de sécuriser le scénario autour d'1 M€ avec des preuves commerciales, R&D, PRISM et techniques, puis de laisser la borne haute comme marge de négociation.
