import websocket
import hashlib
import hmac
import json
import time
import datetime


# production websocket base url and api keys/secrets
WEBSOCKET_URL = "wss://socket.india.delta.exchange"
API_KEY = '2gtuz8LLl19ezKjYlvApsqv7kK6UYI'
API_SECRET = 'aehICdR8xRrK8wjFinqblJvM5ljXV8vHwH6sgasyMn0wF9AJP4A6fFPt6qdT'

def on_error(ws, error):
    print(f"Socket Error: {error}")

def on_close(ws, close_status_code, close_msg):
    print(f"Socket closed with status: {close_status_code} and message: {close_msg}")

def on_open(ws):
    print(f"Socket opened")
    # api key authentication
    send_authentication(ws)

def send_authentication(ws):
    method = 'GET'
    timestamp = str(int(time.time()))
    path = '/live'
    signature_data = method + timestamp + path
    signature = generate_signature(API_SECRET, signature_data)
    ws.send(json.dumps({
        "type": "auth",
        "payload": {
            "api-key": API_KEY,
            "signature": signature,
            "timestamp": timestamp
        }
    }))

def generate_signature(secret, message):
    message = bytes(message, 'utf-8')
    secret = bytes(secret, 'utf-8')
    hash = hmac.new(secret, message, hashlib.sha256)
    return hash.hexdigest()

def on_message(ws, message):
    message_json = json.loads(message)
    # subscribe private channels after successful authentication
    if message_json['type'] == 'success' and message_json['message'] == 'Authenticated':
         # subscribe orders channel for order updates for all contracts
        # subscribe(ws, "orders", ["all"])
        # subscribe positions channel for position updates for all contracts
        # subscribe(ws, "v2/ticker", ["BTCUSD"])
        subscribe(ws, "candlestick_1m", ["BTCUSD"])

        

    else:
      print(message_json)

def subscribe(ws, channel, symbols):
    payload = {
        "type": "subscribe",
        "payload": {
            "channels": [
                {
                    "name": channel,
                    "symbols": symbols
                }
            ]
        }
    }
    ws.send(json.dumps(payload))

if __name__ == "__main__":
  ws = websocket.WebSocketApp(WEBSOCKET_URL, on_message=on_message, on_error=on_error, on_close=on_close)
  ws.on_open = on_open
  ws.run_forever() # runs indefinitely

# import websocket
# import hashlib
# import hmac
# import json
# import time
# from datetime import datetime, timezone, timedelta

# # WebSocket base url and API keys
# WEBSOCKET_URL = "wss://socket.india.delta.exchange"
# API_KEY = '2gtuz8LLl19ezKjYlvApsqv7kK6UYI'
# API_SECRET = 'aehICdR8xRrK8wjFinqblJvM5ljXV8vHwH6sgasyMn0wF9AJP4A6fFPt6qdT'

# def on_error(ws, error):
#     print(f"Socket Error: {error}")

# def on_close(ws, close_status_code, close_msg):
#     print(f"Socket closed with status: {close_status_code} and message: {close_msg}")

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
#     # After successful authentication, subscribe to BTCUSD 1m candlestick
#     if message_json.get('type') == 'success' and message_json.get('message') == 'Authenticated':
#         subscribe(ws, "candlestick_1m", ["BTCUSD"])
#     # Process incoming 1m candlestick messages
#     elif message_json.get('type') == 'candlestick_1m':
#         ts_micro = message_json.get('timestamp')
#         if ts_micro:
#             ts_sec = ts_micro / 1_000_000
#             utc_dt = datetime.fromtimestamp(ts_sec, tz=timezone.utc)
#             ist_dt = utc_dt + timedelta(hours=5, minutes=30)
#             time_str = ist_dt.strftime('%Y-%m-%d %H:%M:%S')
#         else:
#             time_str = "N/A"
#         print(f"[IST] {time_str} | open={message_json.get('open')} high={message_json.get('high')} low={message_json.get('low')} close={message_json.get('close')} volume={message_json.get('volume')}")
#     else:
#         print(message_json)

# def subscribe(ws, channel, symbols):
#     payload = {
#         "type": "subscribe",
#         "payload": {
#             "channels": [
#                 {"name": channel, "symbols": symbols}
#             ]
#         }
#     }
#     ws.send(json.dumps(payload))

# if __name__ == "__main__":
#     ws = websocket.WebSocketApp(
#         WEBSOCKET_URL,
#         on_message=on_message,
#         on_error=on_error,
#         on_close=on_close
#     )
#     ws.on_open = on_open
#     ws.run_forever()  # runs indefinitely
