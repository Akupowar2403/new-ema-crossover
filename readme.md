# 📈 EMA Crossover Screener<b1>
A real-time cryptocurrency screener that monitors Exponential Moving Average (EMA) crossovers for multiple symbols and timeframes. The application features a high-performance Python backend powered by FastAPI and a dynamic, interactive web-based frontend.

## ✨ Features

Real-time Signal Detection: Uses a persistent WebSocket connection to receive live market data and identify EMA crossovers as they happen.

Multi-Timeframe Dashboard: Displays signals for multiple timeframes (1m, 15m, 1h, 4h, 1d) in a clean, color-coded table.

Dynamic Watchlist: Add or remove symbols from your watchlist through the UI, with the backend dynamically subscribing/unsubscribing from data streams without a restart.

High-Performance Caching: Leverages Redis to cache historical data, allowing for near-instantaneous application startups after the initial run.

Historical Data Analysis: Fetch and view a complete history of all past crossover events for any symbol and timeframe.

Live Alerts: Get immediate notifications in the UI when a new crossover is confirmed on any symbol in your watchlist.

## 🛠️ Tech Stack

Backend: Python, FastAPI, Uvicorn, Pandas, Redis, HTTPX, WebSockets

Frontend: HTML5, CSS3, Vanilla JavaScript

## 📂 Project Structure
NEW-EMA-CROSSOVER/<b1>
├── frontend/<b1>
│   ├── index.html<b1>
│   ├── style.css<b1>
│   └── script.js<b1>
├── fast.py                 # FastAPI server and API endpoints<b1>
├── helpers.py              # Core logic for data fetching, analysis, caching<b1>
├── websocket_manager.py    # Manages the live connection to the exchange<b1>
├── shared_state.py         # Connects the API and WebSocket manager<b1>
├── config.py               # Configuration file (API keys, settings)<b1>
├── requirements.txt        # Python dependencies<b1>
└── watchlist.json          # Stores your saved symbols<b1>

## 🚀 Setup and Installation
Prerequisites
Python 3.10+

Redis installed and running. You can download it from the official Redis website.

### Clone the Repository
Bash

git clone <your-repository-url>
cd NEW-EMA-CROSSOVER

### Backend Setup
Create a virtual environment and install the required Python packages.

Bash

Create a virtual environment
python -m venv .venv

Activate it
On Windows:
.venv\Scripts\Activate.ps1

On macOS/Linux:
source .venv/bin/activate

Install dependencies:
pip install -r requirements.txt

### Configuration
Create a file named config.py in the main project directory and add your settings.

config.py Template:

Python

config.py<b1>

1. Delta Exchange API Credentials:
API_KEY = "YOUR_API_KEY_HERE"
API_SECRET = "YOUR_API_SECRET_HERE"

2. EMA Settings:
SHORT_EMA_PERIOD = 9
LONG_EMA_PERIOD = 21

3. Timeframes to Monitor:
These must match the headers in your frontend table
TIMEFRAMES = ["1m", "15m", "1h", "4h", "1d"]

## ▶️ Running the Application
You will need two separate terminals to run the backend and frontend servers.

1. Start the Backend Server
Make sure your Redis server is running. Then, from the main project directory (NEW-EMA-CROSSOVER/), run:<b1>

Bash

uvicorn fast:app --reload<b1>
2. Start the Frontend Server
Open a new terminal, navigate into the frontend directory, and start Python's simple HTTP server:,<b1>

Bash

cd frontend
python -m http.server 8000
(Note: We specify port 8000 to match the backend and avoid any potential CORS issues).<b1>

3. Access the Screener
Open your web browser and navigate to:
http://localhost:8000

The application should now be fully functional. The first startup may be slow as it populates the Redis cache. Subsequent startups will be much faster.