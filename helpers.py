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
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

try:
    redis_client = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
    redis_client.ping()
    logger.info("Successfully connected to Redis.")
except redis.exceptions.ConnectionError as e:
    logger.critical(f"Could not connect to Redis. Caching will be disabled. Error: {e}")
    redis_client = None

client = httpx.AsyncClient()

async def fetch_historical_candles(symbol: str, resolution: str, start: int, end: int, semaphore: asyncio.Semaphore) -> pd.DataFrame:
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
    if not data: return pd.DataFrame()
    df = pd.DataFrame(data, columns=['time', 'open', 'high', 'low', 'close', 'volume'])
    df.set_index('time', inplace=True)
    df.index = pd.to_datetime(df.index, unit='s').tz_localize('UTC')
    price_cols = ['open', 'high', 'low', 'close']
    df = df[df['volume'] > 0]
    df = df[(df[price_cols] > 0).all(axis=1)]
    for col in price_cols:
        if not df.empty:
            median = df[col].median()
            mad = (df[col] - median).abs().median()
            if mad > 0: df = df[(df[col] - median).abs() < (10 * mad)]
    return df


def analyze_ema_state(df: pd.DataFrame) -> dict:
    """
    Analyzes candle data and returns a dictionary with keys
    matching the frontend's expectations ('status', 'bars_since').
    """
    analysis = {
        "status": "N/A",
        "bars_since": None,
        "live_status": "N/A",
        "live_crossover_detected": None
    }

    if len(df) < config.LONG_EMA_PERIOD + 2:
        return analysis

    df = df.copy()
    df['ema_short'] = df['close'].ewm(span=config.SHORT_EMA_PERIOD, adjust=False).mean()
    df['ema_long'] = df['close'].ewm(span=config.LONG_EMA_PERIOD, adjust=False).mean()

    confirmed_crossover_index = None
    for i in range(len(df) - 2, 0, -1):
        prev_s, curr_s = df['ema_short'].iloc[i - 1], df['ema_short'].iloc[i]
        prev_l, curr_l = df['ema_long'].iloc[i - 1], df['ema_long'].iloc[i]
        
        if prev_s <= prev_l and curr_s > curr_l:
            analysis["status"] = 'Bullish'
            confirmed_crossover_index = i
            break
        elif prev_s >= prev_l and curr_s < curr_l:
            analysis["status"] = 'Bearish'
            confirmed_crossover_index = i
            break

    if confirmed_crossover_index is not None:
        analysis["bars_since"] = (len(df) - 2) - confirmed_crossover_index

    last_closed_short, live_short = df['ema_short'].iloc[-2], df['ema_short'].iloc[-1]
    last_closed_long, live_long = df['ema_long'].iloc[-2], df['ema_long'].iloc[-1]
    analysis["live_status"] = "Short > Long" if live_short > live_long else "Short < Long"
    if last_closed_short <= last_closed_long and live_short > live_long:
        analysis["live_crossover_detected"] = 'Bullish'
    elif last_closed_short >= last_closed_long and live_short < live_long:
        analysis["live_crossover_detected"] = 'Bearish'
        
    return analysis

def find_all_crossovers(df: pd.DataFrame, short_period: int = 9, long_period: int = 21, confirmation_periods: int = 1) -> list:

    if len(df) < long_period + confirmation_periods:
        return []

    df = df.sort_index().copy()
    short_ema_col = f"ema_{short_period}"
    long_ema_col = f"ema_{long_period}"

    df[short_ema_col] = df['close'].ewm(span=short_period, adjust=False).mean()
    df[long_ema_col] = df['close'].ewm(span=long_period, adjust=False).mean()

    crossovers = []
    for i in range(1, len(df) - confirmation_periods):
        prev_s = df[short_ema_col].iloc[i - 1]
        curr_s = df[short_ema_col].iloc[i]
        prev_l = df[long_ema_col].iloc[i - 1]
        curr_l = df[long_ema_col].iloc[i]

        is_bullish_cross = prev_s <= prev_l and curr_s > curr_l
        is_bearish_cross = prev_s >= prev_l and curr_s < curr_l

        if not (is_bullish_cross or is_bearish_cross):
            continue

        confirmation_failed = False
        for j in range(1, confirmation_periods + 1):
            next_s = df[short_ema_col].iloc[i + j]
            next_l = df[long_ema_col].iloc[i + j]

            if is_bullish_cross and next_s < next_l:
                confirmation_failed = True
                break
            elif is_bearish_cross and next_s > next_l:
                confirmation_failed = True
                break

        if confirmation_failed:
            continue

        crossover_type = 'bullish' if is_bullish_cross else 'bearish'
        crossovers.append({
            "type": crossover_type,
            "close": df['close'].iloc[i],
            "timestamp": int(df.index[i].timestamp()),
        })
            
    return crossovers

def save_state_to_redis(symbol: str, timeframe: str, df: pd.DataFrame, last_signal_state: dict):
    if not redis_client: return
    redis_key = f"screener_state:{symbol}:{timeframe}"
    data_to_save = {"df_json": df.to_json(orient='split'), "last_signal_state": json.dumps(last_signal_state)}
    with redis_client.pipeline() as pipe:
        pipe.hset(redis_key, mapping=data_to_save)
        pipe.expire(redis_key, 3 * 24 * 60 * 60)
        pipe.execute()

def load_state_from_redis(symbol: str, timeframe: str) -> tuple[pd.DataFrame | None, dict | None]:
    if not redis_client: return None, None
    redis_key = f"screener_state:{symbol}:{timeframe}"
    saved_data = redis_client.hgetall(redis_key)
    if not saved_data: return None, None
    try:
        df = pd.read_json(saved_data['df_json'], orient='split')
        df.index = df.index.tz_localize('UTC')
        last_signal_state = json.loads(saved_data['last_signal_state'])
        return df, last_signal_state
    except Exception: return None, None

_all_symbols_cache = {"symbols": [], "timestamp": 0}
CACHE_DURATION_SECONDS = 4 * 60 * 60
async def get_all_symbols_cached():
    now = time.time()
    if not _all_symbols_cache["symbols"] or (now - _all_symbols_cache["timestamp"]) > CACHE_DURATION_SECONDS:
        url = "https://api.india.delta.exchange/v2/products"
        try:
            response = await client.get(url, headers={'Accept': 'application/json'}, timeout=10.0)
            response.raise_for_status()
            products = response.json().get('result', [])
            symbols = [p['symbol'] for p in products if not p['symbol'].startswith(('C-', 'P-', 'MV-'))]
            if symbols: _all_symbols_cache.update({"symbols": symbols, "timestamp": now})
        except Exception as exc: logger.error(f"Error fetching all symbols from API: {exc}")
    return _all_symbols_cache["symbols"]

def get_current_watchlist():
    if not WATCHLIST_FILE.exists(): return []
    with open(WATCHLIST_FILE, "r") as f:
        try:
            data = json.load(f)
            return data.get("symbols", []) if isinstance(data, dict) else data
        except json.JSONDecodeError: return []

def _write_watchlist_data(symbols: list):
    with open(WATCHLIST_FILE, "w") as f: json.dump({"symbols": sorted(list(set(symbols)))}, f, indent=2)

def add_symbol_to_watchlist(symbol: str):
    symbols = get_current_watchlist()
    if symbol and symbol not in symbols:
        symbols.append(symbol)
        _write_watchlist_data(symbols)
    return get_current_watchlist()

def remove_symbol_from_watchlist(symbol: str):
    symbols = get_current_watchlist()
    updated = [s for s in symbols if s != symbol]
    _write_watchlist_data(updated)
    return updated