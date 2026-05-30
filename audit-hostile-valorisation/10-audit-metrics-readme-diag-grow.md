<!-- markdownlint-disable MD013 MD024 MD036 MD060 -->

# 10 — Audit hostile metriques tests & README avant acces Diag & Grow

| | |
|---|---|
| Date de redaction | 2026-05-27 |
| Branche de redaction | `chore/diag-grow-metrics-hardening` |
| Branche cible (apres validation) | `main` (HEAD `03a5ce95` au depart) |
| Persona auditeur | Senior Staff Engineer + auditeur technique hostile (valorisation actifs logiciels, decote evaluation) |
| Cible adversaire | Diag & Grow, lecteur hostile cherchant a appliquer une decote |
| Perimetre | PRISM-Oracle uniquement |

---

## 1. Constat initial

Cartographie effectuee le 2026-05-27 sur l'etat de `main` (commit `03a5ce95`). Decouverte de plusieurs incoherences documentaires entre les chiffres de tests cites dans le README, la brochure PME, les guides developpeur et entreprise, et les rapports de valorisation.

### 1.1 Table de constat brute (avant correction)

| # | Fichier | Ligne | Valeur | Contexte | Statut |
|---|---|---:|---|---|---|
| 1 | `README.md` | 9 | `3846 Collected` | Badge Shields | Incoherent vs source canonique |
| 2 | `README.md` | 35 | `**3846 Tests** — 179 fichiers` | Section haute "Presentation" | Incoherent vs source canonique |
| 3 | `README.md` | 148 | `# 346 tests unitaires` | Commentaire arborescence | **Typo critique** (chiffre ~10x trop petit) |
| 4 | `README.md` | 223 | `346 tests unitaires couvrant` | Section "Tests" | **Typo critique** |
| 5 | `README.md` | 322 | `346 tests unitaires couvrant les invariants critiques` | Changelog v2.0.0 (janvier 2026) | **Typo critique** dans contexte historique |
| 6 | `docs/PACK_RDV_COMMISSAIRE_APPORTS.md` | 101, 192-197 | `3 956 tests collectes` (snapshot fige 28 avril 2026) | Pack RDV commissaire | **Canonique** — preuve datee |
| 7 | `docs/PACK_RDV_COMMISSAIRE_APPORTS.md` | 243 | `3 910 (avec parametrisation) ; 3 229 fonctions` | Snapshot 17 avril 2026 | Snapshot anterieur (OK dans contexte) |
| 8 | `docs/DEVELOPER_ONBOARDING_ARCHITECTURE_GUIDE.md` | 33, 880, 1188 | `3846 tests automatises` / 179 fichiers | Onboarding lead engineer | Snapshot anterieur, sans contexte |
| 9 | `docs/GUIDE_DEPLOIEMENT_ENTREPRISE.md` | 1371 | `3846 tests automatises (179 fichiers)` | Guide entreprise | Snapshot anterieur, sans contexte |
| 10 | `docs/audit/PROJECT_DOCUMENTATION_STANDARD.md` | 47, 411, 552 | `3 846` cite plusieurs fois | Documentation standardisee cabinet | Coherent avec README pre-correction, incoherent avec canonique |
| 11 | `docs/reports/KOREV_Evidence_Brochure_PME.html` | 577, 933 | `346+ tests unitaires` / `346+ tests unitaires` | Brochure PME commerciale | **Typo critique** |
| 12 | `tests/README_tests.md` | 5 | `2768 tests collectés — 137 fichiers` | README sous-suite tests | Snapshot tres anterieur (Q1 2026), sans contexte |
| 13 | `docs/RAPPORT_TECHNIQUE_VALORISATION_EVIDENCE.md` | 98-99, 519, 544 | `138 fichiers / 2 386 fonctions` | Analyse de valorisation datee 15 janv – 11 fev 2026 | Snapshot date dans rapport historique (a NE PAS modifier) |
| 14 | `docs/preuves-execution/A11_pytest_collect_only.txt` | EOF | `3956 tests collected in 7.00s` | Sortie brute pytest | **Source canonique brute** — mais ABSENTE de `main` |

### 1.2 Decouverte critique annexe

Le dossier `docs/preuves-execution/` n'existe **pas sur la branche `main`**. Il contient les preuves brutes citees par `docs/PACK_RDV_COMMISSAIRE_APPORTS.md` :

