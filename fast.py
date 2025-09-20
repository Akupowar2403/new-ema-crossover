import json
import time
import asyncio
from pathlib import Path
from fastapi import FastAPI, Query ,WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
from contextlib import asynccontextmanager

import helpers
import config
import websocket_manager

class SymbolRequest(BaseModel):
    symbol: str

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

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Server startup: Starting WebSocket client...")
    # Pass both the manager and the semaphore to the background task
    task = asyncio.create_task(websocket_manager.start_websocket_client(manager, semaphore))
    yield
    print("Server shutdown: Stopping WebSocket client...")
    task.cancel()

app = FastAPI(lifespan=lifespan)

origins = [
    "http://127.0.0.1:5500",
    "http://localhost:5500",
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE"], # <-- Corrected argument name
    allow_headers=["*"],
)

class ScreenerRequest(BaseModel):
    symbols: Optional[List[str]] = None

# This semaphore will allow a maximum of 5 requests to run at the same time.
API_CONCURRENCY_LIMIT = 5
semaphore = asyncio.Semaphore(API_CONCURRENCY_LIMIT)

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)

@app.post("/screener_data")
async def screener_data(request: ScreenerRequest):
    # Use the helper function to get the watchlist for consistency
    symbols_to_scan = request.symbols if request.symbols is not None else helpers.get_current_watchlist()
    now = int(time.time())
    start_time = 1

    tasks, task_metadata = [], []
    for symbol in symbols_to_scan:
        for tf in config.TIMEFRAMES:
            # Pass the semaphore to the helper function for rate limiting
            task = helpers.fetch_historical_candles(symbol, tf, start_time, now, semaphore)
            tasks.append(task)
            task_metadata.append({"symbol": symbol, "tf": tf})

    results = await asyncio.gather(*tasks, return_exceptions=True)

    symbol_results = {symbol: {} for symbol in symbols_to_scan}
    for i, res_df in enumerate(results):
        meta = task_metadata[i]
        symbol, tf = meta["symbol"], meta["tf"]
        
        signal_data = {"status": "N/A", "bars_since": None}

        if not isinstance(res_df, Exception) and not res_df.empty:
            signal_data = helpers.get_ema_signal(res_df, {})
        
        symbol_results[symbol][tf] = signal_data

    response_data = [
        {"name": symbol, "timeframes": tf_signals}
        for symbol, tf_signals in symbol_results.items()
    ]
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
    updated_watchlist = helpers.add_symbol_to_watchlist(request.symbol)
    return {"status": "success", "watchlist": updated_watchlist}

@app.delete("/watchlist/{symbol_name}")
async def delete_from_watchlist(symbol_name: str):
    updated_watchlist = helpers.remove_symbol_from_watchlist(symbol_name)
    return {"status": "success", "watchlist": updated_watchlist}

@app.get("/historical-crossovers")
async def historical_crossovers(symbol: str = Query(...), timeframe: str = Query(...)):
    now = int(time.time())
    start_time = 1
    
    # --- UPDATE IS HERE: Pass the semaphore ---
    df = await helpers.fetch_historical_candles(symbol, timeframe, start_time, now, semaphore)
    
    if df.empty:
        return {"crossovers": []}

    crossovers = helpers.get_historical_ema_crossovers(df, symbol, timeframe)
    return {"crossovers": crossovers}

@app.get("/latest-signal")
async def latest_signal(symbol: str = Query(...), timeframe: str = Query(...)):
    now = int(time.time())
    start_time = 1
    
    # --- UPDATE IS HERE: Pass the semaphore ---
    df = await helpers.fetch_historical_candles(symbol, timeframe, start_time, now, semaphore)

    if df.empty:
        return {"signal": None}

    signal = helpers.get_ema_signal(df, {})
    return {"signal": signal}