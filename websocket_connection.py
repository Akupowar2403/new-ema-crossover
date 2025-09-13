# # import requests
# # headers = {
# #   'Accept': 'application/json'
# # }

# # r = requests.get('https://api.india.delta.exchange/v2/tickers/BTCUSD', params={

# # }, headers = headers)

# # print (r.json())
# import websocket
# import hashlib
# import hmac
# import json
# import time
# import websocket
# import hashlib
# import hmac
# import json
# import time
# import datetime


# # production websocket base url and api keys/secrets
# WEBSOCKET_URL = "wss://socket.india.delta.exchange"
# API_KEY = '6qu5B6CbdjpLFCMgimc6EFPNqBwyYv'
# API_SECRET = 'VosGi1DFf5T0ZTaWIgZ1IboAogQQUAIgYBZUBakguaFRdDjIYbkeHH0dduTS'
# api_key = 'SOCXHh2XbDfJUYAZ317UIg2qjVBNdh'
# api_secret = 'OpJwHMmSOudzjqBK1xr6wcaKaQMzNBnIEodb579VuVMj0ahl8I316V4OTVJy'

# def on_error(ws, error):
#     print(f"Socket Error: {error}")

# def on_close(ws, close_status_code, close_msg):
#     print(f"Socket closed with status: {close_status_code} and message: {close_msg}")

# def on_open(ws):
#     print(f"Socket opened")
#     # api key authentication
#     send_authentication(ws)

# def send_authentication(ws):
#     method = 'GET'
#     timestamp = str(int(time.time()))
#     path = '/live'
#     signature_data = method + timestamp + path
#     signature = generate_signature(API_SECRET, signature_data)
#     ws.send(json.dumps({
#         "type": "auth",
#         "payload": {
#             "api-key": API_KEY,
#             "signature": signature,
#             "timestamp": timestamp
#         }
#     }))

# def generate_signature(secret, message):
#     message = bytes(message, 'utf-8')
#     secret = bytes(secret, 'utf-8')
#     hash = hmac.new(secret, message, hashlib.sha256)
#     return hash.hexdigest()

# def on_message(ws, message):
#     message_json = json.loads(message)
#     # subscribe private channels after successful authentication
#     if message_json['type'] == 'success' and message_json['message'] == 'Authenticated':
#          # subscribe orders channel for order updates for all contracts
#         # subscribe(ws, "orders", ["all"])
#         # subscribe positions channel for position updates for all contracts
#         subscribe(ws, "v2/ticker", ["BTCUSD"])

#     else:
#       print(message_json)

# def subscribe(ws, channel, symbols):
#     payload = {
#         "type": "subscribe",
#         "payload": {
#             "channels": [
#                 {
#                     "name": channel,
#                     "symbols": symbols
#                 }
#             ]
#         }
#     }
#     ws.send(json.dumps(payload))

# if __name__ == "__main__":
#   ws = websocket.WebSocketApp(WEBSOCKET_URL, on_message=on_message, on_error=on_error, on_close=on_close)
#   ws.on_open = on_open
#   ws.run_forever() # runs indefinitely

# --- Global variables to build our candle ---
# --- Global variables to build our candle ---
# RESOLUTION = "1m" # Choose your timeframe: "1m", "5m", "15m", "1h", etc.
# SYMBOLS = ["BTCUSD"] # List of symbols to track
# current_candle_data = {}
# candle_history = []

# def on_error(ws, error):
#     print(f"Socket Error: {error}")

# def on_close(ws, close_status_code, close_msg):
#     print(f"Socket closed: {close_status_code} {close_msg}")

# def on_open(ws):
#     print("Socket opened")
#     send_authentication(ws)

# def send_authentication(ws):
#     method = 'GET'
#     timestamp = str(int(time.time()))
#     path = '/live'
#     signature_data = method + timestamp + path
#     signature = generate_signature(API_SECRET, signature_data)
#     ws.send(json.dumps({
#         "type": "auth",
#         "payload": { "api-key": API_KEY, "signature": signature, "timestamp": timestamp }
#     }))

# def generate_signature(secret, message):
#     message = bytes(message, 'utf-8')
#     secret = bytes(secret, 'utf-8')
#     hash = hmac.new(secret, message, hashlib.sha256)
#     return hash.hexdigest()

# def subscribe(ws, channel, symbols):
#     ws.send(json.dumps({
#         "type": "subscribe",
#         "payload": { "channels": [{ "name": channel, "symbols": symbols }] }
#     }))

# # --- FINAL, SIMPLIFIED on_message function ---
# def on_message(ws, message):
#     try:
#         message_json = json.loads(message)
#         msg_type = message_json.get('type')
#         channel_name = f"candlestick_{RESOLUTION}"

