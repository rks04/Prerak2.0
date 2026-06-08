import socketio
import sys

sio = socketio.Client()
conversation_id = "test_convo"

@sio.event
def connect():
    print(f"Connected to server. Joining room code:{conversation_id}...")
    sio.emit("join_room", {"room": f"code:{conversation_id}"})

@sio.event
def disconnect():
    print("Disconnected from server.")

@sio.on("room_joined")
def on_room_joined(data):
    print(f"Successfully joined room: {data['room']}")
    print("Listening for execution events...\n")

@sio.on("execution_event")
def on_execution_event(data):
    event_type = data.get('event_type')
    success = data.get('success')
    print(f"[EVENT STREAM] {event_type} | Success: {success}")

if __name__ == '__main__':
    try:
        sio.connect('http://localhost:8000')
        sio.wait()
    except Exception as e:
        print(f"Connection failed: {e}")
        sys.exit(1)
