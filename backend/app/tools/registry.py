from typing import Callable, Dict, Literal, get_origin, get_args, Any, Union, Optional
from app.security.tool_permissions import ALLOWED_TOOLS
from pydantic import BaseModel
import inspect

class ToolRegistry:
    def __init__(self):
        self._tools: Dict[str, Callable] = {}
        self._schema_cache = None

    def register(self, name: str, func: Callable):
        if name in ALLOWED_TOOLS:
            self._tools[name] = func
            self._schema_cache = None

    def get_tool(self, name: str) -> Callable:
        return self._tools.get(name)

    def _type_to_json_schema(self, t: Any) -> dict:
        if isinstance(t, type) and issubclass(t, BaseModel):
            return t.model_json_schema()
            
        origin = get_origin(t)
        args = get_args(t)
        
        if origin is Literal:
            return {"type": "string", "enum": list(args)}
            
        if origin is Union:
            # Handle Optional
            if type(None) in args:
                non_none_args = [a for a in args if a is not type(None)]
                if len(non_none_args) == 1:
                    schema = self._type_to_json_schema(non_none_args[0])
                    # JSON Schema draft doesn't formally use "nullable" but many dialects do.
                    # Alternatively, anyOf with null. We'll stick to basic mapping.
                    return schema
            return {"anyOf": [self._type_to_json_schema(a) for a in args]}
            
        if origin is list or t is list or getattr(t, "__name__", "") == "List" or str(t).startswith("typing.List"):
            items_schema = self._type_to_json_schema(args[0]) if args else {}
            return {"type": "array", "items": items_schema}
            
        if origin is dict or t is dict or getattr(t, "__name__", "") == "Dict" or str(t).startswith("typing.Dict"):
            return {"type": "object"}
            
        if t == int:
            return {"type": "integer"}
        if t == float:
            return {"type": "number"}
        if t == bool:
            return {"type": "boolean"}
        if t == str:
            return {"type": "string"}
            
        return {"type": "string"}

    def get_all_tool_schemas(self) -> list[dict]:
        if self._schema_cache is not None:
            return self._schema_cache
            
        schemas = []
        for name, func in self._tools.items():
            sig = inspect.signature(func)
            doc = inspect.getdoc(func) or ""
            
            # The current caller of get_all_tool_schemas expects:
            # parameters: { param_name: { type: ... } }
            # required: [...]
            # We will generate that exactly.
            params = {}
            required = []
            
            for param_name, param in sig.parameters.items():
                if param_name == "workspace_root":
                    continue
                    
                param_schema = self._type_to_json_schema(param.annotation)
                params[param_name] = param_schema
                
                if param.default == inspect.Parameter.empty:
                    required.append(param_name)
                    
            schemas.append({
                "tool_name": name,
                "description": doc.split("\n")[0] if doc else f"Tool: {name}",
                "parameters": params,
                "required": required
            })
            
        self._schema_cache = schemas
        return schemas

tool_registry = ToolRegistry()

# Register core file tools
from app.tools.file_tools.write_file import write_file
from app.tools.file_tools.read_file import read_file
from app.tools.file_tools.edit_file import edit_file
from app.tools.file_tools.delete_file import delete_file
from app.tools.workspace_tools.list_files import list_files
from app.tools.terminal_tools.execute_terminal import execute_terminal

from app.tools.workspace_tools.search_code import search_code_semantic
from app.tools.workspace_tools.search_code_exact import search_code_exact
from app.tools.workspace_tools.http_request import http_request
from app.tools.workspace_tools.create_project import create_project
from app.tools.terminal_tools.tail_process_logs import tail_process_logs
from app.tools.models import ToolResult

tool_registry.register("write_file", write_file)
tool_registry.register("read_file", read_file)
tool_registry.register("edit_file", edit_file)
tool_registry.register("delete_file", delete_file)
tool_registry.register("list_files", list_files)
tool_registry.register("execute_terminal", execute_terminal)
tool_registry.register("search_code_semantic", search_code_semantic)
tool_registry.register("search_code_exact", search_code_exact)
tool_registry.register("http_request", http_request)
tool_registry.register("create_project", create_project)
tool_registry.register("tail_process_logs", tail_process_logs)
