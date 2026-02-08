"""
╔══════════════════════════════════════════════════════════════════════════════╗
║              CONSENSUS ARBITER — Real LLM Voting System                      ║
║                                                                              ║
║  Système d'arbitrage réel via LLMs multiples pour le consensus PRISM.        ║
║                                                                              ║
║  RÈGLES CRITIQUES:                                                           ║
║  1. CONSENSUS_SIMULATION=false en production (hard fail si true)             ║
║  2. Chaque arbitre DOIT retourner un vote structuré                          ║
║  3. Timeout = unavailable (pas REJECT par défaut côté arbitre)               ║
║  4. Fail-closed au niveau consensus global                                   ║
║                                                                              ║
║  Les votes simulés sont INTERDITS en production.                             ║
║                                                                              ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import asyncio
import hashlib
import json
import logging
import os
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple

from python.helpers.consensus_manager import (
    ConsensusManager,
    ConsensusStatus,
    DecisionType,
    VoteType,
    VoteCount,
    Vote,
    DecisionProposal,
    ConsensusResult,
    build_vote_prompt,
    parse_llm_vote_response,
    generate_decision_hash,
)

# ═══════════════════════════════════════════════════════════════════════════════
# LLM PROVIDER IMPORT (module-level for stability)
# ═══════════════════════════════════════════════════════════════════════════════
# Import at module level to:
# 1. Fail-fast at boot if provider unavailable in production
# 2. Avoid cwd-dependent import issues
# 3. Make import errors explicit and traceable

from python.helpers import llm_provider as _llm_provider
from python.helpers.print_style import PrintStyle

# Boot validation: ensures we fail early if providers are misconfigured
_LLM_PROVIDER_AVAILABLE = _llm_provider.is_provider_available()

logger = logging.getLogger("consensus_arbiter")

# Log provider status at module load
if _LLM_PROVIDER_AVAILABLE:
    logger.info("✅ LLM provider layer available for consensus arbiters")
else:
    logger.warning(
        "⚠️ LLM provider layer NOT available. "
        "Consensus arbiters will fail unless CONSENSUS_SIMULATION=true"
    )


# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════

class SimulationError(Exception):
    """Erreur levée quand simulation est activée en production."""
    pass


class ArbiterUnavailableError(Exception):
    """Erreur levée quand aucun arbitre n'est disponible."""
    pass


@dataclass
class ArbiterConfig:
    """Configuration d'un arbitre LLM."""
    provider: str          # e.g., "openai", "anthropic", "google"
    model: str             # e.g., "gpt-4", "claude-3-opus", "gemini-pro"
    timeout_ms: int = 5000
    temperature: float = 0.0  # Déterministe
    max_tokens: int = 500
    priority: int = 0      # 0 = plus haute priorité


@dataclass 
class ConsensusConfig:
    """Configuration du système de consensus."""
    # Arbitres
    arbiters: List[ArbiterConfig] = field(default_factory=list)
    local_arbiters: List[ArbiterConfig] = field(default_factory=list)
    
    # Timeouts
    global_timeout_ms: int = 10000
    per_arbiter_timeout_ms: int = 3000
    
    # Simulation
    simulation_enabled: bool = False  # FALSE par défaut
    
    # Quorum
    total_providers: int = 3
    quorum_ratio: float = 2/3
    
    # Mode
    offline_mode: bool = False
    fail_on_no_arbiters: bool = True


def _parse_arbiter_string(arbiter_str: str, priority: int = 0, timeout_ms: int = 5000) -> ArbiterConfig:
    """
    Parse une chaîne arbiter du format UI en ArbiterConfig.
    
    Format UI: "openrouter/anthropic/claude-3.5-sonnet"
    → provider="openrouter", model="anthropic/claude-3.5-sonnet"
    
    Format: "ollama/mistral-large" 
    → provider="ollama", model="mistral-large"
    """
    parts = arbiter_str.split("/", 1)
    if len(parts) == 2:
        provider = parts[0]
        model = parts[1]
    else:
        # Fallback: assume openrouter
        provider = "openrouter"
        model = arbiter_str
    
    return ArbiterConfig(
        provider=provider,
        model=model,
        priority=priority,
        timeout_ms=timeout_ms,
    )


