import time
import httpx  # Import httpx instead of requests
import pandas as pd
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

# Create a single, reusable AsyncClient. This is much more efficient than creating a new one for every request.
# It manages a connection pool internally.
client = httpx.AsyncClient()

# The function is now defined with "async def"
async def fetch_historical_candles(symbol, resolution, start, end):
    """
    Fetches and cleans historical candles asynchronously.
    Returns cleaned pandas DataFrame or empty DataFrame on error/no data.
    """
    url = 'https://api.india.delta.exchange/v2/history/candles'
    params = {
        'symbol': symbol,
        'resolution': resolution,
        'start': start,
        'end': end
    }
    headers = {'Accept': 'application/json'}

    try:
        # We use "await" to pause the function here until the network request is complete,
        # allowing other code to run in the meantime.
        response = await client.get(url, params=params, headers=headers, timeout=10.0)
        response.raise_for_status()  # Still good practice to check for HTTP errors (4xx or 5xx)
        data = response.json().get('result', [])
    except httpx.HTTPStatusError as exc:
        logger.error(f"HTTP error fetching {symbol} {resolution}: {exc}")
        return pd.DataFrame()
    except httpx.RequestError as exc:
        logger.error(f"Network error fetching {symbol} {resolution}: {exc}")
        return pd.DataFrame()
    except Exception as exc:
        logger.error(f"An unexpected error occurred for {symbol} {resolution}: {exc}")
        return pd.DataFrame()

    if not data:
        logger.warning(f"No historical candle data received for {symbol} {resolution}")
        return pd.DataFrame()

    df = pd.DataFrame(data, columns=['time', 'open', 'high', 'low', 'close', 'volume'])
    # The rest of your data cleaning logic is great and remains the same!
    df.set_index('time', inplace=True)
    df = df[df['volume'] > 0]
    for col in ['open', 'high', 'low', 'close']:
        df = df[df[col] > 0]
        median = df[col].median()
        mad = (df[col] - median).abs().median()
        if mad > 0:
            df = df[((df[col] - median).abs()) < (10 * mad)]
            
    return df

# The other functions (get_historical_ema_crossovers, check_ema_crossover_signal)
# don't do any I/O, so they don't need to be async. They can stay as they are.
# ... (paste your other helper functions here) ...


# Store last crossover timestamps for cooldown (symbol-timeframe keys)
last_crossover_time = {}

def get_historical_ema_crossovers(df, symbol="", timeframe="", short_period=9, long_period=20, volume_threshold_factor=1.0, cooldown_minutes=30):
    warmup = max(short_period, long_period) * 3
    if len(df) < warmup + 2:
        return []

    df[f'ema_{short_period}'] = df['close'].ewm(span=short_period, adjust=False).mean()
    df[f'ema_{long_period}'] = df['close'].ewm(span=long_period, adjust=False).mean()

    df['signal'] = 0
    df.loc[df[f'ema_{short_period}'] > df[f'ema_{long_period}'], 'signal'] = 1
    df.loc[df[f'ema_{short_period}'] < df[f'ema_{long_period}'], 'signal'] = -1

    df['crossover'] = df['signal'].diff()

    crossovers = []
    now = datetime.utcnow()

    for idx, row in df.iterrows():
        if row['crossover'] != 0:
            # Volume filter on this crossover's candle
            avg_volume = df['volume'].rolling(window=20).mean().loc[idx]
            if row['volume'] < volume_threshold_factor * avg_volume:
                continue  # Skip low volume crossovers

            # Cooldown check
            key = f"{symbol}-{timeframe}"
            last_time = last_crossover_time.get(key)
            timestamp = datetime.utcfromtimestamp(idx)
            if last_time and (timestamp - last_time) < timedelta(minutes=cooldown_minutes):
                continue  # Skip within cooldown period

            crossovers.append({
                "timestamp": idx,
                "type": "bullish" if row['crossover'] > 0 else "bearish",
                "close": row['close']
            })

            last_crossover_time[key] = timestamp

    return crossovers


def check_ema_crossover_signal(df, short_period=9, long_period=20):
    """
    Checks for EMA crossovers using only closed candles and enough historical bars.
    Returns "BUY", "SELL", or None.
    - Uses bar[-2] and bar[-1] (last two closed bars)
    - Requires at least 3x longest EMA period as warmup
    """
    warmup = max(short_period, long_period) * 3
    if len(df) < warmup + 2:
        return None  # not enough data for reliable EMA

    # Calculate EMAs
    df[f'ema_{short_period}'] = df['close'].ewm(span=short_period, adjust=False).mean()
    df[f'ema_{long_period}'] = df['close'].ewm(span=long_period, adjust=False).mean()

    # Only use last two *closed* candles (not in-progress candle)
    prev_short = df[f'ema_{short_period}'].iloc[-3]
    prev_long = df[f'ema_{long_period}'].iloc[-3]
    curr_short = df[f'ema_{short_period}'].iloc[-2]
    curr_long = df[f'ema_{long_period}'].iloc[-2]

    if prev_short <= prev_long and curr_short > curr_long:
        return "BUY"
    elif prev_short >= prev_long and curr_short < curr_long:
        return "SELL"
    return None

