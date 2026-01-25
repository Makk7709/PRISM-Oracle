"""
╔══════════════════════════════════════════════════════════════════════════════╗
║              CONSENSUS ARBITER — Real LLM Voting System                      ║
║                                                                              ║
║  Système d'arbitrage réel via LLMs multiples pour le consensus PRISM.        ║
║                                                                              ║
║  RÈGLES CRITIQUES:                                                           ║
║  1. CONSENSUS_SIMULATION=false en production (hard fail si true)             ║
║  2. Chaque arbitre DOIT retourner un vote structuré                          ║
║  3. Timeout = UNAVAILABLE (pas REJECT par défaut côté arbitre)               ║
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

logger = logging.getLogger("consensus_arbiter")


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


def load_consensus_config() -> ConsensusConfig:
    """
    Charge la configuration depuis l'environnement.
    
    Variables d'environnement:
    - CONSENSUS_SIMULATION: "true"/"false" (default: false)
    - CONSENSUS_ARBITERS: JSON list de providers
    - CONSENSUS_LOCAL_ARBITERS: JSON list pour mode offline
    - CONSENSUS_TIMEOUT_MS: Timeout global
    - OFFLINE_MODE: Mode hors-ligne
    - EVIDENCE_ENV: "production"/"development"
    """
    # Vérification critique: simulation en production
    env = os.environ.get("EVIDENCE_ENV", "production").lower()
    is_production = env == "production"
    simulation_enabled = os.environ.get("CONSENSUS_SIMULATION", "false").lower() == "true"
    
    if is_production and simulation_enabled:
        error_msg = (
            "CRITICAL: CONSENSUS_SIMULATION=true is FORBIDDEN in production. "
            "This is a hard fail to prevent fake consensus. "
            "Set EVIDENCE_ENV=development or remove CONSENSUS_SIMULATION."
        )
        logger.critical(error_msg)
        raise SimulationError(error_msg)
    
    # Charger les arbitres
    arbiters_json = os.environ.get("CONSENSUS_ARBITERS", "[]")
    try:
        arbiters_raw = json.loads(arbiters_json)
        arbiters = [
            ArbiterConfig(
                provider=a.get("provider", "unknown"),
                model=a.get("model", "unknown"),
                timeout_ms=a.get("timeout_ms", 3000),
                priority=a.get("priority", 0),
            )
            for a in arbiters_raw
        ]
    except json.JSONDecodeError:
        arbiters = []
    
    # Arbitres par défaut si non configurés
    if not arbiters:
        arbiters = [
            ArbiterConfig(provider="openai", model="gpt-4o", priority=0),
            ArbiterConfig(provider="anthropic", model="claude-3-5-sonnet", priority=1),
            ArbiterConfig(provider="google", model="gemini-1.5-pro", priority=2),
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
        global_timeout_ms=int(os.environ.get("CONSENSUS_TIMEOUT_MS", "10000")),
        per_arbiter_timeout_ms=int(os.environ.get("CONSENSUS_PER_ARBITER_TIMEOUT_MS", "3000")),
        simulation_enabled=simulation_enabled,
        total_providers=len(arbiters) if arbiters else 3,
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
    vote_type: VoteType
    approve: bool
    reasoning: str
    confidence: float  # 0.0-1.0
    risks_identified: List[str] = field(default_factory=list)
    
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
        )
    
    def to_audit_dict(self) -> Dict[str, Any]:
        """Génère un dict pour l'audit."""
        return {
            "arbiter_id": self.arbiter_id,
            "provider": self.provider,
            "model": self.model,
            "vote": self.vote_type.value,
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
        
        try:
            # Construire le prompt
            prompt = build_vote_prompt(action, context)
            
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
                vote_type=VoteType.UNAVAILABLE,
                approve=False,
                reasoning="Timeout waiting for arbiter response",
                confidence=0.0,
                latency_ms=arbiter.timeout_ms,
                is_valid=False,
                validation_error="timeout",
            )
            
        except Exception as e:
            return ArbiterVote(
                arbiter_id=arbiter_id,
                provider=arbiter.provider,
                model=arbiter.model,
                vote_type=VoteType.UNAVAILABLE,
                approve=False,
                reasoning=f"Error calling arbiter: {str(e)[:100]}",
                confidence=0.0,
                latency_ms=int((time.time() - start_time) * 1000),
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
        
        Cette méthode doit être implémentée selon votre setup LLM.
        """
        # Import dynamique pour éviter dépendances circulaires
        try:
            from python.helpers.llm_provider import get_provider
            
            provider = get_provider(arbiter.provider, arbiter.model)
            
            response = await asyncio.wait_for(
                provider.generate(
                    prompt=prompt,
                    temperature=arbiter.temperature,
                    max_tokens=arbiter.max_tokens,
                ),
                timeout=timeout_ms / 1000,
            )
            
            return response
            
        except ImportError:
            # Fallback si pas de provider configuré
            logger.warning(
                f"LLM provider {arbiter.provider} not available, "
                "using mock response for testing"
            )
            
            # En mode simulation (dev uniquement)
            if self.config.simulation_enabled:
                return self._generate_simulated_vote(prompt)
            
            raise ArbiterUnavailableError(
                f"Arbiter {arbiter.provider}/{arbiter.model} unavailable "
                "and simulation is disabled"
            )
    
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
        correlation_id = correlation_id or str(uuid.uuid4())
        start_time = time.time()
        
        # Sélectionner les arbitres
        arbiters = self._select_arbiters()
        
        if not arbiters:
            return self._create_no_arbiter_result(
                action, context, decision_type, correlation_id
            )
        
        # Créer la proposition
        decision_hash = generate_decision_hash(action, context)
        proposal_id = await self.manager.propose(
            decision_hash,
            {
                "action": action,
                "context": context,
                "evidence_pack": evidence_pack,
                "correlation_id": correlation_id,
            },
            decision_type,
        )
        
        # Appeler les arbitres en parallèle
        tasks = [
            self.caller.call_arbiter(arbiter, action, context)
            for arbiter in arbiters
        ]
        
        votes = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Soumettre les votes
        arbiter_votes: List[ArbiterVote] = []
        for i, vote_result in enumerate(votes):
            if isinstance(vote_result, Exception):
                vote_result = ArbiterVote(
                    arbiter_id=f"{arbiters[i].provider}:{arbiters[i].model}",
                    provider=arbiters[i].provider,
                    model=arbiters[i].model,
                    vote_type=VoteType.UNAVAILABLE,
                    approve=False,
                    reasoning=f"Exception: {str(vote_result)[:100]}",
                    confidence=0.0,
                    is_valid=False,
                    validation_error=str(vote_result),
                )
            
            arbiter_votes.append(vote_result)
            
            # Soumettre au manager
            self.manager.submit_vote(
                proposal_id=proposal_id,
                provider=vote_result.provider + "/" + vote_result.model,
                vote=vote_result.vote_type,
                reasoning=vote_result.reasoning,
                confidence=vote_result.confidence,
                risks=vote_result.risks_identified,
            )
        
        # Attendre le résultat
        status = await self.manager.wait_for_consensus(
            proposal_id,
            max_wait_ms=self.config.global_timeout_ms,
        )
        
        # Calculer le temps de décision
        decision_time_ms = int((time.time() - start_time) * 1000)
        
        # Construire le résultat
        proposal = self.manager.recent_proposals.get(proposal_id)
        if not proposal:
            # Fallback si pas dans recent (ne devrait pas arriver)
            final_status = ConsensusStatus.TIMEOUT
            approved = False
        else:
            final_status = proposal.status
            approved = final_status == ConsensusStatus.APPROVED
        
        result = ConsensusResult(
            proposal_id=proposal_id,
            approved=approved,
            status=final_status,
            votes={v.provider: v.to_vote() for v in arbiter_votes},
            vote_count=self._count_votes(arbiter_votes),
            decision_hash=decision_hash,
            decision_time_ms=decision_time_ms,
            timestamp=time.time(),
        )
        
        # Audit
        self._log_audit(
            correlation_id=correlation_id,
            action=action,
            decision_type=decision_type,
            result=result,
            arbiter_votes=arbiter_votes,
        )
        
        return result
    
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
            if vote.vote_type == VoteType.APPROVE:
                count.approvals += 1
            elif vote.vote_type == VoteType.REJECT:
                count.rejections += 1
            elif vote.vote_type == VoteType.ABSTAIN:
                count.abstentions += 1
            else:
                count.unavailable += 1
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
            # Fail-closed: pas d'arbitre = pas d'approbation
            status = ConsensusStatus.REJECTED
            approved = False
            logger.warning(
                f"No arbiters available for consensus, fail-closed applied "
                f"(correlation_id={correlation_id})"
            )
        else:
            # Mode dégradé (non recommandé)
            status = ConsensusStatus.APPROVED
            approved = True
            logger.warning(
                f"No arbiters available, degraded mode (auto-approve) "
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
