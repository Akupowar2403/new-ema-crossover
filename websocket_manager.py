import pandas as pd
import helpers # We'll reuse our helper functions
import asyncio
import websockets
import hmac
import hashlib
import time
import json
import asyncio
from typing import Dict, Tuple

import helpers
import config

# --- Config ---
WEBSOCKET_URL = "wss://socket.india.delta.exchange"
API_KEY = '2gtuz8LLl19ezKjYlvApsqv7kK6UYI'
API_SECRET = 'aehICdR8xRrK8wjFinqblJvM5ljXV8vHwH6sgasyMn0wF9AJP4A6fFPt6qdT'


class CandleManager:
    def __init__(self, symbol: str, timeframe: str, manager):
        self.symbol = symbol
        self.timeframe = timeframe
        self.manager = manager # Store the connection manager
        self.candles_df = pd.DataFrame(columns=['open', 'high', 'low', 'close', 'volume'])
        self.last_signal = {"status": "N/A", "bars_since": None}
        self.last_candle_start_time = None

    async def initialize_history(self):
        now = int(time.time())
        print(f"[{self.symbol}-{self.timeframe}] Fetching historical candles...")
        self.candles_df = await helpers.fetch_historical_candles(self.symbol, self.timeframe, 1, now)
        if not self.candles_df.empty:
            self.last_candle_start_time = self.candles_df.index[-1].timestamp()
        print(f"[{self.symbol}-{self.timeframe}] Fetched {len(self.candles_df)} candles.")

    # --- [ UPDATED ] ---
    # This function is now async
    async def process_live_candle(self, msg: dict):
        ts_sec = msg.get('candle_start_time') // 1_000_000
        candle_data = {
            'open': float(msg['open']), 'high': float(msg['high']),
            'low': float(msg['low']), 'close': float(msg['close']),
            'volume': float(msg['volume'])
        }
        candle_timestamp = pd.to_datetime(ts_sec, unit='s')
        self.candles_df.loc[candle_timestamp] = candle_data

        if self.last_candle_start_time is not None and ts_sec > self.last_candle_start_time:
            df_for_analysis = self.candles_df.iloc[:-1].copy()
            status = helpers.check_ema_crossover_signal(df_for_analysis)
            bars_since = helpers.get_bars_since_last_signal(df_for_analysis)
            new_signal = {"status": status, "bars_since": bars_since}

            if new_signal != self.last_signal:
                self.last_signal = new_signal
                
                # --- [ THE BRIDGE ] ---
                # Instead of printing, we now broadcast the new signal to all connected browsers.
                payload = {
                    "type": "new_signal",
                    "symbol": self.symbol,
                    "timeframe": self.timeframe,
                    "signal": self.last_signal
                }
                await self.manager.broadcast(json.dumps(payload))
                print(f"BROADCASTED new signal for {self.symbol}-{self.timeframe}: {self.last_signal}")

        self.last_candle_start_time = ts_sec


# Type hint for our dictionary of managers
CandleManagers = Dict[Tuple[str, str], CandleManager]


def generate_signature(secret, message):
    """Generates the required authentication signature."""
    message = bytes(message, 'utf-8')
    secret = bytes(secret, 'utf-8')
    return hmac.new(secret, message, hashlib.sha256).hexdigest()

async def start_websocket_client(manager):
    uri = WEBSOCKET_URL
    while True: # Add a loop for auto-reconnection
        try:
            async with websockets.connect(uri) as ws:
                print("WebSocket connected. Authenticating...")
                timestamp = str(int(time.time()))
                signature = generate_signature(API_SECRET, 'GET' + timestamp + '/live')
                await ws.send(json.dumps({
                    "type": "auth",
                    "payload": {"api-key": API_KEY, "signature": signature, "timestamp": timestamp}
                }))
                print(f"Authentication response: {await ws.recv()}")

                watchlist = helpers.get_current_watchlist()
                if not watchlist:
                    print("Watchlist is empty. WebSocket client will not subscribe.")
                    await asyncio.sleep(60) # Wait before checking again
                    continue

                managers: CandleManagers = {}
                init_tasks = []
                for symbol in watchlist:
                    for tf in config.TIMEFRAMES:
                        key = (symbol, tf)
                        # Pass the manager to each CandleManager instance
                        manager_instance = CandleManager(symbol, tf, manager)
                        managers[key] = manager_instance
                        init_tasks.append(manager_instance.initialize_history())
                
                await asyncio.gather(*init_tasks)
                print("All historical data has been warmed up.")

                channels = [{"name": f"candlestick_{tf}", "symbols": watchlist} for tf in config.TIMEFRAMES]
                await ws.send(json.dumps({"type": "subscribe", "payload": {"channels": channels}}))
                print("Subscribed to live candlestick channels.")

                async for message in ws:
                    msg = json.loads(message)
                    msg_type = msg.get('type', '')
                    if msg_type.startswith('candlestick_'):
                        symbol = msg.get('symbol')
                        timeframe = msg_type.replace('candlestick_', '')
                        manager_instance = managers.get((symbol, timeframe))
                        if manager_instance:
                            # Await the async function
                            await manager_instance.process_live_candle(msg)
        except Exception as e:
            print(f"WebSocket client error: {e}. Reconnecting in 30 seconds...")
            await asyncio.sleep(30)