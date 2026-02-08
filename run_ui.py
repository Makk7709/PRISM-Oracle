"""
KOREV Evidence Web UI Server

This module provides the Flask web application for KOREV Evidence.

ARCHITECTURE NOTE (App Factory Pattern):
- `create_app()` creates a pure Flask app without heavy dependencies (LLM, MCP, etc.)
- `run()` starts the server with all runtime dependencies (initialize, MCP, A2A)
- This allows E2E tests for /login to run WITHOUT litellm installed

Import cascade prevented:
- `import initialize` → `import models` → `import litellm` (NOT at module level)
- `from python.helpers import mcp_server` → `from initialize import ...` (NOT at module level)
"""

import asyncio
from datetime import timedelta
import hmac
import os
import secrets
import hashlib
import time
import socket
import struct
from functools import wraps
import threading
from typing import Optional

from flask import Flask, request, Response, session, redirect, url_for, render_template_string
from werkzeug.wrappers.response import Response as BaseResponse
from werkzeug.middleware.proxy_fix import ProxyFix

# Light imports only - NO cascade to litellm
# NOTE: ApiHandler is imported lazily in run() to avoid agent → models → litellm cascade
from python.helpers import files, git
from python.helpers.files import get_abs_path
from python.helpers import runtime, dotenv, process
from python.helpers.extract_tools import load_classes_from_folder
from python.helpers.print_style import PrintStyle
from python.helpers import login

# Security imports - Phase 1 P0 (no litellm dependency)
from python.security.rate_limit import (
    check_login_rate_limit,
    reset_login_rate_limit,
    rate_limit_response,
    get_limiter,
)
from python.security.auth import verify_password, is_password_hashed, hash_password
from python.security.ip import get_client_ip

# disable logging
import logging
logging.getLogger().setLevel(logging.WARNING)


# Set the new timezone to 'UTC'
os.environ["TZ"] = "UTC"
os.environ["TOKENIZERS_PARALLELISM"] = "false"
# Apply the timezone change
if hasattr(time, 'tzset'):
    time.tzset()


# ═══════════════════════════════════════════════════════════════════════════════
# APP FACTORY — Pure Flask app without LLM dependencies
# ═══════════════════════════════════════════════════════════════════════════════

def create_app(
    *,
    secret_key: Optional[str] = None,
    testing: bool = False,
) -> Flask:
    """
    Create a Flask application instance without heavy dependencies.
    
    This factory creates a pure Flask app that can be imported and tested
    WITHOUT triggering imports of litellm, models, or initialize modules.
    
    Args:
        secret_key: Optional secret key for sessions. If None, uses env or generates one.
        testing: If True, disables CSRF and enables testing mode.
    
    Returns:
        Configured Flask application.
    
    Usage:
        # For testing (no LLM dependencies)
        app = create_app(testing=True)
        client = app.test_client()
        
        # For production (call run() instead)
        run()  # This will call create_app() internally
    """
    app = Flask("app", static_folder=get_abs_path("./webui"), static_url_path="/")
    app.secret_key = secret_key or os.getenv("FLASK_SECRET_KEY") or secrets.token_hex(32)
    
    # ─────────────────────────────────────────────────────────────────────────────
    # Security Configuration - Phase 1 P0 Hardening
    # ─────────────────────────────────────────────────────────────────────────────
    
    # Production mode detection
    _is_production = os.getenv("KOREV_PRODUCTION", "").lower() in ("true", "1", "yes")
    
    # Secure cookies: explicit env var takes precedence, then infer from production mode
    _secure_cookies_env = os.getenv("KOREV_SECURE_COOKIES", "").lower()
    if _secure_cookies_env in ("true", "1", "yes"):
        _is_secure = True
    elif _secure_cookies_env in ("false", "0", "no"):
        _is_secure = False
    else:
        _host_setting = os.getenv("WEB_UI_HOST", "localhost")
        _is_secure = _is_production or _host_setting not in ("localhost", "127.0.0.1", "::1")
    
    # Apply ProxyFix for proper IP detection behind reverse proxy
    _proxy_fix_enabled = os.getenv("KOREV_BEHIND_PROXY", "").lower() in ("true", "1", "yes")
    if _proxy_fix_enabled or _is_production:
        app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)  # type: ignore
    
    app.config.update(
        JSON_SORT_KEYS=False,
        SESSION_COOKIE_NAME="session_" + runtime.get_runtime_id(),
        SESSION_COOKIE_SAMESITE="Strict",
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SECURE=_is_secure,
        SESSION_PERMANENT=True,
        PERMANENT_SESSION_LIFETIME=timedelta(days=1),
        TESTING=testing,
    )
    
    if testing:
        app.config['WTF_CSRF_ENABLED'] = False
    
    # Store production flag for route handlers
    app.config['KOREV_PRODUCTION'] = _is_production
    
    # Register routes
    _register_routes(app)
    
    return app


