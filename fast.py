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
    if isinstance(data, list):
        return data
    return data.get("symbols", []) if isinstance(data, dict) else []

@app.get("/screener_data")
def screener_data():
    symbols = load_watchlist()
    response = {"crypto": [], "forex": [], "stocks": []}
    timeframes = ["15m", "1h", "4h", "1d"]

    now = int(time.time())
    longest_period = 20
    warmup_bars = longest_period * 3 + 2  # 62 bars
    seconds_per_bar = {
        "15m": 15 * 60,
        "1h": 60 * 60,
        "4h": 4 * 60 * 60,
        "1d": 24 * 60 * 60
    }

    for symbol in symbols:
        timeframes_signals = {}
        for tf in timeframes:
            bar_seconds = seconds_per_bar.get(tf, 60 * 60)
            start_time = now - warmup_bars * bar_seconds
            end_time = now

            df = fetch_historical_candles(symbol, tf, start=start_time, end=end_time)
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
        response["crypto"].append(symbol_data)

    return response

@app.get("/historical-crossovers")
def historical_crossovers(symbol: str = Query(...), timeframe: str = Query(...)):
    now = int(time.time())
    longest_period = 20
    warmup_bars = longest_period * 3 + 2
    seconds_per_bar = {
        "15m": 15 * 60,
        "1h": 60 * 60,
        "4h": 4 * 60 * 60,
        "1d": 24 * 60 * 60
    }
    bar_seconds = seconds_per_bar.get(timeframe, 60 * 60)
    start = now - warmup_bars * bar_seconds
    end = now

    df = fetch_historical_candles(symbol, timeframe, start=start, end=end)
    if df.empty:
        return {"crossovers": []}

    crossovers = get_historical_ema_crossovers(df, symbol=symbol, timeframe=timeframe)
    return {"crossovers": crossovers}

@app.get("/latest-signal")
def latest_signal(symbol: str = Query(...), timeframe: str = Query(...)):
    now = int(time.time())
    longest_period = 20
    warmup_bars = longest_period * 3 + 2
    seconds_per_bar = {
        "15m": 15 * 60,
        "1h": 60 * 60,
        "4h": 4 * 60 * 60,
        "1d": 24 * 60 * 60
    }
    bar_seconds = seconds_per_bar.get(timeframe, 60 * 60)
    start = now - warmup_bars * bar_seconds
    end = now

    df = fetch_historical_candles(symbol, timeframe, start=start, end=end)
    if df.empty:
        return {"signal": None}

    signal = check_ema_crossover_signal(df)
    return {"signal": signal}
