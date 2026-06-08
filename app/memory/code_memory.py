from pathlib import Path
from typing import List, Dict, Any
from app.memory.json_storage import read_json, write_json

class CodeMemory:
    """Manages code agent memories scoped inside a specific workspace (.prerak/)"""
    def __init__(self, workspace_path: str):
        self.base_dir = Path(workspace_path) / ".prerak"

    def get_convo_dir(self, convo_id: str) -> Path:
        return self.base_dir / f"convo_{convo_id}"

    def load_messages(self, convo_id: str) -> List[Dict[str, Any]]:
        path = self.get_convo_dir(convo_id) / "messages.json"
        return read_json(path) or []

    def save_messages(self, convo_id: str, messages: List[Dict[str, Any]]):
        path = self.get_convo_dir(convo_id) / "messages.json"
        write_json(path, messages)

    def load_workspace_state(self, convo_id: str) -> Dict[str, Any]:
        path = self.get_convo_dir(convo_id) / "workspace-state.json"
        return read_json(path) or {}

    def save_workspace_state(self, convo_id: str, state: Dict[str, Any]):
        path = self.get_convo_dir(convo_id) / "workspace-state.json"
        write_json(path, state)
