"""
Shell Safety Tests - Command Injection Prevention

Tests verify:
1. Shell metacharacters are detected and blocked
2. Commands are validated against allowlist
3. Arguments are passed as list, not string
4. Dangerous commands are blocked
"""

import pytest

from python.security.shell_safety import (
    validate_command,
    validate_command_in_allowlist,
    build_safe_command,
    is_command_safe,
    sanitize_for_logging,
    COMMAND_ALLOWLIST,
    BLOCKED_COMMANDS,
    CommandValidationError,
)


class TestMetacharacterDetection:
    """Tests for shell metacharacter detection."""
    
    @pytest.mark.parametrize("cmd", [
        "ls; rm -rf /",
        "echo hello | cat /etc/passwd",
        "cmd && malicious",
        "echo `whoami`",
        "echo $(id)",
        "cat < /etc/shadow",
        "data > /etc/cron.d/evil",
        "cmd || fallback",
        'echo "quoted"',
        "echo 'quoted'",
        "cmd &",
        "echo $HOME",
        "echo ${PATH}",
    ])
    def test_metacharacters_blocked(self, cmd):
        """Commands with shell metacharacters are rejected."""
        with pytest.raises(CommandValidationError, match="metacharacter|pattern"):
            validate_command(cmd)
    
    def test_simple_command_allowed(self):
        """Simple command without metacharacters is allowed."""
        # Should not raise
        validate_command("ls")
        validate_command("python --version")
        validate_command("git status")
    
    def test_empty_command_blocked(self):
        """Empty command is rejected."""
        with pytest.raises(CommandValidationError, match="empty"):
            validate_command("")
        
        with pytest.raises(CommandValidationError, match="empty"):
            validate_command("   ")


class TestCommandAllowlist:
    """Tests for command allowlist validation."""
    
    @pytest.mark.parametrize("cmd", ["ls", "cat", "python", "git", "npm"])
    def test_allowed_commands_pass(self, cmd):
        """Commands in allowlist pass validation."""
        validate_command_in_allowlist(cmd)  # Should not raise
    
    @pytest.mark.parametrize("cmd", ["rm", "sudo", "chmod", "kill", "dd"])
    def test_blocked_commands_rejected(self, cmd):
        """Blocked commands are rejected."""
        with pytest.raises(CommandValidationError, match="blocked"):
            validate_command_in_allowlist(cmd)
    
    def test_unknown_command_rejected(self):
        """Commands not in allowlist are rejected."""
        with pytest.raises(CommandValidationError, match="not in the allowed"):
            validate_command_in_allowlist("unknown_command")
    
    def test_full_path_extracts_basename(self):
        """Full path commands use basename for checking."""
        # /bin/ls should check "ls"
        validate_command_in_allowlist("/bin/ls")  # Should pass
        
        with pytest.raises(CommandValidationError):
            validate_command_in_allowlist("/bin/rm")  # Should fail


class TestBuildSafeCommand:
    """Tests for safe command building."""
    
    def test_returns_list(self):
        """build_safe_command returns a list."""
        result = build_safe_command("ls", ["-la", "/tmp"])
        assert isinstance(result, list)
        assert result == ["ls", "-la", "/tmp"]
    
    def test_validates_command(self):
        """Command is validated against allowlist."""
        with pytest.raises(CommandValidationError):
            build_safe_command("rm", ["-rf", "/"])
    
    def test_validates_args_for_metacharacters(self):
        """Arguments are checked for injection attempts."""
        with pytest.raises(CommandValidationError, match="metacharacter"):
            build_safe_command("echo", ["hello; rm -rf /"])
    
    def test_args_validation_can_be_disabled(self):
        """Argument validation can be disabled (use with caution)."""
        # This is for trusted internal use only
        result = build_safe_command("echo", ["$HOME"], validate_args=False)
        assert "$HOME" in result