def load_consensus_config() -> ConsensusConfig:
    """
    Charge la configuration depuis les settings UI ou l'environnement.
    
    PRIORITÉ:
    1. Settings UI (PRISM Consensus panel)
    2. Variables d'environnement (fallback)
    3. Valeurs par défaut
    
    Variables d'environnement (override):
    - CONSENSUS_SIMULATION: "true"/"false" (force simulation mode)
    - EVIDENCE_ENV: "production"/"development"
    """
    env = os.environ.get("EVIDENCE_ENV", "production").lower()
    is_production = env == "production"
    
    # ═══════════════════════════════════════════════════════════════════════════
    # LOAD FROM SETTINGS UI (Priority source)
    # ═══════════════════════════════════════════════════════════════════════════
    arbiters = []
    timeout_ms = 10000
    quorum_ratio = 0.67
    consensus_enabled = True
    
    try:
        from python.helpers import settings as _settings
        ui_settings = _settings.get_settings()
        
        # Check if consensus is enabled in UI
        consensus_enabled = ui_settings.get("consensus_enabled", True)
        
        # Load timeout and quorum from UI
        timeout_ms = int(ui_settings.get("consensus_timeout_ms", 10000))
        quorum_ratio = float(ui_settings.get("consensus_quorum_ratio", 0.67))
        
        # Load arbiters from UI (format: "openrouter/provider/model")
        arbiter_1_str = ui_settings.get("consensus_arbiter_1", "")
        arbiter_2_str = ui_settings.get("consensus_arbiter_2", "")
        arbiter_3_str = ui_settings.get("consensus_arbiter_3", "")
        
        # Each arbiter gets the full timeout (they run in parallel)
        # 10s is usually enough for OpenRouter but can be slow
        per_arbiter_timeout = max(timeout_ms, 15000)  # Minimum 15 seconds
        
        if arbiter_1_str:
            arbiters.append(_parse_arbiter_string(arbiter_1_str, priority=0, timeout_ms=per_arbiter_timeout))
        if arbiter_2_str:
            arbiters.append(_parse_arbiter_string(arbiter_2_str, priority=1, timeout_ms=per_arbiter_timeout))
        if arbiter_3_str:
            arbiters.append(_parse_arbiter_string(arbiter_3_str, priority=2, timeout_ms=per_arbiter_timeout))
        
        if arbiters:
            logger.info(
                f"Loaded consensus config from UI: "
                f"{len(arbiters)} arbiters, timeout={timeout_ms}ms, quorum={quorum_ratio}"
            )
            for a in arbiters:
                logger.info(f"  Arbiter: {a.provider}/{a.model}")
        
    except Exception as e:
        logger.warning(f"Could not load UI settings, using env/defaults: {e}")
    
    # ═══════════════════════════════════════════════════════════════════════════
    # SIMULATION MODE DETECTION
    # ═══════════════════════════════════════════════════════════════════════════
    explicit_simulation = os.environ.get("CONSENSUS_SIMULATION")
    if explicit_simulation is not None:
        simulation_enabled = explicit_simulation.lower() in ("true", "1")
    else:
        # Default: simulation ON in development (safe), OFF in production (real calls)
        simulation_enabled = not is_production
    
    if is_production and simulation_enabled:
        error_msg = (
            "CRITICAL: CONSENSUS_SIMULATION=true is FORBIDDEN in production. "
            "This is a hard fail to prevent fake consensus. "
            "Set EVIDENCE_ENV=development or remove CONSENSUS_SIMULATION."
        )
        logger.critical(error_msg)
        raise SimulationError(error_msg)
    
    # ═══════════════════════════════════════════════════════════════════════════
    # FALLBACK: Environment variables or defaults
    # ═══════════════════════════════════════════════════════════════════════════
    # Explicit env override (wins over UI if provided)
    arbiters_json = os.environ.get("CONSENSUS_ARBITERS")
    if arbiters_json:
        try:
            arbiters_raw = json.loads(arbiters_json)
            arbiters = [
                ArbiterConfig(
                    provider=a.get("provider", "unknown"),
                    model=a.get("model", "unknown"),
                    timeout_ms=a.get("timeout_ms", 5000),
                    priority=a.get("priority", 0),
                )
                for a in arbiters_raw
            ]
        except json.JSONDecodeError:
            logger.warning("CONSENSUS_ARBITERS invalid JSON; ignoring override")
    
    if not arbiters:
        # Try environment variable fallback
        arbiters_json = os.environ.get("CONSENSUS_ARBITERS", "[]")
        try:
            arbiters_raw = json.loads(arbiters_json)
            arbiters = [
                ArbiterConfig(
                    provider=a.get("provider", "unknown"),
                    model=a.get("model", "unknown"),
                    timeout_ms=a.get("timeout_ms", 5000),
                    priority=a.get("priority", 0),
                )
                for a in arbiters_raw
            ]
        except json.JSONDecodeError:
            pass
    
    # Ultimate fallback: OpenRouter defaults
    if not arbiters:
        logger.warning("No arbiters configured, using OpenRouter defaults")
        arbiters = [
            ArbiterConfig(provider="openrouter", model="anthropic/claude-3.5-sonnet", priority=0),
            ArbiterConfig(provider="openrouter", model="openai/gpt-4o", priority=1),
            ArbiterConfig(provider="openrouter", model="google/gemini-pro-1.5", priority=2),
        ]
    
    # Arbitres locaux (pour mode offline)
    local_arbiters_json = os.environ.get("CONSENSUS_LOCAL_ARBITERS", "[]")
    try:
        local_arbiters_raw = json.loads(local_arbiters_json)
        local_arbiters = [
            ArbiterConfig(
                provider=a.get("provider", "local"),
                model=a.get("model", "unknown"),
                timeout_ms=a.get("timeout_ms", 5000),
            )
            for a in local_arbiters_raw
        ]
    except json.JSONDecodeError:
        local_arbiters = []
    
    return ConsensusConfig(
        arbiters=arbiters,
        local_arbiters=local_arbiters,
        global_timeout_ms=timeout_ms,
        per_arbiter_timeout_ms=timeout_ms // 2,
        simulation_enabled=simulation_enabled,
        total_providers=len(arbiters) if arbiters else 3,
        quorum_ratio=quorum_ratio,
        offline_mode=os.environ.get("OFFLINE_MODE", "false").lower() == "true",
        fail_on_no_arbiters=True,
    )


