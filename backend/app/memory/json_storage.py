import json
from pathlib import Path
from typing import Any, Union

def read_json(path: Union[Path, str]) -> Any:
    """Reads and parses a JSON file. Returns None if it doesn't exist."""
    p = Path(path)
    if not p.exists():
        return None
    with open(p, 'r', encoding='utf-8') as f:
        return json.load(f)

def write_json(path: Union[Path, str], data: Any):
    """Writes data to a JSON file, creating parent directories if needed."""
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2)
