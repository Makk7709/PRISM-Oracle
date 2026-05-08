"""
TDD tests for documentation quality improvements (P1-1, P1-2, P2-3, P2-6).

These tests verify the existence, structure and correctness of:
- SECURITY.md (P1-1)
- Architecture Decision Records (P1-2)
- GLOSSARY.md (P2-6)
- C4 Architecture Diagrams (P2-3)

Run: pytest tests/test_documentation_quality.py -v
"""

import os
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent


# ═══════════════════════════════════════════════════════════════════════════════
# P1-1 — SECURITY.md
# ═══════════════════════════════════════════════════════════════════════════════

class TestSecurityMd:
    """SECURITY.md must exist at repo root and contain required sections."""

    SECURITY_PATH = ROOT / "SECURITY.md"

    @pytest.fixture(autouse=True)
    def _load(self):
        assert self.SECURITY_PATH.exists(), "SECURITY.md must exist at repo root"
        self.content = self.SECURITY_PATH.read_text(encoding="utf-8")

    def test_file_exists(self):
        assert self.SECURITY_PATH.is_file()

    def test_minimum_length(self):
        assert len(self.content) > 500, "SECURITY.md should be substantial (>500 chars)"

    def test_has_disclosure_policy(self):
        assert re.search(r"(?i)(divulgation|disclosure|report.*vulnerabilit)", self.content), \
            "Must contain a responsible disclosure / vulnerability reporting section"

    def test_has_scope(self):
        assert re.search(r"(?i)(p[eé]rim[eè]tre|scope|couverture)", self.content), \
            "Must define the security scope/perimeter"

    def test_has_contact(self):
        assert re.search(r"(?i)(contact|security@|signaler|report)", self.content), \
            "Must provide a security contact or reporting mechanism"

    def test_has_response_commitment(self):
        assert re.search(r"(?i)(d[eé]lai|délai|response.*time|48.*heure|72.*heure|jours)", self.content), \
            "Must include a response time commitment"

    def test_has_crypto_practices(self):
        assert re.search(r"(?i)(argon2|hmac|sha.256|chiffrement|hash|crypto)", self.content), \
            "Must mention cryptographic practices used"

    def test_has_auth_section(self):
        assert re.search(r"(?i)(authentification|authentication|mot de passe|password)", self.content), \
            "Must cover authentication practices"

    def test_has_rate_limiting(self):
        assert re.search(r"(?i)(rate.limit|limitation.*d[eé]bit|protection.*brute)", self.content), \
            "Must mention rate limiting"

    def test_has_no_default_secrets_statement(self):
        assert re.search(r"(?i)(pas de.*secret.*d[eé]faut|no.*default.*secret|RuntimeError)", self.content), \
            "Must state that no default secrets are shipped"

    def test_references_env_variables(self):
        assert "EVIDENCE_HMAC_KEY" in self.content, \
            "Must reference EVIDENCE_HMAC_KEY"

    def test_no_placeholder_text(self):
        assert "TODO" not in self.content, "No TODO placeholders allowed"
        assert "FIXME" not in self.content, "No FIXME placeholders allowed"


# ═══════════════════════════════════════════════════════════════════════════════
# P1-2 — Architecture Decision Records (ADR)
# ═══════════════════════════════════════════════════════════════════════════════

