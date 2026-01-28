"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                         PRISM CONSENSUS MANAGER                              ║
║                                                                              ║
║  Système de consensus multi-IA pour validation des décisions critiques.     ║
║                                                                              ║
║  Principes :                                                                 ║
║  - Vote majoritaire 2/3 entre plusieurs LLMs                                 ║
║  - Fail-closed : en cas de doute, rejeter                                    ║
║  - Traçabilité complète de toutes les décisions                              ║
║  - Timeout strict avec rejet automatique                                     ║
║                                                                              ║
║  "Evidence ne cherche pas, Evidence instruit un dossier."                        ║
║                                                                              ║
║  Version: 1.0.0                                                              ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import asyncio
import hashlib
import json
import logging
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional, Union
from collections import defaultdict

logger = logging.getLogger("prism_consensus")


# ═══════════════════════════════════════════════════════════════════════════════
# ENUMS (single source of truth)
# ═══════════════════════════════════════════════════════════════════════════════

from python.helpers.consensus_contracts import (
    DecisionTypeEnum as DecisionType,
    VoteVerdictEnum as VoteType,
    ConsensusStatusEnum as ConsensusStatus,
)


# ═══════════════════════════════════════════════════════════════════════════════
# DATA CLASSES
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class Vote:
    """Représente un vote d'un arbitre."""
    provider: str
    vote: Optional[VoteType]
    reasoning: str
    confidence: float
    timestamp: float
    risks_identified: List[str] = field(default_factory=list)
    available: bool = True
    availability_reason: Optional[str] = None


@dataclass
class VoteCount:
    """Comptage des votes."""
    approvals: int = 0
    rejections: int = 0
    abstentions: int = 0
    unavailable: int = 0
    total: int = 0
    
    @property
    def effective_votes(self) -> int:
        """
        Number of effective votes (excluding unavailable).
        
        INVARIANT: Only approve/reject/abstain count as effective votes.
        Unavailable is an infrastructure signal, NOT a vote.
        """
        return self.approvals + self.rejections + self.abstentions
    
    @property
    def decisive_votes(self) -> int:
        """Number of decisive votes (approve + reject, excluding abstain)."""
        return self.approvals + self.rejections


