"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                    PRISM + EVIDENCE — Health Endpoints                         ║
║                                                                              ║
║  Endpoints de santé pour monitoring et orchestration.                        ║
║  /healthz : Process alive                                                    ║
║  /readyz  : Dépendances OK (config, volumes, consensus)                      ║
║                                                                              ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import os
import time
import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, asdict
from datetime import datetime

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════════
# HEALTH CHECK TYPES
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class HealthStatus:
    """Statut de santé."""
    status: str  # "healthy", "degraded", "unhealthy"
    message: str
    timestamp: str
    uptime_seconds: int
    version: str


@dataclass
class ReadinessStatus:
    """Statut de readiness."""
    ready: bool
    checks: Dict[str, Dict[str, Any]]
    timestamp: str


@dataclass
class ComponentCheck:
    """Résultat de check d'un composant."""
    name: str
    status: str  # "ok", "warning", "error"
    message: str
    latency_ms: Optional[int] = None


# ═══════════════════════════════════════════════════════════════════════════════
# HEALTH CHECKER
# ═══════════════════════════════════════════════════════════════════════════════

class HealthChecker:
    """
    Vérificateur de santé pour Evidence.
    """
    
    def __init__(self):
        self._start_time = time.time()
        self._version = self._load_version()
    
    def _load_version(self) -> str:
        """Charge la version depuis VERSION.json (case-insensitive search)."""
        for p in [
            "/app/VERSION.json",
            "/app/version.json",
            "VERSION.json",
            "version.json",
        ]:
            try:
                f = Path(p)
                if f.exists():
                    data = json.loads(f.read_text())
                    return data.get("version", "unknown")
            except Exception:
                continue
        return "unknown"
    
    @property
    def uptime_seconds(self) -> int:
        """Temps de fonctionnement en secondes."""
        return int(time.time() - self._start_time)
    
    def health_check(self) -> HealthStatus:
        """
        Check de santé basique (/healthz).
        Vérifie uniquement que le process est vivant.
        """
        return HealthStatus(
            status="healthy",
            message="Evidence is running",
            timestamp=datetime.utcnow().isoformat() + "Z",
            uptime_seconds=self.uptime_seconds,
            version=self._version
        )
    
    def readiness_check(self) -> ReadinessStatus:
        """
        Check de readiness (/readyz).
        Vérifie que toutes les dépendances sont OK.
        """
        checks = {}
        all_ok = True
        
        # 1. Check configuration
        config_check = self._check_config()
        checks["config"] = asdict(config_check)
        if config_check.status == "error":
            all_ok = False
        
        # 2. Check volumes/directories
        volume_check = self._check_volumes()
        checks["volumes"] = asdict(volume_check)
        if volume_check.status == "error":
            all_ok = False
        
        # 3. Check consensus system
        consensus_check = self._check_consensus()
        checks["consensus"] = asdict(consensus_check)
        if consensus_check.status == "error":
            all_ok = False
        
        # 4. Check memory
        memory_check = self._check_memory()
        checks["memory"] = asdict(memory_check)
        if memory_check.status == "error":
            all_ok = False
        
        return ReadinessStatus(
            ready=all_ok,
            checks=checks,
            timestamp=datetime.utcnow().isoformat() + "Z"
        )
    
    def _check_config(self) -> ComponentCheck:
        """Vérifie la configuration."""
        start = time.time()
        try:
            from python.helpers.deploy_config import get_deployment_config
            config = get_deployment_config()
            latency = int((time.time() - start) * 1000)
            
            return ComponentCheck(
                name="config",
                status="ok",
                message=f"Config loaded: {config.instance_id}",
                latency_ms=latency
            )
        except Exception as e:
            return ComponentCheck(
                name="config",
                status="error",
                message=f"Config error: {str(e)}"
            )
    
    def _check_volumes(self) -> ComponentCheck:
        """Vérifie les volumes/répertoires."""
        start = time.time()
        
        dirs_to_check = [
            os.environ.get("DATA_DIR", "/app/data"),
            os.environ.get("LOGS_DIR", "/app/logs"),
            os.environ.get("AUDIT_DIR", "/app/audit"),
        ]
        
        errors = []
        for dir_path in dirs_to_check:
            path = Path(dir_path)
            if not path.exists():
                errors.append(f"{dir_path} missing")
            elif not os.access(dir_path, os.W_OK):
                errors.append(f"{dir_path} not writable")
        
        latency = int((time.time() - start) * 1000)
        
        if errors:
            return ComponentCheck(
                name="volumes",
                status="error",
                message="; ".join(errors),
                latency_ms=latency
            )
        
        return ComponentCheck(
            name="volumes",
            status="ok",
            message=f"All {len(dirs_to_check)} volumes accessible",
            latency_ms=latency
        )
    
    def _check_consensus(self) -> ComponentCheck:
        """Vérifie le système de consensus."""
        start = time.time()
        try:
            from python.helpers.consensus_manager import ConsensusManager
            # Just check it can be instantiated
            ConsensusManager(timeout_ms=5000, total_providers=3)
            latency = int((time.time() - start) * 1000)
            
            return ComponentCheck(
                name="consensus",
                status="ok",
                message="PRISM Consensus ready",
                latency_ms=latency
            )
        except Exception as e:
            return ComponentCheck(
                name="consensus",
                status="error",
                message=f"Consensus error: {str(e)}"
            )
    
    def _check_memory(self) -> ComponentCheck:
        """Vérifie l'utilisation mémoire."""
        try:
            import psutil
            memory = psutil.virtual_memory()
            
            if memory.percent > 90:
                return ComponentCheck(
                    name="memory",
                    status="error",
                    message=f"Memory critical: {memory.percent}%"
                )
            elif memory.percent > 80:
                return ComponentCheck(
                    name="memory",
                    status="warning",
                    message=f"Memory high: {memory.percent}%"
                )
            
            return ComponentCheck(
                name="memory",
                status="ok",
                message=f"Memory OK: {memory.percent}%"
            )
        except ImportError:
            return ComponentCheck(
                name="memory",
                status="ok",
                message="Memory check skipped (psutil not available)"
            )