class TestADRs:
    """ADRs must exist in docs/adr/ with proper format and content."""

    ADR_DIR = ROOT / "docs" / "adr"

    REQUIRED_ADRS = {
        "ADR-001": "PRISM",
        "ADR-002": "router",
        "ADR-003": "Evidence",
        "ADR-004": "LiteLLM",
        "ADR-005": "extension",
    }

    ADR_REQUIRED_SECTIONS = [
        r"(?i)(statut|status)",
        r"(?i)(contexte|context)",
        r"(?i)(d[eé]cision|decision)",
        r"(?i)(cons[eé]quences|consequences)",
        r"(?i)(alternatives|options)",
    ]

    @pytest.fixture(autouse=True)
    def _load(self):
        assert self.ADR_DIR.exists(), "docs/adr/ directory must exist"
        self.adr_files = sorted(self.ADR_DIR.glob("*.md"))

    def test_adr_directory_exists(self):
        assert self.ADR_DIR.is_dir()

    def test_minimum_adr_count(self):
        assert len(self.adr_files) >= 5, f"Need at least 5 ADRs, found {len(self.adr_files)}"

    @pytest.mark.parametrize("adr_id,topic", [
        ("ADR-001", "PRISM"),
        ("ADR-002", "router"),
        ("ADR-003", "Evidence"),
        ("ADR-004", "LiteLLM"),
        ("ADR-005", "extension"),
    ])
    def test_required_adr_exists(self, adr_id, topic):
        matching = [f for f in self.adr_files if adr_id.lower().replace("-", "") in f.name.lower().replace("-", "")]
        assert len(matching) >= 1, f"{adr_id} ({topic}) ADR file not found"

    @pytest.mark.parametrize("adr_id,topic", [
        ("ADR-001", "PRISM"),
        ("ADR-002", "router"),
        ("ADR-003", "Evidence"),
        ("ADR-004", "LiteLLM"),
        ("ADR-005", "extension"),
    ])
    def test_adr_has_required_sections(self, adr_id, topic):
        matching = [f for f in self.adr_files if adr_id.lower().replace("-", "") in f.name.lower().replace("-", "")]
        assert matching, f"No file for {adr_id}"
        content = matching[0].read_text(encoding="utf-8")
        for section_pattern in self.ADR_REQUIRED_SECTIONS:
            assert re.search(section_pattern, content), \
                f"{adr_id}: missing section matching '{section_pattern}'"

    @pytest.mark.parametrize("adr_id,topic", [
        ("ADR-001", "PRISM"),
        ("ADR-002", "router"),
        ("ADR-003", "Evidence"),
        ("ADR-004", "LiteLLM"),
        ("ADR-005", "extension"),
    ])
    def test_adr_minimum_length(self, adr_id, topic):
        matching = [f for f in self.adr_files if adr_id.lower().replace("-", "") in f.name.lower().replace("-", "")]
        assert matching, f"No file for {adr_id}"
        content = matching[0].read_text(encoding="utf-8")
        assert len(content) > 400, f"{adr_id} is too short (<400 chars)"

    @pytest.mark.parametrize("adr_id,topic", [
        ("ADR-001", "PRISM"),
        ("ADR-002", "router"),
        ("ADR-003", "Evidence"),
        ("ADR-004", "LiteLLM"),
        ("ADR-005", "extension"),
    ])
    def test_adr_has_date(self, adr_id, topic):
        matching = [f for f in self.adr_files if adr_id.lower().replace("-", "") in f.name.lower().replace("-", "")]
        assert matching, f"No file for {adr_id}"
        content = matching[0].read_text(encoding="utf-8")
        assert re.search(r"(20\d{2}|Date|date)", content), \
            f"{adr_id}: must include a date"

    def test_no_placeholder_text_in_adrs(self):
        for f in self.adr_files:
            content = f.read_text(encoding="utf-8")
            assert "TODO" not in content, f"{f.name}: no TODO placeholders"
            assert "FIXME" not in content, f"{f.name}: no FIXME placeholders"


# ═══════════════════════════════════════════════════════════════════════════════
# P2-6 — GLOSSARY.md
# ═══════════════════════════════════════════════════════════════════════════════

class TestGlossary:
    """GLOSSARY.md must exist in docs/ and define all proprietary terms."""

    GLOSSARY_PATH = ROOT / "docs" / "GLOSSARY.md"

    REQUIRED_TERMS = [
        "PRISM",
        "Evidence",
        "SessionEnvelope",
        "RouteDecision",
        "IntegrityBlock",
        "ComplianceGrid",
        "ConsensusManager",
        "ArbiterCaller",
        "fail-closed",
        "ReplayEngine",
        "HumanReview",
        "DynamicRiskRegister",
    ]

    @pytest.fixture(autouse=True)
    def _load(self):
        assert self.GLOSSARY_PATH.exists(), "docs/GLOSSARY.md must exist"
        self.content = self.GLOSSARY_PATH.read_text(encoding="utf-8")

    def test_file_exists(self):
        assert self.GLOSSARY_PATH.is_file()

    def test_minimum_length(self):
        assert len(self.content) > 1000, "GLOSSARY.md should be substantial (>1000 chars)"

    @pytest.mark.parametrize("term", [
        "PRISM", "Evidence", "SessionEnvelope", "RouteDecision",
        "IntegrityBlock", "ComplianceGrid", "ConsensusManager",
        "ArbiterCaller", "fail-closed", "ReplayEngine",
        "HumanReview", "DynamicRiskRegister",
    ])
    def test_term_defined(self, term):
        assert re.search(re.escape(term), self.content, re.IGNORECASE), \
            f"Term '{term}' must be defined in GLOSSARY.md"

    def test_minimum_term_count(self):
        headings = re.findall(r"^#{1,4}\s+.+", self.content, re.MULTILINE)
        term_markers = re.findall(r"^\*\*[^*]+\*\*", self.content, re.MULTILINE)
        total_entries = len(headings) + len(term_markers)
        assert total_entries >= 15, f"Need at least 15 glossary entries, found {total_entries}"

    def test_no_placeholder_text(self):
        assert "TODO" not in self.content
        assert "FIXME" not in self.content


