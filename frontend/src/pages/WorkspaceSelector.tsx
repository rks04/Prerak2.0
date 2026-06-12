import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { FolderOpen } from "lucide-react";
import { Button } from "@/components/ui/button";
import { API_BASE_URL } from '../config';

export function WorkspaceSelector() {
  const [path, setPath] = useState("D:/Riya/MyProject");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const navigate = useNavigate();

  const handleOpen = async () => {
    setLoading(true);
    setError("");
    try {
      const res = await fetch(`${API_BASE_URL}/api/workspace/open`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ path }),
      });
      
      if (!res.ok) {
        const data = await res.json();
        throw new Error(data.detail || "Failed to open workspace");
      }
      
      const data = await res.json();
      // Navigate to the dynamic ChatPage route
      navigate(`/code/${data.workspace_id}/${data.conversation_id}`);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex flex-col items-center justify-center h-screen bg-background text-foreground">
      <div className="max-w-md w-full bg-card p-8 rounded-lg shadow-lg border border-border">
        <div className="flex flex-col items-center mb-6">
          <FolderOpen className="w-12 h-12 text-primary mb-4" />
          <h1 className="text-2xl font-bold tracking-tight">PRERAK 2.0</h1>
          <p className="text-muted-foreground mt-2">Open a workspace to continue</p>
        </div>
        
        <div className="space-y-4">
          <div>
            <label className="text-sm font-medium mb-1 block">Workspace Path</label>
            <input
              type="text"
              value={path}
              onChange={(e) => setPath(e.target.value)}
              className="w-full p-2 bg-secondary text-foreground rounded border border-border focus:outline-none focus:ring-2 focus:ring-primary"
              placeholder="e.g. D:/Riya/MyProject"
            />
          </div>
          
          {error && <div className="text-destructive text-sm font-medium">{error}</div>}
          
          <button
            onClick={handleOpen}
            disabled={loading || !path}
            className="w-full bg-primary text-primary-foreground p-2 rounded font-semibold hover:bg-primary/90 disabled:opacity-50 transition-colors"
          >
            {loading ? "Opening..." : "Open Workspace"}
          </button>
        </div>
      </div>
    </div>
  );
}
