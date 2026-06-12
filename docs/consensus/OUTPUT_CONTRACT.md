Output Contract (Chat UI)
=========================

Canonical fields
----------------

- `text` (string, required, non-empty): user-visible response

Internal fields (never displayed)
---------------------------------

- `thoughts` (string, optional)
- `debug` (object, optional)
- `trace` (array, optional)
- `router_decision` (object, optional)
- `tool_calls` (array/object, optional)
- `internal` (any, optional)

Rules
-----

1) UI must display **only** `text`.
2) If `text` is missing or empty:
   - Backend: fail-fast OR fallback to `text="Réponse indisponible (erreur de format)."`
   - UI: if still empty, show `Réponse indisponible.` and never show internal fields.
3) Internal fields are allowed for logging but must never appear in UI.

Examples
--------

Valid:

```json
{"text":"Bonjour","thoughts":"secret","debug":{"x":1}}
```

Invalid:

```json
{"thoughts":"secret"}
```
