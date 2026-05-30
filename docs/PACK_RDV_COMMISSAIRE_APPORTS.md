<!-- markdownlint-disable MD060 MD032 MD013 MD029 MD028 -->

# Pack RDV — Commissaire aux apports & cabinet d'ingenieurs Diag & Grow

**Destinataires :** commissaire aux apports et cabinet d'ingenieurs Diag & Grow.
**Apporteur / inventeur :** Amine Mohamed, inventeur de PRISM et de KOREV Evidence.
**Objet :** dossier probatoire d'evaluation des apports en nature lies a la plateforme KOREV Evidence.
**Date du Pack :** 25 avril 2026 (etat initial) — **revision 5 mai 2026** (3 commits posterieurs : `de8b9c7e`, `b11b4d99`, `0d0a35da`). Le matin du RDV, suivre la procedure de la section 7 pour rafraichir les chiffres Git.
**HEAD Git verifie :** `0d0a35da` au 5 mai 2026 (etat 25 avril : `7a7abd6a`).

> Ce Pack n'est pas un livrable supplementaire qui resumerait les autres. C'est une **carte de lecture** et un **index probatoire** qui pointe vers les documents canoniques. Aucun chiffre n'est duplique : la source canonique est indiquee pour chaque element. En cas d'ecart entre un document et ce Pack, c'est la **source canonique** qui fait foi.

> **Note de revision 5 mai 2026 :** trois commits ont ete pousses depuis l'etat initial du 25 avril. Leurs effets sont consignes dans `audit-hostile-valorisation/09-mise-a-jour-post-p0-yenoyikz.md` (addendum) et reflectes dans la section 10 du dossier commissaire. La presente revision met a jour le HEAD, la liste des ADR (S8 = ADR-001 a 007), ajoute trois documents techniques de soutien (S15-S17), trois annexes optionnelles (A13-A15) et la trace d'audit hostile pre-commit appliquee sur les commits posterieurs. **Aucune modification de fourchettes de valorisation, ni de chiffres deja figes.**

---

## 1. Sommaire de lecture

### 1.1 Ordre recommande pour le commissaire aux apports (lecture courte, ~30 min)

1. `docs/DOSSIER_COMMISSAIRE_APPORTS_EVIDENCE.md` — synthese 1 page + scenarios + section 10 (mise a jour post-25 avril)
2. Section 5 du present Pack — index des chiffres cles
3. Section 4 du present Pack — sommaire d'annexes A1-A12 (+ A13-A15 optionnelles)
4. `audit-hostile-valorisation/08-audit-hostile-dossier-commissaire-apports.md` — preuve de transparence au 25 avril (132 lignes)
5. `audit-hostile-valorisation/09-mise-a-jour-post-p0-yenoyikz.md` — addendum auditable post-25 avril (287 lignes)

### 1.2 Ordre recommande pour Diag & Grow (lecture longue, ~2-3 h)

1. `docs/DOSSIER_COMMISSAIRE_APPORTS_EVIDENCE.md` (incluant section 10) — point d'entree
2. `docs/RAPPORT_TECHNIQUE_VALORISATION_EVIDENCE.md` — preuves chiffrees detaillees (689 lignes)
3. Section 5 du present Pack — verifier coherence chiffres entre documents
4. `docs/BENCHMARK_COMPARABLES_VALORISATION_EVIDENCE.md` — eclairage de marche (204 lignes)
5. `audit-hostile-valorisation/01-executive-summary.md` (81 lignes) puis `07-scorecard-valorisation.md` (273 lignes) — audit interne et notation
6. `audit-hostile-valorisation/08-audit-hostile-dossier-commissaire-apports.md` — audit dedie au dossier (snapshot 25 avril)
7. `audit-hostile-valorisation/09-mise-a-jour-post-p0-yenoyikz.md` — addendum auditable des 3 commits posterieurs
8. Documents techniques de soutien (section 3 du present Pack) en consultation libre, en particulier S15 (ADR-006), S16 (ADR-007) et S17 (journal P0)

### 1.3 Si lecture tres courte (~10 min)

- Section 5 du present Pack uniquement (index des chiffres cles).
- Puis section 1 du dossier commissaire (position defendable en une page).

---

## 2. Documents principaux du Pack (a remettre en mains propres)

| # | Document | Lignes | Role | Destinataire prioritaire |
|---|---|---|---|---|
| D1 | `docs/PACK_RDV_COMMISSAIRE_APPORTS.md` | ce fichier | Carte de lecture, index, sommaire annexes | Les deux |
| D2 | `docs/DOSSIER_COMMISSAIRE_APPORTS_EVIDENCE.md` | 240 (avec section 10) | Synthese 1 page + audit hostile + scenarios + mise a jour post-25 avril | Commissaire |
| D3 | `docs/RAPPORT_TECHNIQUE_VALORISATION_EVIDENCE.md` | 689 | Preuves chiffrees detaillees (apports, LOC, COCOMO) | Diag & Grow |
| D4 | `docs/BENCHMARK_COMPARABLES_VALORISATION_EVIDENCE.md` | 204 | Eclairage de marche, categorie C | Les deux |
| D5 | `audit-hostile-valorisation/08-audit-hostile-dossier-commissaire-apports.md` | 132 | Audit hostile interne du dossier (snapshot 25 avril, non modifie) | Les deux |
| D6 | `audit-hostile-valorisation/09-mise-a-jour-post-p0-yenoyikz.md` | 287 | Addendum auditable des 3 commits posterieurs au 25 avril | Les deux |
| D7 | Sommaire d'annexes A1-A12 + A13-A15 optionnelles (section 4 du present Pack) | — | Index probatoire | Les deux |

