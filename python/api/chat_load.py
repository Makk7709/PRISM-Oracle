from python.helpers.api import ApiHandler, Input, Output, Request, Response
from agent import AgentContext
from python.helpers import persist_chat

class LoadChats(ApiHandler):
    async def process(self, input: Input, request: Request) -> Output:
        chats = input.get("chats", [])
        if not chats:
            raise Exception("No chats provided")

        ctxids = persist_chat.load_json_chats(chats)
        username, workspace = self._session_user_info()
        organization, _ = self._session_org_info()
        for ctxid in ctxids:
            ctx = AgentContext.get(ctxid)
            if not ctx:
                continue
            # Imported data is always re-owned by the importing account.
            ctx.username = username
            ctx.workspace = workspace
            ctx.organization = organization
            persist_chat.save_tmp_chat(ctx)

        return {
            "message": "Chats loaded.",
            "ctxids": ctxids,
        }