# ═══════════════════════════════════════════════════════════════════════════════
# FLASK INTEGRATION
# ═══════════════════════════════════════════════════════════════════════════════

def register_health_endpoints(app):
    """
    Enregistre les endpoints de santé sur une app Flask.
    
    Usage:
        from python.helpers.health_endpoints import register_health_endpoints
        register_health_endpoints(app)
    """
    checker = HealthChecker()
    
    @app.route('/healthz')
    def healthz():
        """Endpoint de santé basique."""
        status = checker.health_check()
        return asdict(status), 200
    
    @app.route('/readyz')
    def readyz():
        """Endpoint de readiness."""
        status = checker.readiness_check()
        http_code = 200 if status.ready else 503
        return asdict(status), http_code
    
    @app.route('/metrics')
    def metrics():
        """Métriques basiques (format Prometheus-like)."""
        uptime = checker.uptime_seconds
        readiness = checker.readiness_check()
        
        lines = [
            f'# HELP evidence_uptime_seconds Total uptime in seconds',
            f'# TYPE evidence_uptime_seconds counter',
            f'evidence_uptime_seconds {uptime}',
            f'',
            f'# HELP evidence_ready Ready status (1=ready, 0=not ready)',
            f'# TYPE evidence_ready gauge',
            f'evidence_ready {1 if readiness.ready else 0}',
        ]
        
        return '\n'.join(lines), 200, {'Content-Type': 'text/plain'}
    
    logger.info("Health endpoints registered: /healthz, /readyz, /metrics")


# ═══════════════════════════════════════════════════════════════════════════════
# STANDALONE CHECK
# ═══════════════════════════════════════════════════════════════════════════════

def run_health_check() -> bool:
    """
    Exécute un check de santé standalone.
    Utilisé par les scripts de diagnostic.
    
    Returns:
        True si healthy, False sinon
    """
    checker = HealthChecker()
    
    print("=" * 60)
    print("EVIDENCE HEALTH CHECK")
    print("=" * 60)
    
    # Health
    health = checker.health_check()
    print(f"\n[HEALTH] {health.status.upper()}")
    print(f"  Version: {health.version}")
    print(f"  Uptime: {health.uptime_seconds}s")
    
    # Readiness
    readiness = checker.readiness_check()
    print(f"\n[READINESS] {'READY' if readiness.ready else 'NOT READY'}")
    
    for name, check in readiness.checks.items():
        status_icon = "✓" if check["status"] == "ok" else "✗"
        print(f"  {status_icon} {name}: {check['message']}")
    
    print("=" * 60)
    
    return readiness.ready


if __name__ == "__main__":
    import sys
    success = run_health_check()
    sys.exit(0 if success else 1)
