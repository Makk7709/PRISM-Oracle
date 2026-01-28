"""
POST /adversarial_dossier — Récupère un dossier existant
"""

import json
import logging
from python.helpers.api import ApiHandler, Request, Response

logger = logging.getLogger("api.adversarial")


class AdversarialDossier(ApiHandler):
    """
    Récupère un dossier existant.
    
    POST /adversarial_dossier
    { "dossier_id": "xxx" }
    
    Returns: Full dossier with all phases
    """
    
    async def process(self, input: dict, request: Request) -> dict | Response:
        from python.helpers.adversarial_consensus_integration import (
            get_adversarial_pipeline,
        )
        
        data = request.get_json() if request.is_json else input
        dossier_id = data.get("dossier_id") or input.get("dossier_id")
        
        if not dossier_id:
            return Response(
                json.dumps({"error": "Missing dossier_id"}),
                status=400,
                mimetype="application/json"
            )
        
        try:
            pipeline = get_adversarial_pipeline()
            dossier = pipeline.get_dossier(dossier_id)
            
            if not dossier:
                return Response(
                    json.dumps({"error": f"Dossier {dossier_id} not found"}),
                    status=404,
                    mimetype="application/json"
                )
            
            # Get presentation for decision
            presentation = pipeline.get_decision_presentation(dossier_id)
            
            # Get trace markdown
            trace_md = pipeline.get_trace_markdown(dossier_id)
            
            return {
                "dossier_id": dossier.id,
                "query": dossier.query,
                "status": dossier.status,
                "domain": dossier.domain.value,
                "criticality": dossier.criticality.value,
                "protocol": dossier.protocol.value,
                "created_at": dossier.created_at,
                "timeline": dossier.timeline,
                "analyses": {
                    agent_id: {
                        "role": analysis.agent_role.value,
                        "model": analysis.model_used,
                        "conclusions": analysis.main_conclusions,
                        "caveats": analysis.caveats,
                    }
                    for agent_id, analysis in dossier.agent_analyses.items()
                },
                "peer_reviews": [
                    {
                        "reviewer": r.reviewer_id,
                        "reviewed": r.reviewed_agent_id,
                        "weaknesses": r.weaknesses[:3],
                        "agreement": r.agreement_points[:3],
                    }
                    for r in dossier.peer_reviews
                ],
                "audit": {
                    "reliability_score": dossier.audit_report.overall_reliability_score if dossier.audit_report else None,
                    "issues_count": len(dossier.audit_report.issues_found) if dossier.audit_report else 0,
                    "recommendations": dossier.audit_report.prudence_recommendations[:5] if dossier.audit_report else [],
                },
                "consolidated": {
                    category.value if hasattr(category, 'value') else str(category): [
                        {"content": b.content, "confidence": b.category.value if hasattr(b.category, 'value') else str(b.category)}
                        for b in blocks[:5]
                    ]
                    for category, blocks in dossier.consolidated_blocks.items()
                },
                "disagreements": dossier.disagreement_points,
                "missing_info": dossier.missing_information,
                "decision_form": presentation.get("decision_form"),
                "trace_markdown": trace_md,
            }
            
        except Exception as e:
            logger.error(f"AdversarialDossier error: {e}")
            return Response(
                json.dumps({"error": str(e)}),
                status=500,
                mimetype="application/json"
            )