# ═══════════════════════════════════════════════════════════════════════════════
# ARBITER RESPONSE
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class ArbiterVote:
    """Vote d'un arbitre avec métadonnées complètes."""
    arbiter_id: str
    provider: str
    model: str
    
    # Vote
    vote_type: Optional[VoteType]
    approve: bool
    reasoning: str
    confidence: float  # 0.0-1.0
    risks_identified: List[str] = field(default_factory=list)
    available: bool = True
    availability_reason: Optional[str] = None
    
    # Métriques
    latency_ms: int = 0
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    
    # Validation
    is_valid: bool = True
    validation_error: Optional[str] = None
    
    # Raw
    raw_response: Optional[str] = None
    
    def to_vote(self) -> Vote:
        """Convertit en Vote pour ConsensusManager."""
        return Vote(
            provider=f"{self.provider}/{self.model}",
            vote=self.vote_type,
            reasoning=self.reasoning,
            confidence=self.confidence,
            timestamp=time.time(),
            risks_identified=self.risks_identified,
            available=self.available,
            availability_reason=self.availability_reason,
        )
    
    def to_audit_dict(self) -> Dict[str, Any]:
        """Génère un dict pour l'audit."""
        return {
            "arbiter_id": self.arbiter_id,
            "provider": self.provider,
            "model": self.model,
            "vote": self.vote_type.value if self.vote_type else "unavailable",
            "approve": self.approve,
            "confidence": self.confidence,
            "latency_ms": self.latency_ms,
            "timestamp": self.timestamp,
            "is_valid": self.is_valid,
            "reasoning": self.reasoning[:200],  # Tronquer pour audit
        }


