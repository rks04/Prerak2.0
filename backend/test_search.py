import os
from app.tools.workspace_tools.search_code import search_code

if __name__ == "__main__":
    workspace_root = os.path.dirname(os.path.abspath(__file__))
    print("Testing search_code in:", workspace_root)
    result = search_code(workspace_root=workspace_root, query="tool dispatch")
    print("\nResult Success:", result.success)
    if result.success:
        print(result.output[:500] + "..." if len(result.output) > 500 else result.output)
    else:
        print("Error:", result.error)
