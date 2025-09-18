import time
import httpx
import pandas as pd
import logging
from datetime import datetime
import redis
import json

from pathlib import Path

WATCHLIST_FILE = Path("watchlist.json")

# --- Basic Setup ---
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- Redis Connection ---
# Establishes a connection to the Redis server.
# decode_responses=True automatically converts Redis's binary responses into Python strings.
try:
    redis_client = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
    redis_client.ping()
    logger.info("Successfully connected to Redis.")
except redis.exceptions.ConnectionError as e:
    logger.critical(f"Could not connect to Redis. Cooldown logic will be disabled. Error: {e}")
    redis_client = None

# --- Reusable HTTP Client ---
# Creates a single, reusable AsyncClient for efficient connection pooling.
client = httpx.AsyncClient()

async def fetch_historical_candles(symbol: str, resolution: str, start: int, end: int) -> pd.DataFrame:
    """
    Fetches and cleans historical candles asynchronously using httpx.
    - Removes zero/negative volume and price rows.
    - Removes extreme price outliers (flash wicks).
    Returns a cleaned pandas DataFrame or an empty one on error.
    """
    url = 'https://api.india.delta.exchange/v2/history/candles'
    params = {'symbol': symbol, 'resolution': resolution, 'start': start, 'end': end}
    headers = {'Accept': 'application/json'}

    try:
        # Increased timeout to 30 seconds for larger data requests
        response = await client.get(url, params=params, headers=headers, timeout=30.0)
        response.raise_for_status()
        data = response.json().get('result', [])
    except (httpx.HTTPStatusError, httpx.RequestError) as exc:
        logger.error(f"Error fetching candles for {symbol} {resolution}: {exc}")
        return pd.DataFrame()

    if not data:
        logger.warning(f"No historical candle data received for {symbol} {resolution}")
        return pd.DataFrame()

    df = pd.DataFrame(data, columns=['time', 'open', 'high', 'low', 'close', 'volume'])
    df.set_index('time', inplace=True)
    
    # Convert Unix timestamp index to datetime, useful for analysis
    df.index = pd.to_datetime(df.index, unit='s')

    # Data Cleaning
    price_cols = ['open', 'high', 'low', 'close']
    df = df[df['volume'] > 0]
    df = df[(df[price_cols] > 0).all(axis=1)]

    # Outlier removal loop (MAD filter)
    for col in price_cols:
        if not df.empty:
            median = df[col].median()
            mad = (df[col] - median).abs().median()
            if mad > 0:
                df = df[(df[col] - median).abs() < (10 * mad)]
    
    return df

def get_historical_ema_crossovers(df: pd.DataFrame, symbol: str, timeframe: str, short_period=9, long_period=20, cooldown_minutes=30) -> list:
    """
    Finds the first valid EMA crossover. (Volume filter is removed).
    """
    warmup = max(short_period, long_period) * 3
    if len(df) < warmup + 2:
        return []
    if not redis_client:
        logger.warning("Redis client not available. Cannot check for crossovers.")
        return []

    # Calculate indicators
    df['ema_short'] = df['close'].ewm(span=short_period, adjust=False).mean()
    df['ema_long'] = df['close'].ewm(span=long_period, adjust=False).mean()
    df['signal'] = 0
    df.loc[df['ema_short'] > df['ema_long'], 'signal'] = 1
    df.loc[df['ema_short'] < df['ema_long'], 'signal'] = -1
    df['crossover'] = df['signal'].diff()

    # Get all points where a crossover occurred
    valid_candidates = df[df['crossover'] != 0].copy()
    if valid_candidates.empty:
        return []

    # Final Redis Check
    final_crossovers = []
    for idx, row in valid_candidates.iterrows():
        redis_key = f"cooldown:{symbol}-{timeframe}"
        if redis_client.exists(redis_key):
            continue

        final_crossovers.append({
            "timestamp": idx,
            "type": "bullish" if row['crossover'] > 0 else "bearish",
            "close": row['close']
        })
        
        cooldown_seconds = cooldown_minutes * 60
        redis_client.set(redis_key, "active", ex=cooldown_seconds)
        break 

    return final_crossovers

def check_ema_crossover_signal(df: pd.DataFrame, short_period=9, long_period=20) -> str:
    """
    Checks the CURRENT STATE of the EMAs on the last closed candle.
    Returns "Bullish" if short > long, "Bearish" if short < long, or "Neutral".
    """
    if len(df) < long_period + 2:
        return "N/A"

    # Ensure EMAs are calculated
    df['ema_short'] = df['close'].ewm(span=short_period, adjust=False).mean()
    df['ema_long'] = df['close'].ewm(span=long_period, adjust=False).mean()

    # Check the state of the last closed candle (iloc[-2])
    last_closed_short_ema = df['ema_short'].iloc[-2]
    last_closed_long_ema = df['ema_long'].iloc[-2]

    if last_closed_short_ema > last_closed_long_ema:
        return "Bullish"
    elif last_closed_short_ema < last_closed_long_ema:
        return "Bearish"
    
    return "Neutral"