# ═══════════════════════════════════════════════════════════════════════════════
# ARBITER CALLER
# ═══════════════════════════════════════════════════════════════════════════════

class ArbiterCaller:
    """
    Appelle les arbitres LLM pour obtenir leurs votes.
    
    Cette classe fait les vrais appels API aux LLMs.
    """
    
    def __init__(self, config: ConsensusConfig):
        self.config = config
        self._llm_clients: Dict[str, Any] = {}
    
    async def call_arbiter(
        self,
        arbiter: ArbiterConfig,
        action: str,
        context: Dict[str, Any],
    ) -> ArbiterVote:
        """
        Appelle un arbitre LLM pour obtenir son vote.
        
        Args:
            arbiter: Configuration de l'arbitre
            action: Action à évaluer
            context: Contexte complet
            
        Returns:
            ArbiterVote avec le résultat
        """
        arbiter_id = f"{arbiter.provider}:{arbiter.model}"
        start_time = time.time()
        
        PrintStyle(font_color="cyan").print(
            f"🔍 call_arbiter: Starting for {arbiter_id}..."
        )
        
        try:
            # Construire le prompt
            PrintStyle(font_color="cyan").print(
                f"🔍 call_arbiter: Building prompt..."
            )
            prompt = build_vote_prompt(action, context)
            PrintStyle(font_color="cyan").print(
                f"🔍 call_arbiter: Prompt built, length={len(prompt)}"
            )
            
            # Appeler le LLM
            response = await self._call_llm(
                arbiter,
                prompt,
                arbiter.timeout_ms,
            )
            
            latency_ms = int((time.time() - start_time) * 1000)
            
            # Parser la réponse
            parsed = parse_llm_vote_response(response)
            
            return ArbiterVote(
                arbiter_id=arbiter_id,
                provider=arbiter.provider,
                model=arbiter.model,
                vote_type=VoteType.APPROVE if parsed["approve"] else VoteType.REJECT,
                approve=parsed["approve"],
                reasoning=parsed["reasoning"],
                confidence=parsed.get("confidence", 0.5),
                risks_identified=parsed.get("risks_identified", []),
                latency_ms=latency_ms,
                raw_response=response[:1000],  # Garder pour debug
            )
            
        except asyncio.TimeoutError:
            return ArbiterVote(
                arbiter_id=arbiter_id,
                provider=arbiter.provider,
                model=arbiter.model,
                vote_type=None,
                approve=False,
                reasoning="Timeout waiting for arbiter response",
                confidence=0.0,
                latency_ms=arbiter.timeout_ms,
                available=False,
                availability_reason="timeout",
                is_valid=False,
                validation_error="timeout",
            )
            
        except Exception as e:
            import traceback
            PrintStyle(font_color="red", bold=True).print(
                f"❌ call_arbiter EXCEPTION for {arbiter_id}: {type(e).__name__}: {str(e)[:200]}"
            )
            PrintStyle(font_color="red").print(
                f"   Traceback: {traceback.format_exc()[:500]}"
            )
            
            # ─── SIMULATION FALLBACK ─────────────────────────────────────
            # If simulation is enabled and the real call failed, generate
            # a simulated approval vote instead of an error vote.
            if self.config.simulation_enabled:
                logger.warning(
                    f"Arbiter {arbiter_id} failed but simulation enabled — "
                    f"returning simulated approval"
                )
                return ArbiterVote(
                    arbiter_id=arbiter_id,
                    provider=arbiter.provider,
                    model=arbiter.model,
                    vote_type=VoteType.APPROVE,
                    approve=True,
                    reasoning="Simulated approval (real call failed, simulation enabled)",
                    confidence=1.0,
                    risks_identified=["simulation_mode_active"],
                    latency_ms=int((time.time() - start_time) * 1000),
                    available=True,
                    availability_reason="simulation",
                )
            
            return ArbiterVote(
                arbiter_id=arbiter_id,
                provider=arbiter.provider,
                model=arbiter.model,
                vote_type=None,
                approve=False,
                reasoning=f"Error calling arbiter: {str(e)[:100]}",
                confidence=0.0,
                latency_ms=int((time.time() - start_time) * 1000),
                available=False,
                availability_reason="error",
                is_valid=False,
                validation_error=str(e)[:200],
            )
    
    async def _call_llm(
        self,
        arbiter: ArbiterConfig,
        prompt: str,
        timeout_ms: int,
    ) -> str:
        """
        Fait l'appel réel au LLM.
        
        Uses module-level imported llm_provider for stability.
        Fails fast if provider unavailable (no silent fallback).
        """
        arbiter_name = f"{arbiter.provider}/{arbiter.model}"
        PrintStyle(font_color="cyan").print(
            f"🔍 _call_llm: Starting call to {arbiter_name}, timeout={timeout_ms}ms"
        )
        
        # Check if provider is available (already validated at boot in prod)
        if not _LLM_PROVIDER_AVAILABLE:
            PrintStyle(font_color="red").print(
                f"❌ _call_llm: LLM provider NOT available!"
            )
            if self.config.simulation_enabled:
                logger.warning(
                    f"LLM provider unavailable, using simulation for "
                    f"{arbiter_name}"
                )
                return self._generate_simulated_vote(prompt)
            
            raise ArbiterUnavailableError(
                f"LLM provider layer unavailable. "
                f"Cannot call arbiter {arbiter_name}. "
                f"Set CONSENSUS_SIMULATION=true for testing without LLMs."
            )
        
        try:
            # Get provider wrapper (validated at module import)
            provider = _llm_provider.get_provider(arbiter.provider, arbiter.model)
            
            PrintStyle(font_color="cyan").print(
                f"🔍 _call_llm: Provider created, calling generate() for {arbiter_name}..."
            )
            
            response = await asyncio.wait_for(
                provider.generate(
                    prompt=prompt,
                    temperature=arbiter.temperature,
                    max_tokens=arbiter.max_tokens,
                ),
                timeout=timeout_ms / 1000,
            )
            
            PrintStyle(font_color="green").print(
                f"✅ _call_llm: Got response from {arbiter_name}: {response[:50]}..."
            )
            
            return response
        except asyncio.TimeoutError:
            PrintStyle(font_color="red").print(
                f"⏱️ _call_llm: TIMEOUT after {timeout_ms}ms for {arbiter_name}"
            )
            raise
        except Exception as e:
            PrintStyle(font_color="red").print(
                f"❌ _call_llm: ERROR calling {arbiter_name}: {type(e).__name__}: {e}"
            )
            raise
    
    def _generate_simulated_vote(self, prompt: str) -> str:
        """
        Génère un vote simulé — UNIQUEMENT EN DEV/TEST.
        
        Cette méthode ne sera JAMAIS appelée en production.
        """
        import random
        
        # Log warning
        logger.warning("⚠️  SIMULATED VOTE — This should NEVER happen in production!")
        
        # Vote aléatoire mais biaisé vers approve pour tests
        approve = random.random() > 0.3
        confidence = random.uniform(0.6, 0.95)
        
        return json.dumps({
            "approve": approve,
            "reasoning": "SIMULATED: This is a test vote, not a real LLM response.",
            "confidence": confidence,
            "risks_identified": ["simulation_mode_active"],
        })


