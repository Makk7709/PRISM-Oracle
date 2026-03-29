from python.helpers.api import ApiHandler, Input, Output, Request
from python.helpers.task_scheduler import TaskScheduler
from agent import AgentContext
import traceback
from python.helpers.print_style import PrintStyle
from python.helpers.localization import Localization


class SchedulerTasksList(ApiHandler):
    async def process(self, input: Input, request: Request) -> Output:
        """
        List all tasks in the scheduler with their types
        """
        try:
            # Get timezone from input (do not set if not provided, we then rely on poll() to set it)
            if timezone := input.get("timezone", None):
                Localization.get().set_timezone(timezone)

            # Get task scheduler
            scheduler = TaskScheduler.get()
            await scheduler.reload()

            # Use the scheduler's convenience method for task serialization
            tasks_list = scheduler.serialize_all_tasks()
            current_username, _ = self._session_user_info()
            if current_username:
                filtered: list[dict] = []
                needs_save = False
                for item in tasks_list:
                    owner = item.get("username")
                    if owner == current_username:
                        filtered.append(item)
                        continue
                    if owner:
                        continue
                    ctx_id = item.get("context_id")
                    ctx = AgentContext.get(ctx_id) if ctx_id else None
                    if ctx and getattr(ctx, "username", None) == current_username:
                        task = scheduler.get_task_by_uuid(item.get("uuid", ""))
                        if task:
                            await scheduler.update_task(task.uuid, username=current_username)
                            needs_save = True
                        item["username"] = current_username
                        filtered.append(item)
                if needs_save:
                    await scheduler.save()
                tasks_list = filtered

            return {"ok": True, "tasks": tasks_list}

        except Exception as e:
            PrintStyle.error(f"Failed to list tasks: {str(e)} {traceback.format_exc()}")
            return {"ok": False, "error": f"Failed to list tasks: {str(e)} {traceback.format_exc()}", "tasks": []}
