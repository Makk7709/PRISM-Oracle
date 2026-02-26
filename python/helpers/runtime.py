"""
KOREV Evidence Runtime Module

ARCHITECTURE NOTE (Lazy Imports):
- `settings` is imported lazily (inside functions) to avoid importing litellm at module level
- This allows `import runtime` without triggering the litellm import cascade
- Functions that need settings import it locally when called
"""
import argparse
import inspect
import os
import secrets
from pathlib import Path
from typing import TypeVar, Callable, Awaitable, Union, overload, cast, TYPE_CHECKING
from python.helpers import dotenv, rfc, files
from python.helpers.print_style import PrintStyle
import asyncio
import threading
import queue
import sys

if TYPE_CHECKING:
    from python.helpers import settings as settings_module

T = TypeVar("T")
R = TypeVar("R")

parser = argparse.ArgumentParser()
args = {}
dockerman = None
runtime_id = None

# ─────────────────────────────────────────────────────────────────────────────
# PRISM Runtime Mode: "user" (default) or "dev"
# In "user" mode: no RFC bridge dependency, direct execution only
# In "dev" mode: RFC bridge optional, fallback to direct if unavailable
# ─────────────────────────────────────────────────────────────────────────────
RUNTIME_MODE_USER = "user"
RUNTIME_MODE_DEV = "dev"


def get_runtime_mode() -> str:
    """Return the current runtime mode: 'user' (default) or 'dev'."""
    return os.environ.get("PRISM_RUNTIME_MODE", RUNTIME_MODE_USER).lower()


def is_user_mode() -> bool:
    """True if running in user-safe mode (no RFC bridge dependency)."""
    return get_runtime_mode() == RUNTIME_MODE_USER


def initialize():
    global args
    if args:
        return
    parser.add_argument("--port", type=int, default=None, help="Web UI port")
    parser.add_argument("--host", type=str, default=None, help="Web UI host")
    parser.add_argument(
        "--cloudflare_tunnel",
        type=bool,
        default=False,
        help="Use cloudflare tunnel for public URL",
    )
    parser.add_argument(
        "--development", type=bool, default=False, help="Development mode"
    )

    known, unknown = parser.parse_known_args()
    args = vars(known)
    for arg in unknown:
        if "=" in arg:
            key, value = arg.split("=", 1)
            key = key.lstrip("-")
            args[key] = value


def get_arg(name: str):
    global args
    return args.get(name, None)


def has_arg(name: str):
    global args
    return name in args


def is_dockerized() -> bool:
    if get_arg("dockerized"):
        return True
    if os.environ.get("EVIDENCE_ENV") == "production":
        return True
    if os.path.exists("/.dockerenv"):
        return True
    return False


def is_development() -> bool:
    return not is_dockerized()


def get_local_url():
    if is_dockerized():
        return "host.docker.internal"
    return "127.0.0.1"


def get_runtime_id() -> str:
    global runtime_id
    if not runtime_id:
        runtime_id = secrets.token_hex(8)
    return runtime_id


def get_persistent_id() -> str:
    # 1. Check env var (loaded from .env or set in memory)
    id = dotenv.get_dotenv_value("KOREV_PERSISTENT_RUNTIME_ID")

    # 2. Check persistent file (Docker: .env is read-only, so we persist here)
    persistent_file = os.path.join(
        os.environ.get("EVIDENCE_HOME", "."), "tmp", ".persistent_runtime_id"
    )
    if not id:
        try:
            if os.path.isfile(persistent_file):
                id = open(persistent_file).read().strip()
        except OSError:
            pass

    # 3. Generate new ID if none found
    if not id:
        id = secrets.token_hex(16)

    # 4. Save to .env (graceful if read-only) and to persistent file
    dotenv.save_dotenv_value("KOREV_PERSISTENT_RUNTIME_ID", id)
    try:
        os.makedirs(os.path.dirname(persistent_file), exist_ok=True)
        with open(persistent_file, "w") as f:
            f.write(id)
    except OSError:
        pass

    return id


@overload
async def call_development_function(
    func: Callable[..., Awaitable[T]], *args, **kwargs
) -> T: ...


@overload
async def call_development_function(func: Callable[..., T], *args, **kwargs) -> T: ...


