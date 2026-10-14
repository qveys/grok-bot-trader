#!/usr/bin/env python3
"""Paper/demo market scanner — Polymarket gamma public API. No orders.

NOTE: Primary Belgium path is Revolut X crypto spot paper — use
scripts/scan_crypto.py instead. This script is Polymarket discovery-only
(geo-blocked for trading); kept for optional research discovery.
"""

from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = ROOT / "config.json"
OUT_PATH = ROOT / "state" / "last_scan.json"
GAMMA_BASE = "https://gamma-api.polymarket.com/markets?limit=100&active=true&closed=false"
# Prefer near-expiry and high 24h volume pages so max_days_to_expiry filter can match.
GAMMA_URLS = [
    GAMMA_BASE + "&order=endDate&ascending=true",
    GAMMA_BASE + "&order=volume24hr&ascending=false",
]
GAMMA_URL = GAMMA_URLS[0]


def load_config() -> dict:
    return json.loads(CONFIG_PATH.read_text())


def fetch_markets(url: str, timeout: int = 25) -> list:
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "predict-market-bot/0.1 (paper-scan)"},
        method="GET",
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        return data.get("markets") or data.get("data") or []
    return []


def parse_float(val, default=None):
    if val is None:
        return default
    try:
        return float(val)
    except (TypeError, ValueError):
        return default


def parse_end_date(m: dict):
    for key in ("endDate", "end_date_iso", "endDateIso", "closeTime", "expiration"):
        raw = m.get(key)
        if not raw:
            continue
        try:
            s = str(raw).replace("Z", "+00:00")
            return datetime.fromisoformat(s)
        except ValueError:
            continue
    return None


def volume_of(m: dict) -> float:
    for key in ("volumeNum", "volume", "volume24hr", "volumeClob"):
        v = parse_float(m.get(key))
        if v is not None:
            return v
    return 0.0


def liquidity_of(m: dict) -> float:
    for key in ("liquidityNum", "liquidity", "liquidityClob"):
        v = parse_float(m.get(key))
        if v is not None:
            return v
    return 0.0


def spread_cents(m: dict):
    bid = parse_float(m.get("bestBid"))
    ask = parse_float(m.get("bestAsk"))
    if bid is None or ask is None:
        # try nested clob token prices
        return None
    return abs(ask - bid) * 100.0


def mid_price(m: dict):
    bid = parse_float(m.get("bestBid"))
    ask = parse_float(m.get("bestAsk"))
    if bid is not None and ask is not None:
        return (bid + ask) / 2.0
    # lastTradePrice / outcomePrices
    last = parse_float(m.get("lastTradePrice"))
    if last is not None:
        return last
    prices = m.get("outcomePrices")
    if isinstance(prices, str):
        try:
            prices = json.loads(prices)
        except json.JSONDecodeError:
            prices = None
    if isinstance(prices, list) and prices:
        return parse_float(prices[0])
    return None


def score_market(m: dict, scan_cfg: dict, now: datetime) -> dict | None:
    vol = volume_of(m)
    liq = liquidity_of(m)
    end = parse_end_date(m)
    max_days = int(scan_cfg.get("max_days_to_expiry", 30))
    min_vol = float(scan_cfg.get("min_volume_contracts", 200))
    min_liq = float(scan_cfg.get("min_liquidity_usd", 1000))
    max_spread = float(scan_cfg.get("max_spread_cents", 5))

    if vol < min_vol:
        return None
    if liq > 0 and liq < min_liq:
        return None

    days_to_expiry = None
    if end is not None:
        if end.tzinfo is None:
            end = end.replace(tzinfo=timezone.utc)
        days_to_expiry = (end - now).total_seconds() / 86400.0
        if days_to_expiry < 0 or days_to_expiry > max_days:
            return None

    spr = spread_cents(m)
    anomalies = []
    if spr is not None and spr > max_spread:
        anomalies.append(f"wide_spread_{spr:.1f}c")

    mid = mid_price(m)
    # Rank: prefer higher volume, tighter spread, nearer expiry with liquidity
    spread_penalty = (spr if spr is not None else 10.0)
    rank = vol * 0.001 + liq * 0.01 - spread_penalty * 2.0
    if days_to_expiry is not None:
        rank += max(0.0, 30.0 - days_to_expiry) * 0.5

    return {
        "id": m.get("id") or m.get("conditionId") or m.get("slug"),
        "question": m.get("question") or m.get("title") or "",
        "slug": m.get("slug"),
        "volume": vol,
        "liquidity": liq,
        "best_bid": parse_float(m.get("bestBid")),
        "best_ask": parse_float(m.get("bestAsk")),
        "mid": mid,
        "spread_cents": spr,
        "end_date": end.isoformat() if end else None,
        "days_to_expiry": round(days_to_expiry, 2) if days_to_expiry is not None else None,
        "anomalies": anomalies,
        "rank_score": round(rank, 4),
        "platform": "polymarket",
    }


def write_scan(payload: dict) -> None:
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(payload, indent=2) + "\n")


def main() -> int:
    now = datetime.now(timezone.utc)
    try:
        cfg = load_config()
    except (OSError, json.JSONDecodeError) as e:
        write_scan(
            {
                "scanned_at": now.isoformat(),
                "markets": [],
                "error": f"config load failed: {e}",
                "count": 0,
            }
        )
        print(f"scan error (config): {e}")
        return 0

    scan_cfg = cfg.get("scan", {})
    raw = []
    fetch_errors = []
    seen_ids = set()
    for url in GAMMA_URLS:
        try:
            batch = fetch_markets(url)
            for m in batch:
                if not isinstance(m, dict):
                    continue
                mid = m.get("id") or m.get("conditionId") or m.get("slug")
                if mid in seen_ids:
                    continue
                seen_ids.add(mid)
                raw.append(m)
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, OSError, json.JSONDecodeError) as e:
            fetch_errors.append(f"{url}: {e}")

    if not raw and fetch_errors:
        write_scan(
            {
                "scanned_at": now.isoformat(),
                "markets": [],
                "error": f"network/fetch failed: {'; '.join(fetch_errors)}",
                "count": 0,
                "source": GAMMA_URLS,
            }
        )
        print(f"scan: network failure — empty scan written ({fetch_errors})")
        return 0

    ranked = []
    for m in raw:
        if not isinstance(m, dict):
            continue
        scored = score_market(m, scan_cfg, now)
        if scored:
            ranked.append(scored)

    ranked.sort(key=lambda x: x["rank_score"], reverse=True)
    anomalous = sum(1 for x in ranked if x["anomalies"])

    payload = {
        "scanned_at": now.isoformat(),
        "source": GAMMA_URLS,
        "filters": scan_cfg,
        "raw_fetched": len(raw),
        "count": len(ranked),
        "anomalous_count": anomalous,
        "markets": ranked,
        "error": None,
    }
    write_scan(payload)

    print(
        f"scan ok: fetched={len(raw)} passed_filters={len(ranked)} "
        f"anomalies={anomalous} -> {OUT_PATH}"
    )
    for row in ranked[:5]:
        q = (row["question"] or "")[:70]
        print(
            f"  [{row['rank_score']:.1f}] vol={row['volume']:.0f} "
            f"liq={row['liquidity']:.0f} mid={row['mid']} | {q}"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
