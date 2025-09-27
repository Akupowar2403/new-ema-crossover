# # # from datetime import datetime, timezone
# # import datetime
# # import time
# # from datetime import timezone
# # from helpers import fetch_historical_candles

# # def _timeframe_to_seconds(timeframe: str) -> int:
# #     timeframe = timeframe.lower().strip()
# #     if timeframe.endswith('s'):
# #         return int(timeframe[:-1])
# #     elif timeframe.endswith('m'):
# #         return int(timeframe[:-1]) * 60
# #     elif timeframe.endswith('h'):
# #         return int(timeframe[:-1]) * 3600
# #     elif timeframe.endswith('d'):
# #         return int(timeframe[:-1]) * 86400
# #     elif timeframe.endswith('w'):
# #         return int(timeframe[:-1]) * 604800
# #     else:
# #         try:
# #             return int(timeframe) * 60
# #         except ValueError:
# #             raise ValueError(f"Invalid timeframe format: {timeframe}")

# # def get_aligned_start_time(timeframe_seconds: int, current_time: int = None) -> int:
# #     now = current_time or int(datetime.now(tz=timezone.utc).timestamp())
# #     aligned_start = (now // timeframe_seconds) * timeframe_seconds
# #     return aligned_start

# # def get_next_incremental_fetch_time(timeframe_seconds: int, current_time: int = None) -> int:
# #     now = current_time or int(datetime.now(tz=timezone.utc).timestamp())
# #     aligned_start = get_aligned_start_time(timeframe_seconds, now)
# #     next_fetch = aligned_start + timeframe_seconds
# #     return next_fetch

# # if __name__ == "__main__":
# #     timeframes = ["1m", "5m", "15m", "1h", "4h", "1d"]

# #     for tf in timeframes:
# #         seconds = _timeframe_to_seconds(tf)
# #         aligned_start = get_aligned_start_time(seconds)
# #         next_fetch = get_next_incremental_fetch_time(seconds)

# #         print(f"Timeframe: {tf}")
# #         print(f"  Seconds: {seconds}")
# #         print(f"  Aligned Start Time: {aligned_start} ({datetime.utcfromtimestamp(aligned_start)})")
# #         print(f"  Next Fetch Time: {next_fetch} ({datetime.utcfromtimestamp(next_fetch)})")
# #         print()  
# # //// this above function is for the calculating time in the second

# # import asyncio
# # import pandas as pd
# # import httpx
# # from datetime import datetime, timezone

# # # Helper: Convert timeframe string to seconds
# # def _timeframe_to_seconds(timeframe: str) -> int:
# #     timeframe = timeframe.lower().strip()
# #     if timeframe.endswith('s'):
# #         return int(timeframe[:-1])
# #     elif timeframe.endswith('m'):
# #         return int(timeframe[:-1]) * 60
# #     elif timeframe.endswith('h'):
# #         return int(timeframe[:-1]) * 3600
# #     elif timeframe.endswith('d'):
# #         return int(timeframe[:-1]) * 86400
# #     elif timeframe.endswith('w'):
# #         return int(timeframe[:-1]) * 604800
# #     else:
# #         try:
# #             return int(timeframe) * 60
# #         except ValueError:
# #             raise ValueError(f"Invalid timeframe format: {timeframe}")

# # # Helper: Align current time to last closed candle boundary
# # def get_aligned_start_time(timeframe_seconds: int, current_time: int = None) -> int:
# #     now = current_time or int(datetime.now(tz=timezone.utc).timestamp())
# #     aligned_start = (now // timeframe_seconds) * timeframe_seconds
# #     return aligned_start

# # # Helper: Filter only completed candles
# # def filter_closed_candles(df: pd.DataFrame, timeframe_seconds: int) -> pd.DataFrame:
# #     now = int(datetime.now(tz=timezone.utc).timestamp())
# #     return df[df.index.astype(int) + timeframe_seconds <= now]

