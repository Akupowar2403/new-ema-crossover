import time
import httpx
import pandas as pd
import logging
from datetime import datetime
import redis

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
        response = await client.get(url, params=params, headers=headers, timeout=10.0)
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

    # --- Data Cleaning (Vectorized) ---
    price_cols = ['open', 'high', 'low', 'close']
    df = df[df['volume'] > 0]
    df = df[(df[price_cols] > 0).all(axis=1)] # Ensure all prices are positive

    # Outlier removal loop (MAD filter)
    for col in price_cols:
        if not df.empty: # Prevent errors on an empty dataframe
            median = df[col].median()
            mad = (df[col] - median).abs().median()
            # Only filter if mad is a positive, non-zero number
            if mad > 0:
                df = df[(df[col] - median).abs() < (10 * mad)]
    
    return df

def get_historical_ema_crossovers(df: pd.DataFrame, symbol: str, timeframe: str, short_period=9, long_period=20, volume_threshold_factor=1.0, cooldown_minutes=30) -> list:
    """
    Finds the first valid EMA crossover using fast, vectorized Pandas operations
    and checks against a Redis-based cooldown.
    """
    warmup = max(short_period, long_period) * 3
    if len(df) < warmup + 2:
        return []
    if not redis_client:
        logger.warning("Redis client not available. Cannot check for crossovers.")
        return []

    # --- Step 1: Calculate Indicators (Vectorized) ---
    df['ema_short'] = df['close'].ewm(span=short_period, adjust=False).mean()
    df['ema_long'] = df['close'].ewm(span=long_period, adjust=False).mean()
    df['signal'] = 0
    df.loc[df['ema_short'] > df['ema_long'], 'signal'] = 1
    df.loc[df['ema_short'] < df['ema_long'], 'signal'] = -1
    df['crossover'] = df['signal'].diff()

    # --- Step 2: Pre-filter Crossovers and Volume (Vectorized) ---
    crossover_points = df[df['crossover'] != 0].copy()
    if crossover_points.empty:
        return []

    df['avg_volume'] = df['volume'].rolling(window=20).mean()
    volume_mask = crossover_points['volume'] >= (volume_threshold_factor * df['avg_volume'].loc[crossover_points.index])
    valid_candidates = crossover_points[volume_mask]

    # --- Step 3: Final Redis Check (Small Loop on Candidates) ---
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
        break # Only signal the very first valid crossover

    return final_crossovers

def check_ema_crossover_signal(df: pd.DataFrame, short_period=9, long_period=20) -> str | None:
    """
    Checks for a fresh EMA crossover on the last two closed candles.
    Returns "BUY", "SELL", or None.
    """
    warmup = max(short_period, long_period) * 3
    if len(df) < warmup + 2:
        return None

    df['ema_short'] = df['close'].ewm(span=short_period, adjust=False).mean()
    df['ema_long'] = df['close'].ewm(span=long_period, adjust=False).mean()

    # Use the last three data points to check the last two *closed* candles
    # df.iloc[-1] is the current, incomplete bar
    # df.iloc[-2] is the most recently closed bar
    # df.iloc[-3] is the bar before that
    prev_short, prev_long = df[['ema_short', 'ema_long']].iloc[-3]
    curr_short, curr_long = df[['ema_short', 'ema_long']].iloc[-2]

    if prev_short <= prev_long and curr_short > curr_long:
        return "BUY"
    elif prev_short >= prev_long and curr_short < curr_long:
        return "SELL"
    
    return None

def get_bars_since_last_signal(df: pd.DataFrame) -> int | None:
    """
    Calculates the number of bars since the last crossover event.
    """
    if 'crossover' not in df.columns or df[df['crossover'] != 0].empty:
        return None
    
    # Find the index (timestamp) of the last row where a crossover occurred
    last_crossover_index = df[df['crossover'] != 0].index[-1]
    
    # Get the integer position of that index
    last_crossover_pos = df.index.get_loc(last_crossover_index)
    
    # Calculate bars since: total bars minus the position of the last crossover minus 1
    bars_since = len(df) - last_crossover_pos - 1
    return bars_since