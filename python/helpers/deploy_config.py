"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                    PRISM + EVIDENCE — Deployment Configuration                 ║
║                                                                              ║
║  Configuration unifiée avec validation Pydantic stricte.                     ║
║  Priorité: ENV > fichier config local > defaults                             ║
║  Mode: fail-closed (erreur si config invalide)                               ║
║                                                                              ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import os
import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Set
from enum import Enum
from functools import lru_cache

from pydantic import BaseModel, Field, field_validator, model_validator
import yaml

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════════
# ENUMS
# ═══════════════════════════════════════════════════════════════════════════════

class DeploymentMode(str, Enum):
    """Mode de déploiement."""
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"


class NetworkMode(str, Enum):
    """Mode réseau."""
    OFFLINE = "offline"
    ONLINE = "online"
    RESTRICTED = "restricted"


# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION SCHEMAS
# ═══════════════════════════════════════════════════════════════════════════════

class NetworkConfig(BaseModel):
    """Configuration réseau."""
    offline_mode: bool = Field(default=True, description="Mode offline par défaut")
    allowed_domains: List[str] = Field(default_factory=list)
    timeout_ms: int = Field(default=30000, ge=1000, le=300000)
    bind_host: str = Field(default="127.0.0.1")
    allow_lan: bool = Field(default=False)
    
    @field_validator('allowed_domains', mode='before')
    @classmethod
    def parse_domains(cls, v):
        if isinstance(v, str):
            return [d.strip() for d in v.split(',') if d.strip()]
        return v
    
    @field_validator('bind_host')
    @classmethod
    def validate_bind_host(cls, v):
        valid_hosts = ['127.0.0.1', 'localhost', '0.0.0.0']
        if v not in valid_hosts and not v.startswith('192.168.'):
            logger.warning(f"Unusual bind host: {v}")
        return v


class ConsensusConfig(BaseModel):
    """Configuration PRISM Consensus."""
    enabled: bool = Field(default=True)
    timeout_ms: int = Field(default=10000, ge=1000, le=60000)
    quorum_ratio: float = Field(default=0.67, ge=0.5, le=1.0)
    arbiter_1: str = Field(default="openrouter/anthropic/claude-3.5-sonnet")
    arbiter_2: str = Field(default="openrouter/openai/gpt-4o")
    arbiter_3: str = Field(default="openrouter/google/gemini-pro-1.5")
    audit_log: bool = Field(default=True)
    
    @field_validator('arbiter_1', 'arbiter_2', 'arbiter_3')
    @classmethod
    def validate_arbiter(cls, v):
        if not v or '/' not in v:
            raise ValueError(f"Invalid arbiter format: {v}. Expected: provider/model")
        return v


class StorageConfig(BaseModel):
    """Configuration stockage."""
    data_dir: Path = Field(default=Path("/app/data"))
    logs_dir: Path = Field(default=Path("/app/logs"))
    audit_dir: Path = Field(default=Path("/app/audit"))
    log_max_size_mb: int = Field(default=50, ge=1, le=1000)
    log_max_files: int = Field(default=10, ge=1, le=100)
    log_level: str = Field(default="INFO")
    audit_retention_days: int = Field(default=90, ge=7, le=365)
    
    @field_validator('log_level')
    @classmethod
    def validate_log_level(cls, v):
        valid = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        if v.upper() not in valid:
            raise ValueError(f"Invalid log level: {v}. Valid: {valid}")
        return v.upper()


class MCPConfig(BaseModel):
    """Configuration MCP servers."""
    firecrawl_enabled: bool = Field(default=False)
    tavily_enabled: bool = Field(default=False)
    playwright_enabled: bool = Field(default=False)
    arxiv_enabled: bool = Field(default=True)
    semanticscholar_enabled: bool = Field(default=True)


class FeatureFlags(BaseModel):
    """Feature flags."""
    research_pipeline: bool = Field(default=True)
    memory_consolidation: bool = Field(default=True)
    task_decomposition: bool = Field(default=True)


