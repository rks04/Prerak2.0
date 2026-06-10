import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { useState } from "react";
import { useSocketStore } from "@/stores/socketStore";
import { Send } from "lucide-react";

export function PromptInput({ onSend }: { onSend: (val: string) => void }) {
  const [val, setVal] = useState("");
  const isConnected = useSocketStore(state => state.isConnected);

  return (
    <div className="p-4 border-t border-border bg-card flex space-x-2">
      <Input 
        value={val} 
        onChange={(e) => setVal(e.target.value)} 
        placeholder="E.g., Create hello.py with Hello World..."
        onKeyDown={(e) => { if (e.key === 'Enter') { onSend(val); setVal(""); } }}
      />
      <Button disabled={!isConnected || !val.trim()} onClick={() => { onSend(val); setVal(""); }}>
        <Send className="w-4 h-4 mr-2" /> Execute
      </Button>
    </div>
  );
}
