class ModelRouter:
    """Routes logical roles to specific Ollama models based on architecture guidelines."""
    
    @staticmethod
    def get_planner_model() -> str:
        return "llama3.1:latest"
        
    @staticmethod
    def get_coder_model() -> str:
        return "Qwen2.5-Coder:7b"
        
    @staticmethod
    def get_recovery_model() -> str:
        return "llama3.1:latest"
