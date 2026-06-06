# Remédiation SonarQube complète — suivi de chantier (cabinet de valo)

**Source** : export SonarQube du cabinet (`correction sonr oracle.pdf`, 316 pages).
**Inventaire** : **1593 findings uniques** sur **313 fichiers**.

## Méthode (consignes)

1. Découpage en **paquets de 20** findings, ordonnés par **tier de risque** (1 → 4).
2. **Audit hostile** après chaque paquet (relecture contradictoire + checklist défauts).
3. **Documentation** de chaque paquet (ce fichier).
4. **Gate qualité** : tests ciblés verts + audit clean ⇒ commit du paquet ; sinon rollback.
5. Tier 4 (renommages API, imports, complexité) : corrigé **seulement si tests verts**.
6. Passe finale de contrôle, puis push.

## Répartition

| Sévérité | Nb |  | Tier (risque) | Findings | Paquets |
|---|---:|---|---|---:|---:|
| BLOCKER | 1 |  | Tier 1 — mécanique (risque ~nul) | 529 | ~27 |
| CRITICAL | 312 |  | Tier 2 — idiomes (risque faible) | 413 | ~21 |
| MAJOR | 636 |  | Tier 3 — adjacent comportement | 238 | ~12 |
| MINOR | 629 |  | Tier 4 — risqué (API/structure) | 413 | ~21 |
| INFO | 15 |  | **Total** | **1593** | **80** |

Tier 1 = code commenté (`S125`), imports/variables inutilisés (`S1128`/`S1481`), littéraux
dupliqués (`S1192`), CSS divers. Tier 4 = classes/fonctions renommées (`S101`/`S100`),
imports absolus (`S6859`), complexité cognitive (`S3776`), paramètres inutilisés (`S1172`).

## Journal des paquets

| # | Tier | Règles | Fichiers | Nb | Statut | Audit | Commit |
|---:|:---:|---|---:|---:|---|---|---|
| 1 | 1 | css:S125, css:S4658 | 7 | 20 | ✅ corrigé | 0 défaut | 35be1ed5 |
| R1 | 1 | python:S1481 (ruff F841, sûrs) | 5 | 8 | ✅ corrigé | 1 régression évitée | 1ffa1ab7 |
| 2a | 1 | css:S4667 (style vide) | 6 | 6 | ✅ corrigé | 0 défaut | _(en cours)_ |
| 2b | 2 | css:S4666, css:S7924 (sélecteurs dupliqués) | — | 13 | ⏸️ différé | render-affecting | — |

### Paquet 2a — blocs `<style></style>` vides (css:S4667)

Suppression de 6 balises `<style></style>` **vides** dans des composants projets/speech :
`project-edit-file-structure`, `project-edit-instructions`, `project-edit-memory` (2e bloc,
le vrai bloc 48-70 conservé), `project-edit-secrets`, `project-file-structure-test`,
`settings/speech/microphone`. **Audit** : balises `<style>` équilibrées après coup. 0 défaut.

> **Différé (2b)** : `css:S4666`/`css:S7924` (sélecteurs/règles dupliqués, ex. `.server-list`,
> `.tool-count`, badges scheduler « subset used in sidebar ») touchent la **cascade/le rendu**
> et certains doublons sont **inter-fichiers** → fusion à faire avec contrôle visuel, dans une
> passe dédiée. Non bâclé.

### Paquet R1 — ruff-assisté (python:S1481, sous-ensemble sûr)

Approche hybride : `ruff check --select F841 --fix` (corrections **sûres** uniquement) sur
les 83 fichiers porteurs de `S1481`. Sur 165 findings, **9 seulement** étaient auto-fixables
sûrement (72 nécessiteraient `--unsafe-fixes` — supprimer `x = func()` pourrait retirer un
appel à effet de bord → écartés, traités manuellement plus tard).

