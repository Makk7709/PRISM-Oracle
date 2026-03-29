from python.helpers.api import ApiHandler, Input, Output, Request, Response
from agent import AgentContext
from python.helpers import persist_chat
from python.helpers.task_scheduler import TaskScheduler
from python.security.security_audit import log_security_event


class RemoveChat(ApiHandler):
    async def process(self, input: Input, request: Request) -> Output:
        ctxid = input.get("context", "")

        try:
            context = self.use_context(ctxid, create_if_not_exists=False)
        except Exception:
            context = None

        if context:
            allowed, _ = self._authorize_context_access(context, action="chat_remove")
            if not allowed:
                return {"error": "Context not found"}

        if context:
            context.reset()

        AgentContext.remove(ctxid)
        persist_chat.remove_chat(ctxid)

        scheduler = TaskScheduler.get()
        await scheduler.reload()

        tasks = scheduler.get_tasks_by_context_id(ctxid)
        for task in tasks:
            await scheduler.remove_task_by_uuid(task.uuid)
        principal = self._principal()
        log_security_event(
            action="chat_remove",
            decision="ALLOW",
            user=principal.username,
            organization=principal.organization,
            resource_type="context",
            resource_id=ctxid,
        )

        return {
            "message": "Context removed.",
        }
