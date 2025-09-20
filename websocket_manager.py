# websocket_manager.py

import pandas as pd
import helpers 
import asyncio
import websockets
import hmac
import hashlib
import time
import json
from typing import Dict, Tuple
import config
# [NEW] STEP 1: Import the shared queue
from shared_state import websocket_command_queue

API_KEY = '2gtuz8LLl19ezKjYlvApsqv7kK6UYI'
API_SECRET = 'aehICdR8xRrK8wjFinqblJvM5ljXV8vHwH6sgasyMn0wF9AJP4A6fFPt6qdT'

WEBSOCKET_URL = "wss://socket.india.delta.exchange"

# The CandleManager class and generate_signature function remain the same
class CandleManager:
    def __init__(self, symbol: str, timeframe: str, manager):
        self.symbol = symbol
        self.timeframe = timeframe
        self.manager = manager
        self.candles_df = pd.DataFrame()
        self.last_signal_state = {'status': None, 'index': None}

    # It now accepts the semaphore as an argument
    async def initialize_history(self, semaphore: asyncio.Semaphore):
        now = int(time.time())
        print(f"[{self.symbol}-{self.timeframe}] Fetching historical candles...")
        # It now passes the semaphore to the helper function
        self.candles_df = await helpers.fetch_historical_candles(self.symbol, self.timeframe, 1, now, semaphore)
        
        if not self.candles_df.empty:
            self.last_signal_state = helpers.get_ema_signal(self.candles_df, self.last_signal_state)
        print(f"[{self.symbol}-{self.timeframe}] Initial state: {self.last_signal_state}")

    async def process_live_candle(self, msg: dict):
        ts_sec = msg.get('candle_start_time') // 1_000_000
        candle_data = {
            'open': float(msg['open']), 'high': float(msg['high']),
            'low': float(msg['low']), 'close': float(msg['close']),
            'volume': float(msg['volume'])
        }
        candle_timestamp = pd.to_datetime(ts_sec, unit='s')
        self.candles_df.loc[candle_timestamp] = candle_data
        
        new_signal = helpers.get_ema_signal(self.candles_df, self.last_signal_state)

        if new_signal and new_signal.get('status') != self.last_signal_state.get('status'):
            self.last_signal_state = new_signal
            payload = {
                "type": "new_signal",
                "symbol": self.symbol,
                "timeframe": self.timeframe,
                "signal": self.last_signal_state
            }
            await self.manager.broadcast(json.dumps(payload))
            print(f"BROADCASTED new signal for {self.symbol}-{self.timeframe}: {self.last_signal_state}")


CandleManagers = Dict[Tuple[str, str], CandleManager]

def generate_signature(secret, message):
    message = bytes(message, 'utf-8')
    secret = bytes(secret, 'utf-8')
    return hmac.new(secret, message, hashlib.sha256).hexdigest()

# [NEW] STEP 2: Create a function to handle commands from the queue
async def handle_commands(ws, managers: CandleManagers, manager):
    """Listens to the queue and sends subscribe/unsubscribe messages."""
    while True:
        command, symbol = await websocket_command_queue.get()
        print(f"Received command from API: {command} {symbol}")
        
        channels = [{"name": f"candlestick_{tf}", "symbols": [symbol]} for tf in config.TIMEFRAMES]
        
        if command == 'subscribe':
            await ws.send(json.dumps({"type": "subscribe", "payload": {"channels": channels}}))
            print(f"Sent SUBSCRIBE request for {symbol}")
            
            # Create and initialize new CandleManagers for the new symbol
            for tf in config.TIMEFRAMES:
                key = (symbol, tf)
                if key not in managers:
                    manager_instance = CandleManager(symbol, tf, manager)
                    await manager_instance.initialize_history()
                    managers[key] = manager_instance

        elif command == 'unsubscribe':
            await ws.send(json.dumps({"type": "unsubscribe", "payload": {"channels": channels}}))
            print(f"Sent UNSUBSCRIBE request for {symbol}")
            
            # Remove the CandleManagers to save memory
            for tf in config.TIMEFRAMES:
                key = (symbol, tf)
                if key in managers:
                    del managers[key]
        
        websocket_command_queue.task_done()

async def start_websocket_client(manager, semaphore: asyncio.Semaphore):
    uri = WEBSOCKET_URL
    while True: 
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
                managers: Dict[Tuple[str, str], CandleManager] = {}
                
                if watchlist:
                    init_tasks = []
                    for symbol in watchlist:
                        for tf in config.TIMEFRAMES:
                            key = (symbol, tf)
                            manager_instance = CandleManager(symbol, tf, manager)
                            managers[key] = manager_instance
                            # It now passes the semaphore to the initialize_history task
                            init_tasks.append(manager_instance.initialize_history(semaphore))
                    
                    await asyncio.gather(*init_tasks)
                    print("All historical data has been warmed up.")

                    channels = [{"name": f"candlestick_{tf}", "symbols": watchlist} for tf in config.TIMEFRAMES]
                    await ws.send(json.dumps({"type": "subscribe", "payload": {"channels": channels}}))
                    print("Subscribed to initial watchlist channels.")
                else:
                    print("Watchlist is empty. Ready for dynamic subscriptions.")
                
                async for message in ws:
                    msg = json.loads(message)
                    msg_type = msg.get('type', '')
                    if msg_type.startswith('candlestick_'):
                        symbol = msg.get('symbol')
                        timeframe = msg_type.replace('candlestick_', '')
                        manager_instance = managers.get((symbol, timeframe))
                        if manager_instance:
                            await manager_instance.process_live_candle(msg)
                            
        except Exception as e:
            print(f"WebSocket client error: {e}. Reconnecting in 30 seconds...")
            await asyncio.sleep(30)