8 corrections retenues (suppression d'un `except … as e` où `e` est inutilisé) :
`python/api/poll.py`, `python/api/upload.py` (×2), `python/helpers/pdf_generator.py` (×3),
`python/helpers/research_pipeline.py`, `python/helpers/vector_db.py`.

**Audit hostile — régression détectée et corrigée** : ruff a aussi proposé de retirer
`as e` dans `python/helpers/mcp_handler.py:902`, MAIS `e` y est **utilisé** (l.910/912) et
seulement **réassigné conditionnellement** (`if original_exception is not None`). Sur le
chemin `original_exception is None`, la suppression aurait provoqué un `NameError`.
→ Fichier **reverté** ; ruff avait sur-corrigé un F841 non flaggé par Sonar. Leçon : les
auto-fixes sont relus un par un, jamais committés en aveugle. Compile OK + tests poll verts.

### Paquet 1 — détail

Suppression de **code CSS commenté** (`S125`, 19 findings) et d'une **règle vide**
(`S4658`, 1 finding) :

- `webui/components/messages/action-buttons/simple-action-buttons.css` (border, transition, opacity commentés)
- `webui/components/notifications/notification-toast-stack.html` (backdrop-filter + 5× background commentés)
- `webui/components/projects/project-edit-basic-data.html` (border commenté)
- `webui/components/settings/memory/memory-detail-modal.html` (5 déclarations commentées)
- `webui/css/settings.css` (2 box-shadow + 1 color commentés ; règle `.light-mode .settings-tab.active` devenue vide → **règle entière supprimée** pour ne pas créer un S4658)
- `webui/css/toast.css` (max-width commenté)
- `webui/css/speech.css` (règle vide `#microphone-button {}` supprimée — S4658)

**Audit hostile** : commentaires descriptifs de section préservés (non flaggés) ; accolades
équilibrées sur les 7 fichiers ; aucune règle vide introduite (le seul `{}` résiduel est
`|| {}` d'une expression Alpine, pré-existant). **0 défaut.**

### Paquet S125-sep — séparateurs décoratifs Python (python:S125, 163 findings)

`python:S125` total = **204** findings sur 105 fichiers. Classification automatique :
- **163 séparateurs décoratifs** (`# ────`/`# ═══`) → faux positifs « commented code ».
- **34 vrais blocs de code commenté** → traités au paquet suivant.
- **7 « autres »** = commentaires inline sur du vrai code (`return False  # UNSUPPORTED`) → FP.

Action : suppression des 163 lignes de pure décoration via `tmp/sonar/remove_separators.py`,
qui **re-vérifie le contenu de chaque ligne** (refus si ce n'est pas un séparateur). Les
libellés de section (`# FINANCE`, …) restent. **163/163 conformes, 0 skip.**

**Audit hostile** : compilation des 87 fichiers → 87/87 OK ; diff = 163 deletions, 0 ligne
ajoutée hors décoration, 0 ligne de code ; gitlinks `mcp_servers/*` exclus (dirty
préexistant). **0 défaut.** Commit `4b7199e0`.

### Paquet S125-code — vrai code commenté Python (python:S125, 34 findings → 14 fichiers)

Suppression des blocs de code réellement commenté (méthodes mortes `_clean_text`/`_chunk_text`
dans `synthesize.py`, chemins RFC dev désactivés dans `kokoro_tts.py`/`whisper.py`, imports
morts dans `memory.py`/`messages.py`/`shell_ssh.py`, fonction `_deserialize_history` morte
dans `persist_chat.py`, etc.) via `tmp/sonar/remove_code_comments.py`.

**Garde-fou** : toute ligne ciblée doit être un commentaire ou une ligne vide ; sinon le
fichier est abandonné (anti off-by-one / anti-régression). 14/14 fichiers traités, **0
abandon**, 130 lignes retirées. Compilation 14/14 OK ; diff = commentaires/vides uniquement.

**Faux positifs conservés (prose, pas du code)** — non touchés :
- `python/helpers/legal_orchestrator.py:296` — `# MEDIUM, HIGH, CRITICAL + non-INFO = required`
  (commentaire explicatif du `return True`).
- `python/helpers/legal_pipeline.py:1179-1181` — documentation des seuils de consensus
  (`LOW/MEDIUM: 2/3`, `BOARD: …`, `HIGH: unanimity`).
- `python/helpers/rfc.py:63` — `# import module` (libellé pédagogique, pas du code exécutable).

**0 défaut.**

### Paquet S125-js — code JavaScript commenté (javascript:S125, 24 findings → 8 fichiers)

Suppression de 107 lignes de code JS commenté + **suppression du module mort
`webui/js/timeout.js`** (16 lignes 100 % commentées en syntaxe TS, **aucune référence**
dans `webui/` → fichier supprimé via `git rm`).

Détail : `node_eval.js` (console.log debug), `speech-store.js` (listener désactivé),
`notification-store.js` (auto-cleanup mort), `memory-dashboard-store.js` (init mort),
`modals.js` (bloc removeChild commenté + meta-commentaire associé), `scheduler.js`
(définition `showToast` morte L12-60 — la vraie est à L63 ; + 1 `showToast` commenté L784),
`settings.js` (`initSettingsModal` mort).

**Faux positif conservé** : `webui/js/modals.js:125`
`const componentPath = modalPath; // \`modals/${modalPath}/modal.html\`;` = **code actif**
avec commentaire inline → non touché.

**Audit hostile** : garde-fou (lignes vides/`//`/`/*`/`*` uniquement) → 0 abandon ; diff =
commentaires/vides uniquement (0 ligne de code retirée, 0 ajout) ; `node --check` en mode
module sur les 5 fichiers ES → 5/5 OK ; `settings.js`/`node_eval.js` OK. **0 défaut.**

### css:S125 (19 findings) — déjà couverts par le Paquet 1

Les 6 fichiers porteurs (`simple-action-buttons.css`, `notification-toast-stack.html`,
`project-edit-basic-data.html`, `memory-detail-modal.html`, `settings.css`, `toast.css`)
ont été nettoyés au Paquet 1. Les numéros de ligne du rapport pointent désormais vers du
code actif (lignes décalées) → **aucune action**, déjà résolu.

### Paquet S1128-js — imports nommés inutilisés (javascript:S1128, 35 findings → 30 fichiers)

Les composants Alpine font `import { store } from ".../X-store.js"` mais ne référencent
**jamais** le binding `store` : chaque `X-store.js` s'auto-enregistre via `createStore(...)`
au niveau module (side-effect), et les templates utilisent la magie Alpine `$store.X`
(sans rapport avec le binding importé).

**Correctif** (préserve le comportement) : `import { store } from "X";` → `import "X";`
(import nu). Le binding inutilisé disparaît (clear S1128) **et** le module reste chargé
→ le store reste enregistré. 35/35 lignes converties (1:1, 30 fichiers).

**Garde anti-régression** : script refusant la conversion si le binding est réellement
utilisé comme identifiant JS (recherche `\bNOM\b` non précédé de `$`, hors lignes
d'import/commentaire, dans les blocs `<script>`). 2 faux positifs de la garde levés
manuellement (`microphone.html` : `store` n'apparaissait que dans une chaîne
`"…-store.js"` ; `messages.js` : commentaire `// keep here, required in html` préservé).

**Audit hostile** : diff = lignes `import` uniquement (35 ins / 35 del, 0 autre) ;
`node --check` (module) sur `messages.js` → OK ; side-effect d'enregistrement des stores
préservé sur les 30 fichiers. **0 défaut.**

### Paquet S7781-js — `replaceAll` (javascript:S7781, 32 findings → 5 fichiers)

`S7781` n'est levé **que** pour `.replace()` avec une regex **globale** (flag `g`) →
conversion 1:1 sûre `.replace(/…/g, …)` → `.replaceAll(/…/g, …)` (replaceAll exige le
flag global, présent). Aucun changement de comportement (replace avec `/g` remplace déjà
toutes les occurrences).

Fichiers : `speech-store.js`, `projects-store.js`, `link-normalizer.mjs`, `messages.js`,
`speech_browser.js`. 25 cas convertis par script (flag global prouvé sur la même ligne :
regex littérale `/…g/` ou `new RegExp(…, "…g…")`), 7 cas multi-ligne / regex en variable
convertis à la main après **vérification de la définition** (`imageTagRegex`, `pathPattern`,
`pathRegex` = `new RegExp(…, "g")`, etc. — tous globaux).

**Audit hostile** : `node --check` (module) sur les 5 fichiers → 5/5 OK ; diff = uniquement
`.replace(` → `.replaceAll(` (aucune autre modification). **0 défaut.**

### Paquet S6582-js — optional chaining (javascript:S6582, 33 findings → 11 fichiers)

⚠️ Mes paquets précédents ont **décalé les numéros de ligne** de plusieurs fichiers
(`scheduler.js` -50, `settings.js` -15, …). J'ai donc repéré les motifs par **pattern**
(`BASE && BASE.x` auto-garde) et non par numéro de ligne — plus robuste.

Règles sûres appliquées : `BASE && BASE.x` → `BASE?.x`, `BASE && BASE()` → `BASE?.()`,
`!BASE || !BASE.x` → `!BASE?.x` (le backreference garantit que c'est le même objet qui se
garde lui-même = exactement la redondance ciblée par S6582). Contextes vérifiés : gardes
`if`, négations, ternaires, appels, assignements — tous équivalents en comportement.

41 motifs corrigés (les 33 findings + extras trouvés par pattern) : 3 chaînes 3 niveaux
collapsées à la main (`authData?.settings?.sections`, `kvps?.attachments?.length`,
`window.Alpine?.store?.(…)`), 38 mono-niveau par script restreint aux lignes inspectées.

**Audit hostile** : `node --check` (module) sur les 11 fichiers → 11/11 OK ; revue visuelle
des 41 lignes du diff (équivalence sémantique confirmée) ; re-scan final → **0 redondance
`X && X.` restante** dans les 11 fichiers. **0 défaut.**

### Paquet S112-py — exceptions génériques (python:S112, 49 findings → 17 fichiers)

`raise Exception(...)` générique → exception spécifique, choisie par sémantique :
- **ValueError** : validation d'entrée / argument manquant ou invalide (handlers API
  `projects`, `upload*`, `knowledge_*`, `nudge` ; `rfc_files` « Path is not a … » ;
  `rfc` « Invalid RFC hash »).
- **PermissionError** : accès refusé (`projects`, `upload_work_dir_files`).
- **RuntimeError** : état/IO/ressource (`shell_ssh`/`shell_local` « Shell not connected »,
  `rfc_files` « Failed to … », `projects` « Context not found », `memory`, `runtime`,
  `settings`, `playwright`).

**46 raises de production convertis** ; 0 `raise Exception(` restant dans les fichiers prod.

**Audit hostile — risque d'interception vérifié** :
- handler API top-level = `except Exception` (`api.py:108`) → toute sous-classe reste
  capturée → 500 inchangé.
- TOUS les `except RuntimeError` étroits du dépôt inspectés (`defer`, `critical_output`,
  `legal_orchestrator:1903`, `task_scheduler:577`, monologue `_35/_36`, `integrity_block`,
  `api.py`) sont scopés sur `loop.stop`/`asyncio.get_event_loop`/`sign_evidence_output`/
  `getattr(g,…)` — **aucun** n'enveloppe d'appel aux helpers convertis → pas d'interception.
- compilation 15/15 OK ; diff = lignes `raise` uniquement.

**Faux positifs (laissés)** : `tests/test_metacognition_policy.py:713/758` (`Exception(...)`
créée volontairement comme **donnée de test** pour `sanitize_exception`) et
`tests/test_research_executor.py:377` (`raise Exception("Simulated failure")` simulant un
échec en test) — modifier le type fausserait l'intention du test. **0 défaut.**

### Paquet S7735-js — conditions négatives (javascript:S7735 no-negated-condition, 14 findings → 7 fichiers)

Règle de **lisibilité** : `if (<négatif>) {A} else {B}` → `if (<positif>) {B} else {A}`
(inversion + permutation des branches). Détection précise par **appariement d'accolades**
(les `if (!…)` sans `else` = gardes, non concernées), car les paquets précédents ont
décalé les numéros de ligne.

**10 cas corrigés** (swaps simples à deux branches, équivalence stricte) :
`input-store.js` (`!response.ok`), `speech-store.js` (`processed !== inputText`),
`mcp-servers-store.js` (`dark != "false"`), `messages.js` ×2 (`!preElement`, `!messageDiv`),
`scheduler.js` ×2 (`!isNaN(...)`), `memory-dashboard-store.js` ×3 (`!silent`).

**4 cas DIFFÉRÉS** (inversion nuirait à la lisibilité / risque de swap disproportionné pour
un finding cosmétique) :
- `scheduler.js:242` et `:599` — chaînes `if / else if / else` (inverser le 1er test
  imposerait de restructurer toute la chaîne).
- `scheduler.js:1515` — `else` contenant toute la définition d'un composant (gros bloc).
- `preferences-store.js:72` — `else if (storedDarkMode !== null)` dans une chaîne.

**Audit hostile** : `node --check` (module) sur les 6 fichiers → 6/6 OK ; re-détection
finale → seuls les 4 cas différés (assumés) subsistent ; revue visuelle des 10 swaps
(branches correctement permutées). **0 défaut.**

### Paquet S1192-py — littéraux dupliqués → constantes (python:S1192, 41 findings → 24 fichiers)

`findings.json` ne porte pas le texte du littéral ; chaque cible a été identifiée par
analyse **token-aware** (`tokenize`), indépendante des numéros de ligne décalés par les
paquets précédents. Extraction via un outil token-aware (`tmp/sonar/extract_const.py`) :
remplace **uniquement** les tokens STRING identiques (jamais une sous-chaîne ni un f-string)
et insère la constante `_UPPER` (privée → pas d'export) au niveau module, après le dernier
import top-level (fin réelle calculée par AST pour gérer les imports multi-lignes).

**26 findings corrigés** (19 fichiers de production), littéraux-**valeurs** uniquement :
- Messages d'erreur : `shell_ssh` (« Shell not connected »), `tty_session`
  (« TTYSpawn is not started »), `scheduler` (« Task UUID is required »), `projects`
  (« Project name is required »), `legal_agent_contracts` (« Must not be empty »).
- Constantes techniques : `replay` (`application/json`), `pdf_generator` (`Helvetica-Bold`),
  `strategic_charts` (`offset points`), `reasoning_engine` (`step by step`),
  `persistence/stores` (`KOREV_REDIS_URL` + URL Redis par défaut), `models.py`
  (préfixe `sentence-transformers/`), `legal_citations_db` (regex `R\d{3}-…`).
- Contenu métier : `settings` (5 libellés/description LiteLLM + JSON MCP par défaut),
  `legal_sources/models` (licence Etalab, URLs Etalab/PISTE, « CGU PISTE »),
  `contract_drafting/templates` (« KOREV Legal — Internal Review » ×8 + séparateur),
  `contract_drafting/models` (séparateur), `evidence_document/templates`
  (« CONFIDENTIEL - SECRET MÉDICAL »), `judilibre` (« Cour de cassation »).

**15 findings DIFFÉRÉS — extraction non pertinente / risquée (documentés)** :
- **Fixtures de test** (7) : `tests/fixtures/legal_corpus.py` (6), `tests/fixtures/pdf_generator.py`
  (1) — duplication = **données de test** intentionnelles ; extraire des constantes nuit à la
  lisibilité des fixtures (pratique courante : exclure les tests de S1192).
- **Clés de dictionnaire / vocabulaire métier** (3) : `memory.py` (`"memory"`/clés),
  `legal_diff.py` (« responsabilité »/« obligation » dans des listes de mots-clés),
  `legal_rendering.py` (`"operational"`) — extraire une constante pour une clé/valeur de
  data-structure est un anti-pattern (perte de lisibilité, pas le défaut visé par S1192).
- **`strategic_orchestrator.py` (5) — behavior-adjacent, NON modifié** : le dict
  `doc_type_labels` est dupliqué 3× mais **pas à l'identique** — L1434 porte
  `"Plan Go-To-Market"` là où les 2 autres copies ont `"Plan Go-to-Market"` (casse). Une
  déduplication changerait **silencieusement** le titre PDF d'un chemin. Conformément au
  protocole d'audit (pas de changement de comportement caché), l'extraction est différée et
  l'**incohérence de casse est remontée** pour décision produit.

**Audit hostile** :
- **DEF-1 (CRITIQUE, corrigé)** : 1ʳᵉ insertion dans `evidence_document/templates.py` plaçait
  la constante **après son usage** (imports top-level dispersés en milieu de fichier →
  `import re` ~L502 postérieur au dict `TEMPLATES` ~L429). `py_compile` ne détecte pas la
  résolution de noms ; l'**import réel** a révélé le `NameError`. Corrigé : constante remontée
  juste après les imports du haut.
- **Contrôle systématique post-DEF-1** : vérification statique AST « constante définie avant
  toutes ses utilisations » sur **les 19 fichiers** → 0 problème ; `import` runtime des modules
  modifiés → OK (l'échec isolé de `shell_ssh` = import circulaire **préexistant** dans
  `helpers/strings`, mon diff n'ajoute aucun import).
- `py_compile` 19/19 OK ; chaque littéral extrait ne subsiste qu'**une fois** (sa définition).
- **Non-régression** : `run_tests.sh local` → **3426 passed**, 36 skipped. Les 82 `failed`
  (`test_pdf_migration_parity`, `test_rebrand_agent_zero`) sont **préexistants** — prouvé en
  rejouant ces fichiers sur l'arbre **sans** mes modifs (échouent à l'identique). Round-trip
  `git stash` revérifié : 0 marqueur de conflit, 19/19 compilent, import OK. **0 défaut résiduel.**

### Paquet S1481-py — variables locales inutilisées (python:S1481, 165 findings ; via ruff F841)

`findings.json` ne porte pas le contexte ; détection croisée avec **ruff F841** (105 occurrences :
68 prod, 37 tests ; 17 = binding d'exception `as e` inutilisé, 17 « safe-fix », 88 « unsafe-fix »).

**Sous-lot A — bindings d'exception inutilisés (16 corrigés, 13 fichiers)** : `except X as e:` →
`except X:` quand `e` n'est **jamais** lu dans le handler (blocs `pass`/`return`/assignation simple).
Fichiers : `agent.py` (×4), `models.py`, `api/tunnel_proxy.py`, `tools/browser_agent.py`, et 6
extensions de masquage/stream + `system_prompt`/`update_check`/`rename_chat`.

**Audit hostile — 1 DEF CRITIQUE évité** : ruff classait `mcp_handler.py:899` en « safe-fix »
alors que `e` y **est** réutilisé (`raise e` L909) sur le chemin où `original_exception is None` —
retirer `as e` provoquerait un `NameError` runtime (= la régression déjà revertée en session
antérieure). **Exclu du fix** (revert ciblé après `ruff --fix`).
- Filet de sécurité AST : aucun handler `except` sans binding (dans les fichiers modifiés) ne
  référence `e` → 0 danger.
- `py_compile` 13/13 OK ; ruff F841 : 105 → **89** (les 16 visés résolus ; le 1 « fixable »
  restant = `mcp_handler`, assumé non corrigé). **0 défaut.**

**Sous-lot B — affectations `var = <expr>` inutilisées (88 traitées, 58 fichiers)** :
transformation **universellement préservante** (outil AST `tmp/sonar/transform_f841.py`) :
- RHS **sans aucun** `Call`/`Await`/`Yield` → suppression de l'instruction (pur, 0 effet de bord).
- RHS **contenant un appel** → on garde l'expression (on retire seulement `var =`), préservant
  TOUS les effets de bord. Cas critiques validés : lancements `defer.DeferredTask().start_task()`
  (settings ×4), `subparsers.add_parser()` (enregistrement sous-commandes), `files.create_dir_safe()`,
  `memory.Memory.get()`, `await self._get_chat_context()`, `_verify_medical_domain()`,
  `safe_path_join()` (validation sécurité), constructions/`record_decision()` en tests.

**Audit hostile** :
- **DEF (corrigés en cours de route)** : `ast.get_source_segment` perdait les parenthèses
  englobantes (`x = ( EXPR )`) → 3 `IndentationError`. Corrigé : coupe juste après le `=`
  (les lignes d'origine, donc les parenthèses, sont gardées verbatim) → `py_compile` 58/58 OK.
- **Cascades** : retirer un binding a révélé 1 2ᵉ affectation inutilisée (`image_get.py` branche
  `if`) → corrigée pareillement (appel `safe_path_join` conservé).
- **2 findings DIFFÉRÉS et documentés** :
  - `mcp_handler.py:896/899` — `except Exception as e:` où `e` **est** réutilisé (`raise e`) sur le
    chemin `original_exception is None` ; ruff le classe « safe-fix » à tort → retirer `as e`
    causerait un `NameError`. **Non corrigé** (assumé).
  - `consensus_arbiter.py:193` — `consensus_enabled = ui_settings.get(...)` : la variable est
    **calculée mais jamais appliquée** (le toggle UI consensus ne gate rien). Plutôt que de
    supprimer silencieusement un flag censé piloter le comportement, **revert + bug latent
    remonté** pour décision produit.
- **Non-régression** : `run_tests.sh local` → **3426 passed**, 36 skipped, 82 failed
  **tous pré-existants** (prouvé : `git stash` de mes 58 fichiers puis rejeu des 4 fichiers
  suspects — `pdf_characterization`, `evidence_document`, `chat_style`, `dockerfile_ocr` —
  qui échouent à l'identique, deps PDF/PyMuPDF/Docker/OCR absentes). Round-trip `git stash`
  revérifié (58/58 compilent, 0 marqueur de conflit).

**Bilan S1481** : ruff F841 **105 → 2** (104 résolus : 16 bindings d'exception + 88 affectations ;
les 2 résiduels = différés assumés ci-dessus).

---

## Bugs latents — investigation ciblée (post-S1481)

Deux affectations « mortes » repérées pendant S1481 méritaient une investigation de fond
(et non une suppression mécanique), pour vérifier qu'elles ne masquaient pas un bug fonctionnel.

### LAT-1 — `consensus_arbiter.py` : `consensus_enabled` lu puis jamais appliqué

- **Symptôme** : `load_consensus_config()` lisait `ui_settings.get("consensus_enabled", True)`
  dans une variable locale jamais réutilisée. À première vue : le toggle UI « activer le consensus »
  serait ignoré → bug critique potentiel.
- **Investigation** : `ConsensusConfig` (le dataclass renvoyé ici) décrit le **COMMENT** du consensus
  (arbitres, timeouts, simulation), **pas le SI**. L'activation/désactivation est appliquée **en amont**
  dans le pipeline de recherche (gating PRISM), pas dans l'arbitre. Le `dataclass` n'a d'ailleurs
  **aucun champ `enabled`** → la lecture locale était structurellement incapable d'avoir un effet.
- **Verdict** : **PAS un bug fonctionnel** — le toggle est bien respecté ailleurs. La ligne était du
  **code mort trompeur** (suggérait un effet inexistant).
- **Action** : lecture retirée + commentaire d'intention ajouté (pourquoi le flag ne se relit PAS ici).
- **Preuve** : `tests/test_consensus_*` **44/44 OK** ; `load_consensus_config()` charge bien 3 arbitres.

### LAT-2 — `image_get.py` : expression `metadata` morte

- **Symptôme** : une expression `input.get("metadata", …) == "true"` était évaluée puis jetée (le
  consommateur — bloc d'enrichissement metadata — est commenté).
- **Verdict** : code mort (fonctionnalité désactivée), **pas une régression** : la route utilisait déjà
  `path` (et non un `resolved`) ; `safe_path_join` (validation/anti-traversal) est **conservé**.
- **Action** : expression morte retirée, appel de validation préservé.

**Bilan bugs latents** : 0 bug fonctionnel confirmé ; 2 cas de code mort trompeur nettoyés.
ruff F841 **2 → 1** (reste `mcp_handler:896`, différé assumé).

---

## Tier 4 — `javascript:S6859` (imports absolus webui, 91 findings) — FAUX POSITIF assumé

**Règle Sonar** : « utiliser des chemins d'import relatifs » (cible les projets bundlés/Node où
`/` = chemin filesystem absolu).

**Pourquoi c'est un FP ici** : le webui est servi par
`Flask(static_folder="./webui", static_url_path="/")`. Les imports `import "/components/..."` /
`from "/js/..."` sont des **URL racine navigateur** (modules ES natifs servis verbatim à `/`), pas
des chemins bundler. Ici `/` = **origine HTTP**, donc l'absolu est **correct et intentionnel** (stable
même si un fichier est déplacé).

**Preuve dure (pourquoi convertir CASSERAIT l'UI)** : `webui/js/components.js` charge les scripts
module **inline** des fragments `.html` en les transformant en **Blob** (`URL.createObjectURL`). Dans
un module Blob, un import **relatif** se résout contre l'URL du blob (sans arborescence) → **cassé** ;
seul un chemin **racine-absolu** se résout (contre l'origine). De plus, le regex de réécriture du
loader ne matche que `import X from "Y"`, alors que les 35 imports HTML sont des imports **à effet de
bord** `import "/x.js";` (sans `from`) → non réécrits, donc l'absolu y est **obligatoire**.

**Répartition** : 91 findings / 49 fichiers (56 en `.js`, 35 en `.html`). Les 35 HTML *exigent*
l'absolu (blob) ; convertir les 56 `.js` seuls n'apporterait rien et rendrait le codebase incohérent
(HTML absolu + JS relatif) + fragiliserait (aucun test JS/webui).

**Action** : neutralisé en FP tracé dans `sonar-project.properties`
(`sonar.issue.ignore.multicriteria.s6859webui` → `javascript:S6859` sur `webui/**/*`). **0 ligne de
code modifiée**, donc **0 risque de régression UI**. Retire les 91 findings du gate Sonar.

---

## Tier 4 — `python:S1172` (paramètres inutilisés, 35 findings) — tri + correctifs

**Constat** : contrairement à S6859 (FP architectural uniforme), S1172 ici est un **mélange**.
Retirer un paramètre change une signature → impacte appelants, overrides, callbacks. Sévérité
**MINOR**. Cartographie AST des 35 findings (helper `tmp/sonar/inspect_s1172.py`, robuste à la dérive
de lignes) → classement en 4 groupes.

### Groupe A — retraits sûrs (vestige pur, appelants maîtrisés)

- `python/helpers/process.py:get_server(server)` → **`server` retiré** : **0 appelant** dans tout le
  repo (les `get_server*` voisins sont des méthodes `MCPConfig` distinctes), arg ignoré (renvoyait le
  global `_server`). Vestige de copier-coller depuis `set_server`.

### Groupe B — singletons suspects investigués (2 vrais correctifs, qui UTILISENT le param)

| Fonction | Verdict | Action |
|---|---|---|
| `contradictor/orchestration.py:build_audit_log(agent_response)` | **Lacune de traçabilité** : la réponse auditée n'était pas hachée alors que la docstring promet « questions and responses are hashed ». | **Fix** : ajout `"response_hash": _stable_hash(agent_response)` au dict d'audit (TDD : `test_contradictor_audit_trace_contains_required_fields`). |
| `metacognition.py:_apply_hardening_signals(raw_confidence)` | Docstring « (pour log) » jamais tenue ; l'appelant (`escalation_computed`) **logge déjà** `raw_confidence`. Param réellement vestigial. | **Fix** : `raw_confidence` retiré (2 appelants internes mis à jour). Restaure la signature historique documentée `(base, signals, flags)`. |

### Groupe C — singletons suspects MAIS légitimes (documentés, won't-fix par design)

- `legal_diff.py:qualify_change(change_type)` : la qualification se calcule **entièrement** par diff de
  mots-clés `before`/`after`, qui encode déjà l'ajout/retrait → `change_type` **redondant**. Fonction
  publique appelée positionnellement par de nombreux tests → retrait = casse disproportionnée pour MINOR.
- `pdf_extraction/pipeline.py:calculate_overall_confidence(pdf_type)` : seul `pdf_type_confidence`
  (le score) sert ; le type est subsumé par ce score → redondant.
- `pdf_extraction/pipeline.py:detect_table_regions(config)` : **stub assumé** (« For now… A real
  implementation would cluster… use DBSCAN ») ; `config` sert dans l'implémentation cible (le voisin
  `cluster_columns` l'utilise). Param de signature prévu.
- `pdf_extraction/pipeline.py:try_optional_engines(words)` : Camelot ré-extrait depuis le fichier (pas
  de `words` pré-extraits) → `words` forward-compat pour l'uniformité des moteurs.

### Groupe D — contrats d'API / familles à signature uniforme (won't-fix par design)

- **Familles de dispatch** (signature uniforme volontaire) : `memory_consolidation._handle_*`
  + `_extract_search_keywords`/`_analyze_memory_consolidation` (`log_item` ×6), `reasoning_engine._handle_trivial`
  + `_try_alternative`/`build_decision_tree`, `tty_session._spawn_*` (`echo`, signature cross-plateforme),
  `evidence_document/renderer._render_*` + `_build_assumptions_section` (`template` ×3, `strict`).
- **Miroirs d'interface / API documentée** : `python/api/message.communicate(input)` (miroir de
  `ApiHandler.process(self, input, request)` — retirer déplacerait juste le finding sur l'override),
  `legal_orchestrator.run_legal_pipeline(route_decision)` / `execute_consensus(call_llm_func)`
  (API documentée appelée par des dizaines de tests + prod), `integrity_block.verify_signature`
  (`query`/`response`/`document` — stabilité de signature du vérifieur).
- **Forward-compat / logging** : `correlation_id`, `validate_medical_output(force_sync)`,
  `contract_drafting(contract_type, max_retries)`, `research_executor.call(timeout_ms)`,
  `research_pipeline._decompose_with_llm(max_depth)`, `create_fail_closed_response(query_context)`,
  `_format_rejected_conclusion(query)`, `record_timeout(engine)`.

**Bilan S1172** : 3 findings résolus dans le code (1 retrait sûr + 2 correctifs qui *utilisent* le
paramètre comme prévu, dont **1 vrai renforcement de traçabilité d'audit**) ; 32 documentés
won't-fix-par-design (familles uniformes, contrats d'API, redondances, stubs, forward-compat). **Aucun
retrait de signature risqué pour un gain MINOR.** Tests : 80/80 verts (contradictor + métacognition
+ doctrine) ; ruff ARG : 0 sur les 3 fonctions corrigées.

---

## Tier 4 — `python:S3776` (complexité cognitive, 123 findings) — refactors par cycles

**Méthode** : 1 fonction = 1 cycle (filet golden en place → refactor à comportement constant →
tests verts → audit hostile → commit). On commence par les fonctions **les mieux couvertes** (le
filet anti-régression prime sur le rang de complexité brut).

### Cycle 1 — `router/router.py:decide_route` (le plus complexe : CC 55, rang F)

**Pourquoi en premier** : cerveau du routage MAIS couverture massive (76 tests router + cité dans
25 fichiers de tests) et fonction **strictement déterministe** → filet golden idéal. Déjà structurée
en STEP 0-12 → extraction mécanique.

**Refactor (comportement constant, 6 helpers extraits)** :

- `_score_all_available_intents` (STEP 2, bloc le plus imbriqué), `_apply_board_level_intents` (STEP 3),
  `_apply_multi_intent_rules` (STEP 4), `_build_sorted_route_intents` (STEP 5),
  `_build_unavailable_critical_decision` (STEP 6, early-return → `Optional[RouteDecision]`),
  `_resolve_injection_enforcement` (STEP 7, early-return → `Optional[RouteDecision]`),
  `_compute_routing_strength` (STEP 10).
- Mutations d'état partagé (`reasons`, `intent_scores`) préservées **par référence** pour garder
  l'ordre exact des messages ; early-returns transformés en pattern `if (d := helper(...)) is not None`.

**Résultat** : `decide_route` **CC 55 (rang F) → 14 (rang C)** ; tous les helpers en rang A/B
(max B/10). **0 ligne de logique modifiée.**

**Audit hostile** : ordre des STEP préservé (board-level avant multi-intent ; STEP 6 avant STEP 7) ;
mutation par référence vérifiée ; 0 défaut. **Tests : 224/224 verts** (router, déterminisme, contrat,
métriques, injection_handling, board_level_collision, strategic_pipeline_e2e).
