import subprocess
import os
from app.tools.models import ToolResult
from app.tools.utils import resolve_safe_path

ALLOWED_COMMAND_PREFIXES = [
    "python",
    "pip",
    "node",
    "npm",
    "pytest",
    "dir",
    "ls",
    "tsc",
    "echo"
]

BLOCKED_COMMAND_PREFIXES = [
    "rm",
    "shutdown",
    "format",
    "del",
    "taskkill",
    "powershell",
    "curl",
    "wget"
]

def _is_command_allowed(command: str) -> bool:
    cmd_parts = command.strip().split()
    if not cmd_parts:
        return False
    
    base_cmd = cmd_parts[0].lower()
    
    # Check blocklist first
    for blocked in BLOCKED_COMMAND_PREFIXES:
        if base_cmd == blocked or base_cmd.startswith(f"{blocked}."):
            return False
            
    # Check allowlist
    for allowed in ALLOWED_COMMAND_PREFIXES:
        if base_cmd == allowed or base_cmd.startswith(f"{allowed}."):
            return True
            
    return False

from app.tools.terminal_tools.shell_adapter import WindowsShellAdapter

def execute_terminal(workspace_root: str, command: str, timeout: int = 30) -> ToolResult:
    try:
        command = WindowsShellAdapter.normalize_command(command)
        
        validation_error = WindowsShellAdapter.validate_command(command)
        if validation_error:
            return ToolResult(success=False, error=validation_error)
            
        if not _is_command_allowed(command):
            return ToolResult(
                success=False, 
                error=f"Command rejected by security policy. Allowed prefixes: {', '.join(ALLOWED_COMMAND_PREFIXES)}"
            )
            
        root_path = resolve_safe_path(workspace_root, ".")
        
        # We use shell=True for convenience, but rely on the allowlist to prevent total disaster
        # In a real prod environment, shell=True is dangerous and should be avoided or containerized
        result = subprocess.run(
            command,
            cwd=str(root_path),
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout
        )
        
        output = result.stdout.strip()
        error = result.stderr.strip()
        
        if result.returncode == 0:
            return ToolResult(success=True, output=output or "Command completed with no output.")
        else:
            # If it failed, we want to return BOTH stdout and stderr, as stdout might have the build errors
            combined = f"STDOUT:\n{output}\n\nSTDERR:\n{error}".strip()
            return ToolResult(success=False, error=f"Command failed with exit code {result.returncode}:\n{combined}")
            
    except subprocess.TimeoutExpired:
        return ToolResult(success=False, error=f"Command timed out after {timeout} seconds.")
    except Exception as e:
        return ToolResult(success=False, error=f"Execution error: {str(e)}")