@dataclass
class DecisionProposal:
    """Proposition de décision pour validation collective."""
    id: str
    decision_hash: str
    payload: Dict[str, Any]
    type: DecisionType
    timestamp: float
    votes: Dict[str, Vote] = field(default_factory=dict)
    status: ConsensusStatus = ConsensusStatus.PENDING
    total_providers: int = 3
    min_effective_votes: int = 2  # Minimum effective votes required for any verdict
    timeout_task: Optional[asyncio.Task] = None
    
    def add_vote(
        self,
        provider: str,
        vote: Optional[VoteType],
        reasoning: str = "",
        confidence: float = 0.0,
        risks: List[str] = None,
        available: bool = True,
        availability_reason: Optional[str] = None,
    ):
        """Ajoute un vote à la proposition."""
        if vote is None and available:
            available = False
        self.votes[provider] = Vote(
            provider=provider,
            vote=vote,
            reasoning=reasoning,
            confidence=confidence,
            timestamp=time.time(),
            risks_identified=risks or [],
            available=available,
            availability_reason=availability_reason,
        )
    
    def get_vote_count(self) -> VoteCount:
        """Calcule le comptage des votes."""
        count = VoteCount()
        for vote in self.votes.values():
            if not vote.available:
                count.unavailable += 1
            elif vote.vote == VoteType.APPROVE:
                count.approvals += 1
            elif vote.vote == VoteType.REJECT:
                count.rejections += 1
            elif vote.vote == VoteType.ABSTAIN:
                count.abstentions += 1
            count.total += 1
        return count
    
    def check_consensus(self) -> bool:
        """
        Vérifie si le consensus est atteint.
        
        INVARIANTS (non-négociables):
        1. Unavailable != vote. Ne compte jamais dans le quorum.
        2. Aucun vote effectif ⇒ aucun verdict juridique (INFRA_FAILURE).
        3. Le quorum se calcule sur les votes effectifs uniquement.
        4. Fail-closed ≠ mensonge : bloquer sans inventer une décision.
        5. Toute décision doit être explicable par un tally réel.
        
        Règles de verdict (ONLY when enough data to decide):
        - First: check if quorum reached (can decide early)
        - Only when ALL providers responded:
          - INFRA_FAILURE if effective_votes == 0
          - NO_CONSENSUS if effective_votes < min_effective_votes
          - NO_CONSENSUS if no quorum reached
        """
        count = self.get_vote_count()
        effective = count.effective_votes
        all_responded = count.total >= self.total_providers
        
        # Log the tally for auditability
        logger.debug(
            f"Consensus tally: approvals={count.approvals}, rejections={count.rejections}, "
            f"abstentions={count.abstentions}, unavailable={count.unavailable}, "
            f"effective_votes={effective}, min_required={self.min_effective_votes}, "
            f"all_responded={all_responded}"
        )
        
        # ─────────────────────────────────────────────────────────────────────────
        # EARLY EXIT: Check if quorum already reached (can decide without all votes)
        # ─────────────────────────────────────────────────────────────────────────
        if effective >= self.min_effective_votes:
            required_quorum = (effective * 2 + 2) // 3  # ceil(2/3 * effective)
            
            # APPROVED if 2/3 of effective votes approve
            if count.approvals >= required_quorum:
                self.status = ConsensusStatus.APPROVED
                logger.info(
                    f"Consensus APPROVED: {count.approvals}/{effective} effective votes "
                    f"(quorum: {required_quorum})"
                )
                return True
            
            # REJECTED if 2/3 of effective votes reject
            if count.rejections >= required_quorum:
                self.status = ConsensusStatus.REJECTED
                logger.info(
                    f"Consensus REJECTED: {count.rejections}/{effective} effective votes "
                    f"(quorum: {required_quorum})"
                )
                return True
        
        # ─────────────────────────────────────────────────────────────────────────
        # NOT ALL PROVIDERS RESPONDED: Wait for more votes
        # ─────────────────────────────────────────────────────────────────────────
        if not all_responded:
            return False  # Keep waiting
        
        # ─────────────────────────────────────────────────────────────────────────
        # ALL PROVIDERS RESPONDED: Now we must render a final verdict
        # ─────────────────────────────────────────────────────────────────────────
        
        # CASE 1: Zero effective votes = Infrastructure failure
        # All providers responded but none provided an actual vote.
        if effective == 0:
            self.status = ConsensusStatus.INFRA_FAILURE
            logger.warning(
                f"Consensus INFRA_FAILURE: 0 effective votes "
                f"({count.unavailable} unavailable). No arbiter evaluated content."
            )
            return True
        
        # CASE 2: Not enough effective votes
        if effective < self.min_effective_votes:
            self.status = ConsensusStatus.NO_CONSENSUS
            logger.warning(
                f"Consensus NO_CONSENSUS: only {effective} effective votes "
                f"(min required: {self.min_effective_votes}). Cannot render verdict."
            )
            return True
        
        # CASE 3: Enough votes but no quorum reached
        # All providers responded, we have enough effective votes, but no 2/3 majority
        required_quorum = (effective * 2 + 2) // 3
        self.status = ConsensusStatus.NO_CONSENSUS
        logger.info(
            f"Consensus NO_CONSENSUS: all {count.total} responded but no quorum. "
            f"Approvals={count.approvals}, Rejections={count.rejections}, "
            f"Abstentions={count.abstentions}, Required={required_quorum}"
        )
        return True


@dataclass
class ConsensusResult:
    """Résultat d'un consensus."""
    proposal_id: str
    approved: bool
    status: ConsensusStatus
    votes: Dict[str, Vote]
    vote_count: VoteCount
    decision_hash: str
    decision_time_ms: int
    timestamp: float


# ═══════════════════════════════════════════════════════════════════════════════
# CONSENSUS MANAGER
# ═══════════════════════════════════════════════════════════════════════════════

