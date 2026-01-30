#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Lint documentaire pour l'audit KOREV Evidence (mode briques).

Règles bloquantes :
A) Chaque brique (B-###) doit avoir : BrickID, Nom, Statut, Preuves, Validation, Limites.
B) Aucune collision de ClaimID (un ClaimID ne peut pointer vers 2+ briques).
C) "Implemented" interdit sans preuve runtime wiring ou test d'intégration.
D) Mentions "audit trail", "persistant", "E2E", "wired" doivent être justifiées.
"""

from __future__ import annotations

import re
import sys
from collections import defaultdict
from pathlib import Path
from typing import NamedTuple

AUDIT_PATH_DEFAULT = Path(__file__).resolve().parents[1] / "docs" / "KOREV_Evidence_Audit.md"

STATUS_ALLOWED = {"Implemented", "Partial", "Planned", "Unverified"}

SECTION_HEADERS_CLAIMS = {
    "## Executive Summary (FR)",
    "## Executive Summary (EN)",
    "## 12. Commercial Extract (1 page, FR)",
    "## 13. CTO Brief (1 page, EN)",
}

# Mots-clés nécessitant preuve explicite (règle D)
PROOF_REQUIRED_KEYWORDS = {
    "audit trail": "preuve d'audit trail",
    "persistant": "persistance",
    "e2e": "test E2E",
    "wired": "wiring runtime",
    "end-to-end": "test end-to-end",
}


class LintError(NamedTuple):
    rule: str
    brick_id: str | None
    message: str

    def __str__(self) -> str:
        prefix = f"[{self.rule}]"
        if self.brick_id:
            prefix += f" {self.brick_id}:"
        return f"{prefix} {self.message}"


class AuditLinter:
    """Lint complet de l'audit KOREV Evidence."""

    def __init__(self, path: Path):
        self.path = path
        self.text = self._read_text(path)
        self.errors: list[LintError] = []
        self.bricks: dict[str, dict] = {}
        self.claim_to_bricks: dict[str, list[str]] = defaultdict(list)

    def _read_text(self, path: Path) -> str:
        try:
            return path.read_text(encoding="utf-8")
        except FileNotFoundError:
            print(f"[ERREUR] Fichier introuvable: {path}")
            sys.exit(2)

    def _truncate_at_marker(self) -> None:
        """Tronque le texte au marqueur END AUDIT pour éviter duplications."""
        marker = "<!-- END AUDIT -->"
        if marker in self.text:
            self.text = self.text.split(marker, 1)[0]
        # Également détecter les répétitions du titre
        title = "# KOREV Evidence — Objective Audit"
        occurrences = self.text.count(title)
        if occurrences > 1:
            # Ne garder que la première occurrence
            parts = self.text.split(title)
            self.text = title + parts[1] if len(parts) > 1 else self.text

    def run(self) -> int:
        """Exécute toutes les vérifications. Retourne 0 si PASS, 1 si FAIL."""
        self._truncate_at_marker()
        
        # Parse les briques
        self._parse_bricks()
        
        # Règle A : structure des briques
        self._lint_brick_structure()
        
        # Règle B : collisions de ClaimID
        self._lint_claim_collisions()
        
        # Règle C : Implemented sans preuve
        self._lint_implemented_without_proof()
        
        # Règle D : mots-clés non justifiés
        self._lint_unjustified_claims()
        
        # Vérifications additionnelles
        self._lint_claims_in_sections()
        self._lint_capability_matrix()
        self._lint_appendix_consistency()

        # Rapport
        if self.errors:
            print("[FAIL] Lint documentaire")
            print(f"       {len(self.errors)} erreur(s) détectée(s)\n")
            for err in self.errors:
                print(f"  - {err}")
            return 1

        print("[PASS] Lint documentaire")
        print(f"       {len(self.bricks)} brique(s) validée(s)")
        return 0

    def _parse_bricks(self) -> None:
        """Parse le registre des briques (section 2.1)."""
        lines = self.text.splitlines()
        in_bricks = False
        current_id: str | None = None
        current_lines: list[str] = []

        for line in lines:
            if line.strip() == "## 2.1 Registre des briques (Brick Register)":
                in_bricks = True
                continue
            if in_bricks and line.startswith("## "):
                break
            if in_bricks:
                match = re.match(r"^###\s+(B-\d{3})\s+[-—]\s+(.+)$", line)
                if match:
                    if current_id:
                        self.bricks[current_id] = {
                            "lines": current_lines,
                            "block": "\n".join(current_lines),
                        }
                    current_id = match.group(1)
                    current_lines = [line]
                elif current_id:
                    current_lines.append(line)
        
        if current_id:
            self.bricks[current_id] = {
                "lines": current_lines,
                "block": "\n".join(current_lines),
            }

        if not self.bricks:
            self.errors.append(LintError("A", None, "Aucune brique détectée (section 2.1 manquante?)"))

    def _lint_brick_structure(self) -> None:
        """Règle A : vérifie la structure de chaque brique."""
        for brick_id, payload in self.bricks.items():
            block = payload["block"]
            
            # Statut
            statut_match = re.search(r"^- Statut:\s*(.+)$", block, re.M)
            if not statut_match:
                self.errors.append(LintError("A", brick_id, "Statut manquant"))
            else:
                statut = statut_match.group(1).strip()
                if statut not in STATUS_ALLOWED:
                    self.errors.append(LintError("A", brick_id, f"Statut invalide '{statut}'"))
            
            # ClaimID
            claim_match = re.search(r"^- ClaimID:\s*(C-\d{3})$", block, re.M)
            if not claim_match:
                self.errors.append(LintError("A", brick_id, "ClaimID manquant ou format invalide (attendu: C-###)"))
            else:
                claim_id = claim_match.group(1)
                self.claim_to_bricks[claim_id].append(brick_id)
            
            # Sections obligatoires
            if "- Preuves:" not in block:
                self.errors.append(LintError("A", brick_id, "Section 'Preuves' manquante"))
            if "- Validation:" not in block:
                self.errors.append(LintError("A", brick_id, "Section 'Validation' manquante"))
            if "- Limites:" not in block:
                self.errors.append(LintError("A", brick_id, "Section 'Limites' manquante"))
            
            # Sous-champs Validation
            for field in ("- Commande:", "- Preuve attendue:", "- Critere PASS/FAIL:"):
                if field not in block:
                    self.errors.append(LintError("A", brick_id, f"Validation: '{field}' manquant"))
            
            # Au moins une preuve listée
            preuves_lines = [
                ln.strip() for ln in payload["lines"]
                if any(ln.strip().startswith(f"- {kw}:") for kw in ("Code", "Test", "Wiring runtime", "Runtime"))
            ]
            if not preuves_lines:
                self.errors.append(LintError("A", brick_id, "Aucune preuve listée (Code/Test/Wiring)"))

    def _lint_claim_collisions(self) -> None:
        """Règle B : détecte les collisions de ClaimID."""
        for claim_id, brick_list in self.claim_to_bricks.items():
            if len(brick_list) > 1:
                bricks_str = ", ".join(brick_list)
                self.errors.append(LintError(
                    "B", None,
                    f"Collision ClaimID {claim_id} : utilisé par {bricks_str}"
                ))

    def _lint_implemented_without_proof(self) -> None:
        """Règle C : Implemented interdit sans preuve runtime/integration."""
        for brick_id, payload in self.bricks.items():
            block = payload["block"]
            statut_match = re.search(r"^- Statut:\s*(.+)$", block, re.M)
            if not statut_match:
                continue
            statut = statut_match.group(1).strip()
            if statut != "Implemented":
                continue
            
            # Doit avoir runtime wiring OU test d'intégration
            has_proof = any(
                kw.lower() in block.lower()
                for kw in (
                    "Wiring runtime:",
                    "Runtime:",
                    "Test d'integration",
                    "Test d'intégration",
                    "E2E",
                    "integration test",
                    "test_e2e",
                    "_e2e_",
                )
            )
            if not has_proof:
                self.errors.append(LintError(
                    "C", brick_id,
                    "Statut 'Implemented' sans preuve runtime wiring ou test d'intégration"
                ))

    def _lint_unjustified_claims(self) -> None:
        """Règle D : mots-clés nécessitant justification."""
        for brick_id, payload in self.bricks.items():
            block = payload["block"].lower()
            
            # Mots-clés à vérifier
            for keyword, description in PROOF_REQUIRED_KEYWORDS.items():
                if keyword in block:
                    # Vérifier si UNVERIFIED ou preuve explicite
                    has_unverified = "unverified" in block
                    has_test = re.search(r"- Test:.*test_", block, re.I)
                    has_wiring = "wiring runtime:" in block.lower() or "runtime:" in block.lower()
                    
                    if not (has_unverified or has_test or has_wiring):
                        # Vérifier si la limite mentionne l'absence de preuve
                        limites_match = re.search(r"- Limites:(.+?)(?=^- |\Z)", block, re.M | re.S)
                        if limites_match:
                            limites_text = limites_match.group(1).lower()
                            if "non démontr" in limites_text or "non demontr" in limites_text or "unverified" in limites_text:
                                continue
                        
                        self.errors.append(LintError(
                            "D", brick_id,
                            f"Mention '{keyword}' sans preuve explicite ni UNVERIFIED"
                        ))

    def _lint_claims_in_sections(self) -> None:
        """Vérifie que les claims dans les sections exécutives ont un ClaimID."""
        lines = self.text.splitlines()
        current_section: str | None = None
        
        for i, line in enumerate(lines, start=1):
            if line.startswith("## "):
                current_section = line.strip()
                continue
            if current_section in SECTION_HEADERS_CLAIMS:
                stripped = line.strip()
                if not stripped or stripped.startswith("## ") or stripped.startswith("**"):
                    continue
                if "[C-" not in stripped and "UNVERIFIED" not in stripped:
                    # Ignorer les lignes de formatage, listes vides, etc.
                    if stripped.startswith("-") and len(stripped) > 5:
                        self.errors.append(LintError(
                            "A", None,
                            f"Ligne {i}: claim sans ClaimID/UNVERIFIED dans {current_section}"
                        ))

    def _lint_capability_matrix(self) -> None:
        """Vérifie que la matrice des capacités a des ClaimID valides."""
        lines = self.text.splitlines()
        in_matrix = False
        
        for i, line in enumerate(lines, start=1):
            if line.strip() == "## 2. Capability Matrix":
                in_matrix = True
                continue
            if in_matrix:
                if line.startswith("## "):
                    break
                if line.startswith("|"):
                    if "ClaimID" in line or re.match(r"^\|\s*-+\s*\|", line):
                        continue
                    cols = [c.strip() for c in line.strip().strip("|").split("|")]
                    if len(cols) >= 3:
                        claim_id = cols[2]
                        if not re.match(r"^C-\d{3}$", claim_id):
                            self.errors.append(LintError(
                                "A", None,
                                f"Ligne {i}: ClaimID manquant/invalide dans Capability Matrix"
                            ))

    def _lint_appendix_consistency(self) -> None:
        """Vérifie la cohérence de l'Appendix A avec les briques."""
        appendix_claims = set()
        in_appendix = False
        
        for line in self.text.splitlines():
            if re.match(r"^## Appendix A\s*[-—]\s*Evidence Index$", line.strip()):
                in_appendix = True
                continue
            if in_appendix and line.startswith("## "):
                break
            if in_appendix:
                # Format attendu : | C-### |
                match = re.match(r"^\|\s*(C-\d{3})\s*\|", line)
                if match:
                    appendix_claims.add(match.group(1))
        
        # Claims utilisés dans le document
        used_claims = set(re.findall(r"\[C-\d{3}\]", self.text))
        used_claims = {c.strip("[]") for c in used_claims}
        
        # Claims dans les briques
        brick_claims = set(self.claim_to_bricks.keys())
        
        # Vérifier cohérence
        missing_in_appendix = brick_claims - appendix_claims
        if missing_in_appendix and appendix_claims:
            self.errors.append(LintError(
                "A", None,
                f"ClaimID(s) brique(s) absents de l'Appendix A: {', '.join(sorted(missing_in_appendix))}"
            ))


def main() -> int:
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else AUDIT_PATH_DEFAULT
    linter = AuditLinter(path)
    return linter.run()


if __name__ == "__main__":
    raise SystemExit(main())