---

## 3. Documents techniques de soutien (cle USB ou PDF, pas forcement imprimes)

| # | Document | Lignes | Role |
|---|---|---|---|
| S1 | `audit-hostile-valorisation/01-executive-summary.md` | 81 | Verdict global et niveau de maturite |
| S2 | `audit-hostile-valorisation/02-cartographie-technique.md` | 255 | Cartographie technique du depot |
| S3 | `audit-hostile-valorisation/03-audit-qualite-hostile.md` | 282 | Audit qualite contradictoire |
| S4 | `audit-hostile-valorisation/04-bilan-documentation.md` | 161 | Bilan documentaire |
| S5 | `audit-hostile-valorisation/05-angle-morts-et-decote-potentielle.md` | 189 | Angles morts, decote potentielle |
| S6 | `audit-hostile-valorisation/06-plan-de-remediation-priorise.md` | 223 | Plan de remediation P0/P1/P2 |
| S7 | `audit-hostile-valorisation/07-scorecard-valorisation.md` | 273 | Scorecard 10 dimensions, score 69/100 |
| S8 | `docs/adr/ADR-001` a `ADR-007` | ~510 cumules | **7 decisions architecturales** (ADR-006 contrat I/O des tools ; ADR-007 adoption Postgres + pgvector) |
| S9 | `docs/ARCHITECTURE_C4_DIAGRAMS.md` | 251 | Diagrammes C4 a 3 niveaux |
| S10 | `docs/GLOSSARY.md` | 91 | Glossaire 30+ termes proprietaires |
| S11 | `SECURITY.md` | 119 | Politique de securite, divulgation responsable |
| S12 | `docs/DEVELOPER_ONBOARDING_ARCHITECTURE_GUIDE.md` | 1 196 | Guide d'onboarding (reduit le bus factor) |
| S13 | `LICENSE` + `legal/THIRD_PARTY_NOTICES.txt` | — | Licence MIT et notices tierces |
| S14 | `docs/preuves-execution/PREUVES_TECHNIQUES_EXECUTION.md` + dossier de preuves brutes (A11_pytest_collect_only.txt, B_pytest_doc_quality.txt, C_git_metrics.txt, D_volumetrie_code.txt, E_docker_inventory.txt, F_decomposition_diff.txt, run_docker_proof.sh) | ~700 lignes + 8 fichiers | **Preuves d'execution figees au 28 avril 2026** (annexes A11 et A12) |
| S15 | `docs/adr/ADR-006-tool-io-integrity-contract.md` | 69 | **Contrat d'integrite I/O des tools** (post-incident yENoyKIZ, commit `de8b9c7e`) |
| S16 | `docs/adr/ADR-007-postgres-pgvector-adoption.md` | 212 | **Roadmap migration RDBMS** Postgres + pgvector en 7 phases (commit `b11b4d99`) |
| S17 | `docs/migration-rdbms/P0_PRE_REQUIS_INFRA.md` | 239 | Journal d'execution P0 + 2 post-mortem (incident `--remove-orphans`, DEF-8 restore fail-silent) |

---

## 4. Sommaire d'annexes probatoires (a constituer J-1)

### 4.1 Tableau d'annexes A1 a A12

Numerotation a reporter sur la couverture de chaque piece annexee. Cocher la case "Joint" au moment de la remise.