#         if msg_type == 'success' and message_json.get('message') == 'Authenticated':
#             print(f"✅ Authentication successful. Subscribing to {channel_name}...")
#             subscribe(ws, channel_name, SYMBOLS)
#         elif msg_type == 'subscriptions':
#             print(f"✅ Successfully subscribed to channels: {message_json.get('channels')}")
#         elif msg_type == channel_name:
#             process_candle(message_json) # Pass to our updated function
#         else:
#             print(f"ℹ️ Received unhandled message type '{msg_type}'")

#     except Exception as e:
#         print(f"❌ Error processing message: {message} | Exception: {e}")

# # --- UPDATED function with different print statements ---
# # --- CORRECTED function with dynamic print statements ---
# def process_candle(candle_data):
#     """Prints a live update and a final closing message for each candle."""
#     global current_candle_data

#     symbol = candle_data.get('symbol', 'N/A')
#     candle_start_time_s = candle_data['candle_start_time'] / 1000000
#     candle_time = datetime.datetime.fromtimestamp(candle_start_time_s).strftime('%Y-%m-%d %H:%M:%S')

#     # Check if a new candle has started
#     if not current_candle_data or candle_data['candle_start_time'] != current_candle_data.get('candle_start_time'):
#         # If a previous candle exists, print its final closed state
#         if current_candle_data:
#             prev_time = datetime.datetime.fromtimestamp(current_candle_data['candle_start_time'] / 1000000).strftime('%Y-%m-%d %H:%M:%S')
#             print("\n------------------------------------")
#             # FIX: Use the RESOLUTION variable for an accurate message
#             print(f"✅ **Final {RESOLUTION} Candle Closed at {prev_time}**")
#             print(f"   Open:  {current_candle_data['open']}")
#             print(f"   High:  {current_candle_data['high']}")
#             print(f"   Low:   {current_candle_data['low']}")
#             print(f"   Close: {current_candle_data['close']}")
#             print("------------------------------------\n")

#         # Start the new candle
#         # FIX: Use the RESOLUTION variable here too
#         print(f" New {RESOLUTION} Candle for {symbol} started at {candle_time}")

#     # Print the live, in-progress update
#     print(f"\r   🔴 Live Update -> H: {candle_data['high']} | L: {candle_data['low']} | C: {candle_data['close']}", end="")

#     # Update the stored data for the current candle
#     current_candle_data = candle_data


# if __name__ == "__main__":
#     ws = websocket.WebSocketApp(WEBSOCKET_URL, on_message=on_message, on_error=on_error, on_close=on_close)
#     ws.on_open = on_open
#     ws.run_forever()

import websocket
import hashlib
import hmac
import json
import time
import datetime
import os
import pandas as pd
from dotenv import load_dotenv


# production websocket base url and api keys/secrets
WEBSOCKET_URL = "wss://socket.india.delta.exchange"
API_KEY = '6qu5B6CbdjpLFCMgimc6EFPNqBwyYv'
API_SECRET = 'VosGi1DFf5T0ZTaWIgZ1IboAogQQUAIgYBZUBakguaFRdDjIYbkeHH0dduTS'

# --- Securely Load API Keys ---
# Make sure you have a .env file in the same directory with your keys:
# API_KEY="YOUR_API_KEY"
# API_SECRET="YOUR_API_SECRET"
# load_dotenv()
# API_KEY = os.getenv("API_KEY")
# API_SECRET = os.getenv("API_SECRET")
# WEBSOCKET_URL = "wss://socket.india.delta.exchange"

# --- Configuration & Global Variables ---
RESOLUTION = "1m"       # Timeframe: "1m", "5m", "15m", "1h", etc.
SYMBOLS = ["BTCUSD"]    # List of symbols to track
current_candle_data = {} # Stores live data for the current candle
candle_history = []     # Stores the last N closed candles

# -----------------------------------------------------------------------------
# --- WebSocket Event Handlers & Core Functions ---
# -----------------------------------------------------------------------------

def on_error(ws, error):
    print(f"Socket Error: {error}")

def on_close(ws, close_status_code, close_msg):
    print(f"Socket closed: {close_status_code} {close_msg}")

def on_open(ws):
    print("Socket opened")
    send_authentication(ws)

def send_authentication(ws):
    method = 'GET'
    timestamp = str(int(time.time()))
    path = '/live'
    signature_data = method + timestamp + path
    signature = generate_signature(API_SECRET, signature_data)
    ws.send(json.dumps({
        "type": "auth",
        "payload": { "api-key": API_KEY, "signature": signature, "timestamp": timestamp }
    }))

def generate_signature(secret, message):
    message = bytes(message, 'utf-8')
    secret = bytes(secret, 'utf-8')
    hash = hmac.new(secret, message, hashlib.sha256)
    return hash.hexdigest()

def subscribe(ws, channel, symbols):
    ws.send(json.dumps({
        "type": "subscribe",
        "payload": { "channels": [{ "name": channel, "symbols": symbols }] }
    }))

