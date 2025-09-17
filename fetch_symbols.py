# import requests
# import json  # <-- Added for writing to the file
# import pprint

# # Define the file to save the watchlist to
# WATCHLIST_FILE = "watchlist.json"

# def fetch_all_symbols():
#     """
#     Fetches all product symbols from the Delta Exchange API, excluding options and move contracts.
#     """
#     url = "https://api.india.delta.exchange/v2/products"
#     headers = {'Accept': 'application/json'}

#     try:
#         response = requests.get(url, headers=headers)
#         response.raise_for_status()
#         products = response.json().get('result', [])

#         # Filter out options and move contracts
#         symbols = [product['symbol'] for product in products
#                    if not (product['symbol'].startswith('C-') or
#                            product['symbol'].startswith('P-') or
#                            product['symbol'].startswith('MV-'))]
        
#         return symbols

#     except requests.exceptions.RequestException as e:
#         print(f"❌ Error fetching symbols from API: {e}")
#         return []

# def fetch_ticker_price(symbol: str):
#     """
#     Fetches the latest ticker information for a single symbol.
#     """
#     url = f"https://api.india.delta.exchange/v2/tickers/{symbol}"
#     headers = {'Accept': 'application/json'}
#     try:
#         response = requests.get(url, headers=headers)
#         response.raise_for_status()
#         ticker_data = response.json().get('result', {})
#         return ticker_data.get('mark_price')
#     except requests.exceptions.RequestException as e:
#         print(f"❌ Error fetching ticker price for {symbol}: {e}")
#         return None

# # This block runs ONLY when you execute the script directly
# if __name__ == "__main__":
#     print("🚀 Fetching all symbols from the exchange...")
    
#     # 1. Fetch the list of symbols
#     symbol_list = fetch_all_symbols()
    
#     # 2. If the fetch was successful, save the list to the file
#     if symbol_list:
#         try:
#             with open(WATCHLIST_FILE, 'w') as f:
#                 json.dump(symbol_list, f, indent=2)
            
#             print(f"✅ Success! Wrote {len(symbol_list)} symbols to {WATCHLIST_FILE}.")
        
#         except Exception as e:
#             print(f"❌ Error writing to {WATCHLIST_FILE}: {e}")
#     else:
#         print("Could not fetch symbols. Watchlist not updated.")

import requests
import json

# File to save the watchlist symbols
WATCHLIST_FILE = "watchlist.json"

def fetch_all_symbols():
    """
    Fetch all product symbols from Delta Exchange API,
    excluding options and move contracts (prefixes 'C-', 'P-', 'MV-').
    Returns a list of valid symbols.
    """
    url = "https://api.india.delta.exchange/v2/products"
    headers = {'Accept': 'application/json'}

    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        products = response.json().get('result', [])

        # Filter out unwanted contract types
        symbols = [
            product['symbol'] for product in products
            if not (
                product['symbol'].startswith('C-') or 
                product['symbol'].startswith('P-') or 
                product['symbol'].startswith('MV-')
            )
        ]
        return symbols

    except requests.exceptions.RequestException as e:
        print(f"❌ Error fetching symbols from API: {e}")
        return []

def fetch_ticker_price(symbol: str):
    """
    Fetch the latest ticker price (mark_price) for a given symbol.
    Returns float price or None on failure.
    """
    url = f"https://api.india.delta.exchange/v2/tickers/{symbol}"
    headers = {'Accept': 'application/json'}
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        ticker_data = response.json().get('result', {})
        return ticker_data.get('mark_price')
    except requests.exceptions.RequestException as e:
        print(f"❌ Error fetching ticker price for {symbol}: {e}")
        return None

if __name__ == "__main__":
    print("🚀 Fetching all symbols from the exchange...")

    # Fetch the list of symbols
    symbol_list = fetch_all_symbols()

    # Save the list as a JSON array to the watchlist file
    if symbol_list:
        try:
            with open(WATCHLIST_FILE, 'w') as f:
                json.dump(symbol_list, f, indent=2)
            print(f"✅ Success! Wrote {len(symbol_list)} symbols to {WATCHLIST_FILE}.")
        except Exception as e:
            print(f"❌ Error writing to {WATCHLIST_FILE}: {e}")
    else:
        print("⚠️ Could not fetch symbols. Watchlist not updated.")