# ═══════════════════════════════════════════════════════════════════════════════
# CONSENSUS ORCHESTRATOR
# ═══════════════════════════════════════════════════════════════════════════════

class ConsensusOrchestrator:
    """
    Orchestrateur de consensus avec arbitres réels.
    
    Usage:
        orchestrator = ConsensusOrchestrator()
        result = await orchestrator.seek_consensus(
            action="Publish research conclusion",
            context={"conclusion": "...", "sources": [...]}
        )
        
        if result.approved:
            # Procéder
        else:
            # Fail-closed
    """
    
    def __init__(self, config: ConsensusConfig = None):
        self.config = config or load_consensus_config()
        self.manager = ConsensusManager(
            timeout_ms=self.config.global_timeout_ms,
            total_providers=self.config.total_providers,
        )
        self.caller = ArbiterCaller(self.config)
        
        # Audit log
        self._audit_log: List[Dict[str, Any]] = []
        
        logger.info(
            f"ConsensusOrchestrator initialized: "
            f"{len(self.config.arbiters)} arbiters, "
            f"simulation={self.config.simulation_enabled}, "
            f"offline={self.config.offline_mode}"
        )
    
    async def seek_consensus(
        self,
        action: str,
        context: Dict[str, Any],
        decision_type: DecisionType = DecisionType.CRITICAL,
        evidence_pack: Optional[Dict[str, Any]] = None,
        correlation_id: str = None,
    ) -> ConsensusResult:
        """
        Cherche un consensus auprès des arbitres.
        
        Args:
            action: Description de l'action à valider
            context: Contexte complet
            decision_type: Type de décision PRISM
            evidence_pack: Pack de preuves (optionnel)
            correlation_id: ID de corrélation pour traçabilité
            
        Returns:
            ConsensusResult
        """
        from python.consensus.engine import run_consensus as run_consensus_v2

        decision = await run_consensus_v2(
            evidence_pack=evidence_pack,
            policy={
                "action": action,
                "context": context,
                "decision_type": decision_type,
                "correlation_id": correlation_id,
            },
        )

        return ConsensusResult(
            proposal_id=decision.proposal_id,
            approved=decision.approved,
            status=decision.status,
            votes=decision.votes,
            vote_count=decision.vote_count,
            decision_hash=decision.decision_hash,
            decision_time_ms=decision.decision_time_ms,
            timestamp=time.time(),
        )
    
    def _select_arbiters(self) -> List[ArbiterConfig]:
        """Sélectionne les arbitres disponibles."""
        if self.config.offline_mode:
            if self.config.local_arbiters:
                return self.config.local_arbiters[:self.config.total_providers]
            # Pas d'arbitres en mode offline
            return []
        
        return sorted(
            self.config.arbiters,
            key=lambda a: a.priority
        )[:self.config.total_providers]
    
    def _count_votes(self, votes: List[ArbiterVote]) -> VoteCount:
        """Compte les votes."""
        count = VoteCount()
        for vote in votes:
            if not vote.available:
                count.unavailable += 1
            elif vote.vote_type == VoteType.APPROVE:
                count.approvals += 1
            elif vote.vote_type == VoteType.REJECT:
                count.rejections += 1
            elif vote.vote_type == VoteType.ABSTAIN:
                count.abstentions += 1
            count.total += 1
        return count
    
    def _create_no_arbiter_result(
        self,
        action: str,
        context: Dict[str, Any],
        decision_type: DecisionType,
        correlation_id: str,
    ) -> ConsensusResult:
        """Crée un résultat quand aucun arbitre n'est disponible."""
        if self.config.fail_on_no_arbiters:
            # Infra failure: no arbiter -> no decision
            status = ConsensusStatus.INFRA_FAILURE
            approved = False
            logger.warning(
                f"No arbiters available for consensus, infra_failure applied "
                f"(correlation_id={correlation_id})"
            )
        else:
            # Mode dégradé désactivé: jamais auto-approve
            status = ConsensusStatus.INFRA_FAILURE
            approved = False
            logger.warning(
                f"No arbiters available, degraded auto-approve disabled "
                f"(correlation_id={correlation_id})"
            )
        
        return ConsensusResult(
            proposal_id=str(uuid.uuid4()),
            approved=approved,
            status=status,
            votes={},
            vote_count=VoteCount(),
            decision_hash=generate_decision_hash(action, context),
            decision_time_ms=0,
            timestamp=time.time(),
        )
    
    def _log_audit(
        self,
        correlation_id: str,
        action: str,
        decision_type: DecisionType,
        result: ConsensusResult,
        arbiter_votes: List[ArbiterVote],
    ):
        """Enregistre l'événement dans l'audit log."""
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "correlation_id": correlation_id,
            "event": "consensus_decision",
            "action": action[:500],
            "decision_type": decision_type.value,
            "result": {
                "proposal_id": result.proposal_id,
                "approved": result.approved,
                "status": result.status.value,
                "decision_time_ms": result.decision_time_ms,
                "vote_count": result.vote_count.__dict__,
            },
            "votes": [v.to_audit_dict() for v in arbiter_votes],
        }
        
        self._audit_log.append(entry)
        
        # Aussi logger pour le fichier
        logger.info(
            f"Consensus decision: {result.status.value} "
            f"({result.vote_count.approvals}/{result.vote_count.total} approvals) "
            f"[{correlation_id}]"
        )
    
    def get_audit_log(self) -> List[Dict[str, Any]]:
        """Retourne le log d'audit."""
        return self._audit_log.copy()
    
    def get_metrics(self) -> Dict[str, Any]:
        """Retourne les métriques."""
        return {
            **self.manager.metrics,
            "arbiters_configured": len(self.config.arbiters),
            "simulation_enabled": self.config.simulation_enabled,
            "offline_mode": self.config.offline_mode,
        }


