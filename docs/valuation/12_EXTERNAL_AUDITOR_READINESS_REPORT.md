<!-- markdownlint-disable MD060 MD032 MD029 MD014 MD013 MD040 MD036 -->

# 12 — External Auditor Readiness Report

**Mission** : verdict final pre-transmission Diag & Grow / commissaire aux apports.
**Auteur** : agent Cursor en posture "associe Diag & Grow hostile + commissaire aux apports prudent + CTO senior securite + auditeur open-source compliance".
**Date** : 10 mai 2026.
**Branche transmise** : `diag-grow/transmission-evidence` (poussee sur `origin`).
**HEAD courant transmis** : `1d05531a` (sera mis a jour apres commit final de cette mission).
**Commit verrouillage securite** : `c990cc55`.
**Base main** : `fab5689a` (snapshot d'analyse 5 mai 2026).
**Source** : `docs/valuation/11_FACTUAL_INTEGRITY_AUDIT.md` (audit hostile total).

---

## 1. Verdict global

**PRET POUR TRANSMISSION AVEC RESERVES MAITRISEES**

Le pack de valorisation Evidence est **factuellement solide**, **arithmetiquement defendable** et **legalement coherent** sous reserve d'application de 5 corrections documentaires (FACT-1 a FACT-3, FACT-5, FACT-6) **deja realisees dans cette mission** et de **3 decisions humaines** restant a prendre par l'apporteur avant transmission externe.

Le pack peut etre transmis a Diag & Grow / commissaire aux apports immediatement apres :
1. Validation par l'apporteur des decisions humaines (cf. §3 ci-dessous).
2. Eventuellement, re-execution `pip-licenses` sur `requirements.txt` courant (annexe AE-11 recommandee).

---

## 2. Niveau de fiabilite du pack

| Dimension | Niveau | Justification |
|---|---|---|
| Coherence des HEAD / branches / commits | **Eleve** | Tous les documents alignes sur `1d05531a` / `c990cc55` / `fab5689a`. Verifie 10 mai 2026. |
| Coherence arithmetique des fourchettes | **Eleve** | 3 modeles cohabitent (inventaire 03, registre 04, rapport technique) avec ecarts explicites <10%. Cible 850 kEUR mathematiquement defendable (modele B, decote 13.6%). |
| Separation IP Agent Zero / Evidence | **Eleve** | 8 modules echantillonnes (sur 17) confirmes absents de l'upstream. Aucune phrase ne pretend que KOREV possede Agent Zero. |
| Conformite licence | **Modere** | Audit licence interne 2025-02-08 (>14 mois). Reformule comme self-declaration. **Re-scan recommande** avant transmission finale (annexe AE-11). |
| Securite / anti-secrets J-0 | **Eleve sur perimetre** mais **risque residuel hors perimetre** | 0 secret exploitable sur fichiers trackes. Risque residuel : prenoms clients reels dans 4 fichiers hors perimetre mission. |
| Tests / qualite probatoire | **Eleve** | 3 956 tests collectes (preuve repo). Estimations clairement marquees comme telles. |
| Formulations / claims | **Eleve apres corrections** | FACT-1 (conformite AI Act), FACT-2 (no-PII garanti), FACT-5 (8/8 modules) corriges dans cette mission. |
| Transparence des limites | **Eleve** | Limites explicites dans `06_*.md` (auth par defaut, pas d'audit externe, CI partielle, monolithes, dette filesystem-first partielle). |

---

## 3. Risques residuels (decisions humaines requises avant transmission)

| ID | Risque | Severite | Decision requise | Action recommandee |
|---|---|---|---|---|
| RES-1 | Prenoms clients reels (`coralie`, `dominique`, `laurianne`) dans 4 fichiers trackes hors perimetre mission : `deploy/docker-compose.yml`, `docs/GUIDE_DEPLOIEMENT_ENTREPRISE.md`, `docs/SPEC_MULTI_USER_WORKSPACE.md`, `tests/test_organization_canonical.py` | **Modere** (PII faible, mais visible par auditeur prudent) | Apporteur : (a) sanitiser dans une mission dediee perimetre `deploy/` + `docs/` + tests ; OU (b) accepter explicitement la transmission en l'etat car les prenoms cohabitent avec mots de passe factices et sont visibles dans logs operationnels deja produits. | (a) **Recommande** : mission de sanitization courte (1-2h) sur ces 4 fichiers avant transmission. |
| RES-2 | Mentions clients **DICA FRANCE**, **Tarmac**, **Centrale Lille / Pr Zoubeir Lafhaj** dans documents valorisation (`RAPPORT_TECHNIQUE_*.md`, `DOSSIER_COMMISSAIRE_*.md`) | **Faible juridiquement** (les mentions sont strategiques pour defendre la borne haute) ; **modere reglementairement** si NDA / clauses confidentialite client non verifiees | Apporteur : confirmer que les mentions clients dans le pack respectent les NDA / engagements contractuels signes avec DICA, Tarmac, Centrale Lille. | Verification documentaire NDA cote apporteur avant transmission. Si doute, anonymiser en "Client A (PME conseil)", "Client B (incubateur public)", "Client C (chaire universitaire)". |
| RES-3 | Audit licence interne date 2025-02-08 (>14 mois) sans rapport `pip-licenses` annexe | **Modere** | Apporteur : re-executer `pip-licenses --format=markdown` et `pip-licenses --format=json --output-file=licenses_2026-05-10.json` sur `requirements.txt` courant et joindre en annexe AE-11. | Recommande avant transmission finale. Pas un blocker tant que l'auto-declaration est explicitement marquee comme telle (deja fait dans `legal/THIRD_PARTY_NOTICES.txt` apres correction FACT-3). |

---

## 4. Claims verifies

| Claim | Statut |
|---|---|
| HEAD courant transmis `1d05531a` | Verifie repo |
| HEAD verrouillage securite `c990cc55` | Verifie repo (ancetre) |
| HEAD analyse `fab5689a` | Verifie repo (ancetre) |
| Branche `diag-grow/transmission-evidence` | Verifie repo |
| 47 fichiers modifies depuis main | Verifie repo |
| `git diff 9a3a92b6..fab5689a` -> 920 fichiers / +217 192 / -14 434 | Verifie repo |
| 3 956 tests collectes (28 avril 2026) | Verifie repo (`A11_pytest_collect_only.txt`) |
| 7 ADR (ADR-001 a ADR-007) | Verifie repo |
| 17 modules proprietaires inventories | Verifie repo (`03_*.md`) |
| 23 lots de reconstruction | Verifie repo (`04_*.md`) |
| **Inventaire 03 : 1 205,5 / 1 593 / 2 090 j-h** | Verifie calcul |
| **Registre 04 : 1 230,5 / 1 622 / 2 130,5 j-h** | Verifie calcul (ecart de +29 j-h vs 03 explique) |
| **Rapport technique : 1 324 / — / 2 362 j-h** | Verifie calcul (date 17 avril) |
| TJM 650 EUR | Reference marche externe (preuve a annexer si demandee) |
| Coefficient qualite 0.95 | Auto-evaluation justifiee score 69/100 |
| Decote 12-20% | Auto-evaluation justifiee limites |
| **Conservateur : 662 000 a 850 000 EUR** | Verifie calcul |
| **Defendable equilibre : 958 000 a 1 054 000 EUR** | Verifie calcul (modele A : mediane 1 200 kEUR × decote) |
| **Offensif maitrise : 1 150 000 a 1 350 000 EUR** | Verifie calcul **conditionnel aux annexes externes** |
| 0 secret reel detecte | Verifie repo (10 mai 2026, HEAD `1d05531a`) |
| 0 hash Argon2id valide | Verifie repo (10 mai 2026) |
| Agent Zero MIT (Jan Tomasek) | Verifie (`legal/THIRD_PARTY_NOTICES.txt`) |
| 8 modules echantillonnes / 17 absents de l'upstream | Verifie repo (FACT-5 corrige) |

---

## 5. Claims rétrogradés (FACT-1 a FACT-6 corriges)

| ID | Avant | Apres |
|---|---|---|
| FACT-1 | "conformite AI Act / RGPD" (`02_*.md` §117, §223) | "alignement architectural avec exigences AI Act et RGPD (auto-evalue, sans certification externe)" |
| FACT-2 | "no-PII garanti" (`03_*.md` §94) | "no-PII par design (escalade non-diluable et tests adversariaux dedies dans la suite TDD)" |
| FACT-3 | "All 372 packages have been audited (2025-02-08)" (`legal/THIRD_PARTY_NOTICES.txt`) | Reformule comme self-declaration interne datee, avec recommandation explicite de re-scan avant transmission |
| FACT-5 | "8/8 modules confirmes 100% proprietaires" (`CONTROLE_AUDIT_PACK_*.md`) | "8 modules echantillonnes parmi 17 confirmes absents de l'upstream Agent Zero" + note sur les 9 autres modules par construction post-fork |
| FACT-6 | "271 commits" (claim sec dans `08_*.md` §100) | "~271 commits Amine (snapshot 5 mai 2026), exact a +/-1 a 4 commits selon date de coupe (270 sur HEAD `fab5689a`, 273 sur HEAD `1d05531a`)" |
| FACT-7 | Mediane brute 1 200 kEUR implicite dans rapport technique | Eclairage explicite dans `11_*.md` §4 et le present `12_*.md` §4.4 (cf. ci-dessous) |

---

## 6. Claims nécessitant des annexes externes

Aucune correction documentaire necessaire. Les annexes externes sont deja correctement signalees dans `01_*.md`, `06_*.md` §C, `07_*.md` et `RAPPORT_TECHNIQUE_*.md`. Liste consolidee :

| Annexe | Description | Statut transmission | Priorite |
|---|---|---|---|
| AE-1 | Factures DICA FRANCE (1 500 EUR/mois) | A annexer si traction commerciale a defendre | Haute (defense scenario offensif) |
| AE-2 | Preuves de paiement (releves bancaires correspondants) | Idem | Haute |
| AE-3 | Pieces R&D pre-repository (notes, brouillons, schemas) | A annexer si anteriorite PRISM a defendre | Haute |
| AE-4 | Dossier 4 brevets PRISM (numeros, dates, abstracts) | A annexer si valeur brevets revendiquee | Haute |
| AE-5 | Chaine de droits PRISM -> Evidence (cession, accord) | A annexer si pertinent | Modere |
| AE-6 | Echanges clients (emails de validation, demandes de fonctionnalites) | A annexer si pertinent | Modere |
| AE-7 | Confirmations pilotes terrain (Centrale Lille, Tarmac) | A annexer | Modere |
| AE-8 | Build Docker verifie (preuve d'execution recente) | Optionnel | Faible |
| AE-9 | Matrice des dependances externes et justification sources de marche | Optionnel (le repo contient deja `requirements.txt` + `THIRD_PARTY_NOTICES.txt`) | Faible |
| **AE-10** | Audit penetration externe / conformite externe (si disponible) | Atteneurait la decote 2-4% | Faible (decote deja appliquee) |
| **AE-11** | Rapport `pip-licenses` a jour (date <30 jours) | **Recommande** apres correction FACT-3 | Modere a haute |

---

## 7. Separation Agent Zero / Evidence

**Verdict** : **Robuste**.

| Aspect | Statut |
|---|---|
| Texte LICENSE / THIRD_PARTY_NOTICES.txt | OK |
| Phrase canonique "Agent Zero exclu de la valorisation" | Presente dans `01_*.md`, `02_*.md`, `04_*.md` §4, `08_*.md` |
| Tableau de delta module par module | OK (`02_*.md`) |
| Anti-double-comptage | OK (`04_*.md` §4) |
| Verification "absent de upstream" | 8 modules echantillonnes / 17 (post-FACT-5) — formulation prudente |

**Risque hostile** : "ce n'est qu'un fork Agent Zero" -> **defense robuste** par tableau delta + multiplicateur 6.7x + analogie Red Hat / Linux + 100% des modules de valeur cotee KOREV.

---

## 8. Cohérence valorisation

**Verdict** : **Coherente avec ecarts expliques**.

### 8.1 Recap des trois bases de calcul

| Base | Total cible | Methode | Coherence vs autres bases |
|---|---|---|---|
| Inventaire 03 | 1 593 j-h | Somme module par module | Reference inventaire |
| Registre 04 | 1 622 j-h | Lots agreges (modules + ADR + audit + RDBMS) | +29 j-h vs 03 explique en `04_*.md` §35 |
| Rapport tech | 1 324-2 362 j-h | COCOMO/ISBSG (etat 17 avril) | +/- 10% vs 03/04, ecart explique en `04_*.md` §34 |

### 8.2 Trois fourchettes de defense

| Position | Fourchette | Modele | Conditions |
|---|---|---|---|
| **Cible apport prudente** | **850 kEUR** | Modele B (registre 04) median-haut, decote 13.6% | Defense par scrutiny ligne par ligne. Sans annexes externes obligatoires. |
| Defendable equilibre | 958-1 054 kEUR | Modele A (rapport technique) mediane 1 200 kEUR × decote 12-20% | Acceptation de la base COCOMO/ISBSG. Annexes recommandees. |
| Offensif maitrise | 1 150-1 350 kEUR | Modele A borne haute + annexes externes | **Conditionnel** a l'acceptation des annexes AE-1 a AE-9. |

### 8.3 Phrase recommandee pour le commissaire

> La cible d'apport de 850 kEUR correspond a une lecture prudente du registre des 23 lots de reconstruction apres application d'un coefficient qualite 0,95 et d'une decote de prudence de 13,6% (centrale dans la fourchette 12-20% justifiee par les limites assumees : CI partielle, monolithes, mode sans auth par defaut, pas d'audit externe). Les scenarios superieurs (958-1 054 kEUR equilibre, 1 150-1 350 kEUR offensif) necessitent l'acceptation par le commissaire de la base de calcul COCOMO du rapport technique et / ou des annexes externes (factures clients, dossier brevets, pieces R&D pre-repository, chaine de droits PRISM -> Evidence, pilotes terrain documentes).

---

## 9. Sécurité / anti-secrets

**Verdict** : **POSITIF avec reserve hors perimetre (RES-1)**.

| Verification | Resultat |
|---|---|
| Hashes Argon2id valides | 0 (tous placeholders) |
| Tokens API exploitables (sk-, ghp_, AIza) | 0 |
| Cles privees (BEGIN PRIVATE KEY) | 0 |
| Sensitive untracked files | Deplaces hors Git le 10 mai 2026 |
| `deploy/users.demo.json` | Sanitize (commit `c990cc55`) |
| `deploy/users.json.example` | Sanitize (commit `aad0c102`) |
| `scripts/add_tarmac_user.py` | Sanitize (commit `c990cc55`) |
| **Risque residuel** | Prenoms clients dans 4 fichiers hors perimetre mission (RES-1, cf. §3) |

---

## 10. Licence / open-source

**Verdict** : **OK avec recommandation re-scan**.

| Element | Statut |
|---|---|
| MIT Agent Zero (Jan Tomasek) | OK (texte integral inclus) |
| Liste packages tiers cites (LiteLLM, Flask, aiohttp, etc.) | OK declaratif |
| "Pas de GPL/AGPL/SSPL" | Auto-declaration interne 2025-02-08 (FACT-3 reformule) |
| markdown-pdf -> shim local reportlab | OK documente |
| Re-scan licence avant transmission | **Recommande** (annexe AE-11) |

---

## 11. CI / tests / qualité

**Verdict** : **OK**.

| Element | Statut |
|---|---|
| 3 workflows GitHub Actions | OK |
| 3 956 tests collectes (28 avril 2026) | Preuve repo |
| 35 tests post-25 avril | Verifie par presence (execution non rejouee) |
| Limites CI documentees (mypy, ruff, SAST, Dependabot, Docker build) | OK (`05_*.md`, `06_*.md`) |
| Coverage | Non revendique sans preuve. Conforme. |

**Recommandation marginale** : rejouer `pytest --collect-only -q tests/` sur HEAD `1d05531a` pour confirmer le chiffre exact (~3 991 tests attendus).

---

## 12. Limites assumées

| Limite | Document de reference |
|---|---|
| Bus factor fondateur (Amine seul) | `06_*.md` §4 |
| Pas d'audit penetration externe | `06_*.md` §9 |
| CI partielle (pas de mypy strict, pas de SAST, pas de Dependabot) | `05_*.md`, `06_*.md` |
| Mode sans auth par defaut (`AUTH_LOGIN=""`) | `06_*.md`, `SECURITY.md` |
| Dette filesystem-first (partiellement levee par P0 RDBMS) | `00_*.md`, `04_*.md` Lot 22, `audit-hostile-valorisation/09-*.md` |
| Maturite TRL non revendiquee comme "production validee" | `01_*.md`, `RAPPORT_TECHNIQUE_*.md` |
| Dependances LLM providers (OpenAI, Anthropic, Google) | `06_*.md` |
| Auto-evaluation conformite (sans certification tiers) | `02_*.md` (post-FACT-1), `06_*.md`, `08_*.md` |

Toutes ces limites sont **explicitement assumees** dans le pack. Aucune n'est masquee. **Defense robuste face a l'objection "vous cachez les faiblesses"**.

---

## 13. Fourchette défendable recommandée

**Cible apport prudente : 850 kEUR**

Defendable par scrutiny ligne par ligne du registre 04 (modele B), decote centrale 13.6% dans la fourchette 12-20%, sans necessite d'annexes externes obligatoires. C'est la position recommandee pour la transmission initiale.

---

## 14. Fourchette à NE PAS défendre sans annexes externes

**Offensif maitrise : 1 150-1 350 kEUR**

Cette fourchette est mathematiquement defendable mais **conditionnelle a l'acceptation par le commissaire** de :
- Annexes AE-1 a AE-2 (factures et preuves de paiement DICA)
- Annexes AE-3 a AE-5 (R&D pre-repo, brevets, chaine de droits PRISM)
- Annexes AE-6 a AE-7 (echanges clients, pilotes terrain)
- Acceptation de la base de calcul COCOMO du rapport technique

**Position** : ne pas defendre cette fourchette en transmission initiale. La proposer seulement si demande explicite du commissaire et apres validation des annexes.

---

## 15. Mail de transmission recommandé

```text
Bonjour Madame / Monsieur,

Veuillez trouver ci-joint l'acces a la branche `diag-grow/transmission-evidence`
du depot KOREV / Evidence (HEAD post-verrouillage `<HEAD final>`, snapshot
d'analyse `fab5689a` du 5 mai 2026).

Le pack de valorisation est dans `docs/valuation/` (12 documents) :
- `00_REPO_DIAGNOSTIC.md` : etat technique du repo.
- `01_VALUATION_SCOPE.md` : perimetre incluant / excluant.
- `02_AGENT_ZERO_DELTA.md` : delta proprietaire vs base MIT Agent Zero.
- `03_EVIDENCE_PROPRIETARY_MODULES.md` : 17 modules proprietaires.
- `04_HOURS_RECONSTRUCTION_REGISTER.md` : 23 lots de reconstruction.
- `05_CODE_QUALITY_SNAPSHOT.md` : qualite (score 69/100, coefficient 0,95).
- `06_KNOWN_LIMITS_AND_REMEDIATION.md` : limites assumees + remediation.
- `07_DIAG_GROW_TRANSMISSION_NOTE.md` : note de couverture (ce document).
- `08_AUDIT_HOSTILE_VALUATION_PACK.md` : auto-audit anti-attaque hostile.
- `09_CORRECTIONS_DEF_A1_A2_A3.md` : corrections post-audit de controle.
- `10_FINAL_TRANSMISSION_CHECKLIST.md` : checklist finale + verrouillage securite.
- `11_FACTUAL_INTEGRITY_AUDIT.md` : audit hostile externe pre-transmission.
- `12_EXTERNAL_AUDITOR_READINESS_REPORT.md` : verdict final (le present document).

La distinction Agent Zero (MIT) / Evidence (proprietaire KOREV) est explicitee
dans `02_AGENT_ZERO_DELTA.md`. Les fourchettes de valorisation sont documentees
dans `04_HOURS_RECONSTRUCTION_REGISTER.md` et le rapport technique. La position
defendable retenue est **850 kEUR** (cible prudente, modele registre par lot,
decote 13,6%). Les scenarios superieurs (958-1 054 kEUR equilibre,
1 150-1 350 kEUR offensif) sont documentes mais conditionnels aux annexes
externes (factures clients, dossier brevets, pieces R&D pre-repo).

Les limites connues sont assumees dans `06_KNOWN_LIMITS_AND_REMEDIATION.md`.
La methode recommandee est le cout de reproduction (norme IVS 210). Nous
privilegions une valorisation defendable plutot qu'une survalorisation
artificielle.

Recommandations pour votre revue :
- Verifier d'abord `12_EXTERNAL_AUDITOR_READINESS_REPORT.md` pour le verdict
  global et `11_FACTUAL_INTEGRITY_AUDIT.md` pour la matrice claim-to-evidence.
- Puis lire `02_AGENT_ZERO_DELTA.md` pour la separation IP et `04_*.md` pour
  les fourchettes.

Cordialement,
[L'apporteur]
```

---

## 16. Liste des fichiers à transmettre

**Branche** : `diag-grow/transmission-evidence` integralement (47 fichiers modifies depuis main + tout le code applicatif inchange).

**Documents valorisation prioritaires** (ordre de lecture recommande pour Diag & Grow) :

1. `docs/valuation/12_EXTERNAL_AUDITOR_READINESS_REPORT.md` (le present, verdict + checklist)
2. `docs/valuation/11_FACTUAL_INTEGRITY_AUDIT.md` (matrice claim-to-evidence)
3. `docs/valuation/07_DIAG_GROW_TRANSMISSION_NOTE.md` (note de couverture)
4. `docs/valuation/02_AGENT_ZERO_DELTA.md` (separation IP)
5. `docs/valuation/04_HOURS_RECONSTRUCTION_REGISTER.md` (fourchettes)
6. `docs/valuation/06_KNOWN_LIMITS_AND_REMEDIATION.md` (limites assumees)
7. `docs/valuation/03_EVIDENCE_PROPRIETARY_MODULES.md` (inventaire)
8. `docs/valuation/05_CODE_QUALITY_SNAPSHOT.md` (qualite)
9. `docs/valuation/00_REPO_DIAGNOSTIC.md` (etat repo)
10. `docs/valuation/01_VALUATION_SCOPE.md` (perimetre)
11. `docs/valuation/08_AUDIT_HOSTILE_VALUATION_PACK.md` (auto-audit)
12. `docs/valuation/09_CORRECTIONS_DEF_A1_A2_A3.md` (historique corrections)
13. `docs/valuation/10_FINAL_TRANSMISSION_CHECKLIST.md` (checklist + verrouillage)
14. `docs/valuation/CONTROLE_AUDIT_PACK_2026-05-09.md` (audit de controle independant)
15. `docs/RAPPORT_TECHNIQUE_VALORISATION_EVIDENCE.md` (rapport technique principal)
16. `docs/DOSSIER_COMMISSAIRE_APPORTS_EVIDENCE.md` (dossier commissaire)
17. `audit-hostile-valorisation/01-*.md` a `09-*.md` (audit hostile interne)
18. `legal/THIRD_PARTY_NOTICES.txt` (notices tierces)
19. `SECURITY.md` (politique securite)
20. `docs/preuves-execution/PREUVES_TECHNIQUES_EXECUTION.md` + fichiers traces

**Annexes externes a fournir separement** : AE-1 a AE-11 (cf. §6).

---

## 17. Liste des fichiers à NE PAS transmettre

| Fichier / dossier | Raison | Action |
|---|---|---|
| `~/KOREV_PRIVATE_NON_GIT/evidence-sensitive-excluded-2026-05-09/` | Vault local des fichiers sensibles deplaces hors Git | Ne pas inclure |
| Branche locale `valuation/diag-grow-evidence-pack` | Branche d'analyse interne, contient potentiellement des references pre-sanitization | Ne pas pousser, ne pas transmettre |
| `deploy/users.json` reel (si present localement) | Fichier de production (jamais tracke) | Verifier localement avant transmission |
| `.env` reel (si present localement) | Variables d'environnement de production | Verifier localement |

---

## 18. Checklist finale Diag & Grow (apporteur)

L'apporteur Amine Mohamed doit valider explicitement chaque ligne avant tout partage d'acces externe :

- [ ] J'ai lu integralement `docs/valuation/12_EXTERNAL_AUDITOR_READINESS_REPORT.md` et je valide le verdict "PRET POUR TRANSMISSION AVEC RESERVES MAITRISEES".
- [ ] J'ai lu `docs/valuation/11_FACTUAL_INTEGRITY_AUDIT.md` et je valide la matrice claim-to-evidence et les corrections FACT-1 a FACT-6.
- [ ] **RES-1** : j'ai pris une decision documentee sur les prenoms clients dans `deploy/docker-compose.yml`, `docs/GUIDE_DEPLOIEMENT_ENTREPRISE.md`, `docs/SPEC_MULTI_USER_WORKSPACE.md`, `tests/test_organization_canonical.py` :
  - [ ] OPTION A : sanitization dans une mission dediee (recommande)
  - [ ] OPTION B : transmission en l'etat (acceptation explicite)
- [ ] **RES-2** : j'ai verifie que les mentions DICA / Tarmac / Centrale Lille dans le pack respectent les NDA / clauses confidentialite signes.
- [ ] **RES-3** : j'ai re-execute `pip-licenses` sur `requirements.txt` courant et je joins le rapport en annexe AE-11 (recommande).
- [ ] J'ai verifie qu'aucun `deploy/users.json` reel ni `.env` reel ne traine localement.
- [ ] J'ai prepare les annexes externes AE-1 a AE-9 selon la fourchette de defense visee (850 kEUR ne necessite aucune annexe obligatoire ; 958+ kEUR recommande AE-1 et AE-3 ; 1 150+ kEUR exige toutes les annexes).
- [ ] J'ai verifie que la branche partagee est **bien `diag-grow/transmission-evidence`** et non `valuation/diag-grow-evidence-pack` ni `main`.
- [ ] Je donne mon accord pour la transmission a Diag & Grow / commissaire aux apports.

---

## 19. Verdict final

**STATUT** : **PRET POUR TRANSMISSION AVEC RESERVES MAITRISEES**

**Blockers** : aucun.

**Reserves** : 3 decisions humaines (RES-1, RES-2, RES-3) documentees au §3.

**Defense recommandee** : **850 kEUR (cible prudente)**, defendable par scrutiny ligne par ligne du registre 04 sans annexes obligatoires. Les scenarios superieurs sont documentes mais conditionnels.

**Risque de decote** :
- **Faible** sur la cible 850 kEUR
- **Modere** sur la fourchette 958-1 054 kEUR (sans annexes)
- **Modere a eleve** sur la fourchette 1 150-1 350 kEUR (sans annexes)

**Top 3 actions de remediation conditionnelle (apporteur)** :
1. Sanitiser les 4 fichiers hors perimetre (RES-1) — 1-2h.
2. Re-executer `pip-licenses` (RES-3) — 15 min.
3. Verifier NDA clients (RES-2) — vérification documentaire.

---

*Rapport produit le 10 mai 2026 sur la branche `diag-grow/transmission-evidence` avant push de la mission "Audit contradictoire total".*
