import json
import urllib.request
import urllib.error
import time
from typing import Dict, Any, Optional
from app.tools.models import ToolResult

def http_request(method: str, url: str, headers: Optional[Dict[str, str]] = None, json_data: Optional[Dict[str, Any]] = None) -> ToolResult:
    """Make an HTTP request and return the structured response. Use this instead of curl. Supported methods: GET, POST, PUT, DELETE, PATCH.
    json_data: Python object. Do NOT serialize into a string. The executor serializes automatically.
    """
    if headers is None:
        headers = {}
        
    if isinstance(json_data, str):
        try:
            json_data = json.loads(json_data)
        except:
            pass

    data = None
    if json_data is not None:
        try:
            data = json.dumps(json_data).encode('utf-8')
            headers['Content-Type'] = 'application/json'
        except TypeError as e:
            result = {
                "success": False,
                "error_type": "invalid_json",
                "message": f"Failed to encode json_data: {str(e)}",
                "status_code": None
            }
            return ToolResult(success=False, error=json.dumps(result))

    req = urllib.request.Request(url, data=data, headers=headers, method=method.upper())
    
    start_time = time.time()
    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            elapsed_ms = int((time.time() - start_time) * 1000)
            status_code = response.getcode()
            resp_headers = dict(response.headers)
            body_bytes = response.read()
            
            try:
                body = json.loads(body_bytes.decode('utf-8'))
            except Exception:
                body = body_bytes.decode('utf-8', errors='replace')
                
            result = {
                "success": True,
                "status_code": status_code,
                "headers": resp_headers,
                "body": body,
                "elapsed_ms": elapsed_ms
            }
            return ToolResult(success=True, output=json.dumps(result))
            
    except urllib.error.HTTPError as e:
        elapsed_ms = int((time.time() - start_time) * 1000)
        try:
            body = json.loads(e.read().decode('utf-8'))
        except Exception:
            body = e.read().decode('utf-8', errors='replace')
            
        result = {
            "success": False,
            "error_type": "http_error",
            "message": str(e),
            "status_code": e.code,
            "headers": dict(e.headers),
            "body": body,
            "elapsed_ms": elapsed_ms
        }
        return ToolResult(success=False, error=json.dumps(result))
    except urllib.error.URLError as e:
        reason = str(e.reason).lower()
        error_type = "network_error"
        if "connection refused" in reason or "refused" in reason:
            error_type = "connection_refused"
        elif "timed out" in reason or "timeout" in reason:
            error_type = "timeout"
        elif "certificate verify failed" in reason:
            error_type = "ssl_error"
        elif "getaddrinfo failed" in reason:
            error_type = "dns_failure"
            
        result = {
            "success": False,
            "error_type": error_type,
            "message": str(e.reason),
            "status_code": None
        }
        return ToolResult(success=False, error=json.dumps(result))
    except Exception as e:
        result = {
            "success": False,
            "error_type": "unknown_error",
            "message": str(e),
            "status_code": None
        }
        return ToolResult(success=False, error=json.dumps(result))
