"""
POST /adversarial_decide — Enregistre une décision humaine
"""

import json
import logging
from python.helpers.api import ApiHandler, Request, Response

logger = logging.getLogger("api.adversarial")


class AdversarialDecide(ApiHandler):
    """
    Enregistre une décision humaine sur un dossier.
    
    POST /adversarial_decide
    {
        "dossier_id": "xxx",
        "decision": "accept_with_reserves",
        "acknowledged_risks": ["risk1", "risk2"],
        "notes": "Optional notes..."
    }
    
    Returns: { "success": true, "dossier_id": "xxx", "decision": "..." }
    """
    
    async def process(self, input: dict, request: Request) -> dict | Response:
        from python.helpers.adversarial_consensus_integration import (
            get_adversarial_pipeline,
        )
        
        data = request.get_json() if request.is_json else input
        
        dossier_id = data.get("dossier_id") or input.get("dossier_id")
        decision = data.get("decision")
        acknowledged_risks = data.get("acknowledged_risks", [])
        notes = data.get("notes", "")
        
        if not dossier_id or not decision:
            return Response(
                json.dumps({"error": "Missing required fields: dossier_id, decision"}),
                status=400,
                mimetype="application/json"
            )
        
        valid_decisions = ["accept", "accept_with_reserves", "reject", "request_more_info"]
        if decision not in valid_decisions:
            return Response(
                json.dumps({
                    "error": f"Invalid decision. Must be one of: {valid_decisions}"
                }),
                status=400,
                mimetype="application/json"
            )
        
        try:
            pipeline = get_adversarial_pipeline()
            
            success = pipeline.record_decision(
                dossier_id=dossier_id,
                decision=decision,
                acknowledged_risks=acknowledged_risks,
                notes=notes,
            )
            
            if success:
                return {
                    "success": True,
                    "dossier_id": dossier_id,
                    "decision": decision,
                }
            else:
                return Response(
                    json.dumps({"error": "Failed to record decision"}),
                    status=500,
                    mimetype="application/json"
                )
                
        except ValueError as e:
            return Response(
                json.dumps({"error": str(e)}),
                status=404,
                mimetype="application/json"
            )
        except Exception as e:
            logger.error(f"AdversarialDecide error: {e}")
            return Response(
                json.dumps({"error": str(e)}),
                status=500,
                mimetype="application/json"
            )
