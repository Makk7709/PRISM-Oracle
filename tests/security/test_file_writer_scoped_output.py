from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock
import sys
import types

import pytest

sys.modules.setdefault("whisper", types.ModuleType("whisper"))

from python.tools.file_writer import FileWriter


def _make_writer(*, workspace: str | None, username: str | None, args: dict) -> FileWriter:
    writer = FileWriter.__new__(FileWriter)
    writer.agent = MagicMock()
    writer.agent.context = SimpleNamespace(workspace=workspace, username=username)
    writer.args = args
    writer.message = ""
    writer.name = "file_writer"
    return writer


@pytest.mark.asyncio
async def test_file_writer_falls_back_to_user_workspace_when_workspace_missing(monkeypatch, tmp_path: Path):
    user_root = tmp_path / "shared" / "users" / "amine"

    def _fake_get_abs_path(*parts):
        if parts == ("shared/users", "amine"):
            return str(user_root)
        return str(tmp_path.joinpath(*parts))

    monkeypatch.setattr("python.tools.file_writer.files.get_abs_path", _fake_get_abs_path)

    writer = _make_writer(
        workspace=None,
        username="amine",
        args={
            "filename": "strategic_report",
            "content": "hello world",
            "format": "txt",
        },
    )

    response = await writer.execute()
    assert "File created successfully" in response.message
    assert "/download_work_dir_file?path=/generated/" in response.message
    assert "/tmp/generated/" not in response.message

    generated_dir = user_root / "generated"
    created = list(generated_dir.glob("strategic_report_*.txt"))
    assert len(created) == 1

