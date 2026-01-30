"""
╔══════════════════════════════════════════════════════════════════════════════╗
║            STRATEGIC DOCUMENT ENFORCEMENT — MONOLOGUE_START HOOK             ║
║                                                                              ║
║  Détecte les requêtes de documents stratégiques et lance le pipeline        ║
║  multi-agent avec validation Evidence.                                       ║
║                                                                              ║
║  Si activé: court-circuite le LLM principal et exécute:                      ║
║  1. Détection du type de document                                            ║
║  2. Appel des agents spécialisés (researcher, finance, marketing)           ║
║  3. Validation des sources et du contenu                                     ║
║  4. FAIL_CLOSED si standards non respectés                                   ║
║                                                                              ║
║  Version: 1.0.0                                                              ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""
import json
import logging
from uuid import uuid4

from python.helpers.extension import Extension
from python.helpers.print_style import PrintStyle
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from agent import Agent, LoopData

logger = logging.getLogger("strategic_enforcement_hook")

# Import orchestrator
try:
    from python.helpers.strategic_orchestrator import (
        detect_strategic_document,
        run_strategic_orchestrator,
        is_strategic_orchestrator_enabled,
        StrategicDetection,
    )
    ORCHESTRATOR_AVAILABLE = True
except ImportError as e:
    logger.warning(f"Strategic orchestrator not available: {e}")
    ORCHESTRATOR_AVAILABLE = False
    is_strategic_orchestrator_enabled = lambda: False


class StrategicEnforcementMonologueHook(Extension):
    """
    Détecte les documents stratégiques et lance le pipeline multi-agent.
    
    Court-circuite le LLM principal si une requête stratégique est détectée.
    """
    
    def _extract_user_text(self, loop_data) -> str:
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
    
    async def execute(self, loop_data: "LoopData" = None, **kwargs):
        """
        Execute strategic document detection and orchestration.
        
        If a strategic document is detected:
        1. Run multi-agent pipeline
        2. Validate output
        3. Short-circuit LLM with pipeline response
        """
        if not ORCHESTRATOR_AVAILABLE:
            return
        
        if not is_strategic_orchestrator_enabled():
            return
        
        # Extract user text
        user_text = self._extract_user_text(loop_data)
        if not user_text:
            return
        
        # Detect strategic document
        detection = detect_strategic_document(user_text)
        
        if not detection.is_strategic:
            return
        
        # Generate correlation ID
        correlation_id = str(uuid4())
        
        # Log detection
        PrintStyle(font_color="yellow", bold=True).print(
            f"📊 STRATEGIC DOCUMENT DETECTED: type={detection.document_type}, "
            f"agents={detection.required_agents}"
        )
        
        self.agent.context.log.log(
            type="info",
            heading="📊 Strategic Pipeline Started",
            content=f"Document stratégique détecté — Lancement pipeline multi-agent",
            kvps={
                "correlation_id": correlation_id,
                "document_type": detection.document_type,
                "required_agents": detection.required_agents,
                "min_sources": detection.min_sources,
            }
        )
        
        logger.info(
            f"[{correlation_id}] Strategic document detected: "
            f"type={detection.document_type}, agents={detection.required_agents}"
        )
        
        try:
            # Run the strategic orchestrator
            result = await run_strategic_orchestrator(
                agent=self.agent,
                query=user_text,
                detection=detection,
                correlation_id=correlation_id,
            )
            
            # Log result
            if result.validation_passed:
                PrintStyle(font_color="green", bold=True).print(
                    f"✅ STRATEGIC VALIDATION PASSED: {result.total_sources} sources, "
                    f"{result.duration_ms}ms"
                )
                
                self.agent.context.log.log(
                    type="info",
                    heading="✅ Strategic Pipeline APPROVED",
                    content=f"Document validé avec {result.total_sources} sources",
                    kvps={
                        "correlation_id": correlation_id,
                        "total_sources": result.total_sources,
                        "duration_ms": result.duration_ms,
                        "validation": "APPROVED",
                    }
                )
            else:
                PrintStyle(font_color="red", bold=True).print(
                    f"⛔ STRATEGIC VALIDATION FAILED: {result.fail_reason}"
                )
                
                self.agent.context.log.log(
                    type="warning",
                    heading="⛔ Strategic Pipeline FAIL_CLOSED",
                    content=f"Document non validé: {result.fail_reason}",
                    kvps={
                        "correlation_id": correlation_id,
                        "total_sources": result.total_sources,
                        "fail_reason": result.fail_reason,
                        "validation": "FAIL_CLOSED",
                    }
                )
            
            # ═══════════════════════════════════════════════════════════════════
            # CRITICAL: Short-circuit LLM with pipeline response
            # ═══════════════════════════════════════════════════════════════════
            self.agent.set_data("_pipeline_final_response", result.consolidated_response)
            self.agent.set_data("_skip_llm", True)
            self.agent.set_data("_pipeline_was_used", True)
            self.agent.set_data("_strategic_result", result)
            self.agent.set_data("_strategic_correlation_id", correlation_id)
            
            logger.info(
                f"[{correlation_id}] Strategic pipeline completed: "
                f"validation={result.validation_passed}, llm_bypassed=True"
            )
            
        except Exception as e:
            logger.error(f"[{correlation_id}] Strategic orchestrator failed: {e}")
            import traceback
            traceback.print_exc()
            
            # On error, allow LLM fallback but log warning
            self.agent.context.log.log(
                type="error",
                heading="⚠️ Strategic Pipeline ERROR",
                content=f"Pipeline failed: {str(e)[:200]}",
                kvps={
                    "correlation_id": correlation_id,
                    "error": str(e)[:500],
                    "llm_fallback": True,
                }
            )
            
            # Do NOT set _skip_llm - let the LLM respond as fallback
