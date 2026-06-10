import os
import asyncio
from app.agents.orchestrator import Orchestrator

async def main():
    workspace_root = os.path.abspath("./workspace_test")
    os.makedirs(workspace_root, exist_ok=True)
    
    print(f"Starting Hello World deterministic test in {workspace_root}...")
    orchestrator = Orchestrator(workspace_root=workspace_root)
    
    prompt = "Create hello.py with Hello World"
    print(f"User Prompt: {prompt}")
    
    success = await orchestrator.run_pipeline(convo_id="test_convo", prompt=prompt)
    
    if success:
        print("[SUCCESS] Pipeline executed successfully! Hello World test passed.")
        with open(os.path.join(workspace_root, "hello.py"), "r", encoding="utf-8") as f:
            print("Content of hello.py:", f.read().strip())
    else:
        print("[FAILED] Pipeline failed.")

if __name__ == "__main__":
    asyncio.run(main())
