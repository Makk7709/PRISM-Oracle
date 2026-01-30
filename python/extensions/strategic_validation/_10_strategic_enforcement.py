"""
╔══════════════════════════════════════════════════════════════════════════════╗
║              STRATEGIC DOCUMENT ENFORCEMENT — AGENT EXTENSION                ║
║                                                                              ║
║  Extension pour forcer la validation Evidence-grade sur les documents        ║
║  stratégiques (études de marché, prévisionnels, pricing, GTM).              ║
║                                                                              ║
║  PRINCIPE: Un document stratégique non sourcé → FAIL_CLOSED                  ║
║                                                                              ║
║  Hooks utilisés:                                                             ║
║  - monologue_start: Détection du type de requête + enrichissement           ║
║  - response_stream_end: Validation post-génération + FAIL_CLOSED            ║
║                                                                              ║
║  Version: 1.0.0                                                              ║
║  © 2026 Korev AI — Proprietary                                               ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

from __future__ import annotations

import json
import logging
import os
import re
import time
from typing import TYPE_CHECKING, Any, Optional, Dict
from uuid import uuid4

from python.helpers.extension import Extension

if TYPE_CHECKING:
    from agent import Agent, LoopData

# Structured logging
logger = logging.getLogger("strategic_enforcement")

# Import strategic pipeline
try:
    from python.helpers.strategic_pipeline import (
        StrategicRouteContext,
        detect_strategic_context,
        get_strategic_requirements_summary,
    )
    from python.helpers.strategic_contract import (
        StrategicDocumentType,
        StrategicDecision,
        Criticality,
        create_strategic_fail_closed,
        DOCUMENT_REQUIREMENTS,
    )
    STRATEGIC_PIPELINE_AVAILABLE = True
except ImportError as e:
    logger.warning(f"Strategic pipeline not available: {e}")
    STRATEGIC_PIPELINE_AVAILABLE = False
    detect_strategic_context = None
    create_strategic_fail_closed = None


def is_strategic_enforcement_enabled() -> bool:
    """Check if strategic enforcement is enabled."""
    return os.environ.get("STRATEGIC_ENFORCEMENT_ENABLED", "1") == "1"


# ═══════════════════════════════════════════════════════════════════════════════
# EXTENSION CLASS
# ═══════════════════════════════════════════════════════════════════════════════

class StrategicEnforcementExtension(Extension):
    """
    Extension pour enforcer les standards Evidence sur les documents stratégiques.
    
    Hooks utilisés:
    - monologue_start: Détection et marquage des requêtes stratégiques
    - response_stream_end: Validation et FAIL_CLOSED si nécessaire
    """
    
    # ─────────────────────────────────────────────────────────────────────────
    # CONFIGURATION
    # ─────────────────────────────────────────────────────────────────────────
    
    STRATEGIC_CONTEXT_KEY = "_strategic_context"
    STRATEGIC_QUERY_KEY = "_strategic_query"
    CORRELATION_ID_KEY = "_strategic_correlation_id"
    START_TIME_KEY = "_strategic_start_time"
    
    # Minimum sources required for quick validation
    MIN_CITATIONS_QUICK = 3
    
    # Patterns for detecting sourced content
    SOURCE_PATTERNS = [
        r"\[REF-\d+\]",
        r"\[S\d+\]",
        r"Source\s*:\s*\w+",
        r"Eurostat|Gartner|McKinsey|Forrester|IDC|Statista|INSEE",
        r"\(20\d{2}\)",  # Year in parentheses
        r"https?://",    # URLs
        r"\d+\s*Md?\$?€?",  # Numbers with M/Md/$/€
    ]
    
    # Patterns for TAM/SAM/SOM
    TAM_SAM_SOM_PATTERNS = [
        r"\bTAM\b.*\d+",
        r"\bSAM\b.*\d+",
        r"\bSOM\b.*\d+",
        r"Total\s*Addressable\s*Market",
        r"Serviceable\s*Available\s*Market",
        r"Serviceable\s*Obtainable\s*Market",
    ]
    
    # ─────────────────────────────────────────────────────────────────────────
    # HELPERS
    # ─────────────────────────────────────────────────────────────────────────
    
    def is_enforcement_active(self) -> bool:
        """Check if strategic enforcement is active."""
        if not STRATEGIC_PIPELINE_AVAILABLE:
            return False
        return is_strategic_enforcement_enabled()
    
    def extract_user_text(self, loop_data: "LoopData") -> str:
        """Extract user message text from loop_data."""
        if not loop_data or not loop_data.user_message:
            return ""
        
        msg = loop_data.user_message
        msg_content = msg.content if hasattr(msg, 'content') else None
        
        if isinstance(msg_content, dict):
            return (
                msg_content.get("user_message", "") or 
                msg_content.get("message", "") or 
                msg_content.get("text", "") or 
                ""
            )
        elif isinstance(msg_content, str):
            try:
                parsed = json.loads(msg_content.strip().strip('`').replace('json\n', ''))
                return (
                    parsed.get("user_message", "") or 
                    parsed.get("message", "") or 
                    msg_content
                )
            except (json.JSONDecodeError, ValueError):
                return msg_content
        elif msg_content is not None:
            return str(msg_content)
        
        return ""
    
    def count_source_indicators(self, text: str) -> int:
        """Count source indicators in response text."""
        count = 0
        for pattern in self.SOURCE_PATTERNS:
            matches = re.findall(pattern, text, re.IGNORECASE)
            count += len(matches)
        return count
    
    def has_tam_sam_som(self, text: str) -> bool:
        """Check if TAM/SAM/SOM analysis is present."""
        for pattern in self.TAM_SAM_SOM_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                return True
        return False
    
    def quick_validate_response(
        self, 
        response_text: str, 
        context: StrategicRouteContext
    ) -> tuple[bool, list[str]]:
        """
        Quick validation of response against strategic requirements.
        
        Returns:
            (is_valid, missing_requirements)
        """
        missing = []
        
        # Count sources
        source_count = self.count_source_indicators(response_text)
        if source_count < self.MIN_CITATIONS_QUICK:
            missing.append(f"Sources insuffisantes ({source_count} trouvées, minimum 3)")
        
        # Check TAM/SAM/SOM for market studies
        if StrategicDocumentType.MARKET_STUDY in context.document_types:
            if not self.has_tam_sam_som(response_text):
                missing.append("TAM/SAM/SOM absent")
        
        # Check for alternatives
        alternatives_patterns = [
            r"alternative",
            r"option\s*\d",
            r"scénario",
            r"comparaison",
            r"écartée?",
            r"rejetée?",
        ]
        has_alternatives = any(
            re.search(p, response_text, re.IGNORECASE) 
            for p in alternatives_patterns
        )
        if not has_alternatives:
            missing.append("Analyse des alternatives absente")
        
        # Check for hypotheses
        hypothesis_patterns = [
            r"hypothèse",
            r"assumption",
            r"supposant",
            r"si\s+.*alors",
            r"basé\s+sur",
        ]
        has_hypotheses = any(
            re.search(p, response_text, re.IGNORECASE) 
            for p in hypothesis_patterns
        )
        if not has_hypotheses:
            missing.append("Hypothèses non explicites")
        
        is_valid = len(missing) == 0
        return is_valid, missing
    
    def generate_fail_closed_response(
        self,
        context: StrategicRouteContext,
        missing: list[str],
        correlation_id: str,
    ) -> str:
        """Generate FAIL_CLOSED response for unsourced strategic document."""
        
        doc_types_str = ", ".join([dt.value for dt in context.document_types])
        agents_str = ", ".join(context.required_agents)
        
        missing_list = "\n".join([f"- {m}" for m in missing])
        
        # Build requirements table
        req_rows = []
        for dt in context.document_types:
            if dt in DOCUMENT_REQUIREMENTS:
                req = DOCUMENT_REQUIREMENTS[dt]
                req_rows.append(f"| {dt.value} | {req.min_sources}+ | {req.min_public_sources}+ | {'Oui' if req.require_tam_sam_som else 'Non'} |")
        
        req_table = "\n".join(req_rows) if req_rows else "| - | - | - | - |"
        
        return f"""# ⛔ DOCUMENT NON VALIDABLE — FAIL_CLOSED

