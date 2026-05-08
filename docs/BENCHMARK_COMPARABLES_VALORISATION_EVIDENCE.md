<!-- markdownlint-disable MD060 MD032 -->

# References de marche et positionnement comparatif de l'actif Evidence

**Objet :** Eclairage comparatif de marche, destine a situer l'actif logiciel Evidence dans une categorie de valeur coherente avec ses caracteristiques techniques, fonctionnelles et strategiques.

**Date :** 17 avril 2026
**Prepare par :** Amine Mohamed
**Positionnement dans le dossier :** Ce chapitre s'insere apres la section 6 (Estimation du cout de reproduction) et avant la section 7 (Elements de preuve pour le commissaire aux apports) du Rapport Technique de Valorisation.

---

## 1. Objet et cadre methodologique du benchmark

### 1.1 Fonction des comparables dans un dossier de valorisation d'actif logiciel

Dans le cadre d'une evaluation d'actif incorporel destine a un apport en societe, le recours a des references de marche remplit une fonction d'eclairage complementaire. Il ne constitue pas a lui seul une methode de valorisation suffisante, et ne saurait se substituer a l'approche par les couts de reproduction ou a l'approche par les revenus futurs actualises (DCF). Son role est plus modeste et plus precis : il permet de verifier que la valorisation proposee s'inscrit dans un ordre de grandeur coherent avec les niveaux de valeur observes pour des actifs logiciels presentant des caracteristiques comparables.

Le commissaire aux apports, dans l'exercice de sa mission telle que definie par la doctrine de la Compagnie Nationale des Commissaires aux Comptes (CNCC), n'a pas pour objet de proceder lui-meme a l'evaluation. Il apprecie la valeur retenue par les parties et conclut qu'elle n'est pas surevaluee. L'apport de references de marche contribue a cette appreciation en fournissant un cadre de comparaison externe.

### 1.2 Limites inherentes a l'exercice

Plusieurs precautions s'imposent en preambule.

Les comparables de marche publiquement disponibles se rapportent majoritairement a des valorisations d'entreprises, non a des valorisations d'actifs isoles. Or, la valeur d'une entreprise englobe son equipe, sa base de clients, son positionnement commercial, sa tresorerie et ses perspectives de croissance, tandis que la valeur d'un actif logiciel repose sur ses qualites intrinseques, son cout de reproduction, sa capacite a generer des revenus futurs et sa differenciation technique. Ces deux perimetres ne doivent pas etre confondus.

En outre, les multiples de valorisation issus des levees de fonds ou des marches boursiers refletent des conditions de marche specifiques, un appetit pour le risque variable selon les cycles, et des effets de taille sans rapport direct avec un actif logiciel individuel. Les reprendre mecaniquement pour fonder la valeur d'un apport serait methodologiquement incorrect.

Le present benchmark s'en tient donc a un exercice de positionnement qualitatif et comparatif, qui vise a eclairer la categorie de valeur dans laquelle l'actif Evidence peut raisonnablement etre situe, sans en deduire mecaniquement un chiffre de valorisation.

---

## 2. Categorisation des actifs logiciels par densite de valeur

L'experience des transactions et des evaluations d'actifs logiciels permet de distinguer trois grandes categories, qui correspondent a des niveaux croissants de complexite technique, de criticite fonctionnelle et, in fine, de densite de valeur.

### 2.1 Categorie A — SaaS B2B standard

Le logiciel SaaS B2B standard designe un applicatif heberge, distribue par abonnement, qui adresse un besoin fonctionnel courant : gestion commerciale, comptabilite, gestion de projet, communication d'equipe, helpdesk. La logique economique repose sur le volume d'utilisateurs et la recurrence du revenu (ARR). Le cout de changement pour le client est generalement modere.

La complexite technique est reelle mais maitrisee. L'architecture repose sur des patterns eprouves (API REST, base relationnelle, frontend reactif, CI/CD standard). Le cout de reproduction d'un tel logiciel par une equipe competente est generalement estimable en 6 a 18 mois de travail d'equipe, selon l'etendue fonctionnelle.

