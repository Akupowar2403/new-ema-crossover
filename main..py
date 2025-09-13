# # import requests
# # import pandas as pd



# # def fetch_historical_candles(symbol, resolution, start, end):
# #     url = f'https://api.india.delta.exchange/v2/history/candles?symbol={symbol}&resolution={resolution}&start={start}&end{end}'
# #     params = {
# #         'symbol': symbol,
# #         'resolution': resolution,
# #         'start': start,  # Unix timestamp in seconds
# #         'end': end       # Unix timestamp in seconds
# #     }
# #     headers = {'Accept': 'application/json'}

# #     response = requests.get(url, params=params, headers=headers)
# #     data = response.json().get('result', [])

# #     if not data:
# #         print("No historical candle data received")
# #         return pd.DataFrame()

# #     # Create DataFrame with Unix timestamps as index
# #     df = pd.DataFrame(data, columns=['time', 'open', 'high', 'low', 'close', 'volume'])
# #     df.set_index('time', inplace=True)  # 'time' is in Unix seconds, keep as is

# #     return df

# # # Example usage:
# # if __name__ == "__main__":
# #     import time

# #     symbol = 'BTCUSD'
# #     resolution = '5m'
# #     now = int(time.time())
# #     start_time = now - 24*60*60  # 24 hours ago
# #     end_time = now

# #     candles_df = fetch_historical_candles(symbol, resolution, start_time, end_time)
 

# import requests
# import pandas as pd
# import websocket
# import hashlib
# import hmac
# import json
# import time

# from datetime import datetime, timezone

# # Config & globals
# WEBSOCKET_URL = "wss://socket.india.delta.exchange"
# API_KEY = '2gtuz8LLl19ezKjYlvApsqv7kK6UYI'
# API_SECRET = 'aehICdR8xRrK8wjFinqblJvM5ljXV8vHwH6sgasyMn0wF9AJP4A6fFPt6qdT'

# symbol = 'BTCUSD'
# resolution = '1m'
# candles_df = pd.DataFrame()  # Global DataFrame to hold candles

# # Fetch historical candles
# def fetch_historical_candles(symbol, resolution, start, end):
#     url = f'https://api.india.delta.exchange/v2/history/candles'
#     params = {
#         'symbol': symbol,
#         'resolution': resolution,
#         'start': start,
#         'end': end
#     }
#     headers = {'Accept': 'application/json'}

#     response = requests.get(url, params=params, headers=headers)
#     data = response.json().get('result', [])

#     if not data:
#         print("No historical candle data received")
#         return pd.DataFrame()

#     df = pd.DataFrame(data, columns=['time', 'open', 'high', 'low', 'close', 'volume'])
#     df.set_index('time', inplace=True)
#     return df

# # Generate WebSocket auth signature
# def generate_signature(secret, message):
#     message = bytes(message, 'utf-8')
#     secret = bytes(secret, 'utf-8')
#     return hmac.new(secret, message, hashlib.sha256).hexdigest()

# # WebSocket callbacks
# def send_authentication(ws):
#     method = 'GET'
#     timestamp = str(int(time.time()))
#     path = '/live'
#     message = method + timestamp + path
#     signature = generate_signature(API_SECRET, message)
#     ws.send(json.dumps({
#         "type": "auth",
#         "payload": {
#             "api-key": API_KEY,
#             "signature": signature,
#             "timestamp": timestamp
#         }
#     }))

# def on_open(ws):
#     print("WebSocket opened")
#     send_authentication(ws)

# def subscribe(ws, channel, symbols):
#     ws.send(json.dumps({
#         "type": "subscribe",
#         "payload": {
#             "channels": [
#                 {"name": channel, "symbols": symbols}
#             ]
#         }
#     }))

# def on_message(ws, message):
#     global candles_df
#     msg = json.loads(message)

#     # After auth success, subscribe to live candles
#     if msg.get('type') == 'success' and msg.get('message') == 'Authenticated':
#         print("Authenticated successfully")
#         subscribe(ws, f'candlestick_{resolution}', [symbol])