# ═══════════════════════════════════════════════════════════════════════════════
# SINGLETON & FACTORY
# ═══════════════════════════════════════════════════════════════════════════════

_orchestrator_instance: Optional[ConsensusOrchestrator] = None


def reset_consensus_orchestrator() -> None:
    """
    Reset the singleton orchestrator to force reload of configuration.
    
    Use this after changing environment variables or configuration
    without restarting the application.
    """
    global _orchestrator_instance
    if _orchestrator_instance is not None:
        logger.info("🔄 Resetting ConsensusOrchestrator singleton")
    _orchestrator_instance = None


def get_consensus_orchestrator() -> ConsensusOrchestrator:
    """Retourne l'instance singleton de l'orchestrateur."""
    global _orchestrator_instance
    if _orchestrator_instance is None:
        _orchestrator_instance = ConsensusOrchestrator()
    return _orchestrator_instance


async def seek_consensus(
    action: str,
    context: Dict[str, Any],
    decision_type: DecisionType = DecisionType.CRITICAL,
    evidence_pack: Optional[Dict[str, Any]] = None,
    correlation_id: str = None,
) -> ConsensusResult:
    """
    Fonction raccourci pour chercher un consensus.
    
    Usage:
        from python.helpers.consensus_arbiter import seek_consensus
        
        result = await seek_consensus(
            action="Publish conclusion",
            context={"conclusion": "...", "sources": [...]},
            decision_type=DecisionType.RESEARCH_VALIDATION,
        )
        
        if result.approved:
            # OK
    """
    orchestrator = get_consensus_orchestrator()
    return await orchestrator.seek_consensus(
        action, context, decision_type, evidence_pack, correlation_id
    )


