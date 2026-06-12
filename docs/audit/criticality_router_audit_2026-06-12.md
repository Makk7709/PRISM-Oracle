<!-- cspell:words synallagmatique indemniser prud assureur -->
# Audit & optimisation du classifieur de criticité (LEVEL 1/2/3)

**Date** : 2026-06-12
**Périmètre** : `python/helpers/criticality_router.py` (classifieur unique consensus/bypass)
**Méthode** : sondes adversariales quantifiées + TDD (tests rouges avant correctif)

## Résultat en une ligne

Avant : **12/15** requêtes critiques réelles sortaient **sans consensus** (faux négatifs)
et **4/10** requêtes banales déclenchaient le consensus (faux positifs).
Après : **0/15** faux négatifs, **1/10** faux positif (résiduel par design, voir D-1).

## Défauts identifiés

| DEF | Sévérité | Description | Correctif |
| --- | :---: | --- | --- |
| DEF-CRIT-1 | **Critique** | **Inversion de priorité** : la Règle 0 (bypass LEVEL 1) était évaluée AVANT la détection LEVEL 3. Toute requête critique réelle enrobée d'une formulation simple ("explique-moi mes recours après mon licenciement", "que signifie cette mise en demeure que j'ai reçue") matchait un pattern L1 (`expliquer`, `signifie`, `calcule`, `résume`, `traduis`, `cherche`, `liste`, `c'est quoi`, `définis`) et **bypassait le consensus**. | LEVEL 3 (patterns + actions critiques) est désormais détecté **avant** le bypass L1 ; en cas de double match, L3 gagne (fail-closed). |
| DEF-CRIT-2 | **Important** | Pattern L1 traduction `(?:en\s+)?(?:anglais\|français\|…)` : la préposition étant optionnelle, **tout adjectif de langue matchait** ("droit **français**", "restaurant **italien**" → LEVEL 1). | Préposition obligatoire : `\ben\s+(?:anglais\|français\|…)\b`. |
| DEF-CRIT-3 | **Important** | Verbes de transaction (`acheter`, `vendre`, `invest`, `transfer`…) dans `CRITICAL_ACTION_PATTERNS` déclenchaient le consensus **hors de tout contexte financier** ("où acheter du bon pain ?" → LEVEL 3 + consensus). | Extraits dans `FINANCE_GATED_ACTION_PATTERNS`, activés uniquement si le domaine détecté est `FINANCE_HIGH_RISK`. |
| DEF-CRIT-4 | **Important** | Le NOM anglais `contract` figurait dans les patterns d'action ("What is a contract?" → action critique). Masqué avant par DEF-CRIT-1, révélé par sa correction. | Pattern restreint aux verbes (`contracter\|sign\|signer`). |
| DEF-CRIT-5 | Modéré | Patterns L3 trop rigides : adjacence stricte ratait "dommages et intérêts **que je peux** réclamer", "je dois **la** contester", "les recours **que j'ai**", "mes droits", "mon licenciement". | Tolérance bornée (`.{0,40}?`), pronoms objets optionnels (`l[ae]s?`), possessifs étendus (`droits?\|recours\|licenciement`), variante `que j'ai`. |

## Décisions assumées (pas des défauts)

| ID | Décision |
| --- | --- |
| D-1 | `publier`/`recommander`/`diagnostiquer`/`valider` etc. restent des actions critiques **sans gating de domaine** (doctrine existante, testée par `TestCriticalActions`). Conséquence : "peux-tu publier ce message sur le blog interne ?" déclenche le consensus — sur-prudence acceptée pour un verbe d'engagement. |
| D-2 | "Qu'est-ce qu'un contrat synallagmatique ?" reste LEVEL 1 : une définition reste une définition, même juridique (doctrine du module, inchangée). |
| D-3 | L'opt-in utilisateur et `force_consensus=True` priment toujours sur le bypass L1 (inchangé). |

## Vérification

- `tests/test_criticality_router_priority.py` (**nouveau**, 24 tests) : écrit AVANT le correctif (15 rouges), tous verts après — couvre les 15 sondes FN, les 3 FP commerce, et des garde-fous (L1 purs, opt-in, force_consensus).
- Suites existantes : `test_criticality_router` + `test_criticality_router_level2_optin` (76), `test_critical_output_doctrine` + router intents (139), `pytest -k "consensus or gate or criticality"` (383). **Toutes vertes**, 0 régression.
- Sondes adversariales (`tmp/sonar/probe_criticality.py`) : FN 12/15 → **0/15** ; FP 4/10 → **1/10** (D-1).

## Pistes non traitées (hors périmètre de ce correctif)

- Les patterns regex restent une heuristique lexicale FR/EN ; un étage sémantique (embedding ou LLM léger) réduirait les angles morts de formulation, au prix de latence/déterminisme — à instruire dans un ADR si besoin.
- `release`/`diffuser` (action critique non gatée) peut sur-déclencher sur des emplois nominaux anglais ("press release") ; même famille que D-1.
- `detect_domain()` exécute un `assess()` complet (log inclus) pour ne lire que le domaine — coût mineur, nettoyage possible.
