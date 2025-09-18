import json
import time
import asyncio
from pathlib import Path
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional

# Import our helper functions and the new config file
import helpers
import config

class SymbolRequest(BaseModel):
    symbol: str

app = FastAPI()

# List of origins that are allowed to make requests to this server
origins = [
    "http://127.0.0.1:5500", # The default port for VS Code Live Server
    "http://localhost:5500",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins, # Use the specific list of allowed origins
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE"], # Be specific about allowed methods
    allow_headers=["*"],
)

WATCHLIST_FILE = Path("watchlist.json")

def load_watchlist():
    if not WATCHLIST_FILE.exists():
        return []
    with open(WATCHLIST_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
        if isinstance(data, list):
            return data
        else:
            return data.get("symbols", [])

class ScreenerRequest(BaseModel):
    symbols: Optional[List[str]] = None
    
@app.post("/screener_data")
async def screener_data(request: ScreenerRequest):
    symbols_to_scan = request.symbols if request.symbols is not None else load_watchlist()
    now = int(time.time())
    start_time = 1 # Fetch all available data

    tasks, task_metadata = [], []
    for symbol in symbols_to_scan:
        for tf in config.TIMEFRAMES:
            task = helpers.fetch_historical_candles(symbol, tf, start=start_time, end=now)
            tasks.append(task)
            task_metadata.append({"symbol": symbol, "tf": tf})

    results = await asyncio.gather(*tasks, return_exceptions=True)

    symbol_results = {symbol: {} for symbol in symbols_to_scan}
    for i, res_df in enumerate(results):
        meta = task_metadata[i]
        symbol, tf = meta["symbol"], meta["tf"]
        
        status, bars_since = "N/A", None

        # --- THIS IS THE UPDATED LOGIC ---
        if not isinstance(res_df, Exception) and not res_df.empty:
            # 1. Get the current state (Bullish, Bearish, etc.)
            status = helpers.check_ema_crossover_signal(
                df=res_df.copy(),
                short_period=config.SHORT_EMA_PERIOD,
                long_period=config.LONG_EMA_PERIOD
            )
            
            # 2. If the state is not Neutral, get the bars since the last event
            if status not in ["Neutral", "N/A"]:
                bars_since = helpers.get_bars_since_last_signal(
                    df=res_df.copy(),
                    short_period=config.SHORT_EMA_PERIOD,
                    long_period=config.LONG_EMA_PERIOD
                )
        
        symbol_results[symbol][tf] = {"status": status, "bars_since": bars_since}

    response_data = [
        {"name": symbol, "timeframes": tf_signals}
        for symbol, tf_signals in symbol_results.items()
    ]
    return {"crypto": response_data}

# --- FIX APPLIED HERE ---
@app.get("/historical-crossovers")
async def historical_crossovers(symbol: str = Query(...), timeframe: str = Query(...)):
    now = int(time.time())
    start_time = 1 # Fetch all available data
    
    df = await helpers.fetch_historical_candles(symbol, timeframe, start=start_time, end=now)
    
    if df.empty:
        return {"crossovers": []}

    # The outdated 'volume_threshold_factor' argument has been removed from this call
    crossovers = helpers.get_historical_ema_crossovers(
        df, 
        symbol=symbol, 
        timeframe=timeframe,
        short_period=config.SHORT_EMA_PERIOD,
        long_period=config.LONG_EMA_PERIOD,
        cooldown_minutes=config.COOLDOWN_MINUTES
    )
    return {"crossovers": crossovers}

# --- FIX APPLIED HERE ---
@app.get("/latest-signal")
async def latest_signal(symbol: str = Query(...), timeframe: str = Query(...)):
    now = int(time.time())
    start_time = 1 # Fetch all available data
    
    df = await helpers.fetch_historical_candles(symbol, timeframe, start=start_time, end=now)
    # ... rest of function is the same

    if df.empty:
        return {"signal": None}

    signal = helpers.check_ema_crossover_signal(df, short_period=config.SHORT_EMA_PERIOD, long_period=config.LONG_EMA_PERIOD)
    return {"signal": signal}

@app.get("/all-symbols")
async def get_all_symbols():
    """
    Returns a cached list of all available symbols from the exchange,
    for use in frontend autocomplete features.
    """
    symbols = await helpers.get_all_symbols_cached()
    return {"symbols": symbols}

# --- Watchlist Management Endpoints ---

@app.get("/watchlist")
async def get_watchlist():
    """Gets the current user watchlist."""
    return {"symbols": helpers.get_current_watchlist()}

@app.post("/watchlist")
async def add_to_watchlist(request: SymbolRequest):
    """Adds a symbol to the watchlist."""
    updated_watchlist = helpers.add_symbol_to_watchlist(request.symbol)
    return {"status": "success", "watchlist": updated_watchlist}

@app.delete("/watchlist/{symbol_name}")
async def delete_from_watchlist(symbol_name: str):
    """Deletes a symbol from the watchlist."""
    updated_watchlist = helpers.remove_symbol_from_watchlist(symbol_name)
    return {"status": "success", "watchlist": updated_watchlist}
