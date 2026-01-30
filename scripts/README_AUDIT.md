## Scripts audit - mode briques

### Lint documentaire
- Commande: `python3 scripts/audit_lint.py`
- Objet: verifier que chaque brique a BrickID, Statut, Preuves, Validation, Limites, ClaimID.

### Verification complete
- Commande: `make audit-verify`
- Option tests: `AUDIT_RUN_TESTS=1 make audit-verify`
