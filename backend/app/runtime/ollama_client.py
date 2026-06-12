import httpx
from app.core.config import settings

class OllamaClient:
    """Handles communication with the local Ollama instance."""
    def __init__(self):
        self.base_url = settings.OLLAMA_URL

    async def generate(self, model: str, prompt: str, system_prompt: str, temperature: float = 0.1, json_mode: bool = True) -> str:
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
            
        async with httpx.AsyncClient(timeout=900.0) as client:
            try:
                response = await client.post(url, json=payload)
                response.raise_for_status()
                data = response.json()
                return data.get("response", "")
            except httpx.TimeoutException:
                raise TimeoutError("Ollama took too long to respond (> 900s). Try a simpler prompt or ensure your local model is loaded.")
            except Exception as e:
                raise RuntimeError(f"Ollama connection error: {str(e)}")

ollama_client = OllamaClient()
