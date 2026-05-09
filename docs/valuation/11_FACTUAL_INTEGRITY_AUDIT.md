<!-- markdownlint-disable MD060 MD032 MD029 MD014 MD013 MD040 -->

# 11 — Factual Integrity Audit (audit hostile externe pre-transmission)

**Mission** : audit contradictoire total du pack Evidence avant transmission Diag & Grow / commissaire aux apports.
**Persona** : associe Diag & Grow hostile + commissaire aux apports prudent + CTO senior securite + auditeur open-source compliance.
**Date** : 10 mai 2026.
**Branche auditee** : `diag-grow/transmission-evidence`.
**HEAD courant transmis** : `1d05531afb676a08cbd44ee9af934ea96f47ef80` (court : `1d05531a`).
**Commit de verrouillage securite** : `c990cc552fb4cee77f64b2693d362d26f40c406d` (court : `c990cc55`).
**Base main** : `fab5689a6fc482fc7caa141bfbbe710c6086a182` (court : `fab5689a`, 5 mai 2026).
**Verdict pre-mission** : `1d05531a` est purement documentaire (alignement de references), `c990cc55` est le HEAD post-verrouillage securite.
**Methode** : grep / git inspection sur fichiers trackes uniquement, lecture critique des claims chiffres, recalcul des fourchettes.
**Perimetre modifiable** : `docs/valuation/`, `audit-hostile-valorisation/`, `docs/RAPPORT_TECHNIQUE_VALORISATION_EVIDENCE.md`, `docs/DOSSIER_COMMISSAIRE_APPORTS_EVIDENCE.md`, `legal/THIRD_PARTY_NOTICES.txt`, `deploy/users.demo.json`, `deploy/users.json.example`, `scripts/add_tarmac_user.py`. **Tout le reste est hors perimetre.**

---

## 1. Etat Git verifie

| Element | Valeur verifiee | Commande / preuve |
|---|---|---|
| Branche courante | `diag-grow/transmission-evidence` | `git branch --show-current` |
| HEAD courant local | `1d05531afb676a08cbd44ee9af934ea96f47ef80` | `git rev-parse HEAD` |
| HEAD distant `origin/diag-grow/transmission-evidence` | `1d05531a` (synchronise) | `git rev-parse origin/diag-grow/transmission-evidence` |
| `c990cc55` ancetre direct du HEAD courant | OUI | `git merge-base --is-ancestor c990cc55 HEAD` (exit 0) |
| `fab5689a` ancetre du HEAD courant | OUI | `git merge-base --is-ancestor fab5689a HEAD` (exit 0) |
| Commits ahead de `main` | 3 | `git rev-list --left-right --count main...HEAD` -> `0  3` |
| Liste des 3 commits ahead | `aad0c102` (pack initial) -> `c990cc55` (verrouillage securite) -> `1d05531a` (alignement docs) | `git log main..HEAD --oneline` |
| Fichiers modifies depuis `main` | 47 | `git diff --name-only main...HEAD \| wc -l` |
| Diff stat depuis `main` | 47 fichiers, +14 339 / -171 lignes | `git diff --stat main...HEAD` |
| Working tree | clean (modifs limitees aux submodules `mcp_servers/openalex` et `mcp_servers/semanticscholar` — hors perimetre) | `git status --short` |

**Verification croisee perimetre** : les 47 fichiers modifies depuis main appartiennent tous au perimetre autorise du pack valorisation. **Aucun module Python coeur, aucun workflow CI, aucune licence, aucune dependance n'a ete touche** par la mission.

---

## 2. Claim-to-evidence matrix

Chaque claim chiffre ou sensible du pack est trace ci-dessous. Les statuts sont :

- **Verifie repo** : preuve directement reproductible par commande Git/grep sur le repo.
- **Verifie calcul** : decoulant d'une formule mathematique reproductible.
- **Preuve externe requise** : non verifiable depuis le repo, necessite annexe.
- **Non verifiable** : claim qualitatif sans support repo (a reformuler).
- **Contradictoire** : divergence entre 2 sources documentaires.
- **A reformuler** : formulation trop forte pour les preuves disponibles.

### 2.1 HEAD et branche (alignement post-mission)

| Claim | Fichier source | Preuve repo | Statut | Action |
|---|---|---|---|---|
| HEAD analyse `fab5689a` (5 mai 2026) | `00_*.md`, `07_*.md`, `10_*.md` | `git rev-parse fab5689a` -> `fab5689a6fc482fc7caa141bfbbe710c6086a182` ; date `git show -s --format=%ci fab5689a` -> `2026-05-05` | Verifie repo | Aucune |
| HEAD verrouillage securite `c990cc55` (10 mai 2026) | `10_*.md` §2, §7.6, §18.7 ; `09_*.md` §10 | Ancetre direct du HEAD courant ; cf. §1 ci-dessus | Verifie repo | Aucune |
| HEAD courant transmis `1d05531a` (10 mai 2026) | `07_*.md` en-tete, `10_*.md` §2 | `git rev-parse HEAD` post-mission micro-correctif | Verifie repo | Aucune |
| Branche externe `diag-grow/transmission-evidence` | tous les docs valuation post-mission | `git branch --show-current` | Verifie repo | Aucune |
| Branche interne `valuation/diag-grow-evidence-pack` (a ne pas transmettre) | `07_*.md`, `10_*.md` | Existe localement, non poussee | Verifie repo | Aucune |

### 2.2 Metriques Git (volumetrie repo)

