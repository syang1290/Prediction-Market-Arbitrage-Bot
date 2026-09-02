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

async def live_poly_ws(manager: EventManager, token_ids: list):
    # Use polymarket's clob which reads live market state, then place and manages orders
    url = "wss://ws-subscriptions-clob.polymarket.com/ws/market"
    
    for token_id in token_ids:
        manager.initialize_event(token_id, "Polymarket")
    
    try:
        async with websockets.connect(url) as ws:
            subscribe_msg = {
                "assets": token_ids,
                "type": "market"
            }
            await ws.send(json.dumps(subscribe_msg))
            print(f"Subscribed to {len(token_ids)} Polymarket tokens.")
            
            async for message in ws:
                data = json.loads(message)
                
                if isinstance(data, list) and len(data) > 0 and data[0].get("bids") is not None:
                    market_data = data[0]
                    
                    # The WS payload includes the specific asset ID it is updating
                    current_token_id = market_data.get("asset")
                    
                    if not current_token_id:
                        continue

                    for bid in market_data.get("bids", []):
                        price = float(bid.get("price", 0))
                        quantity = float(bid.get("size", 0))
                        manager.process_delta(current_token_id, "BID", price, quantity)
                        
                    for ask in market_data.get("asks", []):
                        price = float(ask.get("price", 0))
                        quantity = float(ask.get("size", 0))
                        manager.process_delta(current_token_id, "SELL", price, quantity)
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

def get_live_markets(limit: int = 15):
    # Retrieves multiple live markets from Polymarket's REST API
    print(f"Fetching top {limit} active markets from Polymarket...")

    url = f"https://gamma-api.polymarket.com/markets?limit={limit}&active=true&closed=false&order=volumeNum&ascending=false"
    markets_data = []
    
    try:
        response = requests.get(url).json()
        for market in response:
            token_ids = market.get("clobTokenIds")
            if isinstance(token_ids, str):
                token_ids = json.loads(token_ids)
                
            if token_ids and len(token_ids) >= 2:
                yes_token_id = token_ids[0]
                no_token_id = token_ids[1]
                question = market.get('question', 'Unknown')
                markets_data.append((question, yes_token_id, no_token_id))
                
        print(f"Successfully loaded {len(markets_data)} markets.\n")
        return markets_data
    except Exception as e:
        print(f"Error fetching markets: {e}")
        return []

async def main():
    print("Starting Live Polymarket Listener...")
    
    manager = EventManager()
    engine = ArbitrageEngine(manager, fee=0.00) 
    
    markets = get_live_markets(limit=15)
    
    all_tokens = []
    
    print("Fetching initial snapshots for all markets...")
    for question, yes_token, no_token in markets:
        fetch_orderbook_snapshot(manager, yes_token)
        fetch_orderbook_snapshot(manager, no_token)
        all_tokens.extend([yes_token, no_token])
    
    asyncio.create_task(live_poly_ws(manager, all_tokens))
    
    await asyncio.sleep(3)
    
    try:
        while True: 
            print(f"Scanning {len(markets)} markets for intra-market arbitrage...")
            
            for question, yes_token, no_token in markets:
                engine.intra_market_arbitrage(yes_token, no_token, "Polymarket", trade_quantity=100, market_name=question)
            
            await asyncio.sleep(3)
    except KeyboardInterrupt:
        print("Engine stopped.")

if __name__ == "__main__":
    asyncio.run(main())

"""

Right now the arbitrage bot project can monitor a single event every 5-10 seconds and check for updates if there are any arbitrage opportunities
The next step is to make a detector such that it will be monitoring multiple (or all?) events on Polymarket such that if there is a single arbitrage 
opportunity available, it will print that out. Fixed - 8/3/26

The next step is to start integrating Kalshi once Polymarket's Arbitrage works.

"""