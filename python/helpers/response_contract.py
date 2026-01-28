from __future__ import annotations

from typing import Any, Dict, Optional
from pydantic import BaseModel, Field, model_validator, ValidationError


class ResponseEnvelopeSchema(BaseModel):
    """Canonical response envelope for user-visible output."""
    text: str = Field(..., min_length=1)
    thoughts: Optional[str] = None
    debug: Optional[Dict[str, Any]] = None
    trace: Optional[list[Any]] = None
    router_decision: Optional[Dict[str, Any]] = None

    @model_validator(mode="after")
    def validate_text(self) -> "ResponseEnvelopeSchema":
        if not self.text or not self.text.strip():
            raise ValueError("ResponseEnvelope.text must be non-empty")
        self.text = self.text.strip()
        return self


def validate_response_envelope(
    data: Dict[str, Any],
    fallback_text: Optional[str] = None,
) -> ResponseEnvelopeSchema:
    """
    Validate response envelope. Optionally apply a fallback text.
    """
    try:
        return ResponseEnvelopeSchema(**data)
    except ValidationError:
        if fallback_text is None:
            raise
        return ResponseEnvelopeSchema(text=fallback_text)