# ═══════════════════════════════════════════════════════════════════════════════
# ROUTE HANDLERS
# ═══════════════════════════════════════════════════════════════════════════════

def _register_routes(app: Flask) -> None:
    """Register all routes on the Flask app."""
    
    @app.route("/login", methods=["GET", "POST"])
    async def login_handler():
        error = None
        client_ip = get_client_ip(request)
        
        if request.method == 'POST':
            # Rate limiting check
            allowed, retry_after = check_login_rate_limit(client_ip)
            if not allowed:
                body, status, response_headers = rate_limit_response(retry_after)
                login_page_content = files.read_file("webui/login.html")
                error = f'Too many login attempts. Please wait {retry_after} seconds.'
                response = Response(
                    render_template_string(login_page_content, error=error),
                    status=status,
                    mimetype='text/html'
                )
                for header_name, header_value in response_headers.items():
                    response.headers[header_name] = header_value
                return response
            
            expected_user = dotenv.get_dotenv_value("AUTH_LOGIN")
            stored_password = dotenv.get_dotenv_value("AUTH_PASSWORD")
            
            submitted_user = request.form.get('username', '')
            submitted_password = request.form.get('password', '')
            
            # Secure password verification
            password_valid = False
            password_needs_migration = False
            _is_production = app.config.get('KOREV_PRODUCTION', False)
            
            if stored_password:
                if is_password_hashed(stored_password):
                    password_valid = verify_password(stored_password, submitted_password)
                else:
                    if _is_production:
                        PrintStyle.error(
                            "SECURITY ERROR: Plaintext password detected in production mode. "
                            "Set AUTH_PASSWORD to an Argon2 hash or disable KOREV_PRODUCTION."
                        )
                        error = 'Server configuration error. Contact administrator.'
                        login_page_content = files.read_file("webui/login.html")
                        return render_template_string(login_page_content, error=error), 500
                    else:
                        password_valid = hmac.compare_digest(
                            submitted_password.encode('utf-8'),
                            stored_password.encode('utf-8')
                        )
                        if password_valid:
                            password_needs_migration = True
                            PrintStyle.warning(
                                "WARNING: Using plaintext password. "
                                "Run: python -c \"from python.security.auth import hash_password; "
                                f"print(hash_password('{stored_password}'))\" "
                                "and update AUTH_PASSWORD in .env"
                            )
            
            user_valid = hmac.compare_digest(
                submitted_user.encode('utf-8'),
                (expected_user or '').encode('utf-8')
            )
            
            if user_valid and password_valid:
                reset_login_rate_limit(client_ip)
                session['authentication'] = login.get_credentials_hash()
                
                if password_needs_migration:
                    PrintStyle.warning(
                        "REMINDER: Migrate to Argon2 password hash before production deployment."
                    )
                
                return redirect(url_for('serve_index'))
            else:
                error = 'Invalid Credentials. Please try again.'
                
        login_page_content = files.read_file("webui/login.html")
        return render_template_string(login_page_content, error=error)

    @app.route("/logout")
    async def logout_handler():
        session.pop('authentication', None)
        return redirect(url_for('login_handler'))

    @app.route("/", methods=["GET"])
    @_requires_auth
    async def serve_index():
        gitinfo = None
        try:
            gitinfo = git.get_git_info()
        except Exception:
            gitinfo = {
                "version": "unknown",
                "commit_time": "unknown",
            }
        index = files.read_file("webui/index.html")
        index = files.replace_placeholders_text(
            _content=index,
            version_no=gitinfo["version"],
            version_time=gitinfo["commit_time"]
        )
        return index


