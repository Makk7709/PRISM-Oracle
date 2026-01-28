"""
POST /adversarial_list — Liste tous les dossiers actifs
"""

import json
import logging
from python.helpers.api import ApiHandler, Request, Response

logger = logging.getLogger("api.adversarial")


class AdversarialList(ApiHandler):
    """
    Liste tous les dossiers actifs.
    
    POST /adversarial_list
    {}
    
    Returns: List of dossier summaries
    """
    
    async def process(self, input: dict, request: Request) -> dict | Response:
        from python.helpers.adversarial_consensus_integration import (
            get_adversarial_pipeline,
        )
        
        try:
            pipeline = get_adversarial_pipeline()
            
            dossiers = []
            for dossier_id, dossier in pipeline._dossiers.items():
                dossiers.append({
                    "id": dossier.id,
                    "query": dossier.query[:100] + "..." if len(dossier.query) > 100 else dossier.query,
                    "status": dossier.status,
                    "domain": dossier.domain.value,
                    "criticality": dossier.criticality.value,
                    "created_at": dossier.created_at,
                })
            
            # Sort by creation time (most recent first)
            dossiers.sort(key=lambda d: d["created_at"], reverse=True)
            
            return {
                "dossiers": dossiers,
                "count": len(dossiers),
            }
            
        except Exception as e:
            logger.error(f"AdversarialList error: {e}")
            return Response(
                json.dumps({"error": str(e)}),
                status=500,
                mimetype="application/json"
            )
