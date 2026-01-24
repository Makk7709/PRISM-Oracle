from agent import AgentContext, UserMessage
from python.helpers.api import ApiHandler, Request, Response

from python.helpers import files, extension
import os
from werkzeug.utils import secure_filename
from python.helpers.defer import DeferredTask
from python.helpers.print_style import PrintStyle


class Message(ApiHandler):
    async def process(self, input: dict, request: Request) -> dict | Response:
        task, context = await self.communicate(input=input, request=request)
        return await self.respond(task, context)

    async def respond(self, task: DeferredTask, context: AgentContext):
        result = await task.result()  # type: ignore
        return {
            "message": result,
            "context": context.id,
        }

    async def communicate(self, input: dict, request: Request):
        # Handle both JSON and multipart/form-data
        if request.content_type.startswith("multipart/form-data"):
            text = request.form.get("text", "")
            ctxid = request.form.get("context", "")
            message_id = request.form.get("message_id", None)
            attachments = request.files.getlist("attachments")
            attachment_paths = []

            from python.helpers import runtime
            # In Docker: use /korev/tmp/uploads, in development: use local path
            upload_folder_ext = files.get_abs_path("tmp/uploads")
            if runtime.is_dockerized():
                upload_folder_int = "/korev/tmp/uploads"
            else:
                upload_folder_int = upload_folder_ext

            if attachments:
                os.makedirs(upload_folder_ext, exist_ok=True)
                for attachment in attachments:
                    if attachment.filename is None:
                        continue
                    filename = secure_filename(attachment.filename)
                    save_path = os.path.join(upload_folder_ext, filename)
                    attachment.save(save_path)
                    final_path = os.path.join(upload_folder_int, filename)
                    attachment_paths.append(final_path)
                    # Log for debugging
                    PrintStyle(font_color="cyan").print(f"[Upload] Saved: {filename}")
                    PrintStyle(font_color="cyan").print(f"  → Disk: {save_path}")
                    PrintStyle(font_color="cyan").print(f"  → Agent path: {final_path}")
                    PrintStyle(font_color="cyan").print(f"  → Exists: {os.path.exists(save_path)}")
        else:
            # Handle JSON request as before
            input_data = request.get_json()
            text = input_data.get("text", "")
            ctxid = input_data.get("context", "")
            message_id = input_data.get("message_id", None)
            attachment_paths = []

        # Now process the message
        message = text

        # Obtain agent context
        context = self.use_context(ctxid)

        # call extension point, alow it to modify data
        data = { "message": message, "attachment_paths": attachment_paths }
        await extension.call_extensions("user_message_ui", agent=context.get_agent(), data=data)
        message = data.get("message", "")
        attachment_paths = data.get("attachment_paths", [])

        # Store attachments in agent data
        # context.agent0.set_data("attachments", attachment_paths)

        # Prepare attachment filenames for logging
        attachment_filenames = (
            [os.path.basename(path) for path in attachment_paths]
            if attachment_paths
            else []
        )

        # Print to console and log
        PrintStyle(
            background_color="#6C3483", font_color="white", bold=True, padding=True
        ).print(f"User message:")
        PrintStyle(font_color="white", padding=False).print(f"> {message}")
        if attachment_filenames:
            PrintStyle(font_color="white", padding=False).print("Attachments:")
            for filename in attachment_filenames:
                PrintStyle(font_color="white", padding=False).print(f"- {filename}")

        # Log the message with message_id and attachments
        context.log.log(
            type="user",
            heading="User message",
            content=message,
            kvps={"attachments": attachment_filenames},
            id=message_id,
        )

        return context.communicate(UserMessage(message, attachment_paths)), context
