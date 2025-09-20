import asyncio

# This queue will act as a communication channel between your API and the WebSocket client
websocket_command_queue = asyncio.Queue()