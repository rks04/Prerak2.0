from fastapi import APIRouter, BackgroundTasks
import asyncio
from app.agents.orchestrator import Orchestrator
import os
from pydantic import BaseModel

from app.db.database import AsyncSessionLocal
from app.db.repositories.workspace_repo import WorkspaceRepository

class TriggerRequest(BaseModel):
    prompt: str
    convo_id: str
    workspace_id: str

router = APIRouter()

from app.db.database import DBState

@router.get("/health")
async def health_check():
    return {
        "database": "connected" if DBState.is_connected else "disconnected",
        "ollama": "connected", # Assuming always connected for now, can be updated later
        "websocket": "active"
    }

@router.post("/trigger")
async def trigger_pipeline(req: TriggerRequest, background_tasks: BackgroundTasks):
    if not req.convo_id or req.convo_id == "undefined":
        raise HTTPException(status_code=400, detail="Invalid conversation_id")
        
    workspace_root = "./workspace_test" # Fallback
    if AsyncSessionLocal is not None:
        async with AsyncSessionLocal() as session:
            repo = WorkspaceRepository(session)
            ws = await repo.get_by_id(req.workspace_id)
            if ws:
                workspace_root = ws.workspace_path

    if not os.path.exists(workspace_root):
        os.makedirs(workspace_root, exist_ok=True)
        
    orchestrator = Orchestrator(workspace_root=workspace_root, workspace_id=req.workspace_id)
    
    # Run in background to allow websockets to stream while this executes
    background_tasks.add_task(orchestrator.run_pipeline, req.convo_id, req.prompt)
    return {"message": f"Pipeline triggered for prompt: {req.prompt}"}
