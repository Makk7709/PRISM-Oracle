"""
SESSION 7B — Tests audit leger (helpers + extension message_loop_end).
"""

from dataclasses import dataclass, field
from typing import Any, Dict
from unittest.mock import MagicMock, patch

import pytest

from python.helpers import audit_light
from python.extensions.message_loop_end._20_audit_light_append import AuditLightAppend


# ═══════════════════════════════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════════════════════════════

def test_count_words_empty():
    assert audit_light.count_words("") == 0
    assert audit_light.count_words("   ") == 0


def test_count_words_french():
    text = " ".join(["mot"] * 99)
    assert audit_light.count_words(text) == 99
    assert audit_light.count_words(text + " fin") == 100


def test_build_audit_light_markdown_contains_fields():
    md = audit_light.build_audit_light_markdown(
        session_id="KRV-SES-001",
        model_label="openai/gpt-4o",
        completed_at_iso="2026-04-01T12:00:00+00:00",
        evidence_version="v1.0.0",
    )
    assert "KRV-SES-001" in md
    assert "openai/gpt-4o" in md
    assert "2026-04-01T12:00:00+00:00" in md
    assert "v1.0.0" in md
    assert "vue synthetique" in md


def test_build_audit_light_unknown_version():
    md = audit_light.build_audit_light_markdown(
        session_id="x",
        model_label="m",
        completed_at_iso="t",
        evidence_version="unknown",
    )
    assert "non resolu" in md


@dataclass
class FakeModelConfig:
    name: str = "claude-3"
    provider: str = "anthropic"


def test_resolve_model_label():
    assert audit_light.resolve_model_label(None) == "unknown"
    assert audit_light.resolve_model_label(FakeModelConfig()) == "anthropic/claude-3"
    assert audit_light.resolve_model_label(FakeModelConfig(provider="", name="local")) == "local"


# ═══════════════════════════════════════════════════════════════════════════════
# EXTENSION
# ═══════════════════════════════════════════════════════════════════════════════

class FakeLogItem:
    def __init__(self, content: str = ""):
        self.content = content
        self.updates = []

    def update(self, content=None, **kwargs):
        if content is not None:
            self.content = content
        self.updates.append({"content": content, **kwargs})


@dataclass
class FakeLoopData:
    last_response: str = ""
    params_temporary: Dict[str, Any] = field(default_factory=dict)


@dataclass
class FakeEnvelope:
    session_id: str = "KRV-TEST"
    evidence_version: str = "v9.9.9"


class FakeAgent:
    def __init__(self, number: int = 0):
        self.number = number
        self.data: Dict[str, Any] = {}
        self.config = MagicMock()
        self.config.chat_model = FakeModelConfig()

    def get_data(self, key: str):
        return self.data.get(key)

    def set_data(self, key: str, value: Any):
        self.data[key] = value


@pytest.mark.asyncio
async def test_extension_skips_subordinate():
    ext = AuditLightAppend(agent=FakeAgent(number=1))
    loop = FakeLoopData(last_response="x " * 200, params_temporary={"log_item_response": FakeLogItem()})
    await ext.execute(loop_data=loop)
    assert loop.params_temporary["log_item_response"].updates == []


@pytest.mark.asyncio
async def test_extension_skips_without_log_item():
    ext = AuditLightAppend(agent=FakeAgent(number=0))
    loop = FakeLoopData(last_response="x " * 200, params_temporary={})
    await ext.execute(loop_data=loop)


@pytest.mark.asyncio
async def test_extension_skips_short_response():
    ext = AuditLightAppend(agent=FakeAgent(number=0))
    li = FakeLogItem("Bonjour")
    loop = FakeLoopData(last_response="Bonjour", params_temporary={"log_item_response": li})
    await ext.execute(loop_data=loop)
    assert li.content == "Bonjour"
    assert li.updates == []


@pytest.mark.asyncio
async def test_extension_appends_long_response():
    agent = FakeAgent(number=0)
    agent.set_data("_session_envelope", FakeEnvelope())
    ext = AuditLightAppend(agent=agent)
    long_body = " ".join([f"word{i}" for i in range(120)])
    li = FakeLogItem(long_body)
    loop = FakeLoopData(last_response=long_body, params_temporary={"log_item_response": li})
    await ext.execute(loop_data=loop)
    assert li.content.startswith(long_body)
    assert "Metadonnees d'audit Evidence (vue synthetique)" in li.content
    assert "KRV-TEST" in li.content
    assert "anthropic/claude-3" in li.content


@pytest.mark.asyncio
async def test_extension_fail_safe_no_mutation():
    agent = FakeAgent(number=0)
    agent.set_data("_session_envelope", FakeEnvelope())

    def boom(**kw):
        raise RuntimeError("forced")

    ext = AuditLightAppend(agent=agent)
    long_body = " ".join([f"w{i}" for i in range(120)])
    li = FakeLogItem(long_body)
    loop = FakeLoopData(last_response=long_body, params_temporary={"log_item_response": li})

    with patch.object(audit_light, "build_audit_light_markdown", side_effect=boom):
        await ext.execute(loop_data=loop)

    assert li.content == long_body
    assert li.updates == []
