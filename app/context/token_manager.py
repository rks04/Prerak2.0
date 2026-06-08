class TokenManager:
    """Manages context size using a strict character budget."""
    def __init__(self, max_chars: int = 14000):
        self.max_chars = max_chars

    def trim_text(self, text: str, budget: int) -> str:
        if len(text) <= budget:
            return text
        return text[:budget] + "\n\n[...TRUNCATED DUE TO CONTEXT LIMIT...]"
