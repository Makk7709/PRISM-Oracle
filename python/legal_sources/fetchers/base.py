"""
Legal Sources — Base Fetcher

Classes de base pour le téléchargement avec authentification PISTE.
"""

import hashlib
import json
import logging
import time
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Generator, List, Optional

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from ..config import LegalSourcesConfig
from ..models import LegalDoc, LegalSource, Provenance

logger = logging.getLogger("legal_sources.fetcher")


class PisteAuthMixin:
    """
    Mixin pour l'authentification OAuth2 sur le portail PISTE.
    
    https://piste.gouv.fr
    """
    
    _access_token: Optional[str] = None
    _token_expires_at: float = 0
    
    def __init__(self, config: LegalSourcesConfig):
        self.config = config
        self._session: Optional[requests.Session] = None
    
    def _get_session(self) -> requests.Session:
        """Crée une session HTTP avec retry."""
        if self._session is None:
            self._session = requests.Session()
            
            # Configuration retry
            retry_strategy = Retry(
                total=self.config.retry_max,
                backoff_factor=self.config.retry_delay,
                status_forcelist=[429, 500, 502, 503, 504],
            )
            adapter = HTTPAdapter(max_retries=retry_strategy)
            self._session.mount("http://", adapter)
            self._session.mount("https://", adapter)
        
        return self._session
    
    def _authenticate(self) -> str:
        """
        Obtient un token OAuth2 depuis PISTE.
        
        Returns:
            Access token valide
        
        Raises:
            ValueError: Si credentials manquants
            requests.HTTPError: Si authentification échoue
        """
        if not self.config.has_piste_credentials:
            raise ValueError(
                "PISTE credentials not configured. "
                "Set PISTE_CLIENT_ID and PISTE_CLIENT_SECRET environment variables."
            )
        
        # Vérifier si token encore valide
        if self._access_token and time.time() < self._token_expires_at - 60:
            return self._access_token
        
        logger.info("Obtaining PISTE OAuth2 token...")
        
        response = self._get_session().post(
            self.config.piste_token_url,
            data={
                "grant_type": "client_credentials",
                "client_id": self.config.piste_client_id,
                "client_secret": self.config.piste_client_secret,
                "scope": "openid",
            },
            timeout=self.config.request_timeout,
        )
        response.raise_for_status()
        
        data = response.json()
        self._access_token = data["access_token"]
        self._token_expires_at = time.time() + data.get("expires_in", 3600)
        
        logger.info("PISTE authentication successful")
        return self._access_token
    
    def _get_auth_headers(self) -> Dict[str, str]:
        """Retourne les headers d'authentification."""
        token = self._authenticate()
        return {
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
        }


class BaseFetcher(ABC, PisteAuthMixin):
    """
    Classe de base pour les fetchers de données juridiques.
    
    Fournit:
    - Authentification PISTE
    - Gestion du cache
    - Logging structuré
    - Checksum pour intégrité
    """
    
    source: LegalSource  # À définir dans les sous-classes
    
    def __init__(self, config: LegalSourcesConfig):
        super().__init__(config)
        self.config = config
    
    @abstractmethod
    def fetch(
        self,
        since: Optional[datetime] = None,
        limit: Optional[int] = None,
    ) -> Generator[Dict[str, Any], None, None]:
        """
        Récupère les documents depuis la source.
        
        Args:
            since: Date minimum (filtrer les documents récents)
            limit: Nombre maximum de documents
        
        Yields:
            Dict brut de chaque document
        """
        pass
    
    @abstractmethod
    def parse(self, raw_data: Dict[str, Any]) -> Optional[LegalDoc]:
        """
        Parse un document brut en LegalDoc.
        
        Args:
            raw_data: Données brutes de l'API
        
        Returns:
            LegalDoc parsé ou None si invalide
        """
        pass
    
    def fetch_and_parse(
        self,
        since: Optional[datetime] = None,
        limit: Optional[int] = None,
    ) -> Generator[LegalDoc, None, None]:
        """
        Récupère et parse les documents.
        
        Yields:
            LegalDoc parsés
        """
        for raw in self.fetch(since=since, limit=limit):
            doc = self.parse(raw)
            if doc:
                yield doc
    
    def _compute_hash(self, data: bytes) -> str:
        """Calcule le hash SHA256 d'un contenu."""
        return hashlib.sha256(data).hexdigest()
    
    def _cache_path(self, key: str) -> Path:
        """Retourne le chemin de cache pour une clé."""
        hash_key = hashlib.sha256(key.encode()).hexdigest()[:16]
        return self.config.cache_dir / f"{self.source.value}_{hash_key}.json"
    
    def _get_cached(self, key: str) -> Optional[Dict]:
        """Récupère une entrée du cache."""
        cache_file = self._cache_path(key)
        if cache_file.exists():
            try:
                with open(cache_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                pass
        return None
    
    def _set_cached(self, key: str, data: Dict) -> None:
        """Stocke une entrée dans le cache."""
        cache_file = self._cache_path(key)
        cache_file.parent.mkdir(parents=True, exist_ok=True)
        with open(cache_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def _create_provenance(
        self,
        origin_id: str,
        origin_url: Optional[str] = None,
        content_hash: Optional[str] = None,
    ) -> Provenance:
        """Crée un objet Provenance pour ce fetcher."""
        from ..config import SOURCE_PRODUCERS
        
        return Provenance(
            source=self.source,
            source_name=SOURCE_PRODUCERS.get(self.source.value, "Unknown"),
            origin_id=origin_id,
            origin_url=origin_url,
            retrieved_at=datetime.utcnow(),
            content_hash=content_hash,
        )
    
    def _log_fetch(self, message: str, **kwargs) -> None:
        """Log structuré pour les opérations de fetch."""
        extra = {
            "source": self.source.value,
            "timestamp": datetime.utcnow().isoformat(),
            **kwargs,
        }
        if self.config.log_format == "json":
            logger.info(json.dumps({"message": message, **extra}))
        else:
            logger.info(f"[{self.source.value}] {message} | {kwargs}")