# ═══════════════════════════════════════════════════════════════════════════════
# DECORATORS
# ═══════════════════════════════════════════════════════════════════════════════

_app_lock = threading.Lock()


def is_loopback_address(address):
    loopback_checker = {
        socket.AF_INET: lambda x: struct.unpack("!I", socket.inet_aton(x))[0]
        >> (32 - 8)
        == 127,
        socket.AF_INET6: lambda x: x == "::1",
    }
    address_type = "hostname"
    try:
        socket.inet_pton(socket.AF_INET6, address)
        address_type = "ipv6"
    except socket.error:
        try:
            socket.inet_pton(socket.AF_INET, address)
            address_type = "ipv4"
        except socket.error:
            address_type = "hostname"

    if address_type == "ipv4":
        return loopback_checker[socket.AF_INET](address)
    elif address_type == "ipv6":
        return loopback_checker[socket.AF_INET6](address)
    else:
        for family in (socket.AF_INET, socket.AF_INET6):
            try:
                r = socket.getaddrinfo(address, None, family, socket.SOCK_STREAM)
            except socket.gaierror:
                return False
            for family, _, _, _, sockaddr in r:
                if not loopback_checker[family](sockaddr[0]):
                    return False
        return True


def requires_api_key(f):
    @wraps(f)
    async def decorated(*args, **kwargs):
        from python.helpers.settings import get_settings
        valid_api_key = get_settings()["mcp_server_token"]

        if api_key := request.headers.get("X-API-KEY"):
            if api_key != valid_api_key:
                return Response("Invalid API key", 401)
        elif request.json and request.json.get("api_key"):
            api_key = request.json.get("api_key")
            if api_key != valid_api_key:
                return Response("Invalid API key", 401)
        else:
            return Response("API key required", 401)
        return await f(*args, **kwargs)

    return decorated


def requires_loopback(f):
    @wraps(f)
    async def decorated(*args, **kwargs):
        if not is_loopback_address(request.remote_addr):
            return Response("Access denied.", 403, {})
        return await f(*args, **kwargs)

    return decorated


def _requires_auth(f):
    """Internal auth decorator for routes defined in _register_routes."""
    @wraps(f)
    async def decorated(*args, **kwargs):
        user_pass_hash = login.get_credentials_hash()
        if not user_pass_hash:
            return await f(*args, **kwargs)
        if session.get('authentication') != user_pass_hash:
            return redirect(url_for('login_handler'))
        return await f(*args, **kwargs)
    return decorated


def requires_auth(f):
    """Public auth decorator for API handlers."""
    @wraps(f)
    async def decorated(*args, **kwargs):
        user_pass_hash = login.get_credentials_hash()
        if not user_pass_hash:
            return await f(*args, **kwargs)
        if session.get('authentication') != user_pass_hash:
            return redirect(url_for('login_handler'))
        return await f(*args, **kwargs)
    return decorated


def csrf_protect(f):
    @wraps(f)
    async def decorated(*args, **kwargs):
        token = session.get("csrf_token")
        header = request.headers.get("X-CSRF-Token")
        cookie = request.cookies.get("csrf_token_" + runtime.get_runtime_id())
        sent = header or cookie
        if not token or not sent or token != sent:
            return Response("CSRF token missing or invalid", 403)
        return await f(*args, **kwargs)
    return decorated


# ═══════════════════════════════════════════════════════════════════════════════
# RUNTIME — Heavy dependencies loaded here only
# ═══════════════════════════════════════════════════════════════════════════════