| ID | Annexe | Priorite | Joint ? | Reference dossier |
|---|---|:---:|:---:|---|
| A1 | Factures DICA FRANCE (1 500 EUR/mois) | P0 | [ ] | dossier 1.1, rapport 6.5, audit-08 3 |
| A2 | Preuves de paiement DICA FRANCE (relevés, virements ou avis d'encaissement) | P0/P1 | [ ] | dossier 1.1, audit-08 3 |
| A3 | Contrat, devis signe, bon de commande ou email de commande DICA FRANCE | P0 | [ ] | dossier 1.1, audit-08 3 |
| A4 | Perimetre de service DICA FRANCE (description ecrite) | P1 | [ ] | dossier 1.1, audit-08 3 |
| A5 | Email ou attestation Centrale Lille / Chaire Construction 4.0 / Pr Zoubeir Lafhaj | P0 | [ ] | dossier 1.1, audit-08 3 |
| A6 | Protocole ou compte rendu de test Centrale Lille | P1 | [ ] | dossier 1.1, audit-08 3 |
| A7 | Convention, email d'acceptation, fiche incube ou attestation Le Tarmac by inovallée | P0/P1 | [ ] | dossier 1.1, audit-08 3 |
| A8 | Pieces R&D pre-repository (notes datees, schemas, archives, exports) | P1 | [ ] | dossier 5.2, rapport 5.4 |
| A9 | Dossier des 4 brevets PRISM en cours (recépisses, dates, inventeurs, titulaires, perimetre consensus) | P0/P1 | [ ] | dossier 5.2, rapport 5.4 |
| A10 | Acte juridique de chaine de droits PRISM -> Evidence (cession, licence, apport ou autorisation) | P0 | [ ] | dossier 5.2, rapport 5.4 |
| A11 | Capture d'un `pytest --collect-only` reussi en environnement Python 3.11 (preuve **figee** au 28 avril 2026 : 3 956 tests collectes — voir `docs/preuves-execution/PREUVES_TECHNIQUES_EXECUTION.md` section 2 et fichier `A11_pytest_collect_only.txt`) | P1 | [X] | rapport 7.1, audit-08 3 |
| A12 | Capture d'un build Docker reussi (`docker compose -f deploy/docker-compose.yml build`) — script `run_docker_proof.sh` fourni, **a relancer apres demarrage de Docker Desktop** | P1 | [ ] | rapport 7.1, audit-08 3 |
| A13 | Capture `pytest tests/security/test_file_writer_includes_failure.py tests/security/test_file_writer_includes_message.py tests/regression/test_session_yenoyikz_repro.py -v` (28 tests yENoyKIZ verts) | P2 (optionnelle) | [ ] | dossier 10, addendum 09 § 3 |
| A14 | Capture `pytest -m infra tests/infra/ -v` (T1-T7 verts sur staging Postgres ; project name `evidence-staging`) | P2 (optionnelle) | [ ] | dossier 10, addendum 09 § 4-5 |
| A15 | Manifeste SHA-256 du snapshot pre-P0 (`/home/ubuntu/snapshots/pre-P0-20260505-143731/MANIFEST.sha256`, 505 MB) | P2 (optionnelle) | [ ] | dossier 10, addendum 09 § 4.3 |

### 4.2 Fiches modeles par annexe

#### A1 — Factures DICA FRANCE

- **Pieces attendues :** ensemble des factures emises a DICA FRANCE depuis le debut de la prestation (toutes les factures, pas seulement la premiere et la derniere).
- **Format :** PDF des factures originales emises par l'apporteur.
- **Coherence a verifier avant remise :** numero de facture, date, periode facturee, montant HT et TTC, mention TVA (ou exoneration), coordonnees apporteur, coordonnees DICA FRANCE.
- **Ce qu'elles prouvent :** le revenu recurrent de **1 500 EUR/mois** annonce dans le dossier (source canonique : `DOSSIER_COMMISSAIRE_APPORTS_EVIDENCE.md` 1.1).
- **A qui remettre :** commissaire aux apports + Diag & Grow.
- **Risque si absent :** la traction redevient declarative, le scenario haut tombe au plancher 662-850 kEUR.

#### A2 — Preuves de paiement DICA FRANCE

- **Pieces attendues :** releves bancaires (extraits caviardes des autres operations si besoin), avis de virement, captures d'ecran de la banque ou attestation comptable.
- **Format :** PDF des extraits ou captures.
- **Coherence a verifier :** chaque encaissement correspond a une facture A1, dates et montants alignes.
- **Ce qu'elles prouvent :** que la facturation A1 est payee, donc que le revenu est encaisse et non simplement facture.
- **Si certains paiements sont en attente :** lister explicitement les echeances non encore encaissees, ne pas les masquer.
- **A qui remettre :** Diag & Grow en priorite (controle financier).

#### A3 — Contrat, devis ou bon de commande DICA FRANCE

- **Pieces attendues :** contrat signe ou, a defaut, devis accepte par email, bon de commande, ou echange ecrit prouvant l'engagement commercial.
- **Format :** PDF du document signe + capture des emails de validation si applicable.
- **Coherence a verifier :** mentions des parties, perimetre, duree, montant, conditions de renouvellement, conditions de resiliation.
- **Ce qu'elles prouvent :** que la facturation A1 ne repose pas sur une facture isolee mais sur une relation commerciale formalisee.
- **A qui remettre :** les deux.

#### A4 — Perimetre de service DICA FRANCE

- **Pieces attendues :** une note d'1 a 2 pages (peut etre redigee par l'apporteur) decrivant ce qui est vendu : licence d'usage, integration, formation, maintenance, hebergement, support.
- **Format :** note signee + tout document marketing ou contractuel decrivant le service.
- **Coherence a verifier :** description coherente avec ce qui est livre techniquement, et sans surpromesse non tenue.
- **Ce qu'elles prouvent :** Diag & Grow comprend la nature du revenu et peut le qualifier (licence, abonnement, prestation).
- **A qui remettre :** Diag & Grow en priorite.

#### A5 — Email ou attestation Centrale Lille / Pr Zoubeir Lafhaj

