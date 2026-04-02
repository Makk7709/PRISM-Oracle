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
        export_strategic_pdf_for_context,
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
        """
        Extract user message text from loop_data.
        
        Handles various message formats:
        - String content
        - Dict with 'user_message', 'message', or 'text' keys
        - Raw message with 'raw_content' or 'preview'
        - JSON-encoded strings
        """
        if not loop_data or not loop_data.user_message:
            return ""
        
        msg = loop_data.user_message
        msg_content = msg.content if hasattr(msg, 'content') else None
        
        if msg_content is None:
            return ""
        
        # String content - most common case
        if isinstance(msg_content, str):
            # Check if it's JSON-encoded
            try:
                parsed = json.loads(msg_content.strip().strip('`').replace('json\n', ''))
                if isinstance(parsed, dict):
                    return (
                        parsed.get("user_message", "") or 
                        parsed.get("message", "") or 
                        parsed.get("text", "") or
                        msg_content
                    )
            except (json.JSONDecodeError, ValueError):
                pass
            return msg_content
        
        # Dict content - check various keys
        if isinstance(msg_content, dict):
            # Check for raw message format
            if "raw_content" in msg_content:
                raw = msg_content.get("raw_content", "")
                if isinstance(raw, str):
                    return raw
                elif isinstance(raw, dict):
                    return (
                        raw.get("user_message", "") or
                        raw.get("message", "") or
                        raw.get("text", "") or
                        str(raw)
                    )
            
            # Check for preview (used in raw messages)
            if "preview" in msg_content and msg_content.get("preview"):
                return str(msg_content["preview"])
            
            # Standard dict keys
            return (
                msg_content.get("user_message", "") or 
                msg_content.get("message", "") or 
                msg_content.get("text", "") or 
                ""
            )
        
        # List content - concatenate strings
        if isinstance(msg_content, list):
            parts = []
            for item in msg_content:
                if isinstance(item, str):
                    parts.append(item)
                elif isinstance(item, dict):
                    parts.append(
                        item.get("user_message", "") or 
                        item.get("message", "") or 
                        item.get("text", "") or
                        ""
                    )
            return " ".join(filter(None, parts))
        
        # Fallback - stringify
        return str(msg_content)
    
    async def execute(self, loop_data: "LoopData" = None, **kwargs):
        """
        Execute strategic document detection and orchestration.
        
        If a strategic document is detected:
        1. Run multi-agent pipeline
        2. Validate output
        3. Short-circuit LLM with pipeline response
        """
        # Debug: Always visible print for troubleshooting
        PrintStyle(font_color="cyan").print("[STRATEGIC_HOOK] execute() called")
        logger.info("[STRATEGIC_HOOK] execute() called")
        
        if not ORCHESTRATOR_AVAILABLE:
            logger.warning("[STRATEGIC_HOOK] Orchestrator not available")
            return
        
        if not is_strategic_orchestrator_enabled():
            logger.info("[STRATEGIC_HOOK] Orchestrator disabled")
            return
        
        # Extract user text
        user_text = self._extract_user_text(loop_data)
        PrintStyle(font_color="cyan").print(f"[STRATEGIC_HOOK] Extracted: {user_text[:80] if user_text else 'EMPTY'}...")
        
        if not user_text:
            PrintStyle(font_color="gray").print("[STRATEGIC_HOOK] No user text, skipping")
            return
        
        # ─── Check if legal pipeline already claimed this request ─────────
        # If _skip_llm is already set (by legal hook running first via _10_),
        # do NOT override with strategic pipeline.
        if self.agent.get_data("_skip_llm"):
            PrintStyle(font_color="gray").print(
                "[STRATEGIC_HOOK] Another pipeline already active (_skip_llm=True). Skipping."
            )
            return
        
        # Detect strategic document
        detection = detect_strategic_document(user_text)
        PrintStyle(font_color="cyan").print(f"[STRATEGIC_HOOK] Detection: is_strategic={detection.is_strategic}, type={detection.document_type}")
        
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
            final_response = result.consolidated_response
            if result.validation_passed:
                export_info = export_strategic_pdf_for_context(agent=self.agent, result=result)
                if export_info:
                    final_response += (
                        "\n\n---\n\n"
                        "📄 **Version PDF générée**\n\n"
                        f"[📄 Télécharger {export_info['filename']}]({export_info['download_url']})\n"
                    )
                    self.agent.set_data("_strategic_pdf_path", export_info["absolute_path"])
                    self.agent.set_data("_strategic_pdf_download_url", export_info["download_url"])
                else:
                    final_response += (
                        "\n\n⚠️ Export PDF automatique indisponible dans ce contexte. "
                        "Demandez explicitement l'export PDF si nécessaire."
                    )
            self.agent.set_data("_pipeline_final_response", final_response)
            self.agent.set_data("_skip_llm", True)
            self.agent.set_data("_pipeline_was_used", True)
            self.agent.set_data("_strategic_result", result)
            self.agent.set_data("_strategic_correlation_id", correlation_id)

            self._persist_route_decision(result, detection, correlation_id)
            
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

    def _persist_route_decision(self, result, detection, correlation_id: str) -> None:
        """Build and persist a RouteDecision for the audit report (SESSION 11).

        Derives ai_act_category from the agents actually mobilised and
        routing_strength from the pipeline quality signals (source count,
        validation outcome).  Stored as ``_route_decision_v2`` so that
        ``_20_audit_metadata_append`` picks it up via its existing resolver.
        """
        try:
            from python.helpers.router.routing_contract import (
                RouteDecision, RouteIntent, RouteVerdict, IntentName,
                AIActCategory, get_ai_act_category,
            )

            intent_map = {
                "researcher": IntentName.RESEARCHER,
                "finance": IntentName.FINANCE,
                "marketing": IntentName.MARKETING,
                "sales": IntentName.SALES,
            }

            intents = []
            for resp in result.responses:
                intent_name = intent_map.get(resp.profile)
                if intent_name is not None:
                    score = 1.0 if resp.success else 0.2
                    intents.append(RouteIntent(
                        name=intent_name, score=score, is_required=True,
                    ))

            if not intents:
                intents.append(RouteIntent(
                    name=IntentName.RESEARCHER, score=0.8, is_required=True,
                ))

            min_sources = getattr(detection, "min_sources", 10) or 10
            source_ratio = min(result.total_sources / max(min_sources, 1), 1.0)
            validation_bonus = 0.2 if result.validation_passed else 0.0
            strength = round(min(source_ratio * 0.8 + validation_bonus, 1.0), 3)
            _RISK_ORDER = {
                AIActCategory.UNACCEPTABLE: 4,
                AIActCategory.HIGH_RISK: 3,
                AIActCategory.LIMITED_RISK: 2,
                AIActCategory.MINIMAL_RISK: 1,
            }
            highest_cat = max(
                (get_ai_act_category(i.name) for i in intents),
                key=lambda c: _RISK_ORDER.get(c, 0),
            )

            rd = RouteDecision(
                verdict=RouteVerdict.PROCEED,
                intents=intents,
                routing_strength=strength,
                is_board_level=True,
                reasons=[
                    f"Strategic pipeline: {detection.document_type}",
                    f"{result.total_sources} sources, "
                    f"{'PASS' if result.validation_passed else 'FAIL_CLOSED'}",
                ],
                route_id=correlation_id,
                ai_act_category=highest_cat,
            )

            self.agent.set_data("_route_decision_v2", rd.to_dict())
            logger.info(
                "[%s] RouteDecision persisted: ai_act=%s, strength=%.3f",
                correlation_id,
                rd.ai_act_category.value if rd.ai_act_category else "unknown",
                rd.routing_strength,
            )
        except Exception as exc:
            logger.warning("_persist_route_decision failed (non-blocking): %s", exc)
