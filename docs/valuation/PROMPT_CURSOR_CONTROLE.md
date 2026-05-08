# Prompt Cursor de controle — A executer apres production du pack

> **Mode d'emploi :** copier-coller integralement le bloc ci-dessous dans Cursor, sur la branche `valuation/diag-grow-evidence-pack`. Ne pas l'executer dans le pack lui-meme : ce prompt audite **le pack que Cursor vient de produire**, par un second agent Cursor independant.

---

## Mission Cursor — Audit de controle du pack valorisation Evidence

**Persona active** : auditeur senior independant + commissaire aux apports + cabinet d'ingenierie technique hostile (Big4 / Diag & Grow). Ton professionnel, factuel, contradictoire, non complaisant.

**Contexte** : Le depot KOREV-Oracle / Evidence contient un pack de valorisation de 9 fichiers dans `docs/valuation/`, prepare pour transmission au cabinet Diag & Grow et / ou au commissaire aux apports dans le cadre d'un apport en nature. Ce pack est destine a etre evalue de maniere contradictoire avant l'envoi externe.

**Objectif** : verifier de la maniere la plus professionnelle et hostile possible que le pack est :
- coherent en interne,
- coherent avec les documents externes (rapport technique, dossier commissaire, audit hostile interne, preuves d'execution),
- exempt de double comptage,
- exempt d'affirmations non prouvees,
- defendable face a un auditeur externe expert,
- pret pour transmission externe.

**Mission** : aucune modification de code ni de documentation. Lecture seule. Production d'un livrable de controle.

---

### Pipeline d'actions a enchainer

#### 1. Lecture integrale du pack

Lire dans l'ordre les 9 fichiers :

```
docs/valuation/00_REPO_DIAGNOSTIC.md
docs/valuation/01_VALUATION_SCOPE.md
docs/valuation/02_AGENT_ZERO_DELTA.md
docs/valuation/03_EVIDENCE_PROPRIETARY_MODULES.md
docs/valuation/04_HOURS_RECONSTRUCTION_REGISTER.md
docs/valuation/05_CODE_QUALITY_SNAPSHOT.md
docs/valuation/06_KNOWN_LIMITS_AND_REMEDIATION.md
docs/valuation/07_DIAG_GROW_TRANSMISSION_NOTE.md
docs/valuation/08_AUDIT_HOSTILE_VALUATION_PACK.md
```

Lire ensuite les documents externes de reference :

```
docs/RAPPORT_TECHNIQUE_VALORISATION_EVIDENCE.md
docs/DOSSIER_COMMISSAIRE_APPORTS_EVIDENCE.md
docs/BENCHMARK_COMPARABLES_VALORISATION_EVIDENCE.md
audit-hostile-valorisation/01-executive-summary.md
audit-hostile-valorisation/02-cartographie-technique.md
audit-hostile-valorisation/05-angle-morts-et-decote-potentielle.md
audit-hostile-valorisation/06-plan-de-remediation-priorise.md
audit-hostile-valorisation/07-scorecard-valorisation.md
audit-hostile-valorisation/08-audit-hostile-dossier-commissaire-apports.md
audit-hostile-valorisation/09-mise-a-jour-post-p0-yenoyikz.md
docs/preuves-execution/PREUVES_TECHNIQUES_EXECUTION.md
LICENSE
legal/THIRD_PARTY_NOTICES.txt
SECURITY.md
```

#### 2. Verifications de coherence interne (entre fichiers du pack)

Pour chaque element ci-dessous, verifier sa **valeur identique** dans tous les documents du pack qui le mentionnent :

- HEAD analyse (doit etre `fab5689a` ou plus recent ; verifier coherence)
- Nombre de commits Amine (271 attendu)
- Insertions / suppressions / net Amine (+225 477 / -18 030 / +207 447 attendu)
- Diff upstream -> HEAD (920 fichiers / +217 192 / -14 434 / net +202 758 attendu)
- Tests collectes (3 956 attendu)
- Tests qualite documentation (64 / 64 attendu)
- Score qualite global (69/100 attendu)
- Decote technique residuelle (12-20% attendu)
- Coefficient qualite (0.95 attendu)
- TJM cible (650 EUR attendu)
- Heures totales basses / cibles / hautes (1 230 / 1 622 / 2 130 attendu)
- Fourchette equilibree (958 000 EUR a 1 054 000 EUR attendu)
- Fourchette offensive maitrise (1 150 000 EUR a 1 350 000 EUR attendu)
- Liste des annexes externes (AE-1 a AE-11)
- Liste des P1 / P2 ouverts (P1-3, P1-4, P1-5, P1-6, P2-1, P2-2, P2-4, P2-5, P2-7, P2-8)
- Nombre d'ADR (7 attendu : ADR-001 a ADR-007)

Si un ecart est detecte dans un fichier du pack, le marquer comme defaut Critique ou Important.

#### 3. Verification absence de double comptage

Verifier explicitement (dans `03_*.md` et `04_*.md`) :

- `medical_contract.py` (~769 LOC) compte uniquement dans le module 11 / lot 14, **pas** dans le module 7 / lot 12
- `strategic_contract.py` (~843 LOC) compte uniquement dans le module 7 / lot 12
- `reporting/evidence_native.py` (~1 422 LOC) compte uniquement dans le module 7 / lot 12 (pas dans le module 10)
- Tests comptes uniquement dans le module 15 / lot 19
- Documentation proprietaire comptee uniquement dans le module 17 / lot 21
- Modules audit-proof (replay, review, risk) comptes uniquement dans le module 9 / lots 5/6/7
- Boucle agent generique Agent Zero **non** comptee
- Pattern d'extensions Agent Zero **non** compte

Pour chaque double potentiel detecte, marquer Critique.

#### 4. Verification clarte du delta Agent Zero

Verifier dans `02_AGENT_ZERO_DELTA.md` :

- Le delta est documente fichier par fichier (top 20 + tableau analytique par domaine)
- La phrase de cadrage "Agent Zero est exclu de la valorisation comme actif proprietaire" est presente
- La reponse a l'objection "ce n'est qu'un fork" est defendable (sections 7.1, 7.2, 7.3)
- Les commandes de verification automatique sont fournies (section 8.3)
- Aucune ligne d'Agent Zero n'est comptee dans les heures (verifier dans `04_*.md`)

Si une ambiguite est detectee, marquer Important.

#### 5. Verification coherence des heures

Pour chaque lot du `04_HOURS_RECONSTRUCTION_REGISTER.md` section 6 :

- Verifier que la fourchette basse / cible / haute correspond au module decrit dans `03_*.md`
- Verifier que le TJM applique est 650 EUR (cible) ou explicitement 500 EUR (bas) / 800 EUR (haut)
- Verifier que le coefficient qualite est 0.95
- Verifier que la decote 15% est appliquee uniformement

Verifier que le total des fourchettes du tableau (section 6) est :
- Bas : ~1 230 j-h
- Cible : ~1 622 j-h
- Haut : ~2 130 j-h

Verifier que la fourchette finale retenue (`07_*.md` section 8.1, `08_*.md` section 6.3) est **958-1 054 KEUR equilibre** (alignee sur le rapport technique), avec note explicite expliquant l'ecart avec le total brut du tableau.

Si un ecart est detecte, marquer Modere.

#### 6. Verification coherence des decotes

Verifier que la decote 12-20% est :

- Justifiee dans `04_HOURS_RECONSTRUCTION_REGISTER.md` section 4 (decotes detaillees par categorie)
- Coherente avec `audit-hostile-valorisation/05-angle-morts-et-decote-potentielle.md` (cumul realiste 12-20%)
- Coherente avec `audit-hostile-valorisation/07-scorecard-valorisation.md` (decote realiste 12-20%)
- Coherente avec `docs/RAPPORT_TECHNIQUE_VALORISATION_EVIDENCE.md` section 6.4bis et 8 (12-20%)

Si un ecart est detecte, marquer Important.

#### 7. Verification absence d'affirmations non prouvees

Pour chaque chiffre / claim du pack, verifier :

- Soit il est **sourcé** a un fichier reproductible (`docs/preuves-execution/*.txt`, `audit-hostile-valorisation/*.md`, `docs/RAPPORT_TECHNIQUE_*`, ou commande Git directe)
- Soit il est **explicitement marque "a verifier" / "a annexer" / "non prouvable par Git seul"**

Claims a verifier en priorite :
- "5 ans de R&D anterieure" → doit renvoyer aux annexes AE-7
- "4 brevets PRISM en cours" → doit renvoyer aux annexes AE-5 + AE-6
- "Conformite AI Act" → doit etre marque "auto-evaluee"
- "DICA FRANCE 1 500 EUR/mois" → doit renvoyer aux annexes AE-1 + AE-2
- "Pilotes Centrale Lille / Le Tarmac" → doit renvoyer aux annexes AE-3 + AE-4
- "Antériorite PRISM" → doit etre marquee "non prouvable par Git seul"

Si un claim est non source et non marque "a verifier", marquer Critique.

#### 8. Verification lisibilite pour Diag & Grow

Verifier dans `07_DIAG_GROW_TRANSMISSION_NOTE.md` :

- Resume executif clair (section 1)
- Phrase de cadrage du perimetre (section 2)
- Distinction Agent Zero / KOREV claire (section 3)
- Ordre de lecture priorise (section 4)
- Methode de valorisation expliquee (section 8)
- Position finale assumee (section 9)
- Commandes de verification fournies (section 4.4)

Verifier que le ton est **professionnel, factuel, non defensif**.

Si un point est manquant ou peu clair, marquer Modere.

#### 9. Verification risques juridiques / licence

Verifier dans `00_*.md` et `01_*.md` :

- `LICENSE` racine est proprietaire KOREV AI (verifie par lecture)
- `legal/THIRD_PARTY_NOTICES.txt` mentionne explicitement la notice MIT Agent Zero (copyright 2024 Jan Tomasek)
- `README.md` affiche le badge "License-Proprietary" (et non MIT)
- Aucune contradiction entre les fichiers de licence
- La P0-1 (incoherence licence) est marquee corrigee (commit `40808223` du 3 avril 2026)

Si une contradiction est detectee, marquer Critique (eliminatoire).

#### 10. Verification risques de survalorisation

Verifier que :

- Aucune affirmation "leader marche", "best-in-class", "premium" n'est utilisee sans qualification
- Le ton est factuel et non marketing
- Les fourchettes annoncees sont coherentes avec la methode de cout de reproduction (norme IVS 210)
- Les multiples d'entreprise ne sont **pas** utilises pour fonder la valeur (uniquement en verification d'ordre de grandeur)
- La methode des revenus (DCF) est explicitement marquee "non applicable"
- Le scenario offensif est explicitement conditionne aux annexes externes
- Le scenario equilibre est presente comme valeur cible (et non comme borne basse)