# # # Async helper: Fetch historical candles from Delta Exchange
# # async def fetch_historical_candles(symbol: str, resolution: str, start: int, end: int, semaphore: asyncio.Semaphore):
# #     url = 'https://api.india.delta.exchange/v2/history/candles'
# #     params = {'symbol': symbol, 'resolution': resolution, 'start': start, 'end': end}
# #     headers = {'Accept': 'application/json'}
# #     async with semaphore:
# #         async with httpx.AsyncClient() as client:
# #             try:
# #                 response = await client.get(url, params=params, headers=headers, timeout=30.0)
# #                 response.raise_for_status()
# #                 response_json = response.json()
# #                 print(f"API response for {symbol}, {resolution}:", response_json)
# #                 data = response_json.get('result', [])
# #             except Exception as e:
# #                 print(f"Error fetching candles for {symbol} {resolution}: {e}")
# #                 return pd.DataFrame()
# #     if not data:
# #         return pd.DataFrame()
# #     df = pd.DataFrame(data, columns=['time', 'open', 'high', 'low', 'close', 'volume'])
# #     df.set_index('time', inplace=True)
# #     df.index = pd.to_datetime(df.index, unit='s').tz_localize('UTC')
# #     return df


# # # Initial bulk fetch for all timeframes
# # async def initial_bulk_fetch_all_timeframes(symbol: str, timeframes: list, semaphore: asyncio.Semaphore):
# #     results = {}
# #     async def fetch_for_timeframe(tf: str):
# #         tf_seconds = _timeframe_to_seconds(tf)
# #         now_aligned = get_aligned_start_time(tf_seconds)
# #         start_time = 1
# #         df = await fetch_historical_candles(symbol, tf, start_time, now_aligned, semaphore)
# #         df = filter_closed_candles(df, tf_seconds)
# #         results[tf] = df.sort_index()
# #         print(f"Fetched {len(df)} candles for {symbol} at timeframe {tf}.")
# #     tasks = [fetch_for_timeframe(tf) for tf in timeframes]
# #     await asyncio.gather(*tasks)
# #     return results

# # # Test execution
# # if __name__ == "__main__":
# #     async def main():
# #         semaphore = asyncio.Semaphore(5)
# #         symbol = "BTCUSD"
# #         timeframes = ["1m", "5m", "15m", "1h", "4h", "1d"]
# #         candle_data = await initial_bulk_fetch_all_timeframes(symbol, timeframes, semaphore)
# #         for tf, df in candle_data.items():
# #             print(f"Timeframe: {tf}, Candles fetched: {len(df)}")
# #             print(df.head())

# #     asyncio.run(main())

# import asyncio
# import pandas as pd
# import httpx
# import time
# from datetime import datetime, timezone


# # Convert timeframe string to seconds
# def _timeframe_to_seconds(tf: str) -> int:
#     tf = tf.lower().strip()
#     if tf.endswith('s'):
#         return int(tf[:-1])
#     elif tf.endswith('m'):
#         return int(tf[:-1]) * 60
#     elif tf.endswith('h'):
#         return int(tf[:-1]) * 3600
#     elif tf.endswith('d'):
#         return int(tf[:-1]) * 86400
#     elif tf.endswith('w'):
#         return int(tf[:-1]) * 604800
#     else:
#         try:
#             return int(tf) * 60
#         except Exception:
#             raise ValueError(f"Invalid timeframe format '{tf}'")


# # Align timestamp down to last candle boundary
# def get_aligned_time(tf_seconds: int, ts: int = None) -> int:
#     now_ts = ts or int(datetime.now(tz=timezone.utc).timestamp())
#     aligned = (now_ts // tf_seconds) * tf_seconds
#     return aligned


# # Filter DataFrame to include only fully closed candles
# def filter_closed_candles(df: pd.DataFrame, tf_seconds: int) -> pd.DataFrame:
#     now_ts = int(datetime.now(tz=timezone.utc).timestamp())
#     return df[df.index.astype(int) + tf_seconds <= now_ts]


