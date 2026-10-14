#!/usr/bin/env python3
"""Crypto spot paper scanner for Revolut X pipeline.

Fetches PUBLIC spot prices only (Binance / Coinbase / Kraken).
Does NOT call Revolut order or trading APIs. No secrets access.
"""

from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = ROOT / "config.json"
GUARDIAN_CONFIG = ROOT / "guardian" / "config.json"
OUT_PATH = ROOT / "state" / "last_scan.json"
HISTORY_PATH = ROOT / "state" / "scan_history.jsonl"
DEFAULT_STOP = ROOT / "STOP"
UA = "predict-market-bot/0.1 (crypto-paper-scan; public-ticker-only)"

# Box egress often needs the local tunnel proxy for DNS/HTTPS
import os
import time

_PROXY = os.environ.get("HTTPS_PROXY") or os.environ.get("HTTP_PROXY") or "http://127.0.0.1:8791"
# Keep an existing opener if already installed; only install once with proxy
if not getattr(urllib.request, "_pm_bot_proxy_installed", False):
    _opener = urllib.request.build_opener(
        urllib.request.ProxyHandler({"http": _PROXY, "https": _PROXY})
    )
    urllib.request.install_opener(_opener)
    urllib.request._pm_bot_proxy_installed = True  # type: ignore[attr-defined]

# Public venue endpoints (no auth). Prefer EUR pairs when available.
BINANCE_24H = "https://api.binance.com/api/v3/ticker/24hr?symbol={sym}"
BINANCE_BOOK = "https://api.binance.com/api/v3/ticker/bookTicker?symbol={sym}"
COINBASE_TICKER = "https://api.exchange.coinbase.com/products/{pair}/ticker"
COINBASE_STATS = "https://api.exchange.coinbase.com/products/{pair}/stats"
KRAKEN_TICKER = "https://api.kraken.com/0/public/Ticker?pair={pair}"

# Map whitelist pair -> per-venue symbols
PAIR_MAP = {
    "BTC-EUR": {
        "binance": "BTCEUR",
        "coinbase": "BTC-EUR",
        "kraken": "XBTEUR",
    },
    "ETH-EUR": {
        "binance": "ETHEUR",
        "coinbase": "ETH-EUR",
        "kraken": "ETHEUR",
    },
    "SOL-EUR": {
        "binance": "SOLEUR",
        "coinbase": "SOL-EUR",
        "kraken": "SOLEUR",
    },
}


def load_config() -> dict:
    return json.loads(CONFIG_PATH.read_text())


def stop_path(cfg: dict) -> Path:
    return Path(cfg.get("kill_switch_path", str(DEFAULT_STOP)))


def pairs_whitelist(cfg: dict) -> list[str]:
    rx = (cfg.get("platforms") or {}).get("revolut_x") or {}
    pairs = rx.get("pairs_whitelist_hint") or []
    if pairs:
        return list(pairs)
    if GUARDIAN_CONFIG.exists():
        try:
            g = json.loads(GUARDIAN_CONFIG.read_text())
            gp = g.get("pairs_whitelist") or []
            if gp:
                return list(gp)
        except (OSError, json.JSONDecodeError):
            pass
    return ["BTC-EUR", "ETH-EUR", "SOL-EUR"]


def http_json(url: str, timeout: int = 15, attempts: int = 3, backoff_s: float = 2.0) -> dict | list:
    """GET JSON with retries (3 attempts, 2s backoff) on fetch failures."""
    last_err: BaseException | None = None
    for i in range(attempts):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA}, method="GET")
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except (
            urllib.error.HTTPError,
            urllib.error.URLError,
            TimeoutError,
            OSError,
            json.JSONDecodeError,
        ) as e:
            last_err = e
            # Do not burn retries on hard 4xx other than 429
            if isinstance(e, urllib.error.HTTPError) and e.code != 429 and 400 <= e.code < 500:
                raise
            if i < attempts - 1:
                time.sleep(backoff_s)
    assert last_err is not None
    raise last_err