- **Pieces attendues :** au moins un ecrit externe non redige par l'apporteur. Ordre de preference : 1) attestation signee du Pr Lafhaj, 2) convention de collaboration avec la Chaire Construction 4.0, 3) email du Pr Lafhaj decrivant l'usage d'Evidence, 4) email d'un autre membre de la Chaire mentionnant le test.
- **Format :** PDF du document ou capture complete de l'email avec en-tete, expediteur, date.
- **Coherence a verifier :** orthographe **`Lafhaj`** (pas `Lahfaj`), nom complet de la Chaire, contexte du test.
- **Ce qu'elles prouvent :** que la mention de Centrale Lille n'est pas un nom prestigieux cite sans preuve.
- **A qui remettre :** les deux.

#### A6 — Protocole ou compte rendu de test Centrale Lille

- **Pieces attendues :** document decrivant le protocole de test, les usages testes, les resultats observes ou les retours utilisateurs.
- **Format :** PDF, ideal si signe ou valide par un membre de la Chaire.
- **Si pas encore disponible :** le mentionner explicitement dans la note de remise et donner un calendrier de production.
- **A qui remettre :** Diag & Grow.

#### A7 — Preuve Le Tarmac by inovallée

- **Pieces attendues :** convention d'incubation ou d'accompagnement, email d'acceptation, fiche incube, attestation du Tarmac, ou tout ecrit externe.
- **Format :** PDF du document original.
- **Coherence a verifier :** orthographe `Le Tarmac by inovallée` (avec accent), date d'entree dans le programme, type d'accompagnement.
- **Ce qu'elles prouvent :** signal d'ecosysteme et d'accompagnement entrepreneurial.
- **A qui remettre :** les deux.

#### A8 — Pieces R&D pre-repository

- **Pieces attendues :** tout element date anterieur au 15 janvier 2026 demontrant un travail R&D sur PRISM, le consensus anti-hallucination, le pipeline juridique ou l'auditabilite. Exemples : carnets de conception, schemas, exports d'outils de note, archives ZIP, depots Git anterieurs, captures de prototypes, emails, factures d'outils, depots de noms de domaine, depots de marque.
- **Format :** PDF d'un classeur unique organise par theme et par date, contenant les originaux ou des captures avec metadonnees.
- **Coherence a verifier :** chaque piece doit avoir une date verifiable (metadonnee fichier, en-tete email, horodatage de creation).
- **Ce qu'elles prouvent :** la these des 5 ans de R&D anterieure.
- **Si insuffisant :** ne pas survendre. Dire "antériorite documentee partiellement par X pieces, le reste relevant du savoir-faire non documente".
- **A qui remettre :** les deux.

#### A9 — Dossier des 4 brevets PRISM en cours

- **Pieces attendues :** pour chacun des 4 brevets : recepisse de depot ou preuve de depot (INPI ou equivalent), date de depot, inventeurs, titulaires, titre provisoire, abstract ou revendications synthetiques. Indiquer explicitement quel brevet couvre le consensus anti-hallucination.
- **Format :** classeur PDF unique avec sommaire des 4 brevets.
- **Coherence a verifier :** les brevets sont rattaches a **PRISM**, pas a Evidence. Ne jamais les presenter comme "brevets Evidence".
- **Ce qu'elles prouvent :** le portefeuille IP PRISM et le caractere innovant des algorithmes integres a Evidence.
- **A qui remettre :** les deux.

#### A10 — Chaine de droits PRISM -> Evidence

- **Pieces attendues :** un acte juridique ecrit (cession, licence, apport, autorisation d'exploitation, ou pacte d'apporteur) prouvant qu'Evidence a le droit d'utiliser les algorithmes PRISM brevetes.
- **Format :** PDF du document signe ou du projet de document a signer.
- **Coherence a verifier :** identite des parties (titulaire PRISM = inventeur Amine Mohamed = apporteur), perimetre couvert, duree, conditions financieres si applicables.
- **Ce qu'elles prouvent :** que les brevets PRISM peuvent renforcer la valorisation d'Evidence.
- **Risque si absent :** les brevets restent neutres pour Evidence et ne peuvent pas justifier la borne offensive.
- **A qui remettre :** commissaire aux apports en priorite.

#### A11 — Capture pytest --collect-only

- **Statut :** **PREUVE FIGEE** au 28 avril 2026, 09:51 (UTC+02:00). Documentee dans `docs/preuves-execution/PREUVES_TECHNIQUES_EXECUTION.md` section 2, sortie brute dans `A11_pytest_collect_only.txt`.
- **Resultat reel :** **3 956 tests collectes** en Python 3.11.12 / pytest 9.0.2 / 7,00 s d'execution. Network Guard ACTIVE (pas d'appels reseau). Le chiffre depasse les 3 910 cites dans le rapport (tests ajoutes entre le 17 et le 24 avril 2026).
- **Pieces attendues :** sortie texte du terminal (5 080 lignes), conservee dans le dossier `docs/preuves-execution/`.
- **Coherence a verifier :** version Python = 3.11.12, total = 3 956 (en ligne 11 du fichier brut), pied de page = "3956 tests collected in 7.00s".
- **Ce qu'elles prouvent :** que le volume de tests annonce est **reel, reproductible et actuellement plus eleve** que la reference documentaire.
- **Note :** une collecte en Python 3.9 (Python systeme par defaut) echoue partiellement. Le venv du projet (`venv/bin/python`) est en 3.11.12 et est l'environnement officiel.
- **A qui remettre :** Diag & Grow (PDF du fichier `A11_pytest_collect_only.txt` ou capture d'ecran de l'execution).

