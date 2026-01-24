# -*- coding: utf-8 -*-
"""
Fixture management for deterministic LLM testing.

Provides:
- Fixture loading from JSON files
- Message normalization (remove instable fields)
- Stable key computation (hash-based)
- Record mode for generating fixture skeletons
"""

from __future__ import annotations

import hashlib
import json
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

# Default fixture directory
DEFAULT_FIXTURE_DIR = Path(__file__).parent.parent.parent.parent / "tests" / "fixtures" / "llm"


@dataclass
class Fixture:
    """A single LLM fixture (request -> response mapping)."""
    provider: str
    model: str
    role: str  # chat | utility | browser | embedding
    messages_hash: str
    response: str
    reasoning: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def key(self) -> str:
        """Unique fixture key."""
        return f"{self.provider}__{self.role}__{self.model}__{self.messages_hash}"
    
    @property
    def filename(self) -> str:
        """Safe filename for this fixture."""
        safe_model = re.sub(r'[^\w\-.]', '_', self.model)
        return f"{self.provider}__{self.role}__{safe_model}__{self.messages_hash}.json"
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "provider": self.provider,
            "model": self.model,
            "role": self.role,
            "messages_hash": self.messages_hash,
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
            response=data["response"],
            reasoning=data.get("reasoning", ""),
            metadata=data.get("metadata", {}),
        )


class FixtureManager:
    """
    Manages LLM fixtures for deterministic testing.
    
    Usage:
        manager = FixtureManager()
        fixture = manager.get_fixture(provider, model, role, messages)
        if fixture:
            return fixture.response
        else:
            raise MissingFixtureError(...)
    """
    
    def __init__(self, fixture_dir: Optional[Path] = None, record_mode: bool = False):
        self.fixture_dir = fixture_dir or DEFAULT_FIXTURE_DIR
        self.record_mode = record_mode or os.environ.get("A0_RECORD_FIXTURES") == "1"
        self._cache: Dict[str, Fixture] = {}
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
                self._cache[fixture.key] = fixture
            except Exception as e:
                # Ignore malformed fixtures
                pass
    
    def get_fixture(
        self,
        provider: str,
        model: str,
        role: str,
        messages: List[Dict[str, Any]],
    ) -> Optional[Fixture]:
        """
        Get fixture for the given request.
        
        Returns None if not found (caller should raise MissingFixtureError).
        """
        messages_hash = compute_fixture_key(messages)
        key = f"{provider}__{role}__{model}__{messages_hash}"
        return self._cache.get(key)
    
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
        """
        if not self.record_mode:
            raise RuntimeError("Record mode not enabled. Set A0_RECORD_FIXTURES=1")
        
        messages_hash = compute_fixture_key(messages)
        fixture = Fixture(
            provider=provider,
            model=model,
            role=role,
            messages_hash=messages_hash,
            response="TODO: Fill in expected response",
            reasoning="",
            metadata={
                "normalized_messages": normalize_messages(messages),
                "recorded_at": "TODO",
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
