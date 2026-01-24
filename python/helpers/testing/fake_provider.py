# -*- coding: utf-8 -*-
"""
Fake LLM Provider for deterministic offline testing.

Provides FakeLiteLLMChatWrapper that returns responses from fixtures
instead of calling real LLM APIs.

Usage:
    # In tests, install the fake provider
    install_fake_provider()
    
    # Now all get_chat_model() etc. will return fakes
    model = get_chat_model("openai", "gpt-4", ...)
    response = await model.unified_call(...)  # Returns fixture data
    
    # Restore real provider
    uninstall_fake_provider()
"""

from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass
from typing import Any, AsyncIterator, Awaitable, Callable, Dict, Iterator, List, Optional, Tuple

from langchain_core.callbacks.manager import (
    AsyncCallbackManagerForLLMRun,
    CallbackManagerForLLMRun,
)
from langchain_core.language_models.chat_models import SimpleChatModel
from langchain_core.messages import AIMessageChunk, BaseMessage
from langchain_core.outputs.chat_generation import ChatGenerationChunk
from pydantic import ConfigDict

from .fixtures import FixtureManager, compute_fixture_key, normalize_messages


class MissingFixtureError(Exception):
    """
    Raised when a fixture is not found for an LLM request.
    
    Contains helpful info for generating the fixture.
    """
    
    def __init__(
        self,
        provider: str,
        model: str,
        role: str,
        messages: List[Dict[str, Any]],
        fixture_manager: FixtureManager,
    ):
        self.provider = provider
        self.model = model
        self.role = role
        self.messages = messages
        self.fixture_manager = fixture_manager
        
        messages_hash = compute_fixture_key(messages)
        self.expected_filename = f"{provider}__{role}__{model}__{messages_hash}.json"
        
        super().__init__(self._build_message())
    
    def _build_message(self) -> str:
        normalized = normalize_messages(self.messages)
        return (
            f"\n"
            f"╔══════════════════════════════════════════════════════════════════╗\n"
            f"║                    MISSING FIXTURE ERROR                         ║\n"
            f"╠══════════════════════════════════════════════════════════════════╣\n"
            f"║ Provider: {self.provider:<54} ║\n"
            f"║ Model:    {self.model:<54} ║\n"
            f"║ Role:     {self.role:<54} ║\n"
            f"╠══════════════════════════════════════════════════════════════════╣\n"
            f"║ Expected fixture file:                                           ║\n"
            f"║   tests/fixtures/llm/{self.expected_filename:<44} ║\n"
            f"╠══════════════════════════════════════════════════════════════════╣\n"
            f"║ To generate a skeleton, run:                                     ║\n"
            f"║   A0_RECORD_FIXTURES=1 pytest <your_test>                        ║\n"
            f"╠══════════════════════════════════════════════════════════════════╣\n"
            f"║ Normalized messages (for debugging):                             ║\n"
            f"║ {json.dumps(normalized, indent=2)[:500]:<64} ║\n"
            f"╚══════════════════════════════════════════════════════════════════╝\n"
        )


# Global state for provider override
_original_get_chat_model = None
_original_get_browser_model = None
_original_get_embedding_model = None
_fake_provider_installed = False
_fixture_manager: Optional[FixtureManager] = None


