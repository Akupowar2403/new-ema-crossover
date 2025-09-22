# helpers.py
import time
import httpx
import pandas as pd
import logging
from datetime import datetime
import redis
import json
import config
from pathlib import Path
import asyncio

WATCHLIST_FILE = Path("watchlist.json")

# --- Basic Setup ---
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- Redis Connection ---
try:
    redis_client = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
    redis_client.ping()
    logger.info("Successfully connected to Redis.")
except redis.exceptions.ConnectionError as e:
    logger.critical(f"Could not connect to Redis. Caching will be disabled. Error: {e}")
    redis_client = None

# --- Reusable HTTP Client ---
client = httpx.AsyncClient()


# --- Core Data and Signal Logic ---

async def fetch_historical_candles(symbol: str, resolution: str, start: int, end: int, semaphore: asyncio.Semaphore) -> pd.DataFrame:
    """Fetches and cleans historical candles asynchronously, respecting a concurrency limit."""
    url = 'https://api.india.delta.exchange/v2/history/candles'
    params = {'symbol': symbol, 'resolution': resolution, 'start': start, 'end': end}
    headers = {'Accept': 'application/json'}

    async with semaphore:
        try:
            response = await client.get(url, params=params, headers=headers, timeout=30.0)
            response.raise_for_status()
            data = response.json().get('result', [])
            await asyncio.sleep(0.1)
        except (httpx.HTTPStatusError, httpx.RequestError) as exc:
            logger.error(f"Error fetching candles for {symbol} {resolution}: {exc}")
            return pd.DataFrame()

    if not data:
        return pd.DataFrame()

    df = pd.DataFrame(data, columns=['time', 'open', 'high', 'low', 'close', 'volume'])
    df.set_index('time', inplace=True)
    df.index = pd.to_datetime(df.index, unit='s').tz_localize('UTC') # Set timezone to UTC

    price_cols = ['open', 'high', 'low', 'close']
    df = df[df['volume'] > 0]
    df = df[(df[price_cols] > 0).all(axis=1)]

    for col in price_cols:
        if not df.empty:
            median = df[col].median()
            mad = (df[col] - median).abs().median()
            if mad > 0:
                df = df[(df[col] - median).abs() < (10 * mad)]
    
    return df

def analyze_ema_state(df: pd.DataFrame) -> dict:
    """
    Analyzes candle data for both confirmed and live EMA crossover states.

    Returns a dictionary with:
    - trend: The trend ('Bullish'/'Bearish') from the last *confirmed* crossover.
    - bars_since_confirmed: How many closed bars have passed since that crossover.
    - live_status: The current relationship of the EMAs ('Short > Long' or 'Short < Long').
    - live_crossover_detected: The type of crossover happening on the live candle ('Bullish', 'Bearish', or None).
    """
    analysis = {
        "trend": "N/A",
        "bars_since_confirmed": None,
        "live_status": "N/A",
        "live_crossover_detected": None
    }

    if len(df) < config.LONG_EMA_PERIOD + 2:
        return analysis

    df = df.copy()
    df['ema_short'] = df['close'].ewm(span=config.SHORT_EMA_PERIOD, adjust=False).mean()
    df['ema_long'] = df['close'].ewm(span=config.LONG_EMA_PERIOD, adjust=False).mean()

    # --- 1. Find the Last Confirmed Crossover (scans historical closed candles) ---
    confirmed_crossover_index = None
    # We iterate backwards from the second-to-last candle (the last *closed* one)
    for i in range(len(df) - 2, 0, -1):
        prev_s, curr_s = df['ema_short'].iloc[i - 1], df['ema_short'].iloc[i]
        prev_l, curr_l = df['ema_long'].iloc[i - 1], df['ema_long'].iloc[i]
        
        if prev_s <= prev_l and curr_s > curr_l:
            analysis["trend"] = 'Bullish'
            confirmed_crossover_index = i
            break
        elif prev_s >= prev_l and curr_s < curr_l:
            analysis["trend"] = 'Bearish'
            confirmed_crossover_index = i
            break

    if confirmed_crossover_index is not None:
        # Calculate bars since: (index of last closed candle) - (index of crossover candle)
        analysis["bars_since_confirmed"] = (len(df) - 2) - confirmed_crossover_index

    # --- 2. Analyze the Live Candle State ---
    last_closed_short = df['ema_short'].iloc[-2]
    live_short = df['ema_short'].iloc[-1]
    last_closed_long = df['ema_long'].iloc[-2]
    live_long = df['ema_long'].iloc[-1]

    # Determine the current live status
    analysis["live_status"] = "Short > Long" if live_short > live_long else "Short < Long"

    # Detect if a crossover is happening *right now*
    if last_closed_short <= last_closed_long and live_short > live_long:
        analysis["live_crossover_detected"] = 'Bullish'
    elif last_closed_short >= last_closed_long and live_short < live_long:
        analysis["live_crossover_detected"] = 'Bearish'
        
    return analysis


