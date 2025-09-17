# --- STRATEGY PARAMETERS ---
SHORT_EMA_PERIOD = 9
LONG_EMA_PERIOD = 20
VOLUME_THRESHOLD_FACTOR = 1.0 # e.g., 1.5 means volume must be 50% above average
COOLDOWN_MINUTES = 30

# --- SCREENER PARAMETERS ---
TIMEFRAMES = ["15m", "1h", "4h", "1d"]
WARMUP_BARS_FACTOR = 3 # Use 3x the longest EMA period for warmup data
WARMUP_BARS_BUFFER = 2 # Add a small buffer

# --- API & DATA PARAMETERS ---
SECONDS_PER_BAR = {
    "15m": 15 * 60,
    "1h": 60 * 60,
    "4h": 4 * 60 * 60,
    "1d": 24 * 60 * 60
}