def get_bars_since_last_signal(df: pd.DataFrame, short_period=9, long_period=20) -> int | None:
    """
    Calculates the number of bars since the last actual crossover event.
    """
    if len(df) < long_period + 2:
        return None

    # Calculate EMAs and signals to find crossover events
    df['ema_short'] = df['close'].ewm(span=short_period, adjust=False).mean()
    df['ema_long'] = df['close'].ewm(span=long_period, adjust=False).mean()
    
    df['signal'] = 0
    df.loc[df['ema_short'] > df['ema_long'], 'signal'] = 1
    df.loc[df['ema_short'] < df['ema_long'], 'signal'] = -1
    
    # A crossover is where the signal value changes (e.g., from 1 to -1)
    df['crossover'] = df['signal'].diff().fillna(0)
    
    crossover_events = df[df['crossover'] != 0]
    
    if crossover_events.empty:
        return None
    
    # Get the integer position of the last crossover event in the DataFrame
    last_crossover_pos = df.index.get_loc(crossover_events.index[-1])
    
    # Calculate bars since: total bars minus the position of the last crossover, minus 1
    bars_since = len(df) - 1 - last_crossover_pos
    return bars_since

# --- All Symbols Fetching & Caching ---

# Simple in-memory cache to hold the master list of symbols
_all_symbols_cache = {
    "symbols": [],
    "timestamp": 0
}
CACHE_DURATION_SECONDS = 4 * 60 * 60 # Cache for 4 hours

async def _fetch_all_symbols_from_api():
    """
    Fetches all product symbols from Delta Exchange API asynchronously.
    Excludes options ('C-', 'P-') and MOVE contracts ('MV-').
    """
    url = "https://api.india.delta.exchange/v2/products"
    try:
        response = await client.get(url, headers={'Accept': 'application/json'}, timeout=10.0)
        response.raise_for_status()
        products = response.json().get('result', [])
        
        symbols = [
            p['symbol'] for p in products
            if not (p['symbol'].startswith(('C-', 'P-', 'MV-')))
        ]
        return symbols
    except Exception as exc:
        logger.error(f"Error fetching all symbols from API: {exc}")
        return []

async def get_all_symbols_cached():
    """
    Returns a list of all symbols, using a time-based cache to avoid
    hitting the exchange API on every request.
    """
    now = time.time()
    is_cache_stale = (now - _all_symbols_cache["timestamp"]) > CACHE_DURATION_SECONDS
    
    if not _all_symbols_cache["symbols"] or is_cache_stale:
        logger.info("Cache is stale or empty. Fetching fresh list of all symbols...")
        symbols = await _fetch_all_symbols_from_api()
        if symbols: # Only update cache if the fetch was successful
            _all_symbols_cache["symbols"] = symbols
            _all_symbols_cache["timestamp"] = now
    else:
        logger.info("Returning all symbols from cache.")
        
    return _all_symbols_cache["symbols"]

# --- Watchlist File Management ---

def _read_watchlist_data():
    """Reads the watchlist.json file and returns the list of symbols."""
    if not WATCHLIST_FILE.exists():
        return []
    with open(WATCHLIST_FILE, "r", encoding="utf-8") as f:
        try:
            data = json.load(f)
            # Handle both formats: {"symbols": [...]} and [...]
            if isinstance(data, dict):
                return data.get("symbols", [])
            elif isinstance(data, list):
                return data
        except json.JSONDecodeError:
            return [] # Return empty list if file is empty or malformed
    return []

def _write_watchlist_data(symbols: list):
    """Writes a list of symbols to the watchlist.json file."""
    with open(WATCHLIST_FILE, "w", encoding="utf-8") as f:
        # We will now standardize on the dictionary format for writing
        json.dump({"symbols": sorted(list(set(symbols)))}, f, indent=2)

def get_current_watchlist():
    """Returns the current list of symbols from the watchlist."""
    return _read_watchlist_data()

def add_symbol_to_watchlist(symbol: str):
    """Adds a new symbol to the watchlist if it doesn't already exist."""
    current_symbols = _read_watchlist_data()
    if symbol and symbol not in current_symbols:
        current_symbols.append(symbol)
        _write_watchlist_data(current_symbols)
    return get_current_watchlist()

def remove_symbol_from_watchlist(symbol_to_remove: str):
    """Removes a symbol from the watchlist."""
    current_symbols = _read_watchlist_data()
    # Use a list comprehension for a clean removal
    updated_symbols = [s for s in current_symbols if s != symbol_to_remove]
    _write_watchlist_data(updated_symbols)
    return get_current_watchlist()