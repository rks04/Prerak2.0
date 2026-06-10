from typing import List, Dict

class Formatter:
    """Formats assembled context into plain structured text (NO XML)."""
    
    def format_planner_context(self, prompt: str, recent_messages: List[Dict[str, str]], workspace_files: List[str]) -> str:
        parts = []
        if recent_messages:
            parts.append("=== RECENT MESSAGES ===")
            # Just take the last message to keep context tiny
            parts.append(f"User: {recent_messages[-1]['prompt']}")
            parts.append("")
            
        parts.append("=== WORKSPACE FILES ===")
        if workspace_files:
            for f in workspace_files:
                parts.append(f"- {f}")
        else:
            parts.append("(Empty workspace)")
        parts.append("")
        
        parts.append("=== CURRENT REQUEST ===")
        parts.append(prompt)
        
        return "\n".join(parts)
        
    def format_coder_context(self, prompt: str, target_path: str, content: str) -> str:
        parts = []
        parts.append(f"=== TARGET FILE: {target_path} ===")
        if content:
            parts.append(content)
        else:
            parts.append("(File is empty or does not exist)")
        parts.append("")
        
        parts.append("=== ORIGINAL INSTRUCTION ===")
        parts.append(prompt)
        
        return "\n".join(parts)