# ═══════════════════════════════════════════════════════════════════════════════
# P2-3 — C4 Architecture Diagrams
# ═══════════════════════════════════════════════════════════════════════════════

class TestC4Diagrams:
    """Architecture diagrams must exist in docs/ with valid Mermaid."""

    ARCH_PATH = ROOT / "docs" / "ARCHITECTURE_C4_DIAGRAMS.md"

    @pytest.fixture(autouse=True)
    def _load(self):
        assert self.ARCH_PATH.exists(), "docs/ARCHITECTURE_C4_DIAGRAMS.md must exist"
        self.content = self.ARCH_PATH.read_text(encoding="utf-8")

    def test_file_exists(self):
        assert self.ARCH_PATH.is_file()

    def test_minimum_length(self):
        assert len(self.content) > 2000, "C4 diagrams document should be substantial"

    def test_has_context_diagram(self):
        assert re.search(r"(?i)(contexte|context|niveau.1|level.1|C4.*context)", self.content), \
            "Must include a C4 Context diagram (Level 1)"

    def test_has_container_diagram(self):
        assert re.search(r"(?i)(container|conteneur|niveau.2|level.2)", self.content), \
            "Must include a C4 Container diagram (Level 2)"

    def test_has_component_diagram(self):
        assert re.search(r"(?i)(component|composant|niveau.3|level.3)", self.content), \
            "Must include a C4 Component diagram (Level 3)"

    def test_has_mermaid_blocks(self):
        mermaid_blocks = re.findall(r"```mermaid", self.content)
        assert len(mermaid_blocks) >= 3, \
            f"Need at least 3 Mermaid diagram blocks, found {len(mermaid_blocks)}"

    def test_mermaid_blocks_are_closed(self):
        opens = len(re.findall(r"```mermaid", self.content))
        closes = self.content.count("```")
        assert closes >= opens * 2, "All Mermaid blocks must be properly closed"

    def test_mentions_key_components(self):
        key_components = ["Flask", "PRISM", "Evidence", "Caddy", "Docker", "LLM"]
        found = sum(1 for c in key_components if c.lower() in self.content.lower())
        assert found >= 4, f"Diagrams should mention key components, found {found}/6"

    def test_mentions_agent_loop(self):
        assert re.search(r"(?i)(agent|monologue|orchestrat)", self.content), \
            "Must reference the agent orchestration loop"

    def test_no_placeholder_text(self):
        assert "TODO" not in self.content
        assert "FIXME" not in self.content


# ═══════════════════════════════════════════════════════════════════════════════
# Cross-document coherence
# ═══════════════════════════════════════════════════════════════════════════════

class TestCrossDocumentCoherence:
    """Verify that new documents are referenced in existing docs."""

    def test_security_md_referenced_in_onboarding(self):
        onboarding = (ROOT / "docs" / "DEVELOPER_ONBOARDING_ARCHITECTURE_GUIDE.md")
        if onboarding.exists():
            content = onboarding.read_text(encoding="utf-8")
            assert re.search(r"(?i)SECURITY\.md", content), \
                "SECURITY.md should be referenced in the onboarding guide"

    def test_adr_directory_referenced_in_onboarding(self):
        onboarding = (ROOT / "docs" / "DEVELOPER_ONBOARDING_ARCHITECTURE_GUIDE.md")
        if onboarding.exists():
            content = onboarding.read_text(encoding="utf-8")
            assert re.search(r"(?i)(docs/adr|Architecture Decision Record|ADR-\d{3}|\bADR\b.*PRISM)", content), \
                "ADRs should be explicitly referenced in the onboarding guide"

    def test_glossary_referenced_in_onboarding(self):
        onboarding = (ROOT / "docs" / "DEVELOPER_ONBOARDING_ARCHITECTURE_GUIDE.md")
        if onboarding.exists():
            content = onboarding.read_text(encoding="utf-8")
            assert re.search(r"GLOSSARY\.md", content), \
                "GLOSSARY.md should be explicitly referenced in the onboarding guide"