class TestIsSafeCommand:
    """Tests for is_command_safe helper."""
    
    def test_safe_command_returns_true(self):
        """Safe commands return True."""
        assert is_command_safe("ls", ["-la"]) is True
        assert is_command_safe("git", ["status"]) is True
    
    def test_unsafe_command_returns_false(self):
        """Unsafe commands return False."""
        assert is_command_safe("rm", ["-rf", "/"]) is False
        assert is_command_safe("echo", ["hello; evil"]) is False


class TestSanitizeForLogging:
    """Tests for log sanitization."""
    
    def test_command_preserved(self):
        """Command name is preserved in output."""
        result = sanitize_for_logging(["ls", "-la"])
        assert "ls" in result
    
    def test_secrets_masked(self):
        """Arguments following secret keywords are masked."""
        result = sanitize_for_logging(["cmd", "--password", "secret123"])
        assert "secret123" not in result
        assert "MASKED" in result
    
    def test_key_value_secrets_masked(self):
        """KEY=VALUE secrets are masked."""
        result = sanitize_for_logging(["cmd", "API_KEY=secret123"])
        assert "secret123" not in result


class TestBlockedCommands:
    """Verify BLOCKED_COMMANDS contains dangerous commands."""
    
    def test_destructive_commands_blocked(self):
        """Destructive commands are in blocklist."""
        dangerous = ["rm", "rmdir", "mv", "dd", "mkfs"]
        for cmd in dangerous:
            assert cmd in BLOCKED_COMMANDS, f"{cmd} should be blocked"
    
    def test_privilege_escalation_blocked(self):
        """Privilege escalation commands are blocked."""
        priv_cmds = ["sudo", "su", "doas"]
        for cmd in priv_cmds:
            assert cmd in BLOCKED_COMMANDS, f"{cmd} should be blocked"
    
    def test_process_control_blocked(self):
        """Process control commands are blocked."""
        process_cmds = ["kill", "killall", "pkill"]
        for cmd in process_cmds:
            assert cmd in BLOCKED_COMMANDS, f"{cmd} should be blocked"


class TestAllowlistCompleteness:
    """Verify COMMAND_ALLOWLIST contains expected safe commands."""
    
    def test_common_dev_tools_allowed(self):
        """Common development tools are allowed."""
        dev_tools = ["python", "node", "npm", "git", "make"]
        for cmd in dev_tools:
            assert cmd in COMMAND_ALLOWLIST, f"{cmd} should be allowed"
    
    def test_read_only_tools_allowed(self):
        """Read-only system tools are allowed."""
        read_only = ["ls", "cat", "grep", "find", "head", "tail"]
        for cmd in read_only:
            assert cmd in COMMAND_ALLOWLIST, f"{cmd} should be allowed"


class TestIntegration:
    """Integration tests for shell execution (testing tty_session.py changes)."""
    
    @pytest.mark.integration
    def test_tty_session_uses_exec_not_shell(self):
        """
        Verify tty_session.py uses create_subprocess_exec, not shell.
        
        This test validates that the code change was made correctly.
        """
        import re
        from pathlib import Path
        
        # Read the source file directly to avoid import issues
        tty_session_path = Path(__file__).parent.parent.parent / "python" / "helpers" / "tty_session.py"
        
        if not tty_session_path.exists():
            pytest.skip("tty_session.py not found")
        
        source = tty_session_path.read_text()
        
        # Check that create_subprocess_shell FUNCTION CALL is NOT used
        # This regex matches actual function calls, not mentions in comments
        shell_call_pattern = r'await\s+asyncio\.create_subprocess_shell\s*\('
        shell_calls = re.findall(shell_call_pattern, source)
        assert len(shell_calls) == 0, \
            f"tty_session.py must not call create_subprocess_shell, found {len(shell_calls)} call(s)"
        
        # Check that create_subprocess_exec IS called
        exec_call_pattern = r'await\s+asyncio\.create_subprocess_exec\s*\('
        exec_calls = re.findall(exec_call_pattern, source)
        assert len(exec_calls) > 0, \
            "tty_session.py should call create_subprocess_exec"
