# KOREV Evidence — Makefile
# Targets de vérification et d'audit

.PHONY: audit-verify audit-lint audit-smoke help

# Vérification complète de l'audit (lint + fichiers)
audit-verify:
	@bash scripts/audit_verify.sh

# Lint documentaire uniquement
audit-lint:
	@python3 scripts/audit_lint.py docs/KOREV_Evidence_Audit.md

# Lint + tests smoke
audit-smoke:
	@bash scripts/audit_verify.sh --smoke

# Aide
help:
	@echo "KOREV Evidence — Targets disponibles"
	@echo ""
	@echo "  make audit-verify  Vérification complète de l'audit (lint + fichiers)"
	@echo "  make audit-lint    Lint documentaire uniquement"
	@echo "  make audit-smoke   Lint + tests smoke (pytest)"
	@echo "  make help          Cette aide"
