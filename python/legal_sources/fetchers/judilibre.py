"""
Legal Sources — Judilibre Fetcher

Fetcher pour les arrêts de la Cour de cassation via l'API Judilibre (PISTE).

Endpoints utilisés:
  - /export  : Bulk export (pas de query requise) — pour l'ingestion
  - /search  : Recherche par mots-clés (query obligatoire) — pour lookup
  - /decision: Consultation unitaire par ID

API Documentation: https://www.courdecassation.fr/recherche-judilibre
"""

import logging
import time
from datetime import datetime
from typing import Any, Dict, Generator, List, Optional

from ..config import LegalSourcesConfig
from ..models import (
    AccessMode,
    DocumentType,
    Jurisdiction,
    LegalDoc,
    LegalSource,
    Provenance,
)
from .base import BaseFetcher

# Constantes (déduplication littéraux — python:S1192)
_COURT_CASSATION = "Cour de cassation"

logger = logging.getLogger("legal_sources.judilibre")

# Mapping short API chamber codes → long labels & citation abbreviations
_CHAMBER_MAP: Dict[str, Dict[str, str]] = {
    # Cour de cassation chamber codes returned by the API
    "civ1": {"label": "Première chambre civile", "short": "civ. 1re", "jur": "civil"},
    "civ2": {"label": "Deuxième chambre civile", "short": "civ. 2e", "jur": "civil"},
    "civ3": {"label": "Troisième chambre civile", "short": "civ. 3e", "jur": "civil"},
    "comm": {"label": "Chambre commerciale", "short": "com.", "jur": "commercial"},
    "soc":  {"label": "Chambre sociale", "short": "soc.", "jur": "social"},
    "crim": {"label": "Chambre criminelle", "short": "crim.", "jur": "penal"},
    "mi":   {"label": "Chambre mixte", "short": "ch. mixte", "jur": "civil"},
    "pl":   {"label": "Assemblée plénière", "short": "ass. plén.", "jur": "civil"},
    "ordo": {"label": "Ordonnance", "short": "ord.", "jur": "civil"},
    "crepa": {"label": "CREPA", "short": "CREPA", "jur": "civil"},
    # Long-form names (legacy or alternative responses)
    "première chambre civile": {"label": "Première chambre civile", "short": "civ. 1re", "jur": "civil"},
    "deuxième chambre civile": {"label": "Deuxième chambre civile", "short": "civ. 2e", "jur": "civil"},
    "troisième chambre civile": {"label": "Troisième chambre civile", "short": "civ. 3e", "jur": "civil"},
    "chambre commerciale": {"label": "Chambre commerciale", "short": "com.", "jur": "commercial"},
    "chambre sociale": {"label": "Chambre sociale", "short": "soc.", "jur": "social"},
    "chambre criminelle": {"label": "Chambre criminelle", "short": "crim.", "jur": "penal"},
    "assemblée plénière": {"label": "Assemblée plénière", "short": "ass. plén.", "jur": "civil"},
    "chambre mixte": {"label": "Chambre mixte", "short": "ch. mixte", "jur": "civil"},
}

_JUR_MAP = {
    "civil": Jurisdiction.JUDICIAL_CIVIL,
    "penal": Jurisdiction.JUDICIAL_PENAL,
    "social": Jurisdiction.JUDICIAL_SOCIAL,
    "commercial": Jurisdiction.JUDICIAL_COMMERCIAL,
}


