from python.helpers.api import ApiHandler
from flask import Request, Response

from python.observability.runtime import ObservabilityMetrics as RuntimeObservabilityMetrics


class ObservabilityMetrics(ApiHandler):
    @classmethod
    def requires_auth(cls) -> bool:
        return True

    @classmethod
    def requires_admin(cls) -> bool:
        return True

    @classmethod
    def get_methods(cls) -> list[str]:
        return ["GET", "POST"]

    async def process(self, input: dict, request: Request) -> dict | Response:
        return {
            "ok": True,
            "metrics": RuntimeObservabilityMetrics.get().snapshot(),
        }
