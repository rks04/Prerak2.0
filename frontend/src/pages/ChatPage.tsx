import { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { useSocketStore } from "@/stores/socketStore";
import { ExecutionTimeline } from "@/components/execution/ExecutionTimeline";
import { PromptInput } from "@/components/chat/PromptInput";
import { Badge } from "@/components/ui/badge";
import { API_BASE_URL } from '../config';
import { FolderOpen, Plus } from "lucide-react";

export function ChatPage() {
  const { workspaceId, conversationId } = useParams();
  const navigate = useNavigate();
  const { connect, disconnect, joinRoom, isConnected, setEvents } = useSocketStore();
  const [workspaceName, setWorkspaceName] = useState<string>("Loading...");
  const [workspacePath, setWorkspacePath] = useState<string>("");
  const [conversations, setConversations] = useState<any[]>([]);

  useEffect(() => {
    if (!workspaceId || !conversationId || conversationId === "undefined") {
      navigate("/");
      return;
    }
    
    // Fetch historical events and workspace details
    fetch(`${API_BASE_URL}/api/workspace/${workspaceId}/conversation/${conversationId}`)
      .then(res => res.json())
      .then(data => {
        if (data.workspace_name) setWorkspaceName(data.workspace_name);
        if (data.workspace_path) setWorkspacePath(data.workspace_path);
        if (data.events) setEvents(data.events);
      })
      .catch(console.error);

    // Fetch all conversations for the sidebar
    fetch(`${API_BASE_URL}/api/workspace/${workspaceId}/conversations`)
      .then(res => res.json())
      .then(data => {
        setConversations(data);
      })
      .catch(console.error);

    if (conversationId && conversationId !== "undefined") {
      connect();
      joinRoom(conversationId);
    }
    // Cleanup connection when navigating away
    return () => disconnect();
  }, [connect, disconnect, joinRoom, workspaceId, conversationId, navigate, setEvents]);

  const handleNewConversation = async () => {
    const targetPath = window.prompt("Enter workspace path for the new conversation:", workspacePath);
    if (!targetPath) return;

    try {
      // 1. Resolve workspace
      const wsRes = await fetch(`${API_BASE_URL}/api/workspace/open`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ path: targetPath }),
      });
      if (!wsRes.ok) throw new Error("Failed to resolve workspace path.");
      const wsData = await wsRes.json();

      // 2. Force new conversation in resolved workspace
      const res = await fetch(`${API_BASE_URL}/api/workspace/${wsData.workspace_id}/conversation`, {
        method: "POST"
      });
      
      if (res.ok) {
        const data = await res.json();
        setEvents([]); // Clear current events immediately for UX
        navigate(`/code/${wsData.workspace_id}/${data.conversation_id}`);
      }
    } catch (e: any) {
      console.error("Failed to create new conversation", e);
      alert(e.message || "Failed to create conversation");
    }
  };

  const handleSend = async (prompt: string) => {
    if (!conversationId || conversationId === "undefined") {
      console.error("Workspace not fully initialized");
      return;
    }
    try {
      await fetch(`${API_BASE_URL}/api/trigger`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ prompt, convo_id: conversationId, workspace_id: workspaceId })
      });
    } catch (e) {
      console.error("Failed to trigger pipeline", e);
    }
  };

  return (
    <div className="flex h-screen bg-background text-foreground overflow-hidden">
      {/* Sidebar - Connection Status */}
      <div className="w-64 border-r border-border bg-card p-4 flex flex-col">
        <h1 className="text-xl font-bold mb-4 tracking-tight">PRERAK 2.0</h1>
        <div className="flex items-center space-x-2 mb-6">
          <Badge variant={isConnected ? "default" : "destructive"}>
            {isConnected ? "CONNECTED" : "DISCONNECTED"}
          </Badge>
        </div>
        <div className="flex-1">
          <div className="text-sm font-medium text-muted-foreground mb-2 flex items-center gap-2">
            <FolderOpen className="w-4 h-4" /> Workspace
          </div>
          <div className="p-2 bg-secondary rounded text-xs font-mono mb-4 break-all">
            {workspaceName}
          </div>
          <div className="flex items-center justify-between text-sm font-medium text-muted-foreground mb-2">
            <span>Conversations</span>
            <button 
              onClick={handleNewConversation}
              className="p-1 hover:bg-secondary rounded text-primary transition-colors"
              title="New Conversation"
            >
              <Plus className="w-4 h-4" />
            </button>
          </div>
          <div className="space-y-2 overflow-y-auto max-h-[50vh]">
            {conversations.map(c => (
              <div 
                key={c.id}
                onClick={() => navigate(`/code/${workspaceId}/${c.id}`)}
                className={`p-2 rounded text-sm cursor-pointer border transition-colors ${c.id === conversationId ? 'bg-primary/20 border-primary/50 text-primary' : 'bg-secondary border-transparent hover:border-primary/30'}`}
              >
                <div className="font-medium truncate">{c.title}</div>
                <div className="text-xs text-muted-foreground mt-1">#{c.id.substring(0,8)}</div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Center - Main View */}
      <div className="flex-1 flex flex-col">
        <div className="flex-1 p-4 overflow-y-auto">
          {/* Chat history placeholder */}
          <div className="flex flex-col items-center justify-center h-full text-muted-foreground">
            <h2 className="text-2xl font-semibold mb-2">Agent Execution Sandbox</h2>
            <p>Enter a prompt to watch the determinisic execution engine stream live events.</p>
          </div>
        </div>
        <PromptInput onSend={handleSend} />
      </div>

      {/* Right - Execution Timeline */}
      <div className="w-[500px]">
        <ExecutionTimeline />
      </div>
    </div>
  );
}