## Decision Governance

| Paramètre | Valeur |
|-----------|--------|
| **Type document** | `{doc_types_str}` |
| **Criticité** | `{context.criticality.value}` |
| **Mode** | `STRATEGIC_ENFORCEMENT` |
| **Statut** | ⛔ `FAIL_CLOSED` |
| **Correlation ID** | `{correlation_id}` |

---

## ⚠️ Raison du refus

La réponse générée ne respecte pas les standards Evidence pour un document stratégique.

### Exigences non remplies

{missing_list}

### Exigences par type de document

| Type | Sources min | Sources publiques | TAM/SAM/SOM |
|------|-------------|-------------------|-------------|
{req_table}

---

## 📋 Ce qui manque pour validation

Pour générer ce document en mode Evidence :

1. **Sourcing explicite** — Chaque chiffre doit avoir une source [REF-XX]
2. **TAM/SAM/SOM chiffré** — Avec méthodologie et sources
3. **Alternatives analysées** — Options écartées avec justification
4. **Hypothèses explicites** — Listées avec impact

### Agents requis

Les agents suivants doivent être consultés : `{agents_str}`

---

## 🔒 Pourquoi ce refus ?

KOREV Evidence refuse de valider un document stratégique non sourcé car :

1. **Traçabilité** — Un investisseur/board doit pouvoir vérifier chaque chiffre
2. **Auditabilité** — Les décisions basées sur ce document doivent être défendables
3. **Intégrité** — Mieux vaut refuser que produire du contenu non vérifiable

---

*KOREV Evidence — Refus explicite plutôt que contenu non vérifiable.*

