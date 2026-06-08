from typing import Callable, Dict
from app.security.tool_permissions import ALLOWED_TOOLS

class ToolRegistry:
    def __init__(self):
        self._tools: Dict[str, Callable] = {}

    def register(self, name: str, func: Callable):
        if name in ALLOWED_TOOLS:
            self._tools[name] = func

    def get_tool(self, name: str) -> Callable:
        return self._tools.get(name)

tool_registry = ToolRegistry()

# Register core file tools
from app.tools.file_tools.write_file import write_file
from app.tools.file_tools.read_file import read_file
from app.tools.file_tools.edit_file import edit_file
from app.tools.workspace_tools.list_files import list_files

tool_registry.register("write_file", write_file)
tool_registry.register("read_file", read_file)
tool_registry.register("edit_file", edit_file)
tool_registry.register("list_files", list_files)