def is_rate_limited(exc: BaseException) -> bool:
    if isinstance(exc, urllib.error.HTTPError) and exc.code == 429:
        return True
    msg = str(exc).lower()
    return "429" in msg or "too many" in msg or "rate" in msg


def parse_float(val, default=None):
    if val is None:
        return default
    try:
        return float(val)
    except (TypeError, ValueError):
        return default


def fetch_binance(pair: str) -> dict | None:
    sym = PAIR_MAP[pair]["binance"]
    t24 = http_json(BINANCE_24H.format(sym=sym))
    if not isinstance(t24, dict):
        return None
    price = parse_float(t24.get("lastPrice") or t24.get("weightedAvgPrice"))
    change = parse_float(t24.get("priceChangePercent"))
    vol = parse_float(t24.get("quoteVolume"))  # EUR quote volume
    bid = ask = spread_pct = None
    try:
        book = http_json(BINANCE_BOOK.format(sym=sym))
        if isinstance(book, dict):
            bid = parse_float(book.get("bidPrice"))
            ask = parse_float(book.get("askPrice"))
            if bid and ask and bid > 0:
                mid = (bid + ask) / 2.0
                spread_pct = abs(ask - bid) / mid * 100.0
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, OSError, json.JSONDecodeError):
        pass
    if price is None:
        return None
    return {
        "source": "binance",
        "price_eur": price,
        "change_24h_pct": change,
        "volume_24h": vol,
        "bid": bid,
        "ask": ask,
        "spread_pct": spread_pct,
    }


def fetch_coinbase(pair: str) -> dict | None:
    cb = PAIR_MAP[pair]["coinbase"]
    tick = http_json(COINBASE_TICKER.format(pair=cb))
    if not isinstance(tick, dict):
        return None
    price = parse_float(tick.get("price"))
    bid = parse_float(tick.get("bid"))
    ask = parse_float(tick.get("ask"))
    spread_pct = None
    if bid and ask and bid > 0:
        mid = (bid + ask) / 2.0
        spread_pct = abs(ask - bid) / mid * 100.0
    change = vol = None
    try:
        stats = http_json(COINBASE_STATS.format(pair=cb))
        if isinstance(stats, dict):
            open_p = parse_float(stats.get("open"))
            last_p = parse_float(stats.get("last")) or price
            if open_p and open_p > 0 and last_p is not None:
                change = (last_p - open_p) / open_p * 100.0
            vol = parse_float(stats.get("volume"))
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, OSError, json.JSONDecodeError):
        pass
    if price is None:
        return None
    return {
        "source": "coinbase",
        "price_eur": price,
        "change_24h_pct": change,
        "volume_24h": vol,
        "bid": bid,
        "ask": ask,
        "spread_pct": spread_pct,
    }


def fetch_kraken(pair: str) -> dict | None:
    kp = PAIR_MAP[pair]["kraken"]
    data = http_json(KRAKEN_TICKER.format(pair=kp))
    if not isinstance(data, dict):
        return None
    result = data.get("result") or {}
    # Kraken may rename pair keys (e.g. XETHZEUR)
    ticker = None
    for key, val in result.items():
        if isinstance(val, dict) and "c" in val:
            ticker = val
            break
    if not ticker:
        return None
    # c = last trade [price, lot], o = today open, v = volume [today, 24h],
    # b = bid, a = ask
    price = parse_float((ticker.get("c") or [None])[0])
    open_p = parse_float(ticker.get("o"))
    change = None
    if price is not None and open_p and open_p > 0:
        change = (price - open_p) / open_p * 100.0
    vol = parse_float((ticker.get("v") or [None, None])[1])  # 24h volume (base)
    bid = parse_float((ticker.get("b") or [None])[0])
    ask = parse_float((ticker.get("a") or [None])[0])
    spread_pct = None
    if bid and ask and bid > 0:
        mid = (bid + ask) / 2.0
        spread_pct = abs(ask - bid) / mid * 100.0
    if price is None:
        return None
    return {
        "source": "kraken",
        "price_eur": price,
        "change_24h_pct": change,
        "volume_24h": vol,
        "bid": bid,
        "ask": ask,
        "spread_pct": spread_pct,
    }


