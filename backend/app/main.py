import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, RedirectResponse

from backend.app.core.config import settings
from backend.app.core.database import engine, Base
from backend.app.db.seed_data import seed_database
from backend.app.api.router import api_router
from backend.app.services.websocket_manager import ws_manager

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Ensure DB schema & seed
    Base.metadata.create_all(bind=engine)
    seed_database()
    os.makedirs(settings.RECEIPT_OUTPUT_DIR, exist_ok=True)
    yield
    # Shutdown logic if any

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="AI-Powered Smart Shopping Cart with Multimodal Product Verification, Automated Billing and Anomaly Detection.",
    lifespan=lifespan
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API Router
app.include_router(api_router, prefix=settings.API_V1_STR)

# Direct WS endpoint for convenience
@app.websocket("/ws/live/{channel_id}")
async def direct_ws_endpoint(websocket: WebSocket, channel_id: str):
    await ws_manager.connect(websocket, channel_id)
    try:
        while True:
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text('{"type":"pong"}')
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket, channel_id)

# Mount Static UI directories
TOUCHSCREEN_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "frontend", "customer_touchscreen")
RETAILER_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "frontend", "retailer_dashboard")

if os.path.exists(TOUCHSCREEN_DIR):
    app.mount("/touchscreen-assets", StaticFiles(directory=TOUCHSCREEN_DIR), name="touchscreen-assets")
if os.path.exists(RETAILER_DIR):
    app.mount("/retailer-assets", StaticFiles(directory=RETAILER_DIR), name="retailer-assets")

@app.get("/", response_class=HTMLResponse)
def index():
    touchscreen_path = os.path.join(TOUCHSCREEN_DIR, "index.html")
    if os.path.exists(touchscreen_path):
        with open(touchscreen_path, "r", encoding="utf-8") as f:
            return f.read()
    return f"""
    <html>
        <head><title>{settings.PROJECT_NAME}</title></head>
        <body style="font-family:sans-serif; padding:40px; background:#0F172A; color:#F8FAFC;">
            <h1>🛒 {settings.PROJECT_NAME} v{settings.VERSION}</h1>
            <p>Multimodal Sensor Fusion & Automatic Billing Backend is Active.</p>
            <ul>
                <li><a style="color:#38BDF8;" href="/docs">Interactive API Documentation (Swagger)</a></li>
                <li><a style="color:#38BDF8;" href="/touchscreen">Customer Touchscreen Interface</a></li>
                <li><a style="color:#38BDF8;" href="/retailer">Retailer Monitoring Dashboard</a></li>
            </ul>
        </body>
    </html>
    """

@app.get("/touchscreen", response_class=HTMLResponse)
def customer_touchscreen():
    touchscreen_path = os.path.join(TOUCHSCREEN_DIR, "index.html")
    if os.path.exists(touchscreen_path):
        with open(touchscreen_path, "r", encoding="utf-8") as f:
            return f.read()
    return "<h1>Customer Touchscreen interface building...</h1>"

@app.get("/retailer", response_class=HTMLResponse)
def retailer_dashboard():
    retailer_path = os.path.join(RETAILER_DIR, "index.html")
    if os.path.exists(retailer_path):
        with open(retailer_path, "r", encoding="utf-8") as f:
            return f.read()
    return "<h1>Retailer Dashboard interface building...</h1>"
