from fastapi import FastAPI
import socketio
from app.websockets.socket_app import sio
from app.api.routes import router as api_router

from fastapi.middleware.cors import CORSMiddleware

fastapi_app = FastAPI(
    title="PRERAK 2.0 Backend",
    description="Agentic coding AI Assistant Backend",
    version="2.0.0"
)

fastapi_app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins for development
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods (GET, POST, OPTIONS, etc.)
    allow_headers=["*"],  # Allows all headers
)

# Include standard HTTP API routes
fastapi_app.include_router(api_router, prefix="/api")

@fastapi_app.get("/")
async def root():
    return {"message": "PRERAK 2.0 Backend is running"}

# Wrap the FastAPI app with the Socket.IO ASGI app.
# This ensures /socket.io/ traffic goes to socketio, and everything else goes to FastAPI.
app = socketio.ASGIApp(sio, other_asgi_app=fastapi_app)
