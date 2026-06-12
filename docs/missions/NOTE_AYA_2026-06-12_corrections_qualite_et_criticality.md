<!-- cspell:words markdownlint synallagmatique indemniser FAERS pubmed clinicaltrials -->
# Note pour Aya — Corrections qualité doc + classifieur de criticité (12 juin 2026)

> **Destinataire** : Aya (ingénierie)
> **Auteur** : chantier Cursor (audit + correctifs)
> **Branche** : `main`
> **Pré-requis lecture** : `docs/audit/criticality_router_audit_2026-06-12.md`, `python/helpers/criticality_router.py` (en-tête du module), `.markdownlint-cli2.jsonc`

---

## 0. Pourquoi ce document

Deux chantiers distincts ont été menés sur `main` le 12 juin 2026 :

1. **Qualité documentaire** — éliminer les milliers d'alertes markdownlint dans la doc, sans toucher aux prompts/agents (contenu verbatim LLM).
2. **Classifieur LEVEL 1 / 2 / 3** — corriger une faille **fail-open** : des requêtes critiques réelles passaient en LEVEL 1 et **bypassaient le consensus** parce qu'elles étaient formulées comme des questions « simples ».

Ce document te donne le **quoi**, le **pourquoi**, et **comment vérifier** après ton `git pull`.

---

## 1. Markdownlint — doc propre, périmètre volontairement limité

### 1.1 Configuration ajoutée

Fichier racine : **`.markdownlint-cli2.jsonc`**

| Choix | Justification |
| --- | --- |
| **Exclus** : `prompts/`, `agents/`, `knowledge/`, `tmp/`, `venv/`, vendors | Ces fichiers sont du **contenu envoyé tel quel aux LLM**. Les reformater (lignes vides, titres, listes) **changerait le comportement des agents**. |
| **Désactivé MD013** (longueur de ligne) | Stylistique ; la doc utilise des lignes longues (tableaux, URLs, commandes). |
| **Désactivé MD033** (HTML inline) | Badges, `<br>`, alertes GitHub `[!NOTE]` volontaires. |
| **Désactivé MD025** (un seul H1) | Les guides longs (déploiement, manuel client) ont un H1 par chapitre. |
| **Désactivé MD036, MD029, MD028** | Choix éditoriaux (gras-libellé, listes numérotées coupées par des blocs de code, alertes consécutives). |

### 1.2 Corrections appliquées (~85 fichiers `.md` sous `docs/`, `README.md`, `tests/*.md`, etc.)

- **Auto-fix** : lignes vides autour des titres/listes/tableaux, espaces traînants, styles de puces.
- **Script MD040** : 181 blocs de code sans langage → étiquetés (`bash`, `json`, `python`, `text`…).
- **Corrections manuelles ciblées** :
  - `docs/CHANGELOG_AUDIT.md` : bloc shell **sans fence d'ouverture** (le commentaire `# Test multi-worker Redis` était rendu comme titre H1).
  - Liens cassés `#in-depth-guide-for-full-binaries-installation` → repointés vers `docs/development.md`.
  - Tableau tronqué dans `docs/architecture.md` (pipe de fin manquant).
  - Hiérarchies de titres, textes alternatifs images, hiérarchie Ollama dans `installation.md`.

### 1.3 Vérifier chez toi

```bash
npx markdownlint-cli2 "**/*.md"
# Attendu : Summary: 0 error(s)
```

L'extension VS Code/Cursor lit `.markdownlint-cli2.jsonc` automatiquement.

---

## 2. cSpell — termes médicaux et techniques

Fichier : **`cspell.json`**

Mots ajoutés au dictionnaire global :

| Mot | Contexte |
| --- | --- |
| `FAERS` / `faers` | FDA Adverse Event Reporting System (agent médical) |
| `PubMed` / `pubmed` | Base bibliographique |
| `clinicaltrials` | ClinicalTrials.gov |
| `HMAC` | Signature / audit (déjà utilisé ailleurs) |

Fichier concerné en priorité : `agents/medical/PROTOCOL_EVIDENCE_VALIDATION.md`.

---

## 3. Classifieur de criticité — correction fail-closed (IMPORTANT)

### 3.1 Rappel du modèle LEVEL 1 / 2 / 3

Module unique : **`python/helpers/criticality_router.py`**

| Niveau | Comportement consensus |
| --- | --- |
| **LEVEL 1** | Requête simple (définition, résumé, météo, traduction, calcul) → **pas de consensus** |
| **LEVEL 2** | Zone professionnelle (analyse, comparaison, conseil) → pas de consensus **sauf** opt-in utilisateur (`/consensus`, « second avis »…) ou `force_consensus=True` |
| **LEVEL 3** | Cas réel, décision, litige, responsabilité, action critique → **consensus toujours requis** |

Point d'entrée chat : `python/tools/response.py` appelle `get_criticality_router().assess()` avant `finalize_critical_output()`.

