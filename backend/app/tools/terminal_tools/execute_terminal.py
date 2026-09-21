import os
from app.tools.models import ToolResult
from app.tools.utils import resolve_safe_path, run_with_idle_timeout
from typing import Literal

ALLOWED_COMMAND_PREFIXES = [
    "python",
    "pip",
    "node",
    "npm",
    "pytest",
    "dir",
    "ls",
    "tsc",
    "echo",
    "curl"
]

BLOCKED_COMMAND_PREFIXES = [
    "rm",
    "shutdown",
    "format",
    "del",
    "taskkill",
    "powershell",
    "wget"
]

def _is_command_allowed(command: str) -> bool:
    import shlex
    import os
    try:
        cmd_parts = shlex.split(command.strip(), posix=False)
    except ValueError:
        cmd_parts = command.strip().split()
        
    if not cmd_parts:
        return False
    
    base_cmd = cmd_parts[0].strip('"\'')
    executable_name = os.path.basename(base_cmd).lower()
    
    # Check blocklist first
    for blocked in BLOCKED_COMMAND_PREFIXES:
        if executable_name == blocked or executable_name.startswith(f"{blocked}."):
            return False
            
    # Check allowlist
    for allowed in ALLOWED_COMMAND_PREFIXES:
        if executable_name == allowed or executable_name.startswith(f"{allowed}."):
            return True
            
    return False

from app.tools.terminal_tools.shell_adapter import WindowsShellAdapter
import time
from app.execution.process_manager import process_manager, SocketReadyStrategy, HTTPReadyStrategy

def cleanup_background_processes():
    process_manager.cleanup()

def execute_terminal(workspace_root: str, command: str, mode: Literal["blocking", "background"] = "blocking", timeout: int = 120) -> ToolResult:
    try:
        command = WindowsShellAdapter.normalize_command(command)
        
        validation_error = WindowsShellAdapter.validate_command(command)
        if validation_error:
            return ToolResult(success=False, error=validation_error)
            
        if mode not in ["blocking", "background"]:
            return ToolResult(success=False, error=f"Invalid mode '{mode}'. Allowed values: blocking, background.")
            
        if not _is_command_allowed(command):
            return ToolResult(
                success=False, 
                error=f"Command rejected by security policy. Allowed prefixes: {', '.join(ALLOWED_COMMAND_PREFIXES)}"
            )
            
        root_path = resolve_safe_path(workspace_root, ".")
        
        # We use shell=True for convenience, but rely on the allowlist to prevent total disaster
        # In a real prod environment, shell=True is dangerous and should be avoided or containerized
        
        if mode == "background":
            # For now, default to SocketReadyStrategy if we detect it's a Flask app (port 5000)
            # In a real implementation, the Coder could pass a readiness strategy parameter.
            strategy = None
            if "flask" in command.lower() or "app.py" in command.lower():
                strategy = SocketReadyStrategy(port=5000)
            elif "fastapi" in command.lower():
                strategy = HTTPReadyStrategy(url="http://localhost:8000")
                
            proc_id = process_manager.start_process(command, str(root_path), strategy)
            
            # Wait a short moment for initial readiness
            time.sleep(2)
            info = process_manager.processes.get(proc_id)
            if info and info.status == "FAILED":
                logs = process_manager.tail_logs(proc_id)
                return ToolResult(success=False, error=f"Background process immediately failed with exit code {info.exit_code}:\n{logs}")
                
            status_msg = "READY" if info.status == "READY" else "STARTING"
            return ToolResult(success=True, output=f"Process started successfully in background with process_id '{proc_id}'. Current Status: {status_msg}")
            
        # Phase 25: Progress-aware timeout
        # Limit max timeout to 1200
        timeout = min(timeout, 1200)
        
        returncode, stdout, stderr, timeout_occurred = run_with_idle_timeout(
            command,
            str(root_path),
            total_timeout=timeout,
            idle_timeout=120
        )
        
        output = stdout.strip()
        error = stderr.strip()
        
        if timeout_occurred:
            return ToolResult(success=False, error=f"Command timed out after {timeout} seconds (or went idle).\nSTDOUT:\n{output}\nSTDERR:\n{error}")
            
        if returncode == 0:
            return ToolResult(success=True, output=output or "Command completed with no output.")
        else:
            # If it failed, we want to return BOTH stdout and stderr, as stdout might have the build errors
            combined = f"STDOUT:\n{output}\n\nSTDERR:\n{error}".strip()
            return ToolResult(success=False, error=f"Command failed with exit code {returncode}:\n{combined}")
            
    except Exception as e:
        return ToolResult(success=False, error=f"Execution error: {str(e)}")
