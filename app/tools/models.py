from pydantic import BaseModel
from typing import Optional, Dict, Any

class ToolResult(BaseModel):
    success: bool
    output: Optional[str] = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = {}
