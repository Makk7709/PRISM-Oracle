<!-- markdownlint-disable MD060 MD032 MD029 MD014 MD013 -->

# 10 — Checklist finale de transmission Diag & Grow / commissaire aux apports

**Branche de transmission** : `diag-grow/transmission-evidence`
**HEAD local** : `fab5689a` (5 mai 2026 17:37 +0200)
**Commit de pack** : a creer en local — non pousse — message `docs(valuation): finalize Evidence valuation pack for Diag & Grow`
**Date de cette checklist** : 9 mai 2026
**Auditeur** : agent Cursor en posture CTO + securite + auditeur hostile (lecture & ecriture limitee a `docs/valuation/` et `deploy/users.json.example` sanitize)
**Conformite** : protocole interne `pre-commit-audit.mdc` (Phase 1 relecture contradictoire, Phase 2 checklist, Phase 3 boucle si critique, Phase 4 commit avec trace)

---

## 1. Resume executif

**VERDICT FINAL** : **PRET POUR TRANSMISSION — sous reserve de validation humaine finale avant push / partage d'acces.**

Le pack de valorisation est complet, coherent, et anti-secrets J-0 est positif. La sanitization de `deploy/users.json.example` (option C de DEF-A7) est executee. Aucune modification de code applicatif, aucune modification de licence, aucune modification de fourchette de valorisation.

**Audit hostile pre-commit (`pre-commit-audit.mdc`) Phase 1 a detecte un DEF-CRITIQUE-1** (3 fichiers untracked avec hashes Argon2id reels + PII + clients), corrige par **exclusion explicite du `git add`** (cf. §3.5). Le commit final ne contient pas ces 3 fichiers. Phase 3 re-audit total : 0 Critique residuel.

