import json
import os
from pathlib import Path
from typing import List, Dict

class RecentMessagesProvider:
    """Extracts recent user execution prompts directly from log files."""
    def __init__(self, log_dir: str = "logs"):
        self.log_dir = Path(log_dir)

    def get_recent_messages(self, limit: int = 3) -> List[Dict[str, str]]:
        messages = []
        if not self.log_dir.exists():
            return messages

        # Get all log files
        log_files = list(self.log_dir.glob("*.log"))
        
        for file in log_files:
            try:
                with open(file, "r", encoding="utf-8") as f:
                    for line in f:
                        if not line.strip(): continue
                        try:
                            event = json.loads(line)
                            if event.get("event_type") == "execution_started":
                                prompt = event.get("details", {}).get("prompt")
                                if prompt:
                                    messages.append({
                                        "execution_id": event.get("execution_id", ""),
                                        "timestamp": event.get("timestamp", ""),
                                        "prompt": prompt
                                    })
                        except json.JSONDecodeError:
                            continue
            except Exception:
                continue

        # Sort chronologically
        messages.sort(key=lambda x: x["timestamp"])
        return messages[-limit:]
