"""Client REST Revolut X — signature Ed25519, liste blanche d'endpoints.

Référence : https://developer.revolut.com/docs/api/revolut-x-crypto-exchange
Expose la même interface que BitvavoClient pour que le gardien reste inchangé.

Sécurité structurelle : l'API Revolut X ne contient aucun endpoint de retrait,
dépôt ou transfert. La liste blanche ci-dessous fige en plus notre propre surface
d'appel, au cas où l'API s'étendrait un jour.

Notes d'adaptation :
- Symboles : "BTC-EUR" côté gardien et dans les paths ; les réponses utilisent
  "BTC/EUR", normalisé ici en tirets.
- Ordres agent : limit + execution_instructions ["post_only"] -> 0 % maker garanti,
  rejet si le prix croise le carnet (le rejet est journalisé, le bot l'apprend).
- Ordres de protection (stop_loss/death/dilemma) : sans post_only, exécution
  immédiate acceptée (taker 0,09 %). La survie prime sur les frais.
"""
from __future__ import annotations

import base64
import json
import time
import uuid
from decimal import Decimal
from pathlib import Path

import requests
from cryptography.hazmat.primitives import serialization

BASE_URL = "https://revx.revolut.com"
API_PREFIX = "/api"

ALLOWED_ENDPOINTS: frozenset[tuple[str, str]] = frozenset({
    ("GET", "/1.0/tickers"),
    ("GET", "/1.0/configuration/pairs"),
    ("GET", "/1.0/balances"),
    ("GET", "/1.0/orders/active"),
    ("GET", "/1.0/orders/{id}"),
    ("POST", "/1.0/orders"),
    ("DELETE", "/1.0/orders/{id}"),
    ("DELETE", "/1.0/orders"),        # cancel all : procédure de mort/halt
})

FINAL_STATES = {"filled", "cancelled", "canceled", "rejected", "expired"}


class RevolutXError(RuntimeError):
    pass


class ForbiddenEndpoint(RuntimeError):
    pass


def _dash(symbol: str) -> str:
    return symbol.replace("/", "-").upper()


