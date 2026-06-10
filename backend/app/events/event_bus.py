import asyncio
from typing import List, Protocol
from app.events.schema import PrerakEvent

class EventSubscriber(Protocol):
    async def handle_event(self, event: PrerakEvent) -> None:
        pass

class EventBus:
    """Decoupled event broker routing PrerakEvents to multiple independent subscribers."""
    def __init__(self):
        self._subscribers: List[EventSubscriber] = []
        
    def subscribe(self, subscriber: EventSubscriber):
        self._subscribers.append(subscriber)
        
    async def publish(self, event: PrerakEvent):
        # Fire and forget / gather to process asynchronously
        tasks = [sub.handle_event(event) for sub in self._subscribers]
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

event_bus = EventBus()

# Initialize subscribers
from app.events.subscribers.file_logger_subscriber import FileLoggerSubscriber
from app.events.subscribers.websocket_subscriber import WebsocketSubscriber

event_bus.subscribe(FileLoggerSubscriber())
event_bus.subscribe(WebsocketSubscriber())
