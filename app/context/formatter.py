from typing import List, Dict

class Formatter:
    """Formats assembled context into plain structured text (NO XML)."""
    
    def format_context(self, prompt: str, recent_messages: List[Dict[str, str]], workspace_files: List[str], loaded_file_contents: Dict[str, str]) -> str:
        parts = []
        
        # 1. Recent Messages
        if recent_messages:
            parts.append("=== RECENT MESSAGES ===")
            for msg in recent_messages:
                parts.append(f"User:\n{msg['prompt']}")
            parts.append("")
            
        # 2. Workspace Status
        parts.append("=== WORKSPACE FILES ===")
        if workspace_files:
            for f in workspace_files:
                parts.append(f"- {f}")
        else:
            parts.append("(Empty workspace)")
        parts.append("")
        
        # 3. Loaded Files
        for fpath, content in loaded_file_contents.items():
            parts.append(f"=== FILE: {fpath} ===")
            parts.append(content)
            parts.append("")
            
        # 4. Current Prompt
        parts.append("=== CURRENT REQUEST ===")
        parts.append(prompt)
        
        return "\n".join(parts)
