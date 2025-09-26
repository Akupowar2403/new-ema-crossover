import pandas as pd
import helpers 
import asyncio
import websockets
import hmac
import hashlib
import time
import json
import shared_state
import pytz
from typing import Dict, Tuple
from datetime import datetime
from shared_state import websocket_command_queue, candle_managers_state

# --- .env Configuration Loading ---
import os
from dotenv import load_dotenv
load_dotenv()

API_KEY = os.getenv('API_KEY')
API_SECRET = os.getenv('API_SECRET')
TIMEFRAMES_STR = os.getenv('TIMEFRAMES', '1m,15m,1h,4h,1d')
TIMEFRAMES = [tf.strip() for tf in TIMEFRAMES_STR.split(',')]
# ----------------------------------

WEBSOCKET_URL = "wss://socket.india.delta.exchange"

class CandleManager:
    def __init__(self, symbol: str, timeframe: str, manager):
        self.symbol = symbol
        self.timeframe = timeframe
        self.manager = manager
        self.candles_df = pd.DataFrame()
        self.last_signal_state = {}

    async def initialize_history(self, semaphore: asyncio.Semaphore):
        cached_df, cached_state = helpers.load_state_from_redis(self.symbol, self.timeframe)
        now = int(time.time())
        start_time = 1
        if cached_df is not None and not cached_df.empty:
            self.candles_df = cached_df
            self.last_signal_state = cached_state or {}
            last_timestamp = int(self.candles_df.index[-1].timestamp())
            start_time = last_timestamp + 1
            helpers.logger.info(f"[{self.symbol}-{self.timeframe}] Loaded from cache. Fetching delta.")
        if start_time < now:
            new_candles_df = await helpers.fetch_historical_candles(self.symbol, self.timeframe, start_time, now, semaphore)
            if not new_candles_df.empty:
                self.candles_df = pd.concat([self.candles_df, new_candles_df])
                self.candles_df = self.candles_df[~self.candles_df.index.duplicated(keep='last')]
                self.candles_df.sort_index(inplace=True)
        if not self.candles_df.empty:
            self.last_signal_state = helpers.analyze_ema_state(self.candles_df)
            helpers.save_state_to_redis(self.symbol, self.timeframe, self.candles_df, self.last_signal_state)
        helpers.logger.info(f"[{self.symbol}-{self.timeframe}] Initialized with status: {self.last_signal_state.get('status')}")

    async def process_live_candle(self, msg: dict):
        ts_sec = msg.get('candle_start_time') // 1_000_000
        candle_timestamp = pd.to_datetime(ts_sec, unit='s').tz_localize('UTC')
        self.candles_df.loc[candle_timestamp] = {
            'open': float(msg['open']), 'high': float(msg['high']),
            'low': float(msg['low']), 'close': float(msg['close']),
            'volume': float(msg['volume'])
        }
        
        new_signal_state = helpers.analyze_ema_state(self.candles_df)
        
        old_status = self.last_signal_state.get('status', 'N/A')
        new_status = new_signal_state.get('status', 'N/A')

        if new_status != old_status and new_status != 'N/A':
            helpers.logger.info(f"ALERT: New confirmed crossover for {self.symbol}-{self.timeframe}: {new_status}")
            
            crossover_timestamp = None
            if new_signal_state.get("bars_since") == 0:
                if len(self.candles_df.index) >= 2:
                    crossover_time = self.candles_df.index[-2]
                    crossover_timestamp = int(crossover_time.timestamp())

            if shared_state.alert_service:
                crossover_time_str = "N/A"
                if crossover_timestamp:
                    ist_tz = pytz.timezone('Asia/Kolkata')
                    utc_time = datetime.fromtimestamp(crossover_timestamp, tz=pytz.utc)
                    ist_time = utc_time.astimezone(ist_tz)
                    crossover_time_str = ist_time.strftime('%b %d, %Y %I:%M %p %Z')
                telegram_message = (
                    f"📈 *New Crossover Alert* 📈\n\n"
                    f"*Symbol:* `{self.symbol}`\n"
                    f"*Timeframe:* `{self.timeframe}`\n"
                    f"*Status:* *{new_status}*\n"
                    f"*Crossover Time:* `{crossover_time_str}`"
                )
                await asyncio.to_thread(
                    shared_state.alert_service.send_signal_alert,
                    telegram_message
                )
            
            alert_payload = {
                "type": "crossover_alert", "symbol": self.symbol, "timeframe": self.timeframe,
                "status": new_status, "crossover_timestamp": crossover_timestamp
            }
            await self.manager.broadcast(json.dumps(alert_payload))
        
        live_update_payload = {
            "type": "live_update",
            "symbol": self.symbol,
            "timeframe": self.timeframe,
            "signal": new_signal_state
        }
        await self.manager.broadcast(json.dumps(live_update_payload))

        helpers.save_state_to_redis(self.symbol, self.timeframe, self.candles_df, new_signal_state)
        
        self.last_signal_state = new_signal_state