class ConsensusManager:
    """
    Gestionnaire de consensus pour les décisions critiques.
    
    Implémente le principe fail-closed : en cas de doute, rejeter.
    """
    
    def __init__(
        self,
        timeout_ms: int = 10000,
        total_providers: int = 3,
        max_concurrent_proposals: int = 10
    ):
        self.timeout_ms = timeout_ms
        self.total_providers = total_providers
        self.max_concurrent_proposals = max_concurrent_proposals
        
        self.proposals: Dict[str, DecisionProposal] = {}
        self.recent_proposals: Dict[str, DecisionProposal] = {}
        
        # Métriques
        self.metrics = {
            "total_proposals": 0,
            "approved_proposals": 0,
            "rejected_proposals": 0,
            "timeout_proposals": 0,
            "average_decision_time": 0.0
        }
        
        # Callbacks pour événements
        self._callbacks: Dict[str, List[Callable]] = defaultdict(list)
        
        logger.info("🔒 ConsensusManager initialized")
    
    def on(self, event: str, callback: Callable):
        """Enregistre un callback pour un événement."""
        self._callbacks[event].append(callback)
    
    def _emit(self, event: str, data: Any):
        """Émet un événement."""
        for callback in self._callbacks.get(event, []):
            try:
                callback(data)
            except Exception as e:
                logger.error(f"Error in event callback: {e}")
    
    async def propose(
        self,
        decision_hash: str,
        payload: Dict[str, Any],
        decision_type: DecisionType = DecisionType.CRITICAL
    ) -> str:
        """
        Propose une décision pour validation collective.
        
        Args:
            decision_hash: Hash unique de la décision
            payload: Données de la décision
            decision_type: Type de décision
            
        Returns:
            ID de la proposition
        """
        # Vérifier limite de propositions
        if len(self.proposals) >= self.max_concurrent_proposals:
            raise RuntimeError("Maximum concurrent proposals reached")
        
        # Créer la proposition
        proposal = DecisionProposal(
            id=str(uuid.uuid4()),
            decision_hash=decision_hash,
            payload=payload,
            type=decision_type,
            timestamp=time.time(),
            total_providers=self.total_providers
        )
        
        self.proposals[proposal.id] = proposal
        self.metrics["total_proposals"] += 1
        
        # Configurer le timeout
        proposal.timeout_task = asyncio.create_task(
            self._handle_timeout(proposal.id)
        )
        
        # Émettre événement
        self._emit("proposal_created", {
            "proposal_id": proposal.id,
            "decision_hash": decision_hash,
            "payload": payload,
            "type": decision_type.value,
            "timestamp": proposal.timestamp
        })
        
        logger.info(f"📝 Nouvelle proposition créée: {proposal.id[:8]}...")
        
        return proposal.id
    
    def submit_vote(
        self,
        proposal_id: str,
        provider: str,
        vote: Union[VoteType, bool, str, None],
        reasoning: str = "",
        confidence: float = 0.0,
        risks: List[str] = None,
        available: Optional[bool] = None,
        availability_reason: Optional[str] = None,
    ) -> bool:
        """
        Soumet un vote pour une proposition.
        
        Args:
            proposal_id: ID de la proposition
            provider: Nom du votant (LLM)
            vote: Type de vote
            reasoning: Raisonnement
            confidence: Niveau de confiance (0-1)
            risks: Risques identifiés
            
        Returns:
            True si vote accepté
        """
        proposal = self.proposals.get(proposal_id)
        if not proposal or proposal.status != ConsensusStatus.PENDING:
            return False
        
        # Normaliser le vote
        normalized_vote = self._normalize_vote(vote)
        if available is None:
            available = normalized_vote is not None
        
        # Ajouter le vote
        proposal.add_vote(
            provider,
            normalized_vote,
            reasoning,
            confidence,
            risks,
            available=available,
            availability_reason=availability_reason,
        )
        
        # Émettre événement
        self._emit("vote_submitted", {
            "proposal_id": proposal_id,
            "provider": provider,
            "vote": normalized_vote.value if normalized_vote else "unavailable",
            "reasoning": reasoning,
            "timestamp": time.time()
        })
        
        logger.info(
            f"🗳️  Vote de {provider}: "
            f"{normalized_vote.value if normalized_vote else 'unavailable'}"
        )
        
        # Vérifier si consensus atteint
        if proposal.check_consensus():
            asyncio.create_task(self._finalize_proposal(proposal_id))
        
        return True
    
    def _normalize_vote(self, vote: Union[VoteType, bool, str, None]) -> Optional[VoteType]:
        """Normalise un vote vers VoteType (None = unavailable)."""
        if isinstance(vote, VoteType):
            return vote
        if vote is True or vote == "approve":
            return VoteType.APPROVE
        if vote is False or vote == "reject":
            return VoteType.REJECT
        if vote == "abstain":
            return VoteType.ABSTAIN
        if vote == "unavailable" or vote == "timeout":
            return None
        return None
    
    async def _handle_timeout(self, proposal_id: str):
        """Gère le timeout d'une proposition."""
        await asyncio.sleep(self.timeout_ms / 1000)
        
        proposal = self.proposals.get(proposal_id)
        if not proposal or proposal.status != ConsensusStatus.PENDING:
            return
        
        # Timeout: if no effective votes, infra failure; else no consensus
        count = proposal.get_vote_count()
        if count.effective_votes == 0:
            proposal.status = ConsensusStatus.INFRA_FAILURE
        else:
            proposal.status = ConsensusStatus.NO_CONSENSUS
        self.metrics["timeout_proposals"] += 1
        
        self._emit("consensus_timeout", {
            "proposal_id": proposal_id,
            "status": proposal.status.value,
            "decision_hash": proposal.decision_hash,
            "votes": proposal.get_vote_count().__dict__
        })
        
        logger.warning(f"⏰ Timeout pour proposition: {proposal_id[:8]}...")
        
        # Archiver
        self.recent_proposals[proposal_id] = proposal
        self.proposals.pop(proposal_id, None)
    
    async def _finalize_proposal(self, proposal_id: str):
        """Finalise une proposition."""
        proposal = self.proposals.get(proposal_id)
        if not proposal:
            return
        
        # Annuler timeout
        if proposal.timeout_task and not proposal.timeout_task.done():
            proposal.timeout_task.cancel()
        
        # Calculer temps de décision
        decision_time_ms = int((time.time() - proposal.timestamp) * 1000)
        
        # Mettre à jour métriques selon le statut
        if proposal.status == ConsensusStatus.APPROVED:
            self.metrics["approved_proposals"] += 1
        elif proposal.status == ConsensusStatus.REJECTED:
            self.metrics["rejected_proposals"] += 1
        elif proposal.status == ConsensusStatus.NO_CONSENSUS:
            self.metrics["no_consensus_proposals"] = self.metrics.get("no_consensus_proposals", 0) + 1
        elif proposal.status == ConsensusStatus.INFRA_FAILURE:
            self.metrics["infra_failure_proposals"] = self.metrics.get("infra_failure_proposals", 0) + 1
        
        # Calculer moyenne temps de décision (seulement pour APPROVED/REJECTED)
        if proposal.status in (ConsensusStatus.APPROVED, ConsensusStatus.REJECTED):
            total_decisions = (
                self.metrics["approved_proposals"] + 
                self.metrics["rejected_proposals"]
            )
            self.metrics["average_decision_time"] = (
                (self.metrics["average_decision_time"] * (total_decisions - 1) + 
                 decision_time_ms) / total_decisions
            )
        
        # Émettre événement avec effective_votes pour auditabilité
        vote_count = proposal.get_vote_count()
        self._emit("consensus_reached", {
            "proposal_id": proposal_id,
            "status": proposal.status.value,
            "decision_hash": proposal.decision_hash,
            "approvals": vote_count.approvals,
            "rejections": vote_count.rejections,
            "abstentions": vote_count.abstentions,
            "unavailable": vote_count.unavailable,
            "total": vote_count.total,
            "effective_votes": vote_count.effective_votes,
            "decision_time_ms": decision_time_ms
        })
        
        # Log avec emoji approprié
        status_emoji = {
            ConsensusStatus.APPROVED: "✅",
            ConsensusStatus.REJECTED: "❌",
            ConsensusStatus.NO_CONSENSUS: "⚠️",
            ConsensusStatus.INFRA_FAILURE: "🔴",
        }
        emoji = status_emoji.get(proposal.status, "❓")
        logger.info(
            f"{emoji} Consensus: {proposal.status.value} "
            f"(effective: {vote_count.effective_votes}, "
            f"approvals: {vote_count.approvals}, rejections: {vote_count.rejections})"
        )
        
        # Archiver
        self.recent_proposals[proposal_id] = proposal
        self.proposals.pop(proposal_id, None)
    
    def get_proposal_status(self, proposal_id: str) -> Optional[Dict[str, Any]]:
        """Récupère le statut d'une proposition."""
        proposal = (
            self.proposals.get(proposal_id) or 
            self.recent_proposals.get(proposal_id)
        )
        if not proposal:
            return None
        
        return {
            "status": proposal.status,
            "votes": proposal.get_vote_count().__dict__,
            "timestamp": proposal.timestamp,
            "type": proposal.type.value
        }
    
    async def wait_for_consensus(
        self, 
        proposal_id: str, 
        max_wait_ms: int = 5000
    ) -> Optional[Dict[str, Any]]:
        """Attend qu'une proposition soit finalisée."""
        start_time = time.time()
        
        while (time.time() - start_time) * 1000 < max_wait_ms:
            status = self.get_proposal_status(proposal_id)
            if status and status["status"] != ConsensusStatus.PENDING:
                return status
            await asyncio.sleep(0.1)
        
        return self.get_proposal_status(proposal_id)


