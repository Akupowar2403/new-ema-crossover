import requests
import pandas as pd
import websocket
import hashlib
import hmac
import json
import time
import threading
import logging
import logging.handlers
from datetime import datetime, timezone
import asyncio

# Import the strategy function
from strategy import check_ema_crossover_signal

# Import TelegramBotApp here to start in background
from telegram_bot import TelegramBotApp
from telegram_bot import AlertService

# --------------- Logging Setup ---------------

LOG_FILE = "app.log"
root_logger = logging.getLogger()
root_logger.setLevel(logging.DEBUG)

# Rotating file handler for all logs
file_handler = logging.handlers.RotatingFileHandler(
    LOG_FILE, maxBytes=5*1024*1024, backupCount=5, encoding='utf-8'
)
file_handler.setLevel(logging.DEBUG)
file_format = logging.Formatter('%(asctime)s | %(levelname)s | %(name)s | %(message)s')
file_handler.setFormatter(file_format)
root_logger.addHandler(file_handler)

# Console handler only for strategy logger (EMA debug logs)
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.DEBUG)
console_format = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
console_handler.setFormatter(console_format)

ema_logger = logging.getLogger('strategy')  # Make sure this matches your strategy.py logger name
ema_logger.setLevel(logging.DEBUG)
ema_logger.addHandler(console_handler)

# Suppress noisy logs on console but keep in file
for noisy_logger_name in ['httpx', 'websocket', 'telegram', 'telegram.ext']:
    logger = logging.getLogger(noisy_logger_name)
    logger.setLevel(logging.WARNING)

# ---------------------------------------------

# Config & globals
WEBSOCKET_URL = "wss://socket.india.delta.exchange"
API_KEY = '2gtuz8LLl19ezKjYlvApsqv7kK6UYI'
API_SECRET = 'aehICdR8xRrK8wjFinqblJvM5ljXV8vHwH6sgasyMn0wF9AJP4A6fFPt6qdT'

symbol = 'BTCUSD'
resolution = '1m'
candles_df = pd.DataFrame()  # Global DataFrame to hold candles
last_candle_start_time = None  # Track last processed candle start time

# ---- NEW GLOBAL VARIABLE to track last sent signal ---
last_signal = None  

# Fetch historical candles
def fetch_historical_candles(symbol, resolution, start, end):
    url = f'https://api.india.delta.exchange/v2/history/candles'
    params = {
        'symbol': symbol,
        'resolution': resolution,
        'start': start,
        'end': end
    }
    headers = {'Accept': 'application/json'}

    response = requests.get(url, params=params, headers=headers)
    data = response.json().get('result', [])

    if not data:
        print("No historical candle data received")
        return pd.DataFrame()

    df = pd.DataFrame(data, columns=['time', 'open', 'high', 'low', 'close', 'volume'])
    df.set_index('time', inplace=True)
    return df

def generate_signature(secret, message):
    message = bytes(message, 'utf-8')
    secret = bytes(secret, 'utf-8')
    return hmac.new(secret, message, hashlib.sha256).hexdigest()

def send_authentication(ws):
    method = 'GET'
    timestamp = str(int(time.time()))
    path = '/live'
    message = method + timestamp + path
    signature = generate_signature(API_SECRET, message)
    ws.send(json.dumps({
        "type": "auth",
        "payload": {
            "api-key": API_KEY,
            "signature": signature,
            "timestamp": timestamp
        }
    }))

def on_open(ws):
    print("WebSocket opened")
    send_authentication(ws)

def subscribe(ws, channel, symbols):
    ws.send(json.dumps({
        "type": "subscribe",
        "payload": {
            "channels": [
                {"name": channel, "symbols": symbols}
            ]
        }
    }))

alert_service = AlertService()

def on_message(ws, message):
    global candles_df, last_candle_start_time, last_signal
    msg = json.loads(message)

    if msg.get('type') == 'success' and msg.get('message') == 'Authenticated':
        print("Authenticated successfully")
        subscribe(ws, f'candlestick_{resolution}', [symbol])

    elif msg.get('type') == f'candlestick_{resolution}':
        candle_start_time = msg.get('candle_start_time')  # in microseconds
        if candle_start_time:
            ts_sec = candle_start_time // 1_000_000  # Convert to seconds

            candle_data = {
                'open': msg['open'],
                'high': msg['high'],
                'low': msg['low'],
                'close': msg['close'],
                'volume': msg['volume']
            }

            # Update or append the current candle data
            if ts_sec in candles_df.index:
                candles_df.loc[ts_sec] = candle_data
            else:
                new_df = pd.DataFrame([candle_data], index=[ts_sec])
                candles_df = pd.concat([candles_df, new_df])
                candles_df.sort_index(inplace=True)

            # Run strategy only when a candle completes (on new candle start)
            if last_candle_start_time is not None and candle_start_time != last_candle_start_time:
                signal = check_ema_crossover_signal(candles_df, short_period=9, long_period=20)
                if signal and signal != last_signal:
                    try:
                        alert_message = (
                            f"🚨 Trade Signal Alert 🚨\n"
                            f"Symbol: {symbol}\n"
                            f"Time: {datetime.fromtimestamp(ts_sec).strftime('%Y-%m-%d %H:%M:%S')}\n"
                            f"Resolution: {resolution}\n"
                            f"Signal Triggered: {signal}"
                        )
                        alert_service.send_signal_alert(alert_message)
                        print(f"Sent alert: {alert_message}")
                        last_signal = signal
                    except Exception as e:
                        print(f"Error sending alert: {e}")
                elif not signal:
                    last_signal = None  # Reset state for future crossovers

            last_candle_start_time = candle_start_time
        else:
            print("candlestick message missing candle_start_time:", msg)
    else:
        print(msg)


def on_error(ws, error):
    print(f"WebSocket error: {error}")

def on_close(ws, close_status_code, close_msg):
    print(f"WebSocket closed: {close_status_code} - {close_msg}")

def run_telegram_bot():
    asyncio.set_event_loop(asyncio.new_event_loop())
    bot_app = TelegramBotApp()
    bot_app.run()

if __name__ == "__main__":
    # Start Telegram bot in background thread
    telegram_thread = threading.Thread(target=run_telegram_bot, daemon=True)
    telegram_thread.start()

    now = int(time.time())
    start_time = 1  # Fetch last 7 days of candles

    candles_df = fetch_historical_candles(symbol, resolution, start_time, now)
    print(f"Fetched {len(candles_df)} historical candles")

    ws = websocket.WebSocketApp(
        WEBSOCKET_URL,
        on_message=on_message,
        on_error=on_error,
        on_close=on_close)
    ws.on_open = on_open
    ws.run_forever()
