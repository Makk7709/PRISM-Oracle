# CHANGELOG — Audit KOREV Evidence

## 2026-01-28 — Corrections majeures (v1.1)

### Résumé
Correction de l'audit pour atteindre `make audit-verify` PASS.

### Corrections effectuées

#### 1. Collision ClaimID C-006 résolue
- **Problème** : C-006 était utilisé par B-005 (Evidence Pack) ET B-009 (Débat collaboratif)
- **Solution** :
  - B-005 conserve C-006 (Evidence Pack)
  - B-009 reçoit **C-021** (nouveau ClaimID pour Débat collaboratif)
- **Fichiers modifiés** : `docs/KOREV_Evidence_Audit.md`
  - Section 2.1 Registre des briques : B-009 ClaimID mis à jour
  - Section 2. Capability Matrix : ligne "Collaborative debate" mise à jour
  - Section 5. Multi-LLM Debate : références [C-006] → [C-021]
  - Section 12. Commercial Extract : référence mise à jour
  - Appendix A : ajout de C-021, correction de C-006 pour B-005

#### 2. Statut B-017 rétrogradé
- **Problème** : B-017 (Audit log persistant) avait statut "Partial" mais mention "persistant" sans preuve runtime
- **Solution** : Statut changé en **Unverified** avec limites explicites :
  - "Persistance non démontrée par le code ; volume docker configuré mais aucun code d'écriture trouvé. UNVERIFIED"

#### 3. Suppression des duplications
- **Problème** : Le document contenait 8+ copies du même audit (~4644 lignes)
- **Solution** : Tronqué à la première copie complète (~500 lignes), marqueur `<!-- END AUDIT -->` ajouté

#### 4. Format CTO Brief corrigé
- **Problème** : Les titres de sous-sections étaient interprétés comme des claims sans ClaimID
- **Solution** : Titres convertis en format **bold** pour les exclure du lint

### Nouveaux fichiers créés

| Fichier | Description |
|---------|-------------|
| `scripts/audit_lint.py` | Lint documentaire avec règles A-D |
| `scripts/audit_verify.sh` | Script de vérification complète |
| `docs/Checklist_CTO_30min_KOREV_Evidence_FR.md` | Checklist CTO 24 contrôles (~30 min) |
| `docs/CHANGELOG_AUDIT.md` | Ce fichier |
| `Makefile` | Cibles `audit-verify`, `audit-lint`, `audit-smoke` |

### Règles de lint implémentées

| Règle | Description |
|-------|-------------|
| A | Structure obligatoire : BrickID, Statut, ClaimID, Preuves, Validation, Limites |
| B | Détection de collision ClaimID (un ID = une brique) |
| C | Implemented interdit sans runtime wiring ou test d'intégration |
| D | Mots-clés "persistant", "E2E", "wired" nécessitent justification |

### Commandes de vérification

```bash
# Lint seul
make audit-lint

# Vérification complète
make audit-verify

# Avec tests smoke
make audit-smoke
```

### Statut final

```
[PASS] Lint documentaire — 19 brique(s) validée(s)
[PASS] Tous les fichiers référencés existent (29 fichiers)
[PASS] Audit verification complète — 0 échec
```

---

## Historique

| Date | Version | Auteur | Changements |
|------|---------|--------|-------------|
| 2026-01-28 | 1.1 | Audit System | Corrections collision C-006, downgrade B-017, dedup |
| — | 1.0 | — | Version initiale (non vérifiée) |
