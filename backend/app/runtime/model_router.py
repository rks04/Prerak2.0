class ModelRouter:
    """Routes logical roles to specific Ollama models based on architecture guidelines."""
    
    @staticmethod
    def get_planner_model() -> str:
        return "Qwen2.5:7b"
        
    @staticmethod
    def get_coder_model() -> str:
        return "Qwen2.5-Coder:14b"
        
    @staticmethod
    def get_reasoner_model() -> str:
        return "DeepSeek-R1:14b"
        
    @staticmethod
    def get_verifier_model() -> str:
        return "Qwen2.5:3b"
        
    @staticmethod
    def get_summarizer_model() -> str:
        return "Gemma3:4b"