class RevolutXClient:
    def __init__(self, api_key: str, private_key_path: str, timeout: int = 15):
        self._key = api_key
        pem = Path(private_key_path).read_bytes()
        self._sk = serialization.load_pem_private_key(pem, password=None)
        self._session = requests.Session()
        self._timeout = timeout

    # ------------------------------------------------------------------ core
    def _sign(self, timestamp_ms: int, method: str, path: str, query: str, body: str) -> str:
        message = f"{timestamp_ms}{method}{API_PREFIX}{path}{query}{body}".encode("utf-8")
        return base64.b64encode(self._sk.sign(message)).decode("ascii")

    def _request(self, method: str, endpoint_pattern: str, path: str,
                 params: dict | None = None, body: dict | None = None) -> object:
        if (method, endpoint_pattern) not in ALLOWED_ENDPOINTS:
            raise ForbiddenEndpoint(f"{method} {endpoint_pattern} n'est pas autorisé par le gardien")
        query = "&".join(f"{k}={v}" for k, v in params.items()) if params else ""
        body_str = json.dumps(body, separators=(",", ":")) if body else ""
        now = int(time.time() * 1000)
        headers = {
            "X-Revx-API-Key": self._key,
            "X-Revx-Timestamp": str(now),
            "X-Revx-Signature": self._sign(now, method, path, query, body_str),
        }
        if body_str:
            headers["Content-Type"] = "application/json"
        url = f"{BASE_URL}{API_PREFIX}{path}" + (f"?{query}" if query else "")
        resp = self._session.request(method, url, headers=headers, data=body_str or None, timeout=self._timeout)
        if resp.status_code == 204:
            return {}
        try:
            data = resp.json()
        except ValueError as exc:
            raise RevolutXError(f"Réponse non JSON ({resp.status_code}) sur {method} {path}") from exc
        if resp.status_code >= 400:
            raise RevolutXError(f"{method} {path} -> {resp.status_code} {str(data)[:300]}")
        return data

    # ------------------------------------------------------------------ interface commune (cf. BitvavoClient)
    def server_time_ms(self) -> int:
        data = self._request("GET", "/1.0/tickers", "/1.0/tickers")
        return int(data["metadata"]["timestamp"])

    def markets(self) -> dict[str, dict]:
        data = self._request("GET", "/1.0/configuration/pairs", "/1.0/configuration/pairs")
        out: dict[str, dict] = {}
        for symbol, cfg in data.items():
            out[_dash(symbol)] = {
                "market": _dash(symbol),
                "status": "trading" if cfg.get("status") == "active" else str(cfg.get("status")),
                "minOrderInQuoteAsset": cfg.get("min_order_size_quote", "0.01"),
                # base_step sert de pas d'arrondi pour le montant en base asset
                "minOrderInBaseAsset": cfg.get("base_step", "0.00000001"),
                "quote_step": cfg.get("quote_step", "0.01"),
            }
        return out

    def _tickers(self, markets: tuple[str, ...]) -> dict[str, dict]:
        params = {"symbols": ",".join(markets)}
        data = self._request("GET", "/1.0/tickers", "/1.0/tickers", params=params)
        return {_dash(t["symbol"]): t for t in data["data"]}

    def ticker_prices(self, markets: tuple[str, ...]) -> dict[str, Decimal]:
        return {m: Decimal(t["mid"]) for m, t in self._tickers(markets).items() if t.get("mid")}

    def ticker_book(self, market: str) -> tuple[Decimal, Decimal]:
        t = self._tickers((market,))[market]
        return Decimal(t["bid"]), Decimal(t["ask"])

    def balances(self) -> dict[str, Decimal]:
        out: dict[str, Decimal] = {}
        for b in self._request("GET", "/1.0/balances", "/1.0/balances"):
            total = Decimal(b.get("available", "0")) + Decimal(b.get("reserved", "0"))
            if total > 0:
                out[b["currency"]] = total
        return out

    def open_orders(self) -> list[dict]:
        data = self._request("GET", "/1.0/orders/active", "/1.0/orders/active")
        return data.get("data", [])

    def get_order(self, market: str, order_id: str) -> dict:
        data = self._request("GET", "/1.0/orders/{id}", f"/1.0/orders/{order_id}")
        o = data["data"]
        filled = Decimal(str(o.get("filled_quantity", "0")))
        avg = Decimal(str(o.get("average_fill_price", "0") or "0"))
        return {
            "status": str(o.get("status", "")).lower().replace("canceled", "cancelled"),
            "filledAmount": str(filled),
            "filledAmountQuote": str(filled * avg),
            "total_fee": str(o.get("total_fee", "0")),
        }

    def create_limit_order(self, market: str, side: str, amount: Decimal, price: Decimal,
                           post_only: bool = True) -> dict:
        assert side in ("buy", "sell")
        limit: dict = {"base_size": f"{amount.normalize():f}", "price": f"{price.normalize():f}"}
        limit["execution_instructions"] = ["post_only"] if post_only else ["allow_taker"]
        body = {
            "client_order_id": str(uuid.uuid4()),
            "symbol": _dash(market),
            "side": side,
            "order_configuration": {"limit": limit},
        }
        data = self._request("POST", "/1.0/orders", "/1.0/orders", body=body)
        entry = data["data"][0] if isinstance(data.get("data"), list) else data["data"]
        return {"orderId": str(entry["venue_order_id"])}

    def cancel_order(self, market: str, order_id: str) -> dict:
        self._request("DELETE", "/1.0/orders/{id}", f"/1.0/orders/{order_id}")
        return {}

    def cancel_all_orders(self) -> dict:
        self._request("DELETE", "/1.0/orders", "/1.0/orders")
        return {}