FETCHERS = [
    ("binance", fetch_binance),
    ("coinbase", fetch_coinbase),
    ("kraken", fetch_kraken),
]


def fetch_pair(pair: str) -> tuple[dict | None, list[str]]:
    """Try public sources in order; on 429 skip to next."""
    errors: list[str] = []
    if pair not in PAIR_MAP:
        return None, [f"unsupported pair {pair}"]
    for name, fn in FETCHERS:
        try:
            row = fn(pair)
            if row:
                return row, errors
            errors.append(f"{name}: empty")
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, OSError, json.JSONDecodeError) as e:
            errors.append(f"{name}: {e}")
            if is_rate_limited(e):
                continue
            continue
    return None, errors


def anomaly_flags(row: dict, move_thresh: float, max_spread_pct: float = 0.5) -> list[str]:
    flags: list[str] = []
    ch = row.get("change_24h_pct")
    if ch is not None and abs(ch) > move_thresh:
        flags.append(f"price_move_{ch:+.2f}pct")
    sp = row.get("spread_pct")
    if sp is not None and sp > max_spread_pct:
        flags.append(f"wide_spread_{sp:.3f}pct")
    return flags


def rank_reason(pair: str, row: dict, flags: list[str], rank: int) -> str:
    parts = [f"rank#{rank}", f"pair={pair}", f"src={row.get('source')}"]
    ch = row.get("change_24h_pct")
    if ch is not None:
        parts.append(f"24h={ch:+.2f}%")
    vol = row.get("volume_24h")
    if vol is not None:
        parts.append(f"vol24h={vol:.0f}")
    if flags:
        parts.append("anomalies=" + ",".join(flags))
    else:
        parts.append("no_anomaly_flags")
    parts.append("handoff=directional_spot_edge_research")
    return "; ".join(parts)


def score_row(row: dict, flags: list[str]) -> float:
    """Higher = more interesting for research handoff."""
    score = 0.0
    ch = abs(row.get("change_24h_pct") or 0.0)
    score += ch * 10.0
    vol = row.get("volume_24h") or 0.0
    # Normalize rough EUR volume (Binance quote) vs base volume (Kraken)
    score += min(vol, 1e9) * 1e-6
    score += len(flags) * 25.0
    sp = row.get("spread_pct")
    if sp is not None:
        score -= sp * 5.0  # prefer tighter spreads
    return score



def append_scan_history(payload: dict) -> None:
    """Append one compact line per successful scan for price evolution."""
    if not payload.get("pairs") and not payload.get("markets"):
        return
    row = {
        "scanned_at": payload.get("scanned_at"),
        "sources": payload.get("sources_used"),
        "anomalous_count": payload.get("anomalous_count"),
        "prices": {
            m["pair"]: {
                "price_eur": m.get("price_eur"),
                "change_24h_pct": m.get("change_24h_pct"),
                "spread_pct": m.get("spread_pct"),
                "volume_24h": m.get("volume_24h"),
                "anomaly_flags": m.get("anomaly_flags") or [],
            }
            for m in (payload.get("pairs") or payload.get("markets") or [])
            if m.get("pair")
        },
    }
    HISTORY_PATH.parent.mkdir(parents=True, exist_ok=True)
    with HISTORY_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")


def write_scan(payload: dict) -> None:
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(payload, indent=2) + "\n")