#### A12 — Capture build Docker

- **Statut :** **PARTIELLEMENT FIGEE** au 28 avril 2026 09:52 (validation syntaxe `docker compose config` reussie, exit code 0). Le build complet `docker compose build` necessite Docker Desktop demarre, **non disponible** au moment de la capture.
- **Reproduction differee :** lancer `bash docs/preuves-execution/run_docker_proof.sh > docs/preuves-execution/A12_docker_build.txt 2>&1` apres demarrage de Docker Desktop (script joint, executable, 858 octets).
- **Pieces attendues :** capture terminal de l'execution du script `run_docker_proof.sh`, exit code 0, image `korev*` listee par `docker images`.
- **Coherence a verifier :** reference a `deploy/Dockerfile.backend` (multi-stage Python 3.11-slim + Node.js + WeasyPrint), syntaxe `docker compose config` validee (deja capturee dans `E_docker_inventory.txt`).
- **Ce qu'elles prouvent :** l'industrialisation Docker n'est pas declarative ; l'image se construit reellement depuis les sources versionnees.
- **A qui remettre :** Diag & Grow.
- **Action J-1 :** demarrer Docker Desktop la veille du RDV et lancer le script — quelques minutes suffisent.

---

## 5. Index des chiffres cles et matrice de coherence

> Source canonique = document qui fait foi en cas d'ecart. Toute mention de la meme valeur dans un autre document doit y renvoyer.

### 5.1 Metriques Git

| Element | Valeur | Source canonique | Mentionne aussi dans | Coherence |
|---|---|---|---|---|
| HEAD Git verifie | `7a7abd6a` (24 avril 2026) | `RAPPORT_TECHNIQUE` en-tete | rapport 3.1, 3.2, 5.1, conclusion ; present Pack en-tete | OK |
| Commit upstream de reference | `9a3a92b6` (10 janvier 2026) | `RAPPORT_TECHNIQUE` 2.1 | rapport 3.1, 3.2, 6.2, 7.1 | OK |
| Diff upstream -> HEAD au 24 avr. | 898 fichiers, +213 250 / -14 434, **net 198 816 lignes** | `RAPPORT_TECHNIQUE` 3.1 | rapport 3.2 (encadre git diff), rapport 6.2, conclusion | OK |
| Cumul commits Amine au 24 avr. | **267 commits**, +221 481 insertions, -17 976 suppressions, net +203 505 | `RAPPORT_TECHNIQUE` 1 et 5.3 | rapport 3.3 (note complementaire), 5.3 (tableau), 7 scorecard 10 | OK |
| Etat audite au 8 avril (historique) | 262 commits, +219 008 / -17 859, net +201 149 | `RAPPORT_TECHNIQUE` 3.3 | rapport 5.3, 6.6 ; scorecard 10 | OK |
| Premier commit Amine | 15 janvier 2026 | `RAPPORT_TECHNIQUE` 5.1 | rapport 1, 5.2, conclusion | OK |
| Periode de developpement | 15 janvier - 24 avril 2026 (99 jours calendaires, ~40 jours actifs) | `RAPPORT_TECHNIQUE` 5.2 | rapport 6.6 | OK |
| Total commits depot | 1 357 (au 24 avril) ; 1 352 (au 8 avril) | `RAPPORT_TECHNIQUE` 5.3 | — | OK |
| Commits frdel / Jan Tomasek (cumul deux signatures) | 674 (= 629 sous `frdel` + 45 sous `Jan Tomášek`, meme personne) | `RAPPORT_TECHNIQUE` 2.1 et 5.3 | — | OK |
| Commits autres contributeurs upstream (cumul) | 416 (35 contributeurs distincts upstream au total) | `RAPPORT_TECHNIQUE` 2.1 et 5.3 | — | OK |

### 5.2 Volumetrie code et documentation

| Element | Valeur | Source canonique | Coherence |
|---|---|---|---|
| Fichiers Python upstream (10 jan.) | 210 | `RAPPORT_TECHNIQUE` 1 et 2.2 | OK |
| Fichiers Python Evidence (17 avr.) | 599 | `RAPPORT_TECHNIQUE` 1 | OK |
| Lignes Python upstream | 28 403 | `RAPPORT_TECHNIQUE` 1 et 2.2 | OK |
| Lignes Python Evidence (17 avr.) | 186 865 | `RAPPORT_TECHNIQUE` 1 | OK |
| Total LOC proprietaire (apports A-M, P) | ~137 400 | `RAPPORT_TECHNIQUE` 4 (synthese) | OK |
| Total avec documentation (A-P) | ~166 100 | `RAPPORT_TECHNIQUE` 4 (synthese) | OK |
| Tests collectes en environnement de reference | 3 910 (avec parametrisation) ; 3 229 fonctions | `RAPPORT_TECHNIQUE` 1 et apport M | OK ; cohorent avec scorecard 5 |
| Fichiers de test | 180 | `RAPPORT_TECHNIQUE` 1 et apport M | OK |
| Documents .md ajoutes | +116 fichiers, ~+28 689 lignes | `RAPPORT_TECHNIQUE` 1 et apport O | OK |
| Onboarding developpeur | 1 196 lignes | `wc -l` reel | OK (corrige sur tous les documents) |