- `A11_pytest_collect_only.txt` (5 093 lignes, sortie pytest brute)
- `PREUVES_TECHNIQUES_EXECUTION.md` (synthese auditable)
- `B_pytest_doc_quality.txt`, `C_git_metrics.txt`, `D_volumetrie_code.txt`, `E_docker_inventory.txt`, `F_decomposition_diff.txt`
- `run_docker_proof.sh`

Ces fichiers sont commit `aad0c102` sur la branche `diag-grow/transmission-evidence` uniquement. Le dossier physique n'est plus sur disque (deplacement ancien vers vault prive). Sur `main`, les references croisees depuis `PACK_RDV_COMMISSAIRE_APPORTS.md` pointent donc vers des fichiers absents.

---

## 2. Source canonique retenue

| Champ | Valeur |
|---|---|
| **Chiffre canonique** | **3 956 tests collectes** |
| Date du snapshot | 2026-04-28, 09:51 (UTC+02:00) |
| Environnement | Python 3.11.12, pytest 9.0.2, pluggy 1.6.0, plateforme darwin |
| Network Guard | ACTIVE pendant la collecte (aucun appel LiteLLM reel) |
| Preuve brute | `A11_pytest_collect_only.txt` ligne EOF : `3956 tests collected in 7.00s` |
| Synthese auditable | `PREUVES_TECHNIQUES_EXECUTION.md` section 2 |
| Localisation Git | Commit `aad0c102` sur branche `diag-grow/transmission-evidence` (et descendants) |
| Cite par | `PACK_RDV_COMMISSAIRE_APPORTS.md` lignes 76, 101, 192-197 |

**Fichier de reference cree pour centralisation** : `docs/METRICS_CANONICAL_SOURCE.md`. Ce fichier est desormais la source unique de verite pour toute publication externe.

---

## 3. Corrections appliquees

### 3.1 Fichiers cree

| Fichier | Role |
|---|---|
| `docs/METRICS_CANONICAL_SOURCE.md` | Source unique de verite : chiffre canonique, snapshots historiques traces, procedure d'acces aux preuves, distinction snapshot / metriques courantes, limites assumees |
| `audit-hostile-valorisation/10-audit-metrics-readme-diag-grow.md` | Le present rapport |

### 3.2 Fichiers modifies

| Fichier | Modifications |
|---|---|
| `README.md` | L.9 badge Shields → `3956 Collected (snapshot 28 avril 2026)` + lien vers source canonique ; L.35 → `3 956 tests collectes (snapshot probatoire 28 avril 2026, 179 fichiers, Python 3.11.12 / pytest 9.0.2)` ; L.148 → `# 179 fichiers — 3 956 cas collectés (snapshot 28 avril 2026)` ; L.223 → section "Tests" reformulee avec lien canonique ; L.322 → suppression du chiffre incoherent dans changelog v2.0.0, formulation prudente "Suite de tests unitaires couvrant les invariants critiques (snapshot historique janvier 2026)" |
| `docs/reports/KOREV_Evidence_Brochure_PME.html` | L.577 `346 tests unitaires` → `pres de 4 000 cas de tests automatises (snapshot probatoire 28 avril 2026)` ; L.933 `346+ tests unitaires` → `~3 956 cas de tests collectes (snapshot 28 avril 2026)` |
| `docs/DEVELOPER_ONBOARDING_ARCHITECTURE_GUIDE.md` | L.33, 880, 1188 → mention canonique 3 956 + lien vers METRICS_CANONICAL_SOURCE.md, conservation de la mention 3 846 comme snapshot anterieur explicitement date |
| `docs/GUIDE_DEPLOIEMENT_ENTREPRISE.md` | L.1371 → mention canonique 3 956 + lien |
| `tests/README_tests.md` | L.5 → mention canonique 3 956 + note historique sur le chiffre 2 768 ; arborescence allegee des sous-totaux par dossier qui etaient des snapshots Q1 2026 |
| `docs/audit/PROJECT_DOCUMENTATION_STANDARD.md` | L.47, 411, 552 → mises a jour pour citer 3 956 (source canonique) au lieu de 3 846 |

### 3.3 Fichiers NON modifies (decision documentee)

