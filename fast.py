import json
from pathlib import Path
import time
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from helpers import fetch_historical_candles, get_historical_ema_crossovers, check_ema_crossover_signal

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Set specific origins for production!
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

WATCHLIST_FILE = Path("watchlist.json")

def load_watchlist():
    if not WATCHLIST_FILE.exists():
        return []
    with open(WATCHLIST_FILE, "r") as f:
        data = json.load(f)
    # If it's already a list, just return it
    if isinstance(data, list):
        return data
    # fallback for dict structure
    return data.get("symbols", []) if isinstance(data, dict) else []


@app.get("/screener_data")
def screener_data():
    symbols = load_watchlist()
    response = {"crypto": [], "forex": [], "stocks": []}
    timeframes = ["15m", "1h", "4h", "1d"]

    for symbol in symbols:
        timeframes_signals = {}
        for tf in timeframes:
            df = fetch_historical_candles(symbol, tf)
            if df.empty:
                timeframes_signals[tf] = {"status": "N/A", "bars_since": None}
                continue
            signal = check_ema_crossover_signal(df)
            if signal == "BUY":
                status = "Bullish"
            elif signal == "SELL":
                status = "Bearish"
            else:
                status = "Neutral"
            bars_since = 0 if status in ["Bullish", "Bearish"] else None
            timeframes_signals[tf] = {"status": status, "bars_since": bars_since}

        symbol_data = {"name": symbol, "timeframes": timeframes_signals}
        # Append all to crypto for now; enhance to categorize properly
        response["crypto"].append(symbol_data)

    return response

@app.get("/historical-crossovers")
def historical_crossovers(symbol: str = Query(...), timeframe: str = Query(...)):
    now = int(time.time())
    start = 1  
    df = fetch_historical_candles(symbol, timeframe)
    if df.empty:
        return {"crossovers": []}
    crossovers = get_historical_ema_crossovers(df)
    return {"crossovers": crossovers}

@app.get("/latest-signal")
def latest_signal(symbol: str = Query(...), timeframe: str = Query(...)):
    now = int(time.time())
    start = now - 7 * 24 * 60 * 60
    df = fetch_historical_candles(symbol, timeframe)
    if df.empty:
        return {"signal": None}
    signal = check_ema_crossover_signal(df)
    return {"signal": signal}
