"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                    LEGAL-SAFE MODE — AUDIT LOGGER                           ║
║                                                                              ║
║  Logger NDJSON pour audit et traçabilité des réponses en mode Legal-Safe.   ║
║  Aucune PII stockée, hashes pour intégrité.                                 ║
║                                                                              ║
║  Version: 1.0.0                                                              ║
║  © 2025 Korev AI — Proprietary                                               ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

from __future__ import annotations

import hashlib
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from typing import Any, Optional

from .legal_safe_schema import LegalSafeResponse, ReviewTrigger


# CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════

DEFAULT_LOG_DIR = "logs/legal_safe"
DEFAULT_LOG_FILE = "audit.ndjson"
MAX_LOG_SIZE_MB = 50
MAX_LOG_FILES = 10


# ═══════════════════════════════════════════════════════════════════════════════
# PII DETECTION & REMOVAL
# ═══════════════════════════════════════════════════════════════════════════════

# Patterns de PII à supprimer
PII_PATTERNS = {
    "email": r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
    "phone_fr": r'\b(?:\+33|0)\s*[1-9](?:[\s.-]*\d{2}){4}\b',
    "phone_intl": r'\b\+\d{1,3}[\s.-]?\d{4,14}\b',
    "nir": r'\b[12]\s*\d{2}\s*\d{2}\s*\d{2}\s*\d{3}\s*\d{3}\s*\d{2}\b',
    "iban": r'\b[A-Z]{2}\d{2}[A-Z0-9]{4,30}\b',
    "credit_card": r'\b\d{4}[\s.-]?\d{4}[\s.-]?\d{4}[\s.-]?\d{4}\b',
    "ip_address": r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b',
    "siret": r'\b\d{3}\s*\d{3}\s*\d{3}\s*\d{5}\b',
    "siren": r'\b\d{3}\s*\d{3}\s*\d{3}\b',
}

# Noms propres communs (liste non exhaustive, pour filtrage basique)
# En production, utiliser un NER model


def remove_pii(text: str) -> str:
    """
    Supprime les PII détectables du texte.
    
    Args:
        text: Texte à nettoyer
        
    Returns:
        Texte sans PII
    """
    for pii_type, pattern in PII_PATTERNS.items():
        text = re.sub(pattern, f'[{pii_type.upper()}_REMOVED]', text)
    
    return text


def hash_text(text: str) -> str:
    """
    Crée un hash SHA256 du texte.
    
    Args:
        text: Texte à hasher
        
    Returns:
        Hash hexadécimal préfixé
    """
    return f"sha256:{hashlib.sha256(text.encode()).hexdigest()}"


# ═══════════════════════════════════════════════════════════════════════════════
# LOG ENTRY MODEL
# ═══════════════════════════════════════════════════════════════════════════════

