from flask import session
from python.helpers.api import ApiHandler, Input, Output, Request, Response
from python.helpers import projects


class Projects(ApiHandler):
    async def process(self, input: Input, request: Request) -> Output:
        action = input.get("action", "")
        ctxid = input.get("context_id", None)

        if ctxid:
            _context = self.use_context(ctxid)

        try:
            if action == "list":
                data = self.get_active_projects_list()
            elif action == "load":
                data = self.load_project(input.get("name", None))
            elif action == "create":
                data = self.create_project(input.get("project", None))
            elif action == "update":
                data = self.update_project(input.get("project", None))
            elif action == "delete":
                data = self.delete_project(input.get("name", None))
            elif action == "activate":
                data = self.activate_project(ctxid, input.get("name", None))
            elif action == "deactivate":
                data = self.deactivate_project(ctxid)
            elif action == "file_structure":
                data = self.get_file_structure(input.get("name", None), input.get("settings"))
            else:
                raise ValueError("Invalid action")

            return {
                "ok": True,
                "data": data,
            }
        except Exception as e:
            return {
                "ok": False,
                "error": str(e),
            }

    def _current_user(self) -> tuple[str | None, str | None]:
        try:
            return session.get("username"), session.get("role")
        except RuntimeError:
            return None, None

    def _check_project_access(self, name: str):
        username, role = self._current_user()
        if not username or role == "admin":
            return
        data = projects.load_basic_project_data(name)
        owner = data.get("owner", "")
        if owner and owner != username:
            raise PermissionError(f"Access denied: project '{name}' belongs to another user")

    def get_active_projects_list(self):
        username, role = self._current_user()
        return projects.get_active_projects_list(username=username, role=role)

    def create_project(self, project: dict|None):
        if project is None:
            raise ValueError("Project data is required")
        username, _ = self._current_user()
        if username:
            project["owner"] = username
        data = projects.BasicProjectData(**project)
        name = projects.create_project(project["name"], data)
        return projects.load_edit_project_data(name)

    def load_project(self, name: str|None):
        if name is None:
            raise ValueError("Project name is required")
        self._check_project_access(name)
        return projects.load_edit_project_data(name)

    def update_project(self, project: dict|None):
        if project is None:
            raise ValueError("Project data is required")
        self._check_project_access(project["name"])
        data = projects.EditProjectData(**project)
        name = projects.update_project(project["name"], data)
        return projects.load_edit_project_data(name)

    def delete_project(self, name: str|None):
        if name is None:
            raise ValueError("Project name is required")
        self._check_project_access(name)
        return projects.delete_project(name)

    def activate_project(self, context_id: str|None, name: str|None):
        if not context_id:
            raise ValueError("Context ID is required")
        if not name:
            raise ValueError("Project name is required")
        self._check_project_access(name)
        return projects.activate_project(context_id, name)

    def deactivate_project(self, context_id: str|None):
        if not context_id:
            raise ValueError("Context ID is required")
        return projects.deactivate_project(context_id)

    def get_file_structure(self, name: str|None, settings: dict|None):
        if not name:
            raise ValueError("Project name is required")
        self._check_project_access(name)
        basic_data = projects.load_basic_project_data(name)
        if settings:
            basic_data["file_structure"] = settings # type: ignore
        return projects.get_file_structure(name, basic_data)