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

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
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
    # Use the provided symbols, otherwise fall back to the watchlist file
    symbols_to_scan = request.symbols if request.symbols is not None else load_watchlist()
    
    now = int(time.time())
    warmup_bars = (config.LONG_EMA_PERIOD * config.WARMUP_BARS_FACTOR) + config.WARMUP_BARS_BUFFER

    tasks, task_metadata = [], []
    for symbol in symbols_to_scan:
        for tf in config.TIMEFRAMES:
            bar_seconds = config.SECONDS_PER_BAR.get(tf, 3600)
            start_time = now - (warmup_bars * bar_seconds)
            task = helpers.fetch_historical_candles(symbol, tf, start=start_time, end=now)
            tasks.append(task)
            task_metadata.append({"symbol": symbol, "tf": tf})

    results = await asyncio.gather(*tasks, return_exceptions=True)

    symbol_results = {symbol: {} for symbol in symbols_to_scan}
    for i, res_df in enumerate(results):
        meta = task_metadata[i]
        symbol, tf = meta["symbol"], meta["tf"]
        status, bars_since = "N/A", None

        if not isinstance(res_df, Exception) and not res_df.empty:
            signal = helpers.check_ema_crossover_signal(
                df=res_df,
                short_period=config.SHORT_EMA_PERIOD,
                long_period=config.LONG_EMA_PERIOD
            )
            bars_since = helpers.get_bars_since_last_signal(res_df)
            status = "Bullish" if signal == "BUY" else "Bearish" if signal == "SELL" else "Neutral"
        
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
    warmup_bars = (config.LONG_EMA_PERIOD * config.WARMUP_BARS_FACTOR) + config.WARMUP_BARS_BUFFER
    bar_seconds = config.SECONDS_PER_BAR.get(timeframe, 3600)
    start_time = now - (warmup_bars * bar_seconds)
    
    # We must 'await' the result of an async function
    df = await helpers.fetch_historical_candles(symbol, timeframe, start=start_time, end=now)
    
    if df.empty:
        return {"crossovers": []}

    crossovers = helpers.get_historical_ema_crossovers(
        df, 
        symbol=symbol, 
        timeframe=timeframe,
        short_period=config.SHORT_EMA_PERIOD,
        long_period=config.LONG_EMA_PERIOD,
        volume_threshold_factor=config.VOLUME_THRESHOLD_FACTOR,
        cooldown_minutes=config.COOLDOWN_MINUTES
    )
    return {"crossovers": crossovers}

# --- FIX APPLIED HERE ---
@app.get("/latest-signal")
async def latest_signal(symbol: str = Query(...), timeframe: str = Query(...)):
    now = int(time.time())
    warmup_bars = (config.LONG_EMA_PERIOD * config.WARMUP_BARS_FACTOR) + config.WARMUP_BARS_BUFFER
    bar_seconds = config.SECONDS_PER_BAR.get(timeframe, 3600)
    start_time = now - (warmup_bars * bar_seconds)
    
    # We must 'await' the result of an async function
    df = await helpers.fetch_historical_candles(symbol, timeframe, start=start_time, end=now)

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