| Fichier | Pourquoi NON modifie |
|---|---|
| `docs/PACK_RDV_COMMISSAIRE_APPORTS.md` | Deja coherent : cite 3 956 (canonique 28 avril 2026) et 3 910 (snapshot 17 avril dans son contexte natif). Les snapshots historiques cohabitent avec leur date — ne pas reecrire. |
| `docs/DOSSIER_COMMISSAIRE_APPORTS_EVIDENCE.md` | Aucune mention chiffree de tests detectee. |
| `docs/RAPPORT_TECHNIQUE_VALORISATION_EVIDENCE.md` | Cite `2 386 fonctions / 138 fichiers` comme snapshot date 15 janvier – 11 fevrier 2026 (Apport M). Ces chiffres sont DATES dans leur contexte natif et participent au narratif de valorisation (volumetrie a la date d'apport). **Modification interdite** par la regle "ne pas modifier les dates historiques sauf erreur manifeste". Le fichier `METRICS_CANONICAL_SOURCE.md` indexe ce snapshot en section 3 pour eviter toute confusion. |
| `audit-hostile-valorisation/09-mise-a-jour-post-p0-yenoyikz.md` | Cite `28 tests unitaires + integration + regression` comme decompte d'un sous-systeme (P0 RDBMS), pas du total repo. Pas une contradiction. |
| `docs/FEUILLE_DE_ROUTE_CONFORMITE_FORMAT_EVIDENCE.md` | Cite des nombres de tests par session (37, 46, 90, 51, 45, 18, 33, 12, etc.). Ce sont des sous-totaux historiques par session de developpement, pas des totaux repo. Pas une contradiction. |
| Sous-totaux par suite dans `README.md` section Tests (`204`, `42`, `27`, `30`, `43`) | Sous-totaux de suites specifiques au snapshot — coherent avec la note ajoutee "sous-totaux indicatifs au meme snapshot". |

---

## 4. Commandes executees

```bash
# Branche
git checkout -b chore/diag-grow-metrics-hardening   # depuis main 03a5ce95

# Cartographie initiale
grep -rEn "3[\s ]?846|3[\s ]?956|\b346\b|tests collected" --include="*.md" --include="*.html" .

# Verification source canonique (sans modifier la branche)
git show aad0c102:docs/preuves-execution/A11_pytest_collect_only.txt | tail -1
# → "======================== 3956 tests collected in 7.00s ========================="

git show aad0c102:docs/preuves-execution/PREUVES_TECHNIQUES_EXECUTION.md | grep -nE "3.?956"

# Verification finale post-correction
grep -rEn "\b346\s+tests|\b3846\b|\b3 846\b" --include="*.md" --include="*.html" .
# → Aucune occurrence hors contexte historique trace
```

---

## 5. Commandes NON executees (et pourquoi)

| Commande | Pourquoi non lancee | Risque residuel |
|---|---|---|
| `pytest --collect-only -q tests/` | L'environnement Python local n'a pas ete re-execute dans cette mission pour eviter d'introduire un nouveau snapshot intermediaire (entre 28 avril 2026 canonique et la date courante 27 mai 2026) sans figer formellement les preuves. | Le volume reel courant peut differer de 3 956 (en particulier, +19 tests Contradictor au 27 mai 2026, ce qui porte le minimum a 3 975). Recommandation : executer la commande en environnement de reference puis figer une nouvelle preuve datee. |
| `markdownlint` | Non disponible dans l'environnement courant ; non bloquant. | Quelques fichiers Markdown peuvent contenir des warnings de style ; les nouveaux fichiers ont les directives `<!-- markdownlint-disable ... -->` adequates. |
| `git diff --check` | Sera execute avant validation humaine (section 10). | Aucun a ce stade. |

---

## 6. Audit hostile — PASS 1 : Contradictions documentaires

Recherche post-correction (commande exacte en section 4) :

| Occurrence | Fichier | Statut |
|---|---|---|
| `3 846` cite | `docs/METRICS_CANONICAL_SOURCE.md` lignes 63, 120 | **Intentionnel** : indexe comme snapshot historique avec date |
| `3 846` cite | `docs/DEVELOPER_ONBOARDING_ARCHITECTURE_GUIDE.md` L.33 | **Intentionnel** : cite explicitement comme "snapshot anterieur debut avril" |
| `2 768` cite | `tests/README_tests.md` L.7 | **Intentionnel** : cite explicitement comme "snapshot historique Q1 2026, conserve pour tracabilite" |
| `3 910` cite | `docs/PACK_RDV_COMMISSAIRE_APPORTS.md` L.195, 243 | **Intentionnel** : snapshot 17 avril 2026 dans contexte natif du pack |
| `2 386` cite | `docs/RAPPORT_TECHNIQUE_VALORISATION_EVIDENCE.md` L.98, 99, 519, 544 | **Intentionnel** : snapshot 15 janv – 11 fev 2026, **date dans le rapport** |
| `346` orphelin | aucun fichier Markdown / HTML | **CLEAN** |
| `3846` orphelin | aucun fichier Markdown / HTML | **CLEAN** |

**Verdict PASS 1** : zero contradiction documentaire residuelle. Chaque chiffre non-canonique est explicitement encadre par sa date / son statut de snapshot historique. Le `webui/vendor/ace-min/*.js` contient des chaines minifiees contenant `3846` ou `346` au milieu de code Ace Editor : faux positifs (code tiers, aucun lien metrique).

---

## 7. Audit hostile — PASS 2 : Attaque evaluateur

> **Question posee** : *Si j'etais Diag & Grow et que je voulais appliquer une decote, quelle phrase ou quel chiffre utiliserais-je contre ce depot ?*

### 7.1 Attaques possibles et reponses preparees

| # | Attaque hostile potentielle | Reponse preparee dans le depot |
|---|---|---|
| A1 | "Le badge README affiche `3 956 Collected` mais les preuves brutes (`A11_pytest_collect_only.txt`) ne sont pas presentes dans le repo visible. Comment etre certain que le chiffre est reel ?" | `docs/METRICS_CANONICAL_SOURCE.md` section 4.1 documente la procedure d'acces via `git show aad0c102:docs/preuves-execution/...`. La preuve brute est dans l'historique Git, donc non re-ecrite, donc auditable. Diag & Grow peut verifier en une commande. **Reponse defensive : adequate**. |
| A2 | "Le snapshot est date du 28 avril 2026. Nous sommes plus d'un mois apres. Le chiffre actuel peut etre tres different." | `METRICS_CANONICAL_SOURCE.md` sections 5 et 7 declarent explicitement que c'est un snapshot probatoire date, distinct des metriques courantes, et que la re-execution est possible et documentee en section 4.3. **Reponse defensive : adequate**, transparente. |
| A3 | "Vous citez 3 956 mais dans `RAPPORT_TECHNIQUE_VALORISATION_EVIDENCE.md` on lit `2 386 fonctions`. Lequel est correct ?" | `METRICS_CANONICAL_SOURCE.md` section 3 indexe `2 386` comme snapshot de la periode 15 janv – 11 fev 2026 (apport initial), date explicitement dans le rapport historique. Les deux chiffres mesurent des choses differentes a des dates differentes : fonctions de test brutes au moment de l'apport vs cas collectes (parametrise) au 28 avril. **Reponse defensive : adequate**. |
| A4 | "Le README cite des sous-totaux (204 Router, 42 Metacognition, 27 Research Tool, etc.) qui ne somment pas a 3 956 — il manque ~3 600 tests." | La note section "Tests" indique explicitement que ce sont des "sous-totaux par suite, indicatifs au meme snapshot", et que les suites etendues (e2e, security, integration, infra, harness, golden, regression) sont collectees a part. **Reponse defensive : adequate**. |
| A5 | "Vous parlez de '~3 956 cas' avec un tilde dans la brochure, mais le badge dit '3956 Collected' sans incertitude. Incoherence ?" | Le tilde dans la brochure reflete l'arrondi communicationnel "pres de 4 000". Le badge cite le chiffre exact issu de la preuve brute. **Reponse defensive : adequate**, transparente. Pourrait etre encore plus stricte (eliminer le tilde) si demande. |
| A6 | "Le chiffre `2 768` apparait encore dans `tests/README_tests.md` — c'est contradictoire." | La note explicite a la ligne 7 documente que c'est un snapshot Q1 2026 conserve pour tracabilite. **Reponse defensive : adequate**. |
| A7 (le plus risque) | "Sur la branche `main` (que nous lisons en premier), les references croisees du `PACK_RDV_COMMISSAIRE_APPORTS.md` pointent vers `docs/preuves-execution/A11_pytest_collect_only.txt` qui n'existe pas. C'est un signal de qualite documentaire degrade." | **Reponse partielle** : `METRICS_CANONICAL_SOURCE.md` section 4 documente clairement la procedure d'acces et explique le decouplage. Mais **la coherence des references croisees depuis `PACK_RDV` n'est pas garantie sur main** : l'utilisateur qui ouvre `PACK_RDV` sur main et clique sur le lien `docs/preuves-execution/...` arrive sur un 404. **Risque residuel non resolu — voir plan de remediation P1 ci-dessous**. |
| A8 | "Aucune CI badge live. Le badge est manuellement maintenu, donc subjectif." | Aucune defense dans le repo actuel. Pas un risque majeur car les preuves brutes sont auditables, mais pourrait etre renforce. |
| A9 | "Au 27 mai 2026, 19 tests Contradictor ont ete commit (commit `fb811614`). Le badge dit 3 956, donc le volume reel est au moins 3 975. Le badge est obsolete." | **Reponse partielle** : le snapshot canonique 28 avril 2026 est anterieur au commit Contradictor. Toute communication peut citer "3 956 cas au 28 avril 2026 ; volume reel courant superieur du fait de l'ajout de la suite Contradictor le 27 mai 2026 (19 tests, voir `tests/test_contradictor_agent.py`)". Le risque est mineur si la communication est honnete sur la date du snapshot. |

### 7.2 Phrase de decote la plus probable

> *"Les chiffres de tests sont coherents entre eux, mais le repo cite des preuves d'execution (`A11_pytest_collect_only.txt`) qui ne sont pas presentes sur la branche par defaut `main`. Cela suggere soit un decouplage organisationnel, soit une difficulte a reproduire le snapshot probatoire en l'etat. La diligence requise demande d'acceder a une branche annexe pour valider la metrique principale. **Decote de qualite documentaire applicable : 1 a 3 % sur la fourchette de valorisation.**"*

### 7.3 Reponse hostile preparee

Le `METRICS_CANONICAL_SOURCE.md` documente explicitement le decouplage et fournit la procedure d'acces en 3 lignes de commande. Ce n'est **pas une dissimulation**, c'est une separation historique entre la branche de transmission probatoire (`diag-grow/transmission-evidence`) et la branche de developpement applicatif (`main`). La preuve brute est dans l'historique Git, non re-ecrite, immuable, accessible.

Pour neutraliser totalement cette decote, il faut soit (a) cherry-pick le commit `aad0c102` sur main, soit (b) re-executer `pytest --collect-only` aujourd'hui et figer une nouvelle preuve datee sur main. Voir plan de remediation section 8.

---

## 8. Audit hostile — PASS 3 : Plan de remediation priorise

| Priorite | Defaut | Severite vs Diag & Grow | Action recommandee | Effort |
|---|---|---|---|---|
| **Critique** (bloque acces) | aucun | — | — | — |
| **Important** (corriger avant acces si possible) | A7 : preuves canoniques absentes de `main` | Decote 1-3 % possible | Cherry-pick `aad0c102` (ou export propre des fichiers `docs/preuves-execution/A11_pytest_collect_only.txt` et `PREUVES_TECHNIQUES_EXECUTION.md`) sur la branche courante `chore/diag-grow-metrics-hardening`, puis merge sur main. Necessite validation utilisateur (changement de scope hors mission stricte). | 15 min |
| **Important** | A9 : volume reel actuel non re-execute depuis 28 avril 2026 | Decote 0,5 % possible si Diag & Grow exige une mesure recente | Lancer `pytest --collect-only -q tests/` dans l'environnement de reference, archiver la sortie dans `docs/preuves-execution/A11_pytest_collect_only_<date>.txt`, mettre a jour `METRICS_CANONICAL_SOURCE.md` section 1 avec le nouveau chiffre date. | 5-10 min |
| **Modere** (acceptable si documente) | A8 : pas de CI badge live | Aucun direct, signal de qualite | Brancher le badge Shields sur un workflow GitHub Actions `tests-collect-only` qui s'execute a chaque push sur main et publie le nombre dans un endpoint Shields. | 30-60 min |
| **Modere** | Les sous-totaux par dossier (`31`, `2`, `1`, `2`, `101` dans `tests/README_tests.md`) etaient des snapshots Q1 2026 et ont ete allegees ; un nouveau decompte serait benefique | Aucun direct | Lancer `find tests -name "test_*.py" -type f` puis `wc -l` par sous-dossier et mettre a jour `tests/README_tests.md` avec les chiffres actuels | 5 min |
| **Mineur** | Le webhook `webui/vendor/ace-min/*.js` contient des chaines `346` et `3846` dans du code minifie tiers (Ace Editor) | Aucun (code tiers reconnu) | Aucune action. Documenter en `THIRD_PARTY_NOTICES.txt` si besoin. | 0 |

---

## 9. Limites residuelles

1. **Le snapshot probatoire 28 avril 2026 n'a pas ete re-execute dans cette mission.** Le chiffre 3 956 est donc une **preuve auditable** mais **datee a un mois en arriere** par rapport a la date de redaction. Toute nouvelle communication externe devrait verifier si une re-execution recente est disponible.

2. **Le decouplage `main` vs `diag-grow/transmission-evidence`** persiste. Les preuves brutes restent dans l'historique Git du commit `aad0c102` mais ne sont pas physiquement sur `main`. Le rapport documente la procedure d'acces mais ne resout pas le decouplage structurellement (voir P1).

3. **Aucune CI live ne maintient automatiquement le badge.** Le chiffre du badge est statique et doit etre mis a jour manuellement a chaque nouveau snapshot.

4. **L'arborescence de `tests/` a evolue** : les sous-totaux par dossier cites dans `tests/README_tests.md` ne sont plus exacts (snapshot Q1 2026). La correction applique allege les sous-totaux et renvoie vers la source canonique, mais ne donne pas de nouveaux chiffres precis par dossier. Voir plan de remediation modere ci-dessus.

5. **L'utilisateur final reste le seul juge** de la mise en avant commerciale (brochure PME). Le chiffre canonique 3 956 et son arrondi "pres de 4 000" sont coherents mais l'utilisateur peut decider d'aller au chiffre exact pour eviter toute critique.

---

## 10. Verdict final

| Critere | Statut |
|---|---|
| Source canonique etablie et tracable | OUI (`docs/METRICS_CANONICAL_SOURCE.md`) |
| Incoherences flagrantes residuelles | NON (PASS 1 clean) |
| Typos critiques (346 / 346+) corriges | OUI (5 occurrences README, 2 occurrences brochure HTML) |
| Snapshots historiques distingues vs metriques courantes | OUI (table section 3 de METRICS_CANONICAL_SOURCE.md, mentions explicitement datees) |
| Limites assumees | OUI (section 9 ci-dessus et section 7 de METRICS_CANONICAL_SOURCE.md) |
| Procedure de reproduction documentee | OUI (section 4.3 de METRICS_CANONICAL_SOURCE.md) |
| References croisees sans liens morts (sur main) | **PARTIELLEMENT** (preuves brutes accessibles par git show, mais pas en navigation filesystem directe — voir P1) |
| Aucune invention de chiffres | OUI (zero invention, toutes les valeurs sont sourcees ou marquees comme indicatives) |
| Aucune promesse non prouvee (certifie, audit externe, AI Act compliant) | OUI |

### Recommandation finale

> **PRET POUR ACCES DIAG & GROW SOUS RESERVE de l'action P1 "cherry-pick preuves canoniques sur main".**

Sans cette action P1, la decote A7 (1-3 % sur la fourchette de valorisation, voir section 7.2) reste possible mais defendable par citation de la procedure `git show aad0c102:docs/preuves-execution/...`. L'utilisateur peut decider :

- **Option 1** : commit le present scope en l'etat, accepter la decote A7, fournir la procedure d'acces dans la communication a Diag & Grow.
- **Option 2** : action P1 (cherry-pick / export) avant la transmission. Necessite une mission supplementaire car cela touche au scope strict de cette mission (`chore/diag-grow-metrics-hardening` est dediee a la coherence documentaire, pas a la migration de preuves entre branches).

Recommandation : **Option 2** si le delai le permet (15 min d'effort), sinon **Option 1** avec mention explicite dans le mail de transmission.

---

## 11. Historique de revision

| Date | Action | Auteur |
|---|---|---|
| 2026-05-27 | Audit hostile complet (PASS 1+2+3) ; corrections appliquees sur README, brochure PME, guides developpeur/entreprise, tests/README, audit cabinet ; creation source canonique | Amine Mohamed (mission `chore/diag-grow-metrics-hardening`) |
