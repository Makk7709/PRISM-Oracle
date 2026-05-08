# 07 — Note de transmission Diag & Grow

**Apporteur / inventeur** : Amine Mohamed
**Destinataire** : cabinet Diag & Grow (et / ou commissaire aux apports)
**Objet** : evaluation de l'actif logiciel KOREV Evidence dans le cadre d'un apport en nature
**Branche d'analyse** : `valuation/diag-grow-evidence-pack` (analyse interne)
**Branche de transmission** : `diag-grow/transmission-evidence` (transmission externe Diag & Grow / commissaire — sanitization PII appliquee)
**HEAD analyse** : `fab5689a` (5 mai 2026)
**Date de transmission** : a completer par l'apporteur
**Methode de valorisation principale recommandee** : cout de reproduction (norme IVS 210 — Actifs incorporels)

---

## 1. Resume executif

KOREV Evidence est une plateforme multi-agents d'IA de confiance pour professions reglementees, developpee par Amine Mohamed entre janvier 2026 et mai 2026. Elle est construite sur une fondation open-source MIT (Agent Zero, frdel / Jan Tomasek, https://github.com/frdel/agent-zero), substantiellement etendue par 271 commits, 920 fichiers modifies et +217 192 / -14 434 lignes (net +202 758 lignes) dans le diff `git diff 9a3a92b6..HEAD`.

Le presente note accompagne l'acces au depot et oriente votre analyse :
- vers les fichiers a consulter en priorite,
- vers le perimetre valorisable (oeuvre derivee KOREV),
- vers les annexes externes a fournir hors depot.

L'apporteur privilegie une **valorisation defendable** plutot qu'une survalorisation artificielle. Les limites du projet sont assumees dans le pack et ne sont pas dissimulees.

---

## 2. Cadrage du perimetre valorisable

### 2.1 Phrase de cadrage

> *"Agent Zero est exclu de la valorisation comme actif proprietaire. La valorisation porte sur l'oeuvre derivee KOREV : couches Evidence, PRISM integre, auditabilite, replay, risk register, human review, securite, tests, documentation, industrialisation et specialisation metier."*

### 2.2 Volumetrie comparative

| Metrique | Agent Zero upstream (10 jan. 2026) | KOREV Evidence (HEAD `fab5689a`, 5 mai 2026) | Delta |
|---|---:|---:|---:|
| Fichiers Python | 210 | ~606 | **+396** |
| Lignes Python | 28 403 | ~189 744 | **+161 341** |
| Tests collectes (pytest) | 0 | **3 956** | **+3 956** |
| Documentation `.md` | 130 / 9 426 LOC | 246+ / ~38 100 LOC | **+116 / +28 689** |

### 2.3 Diff Git verifiable

```bash
git diff 9a3a92b6..HEAD --shortstat
# Resultat attendu : 920 files changed, +217 192 / -14 434 (net +202 758)

git log --all --author='Amine' --shortstat
# Resultat attendu : 271 commits, +225 477 / -18 030 (net cumule +207 447)
```

---

## 3. Distinction Agent Zero / KOREV Evidence

| Element | Agent Zero (exclu) | KOREV Evidence (inclus) |
|---|---|---|
| Boucle agent generique (refondue) | Heritage MIT | Refonte avec hooks Evidence |
| Pipeline Consensus PRISM (multi-arbitres, fail-closed) | Aucun | **100% KOREV** (~6 200 LOC) |
| Debat adversarial / instruction contradictoire | Aucun | **100% KOREV** (~4 620 LOC) |
| Router deterministe + Gate de criticite | Aucun | **100% KOREV** (~4 470 LOC) |
| Pipeline Legal-Safe complet (ingestion sources, FTS5, contrats) | Aucun | **100% KOREV** (~16 550 LOC) |
| Moteur PDF / OCR + Evidence Document + PRISM Charts | Aucun | **100% KOREV** (~12 380 LOC) |
| Reasoning Engine + Metacognition | Aucun | **100% KOREV** (~2 240 LOC) |
| Pipeline strategique + Reporting Evidence-grade | Aucun | **100% KOREV** (~6 760 LOC) |
| Securite multi-tenant (Argon2id, RBAC, isolation) | Auth basique | **100% KOREV** (~4 410 LOC) |
| Pipeline Audit-Proof (replay, human review, risk register) | Aucun | **100% KOREV** (~1 690 LOC) |
| Architecture Docker production + scripts industriels | DockerfileLocal dev | **100% KOREV** (~9 500 LOC) |
| Suite de tests TDD (3 956 tests collectes) | 7 fichiers rudimentaires | **100% KOREV** (~67 200 LOC) |
| Documentation proprietaire (148 fichiers diff, +27 675 lignes) | 130 fichiers communautaires | **100% KOREV** |
| Pattern d'extensions (hooks ordonnes) | Heritage MIT | Pattern reutilise, hooks Legal-Safe / Evidence proprietaires |
| WebUI Alpine.js initiale | Heritage MIT (-16 fichiers, +607 lignes) | Refonte branding + i18n FR/EN proprietaire |
| 12 Agents specialises (legal_safe, medical, finance, etc.) | 1 profil generique | **12 profils 100% KOREV** |
| 11 MCP servers configures | Pattern de base | **Configurations + 3 servers locaux KOREV** |