Si une survalorisation est detectee, marquer Important.

#### 11. Verification risques secrets / cles dans le depot

Executer en lecture seule :

```bash
git ls-files | grep -iE '\.(env|pem|key)$|users\.json$|secrets?\.json$'
git log --all -p -- '.env' '.env.production' 'users.json' 'deploy/users.json' 2>&1 | head -50
rg -uu --no-messages -i '(api[_-]?key|password|token|secret)\s*=\s*["\x27][A-Za-z0-9/_+-]{20,}' . --max-count 1
rg -uu --no-messages 'BEGIN (RSA |EC |OPENSSH )?PRIVATE KEY' . --max-count 1
```

Si une cle reelle ou un token est detecte, marquer **CRITIQUE ELIMINATOIRE** (a corriger imperativement avant transmission).

#### 12. Production d'un livrable de controle

Produire un fichier :

```
docs/valuation/CONTROLE_AUDIT_PACK_<DATE_AUDIT>.md
```

Contenant :

1. **Resume executif** (verdict global : pret / pret avec reserves / non pret)
2. **Synthese des verifications** (tableau coherence, double comptage, claims, licence, secrets)
3. **Defauts detectes** (tableau Critique / Important / Modere / Mineur)
4. **Reponse aux 11 questions a traiter** (cf. brief original) :
   - Coherence entre fichiers docs/valuation
   - Absence de double comptage
   - Clarte du delta Agent Zero
   - Coherence des heures
   - Coherence des decotes
   - Absence d'affirmations non prouvees
   - Lisibilite pour Diag & Grow
   - Risques juridiques / licence
   - Risques de survalorisation
   - Corrections prioritaires avant envoi
   - Risques secrets / cles dans le depot
