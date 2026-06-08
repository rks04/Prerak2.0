from fastapi import APIRouter, BackgroundTasks
import asyncio
from app.agents.orchestrator import Orchestrator
import os
from pydantic import BaseModel

class TriggerRequest(BaseModel):
    prompt: str
    convo_id: str = "test_convo"

router = APIRouter()

@router.get("/health")
async def health_check():
    return {"status": "healthy"}

@router.post("/trigger")
async def trigger_pipeline(req: TriggerRequest, background_tasks: BackgroundTasks):
    workspace_root = os.path.abspath("./workspace_test")
    os.makedirs(workspace_root, exist_ok=True)
    orchestrator = Orchestrator(workspace_root=workspace_root)
    
    # Run in background to allow websockets to stream while this executes
    background_tasks.add_task(orchestrator.run_pipeline, req.convo_id, req.prompt)
    return {"message": f"Pipeline triggered for prompt: {req.prompt}"}
