import asyncio
from pathlib import Path
from app.events.schema import PrerakEvent

class FileLoggerSubscriber:
    """Appends structured events to an execution session log file asynchronously."""
    def __init__(self, log_dir: str = "logs"):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
    async def handle_event(self, event: PrerakEvent):
        def _write():
            log_file = self.log_dir / f"{event.execution_id}.log"
            with open(log_file, "a", encoding="utf-8") as f:
                f.write(event.model_dump_json() + "\n")
        
        await asyncio.to_thread(_write)
