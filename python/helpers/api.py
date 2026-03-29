from abc import abstractmethod
import json
import os
import threading
from typing import Union, TypedDict, Dict, Any
from attr import dataclass
from flask import Request, Response, jsonify, Flask, session, request, send_file, g
from agent import AgentContext
from initialize import initialize_agent
from python.helpers.print_style import PrintStyle
from python.helpers.errors import format_error
from werkzeug.serving import make_server

Input = dict
Output = Union[Dict[str, Any], Response, TypedDict]  # type: ignore


class ApiHandler:
    def __init__(self, app: Flask, thread_lock: threading.Lock):
        self.app = app
        self.thread_lock = thread_lock

    @classmethod
    def requires_loopback(cls) -> bool:
        return False

    @classmethod
    def requires_api_key(cls) -> bool:
        return False

    @classmethod
    def requires_auth(cls) -> bool:
        return True

    @classmethod
    def requires_admin(cls) -> bool:
        return False

    @classmethod
    def get_methods(cls) -> list[str]:
        return ["POST"]

    @classmethod
    def requires_csrf(cls) -> bool:
        return cls.requires_auth()

    @abstractmethod
    async def process(self, input: Input, request: Request) -> Output:
        pass

    async def handle_request(self, request: Request) -> Response:
        try:
            # input data from request based on type
            input_data: Input = {}
            if request.is_json:
                try:
                    if request.data:  # Check if there's any data
                        input_data = request.get_json()
                    # If empty or not valid JSON, use empty dict
                except Exception as e:
                    # Just log the error and continue with empty input
                    PrintStyle().print(f"Error parsing JSON: {str(e)}")
                    input_data = {}
            else:
                # input_data = {"data": request.get_data(as_text=True)}
                input_data = {}


            # process via handler
            output = await self.process(input_data, request)

            # return output based on type
            if isinstance(output, Response):
                return output
            else:
                response_json = json.dumps(output)
                return Response(
                    response=response_json, status=200, mimetype="application/json"
                )

            # return exceptions with 500
        except Exception as e:
            error = format_error(e)
            try:
                request_id = getattr(g, "request_id", "-")
            except RuntimeError:
                request_id = "-"
            PrintStyle.error(f"API error [{request_id}] {request.path}: {error}")
            if os.getenv("KOREV_PRODUCTION", "false").lower() == "true":
                return Response(
                    response='{"error":"Internal server error"}',
                    status=500,
                    mimetype="application/json",
                )
            return Response(response=error, status=500, mimetype="text/plain")

    def _session_user_info(self) -> tuple[str | None, str | None]:
        """Extract username and workspace from the current Flask session."""
        try:
            return session.get("username"), session.get("workspace")
        except RuntimeError:
            return None, None

    def _is_owner(self, ctx: AgentContext, username: str | None) -> bool:
        """True if context belongs to this user.

        Rules:
        - No auth mode (username is None): always allowed
        - Context has no owner (legacy): allow access and adopt it
        - Owner matches: allowed
        - Owner mismatch: denied
        """
        if username is None:
            return True
        ctx_owner = getattr(ctx, "username", None)
        if ctx_owner is None:
            return True
        return ctx_owner == username

    def use_context(self, ctxid: str, create_if_not_exists: bool = True):
        username, workspace = self._session_user_info()
        with self.thread_lock:
            if not ctxid:
                owned = [
                    c for c in AgentContext.all()
                    if self._is_owner(c, username)
                ]
                first = owned[0] if owned else None
                if first:
                    if username and not first.username:
                        first.username = username
                        first.workspace = workspace
                    AgentContext.use(first.id)
                    return first
                context = AgentContext(
                    config=initialize_agent(), set_current=True,
                    username=username, workspace=workspace,
                )
                return context
            got = AgentContext.use(ctxid)
            if got:
                if not self._is_owner(got, username):
                    raise Exception(f"Access denied: context {ctxid} belongs to another user")
                if username and not got.username:
                    got.username = username
                    got.workspace = workspace
                return got
            if create_if_not_exists:
                context = AgentContext(
                    config=initialize_agent(), id=ctxid, set_current=True,
                    username=username, workspace=workspace,
                )
                return context
            else:
                raise Exception(f"Context {ctxid} not found")
            
