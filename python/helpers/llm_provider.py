"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                     LLM PROVIDER ADAPTER FOR CONSENSUS                       ║
║                                                                              ║
║  Provides a stable interface for consensus arbiters to call LLM models.      ║
║                                                                              ║
║  DESIGN PRINCIPLES:                                                          ║
║  1. Import-stable: Works regardless of current working directory             ║
║  2. Fail-fast: Validates provider availability at boot time in production    ║
║  3. Explicit errors: Clear messages when configuration is missing            ║
║                                                                              ║
║  Version: 1.0.0                                                              ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import logging
import os
from dataclasses import dataclass
from typing import Any, Optional

logger = logging.getLogger("llm_provider")

# ═══════════════════════════════════════════════════════════════════════════════
# ENVIRONMENT DETECTION
# ═══════════════════════════════════════════════════════════════════════════════

def get_environment() -> str:
    """Get current environment: production, development, or test."""
    return os.environ.get("EVIDENCE_ENV", "production").lower()


def is_production() -> bool:
    """Check if running in production environment."""
    return get_environment() == "production"


def is_simulation_enabled() -> bool:
    """Check if simulation mode is explicitly enabled."""
    return os.environ.get("CONSENSUS_SIMULATION", "false").lower() == "true"


# ═══════════════════════════════════════════════════════════════════════════════
# PROVIDER IMPORT (FAIL-FAST)
# ═══════════════════════════════════════════════════════════════════════════════

# Attempt to import the models module at module load time
# This ensures we fail fast at boot, not during consensus voting
_models_module = None
_import_error: Optional[str] = None

try:
    import models as _models_module
    logger.info("LLM provider layer loaded successfully")
except ImportError as e:
    _import_error = str(e)
    logger.error(f"Failed to import models module: {e}")


def _validate_provider_available() -> None:
    """
    Validate that LLM provider layer is available.
    
    Raises:
        RuntimeError: In production if provider is not available
                      and simulation is not explicitly enabled.
    """
    if _models_module is not None:
        return  # Provider available, all good
    
    env = get_environment()
    simulation = is_simulation_enabled()
    
    error_msg = (
        f"LLM provider layer unavailable: {_import_error}. "
        f"Consensus arbiters cannot operate without LLM access. "
        f"Environment: {env}, Simulation: {simulation}"
    )
    
    if is_production():
        # Production: always fail-fast
        raise RuntimeError(
            f"FATAL: {error_msg} — "
            "In production, consensus requires real LLM providers. "
            "Check that 'models.py' is importable and API keys are configured."
        )
    
    if not simulation:
        # Dev/test without explicit simulation: also fail-fast to avoid ambiguity
        raise RuntimeError(
            f"FATAL: {error_msg} — "
            "In development/test, either fix the import issue or "
            "set CONSENSUS_SIMULATION=true explicitly to use mock voting."
        )
    
    # Dev/test with simulation enabled: allow degraded mode
    logger.warning(
        f"⚠️ LLM provider unavailable but SIMULATION mode is ON. "
        f"Consensus will use mock voting (NOT suitable for real validation)."
    )


# ═══════════════════════════════════════════════════════════════════════════════
# PROVIDER WRAPPER
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class ProviderWrapper:
    """
    Wrapper around LiteLLM chat model for consensus arbiters.
    
    Provides an async `generate()` method compatible with consensus_arbiter.py.
    """
    provider: str
    model: str
    _chat_model: Any = None
    
    def __post_init__(self):
        """Initialize the underlying chat model."""
        if _models_module is None:
            raise RuntimeError("Cannot create ProviderWrapper: models module not available")
        
        self._chat_model = _models_module.get_chat_model(
            provider=self.provider,
            name=self.model,
        )
    
    async def generate(
        self,
        prompt: str,
        temperature: float = 0.0,
        max_tokens: int = 500,
    ) -> str:
        """
        Generate a response from the LLM.
        
        Args:
            prompt: The prompt text to send
            temperature: Sampling temperature (0.0 = deterministic)
            max_tokens: Maximum tokens in response
            
        Returns:
            The generated response text
        """
        response, _ = await self._chat_model.unified_call(
            user_message=prompt,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return response


# ═══════════════════════════════════════════════════════════════════════════════
# PUBLIC API
# ═══════════════════════════════════════════════════════════════════════════════

def get_provider(provider: str, model: str) -> ProviderWrapper:
    """
    Get an LLM provider wrapper for consensus arbitration.
    
    Args:
        provider: Provider name (e.g., "openai", "anthropic", "google")
        model: Model name (e.g., "gpt-4o", "claude-3-5-sonnet")
        
    Returns:
        ProviderWrapper instance with async generate() method
        
    Raises:
        RuntimeError: If provider layer is unavailable
    """
    _validate_provider_available()
    
    return ProviderWrapper(provider=provider, model=model)


def validate_boot() -> dict:
    """
    Validate provider availability at boot time.
    
    Should be called during application startup to fail-fast if
    consensus cannot operate.
    
    Returns:
        Dict with validation status and details
        
    Raises:
        RuntimeError: In production if providers are unavailable
    """
    env = get_environment()
    simulation = is_simulation_enabled()
    
    result = {
        "environment": env,
        "simulation_enabled": simulation,
        "models_module_loaded": _models_module is not None,
        "import_error": _import_error,
    }
    
    try:
        _validate_provider_available()
        result["status"] = "ok"
        result["message"] = "LLM provider layer available for consensus"
    except RuntimeError as e:
        result["status"] = "error"
        result["message"] = str(e)
        raise
    
    logger.info(f"Boot validation: {result}")
    return result


def is_provider_available() -> bool:
    """
    Check if LLM provider is available (for conditional logic).
    
    Returns:
        True if provider is available, False otherwise
    """
    return _models_module is not None


# ═══════════════════════════════════════════════════════════════════════════════
# BOOT VALIDATION (executed at import time in production)
# ═══════════════════════════════════════════════════════════════════════════════

# Only validate at boot if we're being imported (not during test collection)
# and we're in production mode
if is_production() and not os.environ.get("PYTEST_CURRENT_TEST"):
    try:
        validate_boot()
    except RuntimeError:
        # Re-raise to fail application startup
        raise
