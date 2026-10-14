"""Client Bitvavo simulé pour les tests hors ligne (aucun réseau)."""
from __future__ import annotations

import time
from decimal import Decimal


class FakeClient:
    def __init__(self, prices: dict[str, Decimal], eur: Decimal = Decimal("50")):
        self.prices = dict(prices)
        self.eur = eur
        self.crypto: dict[str, Decimal] = {}
        self.orders: dict[str, dict] = {}
        self._seq = 0

    def server_time_ms(self):
        return int(time.time() * 1000)

    def markets(self):
        return {m: {"market": m, "status": "trading", "minOrderInQuoteAsset": "5", "minOrderInBaseAsset": "0.0001"}
                for m in self.prices}

    def ticker_prices(self, markets):
        return {m: self.prices[m] for m in markets if m in self.prices}

    def ticker_book(self, market):
        p = self.prices[market]
        return p * Decimal("0.999"), p * Decimal("1.001")

    def balances(self):
        out = {"EUR": self.eur}
        out.update({k: v for k, v in self.crypto.items() if v > 0})
        return out

    def open_orders(self):
        return [o for o in self.orders.values() if o["status"] == "new"]

    def get_order(self, market, order_id):
        return self.orders[order_id]

    def create_limit_order(self, market, side, amount, price, post_only=True):
        self._seq += 1
        oid = f"fake-{self._seq}"
        self.orders[oid] = {"orderId": oid, "market": market, "side": side, "amount": str(amount),
                            "price": str(price), "status": "new", "filledAmount": "0", "filledAmountQuote": "0"}
        return self.orders[oid]

    def cancel_order(self, market, order_id):
        self.orders[order_id]["status"] = "canceled"
        return self.orders[order_id]

    # --- helpers de test
    def fill(self, order_id):
        o = self.orders[order_id]
        amt, px = Decimal(o["amount"]), Decimal(o["price"])
        base = o["market"].split("-")[0]
        if o["side"] == "buy":
            self.eur -= amt * px
            self.crypto[base] = self.crypto.get(base, Decimal("0")) + amt
        else:
            self.eur += amt * px
            self.crypto[base] = self.crypto.get(base, Decimal("0")) - amt
        o.update(status="filled", filledAmount=str(amt), filledAmountQuote=str(amt * px))
