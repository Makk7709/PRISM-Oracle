"""
Legal Sources — Resilience Module

Gestion robuste des erreurs réseau, rate limiting, et checkpointing.
"""

import json
import logging
import random
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, Optional, TypeVar

import requests

logger = logging.getLogger("legal_sources.resilience")

T = TypeVar("T")


@dataclass
class RetryConfig:
    """Configuration du retry avec exponential backoff."""
    max_retries: int = 5
    base_delay: float = 1.0  # secondes
    max_delay: float = 60.0  # secondes
    exponential_base: float = 2.0
    jitter: float = 0.1  # 10% de jitter
    
    # Codes HTTP à retry
    retryable_status_codes: tuple = (429, 500, 502, 503, 504)
    
    # Rate limiting
    rate_limit_delay: float = 60.0  # Délai par défaut si pas de Retry-After


@dataclass
class CheckpointData:
    """Données de checkpoint pour reprise."""
    source: str
    cursor: Optional[str] = None
    page: int = 0
    last_doc_id: Optional[str] = None
    last_origin_id: Optional[str] = None
    docs_processed: int = 0
    updated_at: datetime = field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "source": self.source,
            "cursor": self.cursor,
            "page": self.page,
            "last_doc_id": self.last_doc_id,
            "last_origin_id": self.last_origin_id,
            "docs_processed": self.docs_processed,
            "updated_at": self.updated_at.isoformat(),
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CheckpointData":
        return cls(
            source=data["source"],
            cursor=data.get("cursor"),
            page=data.get("page", 0),
            last_doc_id=data.get("last_doc_id"),
            last_origin_id=data.get("last_origin_id"),
            docs_processed=data.get("docs_processed", 0),
            updated_at=datetime.fromisoformat(data["updated_at"]) if data.get("updated_at") else datetime.utcnow(),
        )


