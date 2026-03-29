from python.helpers.api import ApiHandler, Input, Output, Request
from python.helpers.task_scheduler import TaskScheduler
import traceback
from python.helpers.print_style import PrintStyle
from python.helpers.localization import Localization
from python.security.authorization import can_access_task


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
            principal = self._principal()
            tasks_list = [
                item for item in tasks_list
                if can_access_task(
                    principal,
                    task_owner=item.get("username"),
                    task_org=item.get("organization"),
                )[0]
            ]

            return {"ok": True, "tasks": tasks_list}

        except Exception as e:
            PrintStyle.error(f"Failed to list tasks: {str(e)} {traceback.format_exc()}")
            return {"ok": False, "error": f"Failed to list tasks: {str(e)} {traceback.format_exc()}", "tasks": []}
