import { io, Socket } from "socket.io-client";

// Connect to the backend
export const socket: Socket = io("http://127.0.0.1:8000", {
  autoConnect: false, // We will explicitly control connections
});
