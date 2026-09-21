import subprocess
import time
import threading
import uuid
import socket
import urllib.request
from typing import Dict, Any, Optional
from pydantic import BaseModel
from enum import Enum

class ProcessHealth(str, Enum):
    STARTING = "STARTING"
    READY = "READY"
    FAILED = "FAILED"
    STOPPED = "STOPPED"

class ProcessInfo(BaseModel):
    id: str
    pid: Optional[int] = None
    command: str
    cwd: str
    port: Optional[int] = None
    status: ProcessHealth = ProcessHealth.STARTING
    started_at: float
    exit_code: Optional[int] = None
    stdout_buffer: list[str] = []
    stderr_buffer: list[str] = []

class ReadyStrategy:
    def check(self, process_info: ProcessInfo) -> bool:
        raise NotImplementedError

class SocketReadyStrategy(ReadyStrategy):
    def __init__(self, port: int, host: str = "127.0.0.1"):
        self.port = port
        self.host = host
    def check(self, process_info: ProcessInfo) -> bool:
        try:
            with socket.create_connection((self.host, self.port), timeout=1):
                return True
        except:
            return False

class HTTPReadyStrategy(ReadyStrategy):
    def __init__(self, url: str):
        self.url = url
    def check(self, process_info: ProcessInfo) -> bool:
        try:
            with urllib.request.urlopen(self.url, timeout=1) as response:
                return response.getcode() < 500
        except:
            return False

class LogReadyStrategy(ReadyStrategy):
    def __init__(self, target_string: str):
        self.target = target_string
    def check(self, process_info: ProcessInfo) -> bool:
        logs = "".join(process_info.stdout_buffer + process_info.stderr_buffer)
        return self.target in logs

class ProcessAliveStrategy(ReadyStrategy):
    def check(self, process_info: ProcessInfo) -> bool:
        return process_info.exit_code is None

class ProcessManager:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.processes = {}
            cls._instance.process_handles = {}
        return cls._instance

    def start_process(self, command: str, cwd: str, strategy: ReadyStrategy = None) -> str:
        proc_id = f"proc_{uuid.uuid4().hex[:8]}"
        
        proc = subprocess.Popen(
            command,
            cwd=cwd,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        info = ProcessInfo(
            id=proc_id,
            pid=proc.pid,
            command=command,
            cwd=cwd,
            started_at=time.time(),
            status=ProcessHealth.STARTING
        )
        self.processes[proc_id] = info
        self.process_handles[proc_id] = proc
        
        def _read_stream(stream, buffer):
            for line in iter(stream.readline, ''):
                if line:
                    buffer.append(line)
                    if len(buffer) > 1000:
                        buffer.pop(0)
            stream.close()

        threading.Thread(target=_read_stream, args=(proc.stdout, info.stdout_buffer), daemon=True).start()
        threading.Thread(target=_read_stream, args=(proc.stderr, info.stderr_buffer), daemon=True).start()
        
        # Check readiness
        if strategy is None:
            strategy = ProcessAliveStrategy()
            
        def _wait_ready():
            for _ in range(30):
                if proc.poll() is not None:
                    info.exit_code = proc.returncode
                    info.status = ProcessHealth.FAILED if proc.returncode != 0 else ProcessHealth.STOPPED
                    return
                if strategy.check(info):
                    info.status = ProcessHealth.READY
                    return
                time.sleep(0.5)
            # Timeout
            info.status = ProcessHealth.FAILED
            
        threading.Thread(target=_wait_ready, daemon=True).start()
        return proc_id

    def tail_logs(self, proc_id: str, lines: int = 20) -> str:
        if proc_id not in self.processes:
            return f"Process {proc_id} not found."
        info = self.processes[proc_id]
        out = "".join(info.stdout_buffer[-lines:])
        err = "".join(info.stderr_buffer[-lines:])
        return f"STDOUT:\n{out}\n\nSTDERR:\n{err}"

    def stop_process(self, proc_id: str):
        if proc_id in self.process_handles:
            proc = self.process_handles[proc_id]
            try:
                proc.terminate()
                proc.wait(timeout=2)
            except:
                proc.kill()
            info = self.processes[proc_id]
            info.status = ProcessHealth.STOPPED
            info.exit_code = proc.returncode

    def cleanup(self):
        for pid in list(self.process_handles.keys()):
            self.stop_process(pid)

process_manager = ProcessManager()
