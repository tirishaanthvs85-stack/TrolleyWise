from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from backend.app.services.websocket_manager import ws_manager

router = APIRouter()

@router.websocket("/live/{channel_id}")
async def websocket_endpoint(websocket: WebSocket, channel_id: str):
    await ws_manager.connect(websocket, channel_id)
    try:
        while True:
            data = await websocket.receive_text()
            # Echo ping / pong
            if data == "ping":
                await websocket.send_text('{"type":"pong"}')
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket, channel_id)
