import asyncio
from engine import EventManager, ArbitrageEngine
import poly_websocket as poly
import kalshi_websocket as kalshi

async def arbitrage_scanner(engine: ArbitrageEngine, poly_markets: list, kalshi_tickers: list):
    """This function continuously scans the shared EventManager for any arbitrag opportunities"""
    while True:
        for question, yes_token, no_token in poly_markets:
            engine.intra_market_arbitrage(
                yes_token, 
                no_token, 
                "Polymarket", 
                trade_quantity=100, 
                market_name=question
            )
            
        for ticker in kalshi_tickers:
            event = engine.manager.events.get(ticker)
            if event and event.best_sell() is not None and event.best_bid() is not None:
                spread = event.spread()
                if spread is not None and spread < 0:
                    print(f"\n--- Kalshi Crossed Book Found! ---")
                    print(f"[{ticker}] Spread: {spread:.4f}")
        
        await asyncio.sleep(3)

async def main():
    manager = EventManager()
    engine = ArbitrageEngine(manager, fee=0.00)
    
    # Get the markets from both sources
    poly_markets = poly.get_live_markets(limit=15)
    kalshi_markets = kalshi.get_live_kalshi_markets(limit=5)
    
    poly_tokens = []
    for question, yes_token, no_token in poly_markets:
        poly_tokens.extend([yes_token, no_token])
        
    kalshi_tickers = [ticker for title, ticker in kalshi_markets]
    
    if not poly_tokens and not kalshi_tickers:
        print("No markets loaded -> Exiting")
        return
        
    # Getting initial values
    print("\nFetching initial snapshots for all platforms:")
    for token in poly_tokens:
        poly.fetch_orderbook_snapshot(manager, token)
        
    for ticker in kalshi_tickers:
        kalshi.fetch_kalshi_orderbook_snapshot(manager, ticker)
        
    # Get data concurrently
    print("\nStarting concurrent cross-exchange data pipelines:")
    await asyncio.gather(
        poly.live_poly_ws(manager, poly_tokens),
        kalshi.live_kalshi_ws(manager, kalshi_tickers),
        arbitrage_scanner(engine, poly_markets, kalshi_tickers)
    )

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nShut dow.")