> ⚠️ **DOCUMENT ARCHIVÉ**
> **Statut** : Historique (migration terminée)
> **Date d'archivage** : 2026-05-31
> **Raison** : Feuille de route de renommage produit (rebranding). La migration est achevée.
> **Remplacé par** : néant (migration terminée)
> **Ne pas utiliser comme référence opérationnelle active.**

# 🔄 Feuille de Route : KOREV Evidence → KOREV Evidence

## Contexte

**Changement** : Renommer le produit de "KOREV Evidence" à "KOREV Evidence"
**Raison** : Nom libre, valide FR/EN, aligné avec la proposition de valeur (evidence-based)

## Inventaire

| Catégorie | Occurrences | Fichiers |
|-----------|-------------|----------|
| Documentation (*.md) | ~350 | docs/, agents/, knowledge/ |
| Code Python (*.py) | ~150 | python/, tests/, tools/ |
| Configuration (*.json,*.yaml) | ~50 | conf/, mcp_config*.json |
| Scripts (*.sh) | ~20 | scripts/, deploy/ |
| WebUI (*.html,*.js) | ~30 | webui/ |

**Total estimé** : ~600 occurrences (hors logs)

## Patterns à Remplacer

| Pattern Source | Pattern Cible |
|----------------|---------------|
| `KOREV Evidence` | `KOREV Evidence` |
| `KOREV Evidence` | `KOREV Evidence` |
| `KOREV_Evidence` | `KOREV_Evidence` |
| `korev_evidence` | `korev_evidence` |
| `korev-evidence` | `korev-evidence` |

## Feuille de Route (7 Étapes)

### Étape 1: Backup ✅

```bash
git stash  # ou commit préalable
```

### Étape 2: Documentation (docs/, agents/, knowledge/)

- Priorité: HAUTE
- Risque de casse: FAIBLE
- Fichiers: *.md

### Étape 3: Tests

- Priorité: HAUTE  
- Risque de casse: MOYEN (noms de classes, imports)
- Fichiers: tests/*.py, tests/*.md

### Étape 4: Code Python (python/helpers/)

- Priorité: CRITIQUE
- Risque de casse: ÉLEVÉ
- Validation: Run tests après chaque batch

### Étape 5: Configuration

- Priorité: MOYENNE
- Fichiers: *.json,*.yaml, *.yml

### Étape 6: WebUI

- Priorité: MOYENNE
- Fichiers: webui/*.html, webui/*.js

### Étape 7: Scripts & Deploy

- Priorité: BASSE
- Fichiers: scripts/*.sh, deploy/

## Validation Après Chaque Étape

```bash
# Tests rapides
python tools/test_report.py --fast

# Si OK, tests complets
python tools/test_report.py --full
```

## Rollback Plan

```bash
git checkout -- .  # Annuler toutes les modifications
# ou
git stash pop      # Restaurer le stash
```

## Fichiers à NE PAS Modifier

- `logs/*.html` — Historique, pas critique
- `venv/` — Environnement virtuel
- `.git/` — Historique git
- `*.pyc`, `__pycache__/` — Cache Python

## Checklist Finale

- [ ] Tests FAST passent
- [ ] Tests FULL passent
- [ ] WebUI se lance sans erreur
- [ ] Aucune référence "Evidence" restante (sauf logs)
- [ ] Commit + Push

---

**Durée estimée** : 15-20 minutes
**Risque** : Faible si suivi étape par étape