# # Async fetch historical candles from Delta Exchange
# async def fetch_historical_candles(symbol: str, resolution: str, start: int, end: int, semaphore: asyncio.Semaphore) -> pd.DataFrame:
#     url = 'https://api.india.delta.exchange/v2/history/candles'
#     params = {'symbol': symbol, 'resolution': resolution, 'start': start, 'end': end}
#     headers = {'Accept': 'application/json'}
#     async with semaphore:
#         async with httpx.AsyncClient() as client:
#             try:
#                 response = await client.get(url, params=params, headers=headers, timeout=30.0)
#                 response.raise_for_status()
#                 data = response.json().get('result', [])
#                 await asyncio.sleep(0.1)  # slight delay to respect rate limits
#             except (httpx.HTTPStatusError, httpx.RequestError) as exc:
#                 print(f"Error fetching candles for {symbol} {resolution}: {exc}")
#                 return pd.DataFrame()
#     if not data:
#         print(f"No data received for {symbol} {resolution} from {start} to {end}")
#         return pd.DataFrame()
#     df = pd.DataFrame(data, columns=['time', 'open', 'high', 'low', 'close', 'volume'])
#     df.set_index('time', inplace=True)
#     df.index = df.index.astype(int)

#     price_cols = ['open', 'high', 'low', 'close']
#     df = df[df['volume'] > 0]
#     df = df[(df[price_cols] > 0).all(axis=1)]
#     for col in price_cols:
#         if not df.empty:
#             median = df[col].median()
#             mad = (df[col] - median).abs().median()
#             if mad > 0:
#                 df = df[(df[col] - median).abs() < (10 * mad)]
#     return df


# # Initial bulk fetch for 2000 candles with dynamic valid timings
# async def initial_bulk_fetch(symbol, timeframes, semaphore):
#     results = {}
#     for tf in timeframes:
#         tf_sec = _timeframe_to_seconds(tf)
#         end = get_aligned_time(tf_sec)
#         start = end - 2000 * tf_sec
#         now = int(datetime.now(tz=timezone.utc).timestamp())
#         if end > now:
#             end = now - 60  # 1 min buffer behind current
#         if start < 0:
#             start = 1  # Unix epoch minimum
#         df = await fetch_historical_candles(symbol, tf, start, end, semaphore)
#         df = filter_closed_candles(df, tf_sec)
#         results[tf] = df.sort_index()
#         print(f"Total candles fetched for {symbol} {tf}: {len(df)}")
#     return results


# # Incremental update loop to fetch latest 10 candles after each candle interval
# async def incremental_update_loop(symbol: str, timeframe: str, candle_df: pd.DataFrame, semaphore: asyncio.Semaphore):
#     tf_seconds = _timeframe_to_seconds(timeframe)

#     while True:
#         try:
#             aligned_end = get_aligned_time(tf_seconds)
#             start_time = aligned_end - (10 * tf_seconds)
#             end_time = aligned_end

#             new_candles = await fetch_historical_candles(symbol, timeframe, start_time, end_time, semaphore)
#             new_candles = filter_closed_candles(new_candles, tf_seconds)

#             if not new_candles.empty:
#                 combined_df = pd.concat([candle_df, new_candles])
#                 combined_df = combined_df[~combined_df.index.duplicated(keep='last')]
#                 candle_df = combined_df.sort_index()
#                 print(f"[{symbol} {timeframe}] Incremental fetch: {len(new_candles)} new candles added")
#             else:
#                 print(f"[{symbol} {timeframe}] Incremental fetch: no new candles")

#             next_fetch_time = aligned_end + tf_seconds
#             sleep_duration = max(0, next_fetch_time - int(time.time()))
#             await asyncio.sleep(sleep_duration)

#         except Exception as e:
#             print(f"Error in incremental update loop for {symbol} {timeframe}: {e}")
#             await asyncio.sleep(tf_seconds)  # Retry after one candle interval


# async def main():
#     semaphore = asyncio.Semaphore(5)
#     symbol = "BTCUSD"
#     timeframes = ["1m", "5m", "15m", "1h", "4h", "1d"]

#     # Initial bulk fetch to warm up candle data
#     candle_data = await initial_bulk_fetch(symbol, timeframes, semaphore)

#     # Start incremental update loop for all timeframes concurrently
#     tasks = []
#     for tf in timeframes:
#         df = candle_data.get(tf, pd.DataFrame())
#         task = asyncio.create_task(incremental_update_loop(symbol, tf, df, semaphore))
#         tasks.append(task)

#     await asyncio.gather(*tasks)


# if __name__ == '__main__':
#     asyncio.run(main())

# new one with new logic []
# import asyncio
# import pandas as pd
# import httpx
# import time
# from datetime import datetime, timezone


