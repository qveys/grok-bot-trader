#!/usr/bin/env python3
"""Prix en direct (léger, sans IA, sans appel réseau) : lit les ticks 30 s du collecteur
de l'équipe (state/price_ticks/YYYY-MM-DD.jsonl, LECTURE SEULE) et écrit site/data/prices.json.

Variation 24 h : calculée sur les ticks (tick le plus proche d'il y a 24 h, ±15 min) ;
sinon repli sur la variation des tickers Revolut X mise en cache par build.py (cache/prices.json).
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

ROOT = os.path.dirname(os.path.abspath(__file__))
TZ = ZoneInfo("Europe/Brussels")
UTC = timezone.utc
PAIRS = ("BTC-EUR", "ETH-EUR", "SOL-EUR")
STALE_SEC = 120


def _bot_dir():
    try:
        with open(os.path.join(ROOT, "config.json"), encoding="utf-8") as f:
            return json.load(f).get("BOT_DIR", "/workspace/predict-market-bot")
    except Exception:
        return "/workspace/predict-market-bot"


TICKS = os.path.join(_bot_dir(), "state", "price_ticks")


def _ts(s):
    try:
        d = datetime.fromisoformat(str(s).replace("Z", "+00:00"))
        return (d if d.tzinfo else d.replace(tzinfo=UTC)).astimezone(UTC)
    except Exception:
        return None


def _tail(path, nbytes=4000):
    try:
        with open(path, "rb") as f:
            f.seek(0, 2)
            size = f.tell()
            f.seek(max(0, size - nbytes))
            lines = f.read().decode("utf-8", "replace").splitlines()
        if size > nbytes:
            lines = lines[1:]
        out = []
        for ln in lines:
            try:
                out.append(json.loads(ln))
            except Exception:
                pass
        return out
    except Exception:
        return []


def read_ticks(day: str):
    out = []
    try:
        with open(os.path.join(TICKS, f"{day}.jsonl"), encoding="utf-8", errors="replace") as f:
            for ln in f:
                try:
                    out.append(json.loads(ln))
                except Exception:
                    pass
    except Exception:
        pass
    return out


def ticks_since(since: datetime):
    """Tous les ticks depuis `since` (fichiers jour par jour, heure de Bruxelles)."""
    out = []
    d = since.astimezone(TZ).date()
    end = datetime.now(TZ).date()
    while d <= end:
        for t in read_ticks(d.isoformat()):
            ts = _ts(t.get("ts"))
            if ts and ts >= since:
                t["_ts"] = ts
                out.append(t)
        d += timedelta(days=1)
    return out


def _near(ticks, pair, target, tol_min=15):
    best, bd = None, None
    for t in ticks:
        if t.get("pair") != pair:
            continue
        ts = _ts(t.get("ts"))
        if not ts:
            continue
        dd = abs((ts - target).total_seconds())
        if bd is None or dd < bd:
            best, bd = t, dd
    return best if bd is not None and bd <= tol_min * 60 else None


def build_prices(now=None):
    now = now or datetime.now(UTC)
    today = now.astimezone(TZ).date()
    latest = {}
    for day in (today, today - timedelta(days=1)):
        for t in _tail(os.path.join(TICKS, f"{day.isoformat()}.jsonl")):
            p, ts = t.get("pair"), _ts(t.get("ts"))
            if p in PAIRS and ts and (p not in latest or ts > latest[p][0]):
                latest[p] = (ts, t)
        if len(latest) == len(PAIRS):
            break
    target = now - timedelta(hours=24)
    old_ticks = read_ticks(target.astimezone(TZ).date().isoformat())
    cache = {}
    try:
        with open(os.path.join(ROOT, "cache", "prices.json"), encoding="utf-8") as f:
            cache = json.load(f).get("prices", {})
    except Exception:
        pass
    pairs = {}
    for p in PAIRS:
        if p in latest:
            ts, t = latest[p]
            mid = float(t.get("mid"))
            ref = _near(old_ticks, p, target)
            if ref and ref.get("mid"):
                ch, src = (mid / float(ref["mid"]) - 1) * 100, "ticks"
            elif (cache.get(p) or {}).get("change_24h_pct") is not None:
                ch, src = cache[p]["change_24h_pct"], "revolut"
            else:
                ch, src = None, None
            age = (now - ts).total_seconds()
            pairs[p] = {"mid": round(mid, 6), "bid": t.get("bid"), "ask": t.get("ask"), "ts": ts.isoformat().replace("+00:00", "Z"),
                        "age_s": round(age, 1), "stale": age > STALE_SEC, "tick_source": t.get("source"),
                        "change_24h_pct": None if ch is None else round(ch, 2), "change_source": src, "source": "collecteur 30 s"}
        elif p in cache:
            pairs[p] = {"mid": cache[p].get("mid"), "ts": None, "age_s": None, "stale": True,
                        "change_24h_pct": cache[p].get("change_24h_pct"), "change_source": "revolut", "source": "Revolut X (repli, cache 5 min)"}
    last = max([v[0] for v in latest.values()], default=None)
    return {"generated_at": now.isoformat().replace("+00:00", "Z"), "pairs": pairs,
            "last_tick_at": last.isoformat().replace("+00:00", "Z") if last else None,
            "stale": (last is None) or (now - last).total_seconds() > STALE_SEC, "stale_after_s": STALE_SEC,
            "source": "state/price_ticks/*.jsonl (collecteur de l'équipe, toutes les 30 s)"}


def write(path=None):
    path = path or os.path.join(ROOT, "site", "data", "prices.json")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    d = build_prices()
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False, indent=1)
    os.replace(tmp, path)
    return d


if __name__ == "__main__":
    d = write()
    if "-v" in sys.argv:
        print(json.dumps(d, ensure_ascii=False, indent=1))
