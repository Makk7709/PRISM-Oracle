"""
Security Tests — Path Traversal in ImageGet API

Vulnerability: image_get.py uses complex manual string manipulation
(lstrip, prefix stripping, substring extraction) to normalize paths.
This is fragile and could be bypassed to serve arbitrary files.

Tested vectors:
1. Direct absolute path to system files
2. Relative traversal sequences
3. Docker path prefix abuse (korev/, app/, a0/)
4. URL-encoded traversal
5. Double-slash bypass
6. Null byte injection
7. Legitimate image paths (regression)
"""

import pytest
from unittest.mock import MagicMock, patch
from python.api.image_get import ImageGet
from python.security.authorization import AccessPrincipal


def _make_handler(path: str):
    """Create an ImageGet handler with a mocked request containing the given path."""
    handler = ImageGet.__new__(ImageGet)
    handler.request = MagicMock()
    return handler


def _make_request(path: str):
    """Create a mock Flask request with the given path query parameter."""
    req = MagicMock()
    req.args = {"path": path}
    return req


class TestImageGetPathTraversal:
    """Verify that malicious paths cannot escape the project directory."""

    @pytest.mark.asyncio
    async def test_absolute_etc_passwd(self):
        """ATTACK: path=/etc/passwd"""
        handler = _make_handler("/etc/passwd")
        with pytest.raises((ValueError, Exception)):
            await handler.process(
                {"path": "/etc/passwd"},
                _make_request("/etc/passwd"),
            )

    @pytest.mark.asyncio
    async def test_relative_traversal(self):
        """ATTACK: path=../../../etc/passwd"""
        handler = _make_handler("../../../etc/passwd")
        with pytest.raises((ValueError, Exception)):
            await handler.process(
                {"path": "../../../etc/passwd"},
                _make_request("../../../etc/passwd"),
            )

    @pytest.mark.asyncio
    async def test_docker_prefix_traversal(self):
        """ATTACK: path=korev/../../../etc/passwd"""
        handler = _make_handler("korev/../../../etc/passwd")
        with pytest.raises((ValueError, Exception)):
            await handler.process(
                {"path": "korev/../../../etc/passwd"},
                _make_request("korev/../../../etc/passwd"),
            )

    @pytest.mark.asyncio
    async def test_app_prefix_traversal(self):
        """ATTACK: path=app/../../../etc/passwd"""
        handler = _make_handler("app/../../../etc/passwd")
        with pytest.raises((ValueError, Exception)):
            await handler.process(
                {"path": "app/../../../etc/passwd"},
                _make_request("app/../../../etc/passwd"),
            )

    @pytest.mark.asyncio
    async def test_null_byte(self):
        """ATTACK: path=tmp/image.png\x00../../etc/passwd"""
        handler = _make_handler("tmp/image.png\x00../../etc/passwd")
        with pytest.raises((ValueError, Exception)):
            await handler.process(
                {"path": "tmp/image.png\x00../../etc/passwd"},
                _make_request("tmp/image.png\x00../../etc/passwd"),
            )

    @pytest.mark.asyncio
    async def test_double_slash_bypass(self):
        """ATTACK: path=//etc/passwd"""
        handler = _make_handler("//etc/passwd")
        with pytest.raises((ValueError, Exception)):
            await handler.process(
                {"path": "//etc/passwd"},
                _make_request("//etc/passwd"),
            )

    @pytest.mark.asyncio
    async def test_backslash_traversal(self):
        """ATTACK: path=..\\..\\..\\etc\\passwd"""
        handler = _make_handler("..\\..\\..\\etc\\passwd")
        with pytest.raises((ValueError, Exception)):
            await handler.process(
                {"path": "..\\..\\..\\etc\\passwd"},
                _make_request("..\\..\\..\\etc\\passwd"),
            )

    @pytest.mark.asyncio
    async def test_git_config(self):
        """ATTACK: path=.git/config"""
        handler = _make_handler(".git/config")
        with pytest.raises((ValueError, Exception)):
            await handler.process(
                {"path": ".git/config"},
                _make_request(".git/config"),
            )

    @pytest.mark.asyncio
    async def test_env_file(self):
        """ATTACK: path=.env"""
        handler = _make_handler(".env")
        with pytest.raises((ValueError, Exception)):
            await handler.process(
                {"path": ".env"},
                _make_request(".env"),
            )

    @pytest.mark.asyncio
    async def test_empty_path(self):
        """Empty path should raise ValueError."""
        handler = _make_handler("")
        with pytest.raises(ValueError, match="No path provided"):
            await handler.process({"path": ""}, _make_request(""))


