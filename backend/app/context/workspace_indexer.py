import os
import json
import chromadb
from pathlib import Path

IGNORE_DIRS = {
    ".git", "node_modules", "venv", "__pycache__", 
    ".memory", ".prerak", "dist", "build", "logs", 
    "migrations", "scratch"
}

SUPPORTED_EXTENSIONS = {
    ".py", ".js", ".ts", ".jsx", ".tsx", ".html", 
    ".css", ".json", ".md", ".txt", ".yml", ".yaml",
    ".java", ".c", ".cpp", ".h", ".go", ".rs"
}

class WorkspaceIndexer:
    def __init__(self, workspace_root: str):
        self.workspace_root = Path(workspace_root)
        self.prerak_dir = self.workspace_root / ".prerak"
        self.prerak_dir.mkdir(parents=True, exist_ok=True)
        
        self.db_path = self.prerak_dir / "vector_db"
        
        # Initialize ChromaDB client pointing to the workspace's vector_db
        print("Initializing ChromaDB Client...")
        self.client = chromadb.PersistentClient(path=str(self.db_path))
        self.collection = self.client.get_or_create_collection(name="workspace_code")


    def chunk_text(self, text: str, chunk_size: int = 1500, overlap: int = 200) -> list[str]:
        """Simple character-based sliding window chunking."""
        chunks = []
        start = 0
        while start < len(text):
            end = start + chunk_size
            chunks.append(text[start:end])
            start += chunk_size - overlap
        return chunks

    def index_workspace(self):
        """Crawls the workspace and incrementally indexes files."""
        print(f"Starting incremental index for {self.workspace_root}")
        
        for p in self.workspace_root.rglob("*"):
            if not p.is_file():
                continue
                
            if p.suffix not in SUPPORTED_EXTENSIONS:
                continue
                
            # Check ignore dirs
            rel_path = p.relative_to(self.workspace_root)
            if any(part in IGNORE_DIRS for part in rel_path.parts):
                continue
                
            self.index_file(p)
            
    def index_file(self, file_path: Path):
        """Indexes a single file if it has been modified since last index."""
        rel_path = str(file_path.relative_to(self.workspace_root))
        
        try:
            mtime = os.path.getmtime(file_path)
            
            # Check if we already indexed this file with the same or newer mtime
            existing_results = self.collection.get(
                where={"file_path": rel_path},
                include=["metadatas"]
            )
            
            if existing_results and existing_results["metadatas"]:
                # Assume all chunks for this file have the same mtime
                stored_mtime = existing_results["metadatas"][0].get("mtime", 0)
                if mtime <= stored_mtime:
                    # File has not changed, skip!
                    return
                    
            # If we reached here, the file is new or modified.
            # First, delete old chunks for this file
            if existing_results and existing_results["ids"]:
                self.collection.delete(where={"file_path": rel_path})
                
            # Read and chunk the file
            content = file_path.read_text(encoding="utf-8")
            if not content.strip():
                return
                
            chunks = self.chunk_text(content)
            
            ids = []
            documents = []
            metadatas = []
            
            for i, chunk in enumerate(chunks):
                chunk_id = f"{rel_path}_{i}"
                ids.append(chunk_id)
                documents.append(chunk)
                metadatas.append({
                    "file_path": rel_path,
                    "mtime": mtime,
                    "chunk_index": i
                })
                
            # Upsert into Chroma
            self.collection.upsert(
                ids=ids,
                documents=documents,
                metadatas=metadatas
            )
            print(f"Indexed {rel_path} ({len(chunks)} chunks)")
            
        except Exception as e:
            print(f"Failed to index {rel_path}: {e}")

_INDEXERS = {}

def get_indexer(workspace_root: str) -> WorkspaceIndexer:
    if workspace_root not in _INDEXERS:
        _INDEXERS[workspace_root] = WorkspaceIndexer(workspace_root)
    return _INDEXERS[workspace_root]