En mars 2026, la mediane des multiples de valorisation des entreprises SaaS cotees se situe autour de 3,4x le chiffre d'affaires (source : Aventis Advisors, SaaS Valuation Multiples 2015-2026). En marche prive (M&A), la fourchette courante se situe entre 3x et 10x l'ARR, fortement segmentee par le taux de croissance, la profitabilite et la taille de l'entreprise (source : Axial, SaaS Multiples Guide 2026 ; ClearlyAcquired, EBITDA Multiples 2025-2026).

### 2.2 Categorie B — SaaS metier enrichi par IA

La deuxieme categorie designe les logiciels SaaS qui integrent une couche d'intelligence artificielle pour automatiser ou assister des taches metier specifiques : analyse documentaire, detection de fraude, scoring de risque, extraction d'information, suggestion de decisions. Le positionnement se situe a l'intersection du SaaS vertical et de l'IA appliquee.

La valeur ajoutee reside dans la specialisation metier et dans la capacite du modele a traiter des taches que l'humain realise moins efficacement. Le cout de reproduction est plus eleve que pour un SaaS standard, car il inclut l'acquisition de donnees d'entrainement, le tuning des modeles, et l'expertise domaine necessaire a la calibration.

En France, le marche de la LegalTech IA est evalue a environ 1,7 milliard de dollars (source : Research and Markets, France AI-Powered LegalTech SaaS Market). Le marche francais des RegTech representait 445,9 millions de dollars en 2024, en croissance annuelle de 10,8 % (source : Research and Markets, France RegTech Market). Apres correction des exces de 2021-2022, les multiples de valorisation dans ces segments se situent autour de 4,7x l'ARR, avec des plafonds a 12x pour les acteurs premium demontrant une croissance superieure a 40 % (source : Morgan Lewis, M&A in Fintech 2024).

Les solutions de cette categorie generent une prime de valorisation par rapport au SaaS standard, estimee entre 15 et 24 % lorsque l'integration IA produit un gain d'efficacite operationnelle mesurable (source : ClearlyAcquired, EBITDA Multiples 2025-2026).

### 2.3 Categorie C — Infrastructure de decision, d'orchestration et de confiance

La troisieme categorie regroupe les plateformes logicielles qui ne se contentent pas d'assister une tache, mais qui constituent une infrastructure de decision : orchestration d'agents autonomes, validation croisee de resultats, tracabilite des raisonnements, auditabilite des decisions, gouvernance des modeles, conformite reglementaire embarquee.

Ces actifs se distinguent par plusieurs proprietes structurantes :

La criticite fonctionnelle est elevee. Le logiciel intervient dans la chaine de decision, pas seulement dans la chaine de production. Une defaillance ou un biais a des consequences directes en termes de responsabilite juridique, de conformite reglementaire ou de confiance client.

La profondeur d'architecture est significative. L'actif repose sur une combinaison de modules interdependants : moteur de consensus, routage deterministe, pipeline de conformite, journalisation cryptographique, mecanismes de revue humaine, rejeu de session. Cette stratification rend la reproduction couteuse et lente.

Le cout de changement est eleve. L'integration de l'outil dans les processus du client cree une dependance fonctionnelle qui depasse le simple abonnement SaaS. Le retrait de la solution implique la reconstruction de la chaine de confiance.

Le marche de l'orchestration IA est en forte croissance : 11,65 milliards de dollars en 2025, avec une projection a 60,34 milliards de dollars d'ici 2034, soit un taux de croissance annuel compose de 20,05 % (source : Fortune Business Insights, AI Orchestration Market 2026-2034). Le marche de la gouvernance IA, plus specifiquement, passe de 1,87 milliard en 2025 a 2,38 milliards en 2026, avec une projection a 6,23 milliards d'ici 2030 et un TCAC de 27,2 % (source : Research and Markets, AI Governance Platform Market Report 2026).

