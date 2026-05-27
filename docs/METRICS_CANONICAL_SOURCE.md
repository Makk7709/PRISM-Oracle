<!-- markdownlint-disable MD013 MD024 MD060 -->

# Source canonique des metriques tests — KOREV Evidence

> Document de reference unique pour les chiffres de tests cites dans le README, les rapports de valorisation et les supports commerciaux. Toute incoherence apparente entre documents doit etre arbitree par cette source.

| | |
|---|---|
| Date de mise a jour de ce fichier | 2026-05-27 |
| Branche de redaction | `chore/diag-grow-metrics-hardening` |
| Commit HEAD audite | `03a5ce95` (`main`) |
| Mainteneur | Equipe KOREV / Cursor audit |

---

## 1. Chiffre canonique courant

**3 956 tests collectes** — snapshot probatoire fige au 28 avril 2026, 09:51 (UTC+02:00).

| Champ | Valeur |
|---|---|
| Volume collecte | **3 956 tests** (`3956 tests collected in 7.00s`) |
| Environnement | Python 3.11.12 / pytest 9.0.2 / pluggy 1.6.0 |
| Network Guard | ACTIVE (aucun appel LiteLLM reel pendant le collect) |
| Plateforme | darwin (macOS), x86_64 |
| Commande utilisee | `pytest --collect-only -q tests/` |
| Sortie brute integrale | `docs/preuves-execution/A11_pytest_collect_only.txt` (5 093 lignes) |
| Synthese auditable | `docs/preuves-execution/PREUVES_TECHNIQUES_EXECUTION.md` section 2 |
| Cite par | `docs/PACK_RDV_COMMISSAIRE_APPORTS.md` lignes 76, 101, 192-197 |

**Localisation des preuves brutes** : ces fichiers existent uniquement dans le commit `aad0c102` (et descendants) de la branche `diag-grow/transmission-evidence`. Ils ne sont **pas presents sur la branche `main`** au 2026-05-27. Voir section 4 ci-dessous pour la procedure d'acces / re-import.

---

## 2. Repartition par familles (donnees verifiables dans A11)

Les chiffres ci-dessous proviennent de `A11_pytest_collect_only.txt` et de la repartition des fichiers `tests/test_*.py` au 28 avril 2026. Ils sont indicatifs et peuvent avoir bouge depuis (notamment apres l'ajout de la suite Contradictor Agent au 27 mai 2026).

| Famille | Fichiers | Cas collectes (snapshot 28 avril) |
|---|---:|---:|
| Router (deterministe v2 + variants) | ~12 | ~204 |
| Metacognition / Policy | ~5 | ~42 |
| Research tool policy + executor | ~6 | ~57 |
| PDF extraction (timeouts, circuit breakers) | ~8 | ~43 |
| Consensus PRISM / collaborative | ~6 | ~80 |
| Sessions metier (S1-S15, Legal-Safe, Reasoning Engine) | ~30 | ~700 |
| Audit, observabilite, harness, golden | ~20 | ~450 |
| Tests parametrises (parametrize multiplie le volume) | n/a | reste du total |
| **Total approximatif** | **179 fichiers** | **3 956 cas** |

Toute publication d'un chiffre plus precis par famille doit etre justifiee par une nouvelle execution `pytest --collect-only` avec extraction par grep, et la sortie brute doit accompagner la communication.

---

## 3. Snapshots historiques connus (chiffres a NE PAS confondre)

Ces chiffres apparaissent dans la documentation mais correspondent a des dates anterieures. Ils ne sont **pas contradictoires** ; ils refletent l'evolution organique du depot.

| Chiffre | Source documentaire | Periode estimee | Statut |
|---|---|---|---|
| **3 956** | `docs/PACK_RDV_COMMISSAIRE_APPORTS.md` (lignes 101, 192-197), `A11_pytest_collect_only.txt` | 28 avril 2026 | **CANONIQUE courant** |
| 3 910 | `docs/RAPPORT_TECHNIQUE_VALORISATION_EVIDENCE.md` (figure dans le pack 1) et `PACK_RDV` ligne 243 | 17 avril 2026 | Snapshot rapport technique (depasse depuis) |
| 3 846 | `README.md` (badge + section haute, avant ce commit), `docs/DEVELOPER_ONBOARDING_ARCHITECTURE_GUIDE.md` lignes 33/880/1188, `docs/GUIDE_DEPLOIEMENT_ENTREPRISE.md` ligne 1371 | Avant le 17 avril 2026 (probablement debut avril 2026) | Snapshot anterieur, depasse |
| 2 768 | `tests/README_tests.md` ligne 5 | Snapshot tres anterieur (probable Q1 2026) | Historique organique, depasse |
| 2 386 fonctions / 138 fichiers | `docs/RAPPORT_TECHNIQUE_VALORISATION_EVIDENCE.md` lignes 98-99, 519, 544 | 15 janvier – 11 fevrier 2026 | Snapshot d'analyse de valorisation, date explicitement dans le rapport. **A NE PAS confondre** avec le volume actuel. |

Les valeurs hors de l'echelle de centaines (par exemple `346`) qui apparaissent dans certaines versions du README ou de la brochure PME sont des **erreurs de transcription** (perte d'un chiffre) et doivent etre corrigees. Voir section 5.

---

## 4. Procedure d'acces aux preuves canoniques

Les fichiers de preuve brute ne sont pas sur `main` pour des raisons historiques. Trois facons de les consulter :

### 4.1 Lecture en place via Git (sans checkout)

