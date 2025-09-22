# fast.py
import asyncio
from fastapi import FastAPI, Query, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
from contextlib import asynccontextmanager
import time
import helpers
import config
import websocket_manager
# Import the shared state objects that connect the API to the live engine
from shared_state import candle_managers_state, websocket_command_queue

# --- Connection Manager for Frontend Clients ---
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)
    async def broadcast(self, message: str):
        for connection in self.active_connections:
            await connection.send_text(message)

manager = ConnectionManager()

# --- Concurrency Limiter ---
API_CONCURRENCY_LIMIT = 5
semaphore = asyncio.Semaphore(API_CONCURRENCY_LIMIT)

# --- App Lifespan (Starts/Stops Background Task) ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Server startup: Starting WebSocket client...")
    task = asyncio.create_task(websocket_manager.start_websocket_client(manager, semaphore))
    yield
    print("Server shutdown: Stopping WebSocket client...")
    task.cancel()

# --- FastAPI App Initialization ---
app = FastAPI(lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:5500", "http://localhost:5500"], # Add your frontend origin
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["*"],
)

# --- Pydantic Models ---
class SymbolRequest(BaseModel):
    symbol: str

class ScreenerRequest(BaseModel):
    symbols: Optional[List[str]] = None

# --- WebSocket Endpoint ---
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text() # Keep connection alive
    except WebSocketDisconnect:
        manager.disconnect(websocket)

# --- API Endpoints ---
@app.post("/screener_data")
async def screener_data(request: ScreenerRequest):
    """
    Instantly retrieves the latest signal data from the in-memory state.
    This endpoint is now extremely fast as it does not make any external API calls.
    """
    symbols_to_scan = request.symbols or helpers.get_current_watchlist()
    
    response_data = []
    for symbol in symbols_to_scan:
        timeframe_signals = {}
        for tf in config.TIMEFRAMES:
            # Look up the manager instance in our shared state
            manager_instance = candle_managers_state.get((symbol, tf))
            
            if manager_instance and manager_instance.last_signal_state:
                timeframe_signals[tf] = manager_instance.last_signal_state
            else:
                # Fallback if the data isn't loaded yet
                timeframe_signals[tf] = {
                    "trend": "Loading...", "bars_since_confirmed": None,
                    "live_status": "N/A", "live_crossover_detected": None
                }
        response_data.append({"name": symbol, "timeframes": timeframe_signals})
        
    return {"crypto": response_data}

@app.get("/all-symbols")
async def get_all_symbols():
    symbols = await helpers.get_all_symbols_cached()
    return {"symbols": symbols}

@app.get("/watchlist")
async def get_watchlist():
    return {"symbols": helpers.get_current_watchlist()}

@app.post("/watchlist")
async def add_to_watchlist(request: SymbolRequest):
    """Adds a symbol to the file and sends a 'subscribe' command to the live engine."""
    updated_watchlist = helpers.add_symbol_to_watchlist(request.symbol)
    # This command tells the background process to start listening to this symbol
    await websocket_command_queue.put(('subscribe', request.symbol))
    return {"status": "success", "watchlist": updated_watchlist}

@app.delete("/watchlist/{symbol_name}")
async def delete_from_watchlist(symbol_name: str):
    """Removes a symbol from the file and sends an 'unsubscribe' command."""
    updated_watchlist = helpers.remove_symbol_from_watchlist(symbol_name)
    # This command tells the background process to stop listening to this symbol
    await websocket_command_queue.put(('unsubscribe', symbol_name))
    return {"status": "success", "watchlist": updated_watchlist}

# This endpoint is also updated to use the new, more powerful analysis function
@app.get("/latest-signal")
async def latest_signal(symbol: str = Query(...), timeframe: str = Query(...)):
    manager_instance = candle_managers_state.get((symbol, timeframe))
    if manager_instance and manager_instance.last_signal_state:
        return {"signal": manager_instance.last_signal_state}
    
    # Fallback to fetch manually if not on watchlist (could be removed if not needed)
    now = int(time.time())
    df = await helpers.fetch_historical_candles(symbol, timeframe, 1, now, semaphore)
    if df.empty:
        return {"signal": None}
    
    signal = helpers.analyze_ema_state(df)
    return {"signal": signal}

@app.get("/historical-crossovers")
async def historical_crossovers(symbol: str = Query(...), timeframe: str = Query(...)):
    now = int(time.time())
    df = await helpers.fetch_historical_candles(symbol, timeframe, 1, now, semaphore)
    if df.empty: return {"crossovers": []}
    return {"crossovers": helpers.find_all_crossovers(df)}