Les plateformes de reference dans ce segment — IBM watsonx.governance, Credo AI, Holistic AI, Bifrost — se positionnent sur la capacite a appliquer des controles en temps reel dans le pipeline d'inference, et non sur la simple documentation de conformite. Le marche delaisse progressivement les outils de reporting statique pour privilegier les solutions d'enforcement embarque (source : Ethyca, Best AI Governance Platforms 2026 ; Maxim.ai, Top 5 AI Governance Platforms 2026).

Les multiples de valorisation pour les plateformes d'infrastructure IA de premier plan atteignent la fourchette mediane des 20x le chiffre d'affaires (source : Medium/ValuStrat, AI Startup Valuation 2026). Cette prime s'explique par la profondeur d'integration, la criticite fonctionnelle et les barrieres a l'entree liees a la structuration technique de l'actif.

---

## 3. Tableau comparatif

Le tableau ci-dessous positionne les trois categories d'actifs logiciels sur les criteres pertinents pour une evaluation d'actif incorporel, et situe Evidence dans cette grille.

| Critere | SaaS B2B standard | SaaS metier enrichi par IA | Infrastructure de decision / orchestration / confiance | Evidence |
|---|---|---|---|---|
| **Logique economique dominante** | Volume d'utilisateurs, recurrence | Efficacite metier, gain de productivite | Criticite decisionnelle, gouvernance, confiance | Gouvernance de decisions IA en environnement reglemente |
| **Complexite / structuration** | Moderee (patterns eprouves) | Elevee (modeles + domaine) | Tres elevee (modules interdependants, consensus, audit) | Tres elevee : apports A-P documentes, ~137 400 LOC proprietaires, architectures fail-closed |
| **Dependance a l'execution humaine** | Forte (outil d'assistance) | Moyenne (automatisation partielle) | Faible a moyenne (decision assistee avec garde-fous) | Faible : pipeline deterministe, consensus multi-LLM, revue humaine sur exception |
| **Valeur percue par le client** | Operationnelle (efficacite) | Fonctionnelle (qualite de resultat) | Strategique (confiance, conformite, preuve) | Strategique : auditabilite, conformite AI Act/RGPD, integrite cryptographique |
| **Criticite metier / reglementaire** | Faible a moyenne | Moyenne a elevee | Elevee a critique | Critique : domaines juridique, medical, financier avec contrats de surete |
| **Potentiel de differenciation** | Faible (commoditisation) | Moyen (donnees, modeles) | Eleve (architecture, IP, barrieres techniques) | Eleve : anteriorite PRISM, pipeline juridique ex nihilo, moteur de consensus proprietaire |
| **Potentiel de recurrence / integration** | Eleve (abonnement) | Eleve (abonnement + usage) | Tres eleve (integration profonde, lock-in fonctionnel) | Tres eleve : integration dans la chaine de decision, deploiement Docker production |
| **Capacite a justifier une prime de valorisation** | Faible (multiples standards) | Moderee (prime IA 15-24 %) | Elevee (multiples superieurs, barrieres a l'entree) | Coherente avec la categorie C |
| **Multiples de reference (entreprise, indicatif)** | 3x-10x ARR (mediane 3,4x) | 4,7x-12x ARR | Fourchette mediane 20x (plateformes leaders) | Non applicable directement (actif, pas entreprise) |

---

## 4. Positionnement d'Evidence dans cette grille

### 4.1 Caracteristiques rapprochant Evidence de la categorie C

L'analyse des proprietes techniques et fonctionnelles d'Evidence, telles que documentees dans le Rapport Technique de Valorisation et verifiees par l'audit hostile interne, permet d'identifier plusieurs caracteristiques qui rapprochent cet actif de la categorie des infrastructures de decision et de confiance.

**Architecture multi-agents avec consensus deterministe.** Evidence ne delegue pas la prise de decision a un modele de langage unique. Le systeme PRISM, issu d'un projet anterieur, orchestre plusieurs modeles qui votent independamment. Un arbitre consolide les reponses selon un protocole fail-closed : en cas d'absence de consensus, le systeme refuse de repondre. Cette architecture est structurellement plus proche d'un systeme de vote distribue que d'un chatbot.

**Pipeline de conformite embarque.** Le framework Evidence genere automatiquement des rapports d'audit avec integrite cryptographique (SHA-256 + HMAC obligatoire), taxonomie des sources, grille de conformite AI Act (articles 9, 13, 14, 17) et RGPD (article 30). Cette capacite est nativement integree, non ajoutee en surcouche.

**Tracabilite et auditabilite.** Le moteur de rejeu (replay engine) permet de reproduire une session de decision a posteriori. Le workflow de revue humaine formalise l'intervention humaine sur les decisions critiques. Le registre de risques dynamique maintient un scoring en temps reel. Ces trois modules constituent un pipeline de preuve d'audit complet, adressant directement la critique recurrente de l'auto-evaluation sans validation externe.

**Routage deterministe.** Le routeur de criticite fonctionne par hashing et tables de mots-cles, sans recours a un modele de langage dans la boucle de routage. Cette propriete le rend resistant aux injections et previsible dans son comportement, qualite recherchee dans les environnements reglementaires.

**Specialisation metier verticale.** Les modules Legal-Safe (16 556 LOC, pipeline complet d'ingestion juridique), le contrat medical (garde-fous et kill tests) et le pipeline strategique ne sont pas des couches d'abstraction generiques. Ils integrent une expertise domaine qui necessiterait, pour etre reproduite, l'intervention de consultants specialises en plus des developpeurs.

### 4.2 Nuances et reservations

Le positionnement dans la categorie C doit etre nuance par plusieurs observations.

Evidence est un actif logiciel, pas une entreprise. Des factures DICA FRANCE sont disponibles à annexer et établissent un revenu récurrent de **1 500 €/mois**, soit **18 000 €/an en run-rate annualisé** ; des pièces de pilotes sont par ailleurs disponibles concernant Centrale Lille / Chaire Construction 4.0 / Pr Zoubeir Lafhaj ainsi que l'écosystème Le Tarmac by inovallée. Cette traction initiale est un signal positif d'exploitabilité, mais elle ne constitue pas encore une base de clients diversifiée, un historique de revenu récurrent significatif ni des métriques d'usage auditées. Les multiples de marche cites pour la categorie C se rapportent a des entreprises en activite, et ne peuvent pas etre transposes mecaniquement a un actif en debut de commercialisation.

Amine Mohamed est inventeur de PRISM et de KOREV Evidence. 4 brevets PRISM sont en cours et seront présentés séparément aux commissaires aux apports ; le consensus anti-hallucination fait partie du périmètre breveté. Ce point renforce le positionnement technique de la brique PRISM, mais ne doit pas être transposé mécaniquement à Evidence sans documenter le titulaire, le périmètre, les dates de dépôt et la chaîne de droits PRISM -> Evidence.

La maturite technique, telle que mesuree par l'audit hostile mis a jour le 17 avril 2026, se situe a 69/100 (en progression par rapport a 58,75/100 avant les corrections P0). Des axes d'amelioration significatifs subsistent (modules monolithiques, CI incomplete, schema de donnees absent, API reference absente, dependance a l'inventeur). Le potentiel post-remediation est estime a 76/100.

L'absence de metriques d'usage reel auditees (latence, fiabilite, charge) et de validation par un audit securite externe constitue un point d'attention pour un evaluateur prudent. Les confirmations externes disponibles pour les pilotes doivent etre annexees et indexees pour etre prises en compte.

Ces elements ne remettent pas en cause le positionnement de l'actif dans la categorie C du point de vue de ses caracteristiques techniques. Ils appellent en revanche une prudence dans la transposition des ordres de grandeur de marche a la valorisation de l'actif lui-meme.

---

## 5. Implications pour la coherence de la valorisation

### 5.1 Le cout de reproduction comme plancher de valeur

L'estimation du cout de reproduction, detaillee en section 6 du Rapport Technique, situe la valeur de l'actif entre 662 000 euros (hypothese conservatrice, productivite haute) et 1 889 600 euros (hypothese haute, benchmark strict), avec une estimation mediane de 1 197 950 euros. Ces estimations reposent sur les benchmarks industriels COCOMO II, ISBSG et Capers Jones, appliques de maniere coherente a la decomposition du code proprietaire.

Dans une logique de valorisation, le cout de reproduction represente un plancher. Il mesure l'effort minimal qu'il faudrait consentir pour recreer un actif fonctionnellement equivalent, sans tenir compte de la valeur d'usage, de la differenciation, de l'anteriorite ni du positionnement strategique.

### 5.2 Le benchmark de marche comme plafond indicatif

Le positionnement d'Evidence dans la categorie C (infrastructure de decision et de confiance) suggere que la valeur de l'actif, s'il etait exploite commercialement dans des conditions favorables, pourrait atteindre des niveaux significativement superieurs au cout de reproduction. Les plateformes de cette categorie beneficient de multiples de valorisation 3 a 6 fois superieurs a ceux d'un SaaS standard, ce qui reflate la densite de valeur liee a la criticite fonctionnelle, aux barrieres techniques et au potentiel d'integration profonde.

Ce constat ne signifie pas que la valorisation d'Evidence doive etre fixee par reference a ces multiples. Il signifie que l'estimation par les couts de reproduction, situee dans une fourchette de 662 000 a 1 889 600 euros, est compatible avec le positionnement de l'actif dans un segment de marche ou les niveaux de valeur sont structurellement eleves.

### 5.3 Synthese

L'articulation entre les deux approches permet de formuler les constats suivants :

La valorisation par les couts de reproduction (fourchette de 662 000 a 1 889 600 euros) ne presente pas de caractere excessif au regard des references de marche pour des actifs logiciels de la categorie C.

Le positionnement technique d'Evidence — architecture multi-agents, consensus deterministe, pipeline de conformite, auditabilite native, specialisation metier — le distingue objectivement d'un SaaS standard et justifie son rapprochement avec les plateformes d'infrastructure de decision.

La prudence commande de retenir la valeur par les couts de reproduction comme reference principale, le benchmark de marche n'intervenant qu'a titre d'eclairage de coherence, conformement a la hierarchie methodologique attendue par un commissaire aux apports.

---

## 6. Limites methodologiques et precautions d'interpretation

Ce chapitre doit etre lu en gardant a l'esprit les limites suivantes, que le redacteur expose en toute transparence.

### 6.1 Distinction entre valorisation d'entreprise et valorisation d'actif

Les multiples de marche cites dans ce benchmark se rapportent a des valorisations d'entreprises (EV/Revenue, EV/EBITDA, multiples d'ARR). La valorisation d'un actif logiciel isole obeit a une logique differente. Un actif n'a pas de chiffre d'affaires propre, pas de base de clients, pas de structure operationnelle. Sa valeur depend de ses qualites intrinseques et du contexte dans lequel il sera exploite. La transposition mecanique d'un multiple d'entreprise a un actif isole serait methodologiquement infondee.

### 6.2 Distinction entre valeur de marche, valeur d'usage et valeur strategique

La valeur de marche est le prix qu'un acquereur paierait dans une transaction entre parties independantes et informees. La valeur d'usage est la valeur que l'actif represente pour un exploitant specifique, en fonction de son modele economique et de ses synergies. La valeur strategique integre des considerations de positionnement concurrentiel, de time-to-market et de blocage de concurrents. Ces trois notions ne se confondent pas et ne doivent pas etre amalgamees dans un dossier de valorisation.

### 6.3 Volatilite des multiples dans le secteur IA

Le secteur de l'intelligence artificielle connait, depuis 2023, une forte volatilite de valorisations. Les multiples ont atteint des niveaux exceptionnellement eleves en 2021-2022 (superieurs a 10x l'ARR, voire 30x pour certains acteurs), avant de subir une correction significative en 2023-2024. Le marche montre des signes de stabilisation en 2025-2026, mais reste expose a des retournements. Les multiples cites dans le present document refletent les conditions observees a la date de redaction et sont susceptibles d'evolution.

### 6.4 Absence de transactions directement comparables

Il n'existe pas, a notre connaissance, de transaction publique portant sur un actif logiciel strictement comparable a Evidence (plateforme multi-agents, consensus deterministe, pipeline juridique, auditabilite native, pour un marche de professions reglementees). Les comparaisons etablies dans ce chapitre reposent sur des rapprochements par analogie de categorie, non sur des transactions identiques. Un commissaire aux apports devra en tenir compte dans l'appreciation de la robustesse de ce benchmark.

### 6.5 Biais potentiels

Le present benchmark est etabli par l'apporteur et inventeur du projet, qui a un interet direct dans la valorisation. Cette situation est courante dans les dossiers d'apport de logiciels developpes en interne, mais elle doit etre signalee explicitement. Le commissaire aux apports et Diag & Grow exerceront leur jugement professionnel independant sur la pertinence des rapprochements proposes.

### 6.6 Ce qu'un commissaire aux apports attend

Dans la doctrine professionnelle, le commissaire aux apports attend une articulation entre :
- la qualite documentee de l'actif (rapport technique, audit, tests),
- la methode principale de valorisation (couts de reproduction, appuyee sur des benchmarks industriels),
- un eclairage complementaire par des references de marche (le present chapitre),
- la differenciation technique de l'actif par rapport aux alternatives de marche,
- une appreciation de la maturite et des limites de l'actif (score d'audit, axes de remediation),
- et une demonstration d'exploitabilite (architecture deployable, tests executables, documentation technique).

