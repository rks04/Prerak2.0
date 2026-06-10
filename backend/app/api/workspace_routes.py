from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.workspace.manager import WorkspaceManager
from pydantic import BaseModel
import os

router = APIRouter()

class OpenWorkspaceRequest(BaseModel):
    path: str

@router.post("/open")
async def open_workspace(req: OpenWorkspaceRequest, db: AsyncSession = Depends(get_db)):
    if not os.path.exists(req.path):
        raise HTTPException(status_code=400, detail="Path does not exist on disk.")
        
    manager = WorkspaceManager(db)
    result = await manager.open_workspace(req.path)
    
    return {
        "workspace_id": result["workspace"].id,
        "workspace_path": result["workspace"].workspace_path,
        "conversation_id": result["conversation"].id,
        "message": "Workspace restored successfully"
    }

@router.get("/{workspace_id}/conversations")
async def get_workspace_conversations(workspace_id: str, db: AsyncSession = Depends(get_db)):
    from app.db.models import Conversation
    result = await db.execute(
        select(Conversation)
        .where(Conversation.workspace_id == workspace_id)
        .order_by(Conversation.updated_at.desc())
    )
    convos = result.scalars().all()
    return [{"id": c.id, "title": c.title, "updated_at": c.updated_at.isoformat() if c.updated_at else None} for c in convos]

@router.post("/{workspace_id}/conversation")
async def create_new_conversation(workspace_id: str, db: AsyncSession = Depends(get_db)):
    from app.db.models import Conversation
    result = await db.execute(select(Workspace).where(Workspace.id == workspace_id))
    workspace = result.scalars().first()
    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace not found")
        
    conversation = Conversation(
        workspace_id=workspace.id,
        title="New Conversation"
    )
    db.add(conversation)
    await db.commit()
    await db.refresh(conversation)
    
    return {
        "conversation_id": conversation.id,
        "message": "New conversation created"
    }

import json
from sqlalchemy.future import select
from app.db.models import Workspace

@router.get("/{workspace_id}/conversation/{conversation_id}")
async def get_conversation_history(workspace_id: str, conversation_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Workspace).where(Workspace.id == workspace_id))
    workspace = result.scalars().first()
    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace not found")
        
    events = []
    log_path = os.path.join(workspace.workspace_path, ".prerak", conversation_id, "messages.json")
    if os.path.exists(log_path):
        with open(log_path, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    try:
                        events.append(json.loads(line))
                    except:
                        pass
                        
    return {
        "workspace_name": os.path.basename(workspace.workspace_path),
        "workspace_path": workspace.workspace_path,
        "events": events
    }
