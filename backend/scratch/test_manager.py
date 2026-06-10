import asyncio
from app.db.database import AsyncSessionLocal
from app.workspace.manager import WorkspaceManager

async def test():
    try:
        async with AsyncSessionLocal() as session:
            manager = WorkspaceManager(session)
            res = await manager.open_workspace("D:/Riya/Prerak2.0/test")
            print("Result:", res)
    except Exception as e:
        import traceback
        traceback.print_exc()

asyncio.run(test())
