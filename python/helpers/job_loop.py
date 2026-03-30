import asyncio
from datetime import datetime
import time
import os
import fcntl
from python.helpers.task_scheduler import TaskScheduler
from python.helpers.print_style import PrintStyle
from python.helpers import errors
from python.helpers import runtime


SLEEP_TIME = 15

keep_running = True
pause_time = 0
_scheduler_lock_fd = None


def _acquire_scheduler_process_lock() -> bool:
    """
    Ensure only one process executes scheduler ticks for JSON-backed storage.
    Returns False when another process already owns the scheduler lock.
    """
    global _scheduler_lock_fd
    if _scheduler_lock_fd is not None:
        return True
    lock_file = os.getenv("EVIDENCE_SCHEDULER_LOCK_FILE", "/tmp/evidence_scheduler.lock")
    try:
        fd = open(lock_file, "a+", encoding="utf-8")
        fcntl.flock(fd.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        _scheduler_lock_fd = fd
        return True
    except BlockingIOError:
        return False
    except Exception as e:
        PrintStyle().error(f"[JobLoop] Failed to acquire scheduler lock: {errors.error_text(e)}")
        return False


async def run_loop():
    global pause_time, keep_running
    has_scheduler_lock = _acquire_scheduler_process_lock()
    
    PrintStyle(font_color="green").print("[JobLoop] Starting scheduler loop...")
    if not has_scheduler_lock:
        PrintStyle(font_color="yellow").print(
            "[JobLoop] Scheduler lock is already held by another process; this process will not execute ticks"
        )

    while True:
        try:
            # In development mode, only pause if RFC bridge is actually configured
            # This prevents double-running when both dev instance and Docker are running
            # But allows standalone development without Docker
            if runtime.is_development() and _has_rfc_bridge():
                try:
                    # Signal to Docker container that dev instance is handling jobs
                    await runtime.call_development_function(pause_loop)
                except Exception:
                    # RFC bridge failed - resume and handle locally
                    if not keep_running:
                        resume_loop()
            
            # Auto-resume if paused for too long (failsafe)
            if not keep_running and (time.time() - pause_time) > (SLEEP_TIME * 2):
                PrintStyle(font_color="yellow").print("[JobLoop] Auto-resuming after pause timeout")
                resume_loop()
            
            # Run scheduler tick if not paused
            if keep_running and has_scheduler_lock:
                PrintStyle(font_color="cyan").print(f"[JobLoop] Running scheduler tick at {datetime.now().strftime('%H:%M:%S')}")
                try:
                    await scheduler_tick()
                except Exception as e:
                    PrintStyle().error(f"[JobLoop] Scheduler tick error: {errors.error_text(e)}")
        
        except Exception as e:
            # Catch any unexpected errors to prevent loop from crashing
            PrintStyle().error(f"[JobLoop] Unexpected error: {errors.error_text(e)}")
        
        await asyncio.sleep(SLEEP_TIME)


def _has_rfc_bridge() -> bool:
    """Check if RFC bridge is configured (for Docker communication)"""
    try:
        import os
        # Only consider RFC available if password is set in environment
        rfc_password = os.environ.get("RFC_PASSWORD", "")
        return bool(rfc_password and len(rfc_password) > 0)
    except Exception:
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
