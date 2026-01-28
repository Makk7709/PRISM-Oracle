"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                    COLLABORATIVE CONSENSUS — DÉBAT IA                        ║
║                                                                              ║
║  Système de consensus collaboratif où 3 LLMs débattent pour vérifier        ║
║  la fiabilité d'une réponse et détecter les hallucinations.                 ║
║                                                                              ║
║  ARCHITECTURE:                                                               ║
║  ┌─────────────────────────────────────────────────────────────────────┐    ║
║  │  ROUND 1: Analyse indépendante (3 LLMs en parallèle)                │    ║
║  │  - Extraire les claims factuels                                     │    ║
║  │  - Évaluer la vérifiabilité de chaque claim                        │    ║
║  │  - Identifier les potentielles hallucinations                       │    ║
║  └─────────────────────────────────────────────────────────────────────┘    ║
║                              ↓                                               ║
║  ┌─────────────────────────────────────────────────────────────────────┐    ║
║  │  ROUND 2: Débat collaboratif (LLMs voient les analyses des autres)  │    ║
║  │  - Challenger les claims douteux                                    │    ║
║  │  - Argumenter avec sources/logique                                  │    ║
║  │  - Proposer corrections si nécessaire                               │    ║
║  └─────────────────────────────────────────────────────────────────────┘    ║
║                              ↓                                               ║
║  ┌─────────────────────────────────────────────────────────────────────┐    ║
║  │  ROUND 3: Synthèse et verdict (convergence collaborative)           │    ║
║  │  - Points de consensus                                              │    ║
║  │  - Points de désaccord restants                                     │    ║
║  │  - Verdict final avec confiance                                     │    ║
║  └─────────────────────────────────────────────────────────────────────┘    ║
║                                                                              ║
║  TIMEOUTS ÉTENDUS:                                                           ║
║  - Round 1: 15s par LLM (parallèle)                                         ║
║  - Round 2: 20s par LLM (débat)                                             ║
║  - Round 3: 15s (synthèse)                                                  ║
║  - Total max: ~60s pour un débat complet                                    ║
║                                                                              ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import asyncio
import json
import logging
import os
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from python.helpers.print_style import PrintStyle

logger = logging.getLogger("collaborative_consensus")


# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class DebateConfig:
    """Configuration du débat collaboratif."""
    # Timeouts étendus pour collaboration
    round1_timeout_ms: int = 15000   # 15s pour analyse initiale
    round2_timeout_ms: int = 20000   # 20s pour débat
    round3_timeout_ms: int = 15000   # 15s pour synthèse
    total_timeout_ms: int = 60000    # 60s max total
    
    # Quorum pour validation
    quorum_ratio: float = 0.67  # 2/3 minimum
    
    # Seuils de confiance
    high_confidence_threshold: float = 0.8
    low_confidence_threshold: float = 0.5
    
    # Mode
    skip_round2_if_unanimous: bool = True  # Optimisation si tous d'accord


class ClaimVerdict(str, Enum):
    """Verdict sur un claim individuel."""
    VERIFIED = "verified"           # Claim vérifié et correct
    LIKELY_CORRECT = "likely_correct"  # Probablement correct mais non vérifié
    UNCERTAIN = "uncertain"         # Incertain, besoin de plus d'info
    LIKELY_FALSE = "likely_false"   # Probablement faux
    HALLUCINATION = "hallucination" # Hallucination détectée


class DebateVerdict(str, Enum):
    """Verdict final du débat."""
    APPROVED = "approved"           # Réponse fiable
    APPROVED_WITH_CAVEATS = "approved_with_caveats"  # OK avec réserves
    NEEDS_REVISION = "needs_revision"  # Doit être modifiée
    REJECTED = "rejected"           # Contient des hallucinations


# ═══════════════════════════════════════════════════════════════════════════════
# DATA STRUCTURES
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class ExtractedClaim:
    """Un claim factuel extrait de la réponse."""
    claim_id: str
    text: str
    source_mentioned: Optional[str] = None  # Source citée dans la réponse
    is_verifiable: bool = True
    confidence: float = 0.5
    verdict: ClaimVerdict = ClaimVerdict.UNCERTAIN


