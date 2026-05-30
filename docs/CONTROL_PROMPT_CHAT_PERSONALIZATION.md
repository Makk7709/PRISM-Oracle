# PROMPT DE CONTRÔLE — Personnalisation du chat (symbiose homme-IA)

**Version :** 1.0  
**Usage :** Appliquer ce checklist avant de considérer la feature comme validée.  
**Mode :** Contrôle hyper strict — aucun écart toléré.

---

## 1. Règle R1 — Overlay uniquement (aucun impact sur logique)

| # | Critère | Vérification | OK |
|---|---------|--------------|-----|
| R1.1 | Le bloc style ne modifie pas les tool calls | `build_style_instruction()` ne contient aucun mot-clé `tool_name`, `tool_args`, `arguments` dans un contexte d'instruction de modification | ☐ |
| R1.2 | Aucune instruction de bypass sécurité | Le texte généré ne contient pas : "ignore", "bypass", "contourner", "skip", "override" | ☐ |
| R1.3 | Pas de modification du consensus | Le fichier `_05_chat_style.py` n'importe pas et n'appelle pas consensus / strategic enforcement | ☐ |
| R1.4 | Extension overlay-only | L'extension ne fait QUE `system_prompt.insert(0, block)` — pas de modification de loop_data, tool schemas, etc. | ☐ |

---

## 2. Règle R2 — Options prédéfinies (pas d'injection)

| # | Critère | Vérification | OK |
|---|---------|--------------|-----|
| R2.1 | Valeurs ton strictes | `_VALID_TONE` = `formel`, `cordial`, `direct`, `bienveillant` | ☐ |
| R2.2 | Valeurs humanisation strictes | `_VALID_HUMANIZATION` = `minimal`, `modere`, `eleve` | ☐ |
| R2.3 | Valeurs verbosité strictes | `_VALID_VERBOSITY` = `concise`, `equilibre`, `detaille` | ☐ |
| R2.4 | Pas de format string user | Aucun `.format()` ou f-string avec des valeurs utilisateur non validées ; templates codés en dur | ☐ |
| R2.5 | UI limitée aux options | `convert_out` expose uniquement des `select`/`switch` avec options fixes | ☐ |

---

## 3. Règle R3 — Injection en début de system prompt

| # | Critère | Vérification | OK |
|---|---------|--------------|-----|
| R3.1 | `insert(0, ...)` utilisé | `system_prompt.insert(0, style_block)` — pas `append` | ☐ |
| R3.2 | Extension `_05_` avant `_10_` | Nom de fichier garantit ordre d'exécution avant system prompt principal | ☐ |
| R3.3 | Bloc non vide | `build_style_instruction()` ne retourne jamais une chaîne vide | ☐ |

---

## 4. Règle R4 — Rétrocompatibilité

| # | Critère | Vérification | OK |
|---|---------|--------------|-----|
| R4.1 | `settings=None` → défaut | `build_style_instruction(None)` retourne un bloc valide (vouvoiement, cordial, modere, equilibre) | ☐ |
| R4.2 | `settings={}` → défaut | Idem pour dict vide | ☐ |
| R4.3 | Valeur invalide → fallback | `chat_tone="xyz"` → fallback `cordial` ; idem pour humanization, verbosity | ☐ |
| R4.4 | settings.json sans clés → démarrage OK | `normalize_settings` ajoute les clés manquantes avec défauts | ☐ |

---

## 5. Règle R5 — Non-régression

| # | Critère | Vérification | OK |
|---|---------|--------------|-----|
| R5.1 | Tests chat_personalization verts | `pytest tests/chat_personalization/ -v` → 26 passed | ☐ |
| R5.2 | Tests security verts | `pytest tests/security/ -q` → 330+ passed | ☐ |
| R5.3 | Aucun import circulaire | Démarrage de l'app sans ImportError | ☐ |

---

## 6. Tests TDD obligatoires (matrice spec)

| ID | Description | Fichier test | OK |
|----|-------------|--------------|-----|
| T01 | build_style_instruction importable, retourne str, non vide | test_chat_style.py | ☐ |
| T02 | None/empty settings → défaut neutre | test_chat_style.py | ☐ |
| T03 | Tutoiement vs vouvoiement | test_chat_style.py | ☐ |
| T04 | Ton values (formel, cordial, direct, bienveillant) | test_chat_style.py | ☐ |
| T05 | Humanization values | test_chat_style.py | ☐ |
| T06 | Verbosity values | test_chat_style.py | ☐ |
| T07 | Pas d'injection (curly braces) | test_chat_style.py | ☐ |
| T08 | Toutes combinaisons produisent non-vide | test_chat_style.py | ☐ |
| T08 | Extension exists, execute callable | test_chat_style_extension.py | ☐ |
| T09 | Extension prepend à system_prompt, index 0 | test_chat_style_extension.py | ☐ |
| T10 | Style block ne contient pas override tool schema | test_chat_style_extension.py | ☐ |
| T11 | chat_persona : homme, femme, ia | test_chat_style.py | ☐ |
| T12 | chat_ai_name sanitisé, max 30 | test_chat_style.py | ☐ |
| T13 | chat_persona invalide → ia | test_chat_style.py | ☐ |

---

## 7. Fichiers requis

| Fichier | Existe | Contenu attendu |
|---------|--------|-----------------|
| `python/helpers/chat_style.py` | ☐ | `build_style_instruction(settings) -> str` |
| `python/extensions/system_prompt/_05_chat_style.py` | ☐ | `ChatStyleExtension` avec `execute(system_prompt, loop_data)` |
| `python/helpers/settings.py` | ☐ | chat_address_tu, chat_tone, chat_humanization, chat_verbosity, chat_persona, chat_ai_name |
| `docs/SPEC_CHAT_PERSONALIZATION.md` | ☐ | Spec complète |
| `docs/CONTROL_PROMPT_CHAT_PERSONALIZATION.md` | ☐ | Ce document |

---

## 8. Application du contrôle (commandes)

```bash
# 1. Tests personnalisation
python -m pytest tests/chat_personalization/ -v --tb=short

# 2. Tests non-régression
python -m pytest tests/security/ -q --tb=no

# 3. Vérification imports
python -c "
from python.helpers.chat_style import build_style_instruction
from python.extensions.system_prompt._05_chat_style import ChatStyleExtension
from python.helpers.settings import get_settings
s = get_settings()
assert 'chat_address_tu' in s
assert 'chat_tone' in s
assert 'chat_persona' in s
assert 'chat_ai_name' in s
block = build_style_instruction(s)
assert len(block) > 0
assert 'STYLE' in block or 'style' in block.lower()
print('OK: imports and defaults')
"
```

---

## 9. Résultat du dernier contrôle

| Date | Résultat | Exécutant |
|------|----------|-----------|
| 2026-02-08 | **VALIDÉ** — 26/26 tests chat_personalization, 330+ security | Amine Mohamed |

### Checklist exécutée

- **R1** : Overlay uniquement — OK (pas de tool_name/tool_args, pas de bypass, extension fait uniquement insert)
- **R2** : Options prédéfinies — OK (_VALID_TONE/HUMANIZATION/VERBOSITY, UI select/switch)
- **R3** : Injection en début — OK (insert(0, ...), _05_ avant _10_)
- **R4** : Rétrocompatibilité — OK (None/{} → défaut, invalides → fallback)
- **R5** : Non-régression — OK (tests security verts)
- **T01-T10** : Tous les tests passent
- **Fichiers** : Présents et conformes

---

**Signature :** Ce prompt de contrôle doit être exécuté et les cases cochées avant toute merge de la feature personnalisation chat.