# def _timeframe_to_seconds(tf: str) -> int:
#     tf = tf.lower().strip()
#     if tf.endswith('s'):
#         return int(tf[:-1])
#     elif tf.endswith('m'):
#         return int(tf[:-1]) * 60
#     elif tf.endswith('h'):
#         return int(tf[:-1]) * 3600
#     elif tf.endswith('d'):
#         return int(tf[:-1]) * 86400
#     elif tf.endswith('w'):
#         return int(tf[:-1]) * 604800
#     else:
#         try:
#             return int(tf) * 60
#         except Exception:
#             raise ValueError(f"Invalid timeframe format '{tf}'")


# def get_aligned_time(tf_seconds: int, ts: int = None) -> int:
#     now_ts = ts or int(datetime.now(tz=timezone.utc).timestamp())
#     aligned = (now_ts // tf_seconds) * tf_seconds
#     return aligned


# def filter_closed_candles(df: pd.DataFrame, tf_seconds: int) -> pd.DataFrame:
#     now_ts = int(datetime.now(tz=timezone.utc).timestamp())
#     return df[df.index.astype(int) + tf_seconds <= now_ts]


# async def fetch_historical_candles(symbol: str, resolution: str, start: int, end: int, semaphore: asyncio.Semaphore) -> pd.DataFrame:
#     url = 'https://api.india.delta.exchange/v2/history/candles'
#     params = {'symbol': symbol, 'resolution': resolution, 'start': start, 'end': end}
#     headers = {'Accept': 'application/json'}
#     async with semaphore:
#         async with httpx.AsyncClient() as client:
#             try:
#                 response = await client.get(url, params=params, headers=headers, timeout=30.0)
#                 response.raise_for_status()
#                 data = response.json().get('result', [])
#                 await asyncio.sleep(0.1)
#             except (httpx.HTTPStatusError, httpx.RequestError) as exc:
#                 print(f"Error fetching candles for {symbol} {resolution}: {exc}")
#                 return pd.DataFrame()
#     if not data:
#         print(f"No data received for {symbol} {resolution} from {start} to {end}")
#         return pd.DataFrame()
#     df = pd.DataFrame(data, columns=['time', 'open', 'high', 'low', 'close', 'volume'])
#     df.set_index('time', inplace=True)
#     df.index = df.index.astype(int)

#     price_cols = ['open', 'high', 'low', 'close']
#     df = df[df['volume'] > 0]
#     df = df[(df[price_cols] > 0).all(axis=1)]
#     for col in price_cols:
#         if not df.empty:
#             median = df[col].median()
#             mad = (df[col] - median).abs().median()
#             if mad > 0:
#                 df = df[(df[col] - median).abs() < (10 * mad)]
#     return df


# async def initial_bulk_fetch(symbol, timeframes, semaphore):
#     results = {}
#     for tf in timeframes:
#         tf_sec = _timeframe_to_seconds(tf)
#         end = get_aligned_time(tf_sec)
#         start = end - 2000 * tf_sec
#         now = int(datetime.now(tz=timezone.utc).timestamp())
#         if end > now:
#             end = now - 60
#         if start < 0:
#             start = 1
#         df = await fetch_historical_candles(symbol, tf, start, end, semaphore)
#         df = filter_closed_candles(df, tf_sec)
#         results[tf] = df.sort_index()
#         print(f"Total candles fetched for {symbol} {tf}: {len(df)}")
#     return results


# def tolerantly_match_candles(df1, df2):
#     if len(df1) != len(df2):
#         return False
#     if not all(df1.index == df2.index):
#         return False
#     close_diff = (df1['close'] - df2['close']).abs()
#     return all(close_diff <= 0.01)


# async def incremental_update_loop(symbol: str, timeframe: str, candle_df: pd.DataFrame, semaphore: asyncio.Semaphore):
#     tf_seconds = _timeframe_to_seconds(timeframe)

#     while True:
#         try:
#             aligned_end = get_aligned_time(tf_seconds)
#             fetch_size = 10
#             start_time = aligned_end - fetch_size * tf_seconds
#             end_time = aligned_end

#             new_candles = await fetch_historical_candles(symbol, timeframe, start_time, end_time, semaphore)
#             new_candles = filter_closed_candles(new_candles, tf_seconds)