@dataclass
class Round1Analysis:
    """Analyse d'un LLM au Round 1."""
    llm_id: str
    claims_extracted: List[ExtractedClaim]
    potential_hallucinations: List[str]
    overall_confidence: float
    reasoning: str
    timestamp: float = field(default_factory=time.time)


@dataclass
class Round2Argument:
    """Argument d'un LLM au Round 2 (débat)."""
    llm_id: str
    claim_id: str
    position: str  # "agree", "disagree", "uncertain"
    argument: str
    counter_evidence: Optional[str] = None
    suggested_correction: Optional[str] = None
    confidence: float = 0.5


@dataclass
class Round2DebateResult:
    """Résultat du débat Round 2 pour un LLM."""
    llm_id: str
    arguments: List[Round2Argument]
    claims_to_flag: List[str]  # claim_ids douteux
    proposed_revisions: List[str]
    overall_assessment: str
    timestamp: float = field(default_factory=time.time)


@dataclass
class Round3Synthesis:
    """Synthèse finale du débat."""
    consensus_points: List[str]
    disagreement_points: List[str]
    flagged_claims: List[Tuple[str, str]]  # (claim_id, reason)
    final_verdict: DebateVerdict
    confidence: float
    recommended_action: str
    reasoning: str


@dataclass
class CollaborativeConsensusResult:
    """Résultat complet du consensus collaboratif."""
    debate_id: str
    
    # Rounds
    round1_analyses: List[Round1Analysis]
    round2_debates: List[Round2DebateResult]
    round3_synthesis: Round3Synthesis
    
    # Verdict
    approved: bool
    verdict: DebateVerdict
    confidence: float
    
    # Métriques
    total_duration_ms: int
    round1_duration_ms: int
    round2_duration_ms: int
    round3_duration_ms: int
    
    # Claims
    total_claims: int
    verified_claims: int
    flagged_claims: int
    
    timestamp: float = field(default_factory=time.time)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "debate_id": self.debate_id,
            "approved": self.approved,
            "verdict": self.verdict.value,
            "confidence": self.confidence,
            "total_duration_ms": self.total_duration_ms,
            "total_claims": self.total_claims,
            "verified_claims": self.verified_claims,
            "flagged_claims": self.flagged_claims,
            "consensus_points": self.round3_synthesis.consensus_points,
            "disagreement_points": self.round3_synthesis.disagreement_points,
            "recommended_action": self.round3_synthesis.recommended_action,
        }


# ═══════════════════════════════════════════════════════════════════════════════
# PROMPTS POUR DÉBAT COLLABORATIF
# ═══════════════════════════════════════════════════════════════════════════════

ROUND1_PROMPT = """Tu es un expert en vérification de faits et détection d'hallucinations IA.

## Ta mission
Analyser la réponse suivante pour identifier TOUS les claims factuels et évaluer leur fiabilité.

## Réponse à analyser
{response}

## Question originale
{question}

## Instructions
1. EXTRAIS chaque affirmation factuelle (claim) de la réponse
2. Pour chaque claim, évalue:
   - Est-il vérifiable ? (oui/non)
   - Une source est-elle citée ? (laquelle)
   - Quelle est ta confiance ? (0.0-1.0)
   - Y a-t-il un risque d'hallucination ?

3. Identifie les potentielles hallucinations:
   - Affirmations sans source
   - Détails trop précis sans référence
   - Contradictions internes
   - Informations qui semblent inventées

## Format de réponse (JSON uniquement)
{{
  "claims": [
    {{
      "claim_id": "C1",
      "text": "Le claim exact extrait",
      "source_mentioned": "Article X" ou null,
      "is_verifiable": true/false,
      "confidence": 0.0-1.0,
      "hallucination_risk": "low/medium/high"
    }}
  ],
  "potential_hallucinations": [
    "Description de l'hallucination potentielle 1",
    "Description de l'hallucination potentielle 2"
  ],
  "overall_confidence": 0.0-1.0,
  "reasoning": "Explication de ton analyse en 2-3 phrases"
}}

Réponds UNIQUEMENT avec le JSON, sans texte avant ou après."""