class CheckpointManager:
    """
    Gestion des checkpoints pour reprise après crash.
    
    Stocke l'état de pagination dans un fichier JSON.
    Permet de reprendre l'ingestion au dernier point sans duplication.
    """
    
    def __init__(self, checkpoint_dir: Path):
        self.checkpoint_dir = checkpoint_dir
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)
        self._checkpoint_file = checkpoint_dir / "checkpoints.json"
        self._checkpoints: Dict[str, CheckpointData] = {}
        self._load()
    
    def _load(self) -> None:
        """Charge les checkpoints depuis le fichier."""
        if self._checkpoint_file.exists():
            try:
                with open(self._checkpoint_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for source, cp_data in data.items():
                        self._checkpoints[source] = CheckpointData.from_dict(cp_data)
                logger.info(f"Loaded {len(self._checkpoints)} checkpoints")
            except (json.JSONDecodeError, IOError) as e:
                logger.warning(f"Failed to load checkpoints: {e}")
                self._checkpoints = {}
    
    def _save(self) -> None:
        """Persiste les checkpoints."""
        data = {source: cp.to_dict() for source, cp in self._checkpoints.items()}
        with open(self._checkpoint_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    
    def get(self, source: str) -> Optional[CheckpointData]:
        """Récupère le checkpoint pour une source."""
        return self._checkpoints.get(source)
    
    def update(
        self,
        source: str,
        cursor: Optional[str] = None,
        page: int = 0,
        last_doc_id: Optional[str] = None,
        last_origin_id: Optional[str] = None,
        docs_processed: int = 0,
    ) -> None:
        """Met à jour et persiste le checkpoint."""
        self._checkpoints[source] = CheckpointData(
            source=source,
            cursor=cursor,
            page=page,
            last_doc_id=last_doc_id,
            last_origin_id=last_origin_id,
            docs_processed=docs_processed,
            updated_at=datetime.utcnow(),
        )
        self._save()
        
        logger.info(json.dumps({
            "event": "checkpoint_updated",
            "source": source,
            "cursor": cursor,
            "page": page,
            "docs_processed": docs_processed,
        }))
    
    def clear(self, source: str) -> None:
        """Efface le checkpoint pour une source."""
        if source in self._checkpoints:
            del self._checkpoints[source]
            self._save()
            logger.info(f"Cleared checkpoint for {source}")
    
    def clear_all(self) -> None:
        """Efface tous les checkpoints."""
        self._checkpoints = {}
        self._save()


class RateLimiter:
    """
    Gestion du rate limiting avec respect des headers API.
    
    Lit les headers:
    - Retry-After
    - X-RateLimit-Remaining
    - X-RateLimit-Reset
    """
    
    def __init__(self, config: RetryConfig):
        self.config = config
        self._last_request_time: float = 0
        self._min_interval: float = 0.1  # 100ms entre requêtes
    
    def wait_if_needed(self) -> None:
        """Attend si nécessaire pour respecter le rate limit."""
        elapsed = time.time() - self._last_request_time
        if elapsed < self._min_interval:
            time.sleep(self._min_interval - elapsed)
        self._last_request_time = time.time()
    
    def handle_rate_limit(self, response: requests.Response) -> float:
        """
        Gère une réponse 429 et retourne le délai à attendre.
        
        Args:
            response: Réponse HTTP 429
            
        Returns:
            Délai en secondes à attendre
        """
        # Chercher Retry-After
        retry_after = response.headers.get("Retry-After")
        if retry_after:
            try:
                delay = float(retry_after)
                logger.info(json.dumps({
                    "event": "rate_limit_retry_after",
                    "delay_seconds": delay,
                }))
                return delay
            except ValueError:
                pass
        
        # Chercher X-RateLimit-Reset
        reset_time = response.headers.get("X-RateLimit-Reset")
        if reset_time:
            try:
                reset_ts = float(reset_time)
                delay = max(0, reset_ts - time.time())
                logger.info(json.dumps({
                    "event": "rate_limit_reset",
                    "delay_seconds": delay,
                }))
                return delay
            except ValueError:
                pass
        
        # Délai par défaut
        logger.info(json.dumps({
            "event": "rate_limit_default",
            "delay_seconds": self.config.rate_limit_delay,
        }))
        return self.config.rate_limit_delay


def retry_with_backoff(
    func: Callable[[], T],
    config: Optional[RetryConfig] = None,
    on_retry: Optional[Callable[[int, Exception, float], None]] = None,
) -> T:
    """
    Exécute une fonction avec retry et exponential backoff.
    
    Args:
        func: Fonction à exécuter
        config: Configuration du retry
        on_retry: Callback appelé à chaque retry (attempt, exception, delay)
        
    Returns:
        Résultat de la fonction
        
    Raises:
        Exception: Si tous les retries échouent
    """
    config = config or RetryConfig()
    rate_limiter = RateLimiter(config)
    
    last_exception: Optional[Exception] = None
    
    for attempt in range(config.max_retries + 1):
        try:
            rate_limiter.wait_if_needed()
            return func()
            
        except requests.exceptions.HTTPError as e:
            response = e.response
            status_code = response.status_code if response else 0
            
            if status_code not in config.retryable_status_codes:
                raise
            
            last_exception = e
            
            # Calculer le délai
            if status_code == 429:
                delay = rate_limiter.handle_rate_limit(response)
            else:
                # Exponential backoff avec jitter
                delay = min(
                    config.base_delay * (config.exponential_base ** attempt),
                    config.max_delay,
                )
                # Ajouter jitter
                jitter_amount = delay * config.jitter
                delay += random.uniform(-jitter_amount, jitter_amount)
            
            logger.warning(json.dumps({
                "event": "retry_scheduled",
                "attempt": attempt + 1,
                "max_retries": config.max_retries,
                "status_code": status_code,
                "delay_seconds": round(delay, 2),
            }))
            
            if on_retry:
                on_retry(attempt + 1, e, delay)
            
            if attempt < config.max_retries:
                time.sleep(delay)
            
        except requests.exceptions.Timeout as e:
            last_exception = e
            
            delay = min(
                config.base_delay * (config.exponential_base ** attempt),
                config.max_delay,
            )
            
            logger.warning(json.dumps({
                "event": "retry_timeout",
                "attempt": attempt + 1,
                "delay_seconds": round(delay, 2),
            }))
            
            if on_retry:
                on_retry(attempt + 1, e, delay)
            
            if attempt < config.max_retries:
                time.sleep(delay)
            
        except requests.exceptions.ConnectionError as e:
            last_exception = e
            
            delay = min(
                config.base_delay * (config.exponential_base ** attempt),
                config.max_delay,
            )
            
            logger.warning(json.dumps({
                "event": "retry_connection_error",
                "attempt": attempt + 1,
                "delay_seconds": round(delay, 2),
            }))
            
            if on_retry:
                on_retry(attempt + 1, e, delay)
            
            if attempt < config.max_retries:
                time.sleep(delay)
    
    # Tous les retries ont échoué
    logger.error(json.dumps({
        "event": "all_retries_failed",
        "total_attempts": config.max_retries + 1,
        "error": str(last_exception),
    }))
    
    raise last_exception


class ResilientSession:
    """
    Session HTTP résiliente avec retry intégré.
    
    Wrapper autour de requests.Session avec:
    - Retry automatique
    - Rate limiting
    - Logging structuré
    """
    
    def __init__(self, config: Optional[RetryConfig] = None):
        self.config = config or RetryConfig()
        self._session = requests.Session()
        self._total_retries = 0
        self._rate_limited_count = 0
    
    @property
    def total_retries(self) -> int:
        return self._total_retries
    
    @property
    def rate_limited_count(self) -> int:
        return self._rate_limited_count
    
    def _on_retry(self, attempt: int, exc: Exception, delay: float) -> None:
        """Callback pour tracking des retries."""
        self._total_retries += 1
        if isinstance(exc, requests.exceptions.HTTPError):
            if exc.response and exc.response.status_code == 429:
                self._rate_limited_count += 1
    
    def get(
        self,
        url: str,
        params: Optional[Dict] = None,
        headers: Optional[Dict] = None,
        timeout: int = 30,
    ) -> requests.Response:
        """GET avec retry."""
        def _do_get():
            response = self._session.get(
                url,
                params=params,
                headers=headers,
                timeout=timeout,
            )
            response.raise_for_status()
            return response
        
        return retry_with_backoff(
            _do_get,
            config=self.config,
            on_retry=self._on_retry,
        )
    
    def post(
        self,
        url: str,
        data: Optional[Dict] = None,
        json: Optional[Dict] = None,
        headers: Optional[Dict] = None,
        timeout: int = 30,
    ) -> requests.Response:
        """POST avec retry."""
        def _do_post():
            response = self._session.post(
                url,
                data=data,
                json=json,
                headers=headers,
                timeout=timeout,
            )
            response.raise_for_status()
            return response
        
        return retry_with_backoff(
            _do_post,
            config=self.config,
            on_retry=self._on_retry,
        )
    
    def close(self) -> None:
        """Ferme la session."""
        self._session.close()
