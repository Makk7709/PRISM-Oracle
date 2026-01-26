"""
Router Metrics — Production Observability

Collecte de métriques exploitables pour audit et enforcement.

Métriques collectées:
- router_divergence_rate: Divergences LLM vs Router par intent
- router_error_rate: Erreurs du router (avec rate-limit)
- router_would_block: Cas où router aurait bloqué mais exécution continue
- router_latency_ms: Temps de décision

Usage:
    from python.helpers.router.metrics import RouterMetrics
    
    metrics = RouterMetrics.get_instance()
    metrics.record_decision(route_decision, llm_profile, was_blocked=False)
    metrics.record_error(error, input_hash)
    
    # Export stats
    stats = metrics.get_stats()
"""

import hashlib
import logging
import threading
import time
from collections import deque
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set
from datetime import datetime, timedelta

logger = logging.getLogger("router_metrics")


@dataclass
class DivergenceSample:
    """Échantillon de divergence (hashé, pas de PII)."""
    input_hash: str
    llm_profile: str
    router_intents: List[str]
    router_verdict: str
    is_board_level: bool
    timestamp: float = field(default_factory=time.time)


@dataclass
class RouterStats:
    """Statistiques agrégées du router."""
    # Compteurs globaux
    total_decisions: int = 0
    total_divergences: int = 0
    total_errors: int = 0
    total_would_block: int = 0
    
    # Par intent
    divergence_by_intent: Dict[str, int] = field(default_factory=dict)
    decisions_by_intent: Dict[str, int] = field(default_factory=dict)
    
    # Latence
    avg_latency_ms: float = 0.0
    max_latency_ms: float = 0.0
    
    # Périodes
    window_start: float = 0.0
    window_end: float = 0.0
    
    def divergence_rate(self, intent: Optional[str] = None) -> float:
        """Taux de divergence global ou par intent."""
        if intent:
            decisions = self.decisions_by_intent.get(intent, 0)
            divergences = self.divergence_by_intent.get(intent, 0)
            return divergences / decisions if decisions > 0 else 0.0
        return self.total_divergences / self.total_decisions if self.total_decisions > 0 else 0.0
    
    def error_rate(self) -> float:
        """Taux d'erreur."""
        total = self.total_decisions + self.total_errors
        return self.total_errors / total if total > 0 else 0.0
    
    def to_dict(self) -> Dict:
        """Export pour logging/monitoring."""
        return {
            "total_decisions": self.total_decisions,
            "total_divergences": self.total_divergences,
            "total_errors": self.total_errors,
            "total_would_block": self.total_would_block,
            "divergence_rate": round(self.divergence_rate(), 4),
            "error_rate": round(self.error_rate(), 4),
            "avg_latency_ms": round(self.avg_latency_ms, 2),
            "max_latency_ms": round(self.max_latency_ms, 2),
            "divergence_by_intent": {
                k: round(self.divergence_rate(k), 4) 
                for k in self.decisions_by_intent.keys()
            },
            "window_hours": round((self.window_end - self.window_start) / 3600, 2),
        }


