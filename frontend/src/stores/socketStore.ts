import { create } from "zustand";
import { socket } from "@/services/socket";
import type { PrerakEvent } from "@/types/events";

interface SocketState {
  isConnected: boolean;
  events: PrerakEvent[];
  connect: () => void;
  disconnect: () => void;
  joinRoom: (conversationId: string) => void;
  clearEvents: () => void;
  setEvents: (events: PrerakEvent[]) => void;
}

export const useSocketStore = create<SocketState>((set) => {
  // Bind socket event listeners
  socket.on("connect", () => {
    set({ isConnected: true });
  });

  socket.on("disconnect", () => {
    set({ isConnected: false });
  });

  socket.on("execution_event", (event: PrerakEvent) => {
    set((state) => ({ events: [...state.events, event] }));
  });

  return {
    isConnected: false,
    events: [],
    connect: () => {
      if (!socket.connected) {
        socket.connect();
      }
    },
    disconnect: () => {
      if (socket.connected) {
        socket.disconnect();
      }
    },
    joinRoom: (conversationId: string) => {
      socket.emit("join_room", { room: `code:${conversationId}` });
    },
    clearEvents: () => set({ events: [] }),
    setEvents: (events) => set({ events }),
  };
});
