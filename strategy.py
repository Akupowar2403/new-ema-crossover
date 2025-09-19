
# import pandas as pd

# last_crossover = None  # Track the last crossover direction globally

# def detect_last_crossover(df, short_period=9, long_period=20):
#     """
#     Scan historical data to find the most recent EMA crossover direction.
#     Returns 'bullish', 'bearish', or None if no crossover found.
#     """

#     ema_short = df['close'].ewm(span=short_period, adjust=False).mean()
#     ema_long = df['close'].ewm(span=long_period, adjust=False).mean()

#     # Iterate backward to find the last crossover point
#     for i in range(len(df)-1, 0, -1):
#         prev_short = ema_short.iloc[i-1]
#         curr_short = ema_short.iloc[i]
#         prev_long = ema_long.iloc[i-1]
#         curr_long = ema_long.iloc[i]

#         if prev_short <= prev_long and curr_short > curr_long:
#             return 'bullish'
#         elif prev_short >= prev_long and curr_short < curr_long:
#             return 'bearish'
#     return None

# def check_ema_crossover_signal(df, short_period=9, long_period=20):
#     global last_crossover

#     # On first run, determine the last crossover from historical data
#     if last_crossover is None:
#         last_crossover = detect_last_crossover(df, short_period, long_period)

#     # Calculate EMAs
#     df[f'ema_{short_period}'] = df['close'].ewm(span=short_period, adjust=False).mean()
#     df[f'ema_{long_period}'] = df['close'].ewm(span=long_period, adjust=False).mean()

#     # Get previous and current EMA values
#     prev_short = df[f'ema_{short_period}'].iloc[-2]
#     curr_short = df[f'ema_{short_period}'].iloc[-1]
#     prev_long = df[f'ema_{long_period}'].iloc[-2]
#     curr_long = df[f'ema_{long_period}'].iloc[-1]

#     # Get current candle time and readable format
#     candle_time = df.index[-1]
#     readable_time = pd.to_datetime(candle_time, unit='s')

#     # Detect crossover signals and update last_crossover accordingly
#     signal = None
#     if prev_short <= prev_long and curr_short > curr_long:
#         signal = "📈 BUY"
#         last_crossover = 'bullish'
#     elif prev_short >= prev_long and curr_short < curr_long:
#         signal = "📉 SELL"
#         last_crossover = 'bearish'

#     # Use last crossover to determine trend
#     if last_crossover == 'bullish':
#         trend = "Bullish Trend"
#     elif last_crossover == 'bearish':
#         trend = "Bearish Trend"
#     else:
#         trend = "Unknown Trend"

#     # Print EMAs, signal, and trend
#     print(f"Time: {readable_time}")
#     print(f"EMA {short_period}: {curr_short:.4f}, EMA {long_period}: {curr_long:.4f}")
#     if signal:
#         print(f"Signal: {signal} | Trend: {trend}")
#     else:
#         print(f"Trend: {trend}")

#     return signal, trend

# import pandas as pd

# last_crossover = None  # Track the last crossover direction globally
# last_crossover_index = None  # Track the index of last crossover

# def detect_last_crossover(df, short_period=9, long_period=20):
#     """
#     Scan historical data to find the most recent EMA crossover direction and its index.
#     Returns tuple: (direction, index) where direction is 'bullish' or 'bearish', index is int
#     or (None, None) if no crossover found.
#     """
#     ema_short = df['close'].ewm(span=short_period, adjust=False).mean()
#     ema_long = df['close'].ewm(span=long_period, adjust=False).mean()

#     # Iterate backward to find the last crossover point
#     for i in range(len(df) - 1, 0, -1):
#         prev_short = ema_short.iloc[i - 1]
#         curr_short = ema_short.iloc[i]
#         prev_long = ema_long.iloc[i - 1]
#         curr_long = ema_long.iloc[i]

#         if prev_short <= prev_long and curr_short > curr_long:
#             return 'bullish', i
#         elif prev_short >= prev_long and curr_short < curr_long:
#             return 'bearish', i
#     return None, None

# def check_ema_crossover_signal(df, short_period=9, long_period=20):
#     global last_crossover
#     global last_crossover_index

#     # On first run, determine the last crossover from historical data
#     if last_crossover is None or last_crossover_index is None:
#         last_crossover, last_crossover_index = detect_last_crossover(df, short_period, long_period)

#     # Calculate EMAs
#     df[f'ema_{short_period}'] = df['close'].ewm(span=short_period, adjust=False).mean()
#     df[f'ema_{long_period}'] = df['close'].ewm(span=long_period, adjust=False).mean()

#     # Get previous and current EMA values
#     prev_short = df[f'ema_{short_period}'].iloc[-2]
#     curr_short = df[f'ema_{short_period}'].iloc[-1]
#     prev_long = df[f'ema_{long_period}'].iloc[-2]
#     curr_long = df[f'ema_{long_period}'].iloc[-1]

