import sys
from pathlib import Path
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from python.helpers.response_contract import validate_response_envelope


def test_response_envelope_requires_text():
    with pytest.raises(Exception):
        validate_response_envelope({"text": ""})


def test_response_envelope_fallback_text():
    envelope = validate_response_envelope(
        {"text": ""},
        fallback_text="Réponse indisponible (erreur de format).",
    )
    assert envelope.text.startswith("Réponse indisponible")
