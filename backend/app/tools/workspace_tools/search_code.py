import json
from app.tools.models import ToolResult
from app.context.workspace_indexer import WorkspaceIndexer

def search_code(workspace_root: str, query: str) -> ToolResult:
    """Semantically searches the workspace codebase for the query."""
    print(f"SEARCH_CODE: started with query '{query}'")
    try:
        from app.context.workspace_indexer import get_indexer
        
        print("Loading WorkspaceIndexer (ChromaClient)...")
        indexer = get_indexer(workspace_root)
        
        print("Checking incremental index...")
        # Ensure the index is up-to-date (this is very fast incrementally)
        indexer.index_workspace()
        
        print("Running vector search...")
        
        # Query ChromaDB
        results = indexer.collection.query(
            query_texts=[query],
            n_results=5
        )
        
        if not results or not results["documents"] or not results["documents"][0]:
            return ToolResult(success=True, output="No relevant code found.")
            
        # Format results
        formatted_results = []
        for doc, metadata in zip(results["documents"][0], results["metadatas"][0]):
            file_path = metadata.get("file_path", "Unknown File")
            formatted_results.append(f"--- File: {file_path} ---\n{doc}\n")
            
        final_output = "\n".join(formatted_results)
        return ToolResult(success=True, output=final_output)
        
    except Exception as e:
        return ToolResult(success=False, error=str(e))
