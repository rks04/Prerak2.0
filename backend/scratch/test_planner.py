import asyncio
from app.agents.planner_agent import PlannerAgent

async def test():
    planner = PlannerAgent()
    try:
        out = await planner.decompose_task("Create a python script", "Context goes here")
        print("Success:", out)
    except Exception as e:
        print("Caught Exception:", type(e), str(e))
    except BaseException as e:
        print("Caught BaseException:", type(e), str(e))

asyncio.run(test())
