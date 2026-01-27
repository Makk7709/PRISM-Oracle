"""
Legal Sources — Configuration

Configuration centralisée pour l'ingestion des données juridiques.
"""

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional


@dataclass
class LegalSourcesConfig:
    """Configuration pour l'ingestion des sources juridiques."""
    
    # === Chemins ===
    base_dir: Path = field(default_factory=lambda: Path("data/legal"))
    raw_dir: Path = field(default_factory=lambda: Path("data/legal/raw"))
    processed_dir: Path = field(default_factory=lambda: Path("data/legal/processed"))
    index_dir: Path = field(default_factory=lambda: Path("data/legal/index"))
    cache_dir: Path = field(default_factory=lambda: Path("data/legal/cache"))
    
    # === API PISTE ===
    piste_client_id: Optional[str] = None
    piste_client_secret: Optional[str] = None
    piste_token_url: str = "https://oauth.piste.gouv.fr/api/oauth/token"
    
    # === API Judilibre ===
    judilibre_base_url: str = "https://api.piste.gouv.fr/cassation/judilibre/v1.0"
    
    # === API Légifrance ===
    legifrance_base_url: str = "https://api.piste.gouv.fr/dila/legifrance/lf-engine-app/v1"
    
    # === Chunking ===
    chunk_size: int = 1000  # Caractères
    chunk_overlap: int = 100
    min_chunk_size: int = 100
    
    # === Performance ===
    batch_size: int = 100
    max_concurrent_requests: int = 5
    request_timeout: int = 30
    retry_max: int = 3
    retry_delay: float = 1.0
    
    # === Indexation ===
    embedding_model: str = "text-embedding-3-small"
    embedding_dimension: int = 1536
    
    # === Sources activées ===
    enabled_sources: List[str] = field(default_factory=lambda: ["legi", "cass"])
    
    # === Logging ===
    log_level: str = "INFO"
    log_format: str = "json"  # "json" ou "text"
    
    def __post_init__(self):
        """Charge les variables d'environnement."""
        # API credentials
        self.piste_client_id = os.getenv("PISTE_CLIENT_ID", self.piste_client_id)
        self.piste_client_secret = os.getenv("PISTE_CLIENT_SECRET", self.piste_client_secret)
        
        # Paths from env
        if base := os.getenv("LEGAL_SOURCES_DIR"):
            self.base_dir = Path(base)
            self.raw_dir = self.base_dir / "raw"
            self.processed_dir = self.base_dir / "processed"
            self.index_dir = self.base_dir / "index"
            self.cache_dir = self.base_dir / "cache"
    
    def ensure_dirs(self) -> None:
        """Crée les répertoires nécessaires."""
        for dir_path in [self.raw_dir, self.processed_dir, self.index_dir, self.cache_dir]:
            dir_path.mkdir(parents=True, exist_ok=True)
    
    @property
    def has_piste_credentials(self) -> bool:
        """Vérifie si les credentials PISTE sont configurés."""
        return bool(self.piste_client_id and self.piste_client_secret)
    
    def to_dict(self) -> Dict:
        return {
            "base_dir": str(self.base_dir),
            "chunk_size": self.chunk_size,
            "chunk_overlap": self.chunk_overlap,
            "batch_size": self.batch_size,
            "enabled_sources": self.enabled_sources,
            "has_piste_credentials": self.has_piste_credentials,
        }


def get_default_config() -> LegalSourcesConfig:
    """Retourne la configuration par défaut."""
    return LegalSourcesConfig()


# === Constantes sources ===

# Codes principaux à indexer (MVP)
PRIORITY_CODES = [
    "Code civil",
    "Code pénal",
    "Code de commerce",
    "Code du travail",
    "Code de procédure civile",
    "Code de procédure pénale",
    "Code général des impôts",
    "Code de la consommation",
    "Code de la propriété intellectuelle",
    "Code de l'environnement",
]

# Mapping source -> URL data.gouv.fr
SOURCE_URLS = {
    "legi": "https://www.data.gouv.fr/fr/datasets/legi-codes-lois-et-reglements-consolides/",
    "jorf": "https://www.data.gouv.fr/fr/datasets/jorf/",
    "cass": "https://www.data.gouv.fr/fr/dataservices/api-judilibre/",
    "jade": "https://www.data.gouv.fr/fr/datasets/jade/",
    "constit": "https://www.data.gouv.fr/fr/datasets/constit-les-decisions-du-conseil-constitutionnel/",
}

# Mapping source -> producteur
SOURCE_PRODUCERS = {
    "legi": "DILA (Direction de l'Information Légale et Administrative)",
    "jorf": "DILA (Direction de l'Information Légale et Administrative)",
    "cass": "Cour de cassation",
    "jade": "Conseil d'État / DILA",
    "constit": "Conseil constitutionnel",
}