def generate_signature(secret, message):
    return hmac.new(bytes(secret, 'utf-8'), bytes(message, 'utf-8'), hashlib.sha256).hexdigest()

async def handle_commands(ws, manager, semaphore: asyncio.Semaphore):
    while True:
        command, symbol = await websocket_command_queue.get()
        helpers.logger.info(f"Received command from API: {command} {symbol}")
        channels = [{"name": f"candlestick_{tf}", "symbols": [symbol]} for tf in TIMEFRAMES]
        
        try: # <--- ADDED: Start of the error handling block
            if command == 'subscribe':
                await ws.send(json.dumps({"type": "subscribe", "payload": {"channels": channels}}))
                for tf in TIMEFRAMES:
                    key = (symbol, tf)
                    if key not in candle_managers_state:
                        manager_instance = CandleManager(symbol, tf, manager)
                        candle_managers_state[key] = manager_instance
                        asyncio.create_task(manager_instance.initialize_history(semaphore))
            
            elif command == 'unsubscribe':
                await ws.send(json.dumps({"type": "unsubscribe", "payload": {"channels": channels}}))
                for tf in TIMEFRAMES:
                    if (key := (symbol, tf)) in candle_managers_state:
                        del candle_managers_state[key]

        except websockets.exceptions.ConnectionClosedOK: # <--- ADDED: Catch the specific error
            helpers.logger.warning(f"Could not send '{command}' command; WebSocket connection was closing.")
            # The connection is gone, so we break the loop to end this task safely.
            break # <--- ADDED: Safely exit the loop

        except Exception as e: # <--- ADDED: Catch any other potential errors
            helpers.logger.error(f"An unexpected error occurred in handle_commands: {e}")
            break # <--- ADDED: Safely exit the loop
            
        websocket_command_queue.task_done()

async def start_websocket_client(manager, semaphore: asyncio.Semaphore):
    uri = WEBSOCKET_URL
    while True: 
        try:
            async with websockets.connect(uri) as ws:
                helpers.logger.info("WebSocket connected. Authenticating...")
                timestamp = str(int(time.time()))
                signature = generate_signature(API_SECRET, 'GET' + timestamp + '/live')
                await ws.send(json.dumps({
                    "type": "auth",
                    "payload": {"api-key": API_KEY, "signature": signature, "timestamp": timestamp}
                }))
                auth_resp = await ws.recv()
                helpers.logger.info(f"Authentication response: {auth_resp}")

                candle_managers_state.clear()
                command_handler_task = asyncio.create_task(handle_commands(ws, manager, semaphore))

                watchlist = helpers.get_current_watchlist()
                if watchlist:
                    init_tasks = []
                    for symbol in watchlist:
                        for tf in TIMEFRAMES:
                            manager_instance = CandleManager(symbol, tf, manager)
                            candle_managers_state[(symbol, tf)] = manager_instance
                            init_tasks.append(manager_instance.initialize_history(semaphore))
                    
                    await asyncio.gather(*init_tasks)
                    helpers.logger.info("All historical data has been warmed up.")
                    
                    channels = [{"name": f"candlestick_{tf}", "symbols": watchlist} for tf in TIMEFRAMES]
                    await ws.send(json.dumps({"type": "subscribe", "payload": {"channels": channels}}))
                    helpers.logger.info("Subscribed to initial watchlist channels.")

                async for message in ws:
                    msg = json.loads(message)
                    if (msg_type := msg.get('type', '')).startswith('candlestick_'):
                        symbol, timeframe = msg.get('symbol'), msg_type.replace('candlestick_', '')
                        if manager_instance := candle_managers_state.get((symbol, timeframe)):
                            await manager_instance.process_live_candle(msg)
                
                command_handler_task.cancel()
        except Exception as e:
            helpers.logger.error(f"WebSocket client error: {e}. Reconnecting in 30 seconds...")
            await asyncio.sleep(30)