class JudilibreFetcher(BaseFetcher):
    """
    Fetcher pour l'API Judilibre (Cour de cassation) via PISTE.

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

    # ──────────────────────────────────────────────
    # Bulk fetch via /export (no query required)
    # ──────────────────────────────────────────────
    def fetch(
        self,
        since: Optional[datetime] = None,
        limit: Optional[int] = None,
        batch_size: int = 100,
    ) -> Generator[Dict[str, Any], None, None]:
        """
        Récupère les décisions en masse via /export.

        Args:
            since: Date minimum de décision (YYYY-MM-DD)
            limit: Nombre maximum de décisions
            batch_size: Taille des lots (max 1000)

        Yields:
            Dict brut de chaque décision
        """
        self._log_fetch(
            "Starting bulk export",
            since=since.isoformat() if since else None,
            limit=limit,
        )

        session = self._get_session()
        headers = self._get_auth_headers()

        batch_idx = 0
        total_fetched = 0
        batch_size = min(batch_size, 1000)  # API hard limit

        while True:
            params: Dict[str, Any] = {
                "batch_size": batch_size,
                "batch": batch_idx,
            }

            if since:
                params["date_start"] = since.strftime("%Y-%m-%d")

            try:
                response = session.get(
                    f"{self.base_url}/export",
                    headers=headers,
                    params=params,
                    timeout=self.config.request_timeout,
                )
                response.raise_for_status()
                data = response.json()

            except Exception as e:
                logger.error(
                    f"Judilibre export error at batch {batch_idx}: {e}"
                )
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

            batch_idx += 1

            # Check if all pages exhausted
            if batch_idx * batch_size >= total_available:
                break

            self._log_fetch(
                "Batch fetched",
                batch=batch_idx,
                fetched=total_fetched,
                total=total_available,
            )

            # Polite delay (shared PISTE quotas)
            time.sleep(0.5)

        self._log_fetch("Export complete", total_fetched=total_fetched)

    # ──────────────────────────────────────────────
    # Search via /search (query required)
    # ──────────────────────────────────────────────
    def search(
        self,
        query: str,
        limit: int = 50,
        batch_size: int = 50,
        since: Optional[datetime] = None,
    ) -> Generator[Dict[str, Any], None, None]:
        """
        Recherche de décisions par mots-clés via /search.

        Args:
            query: Termes de recherche (obligatoire)
            limit: Nombre maximum de résultats
            batch_size: Taille des lots
            since: Date minimum

        Yields:
            Dict brut de chaque décision
        """
        session = self._get_session()
        headers = self._get_auth_headers()

        batch_idx = 0
        total_fetched = 0
        batch_size = min(batch_size, 1000)

        while True:
            params: Dict[str, Any] = {
                "query": query,
                "batch_size": batch_size,
                "batch": batch_idx,
                "sort": "score",
                "order": "desc",
                "type": "arret",
            }

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
                logger.error(f"Judilibre search error: {e}")
                raise

            results = data.get("results", [])
            if not results:
                break

            for item in results:
                yield item
                total_fetched += 1
                if total_fetched >= limit:
                    return

            batch_idx += 1
            total_available = data.get("total", 0)
            if batch_idx * batch_size >= total_available:
                break

            time.sleep(0.5)

    # ──────────────────────────────────────────────
    # Single decision fetch
    # ──────────────────────────────────────────────
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

    # Parser
    # ──────────────────────────────────────────────
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
                logger.warning("Invalid Judilibre decision: missing id or text")
                return None

            # Métadonnées
            decision_date = self._parse_date(raw_data.get("decision_date"))
            chamber_raw = raw_data.get("chamber", "")
            formation = raw_data.get("formation", "")
            solution = raw_data.get("solution", "")
            ecli = raw_data.get("ecli", "")
            pourvoi = raw_data.get("number", "")

            # Résoudre la chambre
            chamber_info = self._resolve_chamber(chamber_raw)
            chamber_label = chamber_info["label"]
            chamber_short = chamber_info["short"]
            jur_key = chamber_info["jur"]

            # Construire la citation
            citation = self._build_citation(
                chamber_short=chamber_short,
                date=decision_date,
                pourvoi=pourvoi,
            )

            # Déterminer la juridiction
            jurisdiction = _JUR_MAP.get(jur_key, Jurisdiction.JUDICIAL_CIVIL)

            # URL Judilibre
            origin_url = f"https://www.courdecassation.fr/decision/{decision_id}"

            # Provenance — Licence Ouverte 2.0 (Etalab) pour Judilibre
            provenance = Provenance(
                source=LegalSource.CASS,
                source_name=_COURT_CASSATION,
                origin_id=decision_id,
                origin_url=origin_url,
                retrieved_at=datetime.utcnow(),
                api_version="v1.0",
                license_name="Licence Ouverte 2.0 (Etalab)",
                license_url="https://www.etalab.gouv.fr/licence-ouverte-open-licence/",
                terms_name="CGU PISTE + CGU Judilibre",
                terms_url="https://piste.gouv.fr/cgu",
                access_mode=AccessMode.API_KEY_CGU,
                content_hash=self._compute_hash(text.encode("utf-8")),
            )

            # Construire le document
            doc = LegalDoc(
                doc_id="",  # Auto-calculé
                source=LegalSource.CASS,
                origin_id=decision_id,
                document_type=DocumentType.ARRET,
                jurisdiction=jurisdiction,
                title=self._build_title(chamber_label, decision_date, solution),
                citation=citation,
                date=decision_date,
                text=text,
                summary=raw_data.get("summary"),
                court=_COURT_CASSATION,
                chamber=chamber_label,
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

    # ──────────────────────────────────────────────
    # Internal helpers
    # ──────────────────────────────────────────────
    @staticmethod
    def _resolve_chamber(raw: str) -> Dict[str, str]:
        """Resolve short or long chamber code to label/short/jur triple."""
        key = raw.strip().lower()
        info = _CHAMBER_MAP.get(key)
        if info:
            return info
        # Fallback: detect keywords
        if "civ" in key:
            return {"label": raw, "short": raw[:10], "jur": "civil"}
        if "crim" in key or "pén" in key:
            return {"label": raw, "short": raw[:10], "jur": "penal"}
        if "soc" in key:
            return {"label": raw, "short": raw[:10], "jur": "social"}
        if "com" in key:
            return {"label": raw, "short": raw[:10], "jur": "commercial"}
        return {"label": raw or _COURT_CASSATION, "short": raw[:10] if raw else "", "jur": "civil"}

    @staticmethod
    def _parse_date(date_str: Optional[str]) -> Optional[datetime]:
        """Parse une date au format YYYY-MM-DD."""
        if not date_str:
            return None
        try:
            return datetime.strptime(date_str[:10], "%Y-%m-%d")
        except ValueError:
            return None

    @staticmethod
    def _build_citation(
        chamber_short: str,
        date: Optional[datetime],
        pourvoi: str,
    ) -> str:
        """
        Construit une citation au format standard.

        Format: "Cass. [chambre], [date], n° [pourvoi]"
        Exemple: "Cass. civ. 2e, 5 févr. 2026, n° 23-22.049"
        """
        months_fr = [
            "janv.", "févr.", "mars", "avr.", "mai", "juin",
            "juill.", "août", "sept.", "oct.", "nov.", "déc.",
        ]

        date_str = ""
        if date:
            date_str = f"{date.day} {months_fr[date.month - 1]} {date.year}"

        parts = ["Cass."]
        if chamber_short:
            parts.append(chamber_short)
        if date_str:
            parts.append(date_str)
        if pourvoi:
            parts.append(f"n° {pourvoi}")

        return ", ".join(parts)

    @staticmethod
    def _build_title(
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
        info = self._resolve_chamber(raw_data.get("chamber", ""))
        return _JUR_MAP.get(info["jur"], Jurisdiction.JUDICIAL_CIVIL)