#     # Get current candle time and readable format
#     candle_time = df.index[-1]
#     readable_time = pd.to_datetime(candle_time, unit='s')

#     # Detect crossover signals and update last_crossover accordingly
#     signal = None
#     if prev_short <= prev_long and curr_short > curr_long:
#         signal = "📈 BUY"
#         last_crossover = 'bullish'
#         last_crossover_index = len(df) - 1
#     elif prev_short >= prev_long and curr_short < curr_long:
#         signal = "📉 SELL"
#         last_crossover = 'bearish'
#         last_crossover_index = len(df) - 1

#     # Calculate bars since last crossover
#     bars_since_crossover = (len(df) - 1) - last_crossover_index if last_crossover_index is not None else None

#     # Use last crossover to determine trend
#     if last_crossover == 'bullish':
#         trend = "Bullish Trend"
#     elif last_crossover == 'bearish':
#         trend = "Bearish Trend"
#     else:
#         trend = "Unknown Trend"

#     # Print EMAs, signal, trend, and bars since crossover
#     print(f"Time: {readable_time}")
#     print(f"EMA {short_period}: {curr_short:.4f}, EMA {long_period}: {curr_long:.4f}")
#     if signal:
#         print(f"Signal: {signal} | Trend: {trend} | Bars Since Crossover: {bars_since_crossover}")
#     else:
#         print(f"Trend: {trend} | Bars Since Crossover: {bars_since_crossover}")

#     return signal, trend, bars_since_crossover

import pandas as pd

last_crossover = None  # Track the last crossover direction globally
last_crossover_index = None  # Track the index of last crossover

def detect_last_crossover(df, short_period=9, long_period=20):
    """
    Scan historical data to find the most recent EMA crossover direction and its index.
    Returns tuple: (direction, index) where direction is 'bullish' or 'bearish', index is int
    or (None, None) if no crossover found.
    """
    ema_short = df['close'].ewm(span=short_period, adjust=False).mean()
    ema_long = df['close'].ewm(span=long_period, adjust=False).mean()

    # Iterate backward to find the last crossover point
    for i in range(len(df) - 1, 0, -1):
        prev_short = ema_short.iloc[i - 1]
        curr_short = ema_short.iloc[i]
        prev_long = ema_long.iloc[i - 1]
        curr_long = ema_long.iloc[i]

        if prev_short <= prev_long and curr_short > curr_long:
            return 'bullish', i
        elif prev_short >= prev_long and curr_short < curr_long:
            return 'bearish', i
    return None, None

def check_ema_crossover_signal(df, short_period=9, long_period=20):
    global last_crossover
    global last_crossover_index

    # On first run, determine the last crossover from historical data
    if last_crossover is None or last_crossover_index is None:
        last_crossover, last_crossover_index = detect_last_crossover(df, short_period, long_period)

    # Calculate EMAs
    df[f'ema_{short_period}'] = df['close'].ewm(span=short_period, adjust=False).mean()
    df[f'ema_{long_period}'] = df['close'].ewm(span=long_period, adjust=False).mean()

    # Get previous and current EMA values
    prev_short = df[f'ema_{short_period}'].iloc[-2]
    curr_short = df[f'ema_{short_period}'].iloc[-1]
    prev_long = df[f'ema_{long_period}'].iloc[-2]
    curr_long = df[f'ema_{long_period}'].iloc[-1]

    # Get current candle time and readable format
    candle_time = df.index[-1]
    readable_time = pd.to_datetime(candle_time, unit='s')

    # Detect crossover signals and update last_crossover accordingly
    signal = None
    new_crossover = False
    if prev_short <= prev_long and curr_short > curr_long:
        signal = "📈 BUY"
        last_crossover = 'bullish'
        last_crossover_index = len(df) - 1
        new_crossover = True
    elif prev_short >= prev_long and curr_short < curr_long:
        signal = "📉 SELL"
        last_crossover = 'bearish'
        last_crossover_index = len(df) - 1
        new_crossover = True

    # Calculate bars since last crossover
    bars_since_crossover = (len(df) - 1) - last_crossover_index if last_crossover_index is not None else None

    # Use last_crossover to determine trend
    if last_crossover == 'bullish':
        trend = "Bullish Trend"
    elif last_crossover == 'bearish':
        trend = "Bearish Trend"
    else:
        trend = "Unknown Trend"

    # Print EMAs and trend info every call
    print(f"Time: {readable_time}")
    print(f"EMA {short_period}: {curr_short:.4f}, EMA {long_period}: {curr_long:.4f}")
    print(f"Trend: {trend} | Bars Since Crossover: {bars_since_crossover}")

    # Print alert only on new crossover
    if new_crossover and signal:
        print(f"Signal Alert: {signal}")

    return signal if new_crossover else None, trend, bars_since_crossover
