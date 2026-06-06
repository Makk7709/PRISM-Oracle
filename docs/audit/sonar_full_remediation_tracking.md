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
