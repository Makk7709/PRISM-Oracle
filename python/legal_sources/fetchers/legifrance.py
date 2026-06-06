"""
Legal Sources — LegiFrance Fetcher

Fetcher pour les codes et textes législatifs via l'API Légifrance.

API Documentation: https://www.legifrance.gouv.fr/contenu/pied-de-page/open-data-et-api
"""

import logging
import re
from datetime import datetime
from typing import Any, Dict, Generator, List, Optional

from ..config import LegalSourcesConfig, PRIORITY_CODES
from ..models import (
    DocumentType,
    Jurisdiction,
    LegalDoc,
    LegalSource,
    Provenance,
)
from .base import BaseFetcher

logger = logging.getLogger("legal_sources.legifrance")


class LegiFranceFetcher(BaseFetcher):
    """
    Fetcher pour l'API Légifrance (LEGI).
    
    Contenu:
    - 73 codes officiels consolidés
    - Lois, décrets-lois, ordonnances, décrets depuis 1945
    - Versions consolidées avec historique
    """
    
    source = LegalSource.LEGI
    
    def __init__(self, config: LegalSourcesConfig):
        super().__init__(config)
        self.base_url = config.legifrance_base_url
    
    def fetch(
        self,
        since: Optional[datetime] = None,
        limit: Optional[int] = None,
        codes: Optional[List[str]] = None,
    ) -> Generator[Dict[str, Any], None, None]:
        """
        Récupère les articles de codes depuis Légifrance.
        
        Args:
            since: Date minimum de modification
            limit: Nombre maximum d'articles
            codes: Liste des codes à récupérer (défaut: PRIORITY_CODES)
        
        Yields:
            Dict brut de chaque article
        """
        codes = codes or PRIORITY_CODES
        
        self._log_fetch("Starting fetch", codes=codes, limit=limit)
        
        total_fetched = 0
        
        for code_name in codes:
            self._log_fetch(f"Fetching code: {code_name}")
            
            try:
                # Récupérer le sommaire du code
                toc = self._fetch_code_toc(code_name)
                if not toc:
                    logger.warning(f"Could not fetch TOC for {code_name}")
                    continue
                
                # Parcourir les articles
                for article in self._fetch_code_articles(toc, since):
                    article["code_name"] = code_name
                    yield article
                    
                    total_fetched += 1
                    if limit and total_fetched >= limit:
                        self._log_fetch("Limit reached", fetched=total_fetched)
                        return
                
            except Exception as e:
                logger.error(f"Error fetching code {code_name}: {e}")
                continue
        
        self._log_fetch("Fetch complete", total_fetched=total_fetched)
    
    def _fetch_code_toc(self, code_name: str) -> Optional[Dict]:
        """
        Récupère le sommaire d'un code.
        
        Args:
            code_name: Nom du code (ex: "Code civil")
        
        Returns:
            Dict du sommaire ou None
        """
        session = self._get_session()
        headers = self._get_auth_headers()
        
        # Rechercher le code
        try:
            response = session.post(
                f"{self.base_url}/search",
                headers=headers,
                json={
                    "recherche": {
                        "champs": [
                            {
                                "typeChamp": "TITLE",
                                "criteres": [
                                    {
                                        "typeRecherche": "EXACTE",
                                        "valeur": code_name,
                                    }
                                ],
                            }
                        ],
                        "filtres": [
                            {"facette": "TEXT_LEGAL_STATUS", "valeurs": ["VIGUEUR"]},
                            {"facette": "NATURE", "valeurs": ["CODE"]},
                        ],
                        "pageNumber": 1,
                        "pageSize": 1,
                        "sort": "PERTINENCE",
                    }
                },
                timeout=self.config.request_timeout,
            )
            response.raise_for_status()
            data = response.json()
            
            results = data.get("results", [])
            if not results:
                return None
            
            code_id = results[0].get("id")
            if not code_id:
                return None
            
            # Récupérer le sommaire complet
            toc_response = session.get(
                f"{self.base_url}/consult/code/tableMatieres",
                headers=headers,
                params={"textId": code_id},
                timeout=self.config.request_timeout,
            )
            toc_response.raise_for_status()
            
            return toc_response.json()
            
        except Exception as e:
            logger.error(f"Error fetching TOC for {code_name}: {e}")
            return None
    
    def _fetch_code_articles(
        self,
        toc: Dict,
        since: Optional[datetime] = None,
    ) -> Generator[Dict, None, None]:
        """
        Parcourt récursivement le sommaire et récupère les articles.
        
        Args:
            toc: Sommaire du code
            since: Filtre date modification
        
        Yields:
            Dict de chaque article
        """
        session = self._get_session()
        headers = self._get_auth_headers()
        
        def traverse(section: Dict):
            """Traverse récursivement les sections."""
            # Articles directs
            for article_ref in section.get("articles", []):
                article_id = article_ref.get("id")
                if not article_id:
                    continue
                
                # Récupérer le contenu de l'article
                try:
                    response = session.get(
                        f"{self.base_url}/consult/legiPart",
                        headers=headers,
                        params={"id": article_id},
                        timeout=self.config.request_timeout,
                    )
                    response.raise_for_status()
                    article = response.json()
                    
                    # Filtre par date si nécessaire
                    if since:
                        mod_date = article.get("dateModification")
                        if mod_date:
                            try:
                                mod_dt = datetime.strptime(mod_date[:10], "%Y-%m-%d")
                                if mod_dt < since:
                                    continue
                            except ValueError:
                                pass
                    
                    yield article
                    
                except Exception as e:
                    logger.warning(f"Error fetching article {article_id}: {e}")
                    continue
            
            # Sous-sections
            for subsection in section.get("sections", []):
                yield from traverse(subsection)
        
        # Parcourir depuis la racine
        for section in toc.get("sections", []):
            yield from traverse(section)
    
    def fetch_article_by_id(self, article_id: str) -> Optional[Dict]:
        """
        Récupère un article par son ID LEGITEXT.
        
        Args:
            article_id: ID de l'article (LEGIARTI...)
        
        Returns:
            Dict de l'article ou None
        """
        cached = self._get_cached(article_id)
        if cached:
            return cached
        
        session = self._get_session()
        headers = self._get_auth_headers()
        
        try:
            response = session.get(
                f"{self.base_url}/consult/legiPart",
                headers=headers,
                params={"id": article_id},
                timeout=self.config.request_timeout,
            )
            response.raise_for_status()
            data = response.json()
            
            self._set_cached(article_id, data)
            return data
            
        except Exception as e:
            logger.error(f"Error fetching article {article_id}: {e}")
            return None
    
    def parse(self, raw_data: Dict[str, Any]) -> Optional[LegalDoc]:
        """
        Parse un article Légifrance en LegalDoc.
        
        Args:
            raw_data: Données brutes de l'API
        
        Returns:
            LegalDoc ou None si invalide
        """
        try:
            article_id = raw_data.get("id", "")
            text = raw_data.get("texte", "") or raw_data.get("content", "")
            
            if not article_id:
                return None
            
            # Nettoyer le texte HTML
            text = self._clean_html(text)
            
            if not text:
                logger.warning(f"Empty text for article {article_id}")
                return None
            
            # Métadonnées
            code_name = raw_data.get("code_name", "")
            article_num = raw_data.get("num", "") or self._extract_article_num(raw_data)
            title = raw_data.get("titre", "") or f"Article {article_num}"
            
            # Dates
            date_debut = self._parse_date(raw_data.get("dateDebut"))
            self._parse_date(raw_data.get("dateFin"))
            date_mod = self._parse_date(raw_data.get("dateModification"))
            
            # Status (en vigueur ou abrogé)
            raw_data.get("etat", "").upper()
            
            # Citation
            citation = self._build_citation(code_name, article_num)
            
            # URL Légifrance
            origin_url = f"https://www.legifrance.gouv.fr/codes/article_lc/{article_id}"
            
            # Provenance
            provenance = self._create_provenance(
                origin_id=article_id,
                origin_url=origin_url,
                content_hash=self._compute_hash(text.encode()),
            )
            
            # Document
            doc = LegalDoc(
                doc_id="",  # Auto-calculé
                source=LegalSource.LEGI,
                origin_id=article_id,
                document_type=DocumentType.CODE,
                jurisdiction=Jurisdiction.LEGISLATIVE,
                title=title,
                citation=citation,
                date=date_mod or date_debut,
                date_effect=date_debut,
                text=text,
                code_name=code_name,
                article_number=article_num,
                articles_refs=self._extract_refs(text),
                provenance=provenance,
            )
            
            return doc
            
        except Exception as e:
            logger.error(f"LegiFrance parse error: {e}")
            return None
    
    def _parse_date(self, date_str: Optional[str]) -> Optional[datetime]:
        """Parse une date ISO ou française."""
        if not date_str:
            return None
        
        for fmt in ["%Y-%m-%d", "%d/%m/%Y", "%Y-%m-%dT%H:%M:%S"]:
            try:
                return datetime.strptime(date_str[:len(fmt.replace("%", ""))], fmt)
            except ValueError:
                continue
        return None
    
    def _clean_html(self, html: str) -> str:
        """Nettoie le HTML et extrait le texte."""
        if not html:
            return ""
        
        # Supprimer les tags HTML
        text = re.sub(r"<[^>]+>", " ", html)
        
        # Normaliser les espaces
        text = re.sub(r"\s+", " ", text)
        
        # Entités HTML communes
        text = text.replace("&nbsp;", " ")
        text = text.replace("&amp;", "&")
        text = text.replace("&lt;", "<")
        text = text.replace("&gt;", ">")
        text = text.replace("&quot;", '"')
        
        return text.strip()
    
    def _extract_article_num(self, raw_data: Dict) -> str:
        """Extrait le numéro d'article depuis les données."""
        # Essayer différents champs
        for field in ["num", "numero", "articleNum"]:
            if val := raw_data.get(field):
                return str(val)
        
        # Extraire du titre
        title = raw_data.get("titre", "")
        match = re.search(r"Article\s+([\w\d.-]+)", title, re.IGNORECASE)
        if match:
            return match.group(1)
        
        return ""
    
    def _build_citation(self, code_name: str, article_num: str) -> str:
        """
        Construit une citation au format standard.
        
        Format: "Art. [num] [code abrégé]"
        Exemple: "Art. 1134 C. civ."
        """
        # Abréviations des codes
        code_abbrev = {
            "Code civil": "C. civ.",
            "Code pénal": "C. pén.",
            "Code de commerce": "C. com.",
            "Code du travail": "C. trav.",
            "Code de procédure civile": "C. pr. civ.",
            "Code de procédure pénale": "C. pr. pén.",
            "Code général des impôts": "CGI",
            "Code de la consommation": "C. consom.",
            "Code de la propriété intellectuelle": "CPI",
            "Code de l'environnement": "C. envir.",
        }.get(code_name, code_name[:15])
        
        if article_num:
            return f"Art. {article_num} {code_abbrev}"
        return code_abbrev
    
    def _extract_refs(self, text: str) -> List[str]:
        """Extrait les références à d'autres articles."""
        refs = []
        
        # Pattern: "article(s) X, Y, Z"
        patterns = [
            r"articles?\s+([\w\d.-]+(?:\s*,\s*[\w\d.-]+)*)",
            r"art\.\s*([\w\d.-]+)",
            r"L\.\s*([\d-]+)",
            r"R\.\s*([\d-]+)",
            r"D\.\s*([\d-]+)",
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                # Séparer les articles multiples
                for ref in re.split(r"[,\s]+", match):
                    ref = ref.strip()
                    if ref and len(ref) < 20:  # Éviter les faux positifs
                        refs.append(ref)
        
        return list(set(refs))  # Dédupliquer