# ═══════════════════════════════════════════════════════════════════════════════
# VOTE PROMPT BUILDER
# ═══════════════════════════════════════════════════════════════════════════════

def build_vote_prompt(action: str, context: Dict[str, Any]) -> str:
    """
    Construit le prompt pour demander un vote à un LLM arbitre.
    
    Args:
        action: Description de l'action à évaluer
        context: Contexte de l'action
        
    Returns:
        Prompt formaté
    """
    return f"""Tu es un expert en sécurité des systèmes IA et en validation de décisions.
Tu dois évaluer si une action proposée est sûre, appropriée et scientifiquement valide.

## Action Proposée
{action}

## Contexte
{json.dumps(context, indent=2, ensure_ascii=False)}

## Critères d'Évaluation
1. L'action est-elle réversible ?
2. Y a-t-il un risque de perte de données ou d'information erronée ?
3. L'action respecte-t-elle les principes éthiques et scientifiques ?
4. Les sources sont-elles vérifiables et fiables ?
5. Le contexte justifie-t-il cette action/conclusion ?
6. Y a-t-il des biais potentiels dans le raisonnement ?

## Instructions
Réponds UNIQUEMENT avec un objet JSON valide :
{{
  "approve": true ou false,
  "reasoning": "Explication de ta décision en 1-3 phrases",
  "confidence": 0.0 à 1.0,
  "risks_identified": ["liste", "des", "risques"]
}}

Ne fournis AUCUN texte en dehors du JSON."""