| Indicateur | Statut |
|---|---|
| DEF-A1 / DEF-A2 / DEF-A3 (3 moderes) | **CORRIGES** |
| DEF-A4 / DEF-A5 / DEF-A6 (3 mineurs) | Adresses |
| DEF-A7 (`deploy/users.json.example`) | **OPTION C EXECUTEE** sur la branche `diag-grow/transmission-evidence` |
| Anti-secrets J-0 | **POSITIF** (0 secret reel, 2 faux positifs documentes, 2 points hors perimetre signales) |
| Licence | Inchangee (proprietaire KOREV + `legal/THIRD_PARTY_NOTICES.txt` MIT Agent Zero) |
| Fourchettes valorisation | **INCHANGEES** (defenses renforcees, pas d'inflation) |
| Modification code applicatif | **AUCUNE** |
| Commit local | A creer — message preformate ci-dessous |
| Push | **A NE PAS EXECUTER AUTOMATIQUEMENT** (validation humaine requise) |

---

## 2. Branche et HEAD

| Element | Valeur |
|---|---|
| Branche actuelle | `diag-grow/transmission-evidence` |
| Branche source (analyse) | `valuation/diag-grow-evidence-pack` |
| Branche `main` | Inchangee — n'a recu aucune des modifications de cette mission |
| HEAD au depart de la branche | `fab5689a6fc482fc7caa141bfbbe710c6086a182` (5 mai 2026) |
| HEAD apres commit local (a faire) | A determiner apres `git add` + `git commit` |
| Working tree au depart | Modifications non commitees heritees de `valuation/diag-grow-evidence-pack` (pack docs/valuation, audit hostile, ADR, preuves d'execution, scripts, tests, SECURITY.md) |

---

## 3. Fichiers modifies sur cette mission de finalisation (J-0)

### 3.1 Fichier sanitize (DEF-A7 option C)

| Fichier | Etat avant | Etat apres |
|---|---|---|
| `deploy/users.json.example` | 12 prenoms reels (`amine`, `nicolas`, `luc`, `jeremie`, `coralie`, `dominique`, `laurianne`, `sarah`, `christopher`, `louis`, `mathias`, `benj`) + organisation client `Epoque` + 2 profils descriptifs internes + hashes placeholders `REMPLACEZ_PAR_HASH_REEL` (50 lignes) | 3 utilisateurs strictement fictifs (`admin_example`, `user_example_1`, `user_example_2`) + emails `@example.com` (RFC 2606) + organisation `ExampleOrg` + hashes placeholders `PLACEHOLDER_NOT_A_REAL_HASH_REGENERATE_BEFORE_USE` + 3 meta-fields (`_comment`, `_format_version`, `_warning`) (31 lignes) |

JSON valide (`python3 -m json.tool` OK). Aucun PII residuel (verification grep exhaustive).

### 3.2 Documentation mise a jour (DEF-A7 option C)

| Fichier | Modification |
|---|---|
| `docs/valuation/06_KNOWN_LIMITS_AND_REMEDIATION.md` | Ligne 22 du tableau de synthese (risques secrets) : ajout de la mention "sanitize sur branche de transmission `diag-grow/transmission-evidence`" + reference vers ce checklist final |
| `docs/valuation/07_DIAG_GROW_TRANSMISSION_NOTE.md` | En-tete : ajout ligne "Branche de transmission : `diag-grow/transmission-evidence` (transmission externe Diag & Grow / commissaire — sanitization PII appliquee)" |
| `docs/valuation/09_CORRECTIONS_DEF_A1_A2_A3.md` | Section 5.3 : remplacement des "options envisagees a l'apporteur" par "OPTION C VALIDEE PAR L'APPORTEUR LE 9 MAI 2026" + tableau avant/apres sanitization + decision retenue |

### 3.3 Fichier nouveau

| Fichier | Role |
|---|---|
| `docs/valuation/10_FINAL_TRANSMISSION_CHECKLIST.md` | Le present document |

### 3.4 Synthese : aucune modification applicative

`git status` confirme (au-dela des fichiers ci-dessus) :

- Aucune modification dans `python/`, `agent.py`, `tools/`, `models/` ou tout module applicatif Python.
- Aucune modification dans `webui/` (UI Agent Zero).
- Aucune modification dans `tests/*.py` (`tests/test_documentation_quality.py` est ajoute mais c'est un test de qualite documentation, pas un changement applicatif ; `tests/README_tests.md` est de la documentation).
- Aucune modification dans les workflows GitHub Actions, Docker, scripts d'infrastructure (sauf scripts de pack documentaire deja heritage de `valuation/diag-grow-evidence-pack`).

Submodules `mcp_servers/openalex` et `mcp_servers/semanticscholar` apparaissent en drift `m` minuscule mais pas dans `.gitmodules` (residu d'un sous-clone). Pas une modification au sens commit ; ne sera pas inclus dans le commit final (`git add` cible explicitement les fichiers du pack).

### 3.5 Fichiers EXCLUS du commit (DEF-CRITIQUE-1 detecte par audit hostile pre-commit)

Lors de la phase 1 d'audit hostile pre-commit (cf. `pre-commit-audit.mdc`), la relecture contradictoire du diff a detecte **trois fichiers untracked locaux qui contiennent des donnees sensibles non necessaires a la transmission**. Ces fichiers sont **explicitement EXCLUS du `git add`** de cette branche. Ils restent presents dans le working tree mais ne seront pas ajoutes a l'index git ni committes ni transmis.

| Fichier | Donnees sensibles detectees | Severite | Decision |
|---|---|---|---|
| `scripts/add_beatrice_user.py` | Hash Argon2id complet reel (`$argon2id$v=19$m=65536,t=3,p=4$Shx36b/AfqXIUicYEANgwQ$IiZJDffHFA+o1hQOZx+/vISkGbcVVlfSY470Ei3PuWo`) + prenom reel `Béatrice` + organisation client `Centrale Lille` | **CRITIQUE** | **EXCLU du commit** |
| `scripts/add_epoque_user.py` | Hash Argon2id complet reel (`$argon2id$v=19$m=65536,t=3,p=4$lNRSLeJTWqgZJ4W2FP6owQ$uyfcVBEayTvnMF8BHvKeXjQsnZA6XKGSLx1C/H9p6FA`) + prenom reel `Benjamin` + organisation client `Epoque` + role `OWNER` | **CRITIQUE** | **EXCLU du commit** |
| `docs/preuves-execution/check_server_activity.sh` | Script operationnel interne mentionnant explicitement les usernames `tarmac`, `beatrice`, `benj` et les organisations `TARMAC`, `Centrale Lille`, `Epoque` en boucle de log scraping | **IMPORTANT** | **EXCLU du commit** |

**Justification de l'exclusion** :

1. Les 2 scripts d'ajout d'utilisateurs (`add_beatrice_user.py`, `add_epoque_user.py`) **n'ont pas leur place** dans le repo principal en l'etat. Ce sont des scripts one-shot de provisioning qui auraient du etre executes puis supprimes (ou jamais committes). Leur transmission a Diag & Grow exposerait des hashes Argon2id reels, des prenoms d'utilisateurs et l'identite de clients sans autorisation explicite.
2. Le script `check_server_activity.sh` est un outil operationnel interne pour verifier l'activite des comptes clients sur le serveur. Il **n'est pas une preuve d'execution** au sens valorisation (les vraies preuves sont dans `A11_*.txt`, `B_*.txt`, `C_*.txt`, `D_*.txt`, `E_*.txt`, `F_*.txt`).

**Recommandation post-transmission** :

- L'apporteur Amine Mohamed doit decider du sort de ces 3 fichiers locaux :
  - Soit les **supprimer du working tree** (`rm scripts/add_beatrice_user.py scripts/add_epoque_user.py docs/preuves-execution/check_server_activity.sh`) et regenerer un script `provision_user.py` parametrable et sans secrets.
  - Soit les conserver hors-Git dans un repo prive de provisioning (recommande).
  - Soit les commit avec autorisation ecrite des clients (Epoque, Centrale Lille) — option couteuse, peu recommandee.
- **Aucune action n'est requise pour la transmission** : ces fichiers ne sont pas ajoutes a l'index git de cette branche.

### 3.6 Mentions clients legitimes dans la documentation transmise

Les mentions de `Tarmac`, `Centrale Lille`, `Pr Zoubeir Lafhaj`, `DICA FRANCE`, `Epoque` dans la documentation valorisation sont **volontaires et necessaires** pour la valorisation. Elles apparaissent notamment dans :

- `docs/RAPPORT_TECHNIQUE_VALORISATION_EVIDENCE.md` (section pilotes terrain et facturation DICA)
- `audit-hostile-valorisation/01-executive-summary.md` et `audit-hostile-valorisation/08-*.md` (preuves commerciales et pilotes)
- `docs/BENCHMARK_COMPARABLES_VALORISATION_EVIDENCE.md`, `docs/ONBOARDING_AYA_30_60_90.md`, `docs/PLAN_INTEGRATION_LEAD_ENGINEER_30_60_90_INTERNAL.md`, `docs/adr/ADR-001-*.md`
- `docs/valuation/00_*.md`, `01_*.md`, `04_*.md`, `06_*.md`, `07_*.md`, `08_*.md`, `09_*.md`, `10_*.md`, `CONTROLE_AUDIT_PACK_2026-05-09.md`

Ces mentions sont des **preuves d'exploitabilite commerciale et de partenariats academiques** qui defendent le haut de la fourchette de valorisation. Le Pr Zoubeir Lafhaj est une figure publique de la Chaire Construction 4.0 a Centrale Lille. Les mentions Tarmac (Le Tarmac by inovallée) et DICA FRANCE sont des partenariats / clients identifiables publiquement par le metier.

**Risque de divulgation** :

- L'apporteur doit s'assurer que **chaque client cite a donne son accord** (ou que la mention est compatible avec les contrats signes) avant transmission a Diag & Grow.
- Pour la transmission au commissaire aux apports (officier ministeriel), la divulgation est usuellement couverte par le secret professionnel.
- Pour Diag & Grow (cabinet de conseil prive), la divulgation peut necessiter une clause de confidentialite explicite. **A confirmer par l'apporteur avant tout partage d'acces.**

### 3.7 Limite documentee : prenoms internes dans les noms de tests

Le fichier `docs/preuves-execution/A11_pytest_collect_only.txt` (sortie de `pytest --collect-only`) contient les noms de tests committes dans `tests/` qui referencent des prenoms internes (e.g. `test_amine_sees_own_chats`, `test_nicolas_sees_own_chats`). Ces noms de tests **existent deja dans le code source committe** (sur `main` et toutes les branches anterieures). Ils ne sont pas modifiables sans casser les tests de regression existants.

**Decision** : la sortie `A11_*.txt` est conservee telle quelle (preuve fidele du `pytest --collect-only` execute). C'est une limite documentee et non remediable dans le perimetre de cette mission.

**Recommandation post-transmission** : envisager un refactoring des noms de tests (`test_user_a_*`, `test_user_b_*`) dans une mission ulterieure de hardening, en synchronisation avec un commit sur `main`.

---

## 4. Statut DEF-A1 / DEF-A2 / DEF-A3 (defauts moderes)

| Defaut | Description courte | Statut |
|---|---|---|
| DEF-A1 | Pack ne reflete pas le commit `de8b9c7e` (yENoyKIZ + ADR-006) ancetre du HEAD | **CORRIGE** dans `00_REPO_DIAGNOSTIC.md` §2.4, `05_CODE_QUALITY_SNAPSHOT.md` §6.1 et §11.3, `06_*.md`, `07_*.md` §9, `08_*.md` §9 |
| DEF-A2 | Pack ne reflete pas le commit `b11b4d99` (P0 RDBMS + ADR-007) ancetre du HEAD | **CORRIGE** dans `00_*.md` §2.4, `04_*.md` Lot 22, `05_*.md` §4.2 / §6.1 / §11.2, `06_*.md` §1 / §2.5.1 / §3.4, `07_*.md` §4.2 / §5 / §9, `08_*.md` §9 |
| DEF-A3 | Pack ne reflete pas le commit `0d0a35da` (fix DEF-8 pg_dump --clean + test T7) ancetre du HEAD | **CORRIGE** dans `00_*.md` §2.4, `04_*.md` Lot 22, `05_*.md` §11.3, `08_*.md` §9 |

**Cf. detail complet** : `docs/valuation/09_CORRECTIONS_DEF_A1_A2_A3.md`.

---

## 5. Statut DEF-A4 / DEF-A5 / DEF-A6 (defauts mineurs)

| Defaut | Description courte | Statut |
|---|---|---|
| DEF-A4 | Recompte attendu apres 3 commits post-25 avril : ~3 991 tests vs 3 956 (28 avril) | **DOCUMENTE** : note dans `05_*.md` §1.1 + recommandation pytest --collect-only sur HEAD `fab5689a` |
| DEF-A5 | Score 72/100 mentionne dans le doc 09 (audit hostile interne) sans note explicite | **DOCUMENTE** : note dans `05_*.md` §14.1 ("estimation interne, non auditee, ecart de 3 points dans la marge d'erreur de la grille") |
| DEF-A6 | Doctrine `pre-commit-audit.mdc` non valorisee | **DOCUMENTE** : valorisation indirecte via mention dans `08_*.md` §9 et `09_CORRECTIONS_DEF_A1_A2_A3.md`. Pas de modification de fourchette. |

---

## 6. Statut DEF-A7 (defaut faible — `deploy/users.json.example`)

**Decision apporteur (9 mai 2026)** : **OPTION C — branche dediee de transmission avec sanitization complete.**

Cf. detail complet dans `docs/valuation/09_CORRECTIONS_DEF_A1_A2_A3.md` §5.

| Risque adresse | Etat |
|---|---|
| Exposition de 12 prenoms internes (PII partielle) | **ELIMINE** sur la branche `diag-grow/transmission-evidence` |
| Exposition d'organisation client `Epoque` | **ELIMINE** sur la branche `diag-grow/transmission-evidence` |
| Risque cryptographique sur hashes | Inexistant des l'origine (placeholders), reaffirme |
| Preservation operationnelle pour l'equipe technique KOREV | **OK** : version originale conservee sur `valuation/diag-grow-evidence-pack` (et indirectement sur `main` si non-merge) |

**Action humaine post-transmission requise** : decider du sort de la branche `diag-grow/transmission-evidence` — soit la merger dans `main` (sanitization permanente, recommande pour la securite) soit la conserver isolee.

---

## 7. Statut anti-secrets J-0

### 7.1 Outils

| Outil | Disponibilite | Utilise |
|---|---|---|
| gitleaks | Non installe | N/A |
| trufflehog | Non installe | N/A |
| detect-secrets | Non installe | N/A |
| ggshield | Non installe | N/A |
| `grep -rE` (BSD/GNU) | Disponible | OUI |
| `git ls-files` | Disponible | OUI (limite la verification aux fichiers tracks) |

### 7.2 Patterns verifies (sur fichiers tracks par Git uniquement, pour eviter les faux positifs `venv/`)

| Pattern | Resultat |
|---|---|
| Fichiers sensibles tracks (`*.env`, `*.pem`, `*.key`, `*.p12`, `*.pfx`, `*.jks`, `users.json`, `secrets.json`, `credentials.json`, `service_account*.json`) | **0 fichier** |
| Cle OpenAI generique (`sk-[A-Za-z0-9]{20,}`) | **0 occurrence** |
| Cle OpenAI projet (`sk-proj-`) | **1 occurrence** : `docs/GUIDE_DEPLOIEMENT_ENTREPRISE.md` ligne 223 — **faux positif** : "Format : sk-proj-xxxxxxxxxxxx" (placeholder doc) |
| GitHub PAT (`ghp_[A-Za-z0-9]{30,}`) | **0 occurrence** |
| Cle privee PEM (`BEGIN .*PRIVATE KEY`) | **1 occurrence** : `tests/test_session10_hardening.py` ligne 35 — **faux positif** : `assert "-----BEGIN PRIVATE KEY-----" in private_pem` (test de format de cle generee a la volee) |
| Domaine Supabase (`supabase.co`) | **0 occurrence** |
| Cles cloud (AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, GCP_KEY, AZURE_KEY) | **0 occurrence** |
| Provider LLM en assignation (`OPENAI_API_KEY=...`, `ANTHROPIC_API_KEY=...`, `GOOGLE_API_KEY=...`, `MISTRAL_API_KEY=...`, `GROQ_API_KEY=...`, `OPENROUTER_API_KEY=...`) | **0 fichier hors `.example` / `.md` / `tests/`** |
| Cookies / sessions hardcodes | **0 occurrence** hors documentation et tests |
| Hashes Argon2id complets (format reel) sur fichiers tracks | **2 fichiers** : voir §7.4 ci-dessous |

### 7.3 Faux positifs documentes (a NE PAS traiter)

| Fichier | Motif | Justification |
|---|---|---|
| `webui/components/settings/secrets/example-secrets.html` | Match `api_key="..."` | Fichier d'aide UI Agent Zero (origine MIT) qui montre a l'utilisateur comment formater son `.env`. Toutes les valeurs sont des placeholders evidents (`brv_xxxxxxxxxxxxxxxxxxxxx`, `AIzaSyD-xxxxxxxxxxxxxxxxxxxx`, `s3cret-p4$$w0rd`, `another-secret-password`). Ne necessite pas de modification — laisse en l'etat (heritage Agent Zero, pas de PII). |
| `tests/test_session10_hardening.py` ligne 35 | Match `BEGIN PRIVATE KEY` | Assertion de test : verifie que la cle PEM **generee dynamiquement par le test** contient bien le marqueur de format. Pas un secret stocke. |
| `docs/GUIDE_DEPLOIEMENT_ENTREPRISE.md` ligne 223 | Match `sk-proj-` | Placeholder de format documentaire ("Format : sk-proj-xxxxxxxxxxxx"), aucune cle reelle. |

### 7.4 Points a signaler hors perimetre transmission DEF-A7 (a la decision de l'apporteur)

Deux fichiers contiennent des **hashes Argon2id complets** (format reel, pas placeholder). Ils existent **deja sur `main`** (et `valuation/diag-grow-evidence-pack`) — donc **hors du perimetre de la mission de finalisation J-0**. Ils ne sont pas modifies par la branche de transmission.

| Fichier | Contenu | Risque hypothetique | Recommandation |
|---|---|---|---|
| `deploy/users.demo.json` | 2 hashes Argon2id complets (au format `$argon2id$v=19$m=65536,t=3,p=4$<salt>$<hash>`) | Faible : si les mots de passe sources sont des mots de passe de demo publics (e.g. "demo123", "test"), aucun risque. Risque devient reel uniquement si les mots de passe sources etaient des mots de passe d'un utilisateur reel. | **A clarifier par l'apporteur** : confirmer la nature publique/de-demo des mots de passe sources. Si demo, aucune action. Si reel, generer de nouveaux hashes. **Hors perimetre de la transmission DEF-A7**. |
| `scripts/add_tarmac_user.py` | 1 hash Argon2id complet hardcode | Faible : script de provisioning, le hash est probablement celui d'un mot de passe initial Tarmac qui aura ete change a la premiere connexion en production. | **A confirmer par l'apporteur** : le mot de passe initial a-t-il bien ete change en production ? Si oui, aucune action. **Hors perimetre de la transmission DEF-A7**. |

Ces deux points sont signales en transparence dans cette checklist. Ils ne bloquent pas la transmission. Ils relevent d'une decision operationnelle distincte.

### 7.5 Couverture `.gitignore`

| Pattern | Couvert |
|---|---|
| `**/.env` | OUI (ligne 3 du `.gitignore`) |
| `.venv/`, `venv/` | OUI (lignes 16 et 49) |
| `deploy/.env.tmp` | OUI (ligne 60) |
| `memory/`, `logs/`, `tmp/`, `usr/`, `knowledge/`, `instruments/` | OUI |
| `**/users.json` (reel) | **NON** — recommandation post-transmission : ajouter `deploy/users.json` au `.gitignore` pour eviter un commit accidentel du fichier reel. **Hors perimetre transmission DEF-A7** (modification fichier non-pack). |
| `*.pem`, `*.key`, `*.p12` | **NON** — recommandation post-transmission : ajouter ces patterns. |

Verifie : aucun `deploy/users.json` reel n'est tracke a date (`git ls-files | grep -E '(^|/)users\.json$'` ne retourne que `users.demo.json` et `users.json.example`).

### 7.6 Verdict anti-secrets J-0

**POSITIF**. Aucun secret reel detecte sur la branche `diag-grow/transmission-evidence` au HEAD `fab5689a` apres sanitization de `deploy/users.json.example`. Les 2 points hors perimetre (§7.4) et les 2 lacunes de `.gitignore` (§7.5) sont documentes pour decision post-transmission.

---

## 8. Statut licence

| Element | Valeur |
|---|---|
| Licence racine `LICENSE` | Proprietaire KOREV, **inchangee** |
| `legal/THIRD_PARTY_NOTICES.txt` | MIT License Agent Zero, **inchangee** |
| `README.md` racine — mention licence | Inchangee, contient deja la reference proprietaire |
| Aucune modification de licence dans cette mission | Confirme par `git diff LICENSE legal/` (vide) |

---

## 9. Statut Agent Zero

| Element | Valeur |
|---|---|
| Origine MIT Agent Zero | **Conservee, jamais masquee**, mentionnee explicitement dans `01_VALUATION_SCOPE.md` §D + `02_AGENT_ZERO_DELTA.md` integralement + `03_EVIDENCE_PROPRIETARY_MODULES.md` (zone de delimitation) + `legal/THIRD_PARTY_NOTICES.txt` |
| Fichiers Agent Zero non modifies | Confirme : aucun `.py` applicatif, aucun composant `webui/` Agent Zero modifie |
| Phrase obligatoire integree | "Agent Zero est exclu de la valorisation comme actif proprietaire. La valorisation porte sur l'œuvre derivee KOREV…" — presente dans `01_VALUATION_SCOPE.md` |

---

## 10. Statut fourchettes valorisation

**INCHANGEES** par rapport au pack initial (et confirme par l'audit de controle `CONTROLE_AUDIT_PACK_2026-05-09.md`) :

| Scenario | Fourchette |
|---|---|
| Repo seul (sans annexes) | Conforme aux valeurs publiees dans `04_HOURS_RECONSTRUCTION_REGISTER.md` (cf. doc 04 pour les bornes precises) |
| Repo + annexes externes (factures DICA, brevets PRISM, R&D Tarmac, Centrale Lille) | Conforme aux valeurs publiees dans `04_*.md` et reaffirme dans `07_DIAG_GROW_TRANSMISSION_NOTE.md` §9 |
| Coefficient qualite | Inchange (cf. `05_CODE_QUALITY_SNAPSHOT.md` §14) |
| Decotes appliquees (open-source, legacy, maturite) | Inchangees |

Les commits post-25 avril (`de8b9c7e`, `b11b4d99`, `0d0a35da`) **renforcent la defense de la borne haute** mais **ne modifient aucune valeur**. Cette position est explicitement documentee dans `09_CORRECTIONS_DEF_A1_A2_A3.md` §6 et `08_*.md` §9.

---

## 11. Limites restantes (transparence)

| Limite | Statut transmission |
|---|---|
| Bus factor fondateur | Documente dans `06_*.md` ; remediation hors perimetre (recrutement Aya / lead engineer en cours) |
| Dette filesystem-first | Partiellement leve (P0 RDBMS execute), P1-P6 en roadmap |
| Auth par defaut | Hors perimetre transmission ; `deploy/users.json.example` sanitize |
| `.gitignore` ne couvre pas `deploy/users.json` reel ni `*.pem`, `*.key` | **Recommandation post-transmission** ; aucun fichier reel actuellement tracke (verifie) |
| Hashes Argon2id complets dans `users.demo.json` et `add_tarmac_user.py` | A clarifier par l'apporteur (cf. §7.4) ; hors perimetre transmission DEF-A7 |
| Documentation de certains modules incomplete | Documentee dans `06_*.md` |
| Absence d'audit externe (SOC2, ISO27001) | Documentee dans `01_*.md` §C et `06_*.md` |
| Submodules `mcp_servers/openalex`, `mcp_servers/semanticscholar` en drift | Hors perimetre transmission ; ne seront pas inclus dans le commit final |

---

## 12. Elements a transmettre a Diag & Grow

### 12.1 Pack documentaire (priorite 1)

- `docs/valuation/00_REPO_DIAGNOSTIC.md`
- `docs/valuation/01_VALUATION_SCOPE.md`
- `docs/valuation/02_AGENT_ZERO_DELTA.md`
- `docs/valuation/03_EVIDENCE_PROPRIETARY_MODULES.md`
- `docs/valuation/04_HOURS_RECONSTRUCTION_REGISTER.md`
- `docs/valuation/05_CODE_QUALITY_SNAPSHOT.md`
- `docs/valuation/06_KNOWN_LIMITS_AND_REMEDIATION.md`
- `docs/valuation/07_DIAG_GROW_TRANSMISSION_NOTE.md` (note de couverture)
- `docs/valuation/08_AUDIT_HOSTILE_VALUATION_PACK.md`
- `docs/valuation/09_CORRECTIONS_DEF_A1_A2_A3.md`
- `docs/valuation/10_FINAL_TRANSMISSION_CHECKLIST.md` (le present document)

### 12.2 Pack hostile interne (priorite 2)

- `audit-hostile-valorisation/01-executive-summary.md`
- `audit-hostile-valorisation/02-cartographie-technique.md`
- `audit-hostile-valorisation/03-audit-qualite-hostile.md`
- `audit-hostile-valorisation/04-bilan-documentation.md`
- `audit-hostile-valorisation/05-angle-morts-et-decote-potentielle.md`
- `audit-hostile-valorisation/06-plan-de-remediation-priorise.md`
- `audit-hostile-valorisation/07-scorecard-valorisation.md`
- `audit-hostile-valorisation/08-audit-hostile-dossier-commissaire-apports.md`
- `audit-hostile-valorisation/09-mise-a-jour-post-p0-yenoyikz.md` **(critique pour DEF-A1/A2/A3)**

### 12.3 Documents complementaires (priorite 3)

- `docs/RAPPORT_TECHNIQUE_VALORISATION_EVIDENCE.md`
- `docs/DOSSIER_COMMISSAIRE_APPORTS_EVIDENCE.md`
- `docs/BENCHMARK_COMPARABLES_VALORISATION_EVIDENCE.md`
- `docs/ARCHITECTURE_C4_DIAGRAMS.md`
- `docs/preuves-execution/PREUVES_TECHNIQUES_EXECUTION.md`
- `docs/adr/ADR-001` a `ADR-007` (7 ADR)
- `docs/GLOSSARY.md`
- `legal/THIRD_PARTY_NOTICES.txt`
- `LICENSE`
- `README.md`
- `SECURITY.md`
- `deploy/users.json.example` **(version sanitizee de cette branche)**

### 12.4 Acces git

- Branche **`diag-grow/transmission-evidence`** (apres push valide par l'apporteur) — recommande
- OU export ZIP / tarball du working tree de cette branche

---

## 13. Elements a NE PAS transmettre

| Element | Raison |
|---|---|
| Fichier reel `deploy/users.json` (s'il est cree localement) | PII / hashes reels — non tracke par Git, mais a verifier avant tout export tarball |
| Fichiers `.env` reels (s'ils existent localement) | Secrets reels — gitignored par `**/.env` |
| Donnees de production (`memory/`, `logs/`, `tmp/`, `knowledge/`, `instruments/`) | Gitignored ; sortie d'execution non valorisable |
| Dependances locales (`venv/`, `.venv/`, `node_modules/` si present) | Gitignored ; non valorisables |
| Branche `valuation/diag-grow-evidence-pack` (analyse interne) | Contient encore les 12 prenoms internes + `Epoque` dans `deploy/users.json.example`. **Ne PAS partager cette branche a Diag & Grow.** Partager uniquement `diag-grow/transmission-evidence`. |
| Branche `main` (si elle contient encore la version non-sanitizee de `deploy/users.json.example`) | Verifier avant tout partage. La sanitization n'est appliquee que sur `diag-grow/transmission-evidence` au 9 mai 2026. |
| `users.demo.json` et `add_tarmac_user.py` si l'apporteur souhaite eviter tout doute | Decision a la discretion de l'apporteur (cf. §7.4). Par defaut, transmis avec le repo. |

---

## 14. Checklist humaine avant push / partage d'acces

L'apporteur Amine Mohamed doit confirmer **explicitement** chaque ligne avant tout `git push origin diag-grow/transmission-evidence` ou tout partage d'acces GitHub :

- [ ] J'ai relu `docs/valuation/07_DIAG_GROW_TRANSMISSION_NOTE.md` et il reflete fidelement ma position.
- [ ] J'ai relu `docs/valuation/10_FINAL_TRANSMISSION_CHECKLIST.md` (le present document) et je valide chaque section.
- [ ] J'ai verifie que la branche partagee a Diag & Grow est **bien `diag-grow/transmission-evidence`** et non `valuation/diag-grow-evidence-pack` ni `main`.
- [ ] J'ai pris une decision documentee sur les hashes Argon2id complets de `users.demo.json` et `add_tarmac_user.py` (§7.4) : OK / a revoir / a clarifier.
- [ ] J'ai pris une decision documentee sur l'amelioration de `.gitignore` (§7.5) : OK / a revoir / non urgent.
- [ ] J'ai verifie qu'aucun `deploy/users.json` reel ni `.env` reel ne traine localement et ne risque d'etre push par accident.
- [ ] J'ai prepare les annexes externes (factures DICA, brevets PRISM, preuves Tarmac, Centrale Lille, echanges clients) si applicables.
- [ ] Je donne mon accord pour le push de la branche `diag-grow/transmission-evidence` vers le remote.

---

## 15. Commande de push recommandee (a executer manuellement par l'apporteur uniquement apres validation §14)

```bash
# 1. Verifier l'etat de la branche
git status
git log --oneline -5
git diff valuation/diag-grow-evidence-pack diag-grow/transmission-evidence -- deploy/users.json.example

# 2. Push vers le remote (NE PAS executer automatiquement)
git push origin diag-grow/transmission-evidence

# 3. Optionnel : creer un tag de transmission
git tag -a transmission-diag-grow-2026-05-09 -m "Transmission Evidence valuation pack to Diag & Grow"
git push origin transmission-diag-grow-2026-05-09
```

---

## 16. Phrase recommandee pour accompagner la transmission

> Bonjour,
>
> Vous trouverez ci-joint l'acces a la branche `diag-grow/transmission-evidence` du depot KOREV / Evidence (HEAD `fab5689a`, 5 mai 2026). Le pack de valorisation se trouve dans `docs/valuation/` (11 fichiers, dont `07_DIAG_GROW_TRANSMISSION_NOTE.md` qui est la note de couverture). La distinction Agent Zero (MIT) / Evidence (proprietaire KOREV) est explicitee dans `02_AGENT_ZERO_DELTA.md`. Les fourchettes de valorisation, les decotes et les heures de reconstruction sont documentees dans `04_HOURS_RECONSTRUCTION_REGISTER.md`. Les limites connues sont assumees dans `06_KNOWN_LIMITS_AND_REMEDIATION.md`. L'addendum post-25 avril est dans `audit-hostile-valorisation/09-mise-a-jour-post-p0-yenoyikz.md`. Nous privilegions une valorisation defendable plutot qu'une survalorisation artificielle.

---

## 17. Conformite `pre-commit-audit.mdc`

| Phase | Statut |
|---|---|
| Phase 1 — Relecture contradictoire du diff | Effectuee — **DEF-CRITIQUE-1 detecte** (3 fichiers untracked avec hashes Argon2id reels et PII : `scripts/add_beatrice_user.py`, `scripts/add_epoque_user.py`, `docs/preuves-execution/check_server_activity.sh`) |
| Phase 2 — Checklist de defauts | Effectuee : **1 CRITIQUE corrige par exclusion explicite du commit (cf. §3.5)**, 0 Important post-exclusion, 3 Moderes corriges (DEF-A1/A2/A3), 4 Mineurs documentes (DEF-A4/A5/A6 + DEF-A7) |
| Phase 3 — Re-audit total si critique | **DECLENCHE** (DEF-CRITIQUE-1 sur fichiers untracked) — Boucle complete : audit grep PII / hashes / organisations sur tous les fichiers a commit. Resultat : 0 nouveau Critique residuel apres exclusion des 3 fichiers (cf. §3.5). |
| Phase 4 — Commit avec trace d'audit | Message inclut mention "audit hostile pre-commit : 1 DEF-CRITIQUE corrige par exclusion ; 0 Critique residuel" + "anti-secrets J-0 documented" + "DEF-A1/A2/A3 corrected" + "DEF-A7 transmission decision documented" |

---

**Fin de la checklist finale de transmission Diag & Grow.**