### 5.3 Estimation cout de reproduction (COCOMO II / Capers Jones / ISBSG)

| Element | Valeur | Source canonique | Coherence |
|---|---|---|---|
| Conservateur (productivite haute) | 1 324 j-h x 500 EUR = **662 000 EUR** | `RAPPORT_TECHNIQUE` 6.4 | OK |
| Median | 1 843 j-h x 650 EUR = **1 197 950 EUR** | `RAPPORT_TECHNIQUE` 6.4 | OK |
| Haut (benchmark strict) | 2 362 j-h x 800 EUR = **1 889 600 EUR** | `RAPPORT_TECHNIQUE` 6.4 | OK |

### 5.4 Scenarios de valorisation apres decote technique 12-20 %

| Scenario | Fourchette | Source canonique | Mentionne aussi dans |
|---|---:|---|---|
| Plancher prudent | **662 000 - 850 000 EUR** | `RAPPORT_TECHNIQUE` 6.4bis | dossier 6, audit-08 5 |
| Defendable equilibre (cible) | **958 000 - 1 054 000 EUR** | `RAPPORT_TECHNIQUE` 6.4bis | dossier 6, audit-08 5, rapport conclusion |
| Mediane defendable | ~1 006 000 EUR | `RAPPORT_TECHNIQUE` conclusion | — |
| Offensif maitrise | **1 150 000 - 1 350 000 EUR** | `RAPPORT_TECHNIQUE` 6.4bis | dossier 6, audit-08 5 |

### 5.5 Score de maturite technique

| Element | Valeur | Source canonique | Coherence |
|---|---|---|---|
| Audit initial (3 avril) | 58.75/100 | `audit-07` total | OK |
| Apres P0 (8 avril) | 65.25/100 | `audit-07` total | OK |
| Apres P1/P2 partiel (17 avril, etat actuel) | **69.00/100** | `audit-07` total | OK ; cite arrondi a 69/100 dans rapport, dossier, benchmark |
| Apres P1+P2 complets (estime) | ~76/100 | `audit-07` 8 | OK |
| Decote technique residuelle estimee | **12 - 20 %** | `audit-07` 8 et `audit-06` | OK ; cite dans rapport 6.4bis et conclusion |

### 5.6 Traction commerciale et terrain

| Element | Valeur | Source canonique | Coherence |
|---|---|---|---|
| Client recurrent | DICA FRANCE | `DOSSIER_COMMISSAIRE` 1.1 | OK ; cite dans rapport 6.5 et 7.2, benchmark 4.2, audit-08 |
| Tarif | **1 500 EUR/mois** | `DOSSIER_COMMISSAIRE` 1.1 | OK |
| Run-rate annualise | **18 000 EUR/an** | `DOSSIER_COMMISSAIRE` 1.1 | OK ; cite avec la mention "run-rate annualise" partout (jamais "ARR" pour ce poste) |
| Pilote universitaire | Chaire Construction 4.0, Centrale Lille, Pr **Zoubeir Lafhaj** | `DOSSIER_COMMISSAIRE` 1.1 | OK ; orthographe Lafhaj coherente partout (defaut DEF-7 corrige) |
| Ecosysteme | **Le Tarmac by inovallée** | `DOSSIER_COMMISSAIRE` 1.1 | OK |

### 5.7 Propriete intellectuelle PRISM

| Element | Valeur | Source canonique | Coherence |
|---|---|---|---|
| Inventeur PRISM et Evidence | Amine Mohamed | `DOSSIER_COMMISSAIRE` en-tete | OK ; mention "Amine Mohamed, inventeur de PRISM et de KOREV Evidence" dans rapport 5.4, dossier en-tete et 5.1, benchmark 4.2, audit-08 1 et 2 |
| Brevets | **4 brevets PRISM en cours**, dont un periment couvrant le consensus anti-hallucination | `DOSSIER_COMMISSAIRE` 5.2 | OK ; jamais qualifies de "brevets Evidence" (defaut DEF-8 corrige) |
| Chaine de droits | A annexer (A10) ; cession, licence, apport ou autorisation PRISM -> Evidence | `RAPPORT_TECHNIQUE` 5.4 | OK ; cite dans dossier 5.2, audit-08 3 |

### 5.8 Base open-source et licence

| Element | Valeur | Source canonique | Coherence |
|---|---|---|---|
| Projet upstream | Agent Zero (frdel / Jan Tomasek) | `RAPPORT_TECHNIQUE` 2.1 | OK |
| Licence | MIT (usage commercial autorise, oeuvre derivee proprietaire autorisee) | `RAPPORT_TECHNIQUE` 2.3 | OK |
| Position juridique | Aucun obstacle juridique bloquant identifie a ce stade ; conservation des notices tierces requise ; perimetre a faire confirmer par conseil juridique ou commissaire | `RAPPORT_TECHNIQUE` 2.3 | OK ; phrasing prudent |