class DeploymentConfig(BaseModel):
    """Configuration de déploiement complète."""
    # Identification
    version: str = Field(default="1.0.0")
    instance_id: str = Field(default="evidence-001")
    env: DeploymentMode = Field(default=DeploymentMode.PRODUCTION)
    
    # Sous-configurations
    network: NetworkConfig = Field(default_factory=NetworkConfig)
    consensus: ConsensusConfig = Field(default_factory=ConsensusConfig)
    storage: StorageConfig = Field(default_factory=StorageConfig)
    mcp: MCPConfig = Field(default_factory=MCPConfig)
    features: FeatureFlags = Field(default_factory=FeatureFlags)
    
    # Ports
    backend_port: int = Field(default=5050, ge=1024, le=65535)
    frontend_port: int = Field(default=8080, ge=1024, le=65535)
    
    @model_validator(mode='after')
    def validate_consistency(self):
        """Validation de cohérence globale."""
        # Si offline, les MCPs nécessitant réseau doivent être désactivés
        if self.network.offline_mode:
            if self.mcp.firecrawl_enabled:
                logger.warning("Firecrawl requires network, but offline mode is enabled")
            if self.mcp.tavily_enabled:
                logger.warning("Tavily requires network, but offline mode is enabled")
        
        # Vérifier que les chemins sont différents
        if self.storage.logs_dir == self.storage.audit_dir:
            raise ValueError("logs_dir and audit_dir must be different")
        
        return self


# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION LOADER
# ═══════════════════════════════════════════════════════════════════════════════

