from pathlib import Path
from typing import Dict, Any
from app.memory.json_storage import read_json, write_json

class SummaryManager:
    """Handles summary compression files in memory directories."""
    def load_summary(self, dir_path: Path) -> Dict[str, Any]:
        path = dir_path / "summary.json"
        return read_json(path) or {}

    def save_summary(self, dir_path: Path, summary: Dict[str, Any]):
        path = dir_path / "summary.json"
        write_json(path, summary)