### 3.2 La faille (DEF-CRIT-1 — critique)

**Avant** : la Règle 0 (bypass LEVEL 1) était évaluée **avant** la détection LEVEL 3.

Conséquence mesurée par sondes adversariales : **12 requêtes critiques sur 15** sortaient **sans consensus**, parce qu'elles contenaient un mot « simple » :

| Requête (extrait) | Mot piège L1 | Résultat avant |
| --- | --- | --- |
| « Mon employeur m'a licencié, **explique** mes recours » | `explique` | LEVEL_1, pas de consensus |
| « **Que signifie** cette mise en demeure que **j'ai reçue** » | `signifie` | LEVEL_1 |
| « Patient **température** 39.5, **urgences** ? » | `température` (météo) | LEVEL_1 |
| « **Calcule** dommages et intérêts à **réclamer** » | `calcule` | LEVEL_1 |

C'est une violation de la doctrine fail-closed : une formulation polie ne doit pas effacer un cas critique réel.

### 3.3 Correctifs appliqués

| ID | Correctif |
| --- | --- |
| **Priorité L3 > L1** | LEVEL 3 (patterns + actions critiques) est détecté **avant** le bypass L1. Double match → **LEVEL 3 gagne**. |
| **Traduction L1** | `(?:en\s+)?(français\|…)` → `\ben\s+(français\|…)` pour ne plus matcher « droit français ». |
| **Verbes commerce** | `acheter/vendre/investir` extraits dans `FINANCE_GATED_ACTION_PATTERNS` : critiques **uniquement** si domaine `FINANCE_HIGH_RISK`. |
| **Action `contract`** | Retiré des patterns d'action (nom anglais) ; reste `contracter/sign/signer` (verbes). |
| **Patterns L3 élargis** | « mes droits », « mon licenciement », « que j'ai », pronoms objets (`la/le`), tolérance bornée sur dommages/intérêts. |

### 3.4 Résultat mesuré

| Métrique | Avant | Après |
| --- | ---: | ---: |
| Faux négatifs (critique sans consensus) | 12/15 | **0/15** |
| Faux positifs (banal avec consensus) | 4/10 | **1/10** (résiduel volontaire : `publier` = action d'engagement) |

### 3.5 Tests à lancer après ton pull

```bash
source venv/bin/activate

# Nouveau fichier — couvre la priorité L3>L1 (24 tests)
pytest tests/test_criticality_router_priority.py -q

# Suites existantes (ne doivent pas régresser)
pytest tests/test_criticality_router.py tests/test_criticality_router_level2_optin.py -q
pytest -k "consensus or gate or criticality" -q
```

Attendu : **tout vert** (119+ tests router, 383 tests consensus/gate).

Rapport technique détaillé : **`docs/audit/criticality_router_audit_2026-06-12.md`**.

---

## 4. Ce qui n'a PAS changé (à ne pas confondre)

- Les **prompts** (`prompts/`, `agents/*/prompts/`) ne sont **pas** passés au markdownlint — volontairement.
- L'**opt-in consensus** LEVEL 2 (`/consensus`, « second avis ») est **inchangé**.
- `force_consensus=True` reste la **seule garantie absolue** de consensus, même sur LEVEL 1.
- Les définitions pures restent LEVEL 1 : « Qu'est-ce qu'un contrat synallagmatique ? » → pas de consensus (doctrine produit).

---

## 5. Checklist rapide après `git pull origin main`

```bash
git pull origin main
git log -1 --oneline   # vérifier le commit de cette note

# 1. Doc
npx markdownlint-cli2 "**/*.md" | tail -1

# 2. Criticality
pytest tests/test_criticality_router_priority.py -q

# 3. UI locale (si tu avais des bugs d'affichage)
# Hard refresh navigateur : Cmd+Shift+R
# Vérifier branding "KOREV Evidence" (pas "Korev Preuve")
# Si Connection Error 429 : RATE_LIMIT_API_MAX dans .env local
```

---

## 6. Fichiers clés modifiés (référence)

| Fichier | Nature du changement |
| --- | --- |
| `.markdownlint-cli2.jsonc` | **Nouveau** — config lint doc |
| `cspell.json` | Mots médicaux/techniques |
| `python/helpers/criticality_router.py` | **Correctif fonctionnel** priorité L3>L1 |
| `tests/test_criticality_router_priority.py` | **Nouveau** — 24 tests TDD |
| `docs/audit/criticality_router_audit_2026-06-12.md` | **Nouveau** — rapport d'audit |
| `docs/**/*.md`, `README.md`, etc. | Formatage markdown uniquement |

---

## 7. Questions / escalade

- Comportement inattendu sur une requête réelle → noter la **phrase exacte**, le **profil agent**, et le **niveau** affiché dans les logs (`router_decision` JSON dans les logs serveur).
- Ne pas « corriger » les patterns L1/L3 sans relancer `tests/test_criticality_router_priority.py` — les 15 sondes FN sont codées en tests.