> Le delta proprietaire est documente fichier par fichier dans `docs/valuation/02_AGENT_ZERO_DELTA.md` et `docs/valuation/03_EVIDENCE_PROPRIETARY_MODULES.md`. **Aucun module Agent Zero n'est compte. Aucun module n'est compte deux fois.**

---

## 4. Fichiers a consulter en priorite

### 4.1 Priorite 1 — Comprehension globale (1-2 heures)

| # | Fichier | Role |
|---|---|---|
| 1 | `docs/valuation/00_REPO_DIAGNOSTIC.md` | Diagnostic initial complet du depot |
| 2 | `docs/valuation/01_VALUATION_SCOPE.md` | Perimetre valorise (inclus / exclu / annexes) |
| 3 | `docs/valuation/02_AGENT_ZERO_DELTA.md` | Distinction Agent Zero / KOREV (critique) |
| 4 | `docs/valuation/04_HOURS_RECONSTRUCTION_REGISTER.md` | Heures de reconstruction par lot |
| 5 | `docs/valuation/06_KNOWN_LIMITS_AND_REMEDIATION.md` | Limites assumees |
| 6 | `docs/valuation/08_AUDIT_HOSTILE_VALUATION_PACK.md` | Audit hostile final du pack |

### 4.2 Priorite 2 — Validation technique (2-4 heures)

| # | Fichier | Role |
|---|---|---|
| 7 | `docs/RAPPORT_TECHNIQUE_VALORISATION_EVIDENCE.md` | Rapport technique de reference (1 100+ LOC) |
| 8 | `docs/DOSSIER_COMMISSAIRE_APPORTS_EVIDENCE.md` | Dossier commissaire (synthese, mis a jour 5 mai 2026 avec section 10) |
| 9 | `docs/BENCHMARK_COMPARABLES_VALORISATION_EVIDENCE.md` | Benchmark comparables marche |
| 10 | `docs/preuves-execution/PREUVES_TECHNIQUES_EXECUTION.md` | Annexes A11/A12 (preuves reproductibles) |
| 11 | `audit-hostile-valorisation/01-executive-summary.md` | Resume executif audit hostile |
| 12 | `audit-hostile-valorisation/05-angle-morts-et-decote-potentielle.md` | Angles morts et decote potentielle |
| 13 | `audit-hostile-valorisation/07-scorecard-valorisation.md` | Scorecard (69/100) |
| 14 | `audit-hostile-valorisation/09-mise-a-jour-post-p0-yenoyikz.md` | **Addendum 5 mai 2026 : 3 commits posterieurs au snapshot du 25 avril (yENoyKIZ + ADR-006, P0 RDBMS + ADR-007, fix DEF-8). Defenses renforcees, fourchettes inchangees.** |

### 4.3 Priorite 3 — Verification du code (4-8 heures)

| # | Fichier / dossier | Role |
|---|---|---|
| 14 | `LICENSE` + `legal/KOREV_LICENSE.txt` + `legal/THIRD_PARTY_NOTICES.txt` | Verification licences |
| 15 | `SECURITY.md` racine | Politique de securite |
| 16 | `docs/adr/` (7 ADR) | Decisions architecturales |
| 17 | `docs/GLOSSARY.md` | 30+ termes proprietaires |
| 18 | `docs/ARCHITECTURE_C4_DIAGRAMS.md` | Diagrammes C4 (3 niveaux + sequence) |
| 19 | `docs/DEVELOPER_ONBOARDING_ARCHITECTURE_GUIDE.md` (1 196 LOC) | Guide d'onboarding |
| 20 | `docs/GUIDE_DEPLOIEMENT_ENTREPRISE.md` (1 385 LOC) | Guide de deploiement |
| 21 | `python/consensus/`, `python/helpers/consensus_*.py`, `adversarial_*.py` | Modules consensus PRISM |
| 22 | `python/helpers/legal_*.py`, `python/extensions/legal_safe_mode/` | Pipeline Legal-Safe |
| 23 | `python/helpers/replay_engine.py`, `human_review.py`, `dynamic_risk_register.py` | Pipeline Audit-Proof |
| 24 | `python/helpers/integrity_block.py`, `session_envelope.py`, `evidence.py` | Framework Evidence |
| 25 | `python/security/` (14 fichiers) | Securite multi-tenant |
| 26 | `tests/` (180+ fichiers) | Suite de tests TDD |
| 27 | `deploy/Dockerfile.backend`, `deploy/docker-compose.yml`, `scripts/` | Architecture production |
| 28 | `.github/workflows/` (3 workflows) | CI |