`correlation_id: {correlation_id}`
"""
    
    # ─────────────────────────────────────────────────────────────────────────
    # HOOK: monologue_start — Detection and marking
    # ─────────────────────────────────────────────────────────────────────────
    
    async def monologue_start(self, agent: "Agent", loop_data: "LoopData", **kwargs):
        """
        Hook at the start of monologue.
        
        Detects strategic requests and stores context for later validation.
        """
        if not self.is_enforcement_active():
            return
        
        from python.helpers.print_style import PrintStyle
        
        # Extract user text
        user_text = self.extract_user_text(loop_data)
        if not user_text:
            return
        
        # Detect strategic context
        context = detect_strategic_context(user_text)
        
        if not context.is_strategic:
            return
        
        # Generate correlation ID
        correlation_id = str(uuid4())
        
        # Store context for validation in response_stream_end
        agent.set_data(self.STRATEGIC_CONTEXT_KEY, context)
        agent.set_data(self.STRATEGIC_QUERY_KEY, user_text)
        agent.set_data(self.CORRELATION_ID_KEY, correlation_id)
        agent.set_data(self.START_TIME_KEY, time.time())
        
        # Log detection
        PrintStyle(font_color="yellow", bold=True).print(
            f"📊 STRATEGIC DOCUMENT DETECTED: types={[dt.value for dt in context.document_types]}, "
            f"criticality={context.criticality.value}"
        )
        
        agent.context.log.log(
            type="info",
            heading="📊 Strategic Document Detection",
            content=f"Document stratégique détecté — validation Evidence active",
            kvps={
                "correlation_id": correlation_id,
                "document_types": [dt.value for dt in context.document_types],
                "criticality": context.criticality.value,
                "required_agents": context.required_agents,
            }
        )
        
        logger.info(
            f"[{correlation_id}] Strategic document detected: "
            f"types={[dt.value for dt in context.document_types]}, "
            f"criticality={context.criticality.value}"
        )
    
    # ─────────────────────────────────────────────────────────────────────────
    # HOOK: response_stream_end — Post-generation validation
    # ─────────────────────────────────────────────────────────────────────────
    
    async def response_stream_end(self, agent: "Agent", loop_data: "LoopData", **kwargs):
        """
        Hook after response generation.
        
        Validates strategic documents and triggers FAIL_CLOSED if sourcing insufficient.
        """
        if not self.is_enforcement_active():
            return
        
        from python.helpers.print_style import PrintStyle
        
        # Get stored context
        context: Optional[StrategicRouteContext] = agent.get_data(self.STRATEGIC_CONTEXT_KEY)
        if not context or not context.is_strategic:
            return
        
        correlation_id = agent.get_data(self.CORRELATION_ID_KEY) or str(uuid4())
        
        # Get the response
        response_text = loop_data.last_response if loop_data else ""
        if not response_text:
            return
        
        # Quick validate
        is_valid, missing = self.quick_validate_response(response_text, context)
        
        if is_valid:
            # Response passes validation
            PrintStyle(font_color="green", bold=True).print(
                f"✅ STRATEGIC VALIDATION PASSED: Document conforme Evidence"
            )
            
            agent.context.log.log(
                type="info",
                heading="✅ Strategic Validation PASSED",
                content="Document stratégique conforme aux standards Evidence",
                kvps={
                    "correlation_id": correlation_id,
                    "document_types": [dt.value for dt in context.document_types],
                    "validation": "APPROVED",
                }
            )
            
            logger.info(f"[{correlation_id}] Strategic validation PASSED")
            return
        
        # ═══════════════════════════════════════════════════════════════════
        # FAIL_CLOSED: Response does not meet Evidence standards
        # ═══════════════════════════════════════════════════════════════════
        
        PrintStyle(font_color="red", bold=True).print(
            f"⛔ STRATEGIC VALIDATION FAILED: {missing}"
        )
        
        # Generate FAIL_CLOSED response
        fail_closed_response = self.generate_fail_closed_response(
            context=context,
            missing=missing,
            correlation_id=correlation_id,
        )
        
        # Log the failure
        agent.context.log.log(
            type="warning",
            heading="⛔ Strategic Validation FAILED",
            content=f"Document stratégique non conforme — FAIL_CLOSED activé",
            kvps={
                "correlation_id": correlation_id,
                "document_types": [dt.value for dt in context.document_types],
                "criticality": context.criticality.value,
                "missing_requirements": missing,
                "validation": "FAIL_CLOSED",
            }
        )
        
        logger.warning(
            f"[{correlation_id}] Strategic validation FAILED: missing={missing}"
        )
        
        # ═══════════════════════════════════════════════════════════════════
        # CRITICAL: Replace the response with FAIL_CLOSED
        # We modify last_response to inject the fail-closed message
        # ═══════════════════════════════════════════════════════════════════
        
        # Replace the response in loop_data
        loop_data.last_response = fail_closed_response
        
        # Also add a visible log entry for the user
        agent.context.log.log(
            type="response",
            heading=f"{agent.agent_name}",
            content=fail_closed_response,
        )
        
        # Clear stored context
        agent.set_data(self.STRATEGIC_CONTEXT_KEY, None)
        agent.set_data(self.STRATEGIC_QUERY_KEY, None)


# ═══════════════════════════════════════════════════════════════════════════════
# EXPORT
# ═══════════════════════════════════════════════════════════════════════════════

# L'extension est chargée automatiquement par le système d'extensions