class RouterMetrics:
    """
    Singleton de métriques pour le router déterministe.
    
    Thread-safe, avec rate-limiting des erreurs et échantillonnage des divergences.
    """
    
    _instance: Optional["RouterMetrics"] = None
    _lock = threading.Lock()
    
    # Configuration
    MAX_DIVERGENCE_SAMPLES = 20  # Derniers prompts divergents
    ERROR_RATE_LIMIT_SECONDS = 60  # Rate-limit erreurs identiques
    STATS_WINDOW_HOURS = 24  # Fenêtre de stats
    
    def __init__(self):
        self._decisions_lock = threading.Lock()
        
        # Compteurs
        self._total_decisions = 0
        self._total_divergences = 0
        self._total_errors = 0
        self._total_would_block = 0
        
        # Par intent
        self._divergence_by_intent: Dict[str, int] = {}
        self._decisions_by_intent: Dict[str, int] = {}
        
        # Latence
        self._latencies: deque = deque(maxlen=1000)
        
        # Échantillonnage divergences (hashé)
        self._divergence_samples: deque = deque(maxlen=self.MAX_DIVERGENCE_SAMPLES)
        
        # Rate-limit erreurs
        self._error_hashes: Dict[str, float] = {}  # hash -> last_logged_time
        
        # Timestamps
        self._window_start = time.time()
    
    @classmethod
    def get_instance(cls) -> "RouterMetrics":
        """Singleton thread-safe."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance
    
    @classmethod
    def reset(cls) -> None:
        """Reset pour tests."""
        with cls._lock:
            cls._instance = None
    
    def record_decision(
        self,
        route_id: str,
        input_hash: str,
        router_verdict: str,
        router_intents: List[str],
        is_board_level: bool,
        llm_profile: str,
        latency_ms: float,
        execution_blocked: bool = False,
    ) -> None:
        """
        Enregistre une décision de routage.
        
        Args:
            route_id: ID de la route
            input_hash: Hash du prompt (pas de PII)
            router_verdict: proceed/needs_clarification/refuse
            router_intents: Liste des intents détectés
            is_board_level: Si board-level
            llm_profile: Profil choisi par le LLM
            latency_ms: Temps de décision en ms
            execution_blocked: Si l'exécution a été bloquée (enforcement mode)
        """
        with self._decisions_lock:
            self._total_decisions += 1
            
            # Latence
            self._latencies.append(latency_ms)
            
            # Par intent (primary)
            primary_intent = router_intents[0] if router_intents else "none"
            self._decisions_by_intent[primary_intent] = \
                self._decisions_by_intent.get(primary_intent, 0) + 1
            
            # Détection divergence
            intent_to_profile = {
                "finance": "finance",
                "sales": "sales",
                "legal_safe": "legal_safe",
                "medical": "medical",
                "developer": "developer",
                "researcher": "researcher",
                "marketing": "marketing",
                "multitask": "default",
                "contradictor": "default",
            }
            
            router_profiles = [
                intent_to_profile.get(i, i) for i in router_intents
            ]
            
            is_divergent = llm_profile and llm_profile not in router_profiles
            
            if is_divergent:
                self._total_divergences += 1
                self._divergence_by_intent[primary_intent] = \
                    self._divergence_by_intent.get(primary_intent, 0) + 1
                
                # Échantillonner (hashé)
                sample = DivergenceSample(
                    input_hash=input_hash,
                    llm_profile=llm_profile,
                    router_intents=router_intents,
                    router_verdict=router_verdict,
                    is_board_level=is_board_level,
                )
                self._divergence_samples.append(sample)
                
                logger.warning(
                    f"[ROUTER_METRICS] DIVERGENCE | route={route_id} | "
                    f"llm={llm_profile} | router={router_intents} | "
                    f"board={is_board_level}"
                )
            
            # Router would block
            if router_verdict in ("needs_clarification", "refuse") and not execution_blocked:
                self._total_would_block += 1
                logger.warning(
                    f"[ROUTER_METRICS] WOULD_BLOCK | route={route_id} | "
                    f"verdict={router_verdict} | llm={llm_profile} | "
                    f"board={is_board_level} | execution_continued=True"
                )
    
    def record_error(self, error: Exception, input_hash: str) -> bool:
        """
        Enregistre une erreur avec rate-limiting.
        
        Returns:
            True si l'erreur a été loggée, False si rate-limited
        """
        with self._decisions_lock:
            self._total_errors += 1
            
            # Rate-limit par type d'erreur
            error_key = f"{type(error).__name__}:{str(error)[:50]}"
            error_hash = hashlib.sha256(error_key.encode()).hexdigest()[:8]
            
            now = time.time()
            last_logged = self._error_hashes.get(error_hash, 0)
            
            if now - last_logged > self.ERROR_RATE_LIMIT_SECONDS:
                self._error_hashes[error_hash] = now
                
                # Cleanup old hashes
                cutoff = now - self.ERROR_RATE_LIMIT_SECONDS * 10
                self._error_hashes = {
                    k: v for k, v in self._error_hashes.items() 
                    if v > cutoff
                }
                
                logger.error(
                    f"[ROUTER_METRICS] ERROR | hash={error_hash} | "
                    f"input={input_hash} | error={error}"
                )
                return True
            
            return False  # Rate-limited
    
    def get_stats(self) -> RouterStats:
        """Retourne les stats agrégées."""
        with self._decisions_lock:
            latencies = list(self._latencies)
            
            return RouterStats(
                total_decisions=self._total_decisions,
                total_divergences=self._total_divergences,
                total_errors=self._total_errors,
                total_would_block=self._total_would_block,
                divergence_by_intent=dict(self._divergence_by_intent),
                decisions_by_intent=dict(self._decisions_by_intent),
                avg_latency_ms=sum(latencies) / len(latencies) if latencies else 0.0,
                max_latency_ms=max(latencies) if latencies else 0.0,
                window_start=self._window_start,
                window_end=time.time(),
            )
    
    def get_divergence_samples(self) -> List[DivergenceSample]:
        """Retourne les 20 derniers prompts divergents (hashés)."""
        with self._decisions_lock:
            return list(self._divergence_samples)
    
    def log_summary(self) -> None:
        """Log un résumé des stats (pour cron/rapport)."""
        stats = self.get_stats()
        
        logger.info(
            f"[ROUTER_METRICS] SUMMARY | "
            f"decisions={stats.total_decisions} | "
            f"divergence_rate={stats.divergence_rate():.2%} | "
            f"error_rate={stats.error_rate():.2%} | "
            f"would_block={stats.total_would_block} | "
            f"avg_latency={stats.avg_latency_ms:.2f}ms"
        )
        
        # Log par intent si divergences
        if stats.total_divergences > 0:
            for intent, count in stats.divergence_by_intent.items():
                rate = stats.divergence_rate(intent)
                logger.info(
                    f"[ROUTER_METRICS] INTENT | {intent} | "
                    f"divergence_rate={rate:.2%} ({count}/{stats.decisions_by_intent.get(intent, 0)})"
                )
