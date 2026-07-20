import asyncio
import random

class Event:
    def __init__(self, event_id: str, platform: str, buy: dict = None, sell: dict = None):
        self.event_id = event_id
        self.platform = platform

        # event_id is the ID of the event
        # platform describes which platform (polymarket/kalshi)

        # buy are prices that people are willing to buy at
        # key is price, value is amount of shares
        if buy is None:
            self.buy = {}
        else:
            self.buy = buy

        # sell are prices that people are willing to sell at
        # key is price, value is amount of shares
        if sell is None:
            self.sell = {}
        else:
            self.sell = sell
    
    def best_bid(self):
        if self.buy:
            return max(self.buy.keys())
        else:
            return None
    
    def best_sell(self):
        if self.sell:
            return min(self.sell.keys())
        else:
            return None
    
    def spread(self):
        if self.buy is not None and self.sell is not None:
            return round(self.best_sell() - self.best_bid(), 4) 
        return None
    
class EventManager:
    # Manages real-time updates to the events

    def __init__(self):
        self.events = {}
        # dictionary used to match market_id to the event
    
    def initialize_event(self, market_id: str, platform: str):
        if market_id not in self.events:
            self.events[market_id] = Event(market_id, platform)
    
    def process_delta(self, market_id: str, side: str, price: float, quantity: float):
        # processes updates on prices from kalshi/polymarket and if the quantity is 0, the price is removed from the event
        event = self.events.get(market_id)
        if not event:
            return
        
        if side.upper() == "BID":
            target_dict = event.buy
        else:
            target_dict = event.sell

        if quantity <= 0:
            if price in target_dict:
                del target_dict[price]
        else:
            target_dict[price] = quantity

class ArbitrageEngine:
    # Calculates the spread and detects cross-market arbitrage opportunities

    def __init__(self, manager: EventManager, fee: float = 0.01):
        self.manager = manager
        self.fee = fee

    def cross_market_arbitrage(self, kalshi_market_id: str, polymarket_market_id: str, trade_quantity: float):
        kalshi_event = self.manager.events.get(kalshi_market_id)
        polymarket_event = self.manager.events.get(polymarket_market_id)

        if not kalshi_event or not polymarket_event:
            return
        
        kalshi_price = kalshi_event.best_sell()
        polymarket_price = polymarket_event.best_sell()

        if kalshi_price is None or polymarket_price is None:
            return
        
        kalshi_cost = (kalshi_price * trade_quantity) * (1 + self.fee)
        polymarket_cost = (polymarket_price * trade_quantity) * (1 + self.fee)

        total_cost = kalshi_cost + polymarket_cost
        payout = trade_quantity * 1.00

        net_profit = payout - total_cost

        print(f"Kalshi Spread: {kalshi_event.spread()}")
        print(f"Polymarket Spread: {polymarket_event.spread()}")
        print(f"Total Cost (for both sides): {total_cost}")

        if net_profit > 0:
            print(f"This is an arbitrage opportunity. The profit is {net_profit}")
            print(f"You need to buy {trade_quantity} of Kalshi YES at {kalshi_price}")
            print(f"You need to buy {trade_quantity} of Polymarket NO at {polymarket_price}")
        else:
            print("There is no arbitrage opportunity")

async def mock_kalshi_ws(manager: EventManager):
    """Simulates a live Kalshi WebSocket feed."""
    manager.initialize_event("KALSHI_ELECTION_YES", "Kalshi")
    
    # Initial state
    manager.process_delta("KALSHI_ELECTION_YES", "SELL", 0.53, 500)
    manager.process_delta("KALSHI_ELECTION_YES", "BID", 0.51, 300)
    
    while True:
        await asyncio.sleep(2) # Send a price update every 2 seconds
        # Randomly fluctuate the Kalshi Ask price to simulate market movement
        new_sell = round(random.uniform(0.50, 0.55), 2)
        manager.process_delta("KALSHI_ELECTION_YES", "SELL", new_sell, random.randint(100, 1000))

async def mock_poly_ws(manager: EventManager):
    """Simulates a live Polymarket WebSocket feed."""
    manager.initialize_event("POLY_ELECTION_NO", "Polymarket")
    
    # Initial state
    manager.process_delta("POLY_ELECTION_NO", "SELL", 0.49, 1000)
    manager.process_delta("POLY_ELECTION_NO", "BID", 0.47, 800)
    
    while True:
        await asyncio.sleep(1.5) # Send a price update every 1.5 seconds
        # Randomly fluctuate the Poly Ask price
        new_sell = round(random.uniform(0.45, 0.50), 2)
        manager.process_delta("POLY_ELECTION_NO", "SELL", new_sell, random.randint(100, 1000))

async def main():
    print("Starting Prediction Market Arbitrage Engine...")
    
    manager = EventManager()
    engine = ArbitrageEngine(manager, fee=0.005) # Example: 0.5% fee
    
    # Start the simulated WebSocket connections in the background
    asyncio.create_task(mock_kalshi_ws(manager))
    asyncio.create_task(mock_poly_ws(manager))
    
    # Give the WebSockets a moment to process the initial state
    await asyncio.sleep(0.5)
    
    # Main evaluation loop
    try:
        for _ in range(10): # Run for 10 iterations for demonstration
            engine.cross_market_arbitrage("KALSHI_ELECTION_YES", "POLY_ELECTION_NO", trade_quantity=100)
            await asyncio.sleep(1) # Evaluate the market every second
    except KeyboardInterrupt:
        print("Engine stopped.")

if __name__ == "__main__":
    asyncio.run(main())
    
    
