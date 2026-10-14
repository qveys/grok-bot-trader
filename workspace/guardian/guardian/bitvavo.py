"""Client REST Bitvavo v2 — signature HMAC-SHA256, liste blanche d'endpoints.

Référence : https://docs.bitvavo.com/docs/rest-api/introduction/
Seul le gardien instancie ce client. Aucun endpoint de retrait n'est atteignable.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import time
from decimal import Decimal

import requests

BASE_URL = "https://api.bitvavo.com"
API_PREFIX = "/v2"

# Défense en profondeur : tout appel hors de cette liste lève avant l'envoi.
ALLOWED_ENDPOINTS: frozenset[tuple[str, str]] = frozenset({
    ("GET", "/time"),
    ("GET", "/markets"),
    ("GET", "/ticker/price"),
    ("GET", "/ticker/book"),
    ("GET", "/balance"),
    ("GET", "/account"),
    ("GET", "/order"),
    ("GET", "/ordersOpen"),
    ("POST", "/order"),
    ("DELETE", "/order"),
})


class BitvavoError(RuntimeError):
    pass


class ForbiddenEndpoint(RuntimeError):
    pass


class BitvavoClient:
    def __init__(self, api_key: str, api_secret: str, access_window_ms: int = 10_000, timeout: int = 15):
        self._key = api_key
        self._secret = api_secret.encode("utf-8")
        self._window = access_window_ms
        self._timeout = timeout
        self._session = requests.Session()

    # ------------------------------------------------------------------ core
    def _sign(self, timestamp_ms: int, method: str, path_with_query: str, body: str) -> str:
        payload = f"{timestamp_ms}{method}{API_PREFIX}{path_with_query}{body}"
        return hmac.new(self._secret, payload.encode("utf-8"), hashlib.sha256).hexdigest()

    def _request(self, method: str, endpoint: str, params: dict | None = None, body: dict | None = None) -> object:
        if (method, endpoint) not in ALLOWED_ENDPOINTS:
            raise ForbiddenEndpoint(f"{method} {endpoint} n'est pas autorisé par le gardien")

        query = ""
        if params:
            query = "?" + "&".join(f"{k}={v}" for k, v in params.items())
        body_str = json.dumps(body, separators=(",", ":")) if body else ""

        now = int(time.time() * 1000)
        headers = {
            "Bitvavo-Access-Key": self._key,
            "Bitvavo-Access-Signature": self._sign(now, method, endpoint + query, body_str),
            "Bitvavo-Access-Timestamp": str(now),
            "Bitvavo-Access-Window": str(self._window),
            "Content-Type": "application/json",
        }
        url = f"{BASE_URL}{API_PREFIX}{endpoint}{query}"
        resp = self._session.request(method, url, headers=headers, data=body_str or None, timeout=self._timeout)
        try:
            data = resp.json()
        except ValueError as exc:
            raise BitvavoError(f"Réponse non JSON ({resp.status_code}) sur {method} {endpoint}") from exc
        if resp.status_code >= 400 or (isinstance(data, dict) and "errorCode" in data):
            raise BitvavoError(f"{method} {endpoint} -> {resp.status_code} {data}")
        return data

    # ------------------------------------------------------------------ public
    def server_time_ms(self) -> int:
        return int(self._request("GET", "/time")["time"])

    def markets(self) -> dict[str, dict]:
        """market -> {minOrderInQuoteAsset, minOrderInBaseAsset, pricePrecision, status, ...}"""
        return {m["market"]: m for m in self._request("GET", "/markets")}

    def ticker_prices(self, markets: tuple[str, ...]) -> dict[str, Decimal]:
        data = self._request("GET", "/ticker/price")
        wanted = set(markets)
        return {d["market"]: Decimal(d["price"]) for d in data if d["market"] in wanted and d.get("price")}

    def ticker_book(self, market: str) -> tuple[Decimal, Decimal]:
        d = self._request("GET", "/ticker/book", params={"market": market})
        return Decimal(d["bid"]), Decimal(d["ask"])

    # ------------------------------------------------------------------ private
    def balances(self) -> dict[str, Decimal]:
        """symbol -> available + inOrder"""
        out: dict[str, Decimal] = {}
        for b in self._request("GET", "/balance"):
            total = Decimal(b.get("available", "0")) + Decimal(b.get("inOrder", "0"))
            if total > 0:
                out[b["symbol"]] = total
        return out

    def account(self) -> dict:
        return self._request("GET", "/account")

    def open_orders(self) -> list[dict]:
        return self._request("GET", "/ordersOpen")

    def get_order(self, market: str, order_id: str) -> dict:
        return self._request("GET", "/order", params={"market": market, "orderId": order_id})

    def create_limit_order(self, market: str, side: str, amount: Decimal, price: Decimal,
                           post_only: bool = True) -> dict:
        # Bitvavo : postOnly existe sur les ordres limit ; appliqué seulement aux ordres agent.
        assert side in ("buy", "sell")
        body = {
            "market": market,
            "side": side,
            "orderType": "limit",
            "amount": f"{amount.normalize():f}",
            "price": f"{price.normalize():f}",
        }
        if post_only:
            body["postOnly"] = True
        return self._request("POST", "/order", body=body)

    def cancel_order(self, market: str, order_id: str) -> dict:
        return self._request("DELETE", "/order", params={"market": market, "orderId": order_id})
