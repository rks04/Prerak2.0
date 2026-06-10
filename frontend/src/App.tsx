import { BrowserRouter as Router, Routes, Route } from "react-router-dom";
import { ChatPage } from "@/pages/ChatPage";
import { WorkspaceSelector } from "@/pages/WorkspaceSelector";

function App() {
  return (
    <Router>
      <Routes>
        <Route path="/" element={<WorkspaceSelector />} />
        <Route path="/code/:workspaceId/:conversationId" element={<ChatPage />} />
      </Routes>
    </Router>
  );
}

export default App;
