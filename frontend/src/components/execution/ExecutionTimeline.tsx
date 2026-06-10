import { useSocketStore } from "@/stores/socketStore";
import { Card } from "@/components/ui/card";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Badge } from "@/components/ui/badge";
import { useState } from "react";
import { format } from "date-fns";
import { Brain, Code, Wrench, CheckCircle, Play, AlertTriangle, Database } from "lucide-react";

const EVENT_ICONS: Record<string, any> = {
  planner_started: Brain,
  planner_completed: Brain,
  coder_started: Code,
  coder_completed: Code,
  tool_started: Wrench,
  tool_completed: Wrench,
  verification_started: CheckCircle,
  verification_completed: CheckCircle,
  execution_started: Play,
  execution_completed: CheckCircle,
  execution_failed: AlertTriangle,
  state_transition: Play,
  context_built: Database,
};

export function ExecutionTimeline() {
  const events = useSocketStore((state) => state.events);
  const [filter, setFilter] = useState<string>("ALL");

  const filteredEvents = events.filter((e) => {
    if (filter === "ALL") return true;
    if (filter === "CONTEXT" && e.event_type === "context_built") return true;
    if (filter === "TOOLS" && e.event_type.startsWith("tool_")) return true;
    if (filter === "PLANNER" && e.event_type.startsWith("planner_")) return true;
    if (filter === "VERIFIER" && e.event_type.startsWith("verification_")) return true;
    if (filter === "ERRORS" && e.event_type === "execution_failed") return true;
    return false;
  });

  return (
    <div className="flex flex-col h-full bg-background border-l border-border">
      <div className="p-4 border-b border-border flex justify-between items-center bg-card">
        <h2 className="font-semibold text-lg">Execution Timeline</h2>
        <div className="flex space-x-2">
          {["ALL", "CONTEXT", "PLANNER", "TOOLS", "VERIFIER", "ERRORS"].map((f) => (
            <Badge 
              key={f}  
              variant={filter === f ? "default" : "secondary"}
              className="cursor-pointer"
              onClick={() => setFilter(f)}
            >
              {f}
            </Badge>
          ))}
        </div>
      </div>
      <ScrollArea className="flex-1 p-4">
        <div className="space-y-4">
          {filteredEvents.map((event) => {
            const Icon = EVENT_ICONS[event.event_type] || Play;
            return (
              <Card key={event.event_id} className="p-4 flex space-x-4 bg-secondary/30">
                <div className="mt-1">
                  <Icon className="w-5 h-5 text-muted-foreground" />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex justify-between items-center">
                    <span className="font-medium truncate">{event.event_type}</span>
                    <span className="text-xs text-muted-foreground shrink-0">
                      {format(new Date(event.timestamp), "hh:mm:ss a")}
                    </span>
                  </div>
                  {event.tool && <p className="text-sm text-muted-foreground mt-1">Tool: {event.tool}</p>}
                  {event.path && <p className="text-sm text-muted-foreground mt-1">Path: {event.path}</p>}
                  {event.details && (
                    <pre className="mt-2 text-xs bg-black/50 p-2 rounded overflow-x-auto text-green-400">
                      {JSON.stringify(event.details, null, 2)}
                    </pre>
                  )}
                </div>
              </Card>
            );
          })}
          {filteredEvents.length === 0 && (
            <div className="text-center text-muted-foreground mt-10">Waiting for execution events...</div>
          )}
        </div>
      </ScrollArea>
    </div>
  );
}
