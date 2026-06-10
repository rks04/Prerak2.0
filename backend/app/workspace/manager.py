from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.db.models import Workspace, Conversation, Execution, TouchedFile
import os

class WorkspaceManager:
    """Core subsystem for handling persistent workspace intelligence."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
        
    async def open_workspace(self, path: str) -> dict:
        """Finds or creates a workspace, and ensures an active conversation exists."""
        normalized_path = os.path.normpath(path)
        
        # 1. Find or create workspace
        result = await self.session.execute(select(Workspace).where(Workspace.workspace_path == normalized_path))
        workspace = result.scalars().first()
        
        if not workspace:
            workspace = Workspace(workspace_path=normalized_path)
            self.session.add(workspace)
            await self.session.commit()
            await self.session.refresh(workspace)
            
        # 2. Find or create the latest conversation
        conv_result = await self.session.execute(
            select(Conversation)
            .where(Conversation.workspace_id == workspace.id)
            .order_by(Conversation.updated_at.desc())
        )
        conversation = conv_result.scalars().first()
        
        if not conversation:
            conversation = Conversation(
                workspace_id=workspace.id,
                title="New Conversation"
            )
            self.session.add(conversation)
            await self.session.commit()
            await self.session.refresh(conversation)
            
        return {
            "workspace": workspace,
            "conversation": conversation
        }
        
    async def save_execution_state(
        self, 
        workspace_id: str, 
        conversation_id: str, 
        execution_id: str, 
        prompt: str,
        state: str, 
        success: bool, 
        touched_files: list[dict]
    ):
        """Saves execution history and touched files to the database."""
        
        # Save Execution
        execution = Execution(
            execution_id=execution_id,
            conversation_id=conversation_id,
            state=state,
            success=success
        )
        # Note: Added dynamically since schema evolution is ongoing
        if hasattr(execution, 'prompt'):
            execution.prompt = prompt
            
        self.session.add(execution)
        
        # Save touched files
        for f in touched_files:
            tf = TouchedFile(
                execution_id=execution_id,
                workspace_id=workspace_id,
                file_path=f["path"],
                action=f["action"]
            )
            self.session.add(tf)
            
        # Update conversation timestamp
        conv_result = await self.session.execute(select(Conversation).where(Conversation.id == conversation_id))
        conv = conv_result.scalars().first()
        if conv:
            if hasattr(conv, 'last_message_preview'):
                conv.last_message_preview = prompt[:100]
                
        await self.session.commit()

    async def get_recent_touched_files(self, workspace_id: str, limit: int = 5) -> list[str]:
        """Fetches the most recently modified files across all executions in this workspace."""
        result = await self.session.execute(
            select(TouchedFile.file_path)
            .where(TouchedFile.workspace_id == workspace_id)
            .order_by(TouchedFile.timestamp.desc())
            .limit(limit * 3) # Fetch more to account for duplicates
        )
        
        paths = []
        for path in result.scalars().all():
            if path not in paths:
                paths.append(path)
            if len(paths) >= limit:
                break
        return paths
