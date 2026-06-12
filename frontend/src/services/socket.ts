import { io, Socket } from "socket.io-client";
import { API_BASE_URL } from '../config';

// Connect to the backend
export const socket: Socket = io(API_BASE_URL, {
  autoConnect: false, // We will explicitly control connections
  transports: ["websocket"],
});
