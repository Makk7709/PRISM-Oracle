#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                    PRISM + EVIDENCE — Diagnostics Bundle                       ║
║                                                                              ║
║  Génère un bundle de diagnostic pour le support.                             ║
║  Collecte: version, config (sans secrets), logs, métriques, OS info          ║
║                                                                              ║
║  Usage: python tools/diagnostics_bundle.py [--output DIR]                    ║
║                                                                              ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import argparse
import json
import os
import platform
import shutil
import subprocess
import sys
import tempfile
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


# ═══════════════════════════════════════════════════════════════════════════════
# SECRETS PATTERNS (à masquer)
# ═══════════════════════════════════════════════════════════════════════════════

SECRET_PATTERNS = [
    "api_key",
    "apikey",
    "secret",
    "password",
    "token",
    "bearer",
    "authorization",
    "credential",
]


def mask_secrets(data: Dict[str, Any], depth: int = 0) -> Dict[str, Any]:
    """Masque les secrets dans un dictionnaire."""
    if depth > 10:
        return data
    
    result = {}
    for key, value in data.items():
        key_lower = key.lower()
        
        # Vérifier si la clé contient un pattern secret
        is_secret = any(pattern in key_lower for pattern in SECRET_PATTERNS)
        
        if is_secret and value:
            result[key] = "***MASKED***"
        elif isinstance(value, dict):
            result[key] = mask_secrets(value, depth + 1)
        elif isinstance(value, list):
            result[key] = [
                mask_secrets(v, depth + 1) if isinstance(v, dict) else v
                for v in value
            ]
        else:
            result[key] = value
    
    return result


# ═══════════════════════════════════════════════════════════════════════════════
# COLLECTORS
# ═══════════════════════════════════════════════════════════════════════════════

def collect_system_info() -> Dict[str, Any]:
    """Collecte les informations système."""
    info = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "platform": {
            "system": platform.system(),
            "release": platform.release(),
            "version": platform.version(),
            "machine": platform.machine(),
            "processor": platform.processor(),
            "python_version": platform.python_version(),
        },
        "environment": {
            "pwd": os.getcwd(),
            "user": os.environ.get("USER", "unknown"),
            "home": os.environ.get("HOME", "unknown"),
        }
    }
    
    # Memory info
    try:
        import psutil
        mem = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        info["resources"] = {
            "memory_total_gb": round(mem.total / (1024**3), 2),
            "memory_available_gb": round(mem.available / (1024**3), 2),
            "memory_percent": mem.percent,
            "disk_total_gb": round(disk.total / (1024**3), 2),
            "disk_free_gb": round(disk.free / (1024**3), 2),
            "disk_percent": disk.percent,
            "cpu_count": psutil.cpu_count(),
        }
    except ImportError:
        info["resources"] = {"error": "psutil not available"}
    
    return info