ROUND2_PROMPT = """Tu es un expert participant à un débat collaboratif sur la fiabilité d'une réponse IA.

## Contexte
Trois experts IA analysent la même réponse. Tu vas voir les analyses des autres experts et tu dois:
1. Examiner leurs claims identifiés
2. Challenger ceux que tu trouves douteux
3. Proposer des corrections si nécessaire

## Réponse originale analysée
{response}

## Analyses des autres experts

### Expert 1 ({llm1_id})
{llm1_analysis}

### Expert 2 ({llm2_id})
{llm2_analysis}

### Expert 3 ({llm3_id}) 
{llm3_analysis}

## Ta tâche
Pour chaque claim identifié par les autres experts:
- Es-tu D'ACCORD (agree), PAS D'ACCORD (disagree), ou INCERTAIN (uncertain) ?
- Si pas d'accord: donne ton contre-argument avec preuves/logique
- Si tu détectes une hallucination: propose une correction

## Format de réponse (JSON uniquement)
{{
  "arguments": [
    {{
      "claim_id": "C1",
      "position": "agree/disagree/uncertain",
      "argument": "Ton raisonnement",
      "counter_evidence": "Preuve contraire si applicable" ou null,
      "suggested_correction": "Correction proposée" ou null,
      "confidence": 0.0-1.0
    }}
  ],
  "claims_to_flag": ["C2", "C5"],
  "proposed_revisions": [
    "Révision suggérée pour améliorer la fiabilité"
  ],
  "overall_assessment": "Évaluation globale en 1-2 phrases"
}}

Réponds UNIQUEMENT avec le JSON."""


ROUND3_PROMPT = """Tu es le modérateur final d'un débat IA sur la fiabilité d'une réponse.

## Réponse originale
{response}

## Résumé du débat

### Round 1 - Analyses initiales
{round1_summary}

### Round 2 - Débat et arguments
{round2_summary}

## Ta mission
Synthétise le débat et donne un verdict final:
1. Quels points font CONSENSUS entre les experts ?
2. Quels points restent en DÉSACCORD ?
3. Quels claims sont FLAGGUÉS comme potentiellement faux ?
4. Quel est le VERDICT FINAL ?

## Verdicts possibles
- "approved": Réponse fiable, pas d'hallucination détectée
- "approved_with_caveats": OK mais avec réserves sur certains points
- "needs_revision": Contient des erreurs qui doivent être corrigées
- "rejected": Contient des hallucinations significatives

## Format de réponse (JSON uniquement)
{{
  "consensus_points": [
    "Point 1 où tous les experts sont d'accord",
    "Point 2 de consensus"
  ],
  "disagreement_points": [
    "Point 1 de désaccord",
    "Point 2 de désaccord"
  ],
  "flagged_claims": [
    {{"claim_id": "C3", "reason": "Raison du flag"}},
    {{"claim_id": "C7", "reason": "Raison du flag"}}
  ],
  "final_verdict": "approved/approved_with_caveats/needs_revision/rejected",
  "confidence": 0.0-1.0,
  "recommended_action": "Action recommandée pour l'utilisateur",
  "reasoning": "Explication du verdict en 2-3 phrases"
}}

Réponds UNIQUEMENT avec le JSON."""


# ═══════════════════════════════════════════════════════════════════════════════
# COLLABORATIVE DEBATE ENGINE
# ═══════════════════════════════════════════════════════════════════════════════