class AuditLogEntry:
    """Entrée de log d'audit."""
    
    def __init__(
        self,
        correlation_id: str,
        timestamp_utc: str,
        mode: str,
        domain: str,
        jurisdiction: str,
        task_type: str,
        complexity: str,
        confidence: float,
        requires_human_review: bool,
        review_triggers: list[str],
        hallucination_risk: str,
        legal_basis_count: int,
        reliable_basis_count: int,
        input_hash: Optional[str] = None,
        response_hash: Optional[str] = None,
        provider: str = "",
        model: str = "",
        latency_ms: int = 0,
        fallback_triggered: bool = False,
        fallback_reason: Optional[str] = None,
        error: Optional[str] = None,
    ):
        self.correlation_id = correlation_id
        self.timestamp_utc = timestamp_utc
        self.mode = mode
        self.domain = domain
        self.jurisdiction = jurisdiction
        self.task_type = task_type
        self.complexity = complexity
        self.confidence = confidence
        self.requires_human_review = requires_human_review
        self.review_triggers = review_triggers
        self.hallucination_risk = hallucination_risk
        self.legal_basis_count = legal_basis_count
        self.reliable_basis_count = reliable_basis_count
        self.input_hash = input_hash
        self.response_hash = response_hash
        self.provider = provider
        self.model = model
        self.latency_ms = latency_ms
        self.fallback_triggered = fallback_triggered
        self.fallback_reason = fallback_reason
        self.error = error
    
    def to_dict(self) -> dict[str, Any]:
        """Convertit en dictionnaire pour JSON."""
        return {
            "correlation_id": self.correlation_id,
            "timestamp_utc": self.timestamp_utc,
            "mode": self.mode,
            "domain": self.domain,
            "jurisdiction": self.jurisdiction,
            "task_type": self.task_type,
            "complexity": self.complexity,
            "confidence": self.confidence,
            "requires_human_review": self.requires_human_review,
            "review_triggers": self.review_triggers,
            "hallucination_risk": self.hallucination_risk,
            "legal_basis_count": self.legal_basis_count,
            "reliable_basis_count": self.reliable_basis_count,
            "input_hash": self.input_hash,
            "response_hash": self.response_hash,
            "provider": self.provider,
            "model": self.model,
            "latency_ms": self.latency_ms,
            "fallback_triggered": self.fallback_triggered,
            "fallback_reason": self.fallback_reason,
            "error": self.error,
        }
    
    def to_json(self) -> str:
        """Convertit en ligne JSON."""
        return json.dumps(self.to_dict(), ensure_ascii=False)
    
    @classmethod
    def from_response(
        cls,
        response: LegalSafeResponse,
        input_text: Optional[str] = None,
        error: Optional[str] = None,
    ) -> "AuditLogEntry":
        """
        Crée une entrée de log à partir d'une réponse.
        
        Args:
            response: Réponse LegalSafeResponse
            input_text: Texte de la question (sera hashé, pas stocké)
            error: Message d'erreur éventuel
            
        Returns:
            AuditLogEntry
        """
        # Calcul des bases légales fiables
        from .legal_safe_schema import Reliability
        reliable_count = sum(
            1 for lb in response.legal_basis
            if lb.reliability in [Reliability.HIGH, Reliability.MEDIUM]
        )
        
        # Hash de l'input si fourni
        input_hash = None
        if input_text:
            cleaned_input = remove_pii(input_text)
            input_hash = hash_text(cleaned_input)
        
        return cls(
            correlation_id=response.meta.correlation_id,
            timestamp_utc=response.meta.timestamp_utc,
            mode=response.mode,
            domain=response.classification.domain.value,
            jurisdiction=response.scope.jurisdiction_requested.value,
            task_type=response.classification.task_type.value,
            complexity=response.classification.complexity.value,
            confidence=response.conclusion.confidence,
            requires_human_review=response.safety.requires_human_review,
            review_triggers=[t.value for t in response.safety.review_triggers],
            hallucination_risk=response.safety.hallucination_risk.value,
            legal_basis_count=len(response.legal_basis),
            reliable_basis_count=reliable_count,
            input_hash=input_hash or response.meta.input_hash,
            response_hash=response.meta.response_hash,
            provider=response.meta.provider,
            model=response.meta.model,
            latency_ms=response.meta.latency_ms,
            fallback_triggered=response.fallback.triggered,
            fallback_reason=remove_pii(response.fallback.reason) if response.fallback.reason else None,
            error=remove_pii(error) if error else None,
        )


# ═══════════════════════════════════════════════════════════════════════════════
# LOGGER CLASS
# ═══════════════════════════════════════════════════════════════════════════════

