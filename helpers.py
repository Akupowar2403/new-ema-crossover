import time
import requests
import pandas as pd
import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

def fetch_historical_candles(symbol, resolution):
    """
    Fetches historical candles for a symbol and resolution from Delta Exchange.
    Gets maximum available history by using start=1.
    Returns a pandas DataFrame with time as index.
    """
    start = 1  # get maximum history from epoch start
    end = int(time.time())
    url = "https://api.india.delta.exchange/v2/history/candles"
    params = {
        "symbol": symbol,
        "resolution": resolution,
        "start": start,
        "end": end
    }
    headers = {"Accept": "application/json"}

    try:
        resp = requests.get(url, params=params, headers=headers)
        resp.raise_for_status()
        data = resp.json().get("result", [])
        if not data:
            logger.warning(f"No candles returned for {symbol} {resolution}")
            return pd.DataFrame()
        df = pd.DataFrame(data, columns=["time", "open", "high", "low", "close", "volume"])
        df.set_index("time", inplace=True)
        return df
    except Exception as e:
        logger.error(f"Error fetching candles for {symbol} {resolution}: {e}")
        return pd.DataFrame()

def get_historical_ema_crossovers(df, short_period=9, long_period=20):
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
    for idx, row in df.iterrows():
        if row['crossover'] != 0:
            crossovers.append({
                "timestamp": idx,
                "type": "bullish" if row['crossover'] > 0 else "bearish",
                "close": row['close']
            })

    return crossovers

def check_ema_crossover_signal(df, short_period=9, long_period=20):
    warmup = max(short_period, long_period) * 3
    if len(df) < warmup + 2:
        return None

    df[f'ema_{short_period}'] = df['close'].ewm(span=short_period, adjust=False).mean()
    df[f'ema_{long_period}'] = df['close'].ewm(span=long_period, adjust=False).mean()

    prev_short = df[f'ema_{short_period}'].iloc[-2]
    curr_short = df[f'ema_{short_period}'].iloc[-1]
    prev_long = df[f'ema_{long_period}'].iloc[-2]
    curr_long = df[f'ema_{long_period}'].iloc[-1]

    if prev_short <= prev_long and curr_short > curr_long:
        return "BUY"
    elif prev_short >= prev_long and curr_short < curr_long:
        return "SELL"
    return None
