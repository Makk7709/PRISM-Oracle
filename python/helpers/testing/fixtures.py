# -*- coding: utf-8 -*-
"""
Fixture management for deterministic LLM testing.

Provides:
- Fixture loading from JSON files
- Message normalization (remove instable fields)
- Stable key computation (hash-based, VERSION-AWARE)
- Record mode for generating fixture skeletons

VERSIONING:
Fixture keys include PROMPT_VERSION and TOOL_SCHEMA_VERSION to ensure
fixtures are invalidated when prompts or schemas change.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import warnings
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from .versions import PROMPT_VERSION, TOOL_SCHEMA_VERSION, get_version_suffix

# Default fixture directory
DEFAULT_FIXTURE_DIR = Path(__file__).parent.parent.parent.parent / "tests" / "fixtures" / "llm"

# Logger for fixture warnings
_logger = logging.getLogger(__name__)


@dataclass
class Fixture:
    """A single LLM fixture (request -> response mapping)."""
    provider: str
    model: str
    role: str  # chat | utility | browser | embedding
    messages_hash: str
    response: str
    reasoning: str = ""
    prompt_version: str = ""  # Version when fixture was created
    tool_schema_version: str = ""  # Schema version when fixture was created
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def key(self) -> str:
        """Unique fixture key (VERSIONED)."""
        version_suffix = get_version_suffix()
        return f"{self.provider}__{self.role}__{self.model}__{version_suffix}__{self.messages_hash}"
    
    @property
    def legacy_key(self) -> str:
        """Legacy key without versions (for migration)."""
        return f"{self.provider}__{self.role}__{self.model}__{self.messages_hash}"
    
    @property
    def filename(self) -> str:
        """Safe filename for this fixture (VERSIONED)."""
        safe_model = re.sub(r'[^\w\-.]', '_', self.model)
        version_suffix = get_version_suffix()
        return f"{self.provider}__{self.role}__{safe_model}__{version_suffix}__{self.messages_hash}.json"
    
    @property
    def is_versioned(self) -> bool:
        """Check if fixture has version info."""
        return bool(self.prompt_version and self.tool_schema_version)
    
    @property
    def is_current_version(self) -> bool:
        """Check if fixture matches current versions."""
        return (
            self.prompt_version == PROMPT_VERSION and
            self.tool_schema_version == TOOL_SCHEMA_VERSION
        )
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "provider": self.provider,
            "model": self.model,
            "role": self.role,
            "messages_hash": self.messages_hash,
            "prompt_version": self.prompt_version or PROMPT_VERSION,
            "tool_schema_version": self.tool_schema_version or TOOL_SCHEMA_VERSION,
            "response": self.response,
            "reasoning": self.reasoning,
            "metadata": self.metadata,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Fixture":
        return cls(
            provider=data["provider"],
            model=data["model"],
            role=data["role"],
            messages_hash=data["messages_hash"],
            prompt_version=data.get("prompt_version", ""),
            tool_schema_version=data.get("tool_schema_version", ""),
            response=data["response"],
            reasoning=data.get("reasoning", ""),
            metadata=data.get("metadata", {}),
        )


class FixtureManager:
    """
    Manages LLM fixtures for deterministic testing.
    
    VERSIONING:
    - Fixtures are keyed by provider, model, role, PROMPT_VERSION, TOOL_SCHEMA_VERSION, and messages hash
    - Legacy fixtures (without versions) are supported with a warning
    - Set STRICT_FIXTURES=1 to reject legacy fixtures
    
    Usage:
        manager = FixtureManager()
        fixture = manager.get_fixture(provider, model, role, messages)
        if fixture:
            return fixture.response
        else:
            raise MissingFixtureError(...)
    """
    
    def __init__(
        self,
        fixture_dir: Optional[Path] = None,
        record_mode: bool = False,
        strict_mode: Optional[bool] = None,
    ):
        self.fixture_dir = fixture_dir or DEFAULT_FIXTURE_DIR
        self.record_mode = record_mode or os.environ.get("A0_RECORD_FIXTURES") == "1"
        self.strict_mode = strict_mode if strict_mode is not None else os.environ.get("STRICT_FIXTURES") == "1"
        self._cache: Dict[str, Fixture] = {}
        self._legacy_cache: Dict[str, Fixture] = {}  # Legacy fixtures without versions
        self._load_fixtures()
    
    def _load_fixtures(self):
        """Load all fixtures from disk into cache."""
        if not self.fixture_dir.exists():
            self.fixture_dir.mkdir(parents=True, exist_ok=True)
            return
        
        for filepath in self.fixture_dir.glob("*.json"):
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    data = json.load(f)
                fixture = Fixture.from_dict(data)
                
                # Cache by versioned key
                self._cache[fixture.key] = fixture
                
                # Also cache by legacy key for migration support
                if not fixture.is_versioned:
                    self._legacy_cache[fixture.legacy_key] = fixture
                    
            except Exception as e:
                _logger.warning(f"Failed to load fixture {filepath}: {e}")
    
    def get_fixture(
        self,
        provider: str,
        model: str,
        role: str,
        messages: List[Dict[str, Any]],
    ) -> Optional[Fixture]:
        """
        Get fixture for the given request.
        
        Lookup order:
        1. Versioned key (current PROMPT_VERSION + TOOL_SCHEMA_VERSION)
        2. Legacy key (no versions) - only if not in strict mode
        
        Returns None if not found (caller should raise MissingFixtureError).
        """
        messages_hash = compute_fixture_key(messages)
        version_suffix = get_version_suffix()
        
        # Try versioned key first
        versioned_key = f"{provider}__{role}__{model}__{version_suffix}__{messages_hash}"
        fixture = self._cache.get(versioned_key)
        if fixture:
            return fixture
        
        # Try legacy key if not strict
        legacy_key = f"{provider}__{role}__{model}__{messages_hash}"
        legacy_fixture = self._legacy_cache.get(legacy_key)
        
        if legacy_fixture:
            if self.strict_mode:
                _logger.warning(
                    f"Legacy fixture found but STRICT_FIXTURES=1: {legacy_key}\n"
                    f"Fixture needs to be regenerated with current versions."
                )
                return None
            else:
                _logger.warning(
                    f"Using legacy fixture (no version info): {legacy_key}\n"
                    f"Consider regenerating with A0_RECORD_FIXTURES=1"
                )
                return legacy_fixture
        
        return None
    
    def record_skeleton(
        self,
        provider: str,
        model: str,
        role: str,
        messages: List[Dict[str, Any]],
    ) -> Path:
        """
        Record a fixture skeleton (empty response) for later filling.
        
        Only works if A0_RECORD_FIXTURES=1.
        Returns the path to the skeleton file.
        
        The skeleton includes current PROMPT_VERSION and TOOL_SCHEMA_VERSION.
        """
        if not self.record_mode:
            raise RuntimeError("Record mode not enabled. Set A0_RECORD_FIXTURES=1")
        
        from datetime import datetime, timezone
        
        messages_hash = compute_fixture_key(messages)
        fixture = Fixture(
            provider=provider,
            model=model,
            role=role,
            messages_hash=messages_hash,
            prompt_version=PROMPT_VERSION,
            tool_schema_version=TOOL_SCHEMA_VERSION,
            response="TODO: Fill in expected response",
            reasoning="",
            metadata={
                "normalized_messages": normalize_messages(messages),
                "recorded_at": datetime.now(timezone.utc).isoformat(),
                "versions": {
                    "prompt": PROMPT_VERSION,
                    "tool_schema": TOOL_SCHEMA_VERSION,
                },
            },
        )
        
        filepath = self.fixture_dir / fixture.filename
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(fixture.to_dict(), f, indent=2, ensure_ascii=False)
        
        self._cache[fixture.key] = fixture
        return filepath
    
    def add_fixture(self, fixture: Fixture):
        """Add a fixture to the cache (for programmatic use)."""
        self._cache[fixture.key] = fixture


def normalize_messages(messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Normalize messages for stable hashing.
    
    Removes:
    - Timestamps
    - Debug IDs
    - UUIDs
    - Whitespace variations
    """
    normalized = []
    for msg in messages:
        norm_msg = {}
        for key, value in msg.items():
            # Skip instable fields
            if key in ("timestamp", "debug_id", "id", "created_at", "updated_at"):
                continue
            # Skip fields that look like UUIDs
            if isinstance(value, str) and re.match(r'^[a-f0-9-]{36}$', value):
                continue
            # Normalize whitespace in content
            if key == "content" and isinstance(value, str):
                value = " ".join(value.split())
            norm_msg[key] = value
        normalized.append(norm_msg)
    return normalized


def compute_fixture_key(messages: List[Dict[str, Any]]) -> str:
    """
    Compute a stable hash key for messages.
    
    Returns first 12 chars of SHA256.
    """
    normalized = normalize_messages(messages)
    canonical = json.dumps(normalized, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(canonical.encode()).hexdigest()[:12]