### 4.4 Verifications executables (commandes pour Diag & Grow)

```bash
# 1. Cloner et se positionner sur le HEAD analyse
git clone <url-depot> KOREV_Evidence
cd KOREV_Evidence
git checkout valuation/diag-grow-evidence-pack
git rev-parse HEAD     # Doit retourner fab5689a (ou plus recent)

# 2. Verifier les metriques Git du pack
git diff 9a3a92b6..HEAD --shortstat
# Resultat attendu : ~920 files, ~+217 192 / -14 434

git log --all --author='Amine' --shortstat | tail
# Resultat attendu : ~271 commits, +225 477 / -18 030

# 3. Verifier l'absence de Agent Zero dans les modules de valeur
git show 9a3a92b6:python/helpers/legal_orchestrator.py 2>&1
git show 9a3a92b6:python/helpers/replay_engine.py 2>&1
git show 9a3a92b6:python/consensus/engine.py 2>&1
# Resultats attendus : "fatal: path '...' does not exist"

# 4. Reproduire les preuves d'execution
python3.11 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pytest --collect-only -q tests/        # ~3 956 tests collectes
pytest tests/test_documentation_quality.py -q  # 64 / 64 PASSED
docker compose -f deploy/docker-compose.yml config --quiet  # exit 0
bash docs/preuves-execution/run_docker_proof.sh  # build Docker
```

---

## 5. Fichiers du pack `docs/valuation/`

| # | Fichier | Contenu |
|---|---|---|
| 0 | `00_REPO_DIAGNOSTIC.md` | Diagnostic initial complet (etat Git, architecture, dependances, tests, CI, traces Agent Zero vs KOREV) |
| 1 | `01_VALUATION_SCOPE.md` | Perimetre de valorisation (inclus / exclu / annexes externes / position recommandee) |
| 2 | `02_AGENT_ZERO_DELTA.md` | Delta Agent Zero / KOREV par domaine (tableau analytique, top 20 fichiers, reponse "fork") |
| 3 | `03_EVIDENCE_PROPRIETARY_MODULES.md` | Inventaire des 17 modules proprietaires KOREV avec heures de reconstruction |
| 4 | `04_HOURS_RECONSTRUCTION_REGISTER.md` | Registre des heures par lot, TJM, coefficient qualite, decotes, valeurs cibles |
| 5 | `05_CODE_QUALITY_SNAPSHOT.md` | Snapshot qualite (tests, CI, securite, doc, ADR, type checking, Docker, audit trail) |
| 6 | `06_KNOWN_LIMITS_AND_REMEDIATION.md` | Limites connues et plan de remediation (P0/P1/P2) |
| 7 | `07_DIAG_GROW_TRANSMISSION_NOTE.md` | Le present document (note de transmission) |
| 8 | `08_AUDIT_HOSTILE_VALUATION_PACK.md` | Audit hostile du pack lui-meme (verdict final) |
| 9 | `09_CORRECTIONS_DEF_A1_A2_A3.md` | Note de correction des 3 defauts moderes detectes par l'audit de controle (integration des commits post-25 avril 2026) |
| C | `CONTROLE_AUDIT_PACK_2026-05-09.md` | Audit de controle hostile du pack par auditeur independant (verdict initial : pret avec reserves maitrisees) |
| P | `PROMPT_CURSOR_CONTROLE.md` | Prompt utilise pour l'audit de controle independant (reproductible) |

---

## 6. Limites assumees

> Toutes les limites sont declarees explicitement et ne sont pas dissimulees. Cf. `06_KNOWN_LIMITS_AND_REMEDIATION.md` pour le detail complet.

### 6.1 Limites techniques residuelles

