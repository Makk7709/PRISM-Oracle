"""
Test P0-1 (audit hostile chemin critique) : le garde-fou d'exception de l'outil
`response` ne doit JAMAIS émettre une sortie critique (ou de criticité indéterminée)
non signée. Il n'émet le texte brut que si la non-criticité est prouvée.
"""

import types

import pytest

from python.helpers.tool import Tool  # noqa: F401  (assure que agent importe)
from python.tools.response import ResponseTool


class _FakeConfig:
    profile = ""
    chat_model = None


class _FakeMsg:
    def output_text(self):
        return "requête utilisateur"


class _FakeAgent:
    def __init__(self):
        self._data = {}
        self.config = _FakeConfig()
        self.context = types.SimpleNamespace(get_data=lambda k: None)
        self.last_user_message = _FakeMsg()
        self.agent_name = "test-agent"
        self.number = 0

    def get_data(self, k):
        return self._data.get(k)

    def set_data(self, k, v):
        self._data[k] = v


def _make_tool(agent):
    return ResponseTool(
        agent=agent, name="response", method=None,
        args={"text": "Réponse critique."}, message="", loop_data=None,
    )


@pytest.mark.asyncio
async def test_gate_failure_undetermined_criticality_fail_closed(monkeypatch):
    """Si le router lève (criticité indéterminée) → fail-closed, pas de texte brut."""
    import python.helpers.criticality_router as cr

    def _boom(*a, **k):
        raise RuntimeError("router exploded")

    monkeypatch.setattr(cr, "get_criticality_router", _boom)

    tool = _make_tool(_FakeAgent())
    resp = await tool.execute()
    assert resp.break_loop is True
    assert "fail-closed" in resp.message.lower()
    assert "Réponse critique." not in resp.message


@pytest.mark.asyncio
async def test_gate_failure_proven_noncritical_emits_raw(monkeypatch):
    """Si la non-criticité est prouvée puis le signage échoue → texte brut toléré."""
    import python.helpers.criticality_router as cr
    import python.helpers.critical_output as co

    fake_assessment = types.SimpleNamespace(requires_consensus=False, strict_evidence_mode=False)
    monkeypatch.setattr(
        cr, "get_criticality_router",
        lambda: types.SimpleNamespace(assess=lambda **k: fake_assessment),
    )

    def _boom(**k):
        raise RuntimeError("sign exploded")

    monkeypatch.setattr(co, "finalize_critical_output", _boom)

    tool = _make_tool(_FakeAgent())
    resp = await tool.execute()
    assert resp.break_loop is True
    assert resp.message == "Réponse critique."
