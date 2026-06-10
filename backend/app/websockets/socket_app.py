import socketio

# Create a Socket.IO server
# async_mode='asgi' is needed for integration with FastAPI
sio = socketio.AsyncServer(async_mode='asgi', cors_allowed_origins='*')

# The ASGI application to mount onto FastAPI
socket_app = socketio.ASGIApp(sio)

@sio.event
async def connect(sid, environ):
    print(f"Client connected: {sid}")

@sio.event
async def disconnect(sid):
    print(f"Client disconnected: {sid}")

@sio.on("ping")
async def ping(sid, data):
    await sio.emit("pong", {"message": "pong"}, room=sid)

@sio.on("join_room")
async def join_room(sid, data):
    room = data.get("room")
    if room:
        await sio.enter_room(sid, room)
        print(f"Client {sid} joined room: {room}")
        await sio.emit("room_joined", {"room": room}, room=sid)
