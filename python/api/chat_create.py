from python.helpers.api import ApiHandler, Input, Output, Request, Response


from python.helpers import projects, guids
from agent import AgentContext


class CreateChat(ApiHandler):
    async def process(self, input: Input, request: Request) -> Output:
        current_ctxid = input.get("current_context", "") # current context id
        new_ctxid = input.get("new_context", guids.generate_id()) # given or new guid

        # context instance - get or create
        current_context = None
        if current_ctxid:
            try:
                current_context = self.use_context(current_ctxid, create_if_not_exists=False)
            except Exception:
                current_context = None
        
        # get/create new context
        new_context = self.use_context(new_ctxid)

        # copy selected data from current to new context
        if current_context:
            current_data_1 = current_context.get_data(projects.CONTEXT_DATA_KEY_PROJECT)
            if current_data_1:
                new_context.set_data(projects.CONTEXT_DATA_KEY_PROJECT, current_data_1)
            current_data_2 = current_context.get_output_data(projects.CONTEXT_DATA_KEY_PROJECT)
            if current_data_2:
                new_context.set_output_data(projects.CONTEXT_DATA_KEY_PROJECT, current_data_2)

        return {
            "ok": True,
            "ctxid": new_context.id,
            "message": "Context created.",
        }
