# import pandas as pd

# # def check_ema_crossover_signal(df, short_period=9, long_period=20):
# #     """
# #     Returns "BUY", "SELL", or None based on 9 EMA crossing 20 EMA.
# #     Expects df with 'close' column.
# #     """

# #     if len(df) < max(short_period, long_period) + 2:
# #         return None
# #     print(df[:6])
# #     curr_short= df['close'].ewm(span=short_period, adjust=True).mean()
# #     curr_long = df['close'].ewm(span=long_period, adjust=True).mean()

# #     prev_short = df[f'ema_{short_period}'].iloc[-2]
# #     curr_short = df[f'ema_{short_period}'].iloc[-1]
# #     prev_long = df[f'ema_{long_period}'].iloc[-2]
# #     curr_long = df[f'ema_{long_period}'].iloc[-1]

# #     print(f"ema value for {short_period} close {curr_short}")
# #     print(f"ema value for {long_period} close {curr_long}")

# #     # Bullish crossover: 9 EMA crosses above 20 EMA
# #     if prev_short <= prev_long and curr_short > curr_long:
# #         return "📈 BUY"
# #     # Bearish crossover: 9 EMA crosses below 20 EMA
# #     elif prev_short >= prev_long and curr_short < curr_long:
# #         return "📉 SELL"
# #     return None

# import pandas as pd

# def check_ema_crossover_signal(df, short_period=1, long_period=10):
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

#     # Debug prints (optional, remove in production)
#     # print(df.tail(6))
#     print(f"Previous EMA {short_period}: {prev_short}, Current EMA {short_period}: {curr_short}")
#     print(f"Previous EMA {long_period}: {prev_long}, Current EMA {long_period}: {curr_long}")

#     # Determine crossover signal
#     if prev_short <= prev_long and curr_short > curr_long:
#         return "📈 BUY"
#     elif prev_short >= prev_long and curr_short < curr_long:
#         return "📉 SELL"
#     else:
#         return None

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



# import pandas as pd
# import logging

# # Setup logger for this module
# logger = logging.getLogger(__name__)
# logger.setLevel(logging.DEBUG)  # Set to DEBUG to see detailed SMA logs

# # Add console handler if no handlers exist (for standalone testing)
# if not logger.hasHandlers():
#     ch = logging.StreamHandler()
#     ch.setLevel(logging.DEBUG)
#     formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
#     ch.setFormatter(formatter)
#     logger.addHandler(ch)

# def check_sma_crossover_signal(df, short_period=20, long_period=100):
#     """
#     Returns "📈 BUY", "📉 SELL", or None based on SMA crossover.
#     Expects df with 'close' column indexed by timestamp.
#     """

#     # Ensure enough data points for SMA calculation
#     if len(df) < max(short_period, long_period) + 2:
#         return None

#     # Calculate SMAs
#     df[f'sma_{short_period}'] = df['close'].rolling(window=short_period).mean()
#     df[f'sma_{long_period}'] = df['close'].rolling(window=long_period).mean()

#     # Get previous and current SMA values
#     prev_short = df[f'sma_{short_period}'].iloc[-2]
#     curr_short = df[f'sma_{short_period}'].iloc[-1]
#     prev_long = df[f'sma_{long_period}'].iloc[-2]
#     curr_long = df[f'sma_{long_period}'].iloc[-1]

#     # Log SMA values for debugging
#     logger.debug(f"Previous SMA {short_period}: {prev_short}, Current SMA {short_period}: {curr_short}")
#     logger.debug(f"Previous SMA {long_period}: {prev_long}, Current SMA {long_period}: {curr_long}")

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

def check_ema_crossover_signal(df, short_period=5, long_period=10):
    """
    Returns "📈 BUY", "📉 SELL", or None based on EMA crossover.
    Expects df with 'close' column indexed by timestamp.
    """

    # Ensure enough data points for accurate EMA calculation
    warmup = max(short_period, long_period) * 3
    if len(df) < warmup + 2:
        return None

    # Calculate EMAs with adjust=False (standard for trading charts)
    df[f'ema_{short_period}'] = df['close'].ewm(span=short_period, adjust=False).mean()
    df[f'ema_{long_period}'] = df['close'].ewm(span=long_period, adjust=False).mean()

    # Get previous and current EMA values
    prev_short = df[f'ema_{short_period}'].iloc[-2]
    curr_short = df[f'ema_{short_period}'].iloc[-1]
    prev_long = df[f'ema_{long_period}'].iloc[-2]
    curr_long = df[f'ema_{long_period}'].iloc[-1]

    # Log EMA values for debugging
    logger.debug(
        f"\nPrevious EMA {short_period}: {prev_short}, Current EMA {short_period}: {curr_short}\n"
        f"Previous EMA {long_period}: {prev_long}, Current EMA {long_period}: {curr_long}"
    )
    # Determine crossover signal
    if prev_short <= prev_long and curr_short > curr_long:
        return "📈 BUY"
    elif prev_short >= prev_long and curr_short < curr_long:
        return "📉 SELL"
    else:
        return None

# import pandas as pd
# import logging

# # Setup a named logger for strategy module
# logger = logging.getLogger('strategy')
# logger.setLevel(logging.DEBUG)  # Enables debug logs

# # Do NOT add StreamHandler here if you want logs only in your Telegram bot log files
# # Ensure no duplicate handlers by adding only if none exist - optional
# if not logger.hasHandlers():
#     # If you want to test standalone and see console logs, uncomment this block:
#     # ch = logging.StreamHandler()
#     # ch.setLevel(logging.DEBUG)
#     # formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
#     # ch.setFormatter(formatter)
#     # logger.addHandler(ch)
#     pass

# def check_ema_crossover_signal(df, short_period=5, long_period=10):
#     """
#     Returns "📈 BUY", "📉 SELL", or None based on EMA crossover.
#     Expects df with 'close' column indexed by timestamp.
#     """

#     # Ensure enough data for stable EMA calculation
#     warmup = max(short_period, long_period) * 3
#     if len(df) < warmup + 2:
#         return None

#     # Calculate EMAs, adjust=False for usual trading behavior
#     df[f'ema_{short_period}'] = df['close'].ewm(span=short_period, adjust=False).mean()
#     df[f'ema_{long_period}'] = df['close'].ewm(span=long_period, adjust=False).mean()

#     prev_short = df[f'ema_{short_period}'].iloc[-2]
#     curr_short = df[f'ema_{short_period}'].iloc[-1]
#     prev_long = df[f'ema_{long_period}'].iloc[-2]
#     curr_long = df[f'ema_{long_period}'].iloc[-1]

#     # Unified debug log message
#     logger.debug(
#         f"\nPrevious EMA {short_period}: {prev_short}, Current EMA {short_period}: {curr_short} \n"
#         f"Previous EMA {long_period}: {prev_long}, Current EMA {long_period}: {curr_long}"
#     )

#     # Determine the crossover signal
#     if prev_short <= prev_long and curr_short > curr_long:
#         return "📈 BUY"
#     elif prev_short >= prev_long and curr_short < curr_long:
#         return "📉 SELL"
#     else:
#         return None
