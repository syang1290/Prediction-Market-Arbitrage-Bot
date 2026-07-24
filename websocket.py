import asyncio
import json
import websockets
import requests

from engine import EventManager, ArbitrageEngine

def fetch_orderbook_snapshot(manager: EventManager, token_id: str):
    """Fetches the current state of the orderbook before the WebSocket starts."""
    print(f"Fetching Orderbook Snapshot for ...{token_id[-6:]}")
    url = f"https://clob.polymarket.com/book?token_id={token_id}"

    manager.initialize_event(token_id, "Polymarket")

    try:
        response = requests.get(url).json()
        
        for bid in response.get("bids", []):
            price = float(bid.get("price", 0))
            quantity = float(bid.get("size", 0))
            manager.process_delta(token_id, "BID", price, quantity)
            
        for ask in response.get("asks", []):
            price = float(ask.get("price", 0))
            quantity = float(ask.get("size", 0))
            manager.process_delta(token_id, "SELL", price, quantity)
            
    except Exception as e:
        print(f"Error fetching snapshot: {e}")

async def live_poly_ws(manager: EventManager, token_id: str):
    # Use polymarket's clob which reads live market state, then place and manages orders
    url = "wss://ws-subscriptions-clob.polymarket.com/ws/market"
    
    manager.initialize_event(token_id, "Polymarket")
    
    try:
        async with websockets.connect(url) as ws:
            subscribe_msg = {
                "assets": [token_id],
                "type": "market"
            }
            await ws.send(json.dumps(subscribe_msg))
            print(f"Subscribed to Polymarket token: {token_id}")
            
            async for message in ws:
                data = json.loads(message)
                
                if isinstance(data, list) and len(data) > 0 and data[0].get("bids") is not None:
                    market_data = data[0]
                    
                    print(f"[Network] Orderbook update received for ...{token_id[-6:]}")
                    
                    for bid in market_data.get("bids", []):
                        price = float(bid.get("price", 0))
                        quantity = float(bid.get("size", 0))
                        manager.process_delta(token_id, "BID", price, quantity)
                        
                    for ask in market_data.get("asks", []):
                        price = float(ask.get("price", 0))
                        quantity = float(ask.get("size", 0))
                        manager.process_delta(token_id, "SELL", price, quantity)
    except Exception as e:
        print(f"Polymarket WS Error: {e}")

def get_live_token_id():
    # Retrieves a live market from Polymarket's REST API and returns YES or NO token IDs
    print("Fetching an active market from Polymarket...")

    url = "https://gamma-api.polymarket.com/markets?limit=1&active=true&closed=false&order=volumeNum&ascending=false"
    try:
        response = requests.get(url).json()
        market = response[0]
        
        token_ids = market.get("clobTokenIds")
        if isinstance(token_ids, str):
            token_ids = json.loads(token_ids)
            
        yes_token_id = token_ids[0]
        no_token_id = token_ids[1]
        print(f"Tracking Market: {market.get('question', 'Unknown')}")
        print(f"Using YES Token ID: {yes_token_id}")
        print(f"Using NO Token ID: {no_token_id}\n")
        return yes_token_id, no_token_id
    except Exception as e:
        print(f"Error fetching market: {e}")
        return "0", "0"

async def main():
    print("Starting Live Polymarket Listener...")
    
    manager = EventManager()
    
    engine = ArbitrageEngine(manager, fee=0.00) 
    
    yes_token, no_token = get_live_token_id()
    
    fetch_orderbook_snapshot(manager, yes_token)
    fetch_orderbook_snapshot(manager, no_token)
    
    asyncio.create_task(live_poly_ws(manager, yes_token))
    asyncio.create_task(live_poly_ws(manager, no_token))
    
    await asyncio.sleep(3)
    
    try:
        while True: 
            engine.intra_market_arbitrage(yes_token, no_token, "Polymarket", trade_quantity=100)
            
            await asyncio.sleep(10)
            # Run it every 10 seconds
    except KeyboardInterrupt:
        print("Engine stopped.")

if __name__ == "__main__":
    asyncio.run(main())

"""

Right now the arbitrage bot project can monitor a single event every 5-10 seconds and check for updates if there are any arbitrage opportunities
The next step is to make a detector such that it will be monitoring multiple (or all?) events on Polymarket such that if there is a single arbitrage 
opportunity available, it will print that out.

"""