5. **Top 5 corrections prioritaires** avant transmission externe
6. **Verdict final** :
   - Livrable tel quel : oui / non
   - Risque de decote : faible / moyen / eleve
   - Fourchette defendable repo seul (verifiee)
   - Fourchette defendable avec annexes externes (verifiee)
   - Statut final : **pret / pret avec reserves / non pret**

#### 13. Restitution dans le terminal

Afficher dans le terminal a la fin de l'audit :

- Liste des fichiers du pack lus (9 fichiers)
- Liste des fichiers externes consultes (12+ fichiers)
- Liste des defauts detectes par severite
- Top 5 corrections prioritaires
- Fourchette defendable repo seul (apres verification)
- Fourchette defendable avec annexes (apres verification)
- Statut final : pret / pret avec reserves / non pret

---

### Contraintes qualite

- Aucune modification de code, documentation existante, ou fichiers du pack
- Lecture seule
- Aucun commit, push, ou changement de branche
- Production d'**un seul livrable** : `docs/valuation/CONTROLE_AUDIT_PACK_<DATE>.md`
- Tonalite professionnelle, factuelle, non complaisante, non defensive
- Pas d'emojis
- Pas d'affirmation non sourcée
- Marquer "A verifier" si une preuve manque
- Severite des defauts : Critique (eliminatoire), Important (a corriger), Modere (a noter), Mineur (informatif)

---

### Cadrage final

Cet audit de controle ne doit pas refaire la valorisation. Il doit :
- valider que le pack est defendable face a un auditeur externe expert,
- detecter toute incoherence interne,
- detecter toute affirmation non prouvee,
- detecter tout double comptage,
- detecter tout risque de licence / juridique,
- detecter tout risque de survalorisation,
- detecter tout secret / cle reel residuel dans le depot,
- produire un verdict statut "pret / pret avec reserves / non pret" pour transmission externe.

L'apporteur (Amine Mohamed) prendra ensuite les decisions finales (commit / push / transmission) sur la base du livrable de controle produit.

**Demarrer immediatement l'audit. Aucune confirmation n'est requise.**