class FakeLiteLLMChatWrapper(SimpleChatModel):
    """
    Fake LLM wrapper that returns responses from fixtures.
    
    Compatible with the real LiteLLMChatWrapper interface.
    """
    
    model_name: str
    provider: str
    role: str
    kwargs: dict = {}
    
    model_config = ConfigDict(
        arbitrary_types_allowed=True,
        extra="allow",
        validate_assignment=False,
    )
    
    def __init__(
        self,
        model: str,
        provider: str,
        role: str = "chat",
        model_config: Optional[Any] = None,
        fixture_manager: Optional[FixtureManager] = None,
        **kwargs: Any,
    ):
        model_value = f"{provider}/{model}"
        super().__init__(model_name=model_value, provider=provider, role=role, kwargs=kwargs)
        self.korev_model_conf = model_config
        self._fixture_manager = fixture_manager or _fixture_manager or FixtureManager()
        self._role = role
    
    @property
    def _llm_type(self) -> str:
        return "fake-litellm-chat"
    
    def _convert_messages(self, messages: List[BaseMessage]) -> List[dict]:
        """Convert LangChain messages to dict format."""
        role_mapping = {
            "human": "user",
            "ai": "assistant",
            "system": "system",
            "tool": "tool",
        }
        result = []
        for m in messages:
            role = role_mapping.get(m.type, m.type)
            result.append({"role": role, "content": m.content})
        return result
    
    def _get_fixture_response(self, messages: List[dict]) -> Tuple[str, str]:
        """
        Get response from fixture or raise MissingFixtureError.
        
        Returns (response, reasoning).
        """
        # Extract provider name without prefix
        provider = self.provider.lower()
        model = self.model_name.split("/")[-1] if "/" in self.model_name else self.model_name
        
        fixture = self._fixture_manager.get_fixture(
            provider=provider,
            model=model,
            role=self._role,
            messages=messages,
        )
        
        if fixture:
            return fixture.response, fixture.reasoning
        
        # Record mode: create skeleton
        if self._fixture_manager.record_mode:
            self._fixture_manager.record_skeleton(provider, model, self._role, messages)
            return "FIXTURE_SKELETON_CREATED", ""
        
        # No fixture found: raise error
        raise MissingFixtureError(
            provider=provider,
            model=model,
            role=self._role,
            messages=messages,
            fixture_manager=self._fixture_manager,
        )
    
    def _call(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> str:
        msgs = self._convert_messages(messages)
        response, _ = self._get_fixture_response(msgs)
        return response
    
    def _stream(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> Iterator[ChatGenerationChunk]:
        msgs = self._convert_messages(messages)
        response, _ = self._get_fixture_response(msgs)
        
        # Simulate streaming by yielding chunks
        chunk_size = 10
        for i in range(0, len(response), chunk_size):
            chunk = response[i:i + chunk_size]
            yield ChatGenerationChunk(message=AIMessageChunk(content=chunk))
    
    async def _astream(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[AsyncCallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> AsyncIterator[ChatGenerationChunk]:
        msgs = self._convert_messages(messages)
        response, _ = self._get_fixture_response(msgs)
        
        # Simulate streaming by yielding chunks
        chunk_size = 10
        for i in range(0, len(response), chunk_size):
            chunk = response[i:i + chunk_size]
            yield ChatGenerationChunk(message=AIMessageChunk(content=chunk))
            await asyncio.sleep(0)  # Yield control
    
    async def unified_call(
        self,
        system_message: str = "",
        user_message: str = "",
        messages: Optional[List[BaseMessage]] = None,
        response_callback: Optional[Callable[[str, str], Awaitable[None]]] = None,
        reasoning_callback: Optional[Callable[[str, str], Awaitable[None]]] = None,
        tokens_callback: Optional[Callable[[str, int], Awaitable[None]]] = None,
        rate_limiter_callback: Optional[Callable[[str, str, int, int], Awaitable[bool]]] = None,
        **kwargs: Any,
    ) -> Tuple[str, str]:
        """
        Unified call interface compatible with real LiteLLMChatWrapper.
        
        Returns (response, reasoning).
        """
        from langchain_core.messages import HumanMessage, SystemMessage
        
        if not messages:
            messages = []
        if system_message:
            messages.insert(0, SystemMessage(content=system_message))
        if user_message:
            messages.append(HumanMessage(content=user_message))
        
        msgs = self._convert_messages(messages)
        response, reasoning = self._get_fixture_response(msgs)
        
        # Call callbacks if provided (simulate streaming)
        if response_callback:
            await response_callback(response, response)
        if reasoning_callback and reasoning:
            await reasoning_callback(reasoning, reasoning)
        
        return response, reasoning


class FakeLiteLLMProvider:
    """
    Factory for fake LLM wrappers.
    
    Use install_fake_provider() instead of instantiating directly.
    """
    
    def __init__(self, fixture_manager: Optional[FixtureManager] = None):
        self.fixture_manager = fixture_manager or FixtureManager()
    
    def get_chat_model(
        self,
        provider: str,
        name: str,
        model_config: Optional[Any] = None,
        **kwargs: Any,
    ) -> FakeLiteLLMChatWrapper:
        return FakeLiteLLMChatWrapper(
            model=name,
            provider=provider.lower(),
            role="chat",
            model_config=model_config,
            fixture_manager=self.fixture_manager,
            **kwargs,
        )
    
    def get_browser_model(
        self,
        provider: str,
        name: str,
        model_config: Optional[Any] = None,
        **kwargs: Any,
    ) -> FakeLiteLLMChatWrapper:
        return FakeLiteLLMChatWrapper(
            model=name,
            provider=provider.lower(),
            role="browser",
            model_config=model_config,
            fixture_manager=self.fixture_manager,
            **kwargs,
        )
    
    def get_embedding_model(
        self,
        provider: str,
        name: str,
        model_config: Optional[Any] = None,
        **kwargs: Any,
    ):
        # Return a mock embedding model
        return FakeEmbeddingWrapper(
            provider=provider.lower(),
            model=name,
            fixture_manager=self.fixture_manager,
        )


class FakeEmbeddingWrapper:
    """Fake embedding model that returns deterministic embeddings."""
    
    def __init__(self, provider: str, model: str, fixture_manager: Optional[FixtureManager] = None):
        self.provider = provider
        self.model_name = f"{provider}/{model}"
        self._fixture_manager = fixture_manager
    
    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """Return deterministic embeddings based on text hash."""
        return [self._hash_to_embedding(text) for text in texts]
    
    def embed_query(self, text: str) -> List[float]:
        """Return deterministic embedding based on text hash."""
        return self._hash_to_embedding(text)
    
    def _hash_to_embedding(self, text: str, dim: int = 384) -> List[float]:
        """Convert text to deterministic embedding vector."""
        import hashlib
        h = hashlib.sha256(text.encode()).hexdigest()
        # Generate deterministic floats from hash
        embedding = []
        for i in range(0, min(len(h), dim * 2), 2):
            val = int(h[i:i+2], 16) / 255.0 - 0.5
            embedding.append(val)
        # Pad if necessary
        while len(embedding) < dim:
            embedding.append(0.0)
        return embedding[:dim]


def install_fake_provider(fixture_manager: Optional[FixtureManager] = None):
    """
    Install fake provider to intercept all LLM calls.
    
    After calling this, get_chat_model(), get_browser_model(), etc.
    will return fake wrappers that use fixtures.
    """
    global _original_get_chat_model, _original_get_browser_model
    global _original_get_embedding_model, _fake_provider_installed, _fixture_manager
    
    if _fake_provider_installed:
        return  # Already installed
    
    import models
    
    # Save originals
    _original_get_chat_model = models.get_chat_model
    _original_get_browser_model = models.get_browser_model
    _original_get_embedding_model = models.get_embedding_model
    
    # Create fake provider
    _fixture_manager = fixture_manager or FixtureManager()
    fake = FakeLiteLLMProvider(_fixture_manager)
    
    # Replace
    models.get_chat_model = fake.get_chat_model
    models.get_browser_model = fake.get_browser_model
    models.get_embedding_model = fake.get_embedding_model
    
    _fake_provider_installed = True


def uninstall_fake_provider():
    """Restore real LLM provider."""
    global _original_get_chat_model, _original_get_browser_model
    global _original_get_embedding_model, _fake_provider_installed, _fixture_manager
    
    if not _fake_provider_installed:
        return  # Not installed
    
    import models
    
    # Restore originals
    if _original_get_chat_model:
        models.get_chat_model = _original_get_chat_model
    if _original_get_browser_model:
        models.get_browser_model = _original_get_browser_model
    if _original_get_embedding_model:
        models.get_embedding_model = _original_get_embedding_model
    
    _fake_provider_installed = False
    _fixture_manager = None


def is_fake_provider_installed() -> bool:
    """Check if fake provider is currently installed."""
    return _fake_provider_installed