# Global app instance for backward compatibility (lazy initialization)
_webapp: Optional[Flask] = None


def _get_webapp() -> Flask:
    """Get or create the global webapp instance."""
    global _webapp
    if _webapp is None:
        _webapp = create_app()
    return _webapp


# Backward compatibility: `from run_ui import webapp` still works
# This uses __getattr__ at module level for lazy loading
def __getattr__(name: str):
    if name == "webapp":
        return _get_webapp()
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def run():
    """
    Start the KOREV Evidence server with all runtime dependencies.
    
    This function:
    1. Creates the Flask app via create_app()
    2. Registers API handlers
    3. Sets up MCP and A2A middleware (imports heavy dependencies here)
    4. Starts the server
    5. Calls init_evidence() to initialize agents and MCP
    """
    PrintStyle().print("Initializing framework...")

    # Heavy imports - ONLY at runtime, not at module import
    # These cascade to litellm: mcp_server, fasta2a_server, api (via agent)
    from python.helpers import mcp_server, fasta2a_server
    from python.helpers.api import ApiHandler
    from werkzeug.serving import WSGIRequestHandler
    from werkzeug.serving import make_server
    from werkzeug.middleware.dispatcher import DispatcherMiddleware
    from a2wsgi import ASGIMiddleware

    PrintStyle().print("Starting server...")

    class NoRequestLoggingWSGIRequestHandler(WSGIRequestHandler):
        def log_request(self, code="-", size="-"):
            pass

    port = runtime.get_web_ui_port()
    host = (
        runtime.get_arg("host") or dotenv.get_dotenv_value("WEB_UI_HOST") or "localhost"
    )
    
    # Get or create the webapp
    global _webapp
    _webapp = create_app()

    def register_api_handler(app, handler):
        name = handler.__module__.split(".")[-1]
        instance = handler(app, _app_lock)

        async def handler_wrap() -> BaseResponse:
            return await instance.handle_request(request=request)

        if handler.requires_loopback():
            handler_wrap = requires_loopback(handler_wrap)
        if handler.requires_auth():
            handler_wrap = requires_auth(handler_wrap)
        if handler.requires_api_key():
            handler_wrap = requires_api_key(handler_wrap)
        if handler.requires_csrf():
            handler_wrap = csrf_protect(handler_wrap)

        app.add_url_rule(
            f"/{name}",
            f"/{name}",
            handler_wrap,
            methods=handler.get_methods(),
        )

    # Register API handlers
    handlers = load_classes_from_folder("python/api", "*.py", ApiHandler)
    for handler in handlers:
        register_api_handler(_webapp, handler)

    # Add MCP and A2A middleware
    middleware_routes = {
        "/mcp": ASGIMiddleware(app=mcp_server.DynamicMcpProxy.get_instance()),  # type: ignore
        "/a2a": ASGIMiddleware(app=fasta2a_server.DynamicA2AProxy.get_instance()),  # type: ignore
    }

    app = DispatcherMiddleware(_webapp, middleware_routes)  # type: ignore

    PrintStyle().debug(f"Starting server at http://{host}:{port} ...")

    server = make_server(
        host=host,
        port=port,
        app=app,
        request_handler=NoRequestLoggingWSGIRequestHandler,
        threaded=True,
    )
    process.set_server(server)
    server.log_startup()

    # Initialize agents and MCP
    init_evidence()

    # Run the server
    server.serve_forever()


def init_evidence():
    """
    Initialize agents, MCP, and preload models.
    
    This function imports the heavy `initialize` module which cascades to litellm.
    It is ONLY called at runtime, never at module import.
    """
    # Heavy import - ONLY at runtime
    import initialize
    
    # Initialize contexts and MCP
    init_chats = initialize.initialize_chats()
    init_chats.result_sync()

    initialize.initialize_mcp()
    initialize.initialize_job_loop()
    initialize.initialize_preload()


# ═══════════════════════════════════════════════════════════════════════════════
# ENTRY POINT
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    runtime.initialize()
    dotenv.load_dotenv()
    run()