#             if new_candles.empty:
#                 print(f"[{symbol} {timeframe}] Incremental fetch: no new candles")
#             else:
#                 cached = candle_df
#                 max_shift = min(fetch_size, len(new_candles), len(cached))

#                 aligned_idx = None
#                 for shift in range(max_shift):
#                     cached_slice = cached.iloc[-(max_shift - shift):]
#                     new_slice = new_candles.iloc[shift:shift + len(cached_slice)]

#                     if tolerantly_match_candles(cached_slice, new_slice):
#                         aligned_idx = shift
#                         break

#                 if aligned_idx is None:
#                     print(f"[{symbol} {timeframe}] Warning: no alignment found!")
#                     aligned_idx = 0

#                 candles_to_add = new_candles.iloc[aligned_idx:]
#                 combined_df = pd.concat([cached, candles_to_add])
#                 combined_df = combined_df[~combined_df.index.duplicated(keep='last')]
#                 candle_df = combined_df.sort_index()

#                 print(f"[{symbol} {timeframe}] Incremental fetch: {len(candles_to_add)} candles added after alignment")

#             next_fetch_time = aligned_end + tf_seconds
#             sleep_duration = max(0, next_fetch_time - int(time.time()))
#             await asyncio.sleep(sleep_duration)

#         except Exception as e:
#             print(f"Error in incremental update loop for {symbol} {timeframe}: {e}")
#             await asyncio.sleep(tf_seconds)


# async def main():
#     semaphore = asyncio.Semaphore(5)
#     symbol = "BTCUSD"
#     timeframes = ["1m", "5m", "15m", "1h", "4h", "1d"]

#     candle_data = await initial_bulk_fetch(symbol, timeframes, semaphore)

#     tasks = []
#     for tf in timeframes:
#         df = candle_data.get(tf, pd.DataFrame())
#         task = asyncio.create_task(incremental_update_loop(symbol, tf, df, semaphore))
#         tasks.append(task)

#     await asyncio.gather(*tasks)


# if __name__ == '__main__':
#     asyncio.run(main())

# new logic which strat to find alignment from 1 and go the previous candles 

# import asyncio
# import pandas as pd
# import httpx
# import time
# from datetime import datetime, timezone


# def _timeframe_to_seconds(tf: str) -> int:
#     tf = tf.lower().strip()
#     if tf.endswith('s'):
#         return int(tf[:-1])
#     elif tf.endswith('m'):
#         return int(tf[:-1]) * 60
#     elif tf.endswith('h'):
#         return int(tf[:-1]) * 3600
#     elif tf.endswith('d'):
#         return int(tf[:-1]) * 86400
#     elif tf.endswith('w'):
#         return int(tf[:-1]) * 604800
#     else:
#         try:
#             return int(tf) * 60
#         except Exception:
#             raise ValueError(f"Invalid timeframe format '{tf}'")


# def get_aligned_time(tf_seconds: int, ts: int = None) -> int:
#     now_ts = ts or int(datetime.now(tz=timezone.utc).timestamp())
#     aligned = (now_ts // tf_seconds) * tf_seconds
#     return aligned


# def filter_closed_candles(df: pd.DataFrame, tf_seconds: int) -> pd.DataFrame:
#     now_ts = int(datetime.now(tz=timezone.utc).timestamp())
#     return df[df.index.astype(int) + tf_seconds <= now_ts]


# async def fetch_historical_candles(symbol: str, resolution: str, start: int, end: int, semaphore: asyncio.Semaphore) -> pd.DataFrame:
#     url = 'https://api.india.delta.exchange/v2/history/candles'
#     params = {'symbol': symbol, 'resolution': resolution, 'start': start, 'end': end}
#     headers = {'Accept': 'application/json'}
#     async with semaphore:
#         async with httpx.AsyncClient() as client:
#             try:
#                 response = await client.get(url, params=params, headers=headers, timeout=30.0)
#                 response.raise_for_status()
#                 data = response.json().get('result', [])
#                 await asyncio.sleep(0.1)
#             except (httpx.HTTPStatusError, httpx.RequestError) as exc:
#                 print(f"Error fetching candles for {symbol} {resolution}: {exc}")
#                 return pd.DataFrame()
#     if not data:
#         print(f"No data received for {symbol} {resolution} from {start} to {end}")
#         return pd.DataFrame()
#     df = pd.DataFrame(data, columns=['time', 'open', 'high', 'low', 'close', 'volume'])
#     df.set_index('time', inplace=True)
#     df.index = df.index.astype(int)

