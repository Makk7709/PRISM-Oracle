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

    while True:
        # In development mode, only pause if there's actually a Docker container to defer to
        # Otherwise, run the scheduler normally
        should_pause = False
        if runtime.is_development():
            try:
                # Try to signal pause to Docker container
                # If call fails (no container), we should run locally
                await runtime.call_development_function(pause_loop)
                should_pause = True
            except Exception as e:
                # No Docker container responding - run scheduler locally
                should_pause = False
                if not keep_running:
                    resume_loop()  # Resume if we were paused
        
        # Auto-resume if paused for too long
        if not keep_running and (time.time() - pause_time) > (SLEEP_TIME * 2):
            resume_loop()
        
        # Run scheduler tick if not paused
        if keep_running:
            try:
                await scheduler_tick()
            except Exception as e:
                PrintStyle().error(errors.format_error(e))
        
        await asyncio.sleep(SLEEP_TIME)  # TODO! - if we lower it under 1min, it can run a 5min job multiple times in it's target minute


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