---

## 6. Note de reconciliation des dates (a expliquer si on vous interroge)

Le dossier presente plusieurs dates distinctes. Cette pluralite n'est pas une contradiction, c'est une chronologie auditable :

| Date | Etat | Ce que contient le dossier a cette date |
|---|---|---|
| **17 avril 2026** | Etat audite | Date de redaction principale du rapport technique. C'est l'etat sur lequel l'audit hostile interne (livrables 01-07) a ete realise. Score 69/100. Commits Amine = 262, +219 008 insertions. |
| **24 avril 2026** | HEAD verifie initial | Dernier commit du depot a la date de l'audit-08 (`7a7abd6a`). Corrections de resilience entre le 17 et le 24 avril. Commits Amine = 267, +221 481 insertions. Diff upstream -> HEAD = 898 fichiers, 198 816 lignes nettes. |
| **25 avril 2026** | Verification de coherence Git complementaire | Date a laquelle les chiffres Git ont ete recalcules pour aligner les sections du rapport et tracer les ecarts. |
| **4 mai 2026** | Commit `de8b9c7e` | Fix `file_writer` fail-hard sur `§§include` non resolus (yENoyKIZ) + ADR-006 + 28 tests + post-mortem. |
| **5 mai 2026** | Commits `b11b4d99` + `0d0a35da` ; HEAD verifie de la presente revision | P0 migration RDBMS (Postgres + pgvector gated, ADR-007, 6 tests T1-T6, scripts backup, journal P0) + fix DEF-8 (pg_dump --clean --if-exists, pg_restore fail-loud, test T7). HEAD = `0d0a35da`. |

L'ecart entre l'etat audite (17 avril) et le HEAD verifie au 24 avril est de **+5 commits Amine, +2 359 insertions, +3 suppressions, +4 fichiers, +2 356 lignes nettes**. L'ecart entre le 24 avril et le 5 mai est de **+3 commits Amine, +3 048 insertions, -42 suppressions, 24 fichiers (fix yENoyKIZ + P0 RDBMS + fix DEF-8 ; verifie via `git diff 7a7abd6a..0d0a35da --shortstat`)**. Aucun de ces ecarts n'a d'effet materiel sur la valorisation : la decomposition COCOMO du rapport technique a ete calibree sur l'etat 17 avril ; les ecarts sont absorbes par les fourchettes d'estimation. Les effets qualitatifs des commits du 4 et 5 mai sont decrits dans `audit-hostile-valorisation/09-mise-a-jour-post-p0-yenoyikz.md` et dans la section 10 du dossier commissaire.

---

## 7. Procedure de mise a jour le matin du RDV

Si le HEAD a bouge entre la production de ce Pack et le RDV, executer dans cet ordre :

```bash
# 1. Recalculer les chiffres Git
git rev-parse --short HEAD
git log -1 --format='%ad' --date=short HEAD
git log --all --author='Amine' --shortstat --format='' \
  | awk '/files? changed/ {c++; i+=$4; d+=$6} END {print "Commits: " c " Insertions: " i " Suppressions: " d " Net: " (i-d)}'
git diff 9a3a92b6..HEAD --shortstat
```

2. Si les chiffres changent, mettre a jour **dans cet ordre** :
   - `RAPPORT_TECHNIQUE_VALORISATION_EVIDENCE.md` en-tete (HEAD), section 1 (encadre git diff), section 3.1 (verification), section 3.3 (note complementaire), section 5.3 (tableau et point cle), section 6.2 (note de rapprochement), conclusion (898 fichiers).
   - Section 5 du present Pack (matrice de coherence).
   - Mention "HEAD verifie" en en-tete du present Pack.

3. Relancer les controles avant impression :

```bash
python3 -m pytest tests/test_documentation_quality.py -q
git diff --check
```

4. Generer les PDF d'impression a partir des `.md` (Pandoc, Markdown viewer, ou impression PDF du navigateur). Utiliser le sommaire de la section 2 du present Pack comme ordre d'impression.

---

## 8. Posture en RDV

### 8.1 Valeur a defendre

- **Valeur cible :** **958 000 - 1 054 000 EUR** (mediane ~1 006 000 EUR), source canonique `RAPPORT_TECHNIQUE` 6.4bis.
- **Plancher de retrait :** 850 000 EUR (haut du scenario conservateur).
- **Borne offensive de negociation :** 1 150 000 - 1 350 000 EUR, **conditionnelle** a la remise effective des annexes A1 a A12 et a un rapport d'expert complementaire si demande.
- **Sortie inacceptable :** moins de 662 000 EUR.

### 8.2 Trois pieges a eviter

1. Ne pas annoncer la borne offensive comme valeur retenue. C'est une borne de negociation conditionnelle.
2. Ne pas presenter les 4 brevets comme brevets Evidence. Ce sont des brevets PRISM ; leur effet sur Evidence depend de l'annexe A10.
3. Ne pas pretendre a une certification AI Act ou a un audit securite externe. Dire "pipeline d'auditabilite et grilles de conformite auto-evaluees, a confronter a un audit externe ulterieur".

