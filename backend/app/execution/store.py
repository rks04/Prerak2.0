import json
from pathlib import Path
from typing import Dict, Any, List
from datetime import datetime
from pydantic import BaseModel, Field

class ExecutionRecord(BaseModel):
    tool: str
    arguments: Dict[str, Any]
    stdout: str
    stderr: str
    classification: str = "PENDING"
    timestamp: str
    duration_ms: int
    stage: int

class ExecutionStore:
    def __init__(self, workspace_root: str, execution_id: str):
        self.workspace_root = workspace_root
        self.execution_id = execution_id
        self.records: List[ExecutionRecord] = []
        self.store_dir = Path(workspace_root) / ".memory" / "executions"
        self.store_dir.mkdir(parents=True, exist_ok=True)
        self.store_path = self.store_dir / f"{execution_id}_store.json"

    def add_record(self, record: ExecutionRecord):
        self.records.append(record)
        self.save()

    def update_last_classification(self, classification: str):
        if self.records:
            self.records[-1].classification = classification
            self.save()

    def get_recent_records(self, count: int = 5) -> List[ExecutionRecord]:
        return self.records[-count:]

    def save(self):
        with open(self.store_path, "w", encoding="utf-8") as f:
            json.dump([r.model_dump() for r in self.records], f, indent=2)