def on_message(ws, message):
    try:
        message_json = json.loads(message)
        msg_type = message_json.get('type')
        channel_name = f"candlestick_{RESOLUTION}"

        if msg_type == 'success' and message_json.get('message') == 'Authenticated':
            print(f"✅ Authentication successful. Subscribing to {channel_name}...")
            subscribe(ws, channel_name, SYMBOLS)
        elif msg_type == 'subscriptions':
            print(f"✅ Successfully subscribed to channels: {message_json.get('channels')}")
        elif msg_type == channel_name:
            process_candle(message_json)
        else:
            print(f"ℹ️  Received unhandled message type '{msg_type}'")

    except Exception as e:
        print(f"❌ Error processing message: {message} | Exception: {e}")

# -----------------------------------------------------------------------------
# --- Data Processing & Strategy Logic ---
# -----------------------------------------------------------------------------

def process_candle(candle_data):
    """Prints live updates, final candle, and triggers the strategy check."""
    global current_candle_data

    # Check if a new candle has started
    if not current_candle_data or candle_data['candle_start_time'] != current_candle_data.get('candle_start_time'):
        # If a previous candle exists, print its final state and run the strategy
        if current_candle_data:
            prev_time = datetime.datetime.fromtimestamp(current_candle_data['candle_start_time'] / 1000000).strftime('%Y-%m-%d %H:%M:%S')
            print("\n------------------------------------")
            print(f"✅ **Final {RESOLUTION} Candle Closed at {prev_time}**")
            print(f"   Open:  {current_candle_data['open']}")
            print(f"   High:  {current_candle_data['high']}")
            print(f"   Low:   {current_candle_data['low']}")
            print(f"   Close: {current_candle_data['close']}")
            print("------------------------------------")

            # RUN YOUR STRATEGY ON THE COMPLETED CANDLE
            run_strategy(current_candle_data)
            print("------------------------------------\n")

        # Start the new candle
        symbol = candle_data.get('symbol', 'N/A')
        candle_time = datetime.datetime.fromtimestamp(candle_data['candle_start_time'] / 1000000).strftime('%Y-%m-%d %H:%M:%S')
        print(f" New {RESOLUTION} Candle for {symbol} started at {candle_time}")

    # Print the live, in-progress update
    print(f"\r   🔴 Live Update -> H: {candle_data['high']} | L: {candle_data['low']} | C: {candle_data['close']}", end="")

    # Update the stored data for the current candle
    current_candle_data = candle_data

def run_strategy(closed_candle):
    """Appends candle to history, converts to DataFrame, and runs the EMA check."""
    global candle_history

    print("📈 **Running Strategy Check...**")
    candle_history.append(closed_candle)

    # Keep the history list from growing forever
    if len(candle_history) > 10: # Store the last 50 candles
        candle_history.pop(0)

    df = pd.DataFrame(candle_history)
    df['close'] = pd.to_numeric(df['close'])

    signal = check_ema_crossover_signal(df)

    if signal == "BUY":
        print("   STRATEGY SIGNAL: BUY ✅")
        # --- PLACE YOUR API CALL TO EXECUTE A BUY ORDER HERE ---
    elif signal == "SELL":
        print("  STRATEGY SIGNAL: SELL ❌")
        # --- PLACE YOUR API CALL TO EXECUTE A SELL ORDER HERE ---
    else:
        print(" STRATEGY SIGNAL: HOLD ⚪")

def check_ema_crossover_signal(df, short_period=5, long_period=9):
    """Returns "BUY", "SELL", or None based on 9 EMA crossing 20 EMA."""
    if len(df) < long_period + 2:
        return None # Not enough data to calculate EMAs and check crossover

    df[f'ema_{short_period}'] = df['close'].ewm(span=short_period, adjust=False).mean()
    df[f'ema_{long_period}'] = df['close'].ewm(span=long_period, adjust=False).mean()

    last_row = df.iloc[-1]
    prev_row = df.iloc[-2]

    prev_short, curr_short = prev_row[f'ema_{short_period}'], last_row[f'ema_{short_period}']
    prev_long, curr_long = prev_row[f'ema_{long_period}'], last_row[f'ema_{long_period}']

    # Bullish crossover: 9 EMA was below/equal and now is above 20 EMA
    if prev_short <= prev_long and curr_short > curr_long:
        return "BUY"
    # Bearish crossover: 9 EMA was above/equal and now is below 20 EMA
    elif prev_short >= prev_long and curr_short < curr_long:
        return "SELL"
    
    return None

# -----------------------------------------------------------------------------
# --- Main Execution Block ---
# -----------------------------------------------------------------------------

if __name__ == "__main__":
    # Ensure you have the necessary libraries installed:
    # pip install websocket-client python-dotenv pandas
    
    if not API_KEY or not API_SECRET:
        print("❌ Error: API_KEY and API_SECRET must be set in your .env file.")
    else:
        ws = websocket.WebSocketApp(WEBSOCKET_URL, on_message=on_message, on_error=on_error, on_close=on_close)
        ws.on_open = on_open
        ws.run_forever()