#     price_cols = ['open', 'high', 'low', 'close']
#     df = df[df['volume'] > 0]
#     df = df[(df[price_cols] > 0).all(axis=1)]
#     for col in price_cols:
#         if not df.empty:
#             median = df[col].median()
#             mad = (df[col] - median).abs().median()
#             if mad > 0:
#                 df = df[(df[col] - median).abs() < (10 * mad)]
#     return df


# async def initial_bulk_fetch(symbol, timeframes, semaphore):
#     results = {}
#     for tf in timeframes:
#         tf_sec = _timeframe_to_seconds(tf)
#         end = get_aligned_time(tf_sec)
#         start = end - 2000 * tf_sec
#         now = int(datetime.now(tz=timezone.utc).timestamp())
#         if end > now:
#             end = now - 60
#         if start < 0:
#             start = 1
#         df = await fetch_historical_candles(symbol, tf, start, end, semaphore)
#         df = filter_closed_candles(df, tf_sec)
#         results[tf] = df.sort_index()
#         print(f"Total candles fetched for {symbol} {tf}: {len(df)}")
#     return results


# def tolerantly_match_candles(df1, df2):
#     if len(df1) != len(df2):
#         return False
#     if not all(df1.index == df2.index):
#         return False
#     close_diff = (df1['close'] - df2['close']).abs()
#     return all(close_diff <= 0.01)


# async def incremental_update_loop(symbol: str, timeframe: str, candle_data_dict, semaphore: asyncio.Semaphore):
#     tf_seconds = _timeframe_to_seconds(timeframe)
#     max_fetch_size = 10
#     aligned_idx = None  # Reset alignment index

#     while True:
#         try:
#             aligned_end = get_aligned_time(tf_seconds)

#             # Dynamically adjust fetch size to find alignment if not yet found
#             if aligned_idx is None:
#                 fetch_size = 1
#                 alignment_found = False

#                 while fetch_size <= max_fetch_size and not alignment_found:
#                     start_time = aligned_end - fetch_size * tf_seconds
#                     end_time = aligned_end

#                     new_candles = await fetch_historical_candles(symbol, timeframe, start_time, end_time, semaphore)
#                     new_candles = filter_closed_candles(new_candles, tf_seconds)

#                     if new_candles.empty:
#                         print(f"[{symbol} {timeframe}] Incremental fetch: no candles for size {fetch_size}")
#                         fetch_size += 1
#                         continue

#                     cached = candle_data_dict[timeframe]
#                     max_shift = min(fetch_size, len(new_candles), len(cached))

#                     for shift in range(max_shift):
#                         cached_slice = cached.iloc[-(max_shift - shift):]
#                         new_slice = new_candles.iloc[shift:shift + len(cached_slice)]

#                         if tolerantly_match_candles(cached_slice, new_slice):
#                             aligned_idx = shift
#                             alignment_found = True
#                             break

#                     if not alignment_found:
#                         fetch_size += 1

#                 if not alignment_found:
#                     print(f"[{symbol} {timeframe}] Warning: no alignment found with max window {max_fetch_size}, using full fetch")
#                     aligned_idx = 0

#                 candles_to_add = new_candles.iloc[aligned_idx:]
#                 combined_df = pd.concat([cached, candles_to_add])
#                 combined_df = combined_df[~combined_df.index.duplicated(keep='last')]
#                 candle_data_dict[timeframe] = combined_df.sort_index()

#                 print(f"[{symbol} {timeframe}] Incremental fetch: {len(candles_to_add)} candles added after alignment")

#             else:
#                 # Alignment found, fetch only the newest single candle
#                 start_time = aligned_end
#                 end_time = aligned_end + tf_seconds

#                 new_candles = await fetch_historical_candles(symbol, timeframe, start_time, end_time, semaphore)
#                 new_candles = filter_closed_candles(new_candles, tf_seconds)

