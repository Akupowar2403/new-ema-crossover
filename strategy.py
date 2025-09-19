# import pandas as pd
# import logging

# # Setup logger for this module
# logger = logging.getLogger(__name__)
# logger.setLevel(logging.DEBUG)  # Set to DEBUG to see detailed EMA logs

# # Add console handler if no handlers exist (for standalone testing)
# if not logger.hasHandlers():
#     ch = logging.StreamHandler()
#     ch.setLevel(logging.DEBUG)
#     formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
#     ch.setFormatter(formatter)
#     logger.addHandler(ch)

# def check_ema_crossover_signal(df, short_period=9, long_period=20):
#     """
#     Returns "📈 BUY", "📉 SELL", or None based on EMA crossover.
#     Expects df with 'close' column indexed by timestamp.
#     """

#     # Ensure enough data points for EMA calculation
#     if len(df) < max(short_period, long_period) + 2:
#         return None

#     # Calculate EMAs with adjust=False (standard practice)
#     df[f'ema_{short_period}'] = df['close'].ewm(span=short_period, adjust=False).mean()
#     df[f'ema_{long_period}'] = df['close'].ewm(span=long_period, adjust=False).mean()

#     # Get previous and current EMA values
#     prev_short = df[f'ema_{short_period}'].iloc[-2]
#     curr_short = df[f'ema_{short_period}'].iloc[-1]
#     prev_long = df[f'ema_{long_period}'].iloc[-2]
#     curr_long = df[f'ema_{long_period}'].iloc[-1]

#     # Log EMA values for debugging
#     logger.debug(f"Previous EMA {short_period}: {prev_short}, Current EMA {short_period}: {curr_short}")
#     logger.debug(f"Previous EMA {long_period}: {prev_long}, Current EMA {long_period}: {curr_long}")

#     # Determine crossover signal
#     if prev_short <= prev_long and curr_short > curr_long:
#         return "📈 BUY"
#     elif prev_short >= prev_long and curr_short < curr_long:
#         return "📉 SELL"
#     else:
#         return None

import pandas as pd
import logging

# Setup logger for this module
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)  # Set to DEBUG to see detailed EMA logs

# Add console handler if no handlers exist (for standalone testing)
if not logger.hasHandlers():
    ch = logging.StreamHandler()
    ch.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    ch.setFormatter(formatter)
    logger.addHandler(ch)

last_logged_candle_time = None

def check_ema_crossover_signal(df, short_period=9, long_period=20):
    global last_logged_candle_time

    df[f'ema_{short_period}'] = df['close'].ewm(span=short_period, adjust=False).mean()
    df[f'ema_{long_period}'] = df['close'].ewm(span=long_period, adjust=False).mean()

    prev_short = df[f'ema_{short_period}'].iloc[-2]
    curr_short = df[f'ema_{short_period}'].iloc[-1]
    prev_long = df[f'ema_{long_period}'].iloc[-2]
    curr_long = df[f'ema_{long_period}'].iloc[-1]

    candle_time = df.index[-1]
    close_price = df['close'].iloc[-1]
    readable_time = pd.to_datetime(candle_time, unit='s')

    if candle_time != last_logged_candle_time:
        logger.debug(
            f"Candle Time: {readable_time} | Close: {close_price}\n"
            f"Previous EMA {short_period}: {prev_short}, Current EMA {short_period}: {curr_short}\n"
            f"Previous EMA {long_period}: {prev_long}, Current EMA {long_period}: {curr_long}"
        )
        last_logged_candle_time = candle_time

    signal = None
    if prev_short <= prev_long and curr_short > curr_long:
        signal = "📈 BUY"
    elif prev_short >= prev_long and curr_short < curr_long:
        signal = "📉 SELL"

    if signal:
        logger.info(f"Signal: {signal} at {readable_time}")

    return signal