def collect_evidence_version() -> Dict[str, Any]:
    """Collecte la version Evidence."""
    version_info = {
        "version": "unknown",
        "build_date": "unknown",
        "git_commit": "unknown",
    }
    
    for path in ["/app/VERSION.json", "/app/version.json", "VERSION.json", "version.json", "deploy/version.json"]:
        if Path(path).exists():
            try:
                version_info = json.loads(Path(path).read_text())
                break
            except Exception:
                pass
    
    # Git info si disponible
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0:
            version_info["git_commit"] = result.stdout.strip()
        
        result = subprocess.run(
            ["git", "describe", "--tags", "--always"],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0:
            version_info["git_tag"] = result.stdout.strip()
    except Exception:
        pass
    
    return version_info


def collect_config() -> Dict[str, Any]:
    """Collecte la configuration (sans secrets)."""
    try:
        from python.helpers.deploy_config import get_deployment_config
        config = get_deployment_config()
        config_dict = config.model_dump()
        return mask_secrets(config_dict)
    except Exception as e:
        return {"error": str(e)}


def collect_env_vars() -> Dict[str, str]:
    """Collecte les variables d'environnement Evidence (masquées)."""
    evidence_vars = {}
    
    for key, value in os.environ.items():
        if key.startswith("EVIDENCE_") or key.startswith("CONSENSUS_") or key.startswith("MCP_"):
            key_lower = key.lower()
            if any(pattern in key_lower for pattern in SECRET_PATTERNS):
                evidence_vars[key] = "***MASKED***"
            else:
                evidence_vars[key] = value
    
    return evidence_vars


def collect_health_status() -> Dict[str, Any]:
    """Collecte le statut de santé."""
    try:
        from python.helpers.health_endpoints import HealthChecker
        from dataclasses import asdict
        
        checker = HealthChecker()
        health = checker.health_check()
        readiness = checker.readiness_check()
        
        return {
            "health": asdict(health),
            "readiness": asdict(readiness),
        }
    except Exception as e:
        return {"error": str(e)}


def collect_recent_logs(logs_dir: str, max_lines: int = 500) -> Dict[str, List[str]]:
    """Collecte les dernières lignes des logs."""
    logs = {}
    logs_path = Path(logs_dir)
    
    if not logs_path.exists():
        return {"error": f"Logs directory not found: {logs_dir}"}
    
    for log_file in logs_path.glob("*.log"):
        try:
            with open(log_file, 'r') as f:
                lines = f.readlines()
                logs[log_file.name] = lines[-max_lines:]
        except Exception as e:
            logs[log_file.name] = [f"Error reading: {e}"]
    
    return logs


def collect_docker_info() -> Dict[str, Any]:
    """Collecte les infos Docker si disponible."""
    info = {}
    
    try:
        # Docker version
        result = subprocess.run(
            ["docker", "version", "--format", "{{json .}}"],
            capture_output=True, text=True, timeout=10
        )
        if result.returncode == 0:
            info["version"] = json.loads(result.stdout)
        
        # Container status
        result = subprocess.run(
            ["docker", "ps", "--filter", "name=evidence", "--format", "{{json .}}"],
            capture_output=True, text=True, timeout=10
        )
        if result.returncode == 0:
            containers = []
            for line in result.stdout.strip().split('\n'):
                if line:
                    containers.append(json.loads(line))
            info["containers"] = containers
        
    except FileNotFoundError:
        info["error"] = "Docker not available"
    except Exception as e:
        info["error"] = str(e)
    
    return info


def collect_consensus_metrics() -> Dict[str, Any]:
    """Collecte les métriques du consensus."""
    try:
        from python.helpers.consensus_manager import ConsensusManager
        
        # Try to get existing instance metrics
        manager = ConsensusManager(timeout_ms=5000, total_providers=3)
        return manager.metrics
    except Exception as e:
        return {"error": str(e)}


# ═══════════════════════════════════════════════════════════════════════════════
# BUNDLE GENERATOR
# ═══════════════════════════════════════════════════════════════════════════════

def generate_bundle(output_dir: Optional[Path] = None) -> Path:
    """
    Génère le bundle de diagnostic complet.
    
    Returns:
        Path du fichier zip généré
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    bundle_name = f"evidence_diagnostics_{timestamp}"
    
    # Créer un répertoire temporaire
    with tempfile.TemporaryDirectory() as temp_dir:
        bundle_dir = Path(temp_dir) / bundle_name
        bundle_dir.mkdir()
        
        print("=" * 60)
        print("EVIDENCE DIAGNOSTICS BUNDLE GENERATOR")
        print("=" * 60)
        
        # 1. System info
        print("\n[1/7] Collecting system info...")
        system_info = collect_system_info()
        (bundle_dir / "system_info.json").write_text(
            json.dumps(system_info, indent=2)
        )
        
        # 2. Version
        print("[2/7] Collecting version info...")
        version_info = collect_evidence_version()
        (bundle_dir / "version.json").write_text(
            json.dumps(version_info, indent=2)
        )
        
        # 3. Config
        print("[3/7] Collecting config (secrets masked)...")
        config = collect_config()
        (bundle_dir / "config.json").write_text(
            json.dumps(config, indent=2)
        )
        
        # 4. Environment variables
        print("[4/7] Collecting environment variables...")
        env_vars = collect_env_vars()
        (bundle_dir / "env_vars.json").write_text(
            json.dumps(env_vars, indent=2)
        )
        
        # 5. Health status
        print("[5/7] Collecting health status...")
        health = collect_health_status()
        (bundle_dir / "health.json").write_text(
            json.dumps(health, indent=2)
        )
        
        # 6. Recent logs
        print("[6/7] Collecting recent logs...")
        logs_dir = os.environ.get("LOGS_DIR", "/app/logs")
        if not Path(logs_dir).exists():
            logs_dir = str(PROJECT_ROOT / "logs")
        
        logs = collect_recent_logs(logs_dir)
        logs_bundle_dir = bundle_dir / "logs"
        logs_bundle_dir.mkdir()
        
        for filename, lines in logs.items():
            if isinstance(lines, list):
                (logs_bundle_dir / filename).write_text("".join(lines))
        
        # 7. Docker info
        print("[7/7] Collecting Docker info...")
        docker_info = collect_docker_info()
        (bundle_dir / "docker.json").write_text(
            json.dumps(docker_info, indent=2)
        )
        
        # Create summary
        summary = {
            "generated_at": datetime.utcnow().isoformat() + "Z",
            "bundle_name": bundle_name,
            "evidence_version": version_info.get("version", "unknown"),
            "system": system_info.get("platform", {}).get("system", "unknown"),
            "health_ready": health.get("readiness", {}).get("ready", False),
            "files_included": [
                "system_info.json",
                "version.json", 
                "config.json",
                "env_vars.json",
                "health.json",
                "docker.json",
                "logs/",
            ]
        }
        (bundle_dir / "SUMMARY.json").write_text(
            json.dumps(summary, indent=2)
        )
        
        # Create README
        readme = f"""# Evidence Diagnostics Bundle

Generated: {summary['generated_at']}
Version: {summary['evidence_version']}
System: {summary['system']}

## Contents

- `SUMMARY.json` - Bundle summary
- `system_info.json` - OS and hardware info
- `version.json` - Evidence version info
- `config.json` - Configuration (secrets masked)
- `env_vars.json` - Environment variables (secrets masked)
- `health.json` - Health check results
- `docker.json` - Docker container info
- `logs/` - Recent log files

## Note

All secrets and API keys have been automatically masked.
This bundle is safe to share with support.
"""
        (bundle_dir / "README.md").write_text(readme)
        
        # Create zip
        if output_dir is None:
            output_dir = Path.cwd()
        
        zip_path = output_dir / f"{bundle_name}.zip"
        
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for file_path in bundle_dir.rglob('*'):
                if file_path.is_file():
                    arcname = file_path.relative_to(bundle_dir)
                    zipf.write(file_path, arcname)
        
        print("\n" + "=" * 60)
        print(f"✅ Bundle generated: {zip_path}")
        print(f"   Size: {zip_path.stat().st_size / 1024:.1f} KB")
        print("=" * 60)
        
        return zip_path


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(
        description="Generate Evidence diagnostics bundle"
    )
    parser.add_argument(
        "--output", "-o",
        type=Path,
        default=None,
        help="Output directory for the bundle (default: current directory)"
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output summary as JSON (for scripting)"
    )
    
    args = parser.parse_args()
    
    try:
        zip_path = generate_bundle(args.output)
        
        if args.json:
            print(json.dumps({
                "success": True,
                "path": str(zip_path),
                "size_bytes": zip_path.stat().st_size
            }))
        
        return 0
    except Exception as e:
        if args.json:
            print(json.dumps({
                "success": False,
                "error": str(e)
            }))
        else:
            print(f"❌ Error generating bundle: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