#                 if not new_candles.empty:
#                     combined_df = pd.concat([candle_data_dict[timeframe], new_candles])
#                     combined_df = combined_df[~combined_df.index.duplicated(keep='last')]
#                     candle_data_dict[timeframe] = combined_df.sort_index()
#                     print(f"[{symbol} {timeframe}] Incremental fetch: 1 new candle added")
#                 else:
#                     print(f"[{symbol} {timeframe}] Incremental fetch: no new candle yet")

#             next_fetch_time = aligned_end + tf_seconds
#             sleep_duration = max(0, next_fetch_time - int(time.time()))
#             await asyncio.sleep(sleep_duration)

#         except Exception as e:
#             print(f"Error in incremental update loop for {symbol} {timeframe}: {e}")
#             await asyncio.sleep(tf_seconds)


# async def main():
#     semaphore = asyncio.Semaphore(5)
#     symbol = "BTCUSD"
#     timeframes = ["1m", "5m", "15m", "1h", "4h", "1d"]

#     candle_data_dict = await initial_bulk_fetch(symbol, timeframes, semaphore)

#     tasks = []
#     for tf in timeframes:
#         task = asyncio.create_task(incremental_update_loop(symbol, tf, candle_data_dict, semaphore))
#         tasks.append(task)

#     await asyncio.gather(*tasks)


# if __name__ == '__main__':
#     asyncio.run(main())

#  new update i applied the filter which shows me that only fully completed candle and also align with it
import asyncio
import pandas as pd
import httpx
import time
from datetime import datetime, timezone


def _timeframe_to_seconds(tf: str) -> int:
    tf = tf.lower().strip()
    if tf.endswith('s'):
        return int(tf[:-1])
    elif tf.endswith('m'):
        return int(tf[:-1]) * 60
    elif tf.endswith('h'):
        return int(tf[:-1]) * 3600
    elif tf.endswith('d'):
        return int(tf[:-1]) * 86400
    elif tf.endswith('w'):
        return int(tf[:-1]) * 604800
    else:
        try:
            return int(tf) * 60
        except Exception:
            raise ValueError(f"Invalid timeframe format '{tf}'")


