from python.helpers.api import ApiHandler, Request, Response

from python.helpers import runtime
import os

class RFC(ApiHandler):

    @classmethod
    def requires_csrf(cls) -> bool:
        return False

    @classmethod
    def requires_auth(cls) -> bool:
        return True

    @classmethod
    def requires_api_key(cls) -> bool:
        # Keep strict protection in non-production too.
        return True

    async def process(self, input: dict, request: Request) -> dict | Response:
        if os.getenv("KOREV_PRODUCTION", "false").lower() == "true":
            return Response(response='{"status":"not_found"}', status=404, mimetype="application/json")
        result = await runtime.handle_rfc(input) # type: ignore
        return result
