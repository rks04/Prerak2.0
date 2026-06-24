class ModelRouter:
    """Routes logical roles to specific Ollama models based on architecture guidelines."""
    
    @staticmethod
    def get_planner_model() -> str:
        return "qwen2.5:3b"
        
    @staticmethod
    def get_coder_model() -> str:
        return "qwen2.5-coder:7b"
        
    @staticmethod
    def get_reasoner_model() -> str:
        return "deepseek-r1:7b"  
        
    @staticmethod
    def get_verifier_model() -> str:
        return "qwen2.5:3b"
        
    @staticmethod
    def get_summarizer_model() -> str:
        return "gemma2:2b"
