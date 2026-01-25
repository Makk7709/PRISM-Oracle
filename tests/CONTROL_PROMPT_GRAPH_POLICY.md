# 🎯 PROMPT DE CONTRÔLE — Graph Policy & Anti-Fuite Debug

**Objectif**: Vérifier que le système Evidence route correctement les demandes de graphiques vers `code_execution` et qu'AUCUNE fuite de debug n'atteint l'utilisateur.

---

## 📋 CHECKLIST DE VALIDATION

### ✅ C1 — Détection des requêtes graph (FR/EN)

| Test | Input | Attendu | Status |
|------|-------|---------|--------|
| C1.1 | "Fais un graphique des ventes" | `is_graph_request()` → `True` | ⬜ |
| C1.2 | "Génère un camembert" | `is_graph_request()` → `True` | ⬜ |
| C1.3 | "Create a bar chart" | `is_graph_request()` → `True` | ⬜ |
| C1.4 | "Plot the data" | `is_graph_request()` → `True` | ⬜ |
| C1.5 | "Lis ce fichier Excel" | `is_graph_request()` → `False` | ⬜ |

### ✅ C2 — Routage tool → code_execution

| Test | Tool appelé | Attendu | Status |
|------|-------------|---------|--------|
| C2.1 | `graph` | Reroute vers `code_execution` guidance | ⬜ |
| C2.2 | `plot` | Reroute vers `code_execution` guidance | ⬜ |
| C2.3 | `chart` | Reroute vers `code_execution` guidance | ⬜ |
| C2.4 | `histogram` | Reroute vers `code_execution` guidance | ⬜ |
| C2.5 | `pie_chart` | Reroute vers `code_execution` guidance | ⬜ |

### ✅ C3 — KILL TESTS — Aucune fuite de debug

| Test | Chaîne interdite | Sortie utilisateur | Status |
|------|-----------------|-------------------|--------|
| C3.1 | `"Tool not found"` | JAMAIS visible | ⬜ |
| C3.2 | `"Available tools:"` | JAMAIS visible | ⬜ |
| C3.3 | `"TOOL_UNAVAILABLE"` | JAMAIS visible | ⬜ |
| C3.4 | `"GRAPH_POLICY_REDIRECT"` | JAMAIS visible | ⬜ |
| C3.5 | `"MISSING_TOOL"` | JAMAIS visible | ⬜ |

### ✅ C4 — Génération de graphiques via code_execution

| Test | Fichier | Attendu | Status |
|------|---------|---------|--------|
| C4.1 | Excel valide | PNG généré dans `tmp/generated/` | ⬜ |
| C4.2 | CSV valide | PNG généré dans `tmp/generated/` | ⬜ |
| C4.3 | Fichier vide | `status=needs_input` + diagnostic | ⬜ |
| C4.4 | Colonnes non-numériques | Fallback intelligent + hypothèses | ⬜ |

### ✅ C5 — JSON Output Contract

| Test | Champ | Attendu | Status |
|------|-------|---------|--------|
| C5.1 | `artifacts` | Présent si image générée | ⬜ |
| C5.2 | `artifacts[].type` | `"image"` | ⬜ |
| C5.3 | `artifacts[].path` | Chemin valide vers PNG | ⬜ |
| C5.4 | `hypotheses` | Liste des hypothèses (si type inféré) | ⬜ |
| C5.5 | `sources` | Au moins 2 (document + tool) | ⬜ |

### ✅ C6 — Fallback "needs_input"

| Test | Situation | Attendu | Status |
|------|-----------|---------|--------|
| C6.1 | Données insuffisantes | `status=needs_input` | ⬜ |
| C6.2 | Type graph ambigu | Questions + prochaine action | ⬜ |
| C6.3 | Fichier non trouvé | Erreur propre, pas de crash | ⬜ |

---

## 🧪 COMMANDES DE TEST

### Exécuter les tests unitaires
```bash
cd /Users/aminemohamed/Desktop/APP/KOREV_Oracle/KOREV_Oracle
source venv/bin/activate
python -m pytest tests/test_graph_policy.py -v
```

### Vérifier les kill tests spécifiquement
```bash
python -m pytest tests/test_graph_policy.py::TestKillNoDebugLeaks -v
```

### Tester la génération de graphiques
```bash
python -m pytest tests/test_graph_policy.py::TestGraphGeneration -v
```

---

## 📊 RÉSUMÉ DES FICHIERS MODIFIÉS

| Fichier | Modification |
|---------|--------------|
| `python/helpers/graph_runner.py` | **NOUVEAU** — Module utilitaire matplotlib |
| `python/tools/unknown.py` | **MODIFIÉ** — Graph policy + anti-fuite |
| `python/helpers/execution_guard.py` | **MODIFIÉ** — Bloque fuites debug |
| `python/extensions/system_prompt/_10_system_prompt.py` | **MODIFIÉ** — Charge graph policy |
| `prompts/fw.tool_not_found.md` | **MODIFIÉ** — Message propre sans tool list |
| `prompts/fw.graph_policy.md` | **NOUVEAU** — Policy mandatory pour graphs |
| `tests/test_graph_policy.py` | **NOUVEAU** — 66 tests (kill + intégration) |

---

## 🎯 CRITÈRES DE SUCCÈS

### GO si:
- [ ] 66/66 tests passent
- [ ] Aucune chaîne interdite dans les sorties utilisateur
- [ ] Graph généré depuis Excel → PNG dans tmp/generated/
- [ ] Output Contract respecté (artifacts, hypotheses, sources)
- [ ] Fallback needs_input fonctionne pour données insuffisantes

### NO-GO si:
- [ ] "Tool not found" visible dans le chat
- [ ] "Available tools:" visible dans le chat
- [ ] Graph demandé mais pas généré (sans erreur propre)
- [ ] Crash du système sur fichier invalide
- [ ] seaborn utilisé au lieu de matplotlib

---

## 📝 NOTES D'IMPLÉMENTATION

### Graph Policy (Règle dure)
```
SI demande contient graph/plot/chart/courbe/camembert/histogram/bar/pie/scatter/visualiz*
ALORS utiliser UNIQUEMENT code_execution (Python + matplotlib)
SINON procéder normalement
```

### Anti-Fuite (Kill rule)
```
SI réponse contient ["Tool not found", "Available tools:", "TOOL_UNAVAILABLE", "GRAPH_POLICY_REDIRECT", "MISSING_TOOL"]
ALORS rejeter la réponse + forcer code_execution
```

### Auto-sélection du type de graphique
```
date/time + values → Line chart
categories + values → Bar chart (horizontal si >10 catégories)
categories only → Pie chart
2 numeric columns → Scatter plot
1 numeric column → Histogram
```

---

## ✅ VALIDATION FINALE

```
Date: ____/____/____
Validateur: ____________________
Version: Evidence v2.x

Résultat: [ ] GO  [ ] NO-GO

Commentaires:
_____________________________________
_____________________________________
```
