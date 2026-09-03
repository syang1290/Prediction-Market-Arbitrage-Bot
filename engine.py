import math

class Event:
    def __init__(self, event_id: str, platform: str):
        self.event_id = event_id
        self.platform = platform
        self.buy = {}  
        self.sell = {} 

    def best_bid_with_qty(self):
        if not self.buy:
            return None, 0.0
        best_p = max(self.buy.keys())
        return best_p, self.buy[best_p]

    def best_sell_with_qty(self):
        if not self.sell:
            return None, 0.0
        best_p = min(self.sell.keys())
        return best_p, self.sell[best_p]

    def spread(self):
        best_p_sell, _ = self.best_sell_with_qty()
        best_p_bid, _ = self.best_bid_with_qty()
        if best_p_sell is not None and best_p_bid is not None:
            return round(best_p_sell - best_p_bid, 4)
        return None

class EventManager:
    def __init__(self):
        self.events = {}

    def initialize_event(self, market_id: str, platform: str):
        if market_id not in self.events:
            self.events[market_id] = Event(market_id, platform)

    def process_delta(self, market_id: str, side: str, price: float, quantity: float):
        event = self.events.get(market_id)
        if not event:
            return

        target = event.buy if side.upper() == "BID" else event.sell
        if quantity <= 0:
            target.pop(price, None)
        else:
            target[price] = quantity

class ArbitrageEngine:
    def __init__(self, manager: EventManager, min_profit_threshold: float = 0.50):
        self.manager = manager
        self.min_profit_threshold = min_profit_threshold  # Minimum total dollar return

    def calculate_kalshi_taker_fee(self, price: float, qty: float) -> float:
        """
        Kalshi standard retail taker fee: 7% of expected value capped at $0.07/contract.
        Formula: ceil(0.07 * P * (1 - P) * 100) / 100 per contract.
        """
        per_contract_fee = math.ceil(0.07 * price * (1.0 - price) * 100) / 100
        return per_contract_fee * qty

    def calculate_poly_taker_fee(self, price: float, qty: float) -> float:
        """Polymarket base taker fee (typically 0% for standard event contracts)."""
        return 0.00 * price * qty

    def cross_market_arbitrage(self, kalshi_ticker: str, poly_yes_id: str, poly_no_id: str, 
                               market_name: str, target_qty: float = 50.0):
        kalshi_event = self.manager.events.get(kalshi_ticker)
        poly_yes_event = self.manager.events.get(poly_yes_id)
        poly_no_event = self.manager.events.get(poly_no_id)

        if not kalshi_event or not poly_yes_event or not poly_no_event:
            return

        # Fetch live books and top-of-book depth
        k_yes_ask, k_yes_ask_qty = kalshi_event.best_sell_with_qty()
        k_yes_bid, k_yes_bid_qty = kalshi_event.best_bid_with_qty()
        p_yes_ask, p_yes_ask_qty = poly_yes_event.best_sell_with_qty()
        p_no_ask, p_no_ask_qty = poly_no_event.best_sell_with_qty()

        # Kalshi yes, polymarket no
        if k_yes_ask is not None and p_no_ask is not None:
            executable_qty = min(target_qty, k_yes_ask_qty, p_no_ask_qty)
            if executable_qty > 0:
                k_fees = self.calculate_kalshi_taker_fee(k_yes_ask, executable_qty)
                p_fees = self.calculate_poly_taker_fee(p_no_ask, executable_qty)
                total_cost = (k_yes_ask * executable_qty) + (p_no_ask * executable_qty) + k_fees + p_fees
                payout = executable_qty * 1.00
                net_profit = payout - total_cost

                if net_profit >= self.min_profit_threshold:
                    print(f"\n[ARBITRAGE FOUND - ROUTE A] {market_name}")
                    print(f"Exec Qty: {executable_qty} contracts (Available: Kalshi={k_yes_ask_qty}, Poly={p_no_ask_qty})")
                    print(f"Leg 1: Buy Kalshi YES @ ${k_yes_ask:.3f}")
                    print(f"Leg 2: Buy Poly NO     @ ${p_no_ask:.3f}")
                    print(f"Est Fees: Kalshi=${k_fees:.2f} | Poly=${p_fees:.2f}")
                    print(f"Total Cost: ${total_cost:.2f} | Net Return: ${net_profit:.2f}")

        # Polymarket yes, kalshi no
        if p_yes_ask is not None and k_yes_bid is not None:
            k_no_ask = round(1.00 - k_yes_bid, 4)
            k_no_ask_qty = k_yes_bid_qty
            executable_qty = min(target_qty, p_yes_ask_qty, k_no_ask_qty)

            if executable_qty > 0:
                p_fees = self.calculate_poly_taker_fee(p_yes_ask, executable_qty)
                k_fees = self.calculate_kalshi_taker_fee(k_no_ask, executable_qty)
                total_cost = (p_yes_ask * executable_qty) + (k_no_ask * executable_qty) + p_fees + k_fees
                payout = executable_qty * 1.00
                net_profit = payout - total_cost

                if net_profit >= self.min_profit_threshold:
                    print(f"\n[ARBITRAGE FOUND - ROUTE B] {market_name}")
                    print(f"Exec Qty: {executable_qty} contracts (Available: Poly={p_yes_ask_qty}, Kalshi NO={k_no_ask_qty})")
                    print(f"Leg 1: Buy Poly YES    @ ${p_yes_ask:.3f}")
                    print(f"Leg 2: Buy Kalshi NO   @ ${k_no_ask:.3f} (via YES bid ${k_yes_bid:.3f})")
                    print(f"Est Fees: Poly=${p_fees:.2f} | Kalshi=${k_fees:.2f}")
                    print(f"Total Cost: ${total_cost:.2f} | Net Return: ${net_profit:.2f}")

    def intra_market_arbitrage(self, yes_token_id: str, no_token_id: str, platform: str, 
                               trade_quantity: float, market_name: str = ""):
        yes_event = self.manager.events.get(yes_token_id)
        no_event = self.manager.events.get(no_token_id)

        if not yes_event or not no_event:
            return

        yes_price, yes_qty = yes_event.best_sell_with_qty()
        no_price, no_qty = no_event.best_sell_with_qty()

        if yes_price is None or no_price is None:
            return

        executable_qty = min(trade_quantity, yes_qty, no_qty)
        if executable_qty <= 0:
            return

        total_cost = (yes_price + no_price) * executable_qty
        payout = executable_qty * 1.00
        net_profit = payout - total_cost

        if net_profit >= self.min_profit_threshold:
            print(f"\n--- {platform} Intra-Market Arbitrage Found! ---")
            print(f"Market: {market_name}")
            print(f"Exec Size: {executable_qty} contracts")
            print(f"YES Ask: {yes_price} | NO Ask: {no_price}")
            print(f"Total Cost: ${total_cost:.4f} | Profit: ${net_profit:.4f}")