def get_aligned_time(tf_seconds: int, ts: int = None) -> int:
    now_ts = ts or int(datetime.now(tz=timezone.utc).timestamp())
    aligned = (now_ts // tf_seconds) * tf_seconds
    return aligned


# Filter DataFrame to include only fully closed candles before the current candle period
def filter_only_closed_candles(df: pd.DataFrame, tf_seconds: int) -> pd.DataFrame:
    now_ts = int(datetime.now(tz=timezone.utc).timestamp())
    # Only include candles with close (timestamp + tf_seconds) less or equal to current time
    closed_candles = df[df.index.astype(int) + tf_seconds <= now_ts]
    return closed_candles


async def fetch_historical_candles(symbol: str, resolution: str, start: int, end: int, semaphore: asyncio.Semaphore) -> pd.DataFrame:
    url = 'https://api.india.delta.exchange/v2/history/candles'
    params = {'symbol': symbol, 'resolution': resolution, 'start': start, 'end': end}
    headers = {'Accept': 'application/json'}
    async with semaphore:
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(url, params=params, headers=headers, timeout=30.0)
                response.raise_for_status()
                data = response.json().get('result', [])
                await asyncio.sleep(0.1)
            except (httpx.HTTPStatusError, httpx.RequestError) as exc:
                print(f"Error fetching candles for {symbol} {resolution}: {exc}")
                return pd.DataFrame()
    if not data:
        print(f"No data received for {symbol} {resolution} from {start} to {end}")
        return pd.DataFrame()
    df = pd.DataFrame(data, columns=['time', 'open', 'high', 'low', 'close', 'volume'])
    df.set_index('time', inplace=True)
    df.index = df.index.astype(int)

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


async def initial_bulk_fetch(symbol, timeframes, semaphore):
    results = {}
    for tf in timeframes:
        tf_sec = _timeframe_to_seconds(tf)
        end = get_aligned_time(tf_sec)
        start = end - 2000 * tf_sec
        now = int(datetime.now(tz=timezone.utc).timestamp())
        if end > now:
            end = now - 60
        if start < 0:
            start = 1
        df = await fetch_historical_candles(symbol, tf, start, end, semaphore)
        df = filter_only_closed_candles(df, tf_sec)
        results[tf] = df.sort_index()
        print(f"Total candles fetched for {symbol} {tf}: {len(df)}")
    return results


def tolerantly_match_candles(df1, df2):
    if len(df1) != len(df2):
        return False
    if not all(df1.index == df2.index):
        return False
    close_diff = (df1['close'] - df2['close']).abs()
    return all(close_diff <= 0.01)


async def incremental_update_loop(symbol: str, timeframe: str, candle_data_dict, semaphore: asyncio.Semaphore):
    tf_seconds = _timeframe_to_seconds(timeframe)
    max_fetch_size = 10
    aligned_idx = None  # Reset alignment index

    while True:
        try:
            aligned_end = get_aligned_time(tf_seconds)

            # Dynamically adjust fetch size to find alignment if not yet found
            if aligned_idx is None:
                fetch_size = 1
                alignment_found = False

                while fetch_size <= max_fetch_size and not alignment_found:
                    start_time = aligned_end - fetch_size * tf_seconds
                    end_time = aligned_end

                    new_candles = await fetch_historical_candles(symbol, timeframe, start_time, end_time, semaphore)
                    new_candles = filter_only_closed_candles(new_candles, tf_seconds)

                    if new_candles.empty:
                        print(f"[{symbol} {timeframe}] Incremental fetch: no candles for size {fetch_size}")
                        fetch_size += 1
                        continue

                    cached = candle_data_dict[timeframe]
                    max_shift = min(fetch_size, len(new_candles), len(cached))

                    for shift in range(max_shift):
                        cached_slice = cached.iloc[-(max_shift - shift):]
                        new_slice = new_candles.iloc[shift:shift + len(cached_slice)]

                        if tolerantly_match_candles(cached_slice, new_slice):
                            aligned_idx = shift
                            alignment_found = True
                            break

                    if not alignment_found:
                        fetch_size += 1

                if not alignment_found:
                    print(f"[{symbol} {timeframe}] Warning: no alignment found with max window {max_fetch_size}, using full fetch")
                    aligned_idx = 0

                candles_to_add = new_candles.iloc[aligned_idx:]
                combined_df = pd.concat([cached, candles_to_add])
                combined_df = combined_df[~combined_df.index.duplicated(keep='last')]
                candle_data_dict[timeframe] = combined_df.sort_index()

                print(f"[{symbol} {timeframe}] Incremental fetch: {len(candles_to_add)} candles added after alignment")

            else:
                # Alignment found, fetch only the newest single **previously closed** candle
                start_time = aligned_end - tf_seconds
                end_time = aligned_end

                new_candles = await fetch_historical_candles(symbol, timeframe, start_time, end_time, semaphore)
                new_candles = filter_only_closed_candles(new_candles, tf_seconds)

                if not new_candles.empty:
                    print(f"[{symbol} {timeframe}] New previously closed candle details:\n{new_candles}")
                    combined_df = pd.concat([candle_data_dict[timeframe], new_candles])
                    combined_df = combined_df[~combined_df.index.duplicated(keep='last')]
                    candle_data_dict[timeframe] = combined_df.sort_index()
                    print(f"[{symbol} {timeframe}] Incremental fetch: 1 new previously closed candle added")
                else:
                    print(f"[{symbol} {timeframe}] Incremental fetch: no new closed candle yet")

            next_fetch_time = aligned_end + tf_seconds
            sleep_duration = max(0, next_fetch_time - int(time.time()))
            await asyncio.sleep(sleep_duration)

        except Exception as e:
            print(f"Error in incremental update loop for {symbol} {timeframe}: {e}")
            await asyncio.sleep(tf_seconds)


async def main():
    semaphore = asyncio.Semaphore(5)
    symbol = "BTCUSD"
    timeframes = ["1m", "5m", "15m", "1h", "4h", "1d"]

    candle_data_dict = await initial_bulk_fetch(symbol, timeframes, semaphore)

    tasks = []
    for tf in timeframes:
        task = asyncio.create_task(incremental_update_loop(symbol, tf, candle_data_dict, semaphore))
        tasks.append(task)

    await asyncio.gather(*tasks)


if __name__ == '__main__':
    asyncio.run(main())
