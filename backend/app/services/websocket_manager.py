"""
TrolleyWise Real-Time WebSocket Manager
Broadcasts live cart events, verification states, and billing recalculations
to the customer touchscreen and retailer monitoring dashboard without manual refresh.
"""

import json
from typing import Dict, List
from fastapi import WebSocket

class WebSocketConnectionManager:
    def __init__(self):
        # Maps session_id (or "retailer") to list of active WebSockets
        self.active_connections: Dict[str, List[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, channel_id: str):
        await websocket.accept()
        if channel_id not in self.active_connections:
            self.active_connections[channel_id] = []
        self.active_connections[channel_id].append(websocket)
        print(f"[WebSocket] Client connected to channel: {channel_id}")

    def disconnect(self, websocket: WebSocket, channel_id: str):
        if channel_id in self.active_connections:
            if websocket in self.active_connections[channel_id]:
                self.active_connections[channel_id].remove(websocket)
            if not self.active_connections[channel_id]:
                del self.active_connections[channel_id]
        print(f"[WebSocket] Client disconnected from channel: {channel_id}")

    async def broadcast_to_channel(self, channel_id: str, message: dict):
        if channel_id in self.active_connections:
            payload = json.dumps(message)
            dead_sockets = []
            for connection in self.active_connections[channel_id]:
                try:
                    await connection.send_text(payload)
                except Exception:
                    dead_sockets.append(connection)
            for dead in dead_sockets:
                self.disconnect(dead, channel_id)

    async def broadcast_all(self, message: dict):
        for channel_id in list(self.active_connections.keys()):
            await self.broadcast_to_channel(channel_id, message)

# Global singleton
ws_manager = WebSocketConnectionManager()
