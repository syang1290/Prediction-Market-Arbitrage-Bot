# aysncio

class Event:
    def __init__(self, event_id: str, platform: str, buy: dict, sell: dict):
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
            return max(self.sell.keys())
        else:
            return None
    
    def spread(self):
        if self.buy is not None and self.sell is not None:
            return round(self.best_bid - self.best_sell, 4)
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

        
    
    