def verify_no_simulation_in_production():
    """
    Vérifie que la simulation n'est pas active en production.
    
    À appeler au démarrage de l'application.
    
    Raises:
        SimulationError si CONSENSUS_SIMULATION=true en production
    """
    env = os.environ.get("EVIDENCE_ENV", "production").lower()
    simulation = os.environ.get("CONSENSUS_SIMULATION", "false").lower() == "true"
    
    if env == "production" and simulation:
        raise SimulationError(
            "CONSENSUS_SIMULATION=true is FORBIDDEN in production. "
            "Votes must be real. Set EVIDENCE_ENV=development for testing."
        )
    
    if simulation:
        logger.warning(
            "⚠️  CONSENSUS_SIMULATION=true — Votes are simulated! "
            "This is ONLY acceptable in development/testing."
        )


# ═══════════════════════════════════════════════════════════════════════════════
# EXPORTS
# ═══════════════════════════════════════════════════════════════════════════════

__all__ = [
    # Exceptions
    "SimulationError",
    "ArbiterUnavailableError",
    # Config
    "ArbiterConfig",
    "ConsensusConfig",
    "load_consensus_config",
    # Data
    "ArbiterVote",
    # Classes
    "ArbiterCaller",
    "ConsensusOrchestrator",
    # Functions
    "get_consensus_orchestrator",
    "seek_consensus",
    "verify_no_simulation_in_production",
]
