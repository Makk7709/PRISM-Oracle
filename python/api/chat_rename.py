from python.helpers.api import ApiHandler, Input, Output, Request, Response
from agent import AgentContext
from python.helpers import persist_chat
from python.security.security_audit import log_security_event
try:
    from python.observability.runtime import log_observability_event
except Exception:
    def log_observability_event(**kwargs):
        return None

MAX_TITLE_LENGTH = 120
MIN_TITLE_LENGTH = 1


class ChatRename(ApiHandler):
    async def process(self, input: Input, request: Request) -> Output:
        ctxid = input.get("context", "").strip()
        new_title = input.get("title", "")

        if not ctxid:
            return Response('{"error":"Missing context ID"}', status=400, mimetype="application/json")

        # ── Validate title ──
        if isinstance(new_title, str):
            new_title = new_title.strip()
        else:
            new_title = ""

        if len(new_title) < MIN_TITLE_LENGTH:
            log_observability_event(
                event_type="chat_rename_validation_failed",
                status="DENY",
                username=self._principal().username,
                organization=self._principal().organization,
                reason="title_empty",
                metadata={"context_id": ctxid},
            )
            return Response('{"error":"Title cannot be empty"}', status=400, mimetype="application/json")

        if len(new_title) > MAX_TITLE_LENGTH:
            new_title = new_title[:MAX_TITLE_LENGTH]

        # ── Load context and authorize ──
        try:
            context = self.use_context(ctxid, create_if_not_exists=False)
        except Exception:
            return Response('{"error":"Chat not found"}', status=404, mimetype="application/json")

        allowed, reason = self._authorize_context_access(context, action="chat_rename")
        if not allowed:
            principal = self._principal()
            log_observability_event(
                event_type="chat_rename_denied_scope",
                status="DENY",
                username=principal.username,
                organization=principal.organization,
                reason=reason,
                metadata={"context_id": ctxid},
            )
            return Response('{"error":"Chat not found"}', status=404, mimetype="application/json")

        # ── Apply rename ──
        old_title = context.name
        context.name = new_title
        persist_chat.save_tmp_chat(context)

        principal = self._principal()
        log_security_event(
            action="chat_rename",
            decision="ALLOW",
            user=principal.username,
            organization=principal.organization,
            resource_type="context",
            resource_id=ctxid,
        )
        log_observability_event(
            event_type="chat_rename_success",
            status="ALLOW",
            username=principal.username,
            organization=principal.organization,
            metadata={
                "context_id": ctxid,
                "old_title": old_title,
                "new_title": new_title,
            },
        )

        return {
            "ok": True,
            "context": ctxid,
            "title": new_title,
        }
