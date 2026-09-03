import asyncio
import json
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from engine import EventManager, ArbitrageEngine
from market_matcher import get_or_create_matched_markets
import poly_websocket as poly
import kalshi_websocket as kalshi

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            try:
                await connection.send_text(json.dumps(message))
            except Exception:
                pass

ws_manager = ConnectionManager()
opportunity_queue = asyncio.Queue()

async def monitor_opportunities(engine: ArbitrageEngine, matched_markets: list):
    while True:
        for pair in matched_markets:
            k_ticker = pair["kalshi_ticker"]
            p_yes = pair["poly_yes_token"]
            p_no = pair["poly_no_token"]
            name = pair.get("market_name", "Cross-Platform Event")

            k_event = engine.manager.events.get(k_ticker)
            p_yes_event = engine.manager.events.get(p_yes)
            p_no_event = engine.manager.events.get(p_no)

            if not k_event or not p_yes_event or not p_no_event:
                continue

            k_yes_ask, k_yes_qty = k_event.best_sell_with_qty()
            p_no_ask, p_no_qty = p_no_event.best_sell_with_qty()

            # Route A Check: Kalshi YES + Poly NO
            if k_yes_ask is not None and p_no_ask is not None:
                exec_qty = min(50.0, k_yes_qty, p_no_qty)
                if exec_qty > 0:
                    k_fee = engine.calculate_kalshi_taker_fee(k_yes_ask, exec_qty)
                    p_fee = engine.calculate_poly_taker_fee(p_no_ask, exec_qty)
                    total_cost = (k_yes_ask * exec_qty) + (p_no_ask * exec_qty) + k_fee + p_fee
                    net_profit = (exec_qty * 1.00) - total_cost

                    if net_profit >= engine.min_profit_threshold:
                        await opportunity_queue.put({
                            "type": "CROSS_MARKET",
                            "route": "Route A (Kalshi YES + Poly NO)",
                            "market_name": name,
                            "kalshi_ticker": k_ticker,
                            "leg1": f"Buy Kalshi YES @ ${k_yes_ask:.3f}",
                            "leg2": f"Buy Poly NO @ ${p_no_ask:.3f}",
                            "quantity": exec_qty,
                            "total_cost": round(total_cost, 2),
                            "net_profit": round(net_profit, 2),
                            "roi_pct": round((net_profit / total_cost) * 100, 2),
                            "timestamp": asyncio.get_event_loop().time()
                        })

        await asyncio.sleep(1)

async def broadcaster_loop():
    while True:
        data = await opportunity_queue.get()
        await ws_manager.broadcast(data)

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await ws_manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)

@app.on_event("startup")
async def startup_event():
    manager = EventManager()
    engine = ArbitrageEngine(manager, min_profit_threshold=0.10)
    matched_pairs = get_or_create_matched_markets(refresh=False)

    poly_tokens = []
    kalshi_tickers = []
    for pair in matched_pairs:
        poly_tokens.extend([pair["poly_yes_token"], pair["poly_no_token"]])
        kalshi_tickers.append(pair["kalshi_ticker"])

    for token in set(poly_tokens):
        poly.fetch_orderbook_snapshot(manager, token)
    for ticker in set(kalshi_tickers):
        kalshi.fetch_kalshi_orderbook_snapshot(manager, ticker)

    asyncio.create_task(poly.live_poly_ws(manager, list(set(poly_tokens))))
    asyncio.create_task(kalshi.live_kalshi_ws(manager, list(set(kalshi_tickers))))
    asyncio.create_task(monitor_opportunities(engine, matched_pairs))
    asyncio.create_task(broadcaster_loop())