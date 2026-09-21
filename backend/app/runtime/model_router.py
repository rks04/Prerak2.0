import httpx
import logging
from app.core.config import settings

logger = logging.getLogger(__name__)

class ModelRouter:
    """Handles communication with the central AI Inference server and routes logical roles to models."""
    
    def __init__(self):
        # We load the base URL from settings, which automatically pulls from the OLLAMA_HOST env variable
        self.base_url = settings.OLLAMA_HOST

    @staticmethod
    def get_planner_model() -> str:
        return "qwen3.5:latest"
        
    @staticmethod
    def get_coder_model() -> str:
        return "ornith:35b"
        
    @staticmethod
    def get_reasoner_model() -> str:
        return "deepseek-r1:7b"  
        
    @staticmethod
    def get_verifier_model() -> str:
        return "qwen3.5:latest"
        
    @staticmethod
    def get_summarizer_model() -> str:
        return "gemma4:latest"

    async def health_check(self) -> bool:
        """
        Checks if the remote AI inference server is available.
        Performs a fast GET to the /api/version endpoint.
        """
        url = f"{self.base_url}/api/version"
        async with httpx.AsyncClient(timeout=5.0) as client:
            try:
                response = await client.get(url)
                response.raise_for_status()
                return True
            except Exception as e:
                logger.error(f"Remote AI unavailable at {self.base_url}. Error: {e}")
                return False

    async def generate(self, model: str, prompt: str, system_prompt: str, temperature: float = 0.1, json_mode: bool = True) -> str:
        """
        Routes the generation request to the AI server.
        """
        # 1. Health check before proceeding
        is_healthy = await self.health_check()
        if not is_healthy:
            raise RuntimeError(f"Remote AI unavailable at {self.base_url}. Please ensure the server is running and accessible.")

        # 2. Build request
        url = f"{self.base_url}/api/generate"
        payload = {
            "model": model,
            "prompt": prompt,
            "system": system_prompt,
            "stream": False,
            "options": {
                "temperature": temperature
            }
        }
        if json_mode:
            payload["format"] = "json"
            
        # 3. Call AI Inference Server
        
        async with httpx.AsyncClient(timeout=900.0) as client:
            try:
                response = await client.post(url, json=payload)
                response.raise_for_status()
                
                # HOW IT IS PARSED:
                data = response.json()
                
                # EXTRACTING THE TEXT:
                # Robust extraction layer (Phase 15: Multi-Model Compatibility)
                text = (
                    data.get("response") 
                    or data.get("message", {}).get("content") 
                    or data.get("thinking") 
                    or ""
                )
                
                return str(text).strip()
            except httpx.HTTPStatusError as e:
                error_body = e.response.text
                try:
                    error_json = e.response.json()
                    error_body = error_json.get("error", error_body)
                except Exception:
                    pass
                raise RuntimeError(f"AI API Error [{e.response.status_code}]: {error_body}")
            except httpx.TimeoutException:
                raise TimeoutError("AI inference took too long to respond (> 900s). Try a simpler prompt or ensure the remote server isn't overloaded.")
            except Exception as e:
                raise RuntimeError(f"AI connection error: {str(e)}")

model_router = ModelRouter()
