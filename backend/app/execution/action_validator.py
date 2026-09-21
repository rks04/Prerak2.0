import json
from typing import Dict, Any, List, Optional
from pydantic import BaseModel

class ValidationResult(BaseModel):
    success: bool
    repaired: bool = False
    repairs: List[str] = []
    error: Optional[str] = None
    kwargs: Dict[str, Any] = {}
    error_type: Optional[str] = None

class ActionValidator:
    def __init__(self, tool_registry):
        self.registry = tool_registry
        
    def validate(self, tool_name: str, kwargs: Dict[str, Any]) -> ValidationResult:
        schemas = self.registry.get_all_tool_schemas()
        tool_schema = next((s for s in schemas if s["tool_name"] == tool_name), None)
        
        if not tool_schema:
            return ValidationResult(success=False, error=f"Unknown tool: {tool_name}", error_type="UNKNOWN_TOOL")
            
        result_kwargs = dict(kwargs)
        repairs = []
        
        # Check required fields
        for req in tool_schema.get("required", []):
            if req not in result_kwargs:
                return ValidationResult(success=False, error=f"Missing required parameter: {req}", error_type="MISSING_REQUIRED_FIELD")
                
        # Validate and repair fields based on schema
        parameters = tool_schema.get("parameters", {})
        for param_name, param_val in result_kwargs.items():
            if param_name not in parameters:
                # Optionally allow unknown params or reject. We will reject.
                return ValidationResult(success=False, error=f"Unknown parameter: {param_name}", error_type="UNKNOWN_PARAMETER")
                
            param_schema = parameters[param_name]
            expected_type = param_schema.get("type")
            
            if expected_type == "object" and isinstance(param_val, str):
                try:
                    parsed = json.loads(param_val)
                    if isinstance(parsed, dict):
                        result_kwargs[param_name] = parsed
                        repairs.append(f"Parsed {param_name} from JSON string to object")
                    else:
                        return ValidationResult(success=False, error=f"{param_name} expected object, received JSON string resolving to {type(parsed).__name__}", error_type="TYPE_MISMATCH")
                except json.JSONDecodeError:
                    return ValidationResult(success=False, error=f"{param_name} expected object, but could not parse string as JSON", error_type="INVALID_JSON")
                    
            elif expected_type == "array" and isinstance(param_val, str):
                try:
                    parsed = json.loads(param_val)
                    if isinstance(parsed, list):
                        result_kwargs[param_name] = parsed
                        repairs.append(f"Parsed {param_name} from JSON string to array")
                except:
                    pass
                    
            elif expected_type == "integer" and isinstance(param_val, str):
                if param_val.isdigit():
                    result_kwargs[param_name] = int(param_val)
                    repairs.append(f"Parsed {param_name} from string to integer")
                    
            elif expected_type == "boolean" and isinstance(param_val, str):
                lower_val = param_val.lower()
                if lower_val in ["true", "false"]:
                    result_kwargs[param_name] = lower_val == "true"
                    repairs.append(f"Parsed {param_name} from string to boolean")
                    
            # Enums
            if "enum" in param_schema and isinstance(result_kwargs[param_name], str):
                val = result_kwargs[param_name]
                allowed = param_schema["enum"]
                if val not in allowed:
                    # Attempt case-insensitive match
                    lower_match = next((a for a in allowed if str(a).lower() == val.lower()), None)
                    if lower_match:
                        result_kwargs[param_name] = lower_match
                        repairs.append(f"Normalized enum {param_name} case from {val} to {lower_match}")
                    else:
                        return ValidationResult(success=False, error=f"{param_name} must be one of {allowed}, got {val}", error_type="INVALID_ENUM")

        return ValidationResult(
            success=True,
            repaired=len(repairs) > 0,
            repairs=repairs,
            kwargs=result_kwargs
        )
