"""
╔══════════════════════════════════════════════════════════════════════════════╗
║         API ENDPOINT — ADVERSARIAL INSTRUCTION ANALYSIS                      ║
║                                                                              ║
║  POST /adversarial_analyze                                                   ║
║                                                                              ║
║  Lance une analyse adversariale intégrée avec PRISM Consensus.               ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import json
import logging
import traceback

from python.helpers.api import ApiHandler, Request, Response
from python.helpers.print_style import PrintStyle

logger = logging.getLogger("api.adversarial")


class AdversarialAnalyze(ApiHandler):
    """
    Lance une analyse adversariale sur une question.
    
    POST /adversarial_analyze
    {
        "query": "Ma question...",
        "context": { ... },          // Optionnel
        "agent_profile": "legal_safe", // Optionnel
        "force_consensus": false     // Optionnel
    }
    
    Returns:
    {
        "dossier_id": "xxx",
        "status": "awaiting_human_decision",
        "domain": "legal",
        "criticality": "high",
        "protocol": "reinforced",
        "phases_completed": [...],
        "summary": {...}
    }
    """
    
    async def process(self, input: dict, request: Request) -> dict | Response:
        from python.helpers.adversarial_consensus_integration import (
            get_adversarial_pipeline,
        )
        
        PrintStyle(font_color="magenta", bold=True).print(
            f"📋 AdversarialAnalyze API called"
        )
        
        # Parse input
        data = request.get_json() if request.is_json else input
        
        query = data.get("query", "")
        context = data.get("context", {})
        agent_profile = data.get("agent_profile", None)
        force_consensus = data.get("force_consensus", False)
        
        if not query:
            return Response(
                json.dumps({"error": "Missing required field: query"}),
                status=400,
                mimetype="application/json"
            )
        
        try:
            pipeline = get_adversarial_pipeline()
            
            # Run analysis
            dossier = await pipeline.analyze(
                query=query,
                context=context,
                agent_profile=agent_profile,
                force_consensus=force_consensus,
            )
            
            # Build response
            return {
                "dossier_id": dossier.id,
                "status": dossier.status,
                "domain": dossier.domain.value,
                "criticality": dossier.criticality.value,
                "protocol": dossier.protocol.value,
                "phases_completed": [
                    e["phase"] for e in dossier.timeline if e.get("event", "").endswith("_completed")
                ],
                "summary": {
                    "analyses_count": len(dossier.agent_analyses),
                    "reviews_count": len(dossier.peer_reviews),
                    "audit_score": dossier.audit_report.overall_reliability_score if dossier.audit_report else None,
                    "consolidated_categories": list(dossier.consolidated_blocks.keys()),
                    "disagreements_count": len(dossier.disagreement_points),
                    "missing_info_count": len(dossier.missing_information),
                },
            }
            
        except Exception as e:
            logger.error(f"AdversarialAnalyze error: {e}")
            PrintStyle(font_color="red").print(f"❌ Error: {e}")
            return Response(
                json.dumps({
                    "error": str(e),
                    "traceback": traceback.format_exc()[:1000],
                }),
                status=500,
                mimetype="application/json"
            )


