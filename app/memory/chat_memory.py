from pathlib import Path
from typing import List, Dict, Any
from app.memory.json_storage import read_json, write_json

class ChatMemory:
    """Manages chat conversations stored globally in .memory/chat/"""
    def __init__(self, base_dir: str = ".memory/chat"):
        self.base_dir = Path(base_dir)

    def get_convo_dir(self, convo_id: str) -> Path:
        return self.base_dir / f"convo_{convo_id}"

    def load_messages(self, convo_id: str) -> List[Dict[str, Any]]:
        path = self.get_convo_dir(convo_id) / "messages.json"
        return read_json(path) or []

    def save_messages(self, convo_id: str, messages: List[Dict[str, Any]]):
        path = self.get_convo_dir(convo_id) / "messages.json"
        write_json(path, messages)

    def load_meta(self, convo_id: str) -> Dict[str, Any]:
        path = self.get_convo_dir(convo_id) / "meta.json"
        return read_json(path) or {}

    def save_meta(self, convo_id: str, meta: Dict[str, Any]):
        path = self.get_convo_dir(convo_id) / "meta.json"
        write_json(path, meta)