1. **Suite etendue non-bloquante en CI** (`continue-on-error: true`) — P1-3 ouvert, ~1-2 jours d'effort.
2. **Couverture globale non mesuree** en CI — P1-4 ouvert, ~2 heures d'effort.
3. **Pas de build Docker en CI** — P1-5 ouvert, ~3 heures d'effort.
4. **Mode sans authentification par defaut quand config absente** — P1-6 ouvert, ~3 heures d'effort.
5. **Modules monolithiques** (`settings.py` 2 225 LOC, `legal_orchestrator.py` 1 960 LOC, etc.) — P2-1 ouvert.
6. **Duplications conceptuelles** (3 chemins consensus) — P2-2 ouvert.
7. **Pas de SAST / Dependabot** — P2-4 ouvert, ~3 heures d'effort.
8. **Pas de schema de donnees formel** — P2-5 ouvert.
9. **Code mort residuel** (`browser.py` ~336 LOC commentees) — P2-7 ouvert.
10. **Masquage secrets fail-open** (`except: pass`) — P2-8 ouvert.

**Cumul effort de remediation P1 + P2 restants : ~10 jours** (cf. `06_KNOWN_LIMITS_AND_REMEDIATION.md` section 3).

### 6.2 Limites de gouvernance

11. **Bus factor = 1** (Amine Mohamed unique developpeur) — attenue par 7 ADR + GLOSSARY + C4 + onboarding 1 196 LOC. Estimation onboarding : ~1.5-2 semaines.
12. **Pas d'audit externe** (penetration, conformite). Le pipeline audit-proof attenue l'auto-evaluation.

### 6.3 Limites probatoires