Le present chapitre s'inscrit dans le troisieme de ces elements. Il ne se substitue a aucun des autres.

---

## 7. References et sources

| Source | Date | Donnee | Utilisation dans ce chapitre |
|---|---|---|---|
| Aventis Advisors, SaaS Valuation Multiples 2015-2026 | Mars 2026 | Mediane EV/Revenue 3,4x (SaaS cotees) | Categorie A, reference de multiples |
| Axial, SaaS Multiples Guide 2026 | 2026 | Fourchette 3x-10x ARR (M&A prive) | Categorie A, fourchette privee |
| ClearlyAcquired, EBITDA Multiples 2025-2026 | 2025-2026 | Mediane 22,4x EBITDA, prime IA 15-24 % | Categories A et B |
| Research and Markets, France RegTech Market | 2024 | 445,9 M$, croissance 10,8 %/an | Categorie B, marche francais |
| Research and Markets, France AI-Powered LegalTech SaaS | 2024-2026 | Marche evalue a ~1,7 Md$ | Categorie B, marche francais |
| Morgan Lewis, M&A in Fintech | 2024 | Multiples 4,7x ARR (post-correction) | Categorie B |
| Fortune Business Insights, AI Orchestration Market | 2026-2034 | 11,65 Md$ (2025) → 60,34 Md$ (2034), TCAC 20,05 % | Categorie C, taille du marche |
| Research and Markets, AI Governance Platform Market | 2026 | 1,87 Md$ (2025) → 6,23 Md$ (2030), TCAC 27,2 % | Categorie C, gouvernance IA |
| ValuStrat / Medium, AI Startup Valuation 2026 | 2026 | Fourchette mediane 20x (plateformes leaders) | Categorie C, reference illustrative faible a ne pas utiliser seule |
| Deloitte France, IA et M&A | 2025-2026 | Due diligence IA, actifs IA en M&A | Methodologie, contexte |
| AMF, Adoption IA marches financiers | 2025 | 90 % des acteurs financiers FR utilisent l'IA | Contexte de marche |
