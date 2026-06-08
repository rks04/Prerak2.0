from app.events.schema import PrerakEvent
from app.websockets.socket_app import sio

class WebsocketSubscriber:
    """Streams structured events to room-isolated websocket clients."""
    async def handle_event(self, event: PrerakEvent):
        room = f"code:{event.conversation_id}"
        await sio.emit("execution_event", event.model_dump(), room=room)