13. **Antériorite PRISM** (5 ans de R&D) non demontrable par le seul depot Git (qui demarre le 15 janvier 2026). Necessite annexes externes datees.
14. **4 brevets PRISM en cours** non rattaches a Evidence sans chaine de droits annexee.
15. **Conformite AI Act / RGPD** auto-evaluee (ComplianceGrid implementee, mais pas d'audit externe).

---

## 7. Annexes externes a fournir (hors depot Git)

| # | Annexe | Detenu par | Statut |
|---|---|---|---|
| AE-1 | Factures DICA FRANCE (1 500 EUR/mois recurrent) | Apporteur | A annexer |
| AE-2 | Preuves de paiement DICA FRANCE | Apporteur | A annexer |
| AE-3 | Convention / emails Le Tarmac by inovallee | Apporteur | A annexer |
| AE-4 | Convention / emails Centrale Lille (Chaire Construction 4.0 / Pr Zoubeir Lafhaj) | Apporteur | A annexer |
| AE-5 | Dossier des 4 brevets PRISM en cours (numeros depot, perimetre) | Apporteur | A annexer |
| AE-6 | Chaine de droits PRISM -> Evidence (cession, licence, apport, attestation) | Apporteur | A annexer |
| AE-7 | Pieces datees R&D pre-repository (carnets, exports notes, emails, prototypes, captures, factures outils) | Apporteur | A annexer |
| AE-8 | Echanges clients / prospects | Apporteur | A annexer |
| AE-9 | Attestation d'inventeur d'Amine Mohamed sur PRISM et Evidence | Apporteur | A annexer |
| AE-10 | Eventuels rapports d'audit externes (securite, conformite, accessibilite) | Apporteur | Optionnel — a annexer si disponibles |
| AE-11 | Eventuels contrats clients en cours de negociation ou pilotes | Apporteur | Optionnel |

> Les annexes AE-5, AE-6 et AE-7 sont les plus critiques pour passer du scenario equilibre (~958-1 054 KEUR) au scenario offensif maitrise (~1 150-1 350 KEUR).

---

## 8. Methode de valorisation proposee

### 8.1 Methode principale : cout de reproduction

**Reference normative** : IVS 210 — Actifs incorporels.

**Decomposition** : 17 modules proprietaires KOREV identifies dans `03_EVIDENCE_PROPRIETARY_MODULES.md`, totalisant ~138 100 LOC code metier + ~67 200 LOC tests + ~27 700 LOC documentation proprietaires.

**Effort de reconstruction par une equipe senior** : 1 230 a 2 130 j-h, cible ~1 600 j-h.

**TJM marche francais 2026** : 500-800 EUR (cible 650 EUR) pour developpeur senior IA / Full-stack.

**Cout brut** : 662 000 EUR a 1 889 600 EUR (cible ~1 200 000 EUR).

**Coefficient qualite** : 0.95 (score 69/100, code structurant industrialisable).

**Decote technique residuelle** : 12-20% (post-P0 + P1/P2 partiel actuel).

**Valeur nette defendable** :
- **Conservateur audit-proof (repo seul)** : 662 000 EUR a 850 000 EUR
- **Defendable equilibre (recommande)** : **958 000 EUR a 1 054 000 EUR** (mediane ~1 006 000 EUR)
- **Offensif maitrise (avec annexes externes)** : 1 150 000 EUR a 1 350 000 EUR

### 8.2 Methode complementaire : positionnement de marche

Le benchmark comparables marche (`docs/BENCHMARK_COMPARABLES_VALORISATION_EVIDENCE.md`) classe Evidence dans la categorie C "infrastructures de decision et de confiance", distincte des SaaS B2B standards. Cette categorisation est fondee sur des caracteristiques techniques documentees du depot (consensus deterministe, pipeline de conformite, auditabilite native, routage anti-injection, specialisation metier verticale).

Le positionnement sert **uniquement** a verifier que le cout de reproduction retenu n'est pas excessif. Il **ne fonde pas** une prime de marche fondee sur des multiples d'entreprise.

### 8.3 Methode des revenus (DCF)

**Non applicable a date** :
- Revenu recurrent < 20 KEUR/an (DICA FRANCE 1 500 EUR/mois).
- Pas d'historique commercial suffisant pour DCF.

DICA FRANCE (annexes AE-1, AE-2) **soutient** le haut de la fourchette equilibree mais **ne fonde pas** une approche par multiples de revenus.

### 8.4 Approche brevets

Les 4 brevets PRISM en cours sont presentes en annexe au commissaire. Leur valeur s'agregera a Evidence si la chaine de droits PRISM -> Evidence est annexee (AE-5, AE-6).

### 8.5 Synthese de la position

| Scenario | Valeur | Conditions de defense |
|---|---|---|
| **Conservateur** | 662 000 EUR a 850 000 EUR | Repo seul, decote 20%, scenario hostile maximal |
| **Defendable equilibre (recommande)** | **958 000 EUR a 1 054 000 EUR** | Repo + audit hostile interne + preuves Git + benchmark + tests + DICA FRANCE en complement |
| **Offensif maitrise** | 1 150 000 EUR a 1 350 000 EUR | + annexes AE-1 a AE-9 fournies (factures DICA, preuves de paiement, pieces R&D pre-repo, dossier 4 brevets PRISM + chaine de droits, pilotes terrain) |

---

## 9. Position finale de l'apporteur

> KOREV AI privilegie une **valorisation defendable** plutot qu'une survalorisation artificielle.
>
> Le pack de valorisation a ete prepare en posture d'audit hostile interne afin d'anticiper les objections d'un evaluateur externe. Les limites du projet sont assumees explicitement et integrees au plan de remediation. Les annexes externes a fournir sont identifiees nominativement (AE-1 a AE-11).
>
> La valeur cible recommandee se situe dans la fourchette **958 000 EUR a 1 054 000 EUR (mediane ~1 006 000 EUR)**, fondee sur la methode de cout de reproduction (norme IVS 210), avec un coefficient qualite de 0.95 (score 69/100) et une decote technique residuelle de 12-20%. Cette fourchette est defendable face a une revue hostile sur la base du depot Git, du rapport technique, du pack d'audit hostile interne et du present pack de valorisation.
>
> Les commits posterieurs au snapshot du 25 avril 2026 (`de8b9c7e` yENoyKIZ + ADR-006, `b11b4d99` P0 RDBMS execute + ADR-007, `0d0a35da` fix DEF-8) **ne modifient pas les fourchettes annoncees**. Ils renforcent la defense de la borne haute par la fermeture d'un risque fail-silent reel, l'ajout de 2 ADR structurants, la mise en place d'une roadmap RDBMS gated et la validation d'un pipeline backup/restore fail-loud. Le detail probatoire est dans `audit-hostile-valorisation/09-mise-a-jour-post-p0-yenoyikz.md` (joint en priorite 2 ligne 14).
>
> L'apporteur reste a la disposition du cabinet Diag & Grow et du commissaire aux apports pour toute precision, demonstration ou complement d'information.

---

## 10. Contacts

| Element | Detail |
|---|---|
| Apporteur / inventeur | Amine Mohamed |
| Entite juridique | KOREV AI |
| Depot | a transmettre par voie privee (acces GitHub avec token de lecture seule) |
| Branche d'analyse interne | `valuation/diag-grow-evidence-pack` |
| Branche de transmission externe | `diag-grow/transmission-evidence` (sanitization `deploy/users.json.example` selon option C de DEF-A7) |
| HEAD analyse | `fab5689a` (5 mai 2026) |
| Email de contact | a renseigner par l'apporteur |

---

*Note de transmission etablie le 9 mai 2026 sur la branche `valuation/diag-grow-evidence-pack`. Toutes les references sont verifiables. Aucune affirmation n'est non sourcee.*