# --- Redis Caching Logic ---

def save_state_to_redis(symbol: str, timeframe: str, df: pd.DataFrame, last_signal_state: dict):
    """Saves the DataFrame and last signal state to Redis."""
    if not redis_client: return
    redis_key = f"screener_state:{symbol}:{timeframe}"
    data_to_save = {
        "df_json": df.to_json(orient='split'),
        "last_signal_state": json.dumps(last_signal_state)
    }
    with redis_client.pipeline() as pipe:
        pipe.hset(redis_key, mapping=data_to_save)
        pipe.expire(redis_key, 3 * 24 * 60 * 60) # 3-day expiry
        pipe.execute()
    logger.debug(f"Saved state for {symbol}-{timeframe} to Redis.")

def load_state_from_redis(symbol: str, timeframe: str) -> tuple[pd.DataFrame | None, dict | None]:
    """Loads the DataFrame and last signal state from Redis."""
    if not redis_client: return None, None
    redis_key = f"screener_state:{symbol}:{timeframe}"
    saved_data = redis_client.hgetall(redis_key)
    
    if not saved_data:
        return None, None

    try:
        df = pd.read_json(saved_data['df_json'], orient='split')
        df.index = df.index.tz_localize('UTC') # Restore timezone
        last_signal_state = json.loads(saved_data['last_signal_state'])
        logger.info(f"Loaded state for {symbol}-{timeframe} from Redis.")
        return df, last_signal_state
    except Exception as e:
        logger.error(f"Error decoding Redis state for {symbol}-{timeframe}: {e}")
        return None, None


# --- Symbol & Watchlist Management ---
_all_symbols_cache = {"symbols": [], "timestamp": 0}
CACHE_DURATION_SECONDS = 4 * 60 * 60

async def get_all_symbols_cached():
    now = time.time()
    if not _all_symbols_cache["symbols"] or (now - _all_symbols_cache["timestamp"]) > CACHE_DURATION_SECONDS:
        logger.info("Fetching fresh list of all symbols...")
        url = "https://api.india.delta.exchange/v2/products"
        try:
            response = await client.get(url, headers={'Accept': 'application/json'}, timeout=10.0)
            response.raise_for_status()
            products = response.json().get('result', [])
            symbols = [p['symbol'] for p in products if not p['symbol'].startswith(('C-', 'P-', 'MV-'))]
            if symbols:
                _all_symbols_cache["symbols"] = symbols
                _all_symbols_cache["timestamp"] = now
        except Exception as exc:
            logger.error(f"Error fetching all symbols from API: {exc}")
    return _all_symbols_cache["symbols"]

def get_current_watchlist():
    if not WATCHLIST_FILE.exists(): return []
    with open(WATCHLIST_FILE, "r") as f:
        try:
            data = json.load(f)
            return data.get("symbols", []) if isinstance(data, dict) else data
        except json.JSONDecodeError:
            return []

def _write_watchlist_data(symbols: list):
    with open(WATCHLIST_FILE, "w") as f:
        json.dump({"symbols": sorted(list(set(symbols)))}, f, indent=2)

def add_symbol_to_watchlist(symbol: str):
    current_symbols = get_current_watchlist()
    if symbol and symbol not in current_symbols:
        current_symbols.append(symbol)
        _write_watchlist_data(current_symbols)
    return get_current_watchlist()

def remove_symbol_from_watchlist(symbol_to_remove: str):
    current_symbols = get_current_watchlist()
    updated_symbols = [s for s in current_symbols if s != symbol_to_remove]
    _write_watchlist_data(updated_symbols)
    return updated_symbols