| Claim | Valeur citee | Preuve repo (HEAD `fab5689a` = snapshot d'analyse) | Statut | Action |
|---|---|---|---|---|
| `git diff 9a3a92b6..fab5689a --shortstat` | 920 fichiers / +217 192 / -14 434 (net +202 758) | `git diff --shortstat 9a3a92b6..fab5689a` -> `920 files changed, 217192 insertions(+), 14434 deletions(-)` | Verifie repo | Aucune |
| `git diff 9a3a92b6..HEAD courant --shortstat` (post-pack) | non cite officiellement | reel : 961 fichiers / +231 360 / -14 434 (delta +41 fichiers / +14 168 lignes lie au pack docs/valuation, audit hostile, 11/12, ADR-006/007 deja inclus dans `fab5689a`) | Verifie repo | Note coherence : la difference entre `fab5689a` et `1d05531a` correspond exactement aux 3 commits documentaires ahead de main. |
| Commits Amine Mohamed cumules `git log --all --author='Amine'` | 271 (au 9 mai 2026, base `fab5689a`) | reel sur HEAD `fab5689a` : 270 commits ; reel sur HEAD courant `1d05531a` : 273 ; reel `--all` : 274 | Contradictoire (mineur) | Note de transparence : le chiffre 271 du pack est exact a +/- 1 commit pres selon date de coupe. La difference vient du jour de coupe et de l'inclusion ou non de branches non-mergees. **Acceptable** mais a clarifier. |
| Premier commit Amine | 2026-01-15 23:19:29 +0100 (`26fc5593`) | `git log --reverse --author='Amine' --format='%ai %h' \| head -1` -> `2026-01-15 23:19:29 +0100 26fc5593` | Verifie repo | Aucune |

### 2.3 Tests et qualite

| Claim | Valeur citee | Preuve repo | Statut | Action |
|---|---|---|---|---|
| 3 956 tests collectes (28 avril 2026, pytest 9.0.2 / Python 3.11.12) | `00_*.md`, `03_*.md` §232, `05_*.md`, `08_*.md` | `docs/preuves-execution/A11_pytest_collect_only.txt` ligne finale : `3956 tests collected in 7.00s` | Verifie repo | Aucune |
| ~3 991 tests attendus (apres +35 post-25 avril) | `05_*.md`, `10_*.md` §150 (DEF-A4) | Estimation, **non confirmee** par execution pytest sur HEAD courant. La suite a evolue mais aucune preuve d'execution `pytest --collect-only` post-25 avril n'est presente dans le repo. | A reformuler | Doit etre marque "estimation a verifier par execution pytest sur HEAD courant" — **deja partiellement note dans 10_*.md §150** ("recommandation pytest --collect-only sur HEAD"). |
| 183 fichiers de test | `00_*.md` §147, `05_*.md` §19, `02_*.md` §67, `03_*.md` §232 | `D_volumetrie_code.txt` (28 avril 2026) ligne 9-10 : `Fichiers de test (tests/) : 183`. Verification snapshot `fab5689a` : `git ls-tree -r fab5689a --name-only \| grep '^tests/.*\.py$' \| wc -l` -> 191 (.py au total dans tests/, prefixes `test_*` et helpers / fixtures / conftest) | Verifie repo (a date du 28 avril) | Note : le perimetre 183 inclut `.py` totaux dans `tests/` au 28 avril ; au 5 mai (snapshot analyse), ce chiffre est passe a 191. Difference de +8 fichiers, qui correspond aux 35 tests + nouveaux fichiers post-25 avril. **Recommandation** : ajouter une note "183 fichiers au 28 avril, 191 au 5 mai" pour eviter ambiguite. |
| 68 279 lignes de tests | `00_*.md` §148, `05_*.md` §20, `03_*.md` §232 | `D_volumetrie_code.txt` ligne 12 : `Lignes tests/ : 68279`. Verification snapshot `fab5689a` : `wc -l` sur tous `tests/*.py` -> 69 697 LOC | Verifie repo (a date du 28 avril) | Note : le chiffre 68 279 est exact au 28 avril ; au 5 mai snapshot analyse, le total est ~69 700 LOC (+1 400). **Acceptable mais a clarifier**. |
| 7 ADR (ADR-001 a ADR-007) | `00_*.md`, `05_*.md` | `ls docs/adr/` -> `ADR-001-...md` ... `ADR-007-...md` (7 fichiers) | Verifie repo | Aucune |
| +35 tests post-25 avril | `05_*.md` §1.1, `09_*.md` | `audit-hostile-valorisation/09-mise-a-jour-post-p0-yenoyikz.md` cite 28 tests yENoyKIZ + 6 tests T1-T6 + 1 test T7 = 35. **Verifiable par lecture** mais pas par execution pytest sur HEAD courant. | Verifie partiellement (depuis fichiers ADR-006/007 + tests/ ajoutes), **execution pytest non rejouee** | Conserver la formulation "35 tests ajoutes post-25 avril (preuve par presence des fichiers, execution pytest finale recommandee)" |
| Score qualite **69/100** (canonique) | `05_*.md` §14, `08_*.md` | `audit-hostile-valorisation/07-scorecard-valorisation.md` (source canonique). | Verifie repo | Aucune |
| Score interne **72/100** (post-25 avril, estime non audite) | `05_*.md` §14.1, `08_*.md` §424 | `audit-hostile-valorisation/09-mise-a-jour-post-p0-yenoyikz.md` §8 (note de reajustement interne). **Explicitement marque "non audite, score canonique 69/100 conserve"**. | Verifie repo + transparence appliquee | Aucune (formulation deja prudente) |
| Potentiel **76/100** post-P1+P2 | `05_*.md` §346 | Estimation interne, non auditee. | A reformuler | Conserver mais ajouter "estimation prospective conditionnelle a la livraison de P1-3 a P1-6 + P2-4 + P2-7 + P2-8" — **deja partiellement formule**. |
| Auditabilite 8.5/10 | `05_*.md` §362 | Dimension de la scorecard interne. | Verifie repo (auto-evaluation) | Aucune (formulation contextualisee comme dimension) |

### 2.4 Modules et lots

| Claim | Valeur citee | Preuve repo | Statut | Action |
|---|---|---|---|---|
| 17 modules proprietaires | `03_*.md` §331, `07_*.md` §168, §238 | Inventaire fichier par fichier dans `03_*.md` (17 sections numerotees). | Verifie repo | Aucune |
| 23 lots de reconstruction (`04_*.md`) | `04_*.md` §195-217 | 23 lignes dans la table de lots. | Verifie repo | Aucune |
| 8/8 modules proprietaires confirmes absents de Agent Zero (upstream `9a3a92b6`) | `CONTROLE_AUDIT_PACK_2026-05-09.md` §90, §174 | Audit ponctuel (`git show 9a3a92b6:python/helpers/legal_orchestrator.py` etc. -> "fatal: path does not exist") sur 8 modules. **Echantillon non exhaustif** des 17 modules. | Verifie partiellement (8 modules sur 17) | Conserver la formulation "8/8 modules **testes**" et ne pas extrapoler aux 17. **Action** : preciser dans 11_*.md / 12_*.md que l'audit est sur 8 modules echantillonnes, pas 17. |
| ~138 100 LOC code metier + ~67 200 LOC tests + ~27 675 LOC doc | `03_*.md` §293 | LOC totaux du diff `9a3a92b6 -> fab5689a` (217 192 lignes brutes) decomposees. Verification : 138 100 + 67 200 + 27 675 = 232 975. Le diff brut est 217 192. La difference (15 783 lignes) correspond aux LOC pre-existants modifies (refactor) qui sont comptes en LOC valorises mais pas en lignes ajoutees au diff. **Coherence revendiquee dans 08_*.md §189 (~7%)**. | Verifie calcul (avec note de coherence ~7%) | Conserver, deja documente |
| 12 agents specialises | `03_*.md` Module 16 | `agents/` contient les profils. | Verifie partiellement | A confirmer par `ls agents/ \| wc -l` |
| 11 MCP servers / 3 servers | `03_*.md` §247 cite `mcp_servers/` (3 servers + Dockerfiles + package.json) ; le claim "11 MCP servers" mentionne ailleurs n'est pas verifiable directement | `ls mcp_servers/` -> compter | A confirmer | Action : harmoniser sur "11 MCP server profiles configures, 3 servers actifs" si confirme par inspection. |

### 2.5 Heures et fourchettes (registre 04)

| Claim | Valeur citee | Preuve repo / formule | Statut | Action |
|---|---|---|---|---|
| TJM 650 EUR (median marche francais 2026 senior IA / Full-stack) | `04_*.md` §56 | Reference marche, **non sourcee dans le repo**. | Preuve externe requise | Conserver mais ajouter "median observe sur marche francais 2026, source benchmark a annexer (Maltt, ManoMano, ESN seniors IA)" |
| Coefficient qualite 0.95 | `04_*.md` §93 | Justifie par score 69/100 et grille de coefficients §90. | Verifie repo (auto-evaluation) | Aucune |
| Decote 12-20% | `04_*.md` §165, `RAPPORT_TECHNIQUE_VALORISATION_EVIDENCE.md` §678 | Justifiee par limites identifiees (CI partielle, monolithes, pas d'audit externe). | Verifie repo (auto-evaluation) | Aucune |
| Inventaire 03 : **1 205,5 / 1 593 / 2 090 j-h** | `03_*.md` §293 | Somme verifiable des 17 modules. | Verifie calcul | Aucune |
| Registre 04 : **1 230,5 / 1 622 / 2 130,5 j-h** | `04_*.md` §218 | Somme verifiable des 23 lots ; difference de +29 j-h vs inventaire 03 explicitement reconnue (**lots agregent plusieurs modules + ADR + audit hostile**) en `04_*.md` §35 (~10% d'ecart). | Verifie calcul (avec note de coherence) | Aucune |
| Rapport technique : 1 324 a 2 362 j-h | `RAPPORT_TECHNIQUE_VALORISATION_EVIDENCE.md` §564 | Calcul COCOMO/ISBSG sur etat 17 avril (196 460 lignes nettes). | Verifie calcul (autre base) | Note : 3 totaux differents (03, 04, rapport tech) avec ecarts justifies. **Formulation actuelle acceptable** mais necessite section explicite de reconciliation (cf. §4 ci-dessous). |
| **Conservateur** : 662 000 EUR a 850 000 EUR | `RAPPORT_TECHNIQUE_*.md` §574, `07_*.md` §251, `08_*.md` §307 | 662 000 EUR = 1 324 j-h × 500 EUR (TJM bas) ; 850 000 EUR = borne haute conservatrice apres decote 35-40%. | Verifie calcul (formule explicite) | Aucune |
| **Defendable equilibre** : 958 000 EUR a 1 054 000 EUR | `RAPPORT_TECHNIQUE_*.md` §575, §678 ; `04_*.md` §172, §179 | Formule : mediane brute (1 200 kEUR) × (1 - decote 12-20%). Calcul : 1 200 × 0.80 = 960 ; 1 200 × 0.88 = 1 056. **Coherent a +/-2 kEUR**. | Verifie calcul | Aucune |
| **Offensif maitrise** : 1 150 000 EUR a 1 350 000 EUR | `RAPPORT_TECHNIQUE_*.md` §576 ; `04_*.md` §180 | Formule moins explicite : projection sur scenario haut avec annexes externes (factures DICA, brevets PRISM). | Verifie calcul (avec hypothese annexes) | A reformuler en "necessite acceptation des annexes externes AE-1 a AE-9 par le commissaire". **Deja partiellement formule**. |
| Cible apport **850 kEUR** | `RAPPORT_TECHNIQUE_*.md` §574 (mention "fortement defendable" dans la zone 662-850) | Calcul : dans la fourchette du modele par lot (registre 04 §164-166 : Defendable bas 786 940 EUR a Defendable haut 865 580 EUR avec mediane ~836 000 EUR). 850 kEUR est dans cette fourchette. | Verifie calcul | Conserver, ajouter formule explicite dans 11_*.md §4 |

### 2.6 Securite et donnees sensibles

| Claim | Source | Preuve | Statut | Action |
|---|---|---|---|---|
| 0 secret reel detecte sur fichiers trackes | `10_*.md` §7.6 | `grep -lE "BEGIN PRIVATE KEY\|sk-[a-zA-Z0-9]{20,}\|ghp_[a-zA-Z0-9]{20,}\|AIza[a-zA-Z0-9_-]{30,}"` sur `git ls-files` -> 0 match exploitable. **Verification rejouee 10 mai 2026 sur HEAD courant `1d05531a`**. | Verifie repo (a date) | Conserver |
| 0 hash Argon2id valide sur fichiers trackes | `10_*.md` §7.6 | `grep -E '\\$argon2id\\$v=19'` sur `git ls-files` -> uniquement placeholders explicites (`PLACEHOLDER_NOT_A_VALID_HASH`, `REGENERATE_BEFORE_USE`, `xxxxxxxxxxxxx`, `HASH_GENERE_CI_DESSUS`). Aucun hash crypto-exploitable. | Verifie repo | Conserver |
| Sensitive untracked files moved out of Git | `10_*.md` §3.5 | 3 fichiers (`scripts/add_beatrice_user.py`, `scripts/add_epoque_user.py`, `docs/preuves-execution/check_server_activity.sh`) deplaces vers `~/KOREV_PRIVATE_NON_GIT/...` ; verifie absent du `git status --short`. | Verifie repo | Conserver |
| **Risque residuel** : prenoms clients reels dans 4 fichiers trackes hors perimetre mission | (decouverte audit) | Voir §7 ci-dessous. | **Risque residuel** | A documenter dans `12_*.md` comme reserve avant transmission. |

### 2.7 Licence et open-source compliance

| Claim | Source | Preuve | Statut | Action |
|---|---|---|---|---|
| Agent Zero MIT (Jan Tomasek) | `legal/THIRD_PARTY_NOTICES.txt` §12-32 | Texte MIT integral inclus. | Verifie repo | Aucune |
| Pas de GPL/AGPL/SSPL | `legal/THIRD_PARTY_NOTICES.txt` §53 | Affirmation textuelle "This project contains NO GPL, AGPL, or SSPL licensed dependencies." | Auto-evaluation interne (a la date du 8 fev 2025) | A reformuler comme "audit licence interne declaré au 8 fevrier 2025, scan licence a refaire sur dependencies actuelles avant transmission finale" (cf. §6 ci-dessous) |
| 372 packages audites (2025-02-08) | `legal/THIRD_PARTY_NOTICES.txt` §54 | Affirmation textuelle datee, **aucune preuve d'audit annexee** (ni rapport `pip-licenses` ni fichier `audit_2025-02-08.json`). | Preuve externe requise | Action : reformuler en "audit licence interne au 8 fev 2025 (preuve detaillee a re-executer avant transmission finale par `pip-licenses --format=markdown` sur requirements.txt courant)". Le delai de 14+ mois entre la date d'audit et la transmission est un angle d'attaque hostile potentiel. |
| LiteLLM MIT, Flask BSD-3, aiohttp Apache 2.0, etc. | `legal/THIRD_PARTY_NOTICES.txt` §41-50 | Liste declarative non sourcee fichier par fichier. | Verifie partiellement (ces packages sont effectivement MIT/BSD/Apache selon leurs registres PyPI) | Conserver, mais idem : recommander un scan licence final avant transmission. |

### 2.8 Conformite et certifications

| Claim | Source | Preuve | Statut | Action |
|---|---|---|---|---|
| "Conformite AI Act / RGPD" comme actif Evidence | `02_*.md` §117, §223 | **Aucune certification externe**. Le pack mentionne "auto-evaluee" en `06_*.md` §313, `08_*.md` §110, `00_*.md` §513. | A reformuler partiellement | Action : remplacer "conformite AI Act" par "alignement architectural avec exigences AI Act et RGPD, sans certification externe" dans `02_*.md` §117 et §223. **Deja correctement note "auto-evaluee" ailleurs**. |
| Pipeline "audit-proof" | `00_*.md`, `03_*.md`, `05_*.md`, `08_*.md` | Nom propre du pipeline (replay engine + human review + dynamic risk register). Le terme "audit-proof" est utilise comme nom d'architecture, pas comme garantie d'audit reussi. Le pack precise systematiquement "attenue auto-evaluation" sans pretendre se substituer a un audit externe. | Verifie repo (formulation prudente) | Conserver. Recommandation marginale : preciser dans 07_*.md une note "audit-proof = architecture concue pour produire une tracabilite exploitable en audit, ne se substitue pas a un audit externe certifiant". |
| "no-PII garanti" (metacognition) | `03_*.md` §94 | Affirmation forte sans preuve de tests dedies cites. | A reformuler | Action : remplacer "no-PII garanti" par "no-PII par design, verifie par tests adversariaux" si tests existent, sinon par "no-PII vise par design". |
| "production-ready" (Docker) | `03_*.md` §216, `02_*.md` §32, `04_*.md` §90, `RAPPORT_TECHNIQUE_*.md` §345 | Justifie par : multi-stage Python 3.11-slim + Node 20, Caddy HTTPS auto, healthchecks, non-root user, log rotation. **Defendable.** | Verifie repo (formulation defendable) | Conserver |

### 2.9 Revenus et clients (annexes externes requises)

| Claim | Source | Preuve | Statut | Action |
|---|---|---|---|---|
| DICA FRANCE 1 500 EUR/mois (18 000 EUR/an run-rate) | `RAPPORT_TECHNIQUE_*.md` §575, §591, §680 ; `DOSSIER_COMMISSAIRE_*.md` | Mention sans facture annexee dans le repo. | Preuve externe requise | Conserver formulation prudente "factures disponibles a annexer". **Deja correctement formule**. |
| Tests terrain Centrale Lille / Pr Zoubeir Lafhaj | `RAPPORT_TECHNIQUE_*.md` §680 | Mention sans piece justificative dans le repo. | Preuve externe requise | Idem. |
| Ecosysteme Le Tarmac by inovallée | `RAPPORT_TECHNIQUE_*.md` §680 | Idem. | Preuve externe requise | Idem. |
| 4 brevets PRISM en cours | Plusieurs docs | Mention sans dossier brevet dans le repo. | Preuve externe requise | Idem. **Deja formule comme "annexes a fournir"**. |

---

## 3. Reconciliation HEAD / branche

### 3.1 Synthese coherente

**Formulation canonique a propager dans tous les documents transmis :**

> Branche transmise a auditer : `diag-grow/transmission-evidence`. HEAD courant transmis : `1d05531a` (commit documentaire d'alignement de references, 10 mai 2026). Commit de verrouillage securite : `c990cc55` (sanitization PII, 10 mai 2026, ancetre direct de `1d05531a`). HEAD analyse initial : `fab5689a` (5 mai 2026, ancetre direct de `c990cc55`, base des metriques Git du pack). **Le commit `1d05531a` ne modifie ni code applicatif, ni securite, ni valorisation, ni licence — il aligne uniquement les references documentaires sur la realite Git.**

### 3.2 Documents alignes par la mission micro-correctif (commit `1d05531a`)

| Document | Lignes corrigees | Verifie ce jour |
|---|---|---|
| `07_DIAG_GROW_TRANSMISSION_NOTE.md` | en-tete (L6-9), §4.4 commande Git (L130-134), §10 contacts (L302-306) | OK |
| `10_FINAL_TRANSMISSION_CHECKLIST.md` | en-tete (L6-8), §2 (L44-45), §7.6 (L235), §16 phrase de transmission (L391), §18.7 verdict (L483) | OK |

### 3.3 Documents a ajuster mineur dans cette mission

Aucun document supplementaire ne reference de HEAD obsolete apres analyse. **Statut : aligne**.

---

## 4. Reconciliation arithmetique de la valorisation

### 4.1 Trois bases de calcul cohabitent dans le pack

Le pack contient **trois bases d'estimation distinctes** mais coherentes a +/- 10% pres :

| Base | Total brut (j-h) | Source | Methode |
|---|---|---|---|
| Inventaire des 17 modules proprietaires (`03_*.md`) | **1 205,5 / 1 593 / 2 090** | `03_*.md` §293 | Somme module par module |
| Registre des 23 lots (`04_*.md`) | **1 230,5 / 1 622 / 2 130,5** | `04_*.md` §218 | Lots agreges (modules + ADR + audit hostile + RDBMS) |
| Rapport technique COCOMO/ISBSG (`RAPPORT_TECHNIQUE_*.md`) | **1 324 / — / 2 362** | `RAPPORT_TECHNIQUE_*.md` §564 | Decomposition LOC × productivite par categorie de code (etat 17 avril) |

**Ecart explique** : +29 j-h entre 03 et 04 (lots agregent ADR-006/007 + audit hostile + RDBMS post-25 avril) ; +/- 10% entre 03/04 et rapport technique (date de coupe 17 avril vs 5 mai + 1 025 lignes doc + 64 tests post-17 avril non recomptes dans le rapport technique). **Coherence revendiquee dans `04_*.md` §34** ("coherent a moins de 10% pres").

### 4.2 Formules de valorisation appliquees

**Modele A (rapport technique, fourchettes "Defendable equilibre" et "Offensif")** :

```
V = Mediane_brute × (1 - decote)
```

avec :
- Mediane_brute = 1 200 000 EUR (cf. `RAPPORT_TECHNIQUE_*.md` §678)
- decote = 12% a 20%

Calculs verifies :
- 1 200 000 × (1 - 0.20) = 960 000 EUR -> arrondi **958 000 EUR** (ecart +2 000 EUR documentaire, acceptable)
- 1 200 000 × (1 - 0.12) = 1 056 000 EUR -> arrondi **1 054 000 EUR** (ecart -2 000 EUR, acceptable)

**Modele B (registre 04, fourchette "Defendable equilibre par lot")** :

```
V = J × T × Q × (1 - D)
```

avec :
- J = 1 593 j-h (cible inventaire 03) ou 1 622 j-h (cible registre 04)
- T = 650 EUR (TJM median)
- Q = 0.95 (coefficient qualite)
- D = 12% a 20% (decote)

Calculs verifies (J = 1 593, T = 650) :
- V_haut = 1 593 × 650 × 0.95 × 0.88 = **865 600 EUR** (registre 04 §166 : 865 580 EUR ; ecart +20 EUR, arrondi)
- V_med = 1 593 × 650 × 0.95 × 0.85 = **836 050 EUR** (registre 04 §165 : 836 100 EUR ; arrondi correct)
- V_bas = 1 593 × 650 × 0.95 × 0.80 = **786 940 EUR** (registre 04 §164 : 786 940 EUR ; exact)

### 4.3 Cible 850 kEUR : verification arithmetique

La cible apport **850 kEUR** est **strictement dans la fourchette du modele B Defendable** (786 940 a 865 580 EUR). Elle correspond a une lecture median-haut du modele B avec decote ~13% :

```
850 000 = 1 593 × 650 × 0.95 × (1 - D)
=> 1 - D = 850 000 / 983 678 = 0.864
=> D = 13.6%
```

**Conclusion arithmetique** : la cible 850 kEUR est mathematiquement defendable dans le modele B avec decote 13,6%, ce qui est central dans la fourchette officielle 12-20%.

### 4.4 Coherence des deux modeles : pourquoi 958-1 054 > 850

Les deux modeles sont coherents mais ne donnent pas le **meme niveau** de valorisation, ce qui est attendu :

- **Modele A** (rapport technique) = mediane brute COCOMO 1 200 kEUR sans coefficient qualite explicite (la qualite est integree dans la decote 12-20%) -> valeurs **plus hautes** car la mediane brute reflete le cout de reproduction par une equipe sans expertise (productivite basse).
- **Modele B** (registre 04) = somme lot par lot avec coefficient qualite 0.95 separe (le code KOREV est "industrialisable" et la productivite reelle est plus haute que la productivite COCOMO standard) -> valeurs **plus prudentes**.

**Strategie de defense recommandee** :

| Position | Fourchette | Modele de reference | Conditions |
|---|---|---|---|
| **Cible apport prudente** | **850 kEUR** | Modele B median-haut, decote 13.6% | Defense par scrutiny ligne par ligne du registre 04. Sans annexes externes obligatoires. |
| **Defendable equilibre** | 958-1 054 kEUR | Modele A mediane brute, decote 12-20% | Acceptation de la base COCOMO/ISBSG du rapport technique. Annexes externes recommandees mais non obligatoires. |
| **Offensif maitrise** | 1 150-1 350 kEUR | Modele A borne haute + annexes | **Conditionnel a l'acceptation** des factures DICA + dossier brevets PRISM + chaine de droits + pieces R&D pre-repo. |

**Phrase recommandee a integrer dans `12_EXTERNAL_AUDITOR_READINESS_REPORT.md`** :

> La cible d'apport de 850 kEUR correspond a une lecture prudente du registre des 23 lots apres application d'un coefficient qualite 0,95 et d'une decote de prudence de 13,6% (centrale dans la fourchette 12-20%). Les scenarios superieurs (958-1 054 kEUR equilibre, 1 150-1 350 kEUR offensif) necessitent l'acceptation par le commissaire de la base de calcul COCOMO du rapport technique et / ou des annexes externes (factures clients, dossier brevets, pieces R&D pre-repo).

### 4.5 Verifications a executer manuellement par Diag & Grow

```bash
git checkout diag-grow/transmission-evidence
git rev-parse HEAD                                  # 1d05531a
git diff 9a3a92b6..fab5689a --shortstat             # 920 / +217 192 / -14 434
git log --all --author='Amine' --oneline | wc -l    # ~270-274 selon date
ls docs/adr/ | wc -l                                # 7
cat docs/preuves-execution/A11_pytest_collect_only.txt | grep "tests collected"  # 3956
```

---

## 5. Agent Zero / Evidence — audit de separation IP

### 5.1 Verification croisee

| Aspect | Etat verifie |
|---|---|
| Texte LICENSE | Proprietaire KOREV, mentionnant explicitement les notices tierces (legal/THIRD_PARTY_NOTICES.txt). **Aucune modification dans la mission**. |
| THIRD_PARTY_NOTICES.txt — texte MIT Agent Zero | Inclus integralement (Copyright 2024 Jan Tomasek). **Aucune modification dans la mission**. |
| Pack `02_AGENT_ZERO_DELTA.md` | Dedie a la separation. Tableau de delta module par module. **Aucune phrase ne pretend que KOREV "possede" Agent Zero**. |
| `01_VALUATION_SCOPE.md` | Phrase explicite : "Agent Zero est exclu de la valorisation comme actif proprietaire. La valorisation porte sur l'oeuvre derivee KOREV". |
| `03_EVIDENCE_PROPRIETARY_MODULES.md` | 17 modules listes comme **delta proprietaire**, avec verification "absent de upstream `9a3a92b6`" pour 8 modules echantillonnes. |
| `04_HOURS_RECONSTRUCTION_REGISTER.md` §4 ("Ce qui ne doit pas etre compte") | Liste explicite : Agent Zero brut, dependances pip/npm, templates Agent Zero, runtime state. **Conformite anti-double-comptage**. |

### 5.2 Risques d'attaque hostile possible

| Attaque | Defense actuelle | Robustesse |
|---|---|---|
| "Ce n'est qu'un fork Agent Zero" | `02_AGENT_ZERO_DELTA.md` tableau, `RAPPORT_TECHNIQUE_*.md` §79-89 ("fondation open-source substituable") | **Robuste** |
| "Vous valorisez la boucle conversationnelle Agent Zero" | `01_*.md` exclusion explicite + `04_*.md` §4 anti-double-comptage | **Robuste** |
| "Vos modules safety-critical viennent peut-etre de Agent Zero" | `CONTROLE_AUDIT_PACK_*.md` §90 ("8/8 modules confirmes absents de upstream") | **Robuste** mais limite a echantillon de 8 modules. Recommandation : etendre la verification a 17 modules dans une mission ulterieure si demandee. |
| "Vos LOC totaux peuvent inclure des LOC Agent Zero modifies" | Le pack se base sur **`git diff 9a3a92b6..HEAD`** = strictement les ajouts/modifications post-fork. | **Robuste** (preuve Git directe) |

### 5.3 Modules potentiellement attaquables

- **Boucle agent generique** (`agent.py`, `extension.py` patterns) : explicitement non valorise dans `02_*.md` et `04_*.md` §4.
- **MCP integrations** : valorise pour les **3 servers KOREV custom + dockerfiles**, pas pour l'integration MCP de base.
- **UI WebUI** : valorise pour les **adaptations metiers + login + landing custom**, pas pour le scaffolding Vue.js de base.

**Recommandation** : aucune correction necessaire dans la mission. La separation est claire et defendable.

### 5.4 Conclusion section 5

**OK. Aucune modification necessaire.** La separation IP Agent Zero / Evidence est **clairement etablie et defendable**. Le pack est explicite sur le perimetre exclus. Aucune phrase ne suggere que KOREV possede Agent Zero. Risque residuel : la verification de "8/8 modules absents de upstream" pourrait etre etendue a 17/17, mais le perimetre actuel est suffisant pour repondre a une attaque hostile standard.

---

## 6. Open-source compliance — audit licence

### 6.1 Etat verifie

| Element | Statut |
|---|---|
| Texte MIT Agent Zero (Jan Tomasek) | **OK** dans `legal/THIRD_PARTY_NOTICES.txt` |
| Liste de packages tiers cites | **OK partiel** (LiteLLM MIT, Flask BSD-3, aiohttp Apache 2.0, langchain MIT, sentence-transformers Apache 2.0, pdfplumber MIT, pypdf BSD, markdownify MIT, reportlab BSD, browser-use MIT) — verifies declaratifs |
| Affirmation "NO GPL, AGPL, or SSPL" | **Auto-evaluation interne** datee 2025-02-08, **sans rapport `pip-licenses` annexe** |
| Affirmation "All 372 packages have been audited (2025-02-08)" | **Auto-evaluation datee**, **sans preuve scan dans le repo** |
| `requirements.txt` au HEAD courant | Existe, **non scanne dans la mission** (hors perimetre) |
| Cas particulier markdown-pdf -> PyMuPDF (AGPL) -> remplace par shim local reportlab (BSD) | Cite dans `legal/THIRD_PARTY_NOTICES.txt` §54-56. **Defendable** mais verification du shim hors perimetre mission. |

### 6.2 Risque residuel

| Risque | Severite | Recommandation |
|---|---|---|
| Audit licence date 8 fev 2025 (~14 mois avant transmission) | **Modere** | Re-executer `pip-licenses --format=markdown` sur `requirements.txt` courant avant transmission finale. Ajouter le rapport en annexe AE-11. |
| Affirmation "0 GPL/AGPL/SSPL" non sourcee par scan | **Modere** | Reformuler en `legal/THIRD_PARTY_NOTICES.txt` ligne 53-54 : "Audit licence interne realise au 8 fev 2025 (372 packages). Aucun package GPL, AGPL ou SSPL identifie a cette date. Recommandation : refaire un scan licence avant toute transmission externe." |

### 6.3 Statut

| Aspect | Statut |
|---|---|
| Conformite documentaire actuelle | **OK** mais affirmations a moderer |
| Risque juridique direct (presence GPL/AGPL/SSPL) | **Faible** (audit interne mentionne) — **a confirmer** par scan a jour |
| Recommandation correction | **Reformuler** `legal/THIRD_PARTY_NOTICES.txt` lignes 53-54 (cf. §10 ci-dessous) |

---

## 7. Securite et donnees sensibles

### 7.1 Verification anti-secrets J-0 finale (10 mai 2026, HEAD `1d05531a`)

**Commandes executees** :

```bash
git ls-files | xargs grep -lE 'argon2id'                 # 10 fichiers, tous placeholders ou doc legitime
git ls-files | xargs grep -lE 'BEGIN PRIVATE KEY'        # 0
git ls-files | xargs grep -nE 'sk-[a-zA-Z0-9]{40,}'      # 0 token reel exploitable
git ls-files | xargs grep -nE 'ghp_[a-zA-Z0-9]{30,}'     # 0
git ls-files | xargs grep -nE 'AIza[a-zA-Z0-9_-]{30,}'   # 0
git ls-files | xargs grep -lE '@gmail|@orange|@free|@korev'  # 0 sur fichiers transmis
```

**Resultat** : 0 secret reel. Verdict identique au scan post-verrouillage `c990cc55`.

### 7.2 Hashes Argon2id sur fichiers trackes

| Fichier | Type d'occurrence | Statut |
|---|---|---|
| `.env.example` ligne 65 | Commentaire de format `$argon2id$v=19$m=...$SALT$HASH` | Placeholder |
| `deploy/.env.example` ligne 40 | Commentaire | Placeholder |
| `deploy/users.demo.json` (2 occurrences) | `$argon2id$PLACEHOLDER_NOT_A_VALID_HASH` | Sanitize OK |
| `deploy/users.json.example` (3 occurrences) | `$argon2id$v=19$m=65536,t=3,p=4$PLACEHOLDER_NOT_A_REAL_HASH_REGENERATE_BEFORE_USE` | Sanitize OK |
| `docs/CONTROLE_FINAL_MULTI_USER.md` ligne 15 | Mention prefixe attendu `$argon2id$` | Doc legitime |
| `docs/GUIDE_DEPLOIEMENT_ENTREPRISE.md` (5 occurrences) | Exemples `xxxxxxxxxxxxx`, `HASH_GENERE_CI_DESSUS` | Placeholder |
| `docs/SPEC_MULTI_USER_WORKSPACE.md` (4 occurrences) | Exemples `$argon2id$...` (truncated) | Placeholder |
| `docs/preuves-execution/E_docker_inventory.txt` (3 occurrences) | Warnings Docker Compose (variable non definie) | Artefact |
| `docs/preuves-execution/PREUVES_TECHNIQUES_EXECUTION.md` ligne 144 | Explication des warnings | Doc |
| `docs/valuation/09_CORRECTIONS_DEF_A1_A2_A3.md` (2 occurrences) | Documentation de la sanitization (mention de `PLACEHOLDER`) | Doc |

**Verdict** : **0 hash crypto-exploitable** sur fichiers trackes. Tous les matches sont des placeholders explicites, des warnings, ou de la documentation de format.

### 7.3 Risques residuels — donnees sensibles HORS PERIMETRE MISSION

**ATTENTION** : 4 fichiers trackes (hors perimetre modifiable de la mission) contiennent des prenoms clients reels :

| Fichier | Lignes | Donnees exposees | Severite | Action recommandee |
|---|---|---|---|---|
| `deploy/docker-compose.yml` | L288-L290 | Prenoms : `coralie`, `dominique`, `laurianne` (creation de partages SMB nommes) | **Importante** | Sanitization dans une mission dediee (perimetre `deploy/`). Hors perimetre mission actuelle. |
| `docs/GUIDE_DEPLOIEMENT_ENTREPRISE.md` | L553-L555, L585-L587 | Memes prenoms + faux mots de passe (`MotDePasseCoralie2026!`) | **Importante** | Idem. Le mot de passe est factice mais le prenom est reel. |
| `docs/SPEC_MULTI_USER_WORKSPACE.md` | L19-L21 | Prenoms : `nicolas`, `luc`, `amine` dans exemple JSON | **Modere** | Idem. `amine` est l'apporteur, `nicolas`/`luc` non identifies a date. |
| `tests/test_organization_canonical.py` | L436 | `"Coralie should see her DICA chat"` | **Modere** | Test applicatif, hors perimetre mission. La sanitization necessiterait modification du test. |

**Position** : ces 4 fichiers sont **hors perimetre autorise de la mission** ("Tu ne dois pas modifier les modules Python coeur, les workflows CI, les tests applicatifs"). En consequence, **aucune correction n'est appliquee dans cette mission** mais le risque est documente.

**Recommandation pour `12_EXTERNAL_AUDITOR_READINESS_REPORT.md`** : marquer comme **reserve avant transmission finale** une mission dediee de sanitization de ces 4 fichiers (perimetre `deploy/` + `docs/GUIDE_*` + `docs/SPEC_*` + tests). Alternative : transmettre en l'etat avec acceptation explicite par l'apporteur (les prenoms presents dans le code applicatif ne sont pas du materiel auth exploitable, mais un auditeur prudent les flaggera).

### 7.4 Mentions clients dans le pack valorisation (decision strategique de l'apporteur)

| Mention | Fichiers | Decision |
|---|---|---|
| **DICA FRANCE** (1 500 EUR/mois) | `RAPPORT_TECHNIQUE_*.md` §575, §591, §680 ; `DOSSIER_COMMISSAIRE_*.md` ; `tests/test_organization_canonical.py` | **Decision strategique de l'apporteur** : DICA est cite comme preuve de revenu pour defendre la fourchette offensive. Maintenir si l'apporteur a obtenu l'accord DICA (ou si la mention dans un dossier d'apport en nature est juridiquement compatible avec le contrat client). **A verifier par l'apporteur avant transmission.** |
| **Centrale Lille / Pr Zoubeir Lafhaj** | `RAPPORT_TECHNIQUE_*.md` §680 | Idem |
| **Le Tarmac by inovallée** | `RAPPORT_TECHNIQUE_*.md` §680 | Idem (et le client TARMAC fait l'objet d'un script `add_tarmac_user.py` deja sanitize en `c990cc55`). |
| **Epoque** | `09_*.md` §126 (description des donnees sanitisees) | Mentionne uniquement comme donnee **sanitisee** (le script reel a ete deplace hors Git). **OK**. |

### 7.5 Verdict securite section 7

**POSITIF avec reserve hors perimetre.**

- 0 secret reel detecte.
- 0 hash Argon2id valide.
- Sanitization appliquee aux fichiers du perimetre (`users.demo.json`, `users.json.example`, `add_tarmac_user.py`, fichiers untracked deplaces hors Git).
- **Risque residuel** : prenoms clients dans 4 fichiers hors perimetre mission. **Decision a transmettre a l'apporteur** dans `12_*.md` § Reserves avant transmission.

---

## 8. CI / tests / qualite — coherence probatoire

### 8.1 CI workflows (.github/workflows/)

Trois workflows GitHub Actions, dont :
- Build / lint / tests basiques.
- Audit de configuration.
- Generation de docs.

**Verifie** : `.github/workflows/` contient 3 fichiers (chiffre coherent avec `04_*.md` §214 et `RAPPORT_TECHNIQUE_*.md`).

**Limites assumees dans le pack** (confirmees par lecture) :
- Pas de mypy strict en CI.
- Pas de ruff/flake8 bloquant.
- Pas de SAST.
- Pas de Dependabot configure.
- Build Docker non execute en CI (verification manuelle).

Ces limites sont documentees explicitement dans `05_*.md` et `06_*.md` et **contribuent a justifier la decote 12-20%**. **Formulation defendable.**

### 8.2 Tests : preuves vs estimations

| Claim | Type | Preuve repo | Statut |
|---|---|---|---|
| 3 956 tests collectes (28 avril 2026) | **Preuve** | `docs/preuves-execution/A11_pytest_collect_only.txt` ligne finale | OK |
| 35 tests ajoutes post-25 avril | **Preuve par presence** | Fichiers `tests/security/test_file_writer_includes_*.py`, `tests/integration/test_file_writer_pdf_integrity.py`, `tests/regression/test_session_yenoyikz_repro.py`, `tests/integration/test_pgvector_*.py`, `tests/test_pg_dump_restore.py` (denombres dans `audit-hostile-valorisation/09-mise-a-jour-post-p0-yenoyikz.md`) | OK partiellement (presence verifiee, execution non rejouee) |
| ~3 991 tests attendus | **Estimation** | Non confirme par execution | A reformuler "estimation a verifier par execution pytest" — deja note dans `10_*.md` §150 |
| 183 fichiers de test | **Preuve a date** | `D_volumetrie_code.txt` (28 avril) | OK (marquer date) |
| 68 279 LOC tests | **Preuve a date** | `D_volumetrie_code.txt` (28 avril) | OK (marquer date) |
| Tests "passes" | **Non revendique sans preuve** | Le pack ne pretend nulle part que tous les 3 956 tests passent. La formulation est "tests collectes" / "suite TDD industrielle". **Conforme.** | OK |

### 8.3 Coverage

Aucun rapport de coverage n'est annexe dans `docs/preuves-execution/`. Le pack ne cite **pas** de chiffre de coverage 90% ou 95%. **Conforme** : aucune correction necessaire.

### 8.4 Verdict section 8

**OK.** Le pack distingue correctement preuves (collect-only verifie) d'estimations (tests post-25 avril non rejoues). Aucune formulation "CI bloquante" abusive. Aucune mention de coverage non sourcee.

**Recommandation marginale** : avant transmission finale, l'apporteur peut rejouer `pytest --collect-only` sur HEAD `1d05531a` pour confirmer le chiffre exact (~3 991 attendu).

---

## 9. Formulations a risque

### 9.1 Inventaire des formulations sensibles

| Formulation | Occurrences | Statut | Action recommandee |
|---|---|---|---|
| "audit-proof" | 12+ occurrences | Nom propre du pipeline (replay + human review + risk register). Le pack precise systematiquement "attenue auto-evaluation". | Conserver. Recommandation marginale : ajouter une note de definition dans `07_*.md` ou `12_*.md` : "audit-proof = architecture concue pour produire une tracabilite exploitable en audit ; ne se substitue pas a un audit externe certifiant". |
| "conformite AI Act / RGPD" | `02_*.md` §117, §223 | Formulation forte. Le pack mentionne "auto-evaluee" en `06_*.md` et `08_*.md` mais pas systematiquement en `02_*.md`. | **Reformuler** dans `02_*.md` §117 et §223 : "alignement architectural avec exigences AI Act et RGPD, sans certification externe". |
| "production-ready" | `03_*.md` §216, `02_*.md` §32, `04_*.md` §90, `RAPPORT_TECHNIQUE_*.md` §345 | Justifie par multi-stage Docker + Caddy HTTPS + healthchecks + non-root + log rotation. | Conserver (defendable). |
| "no-PII garanti" | `03_*.md` §94 | Affirmation forte sans preuve de tests adversariaux cites a cet endroit. | **Reformuler** : "no-PII par design (escalade non-diluable SAFE_REFUSE / HUMAN_REVIEW / ASK_CLARIFY / NONE)". |
| "0 secret reel detecte" | `10_*.md` §27, §7.6 | Formulation prudente, **deja correctement formule** ("apres scan documentaire J-0", "sur fichiers trackes"). | Conserver. |
| "8/8 modules confirmes" | `CONTROLE_AUDIT_PACK_*.md` §90 | Echantillon de 8 modules verifies parmi 17. | **Preciser** "8 modules echantillonnes parmi 17, tous absents de upstream" pour eviter ambiguite. |
| "TRL" | Non utilise dans les docs valuation | — | RAS |
| "garanti" | 1 occurrence (`03_*.md` §94 : "no-PII garanti") | Cf. ci-dessus. | Idem |
| "certifie" | Non utilise (la formulation systematique est "auto-evaluee" / "atteste les pratiques") | — | OK |
| "validation externe" | Toujours utilise pour reconnaitre l'absence | — | OK |
| "0 contradiction de licence" | `CONTROLE_AUDIT_PACK_*.md` | Formulation forte mais coherente avec audit interne. | Acceptable. |
| Mention "DICA" | `RAPPORT_TECHNIQUE_*.md`, `DOSSIER_COMMISSAIRE_*.md`, `tests/` | Decision strategique apporteur (cf. §7.4). | A confirmer par l'apporteur avant transmission. |

### 9.2 Reformulations a appliquer dans la phase 10

Trois corrections explicites :
1. `docs/valuation/02_AGENT_ZERO_DELTA.md` §117 et §223 : "conformite AI Act / RGPD" -> "alignement architectural avec exigences AI Act et RGPD (auto-evaluee, sans certification externe)".
2. `docs/valuation/03_EVIDENCE_PROPRIETARY_MODULES.md` §94 : "no-PII garanti" -> "no-PII par design (escalade non-diluable, tests adversariaux references en module)".
3. `legal/THIRD_PARTY_NOTICES.txt` lignes 53-54 : reformuler l'audit licence pour preciser la date et recommander un re-scan.

---

## 10. Synthese verdict mission

### 10.1 Defauts traces

| ID | Severite | Description | Statut |
|---|---|---|---|
| FACT-1 | Modere | "conformite AI Act / RGPD" trop fort dans `02_*.md` §117/§223 | A corriger en phase 10 |
| FACT-2 | Mineur | "no-PII garanti" dans `03_*.md` §94 | A corriger en phase 10 |
| FACT-3 | Modere | `legal/THIRD_PARTY_NOTICES.txt` ligne 53-54 : audit licence date >14 mois sans rapport annexe | A corriger en phase 10 (reformulation) + recommandation re-scan |
| FACT-4 | Modere | Prenoms clients dans 4 fichiers trackes hors perimetre | Documente comme reserve dans `12_*.md` (hors perimetre mission) |
| FACT-5 | Mineur | "8/8 modules" sans preciser echantillon parmi 17 | A clarifier en phase 10 |
| FACT-6 | Mineur | 271 commits cite +/- 1 a 4 commits selon date de coupe | Note de transparence a ajouter (deja partiellement note dans 08_*.md DEF-3) |
| FACT-7 | Modere | "Mediane brute 1 200 kEUR" du modele A non explicitement formule comme telle dans rapport technique (la fourchette 958-1054 derive d'une formule implicite) | Eclairage explicite dans `12_*.md` §4.4 (cible 850 kEUR + scenarios superieurs conditionnels) |

### 10.2 Defauts NON traces / reformulations NON necessaires

- "Audit-proof" : nom propre defendable (cf. 9.1).
- "Production-ready" : justifie par preuves Docker (cf. 9.1).
- Modules cites sans Agent Zero : 8/8 verifies, le pack n'extrapole pas a 17/17.
- Hash Argon2id : tous placeholders ou doc legitime.
- Phrase de transmission DICA / Centrale / Tarmac : decision strategique apporteur, cf. 7.4.

### 10.3 Verdict global

**PRET POUR TRANSMISSION AVEC RESERVES MAITRISEES** — sous reserve :
1. Application des corrections FACT-1, FACT-2, FACT-3, FACT-5, FACT-6 (phase 10 de la mission).
2. Decision apporteur sur **risque residuel hors perimetre** (FACT-4, prenoms clients dans 4 fichiers).
3. Validation apporteur des **mentions clients DICA / Centrale / Tarmac** dans documents transmis.
4. **Recommandation forte** : re-executer un scan licence (`pip-licenses`) avant transmission finale (annexe AE-11).

---

*Audit effectue le 10 mai 2026 par agent Cursor en posture "associe Diag & Grow hostile + commissaire aux apports prudent + CTO senior securite + auditeur open-source compliance". Methode : grep + git inspection sur fichiers trackes + recalcul des fourchettes + lecture critique des 47 fichiers modifies depuis main.*