### 8.3 Phrases-cles

- "Methode principale : cout de reproduction COCOMO II / Capers Jones / ISBSG, eclairee par un benchmark de marche."
- "La traction DICA FRANCE et les pilotes ne sont pas la base de calcul mais reduisent le risque commercial et soutiennent le haut de fourchette."
- "L'audit hostile interne a ete realise et est joint au dossier ; les P0 sont corriges, les P1/P2 partiels sont livres, les P1/P2 restants sont assumes par la decote 12-20 %."
- "Amine Mohamed est inventeur de PRISM et de KOREV Evidence ; les brevets PRISM en cours sont annexes separement, l'effet sur Evidence depend de la chaine de droits A10."

---

## 9. Trace de l'audit hostile pre-remise

Conformement au protocole interne de pre-commit-audit, ce Pack et les documents qu'il reference ont fait l'objet d'une relecture contradictoire en 3 phases.

### 9.1 Audit du 25 avril 2026 (etat initial)

| Phase | Action | Resultat |
|---|---|---|
| 1 | Lecture ligne a ligne des 6 documents principaux | 4 defauts trouves : DEF-A1 (1 195 vs 1 196 lignes onboarding), DEF-A2 (commit audite 7a77fdb6 vs HEAD 7a7abd6a non explicite dans 01), DEF-B1 (1 197L dans 07), DEF-B2 (rattachement DICA/PRISM absent de 01). Tous corriges. |
| 2 | Construction du Pack par references (zero reecriture) | Aucun nouveau contenu duplique. Source canonique indiquee pour chaque chiffre. |
| 3 | Matrice de coherence inter-documents (section 5 du present Pack) | 100 % des cases en OK apres correction. Aucune incoherence residuelle detectee. |

### 9.2 Audit pre-commit applique aux 3 commits posterieurs au 25 avril

Conformement au protocole interne de pre-commit-audit (protocole obligatoire en 3 phases avant tout `git commit`), les 3 commits poses entre le 25 avril et le 5 mai 2026 ont ete audites individuellement avant push :

| Commit | DEF cumules | Severite max | Re-audit total | Trace mention dans message commit |
|---|:---:|:---:|:---:|:---:|
| `de8b9c7e` (yENoyKIZ) | 1 | Mineur (signature manquante) | non requis | Oui |
| `b11b4d99` (P0 RDBMS) | 7 | Modere (DEF-3 ordre integrity check, DEF-6 README staging) | non requis dans le diff (incident `--remove-orphans` runtime hors diff, traite en post-mortem) | Oui |
| `0d0a35da` (DEF-8) | 2 | Important (DEF-8 fail-silent restore) | **1 passe complete** post-correction, 0 defaut residuel | Oui |

### 9.3 Audit de la presente revision (5 mai 2026)

| Phase | Action | Resultat |
|---|---|---|
| 1 | Verification croisee des references aux 3 commits, ADR, fichiers crees, nombres de tests, lignes de doc, volumetrie cumulee | 5 defauts trouves : DEF-V1 (lignes ADR-006 incorrectes : 144 vs 69 reelles), DEF-V2 (lignes ADR-007 : 234 vs 212), DEF-V3 (lignes P0 journal : 256 vs 239), DEF-V4 (lignes addendum 09 : ~250 vs 287, lignes dossier commissaire : ~280 vs 240), DEF-V5 (volumetrie cumulee 24 avr -> 5 mai : +1 684 / -12 / 17 fichiers annonces vs +3 048 / -42 / 24 fichiers reels par `git diff --shortstat`). Tous corriges. |
| 2 | Coherence inter-documents (HEAD `0d0a35da` cite identiquement dans dossier commissaire en-tete, addendum 09 en-tete, present Pack en-tete et section 6 ; volumetrie corrigee identiquement dans addendum 09 § 2.1 et present Pack § 6) | OK. |
| 3 | Re-audit total non declenche (defauts uniquement Mineurs a Moderes : nombres de lignes errones et volumetrie initiale errones, sans impact sur la coherence narrative, sur les fourchettes de valorisation, ni sur les references aux commits / ADR / fichiers) | OK. |

**Defauts critiques residuels :** aucun.  
**Defauts importants residuels :** aucun, sous reserve de la production effective des annexes A1 a A12. Les annexes optionnelles A13-A15 ne sont pas indispensables.  
**Defauts moderes residuels :** ecart historique entre la decomposition COCOMO calibree au 17 avril (~196 500 lignes) et le diff Git au 24 avril (198 816 lignes), explicite dans la section 6.2 du rapport technique et la section 6 du present Pack ; ecart de ~+1,2 % absorbe par les fourchettes d'estimation.  
**Defauts mineurs residuels :** aucun.

---

*Pack produit le 25 avril 2026, revise le 5 mai 2026. HEAD verifie : `0d0a35da` au 5 mai 2026 (etat 25 avril : `7a7abd6a`). Toute mise a jour ulterieure suit la procedure de la section 7.*
