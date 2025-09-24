# shared_state.py
import asyncio
from typing import Dict, Tuple

# The command queue for dynamic watchlist updates
websocket_command_queue = asyncio.Queue()

# The single source of truth for all live candle data and signals.
# The key is a tuple: (symbol, timeframe)
# The value is the CandleManager instance for that pair.
candle_managers_state: Dict[Tuple[str, str], any] = {}

# This file will hold instances that need to be shared across the application.

alert_service = None