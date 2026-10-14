#!/usr/bin/env python3
"""Validate a Revolut X spot order against guardian limits. No live API calls.

Paper (simulation) rules only:
  - size ≤ max_position_pct × bankroll
  - stop obligatoire (stop_pct or stop_price / safety_price)
  - exposition totale simulation ≤ paper_max_exposure_pct (9 oct, choix Quentin : 0.10 → 50 € à 500 €)
    (longs + shorts / idée à la baisse) ; repli sur max_exposure_pct si la clé manque
  - un ordre LIVE (live_place.py appelle ce script avec --live) garde max_exposure_pct (0.05 → 25 €)
  - paires autorisées
  - ordre limité
  - PAS d'exigence gain ≥ 3× coûts (live only, in live_place.py)
  - heure limite (`deadline` / `deadline_at`, ISO local) = rappel seulement : absente, déjà passée
    ou illisible → avertissement (warnings), jamais de refus

Live path here stays the broader legacy checks (size, exposure, kelly, DD, daily, cash…).
Expectancy 3× remains exclusive to live_place.py — never applied in this script.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

GUARDIAN = Path(__file__).resolve().parent.parent
ROOT = Path(os.environ.get("PREDICT_BOT_ROOT", str(GUARDIAN.parent)))
CONFIG_PATH = Path(os.environ.get("GUARDIAN_CONFIG", str(GUARDIAN / "config.json")))
STATE_PATH = Path(os.environ.get("GUARDIAN_STATE", str(GUARDIAN / "state.json")))
MODE_PATH = Path(os.environ.get("MODE_FILE", str(ROOT / "MODE")))
STOP_PATH = Path(os.environ.get("STOP_FILE", str(ROOT / "STOP")))
HALTED_PATH = GUARDIAN / "HALTED"


def _today_brussels():
    from datetime import datetime
    from zoneinfo import ZoneInfo

    return datetime.now(ZoneInfo("Europe/Brussels")).strftime("%Y-%m-%d")


def _daily_pnl_today(state):
    """Daily P&L resets each day (Brussels): stale value from a previous day counts as 0."""
    if state.get("daily_pnl_date") != _today_brussels():
        return 0.0
    return float(state.get("daily_pnl_eur", 0) or 0)


def load_json(path: Path) -> dict:
    return json.loads(path.read_text())


REAL_ROOT = Path("/workspace/predict-market-bot")


def now_local():
    """Europe/Brussels now. TEST ONLY: PMB_FAKE_NOW honoured in a copied tree with TEST_MARKER."""
    import time as _t
    from datetime import datetime as _dt
    from zoneinfo import ZoneInfo as _ZI
    tz = _ZI("Europe/Brussels")
    raw = os.environ.get("PMB_FAKE_NOW")
    if raw and os.environ.get("TEST_MARKER"):
        try:
            if GUARDIAN.parent.resolve() != REAL_ROOT.resolve() and ROOT.resolve() != REAL_ROOT.resolve():
                dt = _dt.fromisoformat(raw)
                return dt.replace(tzinfo=tz) if dt.tzinfo is None else dt.astimezone(tz)
        except (OSError, ValueError):
            pass
    return _dt.now(tz)


def parse_deadline(raw):
    """`deadline` / `deadline_at`: ISO local datetime (naive = Europe/Brussels). Returns aware datetime,
    None if absent; raises ValueError if present but invalid."""
    from datetime import datetime as _dt
    from zoneinfo import ZoneInfo as _ZI
    if raw is None or str(raw).strip() == "":
        return None
    dt = _dt.fromisoformat(str(raw).strip().replace("Z", "+00:00"))
    tz = _ZI("Europe/Brussels")
    return dt.replace(tzinfo=tz) if dt.tzinfo is None else dt.astimezone(tz)


def order_deadline_raw(order: dict):
    return order.get("deadline") if order.get("deadline") not in (None, "") else order.get("deadline_at")


def load_order(args: argparse.Namespace) -> dict:
    if args.order:
        return load_json(Path(args.order))
    raw = sys.stdin.read()
    if not raw.strip():
        raise SystemExit("No order JSON on stdin and no --order path given")
    return json.loads(raw)


def equity(state: dict) -> float:
    """Cash + mark of open positions (cost basis if no mark)."""
    cash = float(state.get("cash_eur", 0) or 0)
    pos_val = 0.0
    for p in state.get("positions") or []:
        if p.get("status", "open") != "open":
            continue
        pos_val += (-1.0 if (str(p.get("side") or "").lower() in ("short","sell") or str(p.get("idea_type") or p.get("kind") or "").lower() == "baisse") else 1.0) * float(p.get("mark_eur", p.get("cost_eur", 0)) or 0)  # baisse = rachat dû
    return cash + pos_val


def open_positions(state: dict) -> list[dict]:
    return [p for p in (state.get("positions") or []) if p.get("status", "open") == "open"]


def exposure_eur(state: dict) -> float:
    """Notional of all open positions (long + short / idée à la baisse)."""
    total = 0.0
    for p in open_positions(state):
        total += float(p.get("cost_eur", p.get("amount_eur", 0)) or 0)
    return total


def drawdown_pct(state: dict) -> float:
    peak = float(state.get("peak_equity_eur", 0) or 0)
    eq = equity(state)
    if peak <= 0:
        bankroll = float(state.get("bankroll_eur", 0) or 0)
        peak = max(bankroll, eq)
    if peak <= 0:
        return 0.0
    return max(0.0, (peak - eq) / peak)


def daily_loss_pct(state: dict) -> float:
    bankroll = float(state.get("bankroll_eur", 0) or 0)
    daily = _daily_pnl_today(state)
    if bankroll <= 0:
        return 0.0 if daily >= 0 else 1.0
    if daily >= 0:
        return 0.0
    return abs(daily) / bankroll


def resolve_idea_type(order: dict) -> str:
    raw = order.get("idea_type") or order.get("kind")
    if raw is None or str(raw).strip() == "":
        return ""  # unset → legacy
    v = str(raw).strip().lower()
    if v in ("baisse", "short", "sell_first"):
        return "baisse"
    if v in ("hausse", "long"):
        return "hausse"
    return v


def is_rebuy_order(order: dict, idea_type: str) -> bool:
    if order.get("rebuy_reason") or order.get("linked_position_id") or order.get("cycle_id"):
        return True
    if idea_type == "baisse" and str(order.get("side", "")).lower() == "buy":
        return True
    return False


def is_baisse_open(order: dict, idea_type: str) -> bool:
    return idea_type == "baisse" and str(order.get("side", "")).lower() == "sell"


def has_stop(order: dict, side: str, idea_type: str, is_rebuy: bool) -> bool:
    """Stop required for opening a new paper cycle; not for closes/rebuys."""
    if is_rebuy:
        return True  # N/A
    if side == "sell" and idea_type != "baisse":
        return True  # closing long — stop not required
    if order.get("stop_price") is not None or order.get("safety_price") is not None:
        return True
    if order.get("stop_price_eur") is not None:
        return True
    if order.get("stop_pct") is not None:
        return True
    return False


def inventory_available(state: dict, pair: str, venue: str) -> float:
    inv = state.get("paper_inventory") or {}
    asset = pair.split("-")[0].upper()
    v = (venue or "revolut_x").lower()
    if v in ("metamask_uniswap", "metamask", "metamask_arbitrum", "uniswap"):
        mm = inv.get("metamask_arbitrum") or {}
        return float(mm.get(asset, 0) or 0)
    return float(inv.get(asset, 0) or 0)


def target_side_reason(order: dict, side: str, idea_type: str, rebuy: bool, baisse_open: bool, price: float) -> str | None:
    """Objectif (target_price) du bon côté, refus sinon (9 oct) — même règle que le prix d'arrêt d'une baisse :
    idée à la hausse (achat d'ouverture) → objectif AU-DESSUS du prix ; idée à la baisse (vente) → EN DESSOUS."""
    tp = order.get("target_price")
    if tp is None:
        return None
    try:
        tp = float(tp)
    except (TypeError, ValueError):
        return "target_price invalide"
    if side == "buy" and not rebuy and tp <= price:
        return f"target_price {tp} doit être AU-DESSUS du prix d'achat {price}"
    if baisse_open and tp >= price:
        return f"target_price {tp} doit être EN DESSOUS du prix de vente {price}"
    return None


def validate(order: dict, cfg: dict, state: dict, live: bool = False) -> dict:
    """live=True: called by live_place.py (real order) → exposure cap max_exposure_pct even when
    MODE=paper (LIVE_ONCE). Paper/simulation orders use paper_max_exposure_pct."""
    reasons: list[str] = []
    warnings: list[str] = []

    # Kill / halt
    if STOP_PATH.exists():
        reasons.append(f"kill switch STOP present at {STOP_PATH}")
    if HALTED_PATH.exists():
        reasons.append(f"HALTED file present at {HALTED_PATH}")
    if bool(state.get("halted")):
        reasons.append("state.halted is true")

    # MODE
    mode = MODE_PATH.read_text().strip() if MODE_PATH.exists() else ""
    if mode not in ("paper", "live"):
        reasons.append(f"MODE must be paper|live, got {mode!r}")

    # Required fields
    pair = str(order.get("pair", "")).strip().upper()
    side = str(order.get("side", "")).strip().lower()
    otype = str(order.get("type", "")).strip().lower()
    idea_type = resolve_idea_type(order)
    rebuy = is_rebuy_order(order, idea_type)
    baisse_open = is_baisse_open(order, idea_type)
    venue = str(order.get("venue") or "revolut_x").strip().lower()

    try:
        price = float(order["price"])
        amount_eur = float(order["amount_eur"]) if order.get("amount_eur") is not None else None
        qty = float(order["qty"]) if order.get("qty") is not None else None
        if amount_eur is None and qty is not None and price > 0:
            amount_eur = qty * price
        if amount_eur is None:
            raise KeyError("amount_eur")
        amount_eur = float(amount_eur)
        if qty is None and price > 0:
            qty = amount_eur / price
    except (KeyError, TypeError, ValueError) as e:
        reasons.append(f"invalid price/amount_eur: {e}")
        return {"ok": False, "reasons": reasons, "max_amount_eur": 0.0, "mode": mode}

    if side not in ("buy", "sell"):
        reasons.append(f"side must be buy|sell, got {side!r}")
    if price <= 0:
        reasons.append(f"price must be > 0, got {price}")
    if amount_eur <= 0:
        reasons.append(f"amount_eur must be > 0, got {amount_eur}")

    # Whitelist / order type / market / leverage
    whitelist = [str(p).upper() for p in cfg.get("pairs_whitelist", [])]
    if pair not in whitelist:
        reasons.append(f"pair {pair!r} not in whitelist {whitelist}")

    allowed_types = [str(t).lower() for t in cfg.get("order_types", ["limit"])]
    if otype not in allowed_types:
        reasons.append(f"order type {otype!r} not allowed; need one of {allowed_types}")

    if not cfg.get("market_orders", False) and otype == "market":
        reasons.append("market orders disabled")

    if cfg.get("leverage") is True:
        reasons.append("config.leverage unexpectedly true — refuse")
    if order.get("leverage") not in (None, False, 0, "false", "0"):
        reasons.append("leverage requested but leverage is disabled")

    if cfg.get("post_only", True) and order.get("post_only") is False:
        reasons.append("post_only required by config")

    # Optional stop_pct sanity
    if "stop_pct" in order and order["stop_pct"] is not None:
        try:
            stop_pct = float(order["stop_pct"])
            if side == "buy" and idea_type != "baisse" and stop_pct > 0:
                reasons.append("stop_pct for buy should be negative (loss threshold)")
            if abs(stop_pct) > 100:
                reasons.append(f"stop_pct {stop_pct} out of range")
        except (TypeError, ValueError):
            reasons.append("stop_pct must be a number")

    # Heure limite (deadline, Predict 8 oct) = reminder only (Quentin 8 oct 23h): past/unreadable/missing → warn, never refuse
    opens_new_any = (side == "buy" and not rebuy) or baisse_open
    dl_raw = order_deadline_raw(order)
    try:
        dl = parse_deadline(dl_raw)
    except (TypeError, ValueError):
        dl = None
        warnings.append(f"heure limite (deadline) illisible: {dl_raw!r} — rappel ignoré, ne bloque pas")
    if dl is not None and opens_new_any and dl <= now_local():
        warnings.append(f"heure limite déjà passée ({dl.isoformat(timespec='minutes')}) — rappel seulement, ne bloque pas")
    if dl_raw in (None, "") and opens_new_any and mode == "paper":
        warnings.append("heure limite (deadline) absente — pas de rappel pour cette position")

    bankroll = float(state.get("bankroll_eur", 0) or 0)
    max_pos_pct = float(cfg.get("max_position_pct", 0.05))
    max_exposure_pct = float(cfg.get("max_exposure_pct", 0.25))
    live_exposure_pct = max_exposure_pct
    if mode == "paper" and not live:
        # Simulation: plafond total à part (9 oct, Quentin : 10 % = 50 €) ; live inchangé (max_exposure_pct)
        max_exposure_pct = float(cfg.get("paper_max_exposure_pct", live_exposure_pct))
    max_dd = float(cfg.get("max_drawdown_pct", 0.08))
    max_daily = float(cfg.get("max_daily_loss_pct", 0.15))
    max_concurrent = int(cfg.get("max_concurrent", 15))
    kelly_fraction = float(cfg.get("kelly_fraction", 0.25))

    pos_cap = max_pos_pct * bankroll
    existing = exposure_eur(state)
    exposure_room = max(0.0, max_exposure_pct * bankroll - existing)
    kelly_cap = kelly_fraction * bankroll

    # Paper: only position cap + exposure room (no kelly hard-block)
    if mode == "paper":
        max_amount = min(pos_cap, exposure_room) if bankroll > 0 else 0.0
    else:
        max_amount = min(pos_cap, exposure_room, kelly_cap) if bankroll > 0 else 0.0

    if bankroll <= 0:
        reasons.append("bankroll_eur is 0 — set bankroll before trading")

    # --- Paper-only gate set (simulation ≠ live) ---
    # No expectancy / 3× coûts check here (live_place only).
    if mode == "paper":
        opens_new = (side == "buy" and not rebuy) or baisse_open
        if opens_new and amount_eur > pos_cap + 1e-9:
            reasons.append(
                f"amount_eur {amount_eur} > max_position_pct*bankroll {pos_cap:.4f}"
            )
        if opens_new and existing + amount_eur > max_exposure_pct * bankroll + 1e-9:
            reasons.append(
                f"exposure+amount {existing + amount_eur:.4f} > "
                f"max_exposure {max_exposure_pct * bankroll:.4f}"
            )
        if opens_new and not has_stop(order, side, idea_type, rebuy):
            reasons.append(
                "stop obligatoire en simulation (stop_pct ou stop_price / safety_price)"
            )
        if baisse_open:
            if order.get("decision_id") is None or str(order.get("decision_id")).strip() == "":
                reasons.append("decision_id obligatoire pour idée à la baisse")
            stop_p = order.get("stop_price")
            if stop_p is None:
                stop_p = order.get("safety_price") or order.get("stop_price_eur")
            if stop_p is not None:
                try:
                    if float(stop_p) <= price:
                        reasons.append(
                            f"stop_price {stop_p} doit être AU-DESSUS du prix de vente {price}"
                        )
                except (TypeError, ValueError):
                    reasons.append("stop_price invalide")
            avail = inventory_available(state, pair, venue)
            need = float(qty or 0)
            if need > avail + 1e-12:
                reasons.append(
                    f"inventaire insuffisant: besoin {need} {pair.split('-')[0]}, dispo {avail}"
                )
        tgt_reason = target_side_reason(order, side, idea_type, rebuy, baisse_open, price)
        if tgt_reason:
            reasons.append(tgt_reason)
        if rebuy:
            linked = order.get("linked_position_id") or order.get("cycle_id")
            shorts = [
                p
                for p in open_positions(state)
                if str(p.get("pair", "")).upper() == pair
                and (
                    str(p.get("side", "")).lower() in ("short", "sell")
                    or p.get("idea_type") == "baisse"
                )
            ]
            if linked:
                shorts = [p for p in shorts if p.get("id") == linked]
            if not shorts:
                reasons.append(f"aucun short ouvert à racheter pour {pair}")
            cash = float(state.get("cash_eur", 0) or 0)
            if amount_eur > cash + 1e-9:
                reasons.append(f"amount_eur {amount_eur} > cash_eur {cash:.4f}")
        elif side == "buy":
            cash = float(state.get("cash_eur", 0) or 0)
            if amount_eur > cash + 1e-9:
                reasons.append(f"amount_eur {amount_eur} > cash_eur {cash:.4f}")
        elif side == "sell" and not baisse_open:
            matching = [
                p
                for p in open_positions(state)
                if str(p.get("pair", "")).upper() == pair
                and str(p.get("side", "long")).lower() in ("long", "buy")
                and p.get("idea_type", "hausse") != "baisse"
            ]
            if not matching:
                reasons.append(f"no open position for pair {pair} to sell")
            else:
                held = sum(
                    float(p.get("cost_eur", p.get("amount_eur", 0)) or 0) for p in matching
                )
                if amount_eur > held + 1e-9:
                    reasons.append(
                        f"sell amount_eur {amount_eur} > held cost {held:.4f}"
                    )

        ok = len(reasons) == 0
        return {
            "ok": ok,
            "reasons": reasons,
            "warnings": warnings,
            "max_amount_eur": round(max(0.0, max_amount), 4),
            "mode": mode,
        }

    # --- Live / non-paper: legacy full checks (unchanged intent) ---
    if amount_eur > pos_cap + 1e-9:
        reasons.append(
            f"amount_eur {amount_eur} > max_position_pct*bankroll {pos_cap:.4f}"
        )
    if side == "buy" and existing + amount_eur > max_exposure_pct * bankroll + 1e-9:
        reasons.append(
            f"exposure+amount {existing + amount_eur:.4f} > "
            f"max_exposure {max_exposure_pct * bankroll:.4f}"
        )
    if amount_eur > kelly_cap + 1e-9 and bankroll > 0:
        reasons.append(
            f"amount_eur {amount_eur} > kelly_fraction*bankroll {kelly_cap:.4f}"
        )

    tgt_reason = target_side_reason(order, side, idea_type, rebuy, baisse_open, price)
    if tgt_reason:
        reasons.append(tgt_reason)

    dd = drawdown_pct(state)
    if dd >= max_dd:
        reasons.append(f"drawdown {dd:.4f} >= max_drawdown_pct {max_dd}")

    dl = daily_loss_pct(state)
    if dl >= max_daily:
        reasons.append(f"daily_loss_pct {dl:.4f} >= max_daily_loss_pct {max_daily}")

    opens = open_positions(state)
    if side == "buy":
        pairs_open = {str(p.get("pair", "")).upper() for p in opens}
        would_add = pair not in pairs_open
        concurrent = len(opens) + (1 if would_add else 0)
        if would_add and len(opens) >= max_concurrent:
            reasons.append(
                f"open_positions {len(opens)} >= max_concurrent {max_concurrent}"
            )
        elif concurrent > max_concurrent:
            reasons.append(
                f"concurrent would be {concurrent} > max_concurrent {max_concurrent}"
            )

    if side == "sell":
        matching = [p for p in opens if str(p.get("pair", "")).upper() == pair]
        if not matching:
            reasons.append(f"no open position for pair {pair} to sell")
        else:
            held = sum(float(p.get("cost_eur", p.get("amount_eur", 0)) or 0) for p in matching)
            if amount_eur > held + 1e-9:
                reasons.append(
                    f"sell amount_eur {amount_eur} > held cost {held:.4f}"
                )
    else:
        cash = float(state.get("cash_eur", 0) or 0)
        if amount_eur > cash + 1e-9:
            reasons.append(f"amount_eur {amount_eur} > cash_eur {cash:.4f}")

    ok = len(reasons) == 0
    return {
        "ok": ok,
        "reasons": reasons,
        "warnings": warnings,
        "max_amount_eur": round(max(0.0, max_amount), 4),
        "mode": mode,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate Revolut X order vs guardian")
    parser.add_argument("--order", type=str, help="Path to order JSON file")
    parser.add_argument("--live", action="store_true",
                        help="Real (live) order from live_place.py: exposure cap = max_exposure_pct")
    args = parser.parse_args()

    try:
        cfg = load_json(CONFIG_PATH)
        state = load_json(STATE_PATH) if STATE_PATH.exists() else {}
        order = load_order(args)
        result = validate(order, cfg, state, live=args.live)
    except (KeyError, ValueError, json.JSONDecodeError, OSError) as e:
        out = {"ok": False, "reasons": [f"validation error: {e}"], "max_amount_eur": 0.0}
        print(json.dumps(out))
        return 1

    print(
        json.dumps(
            {
                "ok": result["ok"],
                "reasons": result["reasons"],
                "warnings": result.get("warnings") or [],
                "max_amount_eur": result["max_amount_eur"],
            }
        )
    )
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