class ConfigLoader:
    """
    Chargeur de configuration avec priorité:
    1. Variables d'environnement
    2. Fichier config local
    3. Valeurs par défaut
    """
    
    ENV_PREFIX = "EVIDENCE_"
    
    def __init__(self, config_path: Optional[Path] = None):
        self.config_path = config_path
        self._config: Optional[DeploymentConfig] = None
    
    def load(self) -> DeploymentConfig:
        """Charge et valide la configuration."""
        if self._config is not None:
            return self._config
        
        # 1. Charger les defaults
        config_dict = {}
        
        # 2. Charger depuis fichier si existe
        if self.config_path and self.config_path.exists():
            config_dict = self._load_file(self.config_path)
            logger.info(f"Loaded config from {self.config_path}")
        
        # 3. Override avec variables d'environnement
        config_dict = self._apply_env_overrides(config_dict)
        
        # 4. Valider avec Pydantic (fail-closed)
        try:
            self._config = DeploymentConfig(**config_dict)
            logger.info(f"Configuration validated: {self._config.instance_id}")
            return self._config
        except Exception as e:
            logger.error(f"Configuration validation failed: {e}")
            raise RuntimeError(f"FAIL-CLOSED: Invalid configuration - {e}")
    
    def _load_file(self, path: Path) -> Dict[str, Any]:
        """Charge un fichier de config (YAML ou JSON)."""
        content = path.read_text()
        
        if path.suffix in ['.yaml', '.yml']:
            return yaml.safe_load(content) or {}
        elif path.suffix == '.json':
            return json.loads(content)
        else:
            raise ValueError(f"Unsupported config format: {path.suffix}")
    
    def _apply_env_overrides(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Applique les overrides depuis les variables d'environnement."""
        env_mapping = {
            # Identification
            'EVIDENCE_VERSION': ('version', str),
            'EVIDENCE_INSTANCE_ID': ('instance_id', str),
            'EVIDENCE_ENV': ('env', str),
            
            # Network
            'OFFLINE_MODE': ('network.offline_mode', self._parse_bool),
            'NETWORK_ALLOWLIST': ('network.allowed_domains', str),
            'NETWORK_TIMEOUT_MS': ('network.timeout_ms', int),
            'BIND_HOST': ('network.bind_host', str),
            
            # Consensus
            'CONSENSUS_ENABLED': ('consensus.enabled', self._parse_bool),
            'CONSENSUS_TIMEOUT_MS': ('consensus.timeout_ms', int),
            'CONSENSUS_QUORUM_RATIO': ('consensus.quorum_ratio', float),
            'CONSENSUS_ARBITER_1': ('consensus.arbiter_1', str),
            'CONSENSUS_ARBITER_2': ('consensus.arbiter_2', str),
            'CONSENSUS_ARBITER_3': ('consensus.arbiter_3', str),
            'CONSENSUS_AUDIT_LOG': ('consensus.audit_log', self._parse_bool),
            
            # Storage
            'DATA_DIR': ('storage.data_dir', Path),
            'LOGS_DIR': ('storage.logs_dir', Path),
            'AUDIT_DIR': ('storage.audit_dir', Path),
            'LOG_LEVEL': ('storage.log_level', str),
            'AUDIT_RETENTION_DAYS': ('storage.audit_retention_days', int),
            
            # Ports
            'BACKEND_PORT': ('backend_port', int),
            'FRONTEND_PORT': ('frontend_port', int),
            
            # MCP
            'MCP_FIRECRAWL_ENABLED': ('mcp.firecrawl_enabled', self._parse_bool),
            'MCP_TAVILY_ENABLED': ('mcp.tavily_enabled', self._parse_bool),
            'MCP_PLAYWRIGHT_ENABLED': ('mcp.playwright_enabled', self._parse_bool),
            'MCP_ARXIV_ENABLED': ('mcp.arxiv_enabled', self._parse_bool),
            'MCP_SEMANTICSCHOLAR_ENABLED': ('mcp.semanticscholar_enabled', self._parse_bool),
            
            # Features
            'FEATURE_RESEARCH_PIPELINE': ('features.research_pipeline', self._parse_bool),
            'FEATURE_MEMORY_CONSOLIDATION': ('features.memory_consolidation', self._parse_bool),
            'FEATURE_TASK_DECOMPOSITION': ('features.task_decomposition', self._parse_bool),
        }
        
        for env_key, (config_path, converter) in env_mapping.items():
            value = os.environ.get(env_key)
            if value is not None:
                self._set_nested(config, config_path, converter(value))
        
        return config
    
    def _set_nested(self, d: Dict, path: str, value: Any):
        """Set a nested dict value using dot notation."""
        keys = path.split('.')
        for key in keys[:-1]:
            d = d.setdefault(key, {})
        d[keys[-1]] = value
    
    @staticmethod
    def _parse_bool(value: str) -> bool:
        """Parse string to bool."""
        return value.lower() in ('true', '1', 'yes', 'on')


# ═══════════════════════════════════════════════════════════════════════════════
# SINGLETON ACCESS
# ═══════════════════════════════════════════════════════════════════════════════

@lru_cache(maxsize=1)
def get_deployment_config() -> DeploymentConfig:
    """
    Retourne la configuration de déploiement (singleton).
    
    Recherche le fichier de config dans l'ordre:
    1. EVIDENCE_CONFIG_PATH env var
    2. /app/config/evidence.yaml
    3. ./deploy/config/evidence.yaml
    4. Defaults
    """
    config_path = None
    
    # Chercher le fichier de config
    search_paths = [
        os.environ.get('EVIDENCE_CONFIG_PATH'),
        '/app/config/evidence.yaml',
        './deploy/config/evidence.yaml',
        './config/evidence.yaml',
    ]
    
    for path in search_paths:
        if path and Path(path).exists():
            config_path = Path(path)
            break
    
    loader = ConfigLoader(config_path)
    return loader.load()


def validate_config() -> bool:
    """
    Valide la configuration actuelle.
    
    Returns:
        True si valide, raise exception sinon
    """
    try:
        config = get_deployment_config()
        logger.info(f"Config validated: v{config.version}, instance={config.instance_id}")
        return True
    except Exception as e:
        logger.error(f"Config validation FAILED: {e}")
        raise


# ═══════════════════════════════════════════════════════════════════════════════
# NETWORK GUARD
# ═══════════════════════════════════════════════════════════════════════════════

class NetworkGuard:
    """
    Garde réseau pour enforcer la politique offline/allowlist.
    """
    
    def __init__(self, config: NetworkConfig):
        self.config = config
        self._allowed_set: Set[str] = set(config.allowed_domains)
    
    def is_allowed(self, domain: str) -> bool:
        """Vérifie si un domaine est autorisé."""
        if self.config.offline_mode:
            return False
        
        # Vérifier allowlist
        domain_lower = domain.lower()
        
        for allowed in self._allowed_set:
            if allowed.startswith('*.'):
                # Wildcard match
                suffix = allowed[2:]
                if domain_lower.endswith(suffix):
                    return True
            elif domain_lower == allowed.lower():
                return True
        
        return False
    
    def check_or_raise(self, domain: str):
        """Vérifie et raise si non autorisé."""
        if not self.is_allowed(domain):
            mode = "OFFLINE" if self.config.offline_mode else "ALLOWLIST"
            raise PermissionError(
                f"Network request blocked ({mode}): {domain}"
            )


def get_network_guard() -> NetworkGuard:
    """Retourne le garde réseau configuré."""
    config = get_deployment_config()
    return NetworkGuard(config.network)


# ═══════════════════════════════════════════════════════════════════════════════
# BOOT GUARDS — HARD FAIL ON CRITICAL MISCONFIG
# ═══════════════════════════════════════════════════════════════════════════════

class BootGuardError(RuntimeError):
    """Erreur de garde au boot — système ne peut pas démarrer."""
    pass


def run_boot_guards():
    """
    Exécute les gardes critiques au démarrage.
    
    DOIT être appelé au boot de l'application.
    Lève BootGuardError si une condition critique est violée.
    
    Usage:
        from python.helpers.deploy_config import run_boot_guards
        run_boot_guards()  # Au début de main()
    """
    errors = []
    warnings = []
    
    # ─────────────────────────────────────────────────────────────────────────
    # GUARD 1: CONSENSUS_SIMULATION interdit en production
    # ─────────────────────────────────────────────────────────────────────────
    
    evidence_env = os.environ.get("EVIDENCE_ENV", "production").lower()
    consensus_simulation = os.environ.get("CONSENSUS_SIMULATION", "false").lower() == "true"
    
    if evidence_env == "production" and consensus_simulation:
        errors.append(
            "CRITICAL: CONSENSUS_SIMULATION=true is FORBIDDEN in production. "
            "Votes MUST be real. Set EVIDENCE_ENV=development for testing."
        )
    
    # ─────────────────────────────────────────────────────────────────────────
    # GUARD 2: Mode offline + arbitres externes → warn + fail-closed
    # ─────────────────────────────────────────────────────────────────────────
    
    offline_mode = os.environ.get("OFFLINE_MODE", "false").lower() == "true"
    arbiters_configured = any([
        os.environ.get("CONSENSUS_ARBITER_1"),
        os.environ.get("CONSENSUS_ARBITER_2"),
        os.environ.get("CONSENSUS_ARBITER_3"),
    ])
    local_arbiters = os.environ.get("CONSENSUS_LOCAL_ARBITERS", "")
    
    if offline_mode and arbiters_configured and not local_arbiters:
        warnings.append(
            "WARNING: OFFLINE_MODE=true but external arbiters configured without local fallback. "
            "Critical domains will use fail-closed behavior."
        )
    
    # ─────────────────────────────────────────────────────────────────────────
    # GUARD 3: Production sans consensus activé → warn
    # ─────────────────────────────────────────────────────────────────────────
    
    consensus_enabled = os.environ.get("CONSENSUS_ENABLED", "true").lower() == "true"
    
    if evidence_env == "production" and not consensus_enabled:
        warnings.append(
            "WARNING: Running in production with CONSENSUS_ENABLED=false. "
            "Critical domains will NOT have consensus validation."
        )
    
    # ─────────────────────────────────────────────────────────────────────────
    # GUARD 4: Vérification des modules critiques
    # ─────────────────────────────────────────────────────────────────────────
    
    try:
        from python.helpers.critical_decision_gate import get_decision_gate
        from python.helpers.criticality_router import get_criticality_router
        from python.helpers.evidence import EvidencePack
        logger.info("✅ Critical modules loaded successfully")
    except ImportError as e:
        errors.append(f"CRITICAL: Failed to import critical module: {e}")
    
    # ─────────────────────────────────────────────────────────────────────────
    # REPORT RESULTS
    # ─────────────────────────────────────────────────────────────────────────
    
    # Log warnings
    for warn in warnings:
        logger.warning(f"⚠️  {warn}")
    
    # Fail if errors
    if errors:
        error_msg = "\n".join(errors)
        logger.critical(f"🚫 BOOT GUARDS FAILED:\n{error_msg}")
        raise BootGuardError(f"Boot guards failed:\n{error_msg}")
    
    logger.info(
        f"✅ Boot guards passed: env={evidence_env}, "
        f"offline={offline_mode}, consensus={consensus_enabled}"
    )
    
    return True


def validate_consensus_config_at_boot():
    """
    Valide la configuration consensus au démarrage.
    
    Vérifie que:
    - Simulation désactivée en production
    - Arbitres configurés correctement
    - Mode offline cohérent
    """
    try:
        from python.helpers.consensus_arbiter import (
            load_consensus_config,
            verify_no_simulation_in_production,
        )
        
        # Vérifier simulation
        verify_no_simulation_in_production()
        
        # Charger et valider config
        config = load_consensus_config()
        logger.info(
            f"Consensus config validated: "
            f"arbiters={len(config.arbiters)}, "
            f"simulation={config.simulation_enabled}, "
            f"offline={config.offline_mode}"
        )
        
        return True
        
    except Exception as e:
        logger.error(f"Consensus config validation failed: {e}")
        raise


# ═══════════════════════════════════════════════════════════════════════════════
# EXPORTS
# ═══════════════════════════════════════════════════════════════════════════════

__all__ = [
    # Enums
    "DeploymentMode",
    "NetworkMode",
    # Config models
    "NetworkConfig",
    "ConsensusConfig",
    "StorageConfig",
    "MCPConfig",
    "FeatureFlags",
    "DeploymentConfig",
    # Loader
    "ConfigLoader",
    "get_deployment_config",
    "validate_config",
    # Network guard
    "NetworkGuard",
    "get_network_guard",
    # Boot guards
    "BootGuardError",
    "run_boot_guards",
    "validate_consensus_config_at_boot",
]
