import json
import os
from pathlib import Path
from typing import List, Dict

class RecentMessagesProvider:
    """Extracts recent user execution prompts directly from scoped conversation memory."""
    def __init__(self, memory_dir: str = ".memory"):
        self.memory_dir = Path(memory_dir)

    def get_recent_messages(self, workspace_root: str, convo_id: str, limit: int = 3) -> List[Dict[str, str]]:
        messages = []
        import hashlib
        path_hash = hashlib.md5(workspace_root.encode('utf-8')).hexdigest()[:8]
        workspace_name = f"{Path(workspace_root).name}_{path_hash}"
        log_file = self.memory_dir / "code" / workspace_name / convo_id / "messages.json"
        
        if not log_file.exists():
            return messages

        try:
            with open(log_file, "r", encoding="utf-8") as f:
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
            pass

        # Sort chronologically
        messages.sort(key=lambda x: x["timestamp"])
        return messages[-limit:]
