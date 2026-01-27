"""
Legal Sources — Judilibre Fetcher

Fetcher pour les arrêts de la Cour de cassation via l'API Judilibre.

API Documentation: https://www.courdecassation.fr/recherche-judilibre
"""

import logging
from datetime import datetime
from typing import Any, Dict, Generator, List, Optional

from ..config import LegalSourcesConfig
from ..models import (
    DocumentType,
    Jurisdiction,
    LegalDoc,
    LegalSource,
    Provenance,
)
from .base import BaseFetcher

logger = logging.getLogger("legal_sources.judilibre")


class JudilibreFetcher(BaseFetcher):
    """
    Fetcher pour l'API Judilibre (Cour de cassation).
    
    Couverture:
    - Cour de cassation: depuis 30/09/2021
    - Juridictions 1er degré (contraventionnel/délictuel): depuis 31/12/2024
    - Cours d'appel: prévu 31/12/2025
    - Matière criminelle: prévu 31/12/2025
    """
    
    source = LegalSource.CASS
    
    def __init__(self, config: LegalSourcesConfig):
        super().__init__(config)
        self.base_url = config.judilibre_base_url
    
    def fetch(
        self,
        since: Optional[datetime] = None,
        limit: Optional[int] = None,
        batch_size: int = 100,
    ) -> Generator[Dict[str, Any], None, None]:
        """
        Récupère les décisions depuis Judilibre.
        
        Args:
            since: Date minimum de décision
            limit: Nombre maximum de décisions
            batch_size: Taille des lots (max 1000)
        
        Yields:
            Dict brut de chaque décision
        """
        self._log_fetch("Starting fetch", since=since.isoformat() if since else None, limit=limit)
        
        session = self._get_session()
        headers = self._get_auth_headers()
        
        offset = 0
        total_fetched = 0
        batch_size = min(batch_size, 1000)  # API limit
        
        while True:
            # Construire la requête
            params = {
                "batch_size": batch_size,
                "batch": offset // batch_size,
                "sort": "decision_date",
                "order": "desc",
            }
            
            # Filtre par date
            if since:
                params["date_start"] = since.strftime("%Y-%m-%d")
            
            try:
                response = session.get(
                    f"{self.base_url}/search",
                    headers=headers,
                    params=params,
                    timeout=self.config.request_timeout,
                )
                response.raise_for_status()
                data = response.json()
                
            except Exception as e:
                logger.error(f"Judilibre fetch error at offset {offset}: {e}")
                raise
            
            results = data.get("results", [])
            total_available = data.get("total", 0)
            
            if not results:
                break
            
            for item in results:
                yield item
                total_fetched += 1
                
                if limit and total_fetched >= limit:
                    self._log_fetch("Limit reached", fetched=total_fetched)
                    return
            
            offset += batch_size
            
            # Vérifier si on a tout récupéré
            if offset >= total_available:
                break
            
            self._log_fetch("Batch fetched", offset=offset, total=total_available)
        
        self._log_fetch("Fetch complete", total_fetched=total_fetched)
    
    def fetch_by_id(self, decision_id: str) -> Optional[Dict[str, Any]]:
        """
        Récupère une décision par son ID.
        
        Args:
            decision_id: ID Judilibre de la décision
        
        Returns:
            Dict brut de la décision ou None
        """
        # Check cache first
        cached = self._get_cached(decision_id)
        if cached:
            return cached
        
        session = self._get_session()
        headers = self._get_auth_headers()
        
        try:
            response = session.get(
                f"{self.base_url}/decision/{decision_id}",
                headers=headers,
                timeout=self.config.request_timeout,
            )
            response.raise_for_status()
            data = response.json()
            
            # Cache result
            self._set_cached(decision_id, data)
            
            return data
            
        except Exception as e:
            logger.error(f"Judilibre fetch by ID error: {e}")
            return None
    
    def parse(self, raw_data: Dict[str, Any]) -> Optional[LegalDoc]:
        """
        Parse une décision Judilibre en LegalDoc.
        
        Args:
            raw_data: Données brutes de l'API
        
        Returns:
            LegalDoc ou None si invalide
        """
        try:
            # Extraire les champs
            decision_id = raw_data.get("id", "")
            text = raw_data.get("text", "")
            
            if not decision_id or not text:
                logger.warning(f"Invalid Judilibre decision: missing id or text")
                return None
            
            # Métadonnées
            decision_date = self._parse_date(raw_data.get("decision_date"))
            chamber = raw_data.get("chamber", "")
            formation = raw_data.get("formation", "")
            solution = raw_data.get("solution", "")
            ecli = raw_data.get("ecli", "")
            pourvoi = raw_data.get("number", "")
            
            # Construire la citation
            citation = self._build_citation(
                chamber=chamber,
                date=decision_date,
                pourvoi=pourvoi,
            )
            
            # Déterminer la juridiction
            jurisdiction = self._determine_jurisdiction(raw_data)
            
            # URL Judilibre
            origin_url = f"https://www.courdecassation.fr/decision/{decision_id}"
            
            # Provenance
            provenance = self._create_provenance(
                origin_id=decision_id,
                origin_url=origin_url,
                content_hash=self._compute_hash(text.encode()),
            )
            
            # Construire le document
            doc = LegalDoc(
                doc_id="",  # Auto-calculé
                source=LegalSource.CASS,
                origin_id=decision_id,
                document_type=DocumentType.ARRET,
                jurisdiction=jurisdiction,
                title=self._build_title(chamber, decision_date, solution),
                citation=citation,
                date=decision_date,
                text=text,
                summary=raw_data.get("summary"),
                court="Cour de cassation",
                chamber=chamber,
                formation=formation,
                decision_number=pourvoi,
                ecli=ecli,
                solution=solution,
                provenance=provenance,
            )
            
            return doc
            
        except Exception as e:
            logger.error(f"Judilibre parse error: {e}")
            return None
    
    def _parse_date(self, date_str: Optional[str]) -> Optional[datetime]:
        """Parse une date au format YYYY-MM-DD."""
        if not date_str:
            return None
        try:
            return datetime.strptime(date_str[:10], "%Y-%m-%d")
        except ValueError:
            return None
    
    def _build_citation(
        self,
        chamber: str,
        date: Optional[datetime],
        pourvoi: str,
    ) -> str:
        """
        Construit une citation au format standard.
        
        Format: "Cass. [chambre], [date], n° [pourvoi]"
        Exemple: "Cass. civ. 1re, 15 janv. 2024, n° 22-18.456"
        """
        # Mapping chambres
        chamber_short = {
            "Première chambre civile": "civ. 1re",
            "Deuxième chambre civile": "civ. 2e",
            "Troisième chambre civile": "civ. 3e",
            "Chambre commerciale": "com.",
            "Chambre sociale": "soc.",
            "Chambre criminelle": "crim.",
            "Assemblée plénière": "ass. plén.",
            "Chambre mixte": "ch. mixte",
        }.get(chamber, chamber[:10] if chamber else "")
        
        # Format date
        date_str = ""
        if date:
            months_fr = [
                "janv.", "févr.", "mars", "avr.", "mai", "juin",
                "juill.", "août", "sept.", "oct.", "nov.", "déc."
            ]
            date_str = f"{date.day} {months_fr[date.month - 1]} {date.year}"
        
        # Construire
        parts = ["Cass."]
        if chamber_short:
            parts.append(chamber_short)
        if date_str:
            parts.append(date_str)
        if pourvoi:
            parts.append(f"n° {pourvoi}")
        
        return ", ".join(parts)
    
    def _build_title(
        self,
        chamber: str,
        date: Optional[datetime],
        solution: str,
    ) -> str:
        """Construit le titre de la décision."""
        parts = []
        if chamber:
            parts.append(chamber)
        if date:
            parts.append(date.strftime("%d/%m/%Y"))
        if solution:
            parts.append(f"({solution})")
        
        return " - ".join(parts) if parts else "Arrêt Cour de cassation"
    
    def _determine_jurisdiction(self, raw_data: Dict[str, Any]) -> Jurisdiction:
        """Détermine la juridiction selon la chambre."""
        chamber = raw_data.get("chamber", "").lower()
        
        if "civil" in chamber:
            return Jurisdiction.JUDICIAL_CIVIL
        elif "pénal" in chamber or "criminel" in chamber:
            return Jurisdiction.JUDICIAL_PENAL
        elif "social" in chamber:
            return Jurisdiction.JUDICIAL_SOCIAL
        elif "commercial" in chamber:
            return Jurisdiction.JUDICIAL_COMMERCIAL
        else:
            return Jurisdiction.JUDICIAL_CIVIL  # Default