#     # Process live candlestick data
#     elif msg.get('type') == f'candlestick_{resolution}':
#         ts_micro = msg.get('timestamp')
#         if ts_micro:
#             ts_sec = ts_micro // 1_000_000  # Unix timestamp in seconds
#             candle_data = {
#                 'open': msg['open'],
#                 'high': msg['high'],
#                 'low': msg['low'],
#                 'close': msg['close'],
#                 'volume': msg['volume']
#             }
#             # Update or append candle in DataFrame
#             if ts_sec in candles_df.index:
#                 candles_df.loc[ts_sec] = candle_data
#             else:
#                 new_df = pd.DataFrame([candle_data], index=[ts_sec])
#                 candles_df = pd.concat([candles_df, new_df])
#                 candles_df.sort_index(inplace=True)
#             print(f"Updated candle at {ts_sec} with close {candle_data['close']}")

#     else:
#         print(msg)

# def on_error(ws, error):
#     print(f"WebSocket error: {error}")

# def on_close(ws, close_status_code, close_msg):
#     print(f"WebSocket closed: {close_status_code} - {close_msg}")


# if __name__ == "__main__":
#     now = int(time.time())
#     start_time = now - 24 * 3600  # last 24 hours

#     # Fetch historical candles first
#     candles_df = fetch_historical_candles(symbol, resolution, start_time, now)
#     print(f"Fetched {len(candles_df)} historical candles")

#     # Start WebSocket for live updates
#     ws = websocket.WebSocketApp(
#         WEBSOCKET_URL,
#         on_message=on_message,
#         on_error=on_error,
#         on_close=on_close)
#     ws.on_open = on_open
#     ws.run_forever()

# import requests
# import pandas as pd
# import websocket
# import hashlib
# import hmac
# import json
# import time
# from telegram_bot import AlertService
# from datetime import datetime, timezone

# # Import the strategy function
# from strategy import check_ema_crossover_signal

# # Config & globals
# WEBSOCKET_URL = "wss://socket.india.delta.exchange"
# API_KEY = '2gtuz8LLl19ezKjYlvApsqv7kK6UYI'
# API_SECRET = 'aehICdR8xRrK8wjFinqblJvM5ljXV8vHwH6sgasyMn0wF9AJP4A6fFPt6qdT'

# symbol = 'BTCUSD'
# resolution = '1m'
# candles_df = pd.DataFrame()  # Global DataFrame to hold candles


# # Fetch historical candles
# def fetch_historical_candles(symbol, resolution, start, end):
#     url = f'https://api.india.delta.exchange/v2/history/candles'
#     params = {
#         'symbol': symbol,
#         'resolution': resolution,
#         'start': start,
#         'end': end
#     }
#     headers = {'Accept': 'application/json'}

#     response = requests.get(url, params=params, headers=headers)
#     data = response.json().get('result', [])

#     if not data:
#         print("No historical candle data received")
#         return pd.DataFrame()

#     df = pd.DataFrame(data, columns=['time', 'open', 'high', 'low', 'close', 'volume'])
#     df.set_index('time', inplace=True)
#     return df


# # Generate WebSocket auth signature
# def generate_signature(secret, message):
#     message = bytes(message, 'utf-8')
#     secret = bytes(secret, 'utf-8')
#     return hmac.new(secret, message, hashlib.sha256).hexdigest()


# # WebSocket callbacks
# def send_authentication(ws):
#     method = 'GET'
#     timestamp = str(int(time.time()))
#     path = '/live'
#     message = method + timestamp + path
#     signature = generate_signature(API_SECRET, message)
#     ws.send(json.dumps({
#         "type": "auth",
#         "payload": {
#             "api-key": API_KEY,
#             "signature": signature,
#             "timestamp": timestamp
#         }
#     }))


# def on_open(ws):
#     print("WebSocket opened")
#     send_authentication(ws)


# def subscribe(ws, channel, symbols):
#     ws.send(json.dumps({
#         "type": "subscribe",
#         "payload": {
#             "channels": [
#                 {"name": channel, "symbols": symbols}
#             ]
#         }
#     }))

# alert_service = AlertService()

# def on_message(ws, message):
#     global candles_df
#     msg = json.loads(message)

#     if msg.get('type') == 'success' and msg.get('message') == 'Authenticated':
#         print("Authenticated successfully")
#         subscribe(ws, f'candlestick_{resolution}', [symbol])

