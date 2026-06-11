import asyncio
from pathlib import Path
from app.events.schema import PrerakEvent

class FileLoggerSubscriber:
    """Appends structured events to an execution session log file asynchronously."""
    def __init__(self, log_dir: str = "logs"):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
    async def handle_event(self, event: PrerakEvent):
        def _write():
            if event.workspace_root:
                # CODE MEMORY: Global memory for workspace chats
                import hashlib
                path_hash = hashlib.md5(event.workspace_root.encode('utf-8')).hexdigest()[:8]
                workspace_name = f"{Path(event.workspace_root).name}_{path_hash}"
                base_dir = Path(".memory") / "code" / workspace_name / event.conversation_id
            else:
                # CHAT MEMORY: Global memory for non-workspace chats
                base_dir = Path(".memory") / "chat" / event.conversation_id
                
            base_dir.mkdir(parents=True, exist_ok=True)
            
            # Write meta.json if it doesn't exist
            meta_file = base_dir / "meta.json"
            if not meta_file.exists():
                import json
                from datetime import datetime
                meta_data = {
                    "conversation_id": event.conversation_id,
                    "workspace": event.workspace_root if event.workspace_root else "",
                    "created_at": datetime.utcnow().isoformat(),
                    "last_active": datetime.utcnow().isoformat(),
                    "model": "qwen2.5-coder:7b",
                    "title": "New Conversation"
                }
                with open(meta_file, "w", encoding="utf-8") as f:
                    json.dump(meta_data, f, indent=2)
                    
                # Initialize other memory files
                with open(base_dir / "summary.json", "w", encoding="utf-8") as f:
                    json.dump({"summary": ""}, f, indent=2)
                with open(base_dir / "tasks.json", "w", encoding="utf-8") as f:
                    json.dump({"tasks": []}, f, indent=2)
                with open(base_dir / "workspace-state.json", "w", encoding="utf-8") as f:
                    json.dump({"active_files": []}, f, indent=2)
            else:
                # Update last_active
                try:
                    import json
                    from datetime import datetime
                    with open(meta_file, "r", encoding="utf-8") as f:
                        meta_data = json.load(f)
                    meta_data["last_active"] = datetime.utcnow().isoformat()
                    with open(meta_file, "w", encoding="utf-8") as f:
                        json.dump(meta_data, f, indent=2)
                except Exception:
                    pass
            
            log_file = base_dir / "messages.json"
            with open(log_file, "a", encoding="utf-8") as f:
                f.write(event.model_dump_json() + "\n")
        
        await asyncio.to_thread(_write)
