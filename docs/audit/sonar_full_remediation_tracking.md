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
| 1 | 1 | css:S125, css:S4658 | 7 | 20 | ✅ corrigé | 0 défaut | _(en cours)_ |

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