#     elif msg.get('type') == f'candlestick_{resolution}':
#         ts_micro = msg.get('timestamp')
#         if ts_micro:
#             ts_sec = ts_micro // 1_000_000  # Unix timestamp seconds
#             candle_data = {
#                 'open': msg['open'],
#                 'high': msg['high'],
#                 'low': msg['low'],
#                 'close': msg['close'],
#                 'volume': msg['volume']
#             }
#             if ts_sec in candles_df.index:
#                 candles_df.loc[ts_sec] = candle_data
#             else:
#                 new_df = pd.DataFrame([candle_data], index=[ts_sec])
#                 candles_df = pd.concat([candles_df, new_df])
#                 candles_df.sort_index(inplace=True)

#             signal = check_ema_crossover_signal(candles_df)
#             if signal:
#                 try:
#                     alert_message = (
#                         f"🚨 Trade Signal Alert 🚨\n"
#                         f"Symbol: {symbol}\n"
#                         f"Time: {datetime.fromtimestamp(ts_sec).strftime('%Y-%m-%d %H:%M:%S')}\n"
#                         f"Resolution: {resolution}\n"
#                         f"Signal Triggered: {signal}"
#                     )
#                     alert_service.send_signal_alert(alert_message)
#                     print(f"Sent alert: {alert_message}")
#                 except Exception as e:
#                     print(f"Error sending alert: {e}")
#     else:
#         print(msg)


# def on_error(ws, error):
#     print(f"WebSocket error: {error}")


# def on_close(ws, close_status_code, close_msg):
#     print(f"WebSocket closed: {close_status_code} - {close_msg}")


# if __name__ == "__main__":
#     now = int(time.time())
#     start_time = now - 24 * 3600  # last 24 hours

#     # Fetch historical candles first
#     candles_df = fetch_historical_candles(symbol, resolution, start_time, now)
#     print(f"Fetched {len(candles_df)} historical candles")

#     # Start WebSocket for live updates
#     ws = websocket.WebSocketApp(
#         WEBSOCKET_URL,
#         on_message=on_message,
#         on_error=on_error,
#         on_close=on_close)
#     ws.on_open = on_open
#     ws.run_forever()

 
import requests
import pandas as pd
import websocket
import hashlib
import hmac
import json
import time
from telegram_bot import AlertService
from datetime import datetime, timezone
import logging
logging.basicConfig(level=logging.INFO) 


# Import the strategy function
from strategy import check_ema_crossover_signal

# Config & globals
WEBSOCKET_URL = "wss://socket.india.delta.exchange"
API_KEY = '2gtuz8LLl19ezKjYlvApsqv7kK6UYI'
API_SECRET = 'aehICdR8xRrK8wjFinqblJvM5ljXV8vHwH6sgasyMn0wF9AJP4A6fFPt6qdT'

symbol = 'BTCUSD'
resolution = '1m'
candles_df = pd.DataFrame()  # Global DataFrame to hold candles
alert_service = AlertService()
last_candle_start_time = None  # Track last processed candle start time

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

# Generate WebSocket auth signature
def generate_signature(secret, message):
    message = bytes(message, 'utf-8')
    secret = bytes(secret, 'utf-8')
    return hmac.new(secret, message, hashlib.sha256).hexdigest()

# WebSocket callbacks
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

def on_message(ws, message):
    global candles_df, last_candle_start_time
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

            # Only run strategy when a new candle starts (previous candle closed)
            if last_candle_start_time is not None and candle_start_time != last_candle_start_time:
                signal = check_ema_crossover_signal(candles_df)
                if signal:
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
                    except Exception as e:
                        print(f"Error sending alert: {e}")

            last_candle_start_time = candle_start_time

        else:
            print("candlestick message missing candle_start_time:", msg)

    else:
        print(msg)

def on_error(ws, error):
    print(f"WebSocket error: {error}")

def on_close(ws, close_status_code, close_msg):
    print(f"WebSocket closed: {close_status_code} - {close_msg}")

if __name__ == "__main__":
    now = int(time.time())
    start_time = 1  

    candles_df = fetch_historical_candles(symbol, resolution, start_time, now)
    print(f"Fetched {len(candles_df)} historical candles")

    ws = websocket.WebSocketApp(
        WEBSOCKET_URL,
        on_message=on_message,
        on_error=on_error,
        on_close=on_close)
    ws.on_open = on_open
    ws.run_forever()