class CollaborativeDebateEngine:
    """
    Moteur de débat collaboratif entre LLMs.
    
    Usage:
        engine = CollaborativeDebateEngine()
        result = await engine.run_debate(
            response="La réponse à vérifier...",
            question="La question originale..."
        )
        
        if result.approved:
            # Réponse fiable
        else:
            # Contient des hallucinations
    """
    
    def __init__(self, config: DebateConfig = None):
        self.config = config or DebateConfig()
        self._llm_provider = None
        self._load_llm_provider()
    
    def _load_llm_provider(self):
        """Charge le provider LLM."""
        try:
            from python.helpers import llm_provider
            self._llm_provider = llm_provider
            logger.info("✅ LLM provider loaded for collaborative debate")
        except ImportError as e:
            logger.error(f"❌ Failed to load LLM provider: {e}")
            self._llm_provider = None
    
    def _load_arbiters_from_ui(self) -> List[Tuple[str, str]]:
        """
        Charge les arbitres depuis la configuration UI (Agent Config → PRISM Consensus).
        
        Format UI: "openrouter/anthropic/claude-3.5-sonnet"
        Format sortie: [("openrouter", "anthropic/claude-3.5-sonnet"), ...]
        """
        arbiters = []
        
        try:
            # Charger les settings depuis l'UI
            from python.helpers import settings as _settings
            settings = _settings.get_settings()
            
            # Lire les 3 arbitres configurés dans l'UI
            arbiter_keys = [
                "consensus_arbiter_1",
                "consensus_arbiter_2", 
                "consensus_arbiter_3",
            ]
            
            for key in arbiter_keys:
                arbiter_str = settings.get(key, "")
                if arbiter_str:
                    parsed = self._parse_arbiter_string(arbiter_str)
                    if parsed:
                        arbiters.append(parsed)
            
            if arbiters:
                PrintStyle(font_color="cyan").print(
                    f"   🎯 Arbiters from UI config: {[f'{p}/{m}' for p, m in arbiters]}"
                )
            else:
                logger.warning("No arbiters in UI config, using defaults")
                
        except Exception as e:
            logger.warning(f"Failed to load UI arbiters: {e}, using defaults")
        
        # Fallback aux défauts si rien de configuré
        if not arbiters:
            arbiters = [
                ("openrouter", "openai/gpt-5.2"),
                ("openrouter", "google/gemini-3-pro-preview"),
                ("openrouter", "perplexity/sonar-reasoning-pro"),
            ]
            PrintStyle(font_color="yellow").print(
                f"   ⚠️ Using default arbiters: {[f'{p}/{m}' for p, m in arbiters]}"
            )
        
        return arbiters
    
    def _parse_arbiter_string(self, arbiter_str: str) -> Optional[Tuple[str, str]]:
        """
        Parse une chaîne arbiter du format UI.
        
        Formats supportés:
        - "openrouter/anthropic/claude-3.5-sonnet" → ("openrouter", "anthropic/claude-3.5-sonnet")
        - "anthropic/claude-3.5-sonnet" → ("openrouter", "anthropic/claude-3.5-sonnet")  # default provider
        """
        if not arbiter_str or arbiter_str.strip() == "":
            return None
        
        parts = arbiter_str.split("/", 1)
        
        if len(parts) == 1:
            # Pas de provider → défaut openrouter
            return ("openrouter", arbiter_str)
        
        provider = parts[0].lower()
        model = parts[1]
        
        # Si provider est un provider connu, l'utiliser
        known_providers = ["openrouter", "openai", "anthropic", "google", "ollama"]
        if provider in known_providers:
            return (provider, model)
        
        # Sinon, c'est probablement openrouter/provider/model
        # Donc provider = openrouter, model = parts[0]/parts[1]
        return ("openrouter", arbiter_str)
    
    async def run_debate(
        self,
        response: str,
        question: str,
        correlation_id: str = None,
        arbiters: List[Tuple[str, str]] = None,  # [(provider, model), ...]
    ) -> CollaborativeConsensusResult:
        """
        Lance un débat collaboratif complet.
        
        Args:
            response: La réponse à vérifier
            question: La question originale
            correlation_id: ID de corrélation
            arbiters: Liste des arbitres [(provider, model), ...]
            
        Returns:
            CollaborativeConsensusResult
        """
        debate_id = correlation_id or str(uuid.uuid4())[:8]
        start_time = time.time()
        
        # Charger arbitres depuis config UI ou utiliser défauts
        if arbiters is None:
            arbiters = self._load_arbiters_from_ui()
        
        PrintStyle(font_color="magenta", bold=True).print(
            f"🎭 COLLABORATIVE DEBATE START [{debate_id}]"
        )
        PrintStyle(font_color="cyan").print(
            f"   Arbiters: {[f'{p}/{m}' for p, m in arbiters]}"
        )
        
        # ═══════════════════════════════════════════════════════════════════
        # ROUND 1: Analyse indépendante (en parallèle)
        # ═══════════════════════════════════════════════════════════════════
        
        PrintStyle(font_color="yellow", bold=True).print(
            f"\n📋 ROUND 1: Analyse indépendante..."
        )
        
        round1_start = time.time()
        round1_analyses = await self._run_round1(
            response=response,
            question=question,
            arbiters=arbiters,
            debate_id=debate_id,
        )
        round1_duration = int((time.time() - round1_start) * 1000)
        
        PrintStyle(font_color="green").print(
            f"   ✅ Round 1 complete: {len(round1_analyses)} analyses, {round1_duration}ms"
        )
        
        # Check si unanimité → skip Round 2
        if self.config.skip_round2_if_unanimous and self._is_unanimous(round1_analyses):
            PrintStyle(font_color="green", bold=True).print(
                f"   🎉 Unanimité détectée - Skip Round 2"
            )
            round2_debates = []
            round2_duration = 0
        else:
            # ═══════════════════════════════════════════════════════════════
            # ROUND 2: Débat collaboratif
            # ═══════════════════════════════════════════════════════════════
            
            PrintStyle(font_color="yellow", bold=True).print(
                f"\n💬 ROUND 2: Débat collaboratif..."
            )
            
            round2_start = time.time()
            round2_debates = await self._run_round2(
                response=response,
                round1_analyses=round1_analyses,
                arbiters=arbiters,
                debate_id=debate_id,
            )
            round2_duration = int((time.time() - round2_start) * 1000)
            
            PrintStyle(font_color="green").print(
                f"   ✅ Round 2 complete: {len(round2_debates)} debates, {round2_duration}ms"
            )
        
        # ═══════════════════════════════════════════════════════════════════
        # ROUND 3: Synthèse finale
        # ═══════════════════════════════════════════════════════════════════
        
        PrintStyle(font_color="yellow", bold=True).print(
            f"\n🔮 ROUND 3: Synthèse et verdict..."
        )
        
        round3_start = time.time()
        synthesis = await self._run_round3(
            response=response,
            round1_analyses=round1_analyses,
            round2_debates=round2_debates,
            arbiters=arbiters,
            debate_id=debate_id,
        )
        round3_duration = int((time.time() - round3_start) * 1000)
        
        PrintStyle(font_color="green").print(
            f"   ✅ Round 3 complete: {round3_duration}ms"
        )
        
        # ═══════════════════════════════════════════════════════════════════
        # BUILD RESULT
        # ═══════════════════════════════════════════════════════════════════
        
        total_duration = int((time.time() - start_time) * 1000)
        
        # Compter les claims
        total_claims = sum(len(a.claims_extracted) for a in round1_analyses)
        verified_claims = sum(
            1 for a in round1_analyses 
            for c in a.claims_extracted 
            if c.confidence >= self.config.high_confidence_threshold
        )
        flagged_claims = len(synthesis.flagged_claims)
        
        result = CollaborativeConsensusResult(
            debate_id=debate_id,
            round1_analyses=round1_analyses,
            round2_debates=round2_debates,
            round3_synthesis=synthesis,
            approved=synthesis.final_verdict in (DebateVerdict.APPROVED, DebateVerdict.APPROVED_WITH_CAVEATS),
            verdict=synthesis.final_verdict,
            confidence=synthesis.confidence,
            total_duration_ms=total_duration,
            round1_duration_ms=round1_duration,
            round2_duration_ms=round2_duration,
            round3_duration_ms=round3_duration,
            total_claims=total_claims,
            verified_claims=verified_claims,
            flagged_claims=flagged_claims,
        )
        
        # Log final
        PrintStyle(font_color="magenta", bold=True).print(
            f"\n🎭 COLLABORATIVE DEBATE COMPLETE [{debate_id}]"
        )
        PrintStyle(font_color="cyan").print(
            f"   Verdict: {synthesis.final_verdict.value}"
        )
        PrintStyle(font_color="cyan").print(
            f"   Confidence: {synthesis.confidence:.0%}"
        )
        PrintStyle(font_color="cyan").print(
            f"   Claims: {verified_claims}/{total_claims} verified, {flagged_claims} flagged"
        )
        PrintStyle(font_color="cyan").print(
            f"   Duration: {total_duration}ms (R1:{round1_duration}ms, R2:{round2_duration}ms, R3:{round3_duration}ms)"
        )
        
        return result
    
    async def _run_round1(
        self,
        response: str,
        question: str,
        arbiters: List[Tuple[str, str]],
        debate_id: str,
    ) -> List[Round1Analysis]:
        """Exécute le Round 1 (analyses indépendantes en parallèle)."""
        
        prompt = ROUND1_PROMPT.format(
            response=response,
            question=question,
        )
        
        # Lancer les 3 LLMs en parallèle
        tasks = []
        for provider, model in arbiters:
            task = self._call_llm_with_timeout(
                provider=provider,
                model=model,
                prompt=prompt,
                timeout_ms=self.config.round1_timeout_ms,
            )
            tasks.append((f"{provider}/{model}", task))
        
        # Attendre les résultats
        analyses = []
        results = await asyncio.gather(*[t[1] for t in tasks], return_exceptions=True)
        
        for i, (llm_id, _) in enumerate(tasks):
            result = results[i]
            
            if isinstance(result, Exception):
                logger.error(f"Round 1 error for {llm_id}: {result}")
                continue
            
            try:
                parsed = self._parse_json_response(result)
                
                claims = []
                for c in parsed.get("claims", []):
                    claims.append(ExtractedClaim(
                        claim_id=c.get("claim_id", f"C{len(claims)+1}"),
                        text=c.get("text", ""),
                        source_mentioned=c.get("source_mentioned"),
                        is_verifiable=c.get("is_verifiable", True),
                        confidence=c.get("confidence", 0.5),
                    ))
                
                analyses.append(Round1Analysis(
                    llm_id=llm_id,
                    claims_extracted=claims,
                    potential_hallucinations=parsed.get("potential_hallucinations", []),
                    overall_confidence=parsed.get("overall_confidence", 0.5),
                    reasoning=parsed.get("reasoning", ""),
                ))
                
                PrintStyle(font_color="green").print(
                    f"   {llm_id}: {len(claims)} claims, confidence={parsed.get('overall_confidence', 0.5):.0%}"
                )
                
            except Exception as e:
                logger.error(f"Failed to parse Round 1 response from {llm_id}: {e}")
        
        return analyses
    
    async def _run_round2(
        self,
        response: str,
        round1_analyses: List[Round1Analysis],
        arbiters: List[Tuple[str, str]],
        debate_id: str,
    ) -> List[Round2DebateResult]:
        """Exécute le Round 2 (débat collaboratif)."""
        
        # Préparer les analyses pour le prompt
        analyses_by_llm = {a.llm_id: a for a in round1_analyses}
        llm_ids = list(analyses_by_llm.keys())
        
        # Pour chaque LLM, construire un prompt avec les analyses des autres
        debates = []
        tasks = []
        
        for provider, model in arbiters:
            llm_id = f"{provider}/{model}"
            
            # Préparer les analyses des autres LLMs
            other_analyses = {}
            for other_id, analysis in analyses_by_llm.items():
                other_analyses[other_id] = json.dumps({
                    "claims": [{"claim_id": c.claim_id, "text": c.text, "confidence": c.confidence} 
                              for c in analysis.claims_extracted],
                    "potential_hallucinations": analysis.potential_hallucinations,
                    "overall_confidence": analysis.overall_confidence,
                    "reasoning": analysis.reasoning,
                }, indent=2, ensure_ascii=False)
            
            # Remplir le prompt
            prompt = ROUND2_PROMPT.format(
                response=response,
                llm1_id=llm_ids[0] if len(llm_ids) > 0 else "Expert 1",
                llm1_analysis=other_analyses.get(llm_ids[0], "{}") if len(llm_ids) > 0 else "{}",
                llm2_id=llm_ids[1] if len(llm_ids) > 1 else "Expert 2",
                llm2_analysis=other_analyses.get(llm_ids[1], "{}") if len(llm_ids) > 1 else "{}",
                llm3_id=llm_ids[2] if len(llm_ids) > 2 else "Expert 3",
                llm3_analysis=other_analyses.get(llm_ids[2], "{}") if len(llm_ids) > 2 else "{}",
            )
            
            task = self._call_llm_with_timeout(
                provider=provider,
                model=model,
                prompt=prompt,
                timeout_ms=self.config.round2_timeout_ms,
            )
            tasks.append((llm_id, task))
        
        # Attendre les résultats
        results = await asyncio.gather(*[t[1] for t in tasks], return_exceptions=True)
        
        for i, (llm_id, _) in enumerate(tasks):
            result = results[i]
            
            if isinstance(result, Exception):
                logger.error(f"Round 2 error for {llm_id}: {result}")
                continue
            
            try:
                parsed = self._parse_json_response(result)
                
                arguments = []
                for arg in parsed.get("arguments", []):
                    arguments.append(Round2Argument(
                        llm_id=llm_id,
                        claim_id=arg.get("claim_id", ""),
                        position=arg.get("position", "uncertain"),
                        argument=arg.get("argument", ""),
                        counter_evidence=arg.get("counter_evidence"),
                        suggested_correction=arg.get("suggested_correction"),
                        confidence=arg.get("confidence", 0.5),
                    ))
                
                debates.append(Round2DebateResult(
                    llm_id=llm_id,
                    arguments=arguments,
                    claims_to_flag=parsed.get("claims_to_flag", []),
                    proposed_revisions=parsed.get("proposed_revisions", []),
                    overall_assessment=parsed.get("overall_assessment", ""),
                ))
                
                flagged = len(parsed.get("claims_to_flag", []))
                PrintStyle(font_color="green").print(
                    f"   {llm_id}: {len(arguments)} arguments, {flagged} claims flagged"
                )
                
            except Exception as e:
                logger.error(f"Failed to parse Round 2 response from {llm_id}: {e}")
        
        return debates
    
    async def _run_round3(
        self,
        response: str,
        round1_analyses: List[Round1Analysis],
        round2_debates: List[Round2DebateResult],
        arbiters: List[Tuple[str, str]],
        debate_id: str,
    ) -> Round3Synthesis:
        """Exécute le Round 3 (synthèse finale)."""
        
        # Préparer le résumé du Round 1
        round1_summary = "\n".join([
            f"**{a.llm_id}**: {len(a.claims_extracted)} claims, "
            f"confidence={a.overall_confidence:.0%}, "
            f"hallucinations={len(a.potential_hallucinations)}"
            for a in round1_analyses
        ])
        
        # Préparer le résumé du Round 2
        if round2_debates:
            round2_summary = "\n".join([
                f"**{d.llm_id}**: {len(d.claims_to_flag)} claims flagged, "
                f"assessment: {d.overall_assessment[:100]}..."
                for d in round2_debates
            ])
        else:
            round2_summary = "(Round 2 skipped - unanimous agreement in Round 1)"
        
        prompt = ROUND3_PROMPT.format(
            response=response,
            round1_summary=round1_summary,
            round2_summary=round2_summary,
        )
        
        # Utiliser le premier arbitre pour la synthèse
        provider, model = arbiters[0]
        
        try:
            result = await self._call_llm_with_timeout(
                provider=provider,
                model=model,
                prompt=prompt,
                timeout_ms=self.config.round3_timeout_ms,
            )
            
            parsed = self._parse_json_response(result)
            
            # Parser les flagged claims
            flagged_claims = []
            for fc in parsed.get("flagged_claims", []):
                if isinstance(fc, dict):
                    flagged_claims.append((fc.get("claim_id", ""), fc.get("reason", "")))
                elif isinstance(fc, str):
                    flagged_claims.append((fc, ""))
            
            return Round3Synthesis(
                consensus_points=parsed.get("consensus_points", []),
                disagreement_points=parsed.get("disagreement_points", []),
                flagged_claims=flagged_claims,
                final_verdict=DebateVerdict(parsed.get("final_verdict", "approved_with_caveats")),
                confidence=parsed.get("confidence", 0.5),
                recommended_action=parsed.get("recommended_action", ""),
                reasoning=parsed.get("reasoning", ""),
            )
            
        except Exception as e:
            logger.error(f"Round 3 synthesis failed: {e}")
            # Fallback basé sur Round 1
            avg_confidence = sum(a.overall_confidence for a in round1_analyses) / len(round1_analyses) if round1_analyses else 0.5
            total_hallucinations = sum(len(a.potential_hallucinations) for a in round1_analyses)
            
            if total_hallucinations == 0 and avg_confidence >= 0.7:
                verdict = DebateVerdict.APPROVED
            elif total_hallucinations <= 1:
                verdict = DebateVerdict.APPROVED_WITH_CAVEATS
            else:
                verdict = DebateVerdict.NEEDS_REVISION
            
            return Round3Synthesis(
                consensus_points=[],
                disagreement_points=[],
                flagged_claims=[],
                final_verdict=verdict,
                confidence=avg_confidence,
                recommended_action="Vérifier manuellement les sources citées",
                reasoning=f"Synthèse automatique (erreur Round 3): {e}",
            )
    
    async def _call_llm_with_timeout(
        self,
        provider: str,
        model: str,
        prompt: str,
        timeout_ms: int,
    ) -> str:
        """Appelle un LLM avec timeout."""
        if self._llm_provider is None:
            raise RuntimeError("LLM provider not available")
        
        try:
            llm = self._llm_provider.get_provider(provider, model)
            
            response = await asyncio.wait_for(
                llm.generate(
                    prompt=prompt,
                    temperature=0.1,  # Faible température pour cohérence
                    max_tokens=2000,
                ),
                timeout=timeout_ms / 1000,
            )
            
            return response
            
        except asyncio.TimeoutError:
            raise TimeoutError(f"LLM call timed out after {timeout_ms}ms")
    
    def _parse_json_response(self, response: str) -> Dict[str, Any]:
        """Parse une réponse JSON (gère les code blocks markdown)."""
        text = response.strip()
        
        # Retirer les code blocks markdown
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0]
        elif "```" in text:
            text = text.split("```")[1].split("```")[0]
        
        return json.loads(text.strip())
    
    def _is_unanimous(self, analyses: List[Round1Analysis]) -> bool:
        """Vérifie si les analyses Round 1 sont unanimes."""
        if len(analyses) < 2:
            return True
        
        # Tous à haute confiance et pas d'hallucinations
        all_high_confidence = all(
            a.overall_confidence >= self.config.high_confidence_threshold 
            for a in analyses
        )
        no_hallucinations = all(
            len(a.potential_hallucinations) == 0 
            for a in analyses
        )
        
        return all_high_confidence and no_hallucinations


