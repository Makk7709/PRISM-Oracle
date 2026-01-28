import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


def test_messages_js_filters_internal_kvps():
    messages_js = Path(__file__).parent.parent / "webui" / "js" / "messages.js"
    contents = messages_js.read_text(encoding="utf-8")
    assert "INTERNAL_KVPS" in contents
    for key in [
        "thoughts",
        "debug",
        "trace",
        "router_decision",
        "tool_calls",
        "internal",
        "reasoning",
    ]:
        assert f"\"{key}\"" in contents
    assert "sanitizeKvps(kvps)" in contents


def test_response_fallback_text_present():
    messages_js = Path(__file__).parent.parent / "webui" / "js" / "messages.js"
    contents = messages_js.read_text(encoding="utf-8")
    assert "Réponse indisponible." in contents
