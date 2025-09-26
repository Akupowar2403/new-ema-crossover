import asyncio
from fastapi import FastAPI, Query, WebSocket, WebSocketDisconnect,HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
from contextlib import asynccontextmanager
import time
import helpers
import websocket_manager
from shared_state import candle_managers_state, websocket_command_queue
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from telegram_bot import TelegramBotApp
import shared_state
import os

# --- .env Configuration Loading ---
from dotenv import load_dotenv
load_dotenv()

TIMEFRAMES_STR = os.getenv('TIMEFRAMES', '1m,15m,1h,4h,1d')
TIMEFRAMES = [tf.strip() for tf in TIMEFRAMES_STR.split(',')]
# ----------------------------------

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

API_CONCURRENCY_LIMIT = 5
semaphore = asyncio.Semaphore(API_CONCURRENCY_LIMIT)

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Server startup: Initializing services...")

    bot_app = TelegramBotApp()
    if bot_app.app:
        shared_state.alert_service = bot_app.alert_service
        telegram_task = asyncio.create_task(bot_app.run_in_background())

    websocket_task = asyncio.create_task(websocket_manager.start_websocket_client(manager, semaphore))
    
    yield
    
    print("Server shutdown: Stopping background tasks...")
    websocket_task.cancel()
    if bot_app.app and 'telegram_task' in locals():
        telegram_task.cancel()

app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:5500", "http://localhost:5500"], 
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["*"],
)

class SymbolRequest(BaseModel):
    symbol: str

class ScreenerRequest(BaseModel):
    symbols: Optional[List[str]] = None

app.mount("/static", StaticFiles(directory="frontend"), name="static")


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text() 
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
        for tf in TIMEFRAMES:
            manager_instance = candle_managers_state.get((symbol, tf))
            
            if manager_instance and manager_instance.last_signal_state:
                timeframe_signals[tf] = manager_instance.last_signal_state
            else:
                timeframe_signals[tf] = {
                    "trend": "Loading...", "bars_since_confirmed": None,
                    "live_status": "N/A", "live_crossover_detected": None
                }
        response_data.append({"name": symbol, "timeframes": timeframe_signals})
    print("--- DATA BEING SENT TO FRONTEND ---", response_data)     
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
    """
    Validates the symbol against the master list before adding it to the watchlist.
    """
    all_symbols = await helpers.get_all_symbols_cached()

    if request.symbol not in all_symbols:
        raise HTTPException(status_code=400, detail=f"Symbol '{request.symbol}' is not a valid symbol.")
    
    updated_watchlist = helpers.add_symbol_to_watchlist(request.symbol)
    await websocket_command_queue.put(('subscribe', request.symbol))
    return {"status": "success", "watchlist": updated_watchlist}

@app.delete("/watchlist/{symbol_name}")
async def delete_from_watchlist(symbol_name: str):
    """Removes a symbol from the file and sends an 'unsubscribe' command."""
    updated_watchlist = helpers.remove_symbol_from_watchlist(symbol_name)
    await websocket_command_queue.put(('unsubscribe', symbol_name))
    return {"status": "success", "watchlist": updated_watchlist}

@app.get("/latest-signal")
async def latest_signal(symbol: str = Query(...), timeframe: str = Query(...)):
    manager_instance = candle_managers_state.get((symbol, timeframe))
    if manager_instance and manager_instance.last_signal_state:
        return {"signal": manager_instance.last_signal_state}
    
    now = int(time.time())
    df = await helpers.fetch_historical_candles(symbol, timeframe, 1, now, semaphore)
    if df.empty:
        return {"signal": None}
    
    signal = helpers.analyze_ema_state(df)
    return {"signal": signal}

@app.get("/historical-crossovers")
async def historical_crossovers(
    symbol: str = Query(...), 
    timeframe: str = Query(...),
    confirmation: int = Query(1, ge=0)
):
    """
    A "smart" endpoint that finds the 10 most recent confirmed crossovers.
    It prioritizes live, in-memory data for accuracy and speed.
    """
    df = None
    
    manager_instance = candle_managers_state.get((symbol, timeframe))
    if manager_instance and not manager_instance.candles_df.empty:
        helpers.logger.info(f"Using LIVE data for {symbol}-{timeframe} crossover check.")
        df = manager_instance.candles_df

    else:
        helpers.logger.info(f"Fetching HISTORICAL data for {symbol}-{timeframe} crossover check.")
        now = int(time.time())
        df = await helpers.fetch_historical_candles(symbol, timeframe, 1, now, semaphore)

    if df is None or df.empty:
        return {"crossovers": []}

    all_crossovers = helpers.find_all_crossovers(df, confirmation_periods=confirmation)
    
    recent_crossovers = all_crossovers[-10:]
    
    return {"crossovers": recent_crossovers}

@app.get("/")
async def read_index():
    return FileResponse('frontend/index.html')