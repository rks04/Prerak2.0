from fastapi import FastAPI
import socketio
from contextlib import asynccontextmanager
from app.websockets.socket_app import sio
from app.api.routes import router as api_router
from app.api.workspace_routes import router as workspace_router
from app.db.database import check_db_connection
from fastapi.middleware.cors import CORSMiddleware

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    db_ok = await check_db_connection()
    if not db_ok:
        print("WARNING: Database connection failed. DB-dependent features are disabled.")
    else:
        print("Database connected successfully.")
    yield
    # Shutdown logic can go here

fastapi_app = FastAPI(
    title="PRERAK 2.0 Backend",
    description="Agentic coding AI Assistant Backend",
    version="2.0.0",
    lifespan=lifespan
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
fastapi_app.include_router(workspace_router, prefix="/api/workspace")

from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os

@fastapi_app.get("/api/health")
async def root():
    return {"message": "PRERAK 2.0 Backend is running"}

# Serve Frontend static files
frontend_dist = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "frontend", "dist")

if os.path.exists(frontend_dist):
    # Mount assets folder explicitly so it doesn't get intercepted by catch-all
    assets_dir = os.path.join(frontend_dist, "assets")
    if os.path.exists(assets_dir):
        fastapi_app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")
        
    @fastapi_app.get("/{full_path:path}")
    async def serve_frontend(full_path: str):
        # Allow API and socket.io to pass through
        if full_path.startswith("api/") or full_path.startswith("socket.io/"):
            return
            
        file_path = os.path.join(frontend_dist, full_path)
        if os.path.exists(file_path) and os.path.isfile(file_path):
            return FileResponse(file_path)
            
        # React Router fallback
        return FileResponse(os.path.join(frontend_dist, "index.html"))

# Wrap the FastAPI app with the Socket.IO ASGI app.
# This ensures /socket.io/ traffic goes to socketio, and everything else goes to FastAPI.
app = socketio.ASGIApp(sio, other_asgi_app=fastapi_app)
