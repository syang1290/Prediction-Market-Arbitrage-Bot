# aysncio

class Event:
    def __init__(self, event_id: int, platform: str, buy: dict, sell: dict):
        self.event_id = event_id
        self.platform = platform

        # event_id is the ID of the event
        # platform describes which platform (polymarket/kalshi)

        # buy are prices that people are willing to buy at
        # key is price, value is amount of shares
        self.buy = buy

        # sell are prices that people are willing to sell at
        # key is price, value is amount of shares
        self.sell = sell
    
