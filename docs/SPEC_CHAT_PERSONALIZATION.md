# SPEC — Personnalisation du chat (symbiose homme-IA)

**Version :** 1.0  
**Date :** 2026-02-11  
**Objectif :** Augmenter la rétention et la symbiose homme-IA via des paramètres de style sans casser la logique système.

---

## Règles absolues

### R1 — Overlay uniquement

Les paramètres de personnalisation sont des **overlays de style** sur les réponses. Ils ne modifient PAS :

- Les structures des tool calls (JSON tool_name, tool_args)
- Les règles de sécurité (cite sources, fail-closed, consensus)
- La logique de routage (orchestrateur → agents)

### R2 — Options prédéfinies

Les valeurs sont **prédéfinies** (dropdown, pas de texte libre) pour éviter les injections de prompt.

### R3 — Injection en début de system prompt

Le bloc de style est injecté **au début** du system prompt (avant le rôle principal) pour que le LLM le voie prioritairement.

### R4 — Rétrocompatibilité

Si les paramètres sont absents ou invalides, le comportement par défaut est neutre (vouvoiement, ton cordial, humanisation modérée).

### R5 — Non-régression

Les tool calls, le consensus, et les réponses structurées restent inchangés. Les tests existants doivent rester verts.

---

## Paramètres

| Paramètre | Clé | Valeurs | Défaut |
|-----------|-----|---------|--------|
| **Adresse** | `chat_address_tu` | `true` (tutoiement), `false` (vouvoiement) | `false` |
| **Ton** | `chat_tone` | `formel`, `cordial`, `direct`, `bienveillant` | `cordial` |
| **Humanisation** | `chat_humanization` | `minimal`, `modere`, `eleve` | `modere` |
| **Verbosité** | `chat_verbosity` | `concise`, `equilibre`, `detaille` | `equilibre` |
| **Persona** | `chat_persona` | `homme`, `femme`, `ia` | `ia` |
| **Nom IA** | `chat_ai_name` | Chaîne max 30 car., sanitisée | `""` |

### chat_persona

- `homme` : L'assistant s'exprime au masculin (ex: "je suis ravi", "content").
- `femme` : L'assistant s'exprime au féminin (ex: "je suis ravie", "contente").
- `ia` : Expression neutre, sans genre explicite.

### chat_ai_name (R2bis)

- Texte libre sanitisé : lettres, chiffres, espaces, accents français uniquement.
- Max 30 caractères. Caractères dangereux supprimés (pas d'injection).

---

## Instructions générées (exemples)

### chat_address_tu=true (tutoiement)

```text
STYLE DE COMMUNICATION — Adresse l'utilisateur en le tutoyant (tu, ton, ta).
```

### chat_address_tu=false (vouvoiement)

```text
STYLE DE COMMUNICATION — Adresse l'utilisateur en le vouvoyant (vous, votre).
```

### chat_tone

- `formel` : Ton professionnel et distant.
- `cordial` : Ton chaleureux et respectueux.
- `direct` : Ton direct, sans formules superflues.
- `bienveillant` : Ton empathique et encourageant.

### chat_humanization

- `minimal` : Réponses factuelles, peu de reformulations.
- `modere` : Reformulations naturelles, transitions fluides.
- `eleve` : Langage très naturel, variété d'expressions, transitions humaines.

### chat_verbosity

- `concise` : Réponses courtes, à l'essentiel.
- `equilibre` : Longueur moyenne.
- `detaille` : Explications complètes.

### chat_persona

- `homme` : Tu t'exprimes au masculin (ex: je suis ravi, content).
- `femme` : Tu t'exprimes au féminin (ex: je suis ravie, contente).
- `ia` : Expression neutre, sans genre explicite.

### chat_ai_name

- Si non vide : Tu te présentes sous le nom « X » lorsque pertinent.

---

## Matrice de tests obligatoires

| ID | Règle | Test |
|----|-------|------|
| T01 | R2 | Valeurs invalides rejetées |
| T02 | R4 | Absence de paramètres → défaut neutre |
| T03 | R3 | Bloc style présent en début de system prompt |
| T04 | R1 | Tool call JSON inchangé avec personnalisation activée |
| T05 | R5 | Tests existants (security, multi-user) restent verts |
| T06 | R2 | build_style_instruction retourne texte non vide pour chaque combinaison valide |
| T07 | R4 | chat_address_tu absent → vouvoiement |
| T08 | - | Extension chargée et injecte le bloc |
| T09 | - | Settings UI affiche les options |
| T10 | R1 | Consensus/critical pipeline non affecté |
| T11 | R2 | chat_persona : homme, femme, ia |
| T12 | R2bis | chat_ai_name sanitisé, max 30 |
| T13 | R4 | chat_persona invalide → ia |

---

## Fichiers concernés

- `python/helpers/chat_style.py` — Nouveau : `build_style_instruction(settings) -> str`
- `python/extensions/system_prompt/_05_chat_style.py` — Nouveau : injection
- `python/helpers/settings.py` — TypedDict, defaults, convert_out, convert_in
- `prompts/agent.system.chat_style.md` — Template optionnel (ou génération in-code)
- `tests/` — Tests unitaires et intégration