```bash
# Sortie brute pytest --collect-only au 28 avril 2026
git show aad0c102:docs/preuves-execution/A11_pytest_collect_only.txt | less

# Synthese executive auditable
git show aad0c102:docs/preuves-execution/PREUVES_TECHNIQUES_EXECUTION.md | less

# Verification rapide du chiffre canonique (doit afficher "3956 tests collected in 7.00s")
git show aad0c102:docs/preuves-execution/A11_pytest_collect_only.txt | tail -1
```

### 4.2 Bascule sur la branche de transmission

```bash
git fetch origin
git checkout origin/diag-grow/transmission-evidence -- docs/preuves-execution/
# Les fichiers apparaissent en stage, lecture possible
```

### 4.3 Re-execution locale (snapshot a une date posterieure)

```bash
# Environnement de reference
python --version  # doit etre 3.11.x
pytest --version  # doit etre >= 9.0

# Collect-only (deterministe, sans execution des cas)
pytest --collect-only -q tests/ | tail -3

# Resultat attendu au format : "XXXX tests collected in YYs"
```

La re-execution produira un chiffre superieur ou egal a 3 956 selon les tests ajoutes depuis (par exemple, la suite Contradictor Agent ajoute 19 cas le 27 mai 2026, ce qui porte le total a au moins 3 975 si rien d'autre n'a ete supprime). Ce chiffre n'est PAS canonique tant qu'une nouvelle execution probatoire datee n'a pas ete archivee.

---

## 5. Distinction snapshot probatoire vs metriques courantes

Les metriques de ce document sont des **snapshots probatoires dates**, pas des chiffres "live". Toute communication externe (notamment a destination de Diag & Grow ou d'un commissaire aux apports) doit :

1. Citer le chiffre canonique **3 956 au 28 avril 2026** comme reference probatoire ;
2. Renvoyer vers `docs/preuves-execution/PREUVES_TECHNIQUES_EXECUTION.md` (accessible via branche `diag-grow/transmission-evidence` — voir section 4) ;
3. Si une re-execution a eu lieu plus recemment, citer la nouvelle date et la nouvelle valeur, accompagnees du fichier de sortie brute ;
4. Ne **jamais** mentionner les chiffres `346` ou `3 846` sans contexte historique : ce sont des snapshots anterieurs ou des typographies de transcription.

---

## 6. Audit interne : verification rapide de coherence

Commande utile pour reauditer la coherence documentaire avant transmission externe :

```bash
# Trouve toute mention de chiffres potentiellement contradictoires
grep -rEn "\\b3[\\s ]?846\\b|\\b3[\\s ]?956\\b|\\b346\\b tests|\\b2[\\s ]?768\\b" --include="*.md" --include="*.html" .

# Reference canonique attendue dans toute publication externe
grep -rn "METRICS_CANONICAL_SOURCE" docs/ README.md
```

---

## 7. Limites assumees

- **Volume sensible a l'environnement Python** : le `pytest --collect-only` collecte tous les tests instancies par parametrization. Une version differente de Python (3.10 vs 3.11 vs 3.12) ou de pytest peut donner un chiffre legerement different. La valeur canonique 3 956 est specifique a Python 3.11.12 / pytest 9.0.2.
- **Pas de mesure d'execution dans ce document** : ce fichier documente le volume *collectable*, pas le nombre de tests *passing* ni le taux de couverture. Pour la couverture, voir `docs/RAPPORT_TECHNIQUE_VALORISATION_EVIDENCE.md` et lancer `pytest --cov`.
- **Decouplage main / branche de transmission** : les preuves brutes ne sont pas sur `main`. C'est un risque documentaire signale dans `docs/audit-hostile-valorisation/10-audit-metrics-readme-diag-grow.md` ; remediation P1.

---

## 8. Logs historiques et occurrences non canoniques

Certaines occurrences anciennes peuvent subsister dans des logs historiques de generation ou de conversation (par exemple, `logs/log_20260208_193504.html` contient des mentions `346 tests unitaires` issues d'un draft de brochure PME genere le 8 fevrier 2026). Ces fichiers ne sont **ni des documents de communication, ni des preuves de metriques, ni des sources utilisees pour la valorisation**. Ils sont conserves comme traces techniques historiques et ne prevalent **jamais** sur le snapshot probatoire date.

### 8.1 Sources canoniques uniques

Seules les sources suivantes font foi pour les metriques tests :

1. `docs/METRICS_CANONICAL_SOURCE.md` (le present fichier)
2. `docs/preuves-execution/PREUVES_TECHNIQUES_EXECUTION.md` (quand accessible — voir section 4 pour la procedure)
3. `docs/preuves-execution/A11_pytest_collect_only.txt` (sortie brute pytest, quand accessible — voir section 4)

### 8.2 Logs historiques explicitement non probatoires

| Fichier | Occurrences | Statut |
|---|---|---|
| `logs/log_20260208_193504.html` | Mentions `346 tests unitaires` / `346+ tests unitaires` issues d'un draft conversationnel du 8 fevrier 2026 | **Non canonique**. Trace technique conservee. Ne prevaut pas sur le snapshot probatoire date. |

### 8.3 Regle generale

Toute occurrence de metrique trouvee dans un fichier de `logs/`, `terminals/`, `agent-transcripts/`, ou autre repertoire de traces techniques est par defaut **non probatoire**. Seules les valeurs presentes dans les trois sources canoniques de la section 8.1 doivent etre utilisees pour la communication externe et l'evaluation.

---

## 9. Historique de revision

| Date | Action | Auteur |
|---|---|---|
| 2026-05-27 | Creation du fichier ; consolidation des metriques eparses ; identification du chiffre canonique 3 956 (28 avril 2026) | Cursor (mission `chore/diag-grow-metrics-hardening`) |
| 2026-05-27 | Ajout section 8 "Logs historiques et occurrences non canoniques" (remediation H-IMP-1) | Cursor (mission `chore/diag-grow-metrics-hardening`) |
