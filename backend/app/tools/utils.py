from pathlib import Path

def resolve_safe_path(workspace_root: str | Path, target_path: str | Path) -> Path:
    """Ensures that the resolved path does not escape the workspace root."""
    root = Path(workspace_root).resolve()
    resolved = (root / target_path).resolve()
    
    if not resolved.is_relative_to(root):
        raise PermissionError(f"Path traversal attempt: {target_path} escapes workspace {root}")
        
    return resolved

import subprocess
import threading
import queue
import time
from typing import Tuple

def run_with_idle_timeout(cmd: str, cwd: str, total_timeout: int = 1200, idle_timeout: int = 120) -> Tuple[int, str, str, bool]:
    """
    Runs a subprocess with an idle timeout and total timeout.
    Returns: (returncode, stdout, stderr, idle_timeout_occurred)
    """
    process = subprocess.Popen(
        cmd,
        cwd=cwd,
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1
    )
    
    q = queue.Queue()
    def reader(pipe, stream_name):
        try:
            for line in pipe:
                q.put((stream_name, line))
        except ValueError:
            pass # pipe closed
        finally:
            q.put((stream_name, None))
            
    threading.Thread(target=reader, args=(process.stdout, "STDOUT"), daemon=True).start()
    threading.Thread(target=reader, args=(process.stderr, "STDERR"), daemon=True).start()
    
    start_time = time.time()
    last_output_time = time.time()
    
    stdout_lines = []
    stderr_lines = []
    
    streams_open = 2
    timeout_occurred = False
    
    while streams_open > 0:
        try:
            stream_name, line = q.get(timeout=1.0)
            if line is None:
                streams_open -= 1
                continue
                
            last_output_time = time.time()
            if stream_name == "STDOUT":
                stdout_lines.append(line)
            else:
                stderr_lines.append(line)
                
        except queue.Empty:
            pass
            
        now = time.time()
        if now - start_time > total_timeout:
            timeout_occurred = True
            break
        if now - last_output_time > idle_timeout:
            timeout_occurred = True
            break
            
    if timeout_occurred:
        process.kill()
        process.wait()
        return -1, "".join(stdout_lines), "".join(stderr_lines), True
        
    process.wait()
    return process.returncode, "".join(stdout_lines), "".join(stderr_lines), False
