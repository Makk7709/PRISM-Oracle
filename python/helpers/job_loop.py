import asyncio
from datetime import datetime
import time
from python.helpers.task_scheduler import TaskScheduler
from python.helpers.print_style import PrintStyle
from python.helpers import errors
from python.helpers import runtime


SLEEP_TIME = 60

keep_running = True
pause_time = 0


async def run_loop():
    global pause_time, keep_running
    
    PrintStyle(font_color="green").print("[JobLoop] Starting scheduler loop...")

    while True:
        # In development mode, only pause if RFC bridge is actually configured
        # This prevents double-running when both dev instance and Docker are running
        # But allows standalone development without Docker
        if runtime.is_development() and _has_rfc_bridge():
            try:
                # Signal to Docker container that dev instance is handling jobs
                await runtime.call_development_function(pause_loop)
            except Exception as e:
                # RFC bridge failed - resume and handle locally
                if not keep_running:
                    resume_loop()
        
        # Auto-resume if paused for too long (failsafe)
        if not keep_running and (time.time() - pause_time) > (SLEEP_TIME * 2):
            PrintStyle(font_color="yellow").print("[JobLoop] Auto-resuming after pause timeout")
            resume_loop()
        
        # Run scheduler tick if not paused
        if keep_running:
            PrintStyle(font_color="cyan").print(f"[JobLoop] Running scheduler tick at {datetime.now().strftime('%H:%M:%S')}")
            try:
                await scheduler_tick()
            except Exception as e:
                PrintStyle().error(errors.format_error(e))
        
        await asyncio.sleep(SLEEP_TIME)


def _has_rfc_bridge() -> bool:
    """Check if RFC bridge is configured (for Docker communication)"""
    try:
        from python.helpers.settings import Settings
        set = Settings.get()
        # Only consider RFC available if password is set (indicates Docker setup)
        rfc_password = set.get("rfc_password", "")
        return bool(rfc_password and len(rfc_password) > 0)
    except:
        return False


async def scheduler_tick():
    # Get the task scheduler instance
    scheduler = TaskScheduler.get()
    # Run the scheduler tick
    try:
        await scheduler.tick()
    except Exception as e:
        PrintStyle().error(f"Scheduler tick error: {errors.error_text(e)}")


def pause_loop():
    global keep_running, pause_time
    keep_running = False
    pause_time = time.time()


def resume_loop():
    global keep_running, pause_time
    keep_running = True
    pause_time = 0