async def call_development_function(
    func: Union[Callable[..., T], Callable[..., Awaitable[T]]], *args, **kwargs
) -> T:
    """
    Execute a function either via RFC bridge (dev mode with bridge) or directly.
    
    MODE=user (default): Always execute directly, never attempt RFC bridge.
    MODE=dev: Try RFC bridge if configured, fallback to direct execution.
    
    NEVER raises an exception for missing RFC password — always falls back gracefully.
    """
    # USER MODE: Always execute directly, no RFC bridge dependency
    if is_user_mode():
        if inspect.iscoroutinefunction(func):
            return await func(*args, **kwargs)
        return func(*args, **kwargs)  # type: ignore

    # DEV MODE: Try RFC bridge if available, fallback to direct
    if is_development():
        try:
            url = _get_rfc_url()
            password = _get_rfc_password()
        except Exception:
            # No RFC password configured — fall back to local execution in dev.
            if inspect.iscoroutinefunction(func):
                return await func(*args, **kwargs)
            return func(*args, **kwargs)  # type: ignore

        try:
            # Normalize path components to build a valid Python module path across OSes
            module_path = Path(
                files.deabsolute_path(func.__code__.co_filename)
            ).with_suffix("")
            module = ".".join(module_path.parts)  # __module__ is not reliable
            result = await rfc.call_rfc(
                url=url,
                password=password,
                module=module,
                function_name=func.__name__,
                args=list(args),
                kwargs=kwargs,
            )
            return cast(T, result)
        except Exception as e:
            # RFC call failed — fall back to direct execution
            PrintStyle.hint(f"RFC bridge unavailable ({e}), falling back to direct execution.")
            if inspect.iscoroutinefunction(func):
                return await func(*args, **kwargs)
            return func(*args, **kwargs)  # type: ignore
    else:
        # Dockerized mode: execute directly
        if inspect.iscoroutinefunction(func):
            return await func(*args, **kwargs)
        else:
            return func(*args, **kwargs)  # type: ignore


async def handle_rfc(rfc_call: rfc.RFCCall):
    return await rfc.handle_rfc(rfc_call=rfc_call, password=_get_rfc_password())


def _get_rfc_password() -> str:
    """Get RFC password from env. Raises Exception if not set (handled by caller)."""
    password = dotenv.get_dotenv_value(dotenv.KEY_RFC_PASSWORD)
    if not password:
        raise Exception("RFC password not configured.")
    return password


def has_rfc_password() -> bool:
    """Check if RFC password is configured (without raising)."""
    password = dotenv.get_dotenv_value(dotenv.KEY_RFC_PASSWORD)
    return bool(password)


def _get_rfc_url() -> str:
    # Lazy import to avoid litellm cascade at module level
    from python.helpers import settings
    s = settings.get_settings()
    url = s["rfc_url"]
    if not "://" in url:
        url = "http://" + url
    if url.endswith("/"):
        url = url[:-1]
    url = url + ":" + str(s["rfc_port_http"])
    url += "/rfc"
    return url


def call_development_function_sync(
    func: Union[Callable[..., T], Callable[..., Awaitable[T]]], *args, **kwargs
) -> T:
    # run async function in sync manner
    result_queue = queue.Queue()

    def run_in_thread():
        result = asyncio.run(call_development_function(func, *args, **kwargs))
        result_queue.put(result)

    thread = threading.Thread(target=run_in_thread)
    thread.start()
    thread.join(timeout=30)  # wait for thread with timeout

    if thread.is_alive():
        raise TimeoutError("Function call timed out after 30 seconds")

    result = result_queue.get_nowait()
    return cast(T, result)


def get_web_ui_port():
    web_ui_port = (
        get_arg("port") or int(dotenv.get_dotenv_value("WEB_UI_PORT", 0)) or 5000
    )
    return web_ui_port


def get_tunnel_api_port():
    tunnel_api_port = (
        get_arg("tunnel_api_port")
        or int(dotenv.get_dotenv_value("TUNNEL_API_PORT", 0))
        or 55520
    )
    return tunnel_api_port


def get_platform():
    return sys.platform


def is_windows():
    return get_platform() == "win32"


def get_terminal_executable():
    if is_windows():
        return "powershell.exe"
    else:
        return "/bin/bash"
