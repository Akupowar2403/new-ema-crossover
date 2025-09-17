import json
from flask import Flask, render_template, request, redirect, url_for
from fetch_symbols import fetch_all_symbols # For syncing

app = Flask(__name__)
WATCHLIST_FILE = "watchlist.json"

# --- Helper Functions to Read/Write our JSON file ---

def read_watchlist():
    """Reads the list of symbols from the JSON file."""
    try:
        with open(WATCHLIST_FILE, 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        # If file doesn't exist or is empty/corrupt, return an empty list
        return []

def write_watchlist(symbols):
    """Writes the list of symbols to the JSON file."""
    with open(WATCHLIST_FILE, 'w') as f:
        json.dump(symbols, f, indent=2)

# --- Flask Routes ---

@app.route('/')
def index():
    """Main page that displays the watchlist."""
    current_watchlist = read_watchlist()
    return render_template('index.html', watchlist=current_watchlist)

@app.route('/add', methods=['POST'])
def add_symbol():
    """Handles adding a new symbol to the watchlist."""
    # Get symbol from form, make it uppercase, and remove whitespace
    new_symbol = request.form['symbol'].upper().strip() 
    if new_symbol:
        current_watchlist = read_watchlist()
        if new_symbol not in current_watchlist:
            current_watchlist.append(new_symbol)
            write_watchlist(current_watchlist)
    return redirect(url_for('index')) # Redirect back to the main page

@app.route('/delete', methods=['POST'])
def delete_symbol():
    """Handles deleting a symbol from the watchlist."""
    symbol_to_delete = request.form['symbol']
    current_watchlist = read_watchlist()
    if symbol_to_delete in current_watchlist:
        current_watchlist.remove(symbol_to_delete)
        write_watchlist(current_watchlist)
    return redirect(url_for('index')) # Redirect back to the main page

@app.route('/sync')
def sync_all_symbols():
    """
    Fetches all symbols from the exchange and overwrites the watchlist.
    Trigger by visiting http://127.0.0.1:5000/sync
    """
    print("🔄 Syncing all symbols from the exchange...")
    all_symbols = fetch_all_symbols()
    
    if all_symbols:
        write_watchlist(all_symbols)
        print(f"✅ Successfully wrote {len(all_symbols)} symbols to watchlist.json")
    else:
        print("❌ Failed to fetch symbols, watchlist not updated.")
        
    return redirect(url_for('index'))

# --- Main entry point to run the app ---

if __name__ == '__main__':
    app.run(debug=True)