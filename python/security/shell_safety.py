"""
Shell Command Safety Module - Injection Prevention

Security Requirements:
- NEVER use subprocess with shell=True
- NEVER use create_subprocess_shell
- Commands MUST be passed as list of arguments
- Shell metacharacters MUST be rejected
- Only allowlisted commands SHOULD be permitted
"""

import os
import re
from typing import List, Optional, Set, Tuple
from pathlib import Path

from python.security.path_safety import SecurityError


# Shell metacharacters that could enable injection
SHELL_METACHARACTERS = set(";|&$`\\\"'<>(){}[]!#*?~")

# Additional dangerous patterns
DANGEROUS_PATTERNS = [
    r"\$\(",          # Command substitution $(...)
    r"`.*`",          # Backtick command substitution
    r"\$\{",          # Variable expansion ${...}
    r">\s*>",         # Append redirect
    r">\s*/",         # Redirect to absolute path
    r"\|\s*\|",       # OR operator
    r"&&",            # AND operator
    r"\|\s*[a-z]",    # Pipe to command
    r";\s*[a-z]",     # Command separator
]

# Allowlist of safe commands (basename only)
# These are the ONLY commands that can be executed
COMMAND_ALLOWLIST: Set[str] = {
    # Shell utilities (read-only)
    "ls", "cat", "head", "tail", "grep", "find", "wc",
    "echo", "printf", "date", "pwd", "whoami",
    "file", "stat", "du", "df",
    # Python
    "python", "python3", "ipython", "pip", "pip3",
    # Node.js
    "node", "npm", "npx", "yarn",
    # Git
    "git",
    # Build tools
    "make", "cmake",
    # Containers (if needed)
    "docker", "docker-compose",
    # Network (read-only)
    "curl", "wget", "ping",
    # Text processing
    "sed", "awk", "sort", "uniq", "cut", "tr",
    # Compression
    "tar", "gzip", "gunzip", "zip", "unzip",
}

# Commands that are NEVER allowed
BLOCKED_COMMANDS: Set[str] = {
    "rm", "rmdir", "mv", "cp",  # Destructive - use Python APIs instead
    "chmod", "chown", "chgrp",  # Permission changes
    "sudo", "su", "doas",       # Privilege escalation
    "kill", "killall", "pkill", # Process killing
    "shutdown", "reboot", "halt", "poweroff",
    "dd", "mkfs", "fdisk", "parted",  # Disk operations
    "iptables", "ufw", "firewall-cmd",  # Firewall
    "useradd", "userdel", "passwd", "usermod",  # User management
    "eval", "exec", "source", ".",  # Code execution
    "nc", "netcat", "ncat",     # Network tools (can create backdoors)
}


class CommandValidationError(SecurityError):
    """Raised when command validation fails."""
    pass


def validate_command(command: str) -> None:
    """
    Validate a command string for shell injection attempts.
    
    Args:
        command: The command string to validate
        
    Raises:
        CommandValidationError: If command contains dangerous patterns
    """
    if not command or not command.strip():
        raise CommandValidationError("Command cannot be empty")
    
    # Check for shell metacharacters
    found_meta = set(command) & SHELL_METACHARACTERS
    if found_meta:
        raise CommandValidationError(
            f"Command contains shell metacharacters: {found_meta}"
        )
    
    # Check for dangerous patterns
    for pattern in DANGEROUS_PATTERNS:
        if re.search(pattern, command, re.IGNORECASE):
            raise CommandValidationError(
                f"Command contains dangerous pattern: {pattern}"
            )


def validate_command_in_allowlist(
    command_name: str,
    *,
    allowlist: Optional[Set[str]] = None,
    blocklist: Optional[Set[str]] = None,
) -> None:
    """
    Validate that a command is in the allowlist.
    
    Args:
        command_name: The command name (basename)
        allowlist: Set of allowed commands (default: COMMAND_ALLOWLIST)
        blocklist: Set of blocked commands (default: BLOCKED_COMMANDS)
        
    Raises:
        CommandValidationError: If command is not allowed
    """
    if allowlist is None:
        allowlist = COMMAND_ALLOWLIST
    if blocklist is None:
        blocklist = BLOCKED_COMMANDS
    
    # Get basename in case full path is provided
    basename = Path(command_name).name
    
    # Check blocklist first (takes precedence)
    if basename in blocklist:
        raise CommandValidationError(
            f"Command '{basename}' is blocked for security reasons"
        )
    
    # Check allowlist
    if basename not in allowlist:
        raise CommandValidationError(
            f"Command '{basename}' is not in the allowed list. "
            f"Allowed: {sorted(allowlist)[:10]}..."
        )


def build_safe_command(
    command: str,
    args: List[str],
    *,
    validate_args: bool = True,
) -> List[str]:
    """
    Build a safe command list for subprocess.
    
    Args:
        command: The command to run (must be in allowlist)
        args: List of arguments
        validate_args: Whether to validate arguments for injection
        
    Returns:
        List suitable for subprocess.run(..., shell=False)
        
    Raises:
        CommandValidationError: If command or args fail validation
    """
    # Validate command is in allowlist
    validate_command_in_allowlist(command)
    
    # Validate each argument if requested
    if validate_args:
        for i, arg in enumerate(args):
            # Check for obvious injection attempts in args
            if any(meta in arg for meta in [";", "|", "&", "`", "$("]):
                raise CommandValidationError(
                    f"Argument {i} contains shell metacharacters: {arg}"
                )
    
    # Return command list (never a string!)
    return [command] + list(args)


def is_command_safe(command: str, args: List[str]) -> bool:
    """
    Check if a command is safe without raising exceptions.
    
    Args:
        command: The command to check
        args: The arguments to check
        
    Returns:
        True if command passes all safety checks
    """
    try:
        build_safe_command(command, args, validate_args=True)
        return True
    except CommandValidationError:
        return False


def get_safe_shell_command() -> List[str]:
    """
    Get the command to spawn a safe shell (bash with restricted options).
    
    Returns:
        Command list for a restricted shell
    """
    # Use bash in restricted mode
    return ["/bin/bash", "--restricted", "--norc", "--noprofile"]


def sanitize_for_logging(command: List[str]) -> str:
    """
    Sanitize a command for safe logging (mask potential secrets).
    
    Args:
        command: The command list
        
    Returns:
        Safe string representation for logging
    """
    result = []
    secret_patterns = ["password", "token", "key", "secret", "auth"]
    
    for i, arg in enumerate(command):
        # Mask arguments that might be secrets
        if i > 0:  # Don't mask the command itself
            lower_prev = command[i-1].lower() if i > 0 else ""
            if any(p in lower_prev for p in secret_patterns):
                result.append("***MASKED***")
                continue
            if any(p in arg.lower() for p in secret_patterns) and "=" in arg:
                # Mask value in KEY=VALUE patterns
                key, _, _ = arg.partition("=")
                result.append(f"{key}=***MASKED***")
                continue
        result.append(arg)
    
    return " ".join(result)
