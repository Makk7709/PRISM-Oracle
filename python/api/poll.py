from python.helpers.api import ApiHandler, Request, Response

from agent import AgentContext, AgentContextType

from python.helpers.task_scheduler import TaskScheduler
from python.helpers.localization import Localization
from python.helpers.dotenv import get_dotenv_value
from python.security.authorization import can_access_context, can_access_task


class Poll(ApiHandler):

    async def process(self, input: dict, request: Request) -> dict | Response:
        ctxid = input.get("context", "")
        from_no = input.get("log_from", 0)
        notifications_from = input.get("notifications_from", 0)

        # Get timezone from input (default to dotenv default or UTC if not provided)
        timezone = input.get("timezone", get_dotenv_value("DEFAULT_USER_TIMEZONE", "UTC"))
        Localization.get().set_timezone(timezone)

        # context instance - get or create only if ctxid is provided
        if ctxid:
            try:
                context = self.use_context(ctxid, create_if_not_exists=False)
            except Exception as e:
                context = None
        else:
            context = None

        # Get logs only if we have a context
        logs = context.log.output(start=from_no) if context else []

        # Get notifications from global notification manager
        notification_manager = AgentContext.get_notification_manager()
        notifications = notification_manager.output(start=notifications_from)

        # loop AgentContext._contexts

        # Get a task scheduler instance
        scheduler = TaskScheduler.get()

        await scheduler.reload()

        principal = self._principal()

        ctxs = []
        tasks = []

        all_ctxs = list(AgentContext._contexts.values())
        all_ctxs = [
            ctx for ctx in all_ctxs
            if can_access_context(
                principal,
                ctx_owner=getattr(ctx, "username", None),
                ctx_org=getattr(ctx, "organization", None),
            )[0]
        ]

        raw_tasks = scheduler.serialize_all_tasks()
        visible_tasks = []
        for task_data in raw_tasks:
            allowed, _ = can_access_task(
                principal,
                task_owner=task_data.get("username"),
                task_org=task_data.get("organization"),
            )
            if not allowed:
                continue
            visible_tasks.append(task_data)

        task_context_ids = {
            task_data.get("context_id")
            for task_data in visible_tasks
            if task_data.get("context_id")
        }

        for ctx in all_ctxs:
            # Skip BACKGROUND contexts as they should be invisible to users
            if ctx.type == AgentContextType.BACKGROUND:
                continue
            if ctx.id in task_context_ids:
                continue
            ctxs.append(ctx.output())

        for task_details in visible_tasks:
            context_data = {}
            task_ctx_id = task_details.get("context_id")
            task_ctx = AgentContext.get(task_ctx_id) if task_ctx_id else None
            if task_ctx and task_ctx.type != AgentContextType.BACKGROUND:
                context_data = task_ctx.output()
            else:
                # Fallback when context is not loaded in memory: keep task visible/retrievable.
                context_data = {
                    "id": task_details.get("uuid"),
                    "name": task_details.get("name"),
                    "created_at": task_details.get("created_at"),
                    "no": 0,
                    "log_guid": "",
                    "log_version": 0,
                    "log_length": 0,
                    "paused": False,
                    "last_message": task_details.get("updated_at") or task_details.get("created_at"),
                }

            # Add task details to context_data with the same field names
            # as used in scheduler endpoints to maintain UI compatibility
            context_data.update({
                "task_name": task_details.get("name"),  # name is for context, task_name for the task name
                "uuid": task_details.get("uuid"),
                "state": task_details.get("state"),
                "type": task_details.get("type"),
                "system_prompt": task_details.get("system_prompt"),
                "prompt": task_details.get("prompt"),
                "last_run": task_details.get("last_run"),
                "last_result": task_details.get("last_result"),
                "attachments": task_details.get("attachments", []),
                "context_id": task_details.get("context_id"),
            })

            # Add type-specific fields
            if task_details.get("type") == "scheduled":
                context_data["schedule"] = task_details.get("schedule")
            elif task_details.get("type") == "planned":
                context_data["plan"] = task_details.get("plan")
            else:
                context_data["token"] = task_details.get("token")

            tasks.append(context_data)

        # Sort tasks and chats by their creation date, descending
        ctxs.sort(key=lambda x: x["created_at"], reverse=True)
        tasks.sort(key=lambda x: x["created_at"], reverse=True)

        # data from this server
        return {
            "deselect_chat": ctxid and not context,
            "context": context.id if context else "",
            "contexts": ctxs,
            "tasks": tasks,
            "logs": logs,
            "log_guid": context.log.guid if context else "",
            "log_version": len(context.log.updates) if context else 0,
            "log_progress": context.log.progress if context else 0,
            "log_progress_active": context.log.progress_active if context else False,
            "paused": context.paused if context else False,
            "notifications": notifications,
            "notifications_guid": notification_manager.guid,
            "notifications_version": len(notification_manager.updates),
        }
