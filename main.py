import asyncio
from engine import EventManager, ArbitrageEngine
from market_matcher import get_or_create_matched_markets
import poly_websocket as poly
import kalshi_websocket as kalshi

async def arbitrage_scanner(engine: ArbitrageEngine, matched_markets: list):
    """Continuously evaluates matched pairs for both directions of cross-platform arb."""
    while True:
        for pair in matched_markets:
            engine.cross_market_arbitrage(
                kalshi_ticker=pair["kalshi_ticker"],
                poly_yes_id=pair["poly_yes_token"],
                poly_no_id=pair["poly_no_token"],
                market_name=pair.get("market_name", "Cross-Platform Event"),
                target_qty=50.0
            )
        await asyncio.sleep(2)

async def main():
    manager = EventManager()
    engine = ArbitrageEngine(manager, min_profit_threshold=0.25)

    matched_pairs = get_or_create_matched_markets(refresh=False)
    if not matched_pairs:
        print("No cross-platform markets matched")
        return

    poly_tokens = []
    kalshi_tickers = []
    for pair in matched_pairs:
        poly_tokens.extend([pair["poly_yes_token"], pair["poly_no_token"]])
        kalshi_tickers.append(pair["kalshi_ticker"])

    poly_tokens = list(set(poly_tokens))
    kalshi_tickers = list(set(kalshi_tickers))

    print(f"\nPre-fetching order book depth for {len(matched_pairs)} matched pairs...")
    for token in poly_tokens:
        poly.fetch_orderbook_snapshot(manager, token)

    for ticker in kalshi_tickers:
        kalshi.fetch_kalshi_orderbook_snapshot(manager, ticker)

    print("\nStarting arbitrage scan...")
    await asyncio.gather(
        poly.live_poly_ws(manager, poly_tokens),
        kalshi.live_kalshi_ws(manager, kalshi_tickers),
        arbitrage_scanner(engine, matched_pairs)
    )

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nShutdown")