class LegalSafeLogger:
    """
    Logger NDJSON thread-safe pour le mode Legal-Safe.
    
    Caractéristiques:
    - Append-only (NDJSON)
    - Pas de PII
    - Rotation automatique
    - Thread-safe
    """
    
    _instance: Optional["LegalSafeLogger"] = None
    _lock = Lock()
    
    def __init__(self, log_dir: Optional[str] = None):
        """
        Initialise le logger.
        
        Args:
            log_dir: Répertoire de logs (défaut: logs/legal_safe)
        """
        self.log_dir = Path(log_dir) if log_dir else Path(DEFAULT_LOG_DIR)
        self.log_file = self.log_dir / DEFAULT_LOG_FILE
        self._file_lock = Lock()
        
        # Créer le répertoire si nécessaire
        self.log_dir.mkdir(parents=True, exist_ok=True)
    
    @classmethod
    def get_instance(cls, log_dir: Optional[str] = None) -> "LegalSafeLogger":
        """Singleton pattern."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls(log_dir)
        return cls._instance
    
    def log(
        self,
        response: LegalSafeResponse,
        input_text: Optional[str] = None,
        error: Optional[str] = None,
    ) -> AuditLogEntry:
        """
        Log une réponse.
        
        Args:
            response: Réponse à logger
            input_text: Question originale (sera hashée)
            error: Erreur éventuelle
            
        Returns:
            L'entrée de log créée
        """
        entry = AuditLogEntry.from_response(response, input_text, error)
        
        with self._file_lock:
            self._check_rotation()
            
            with open(self.log_file, "a", encoding="utf-8") as f:
                f.write(entry.to_json() + "\n")
        
        return entry
    
    def log_error(
        self,
        correlation_id: str,
        error: str,
        input_text: Optional[str] = None,
    ) -> AuditLogEntry:
        """
        Log une erreur sans réponse complète.
        
        Args:
            correlation_id: ID de corrélation
            error: Message d'erreur
            input_text: Question originale
            
        Returns:
            L'entrée de log créée
        """
        entry = AuditLogEntry(
            correlation_id=correlation_id,
            timestamp_utc=datetime.now(timezone.utc).isoformat(),
            mode="legal_safe",
            domain="unknown",
            jurisdiction="UNKNOWN",
            task_type="unknown",
            complexity="unknown",
            confidence=0.0,
            requires_human_review=True,
            review_triggers=["error"],
            hallucination_risk="high",
            legal_basis_count=0,
            reliable_basis_count=0,
            input_hash=hash_text(remove_pii(input_text)) if input_text else None,
            response_hash=None,
            provider="",
            model="",
            latency_ms=0,
            fallback_triggered=True,
            fallback_reason="Error during processing",
            error=remove_pii(error),
        )
        
        with self._file_lock:
            self._check_rotation()
            
            with open(self.log_file, "a", encoding="utf-8") as f:
                f.write(entry.to_json() + "\n")
        
        return entry
    
    def _check_rotation(self):
        """Vérifie si une rotation de log est nécessaire."""
        if not self.log_file.exists():
            return
        
        size_mb = self.log_file.stat().st_size / (1024 * 1024)
        
        if size_mb >= MAX_LOG_SIZE_MB:
            self._rotate()
    
    def _rotate(self):
        """Effectue une rotation des logs."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        rotated_name = f"audit_{timestamp}.ndjson"
        rotated_path = self.log_dir / rotated_name
        
        # Renommer le fichier actuel
        self.log_file.rename(rotated_path)
        
        # Supprimer les anciens fichiers si trop nombreux
        log_files = sorted(
            self.log_dir.glob("audit_*.ndjson"),
            key=lambda p: p.stat().st_mtime,
            reverse=True
        )
        
        for old_file in log_files[MAX_LOG_FILES:]:
            old_file.unlink()
    
    def read_logs(
        self,
        limit: int = 100,
        filters: Optional[dict[str, Any]] = None,
    ) -> list[dict[str, Any]]:
        """
        Lit les dernières entrées de log.
        
        Args:
            limit: Nombre max d'entrées
            filters: Filtres optionnels (ex: {"requires_human_review": True})
            
        Returns:
            Liste des entrées de log
        """
        if not self.log_file.exists():
            return []
        
        entries: list[dict[str, Any]] = []
        
        with open(self.log_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                
                try:
                    entry = json.loads(line)
                    
                    # Appliquer les filtres
                    if filters:
                        match = all(
                            entry.get(k) == v
                            for k, v in filters.items()
                        )
                        if not match:
                            continue
                    
                    entries.append(entry)
                except json.JSONDecodeError:
                    continue
        
        # Retourner les dernières entrées
        return entries[-limit:]
    
    def get_stats(self) -> dict[str, Any]:
        """
        Calcule des statistiques sur les logs.
        
        Returns:
            Dictionnaire de statistiques
        """
        entries = self.read_logs(limit=10000)
        
        if not entries:
            return {
                "total_entries": 0,
                "escalation_rate": 0.0,
                "avg_confidence": 0.0,
                "domain_distribution": {},
                "trigger_frequency": {},
            }
        
        total = len(entries)
        escalated = sum(1 for e in entries if e.get("requires_human_review"))
        confidences = [e.get("confidence", 0) for e in entries]
        
        # Distribution par domaine
        domains: dict[str, int] = {}
        for e in entries:
            d = e.get("domain", "unknown")
            domains[d] = domains.get(d, 0) + 1
        
        # Fréquence des triggers
        triggers: dict[str, int] = {}
        for e in entries:
            for t in e.get("review_triggers", []):
                triggers[t] = triggers.get(t, 0) + 1
        
        return {
            "total_entries": total,
            "escalation_rate": escalated / total if total > 0 else 0.0,
            "avg_confidence": sum(confidences) / total if total > 0 else 0.0,
            "domain_distribution": domains,
            "trigger_frequency": triggers,
        }


# ═══════════════════════════════════════════════════════════════════════════════
# CONVENIENCE FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════════

def log_legal_safe_response(
    response: LegalSafeResponse,
    input_text: Optional[str] = None,
    error: Optional[str] = None,
) -> AuditLogEntry:
    """
    Fonction de commodité pour logger une réponse.
    
    Args:
        response: Réponse à logger
        input_text: Question originale
        error: Erreur éventuelle
        
    Returns:
        L'entrée de log
    """
    return LegalSafeLogger.get_instance().log(response, input_text, error)


def log_legal_safe_error(
    correlation_id: str,
    error: str,
    input_text: Optional[str] = None,
) -> AuditLogEntry:
    """
    Fonction de commodité pour logger une erreur.
    
    Args:
        correlation_id: ID de corrélation
        error: Message d'erreur
        input_text: Question originale
        
    Returns:
        L'entrée de log
    """
    return LegalSafeLogger.get_instance().log_error(correlation_id, error, input_text)


# EXPORTS
# ═══════════════════════════════════════════════════════════════════════════════

__all__ = [
    "remove_pii",
    "hash_text",
    "AuditLogEntry",
    "LegalSafeLogger",
    "log_legal_safe_response",
    "log_legal_safe_error",
]