def parse_llm_vote_response(response: str) -> Dict[str, Any]:
    """
    Parse et valide une réponse de vote d'un LLM.
    
    Args:
        response: Réponse JSON du LLM
        
    Returns:
        Dict avec approve, reasoning, confidence, risks_identified
        
    Raises:
        ValueError: Si parsing ou validation échoue
    """
    import re
    
    # Extraire JSON si entouré de texte
    json_match = re.search(r'\{[\s\S]*\}', response)
    if not json_match:
        raise ValueError("No valid JSON object found in response")
    
    try:
        parsed = json.loads(json_match.group())
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON: {e}")
    
    # Validation des champs requis
    if "approve" not in parsed or not isinstance(parsed["approve"], bool):
        raise ValueError("Missing or invalid 'approve' field (must be boolean)")
    
    if "reasoning" not in parsed or not isinstance(parsed["reasoning"], str):
        raise ValueError("Missing or invalid 'reasoning' field")
    
    # Valeurs par défaut pour champs optionnels
    parsed.setdefault("confidence", 0.5)
    parsed.setdefault("risks_identified", [])
    
    return parsed


# ═══════════════════════════════════════════════════════════════════════════════
# HELPER FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════════

def generate_decision_hash(action: str, context: Dict[str, Any]) -> str:
    """Génère un hash unique pour une décision."""
    data = json.dumps({
        "action": action,
        "context": context,
        "ts": time.time()
    }, sort_keys=True)
    return hashlib.sha256(data.encode()).hexdigest()


def estimate_risk_level(action: str, context: Dict[str, Any] = None) -> float:
    """
    Estime le niveau de risque d'une action.
    
    Returns:
        Float entre 0.0 (faible risque) et 1.0 (haut risque)
    """
    high_risk_patterns = [
        "delete", "remove", "admin", "system", "config",
        "execute", "deploy", "shutdown", "terminate"
    ]
    medium_risk_patterns = [
        "update", "modify", "transfer", "send", "publish",
        "conclusion", "recommendation", "decision"
    ]
    
    action_lower = action.lower()
    
    if any(p in action_lower for p in high_risk_patterns):
        return 0.8
    if any(p in action_lower for p in medium_risk_patterns):
        return 0.5
    return 0.2


def is_critical_action(action: str) -> bool:
    """Vérifie si une action nécessite validation par consensus."""
    critical_patterns = [
        "delete", "remove", "execute", "transfer",
        "payment", "admin", "system", "config",
        "deploy", "shutdown", "terminate",
        "conclusion", "recommendation", "publish",
        "validate", "approve", "final"
    ]
    return any(p in action.lower() for p in critical_patterns)