# ═══════════════════════════════════════════════════════════════════════════════
# SINGLETON & FACTORY
# ═══════════════════════════════════════════════════════════════════════════════

_debate_engine: Optional[CollaborativeDebateEngine] = None


def get_debate_engine(config: DebateConfig = None) -> CollaborativeDebateEngine:
    """Retourne l'instance singleton du moteur de débat."""
    global _debate_engine
    if _debate_engine is None or config is not None:
        _debate_engine = CollaborativeDebateEngine(config)
    return _debate_engine


async def run_collaborative_consensus(
    response: str,
    question: str,
    correlation_id: str = None,
) -> CollaborativeConsensusResult:
    """
    Fonction raccourci pour lancer un débat collaboratif.
    
    Usage:
        result = await run_collaborative_consensus(
            response="La réponse à vérifier...",
            question="La question originale..."
        )
        
        if result.approved:
            # Réponse fiable
        else:
            # Contient des hallucinations potentielles
    """
    engine = get_debate_engine()
    return await engine.run_debate(
        response=response,
        question=question,
        correlation_id=correlation_id,
    )


# ═══════════════════════════════════════════════════════════════════════════════
# EXPORTS
# ═══════════════════════════════════════════════════════════════════════════════

__all__ = [
    # Config
    "DebateConfig",
    "ClaimVerdict",
    "DebateVerdict",
    # Data
    "ExtractedClaim",
    "Round1Analysis",
    "Round2Argument",
    "Round2DebateResult",
    "Round3Synthesis",
    "CollaborativeConsensusResult",
    # Engine
    "CollaborativeDebateEngine",
    "get_debate_engine",
    "run_collaborative_consensus",
]
