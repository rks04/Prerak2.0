import re
from typing import List, Dict, Any, Optional

class BaseCompilerParser:
    def can_parse(self, output: str) -> bool:
        raise NotImplementedError
        
    def parse(self, output: str) -> Dict[str, Any]:
        raise NotImplementedError

class TypeScriptParser(BaseCompilerParser):
    def can_parse(self, output: str) -> bool:
        return "TS" in output and ("error TS" in output or "warning TS" in output)
        
    def parse(self, output: str) -> Dict[str, Any]:
        diagnostics = []
        # Match lines like: src/product/product.controller.ts:11:3 - error TS4053: Return type cannot be named
        pattern = re.compile(r"^(.+?):(\d+):(\d+)\s+-\s+(error|warning)\s+(TS\d+):\s+(.+)$")
        
        for line in output.splitlines():
            match = pattern.match(line.strip())
            if match:
                file_path, line_num, col_num, severity, code, message = match.groups()
                diagnostics.append({
                    "file": file_path,
                    "line": int(line_num),
                    "column": int(col_num),
                    "severity": severity,
                    "code": code,
                    "message": message,
                    "parser": "typescript"
                })
                
        return {
            "language": "typescript",
            "diagnostics": diagnostics
        }

class PythonParser(BaseCompilerParser):
    def can_parse(self, output: str) -> bool:
        # Match typical traceback or flake8 output
        return "Traceback (most recent call last):" in output or "SyntaxError:" in output or re.search(r"\.py:\d+:\d+:", output) is not None
        
    def parse(self, output: str) -> Dict[str, Any]:
        diagnostics = []
        # Flake8 style: file.py:10:5: E225 missing whitespace around operator
        flake8_pattern = re.compile(r"^(.+?):(\d+):(\d+):\s+([A-Z]\d+)\s+(.+)$")
        
        for line in output.splitlines():
            match = flake8_pattern.match(line.strip())
            if match:
                file_path, line_num, col_num, code, message = match.groups()
                diagnostics.append({
                    "file": file_path,
                    "line": int(line_num),
                    "column": int(col_num),
                    "severity": "error" if code.startswith('E') or code.startswith('F') else "warning",
                    "code": code,
                    "message": message,
                    "parser": "python"
                })
        
        return {
            "language": "python",
            "diagnostics": diagnostics
        }

class ParserRegistry:
    def __init__(self):
        self.parsers = [
            TypeScriptParser(),
            PythonParser()
        ]
        
    def parse_diagnostics(self, output: str) -> Optional[Dict[str, Any]]:
        if not output:
            return None
            
        for parser in self.parsers:
            if parser.can_parse(output):
                result = parser.parse(output)
                if result and result.get("diagnostics"):
                    return result
                    
        return None

parser_registry = ParserRegistry()
