import asyncio
import json
import websockets
import requests
import time
import base64
import os
from dotenv import load_dotenv
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives import serialization

from engine import EventManager, ArbitrageEngine

load_dotenv()
KALSHI_KEY_ID = os.getenv("KALSHI_KEY_ID")
KALSHI_PRIVATE_KEY = os.getenv("KALSHI_PRIVATE_KEY")

def generate_kalshi_auth_headers(method: str, path: str):
    """Generates the RSA cryptographic signature required by Kalshi."""
    timestamp = str(int(time.time() * 1000))
    
    path_without_query = path.split('?')[0]
    msg_string = timestamp + method + path_without_query
    
    formatted_key = KALSHI_PRIVATE_KEY.replace("\\n", "\n")
    
    private_key = serialization.load_pem_private_key(
        formatted_key.encode('utf-8'),
        password=None,
    )
    
    signature = private_key.sign(
        msg_string.encode('utf-8'),
        padding.PSS(
            mgf=padding.MGF1(hashes.SHA256()),
            salt_length=padding.PSS.MAX_LENGTH
        ),
        hashes.SHA256()
    )
    
    return {
        "KALSHI-ACCESS-KEY": KALSHI_KEY_ID,
        "KALSHI-ACCESS-SIGNATURE": base64.b64encode(signature).decode('utf-8'),
        "KALSHI-ACCESS-TIMESTAMP": timestamp
    }

def get_live_kalshi_markets(limit: int = 15):
    """Fetches active markets from Kalshi."""
    print(f"Fetching top {limit} active markets from Kalshi...")
    
    path = f"/trade-api/v2/markets?limit={limit}&status=open"
    url = "https://api.elections.kalshi.com" + path
    
    headers = generate_kalshi_auth_headers("GET", path)
    
    markets_data = []
    try:
        response = requests.get(url, headers=headers).json()
        
        if "error" in response:
            print(f"Kalshi API Rejected Request: {response['error']}")
            return []
            
        for market in response.get("markets", []):
            ticker = market.get("ticker")
            title = market.get("title")
            
            markets_data.append((title, ticker))
            
        print(f"Successfully loaded {len(markets_data)} Kalshi markets.\n")
        return markets_data
    except Exception as e:
        print(f"Error fetching Kalshi markets: {e}")
        return []

def fetch_kalshi_orderbook_snapshot(manager: EventManager, ticker: str):
    """Fetches the current state of the orderbook from Kalshi's REST API."""
    print(f"Fetching Orderbook Snapshot for ...{ticker[-15:]}")
    path = f"/trade-api/v2/markets/{ticker}/orderbook"
    url = "https://api.elections.kalshi.com" + path
    
    headers = generate_kalshi_auth_headers("GET", path)
    manager.initialize_event(ticker, "Kalshi")
    
    try:
        response = requests.get(url, headers=headers).json()
        orderbook = response.get("orderbook", {})
        
        for bid in orderbook.get("bids", []):
            price = bid[0] / 100.0
            quantity = bid[1]
            manager.process_delta(ticker, "BID", price, quantity)
            
        for ask in orderbook.get("asks", []):
            price = ask[0] / 100.0
            quantity = ask[1]
            manager.process_delta(ticker, "SELL", price, quantity)
    except Exception as e:
        print(f"Error fetching snapshot: {e}")

async def live_kalshi_ws(manager: EventManager, tickers: list):
    """Connects to Kalshi's WebSocket and normalizes price data."""
    url = "wss://api.elections.kalshi.com/trade-api/ws/v2"
    
    path = "/trade-api/ws/v2"
    headers = generate_kalshi_auth_headers("GET", path)
    
    for ticker in tickers:
        manager.initialize_event(ticker, "Kalshi")
        
    try:
        async with websockets.connect(url, additional_headers=headers) as ws:
            subscribe_msg = {
                "id": 1,
                "cmd": "subscribe",
                "params": {
                    "channels": ["orderbook_delta"],
                    "market_tickers": tickers
                }
            }
            await ws.send(json.dumps(subscribe_msg))
            print(f"Subscribed to {len(tickers)} Kalshi markets.")
            
            async for message in ws:
                data = json.loads(message)
                
                if data.get("type") == "orderbook_delta":
                    delta = data.get("msg", {})
                    ticker = delta.get("market_ticker")
                    
                    if not ticker:
                        continue
                    
                    print(f"[Kalshi Network] Orderbook update received for ...{ticker[-15:]}")
                    
                    for bid in delta.get("bids", []):
                        price = bid[0] / 100.0
                        quantity = bid[1]
                        manager.process_delta(ticker, "BID", price, quantity)
                        
                    for ask in delta.get("asks", []):
                        price = ask[0] / 100.0
                        quantity = ask[1]
                        manager.process_delta(ticker, "SELL", price, quantity)
                        
    except Exception as e:
        print(f"Kalshi WS Error: {e}")

# I combined kalshi and polymarket's websocket main functions into a singular main.py file

""" async def main():
    print("Starting Live Kalshi Listener...")
    
    manager = EventManager()
    
    markets = get_live_kalshi_markets(limit=5)
    tickers = [ticker for title, ticker in markets]
    
    if not tickers:
        print("No markets found. Check API keys and network!")
        return
        
    print("Fetching initial snapshots for Kalshi markets...")
    for ticker in tickers:
        fetch_kalshi_orderbook_snapshot(manager, ticker)
    
    asyncio.create_task(live_kalshi_ws(manager, tickers))
    
    await asyncio.sleep(3)
    
    try:
        while True:
            print("\n--- Current Kalshi Orderbooks ---")
            for ticker in tickers:
                event = manager.events.get(ticker)
                if event:
                    print(f"[{ticker[-20:]}] YES Ask: {event.best_sell()} | YES Bid: {event.best_bid()}")
            
            await asyncio.sleep(5)
    except KeyboardInterrupt:
        print("Engine stopped.")

if __name__ == "__main__":
    asyncio.run(main()) """