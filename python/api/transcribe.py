from python.helpers.api import ApiHandler, Request, Response

from python.helpers import runtime, settings, whisper

class Transcribe(ApiHandler):
    async def process(self, input: dict, request: Request) -> dict | Response:
        audio = input.get("audio")
        ctxid = input.get("ctxid", "")

        if ctxid:
            self.use_context(ctxid)


        set = settings.get_settings()
        result = await whisper.transcribe(set["stt_model_size"], audio) # type: ignore
        return result
