import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


PROMPTS = [
    Path(__file__).parent.parent / "prompts" / "agent.system.main.role.md",
    Path(__file__).parent.parent / "agents" / "multitask" / "prompts" / "agent.system.main.role.md",
    Path(__file__).parent.parent / "agents" / "legal_safe" / "prompts" / "agent.system.main.role.md",
]


def test_identity_branding_prompts():
    for prompt in PROMPTS:
        contents = prompt.read_text(encoding="utf-8")
        assert "KOREV Evidence" in contents
        assert "KOREV AI" in contents
        assert "OpenAI" not in contents