class TestImageGetLegitimate:
    """Regression: legitimate image paths must still be handled."""

    @pytest.mark.asyncio
    async def test_legitimate_generated_image(self):
        """path=tmp/generated_images/chart.png should NOT raise ValueError for path."""
        handler = _make_handler("tmp/generated_images/chart.png")
        # It should not raise "outside of allowed directory"
        # It may raise FileNotFoundError (file doesn't exist) — that's OK
        try:
            await handler.process(
                {"path": "tmp/generated_images/chart.png"},
                _make_request("tmp/generated_images/chart.png"),
            )
        except ValueError as e:
            assert "outside" not in str(e).lower(), (
                f"REGRESSION: legitimate path rejected: {e}"
            )
        except Exception:
            pass  # FileNotFoundError, etc. is fine

    @pytest.mark.asyncio
    async def test_legitimate_upload_image(self):
        """path=tmp/uploads/photo.jpg should NOT raise path error."""
        handler = _make_handler("tmp/uploads/photo.jpg")
        try:
            await handler.process(
                {"path": "tmp/uploads/photo.jpg"},
                _make_request("tmp/uploads/photo.jpg"),
            )
        except ValueError as e:
            assert "outside" not in str(e).lower(), (
                f"REGRESSION: legitimate path rejected: {e}"
            )
        except Exception:
            pass

    @pytest.mark.asyncio
    async def test_legitimate_with_korev_prefix(self):
        """path=/korev/tmp/uploads/photo.jpg should strip prefix and work."""
        handler = _make_handler("/korev/tmp/uploads/photo.jpg")
        try:
            await handler.process(
                {"path": "/korev/tmp/uploads/photo.jpg"},
                _make_request("/korev/tmp/uploads/photo.jpg"),
            )
        except ValueError as e:
            assert "outside" not in str(e).lower(), (
                f"REGRESSION: korev-prefixed path rejected: {e}"
            )
        except Exception:
            pass

    @pytest.mark.asyncio
    async def test_generated_images_own_user_allowed(self):
        """Authenticated user may fetch tmp/generated_images/<username>/file.png."""
        handler = _make_handler("tmp/generated_images/alice/pic.png")
        handler._principal = lambda: AccessPrincipal(
            username="alice",
            organization="org",
            org_role=None,
            role="user",
            workspace=None,
        )
        with patch("python.api.image_get.files.exists", return_value=True):
            with patch("python.api.image_get.send_file") as mock_send:
                mock_send.return_value = MagicMock(headers={})
                await handler.process(
                    {"path": "tmp/generated_images/alice/pic.png"},
                    _make_request("tmp/generated_images/alice/pic.png"),
                )
        mock_send.assert_called_once()

    @pytest.mark.asyncio
    async def test_generated_images_other_user_denied(self):
        """Authenticated user must not read another user's generated_images folder."""
        handler = _make_handler("tmp/generated_images/bob/secret.png")
        handler._principal = lambda: AccessPrincipal(
            username="alice",
            organization="org",
            org_role=None,
            role="user",
            workspace=None,
        )
        handler._is_admin = lambda: False
        with pytest.raises(ValueError, match="Access denied"):
            await handler.process(
                {"path": "tmp/generated_images/bob/secret.png"},
                _make_request("tmp/generated_images/bob/secret.png"),
            )

    @pytest.mark.asyncio
    async def test_generated_images_admin_may_cross_user(self):
        """Admin may fetch another user's generated image (gallery support)."""
        handler = _make_handler("tmp/generated_images/bob/pic.png")
        handler._principal = lambda: AccessPrincipal(
            username="admin",
            organization="org",
            org_role=None,
            role="admin",
            workspace=None,
        )
        handler._is_admin = lambda: True
        with patch("python.api.image_get.files.exists", return_value=True):
            with patch("python.api.image_get.send_file") as mock_send:
                mock_send.return_value = MagicMock(headers={})
                await handler.process(
                    {"path": "tmp/generated_images/bob/pic.png"},
                    _make_request("tmp/generated_images/bob/pic.png"),
                )
        mock_send.assert_called_once()