def main() -> int:
    try:
        from zoneinfo import ZoneInfo
        now = datetime.now(ZoneInfo("Europe/Brussels"))
    except Exception:
        now = datetime.now(timezone.utc)
    now_iso = now.isoformat()

    try:
        cfg = load_config()
    except (OSError, json.JSONDecodeError) as e:
        write_scan(
            {
                "scanned_at": now_iso,
                "venue": "revolut_x_paper",
                "pairs": [],
                "count": 0,
                "error": f"config load failed: {e}",
            }
        )
        print(f"scan_crypto error (config): {e}")
        return 0

    stop = stop_path(cfg)
    if stop.exists():
        note = {
            "scanned_at": now_iso,
            "venue": "revolut_x_paper",
            "halted": True,
            "reason": f"STOP present at {stop}",
            "pairs": [],
            "count": 0,
            "error": "halted",
        }
        write_scan(note)
        print(f"KILL: STOP present at {stop} — crypto scan halted")
        return 2

    scan_cfg = cfg.get("scan") or {}
    move_thresh = float(scan_cfg.get("anomaly_price_move_pct", 10))
    # Convert max_spread_cents (event markets) to a loose crypto pct default
    max_spread_pct = float(scan_cfg.get("anomaly_spread_pct", 0.5))

    pairs = pairs_whitelist(cfg)
    sources_used: list[str] = []
    fetch_errors: list[str] = []
    scored: list[dict] = []

    for pair in pairs:
        raw, errs = fetch_pair(pair)
        fetch_errors.extend(f"{pair}: {e}" for e in errs)
        if not raw:
            print(f"scan_crypto: failed to price {pair}: {errs}")
            continue
        sources_used.append(raw["source"])
        flags = anomaly_flags(raw, move_thresh, max_spread_pct)
        scored.append(
            {
                "pair": pair,
                "raw": raw,
                "flags": flags,
                "score": score_row(raw, flags),
            }
        )

    scored.sort(key=lambda x: x["score"], reverse=True)

    markets: list[dict] = []
    for i, item in enumerate(scored, start=1):
        pair = item["pair"]
        raw = item["raw"]
        flags = item["flags"]
        markets.append(
            {
                "id": f"revolut_x_paper:{pair}",
                "platform": "revolut_x_paper",
                "pair": pair,
                "price_eur": round(raw["price_eur"], 6) if raw.get("price_eur") is not None else None,
                "change_24h_pct": (
                    round(raw["change_24h_pct"], 4) if raw.get("change_24h_pct") is not None else None
                ),
                "volume_24h": raw.get("volume_24h"),
                "spread_pct": (
                    round(raw["spread_pct"], 6) if raw.get("spread_pct") is not None else None
                ),
                "bid": raw.get("bid"),
                "ask": raw.get("ask"),
                "price_source": raw.get("source"),
                "anomaly_flags": flags,
                "rank_score": round(item["score"], 4),
                "rank_reason": rank_reason(pair, raw, flags, i),
                "scanned_at": now_iso,
            }
        )

    payload = {
        "scanned_at": now_iso,
        "venue": "revolut_x_paper",
        "primary_venue": cfg.get("primary_venue", "revolut_x"),
        "mode": "paper",
        "trading": False,
        "note": "Public spot prices only; Revolut order/trading APIs not called.",
        "pairs_whitelist": pairs,
        "filters": {
            "anomaly_price_move_pct": move_thresh,
            "anomaly_spread_pct": max_spread_pct,
        },
        "sources_used": sorted(set(sources_used)),
        "fetch_errors": fetch_errors or None,
        "count": len(markets),
        "anomalous_count": sum(1 for m in markets if m["anomaly_flags"]),
        "markets": markets,
        "pairs": markets,  # alias for crypto handoff consumers
        "error": None if markets else ("all public sources failed" if fetch_errors else "no pairs"),
    }
    write_scan(payload)
    append_scan_history(payload)

    print(
        f"scan_crypto ok: pairs={len(markets)} anomalies="
        f"{payload['anomalous_count']} sources={payload['sources_used']} -> {OUT_PATH}"
    )
    for m in markets:
        print(
            f"  [{m['rank_score']:.1f}] {m['pair']} "
            f"price_eur={m['price_eur']} 24h={m['change_24h_pct']}% "
            f"spread={m['spread_pct']} flags={m['anomaly_flags']} "
            f"| {m['rank_reason']}"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
