#!/usr/bin/env python3
"""Simulate a paper fill into guardian state + ../state/trades_log.jsonl. No live API.

Supports:
  - idée à la hausse (default / idea_type "hausse"): buy opens long, sell closes long
  - idée à la baisse (idea_type/kind "baisse"): sell opens short from paper_inventory,
    buy with linked_position_id / cycle_id closes (rebuy)

After every successful OPEN (hausse buy / baisse sell) the stop watcher
(watch_stops.py) is started detached if not already running (watcher_launch.py);
before an open, if paper positions are open but no watcher is alive, it is started too.
Output JSON carries watcher_started / watcher_already_running.
Disable with PAPER_FILL_NO_WATCH=1 (tests).

Heure limite: optional `deadline` (alias `deadline_at`, ISO local Europe/Brussels) is stored
on the opened position; reminder only (watch_stops writes state/deadline_reminder.json, closes nothing
unless guardian/config.json deadline.close_enabled=true).
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
try:
    import watcher_launch  # noqa: E402
except Exception:  # never block a paper fill on the launcher
    watcher_launch = None  # type: ignore[assignment]
import state_summary  # noqa: E402  (champs tableau + verrou/écriture atomique de state.json)

GUARDIAN = Path(__file__).resolve().parent.parent
ROOT = Path(os.environ.get("PREDICT_BOT_ROOT", str(GUARDIAN.parent)))
STATE_PATH = Path(os.environ.get("GUARDIAN_STATE", str(GUARDIAN / "state.json")))
TRADES_PATH = Path(os.environ.get("TRADES_LOG", str(ROOT / "state" / "trades_log.jsonl")))
VALIDATE = GUARDIAN / "scripts" / "validate_order.py"
MODE_PATH = Path(os.environ.get("MODE_FILE", str(ROOT / "MODE")))

# One-way fee rates (fraction of notional)
FEE_REVOLUT = 0.0005  # 0.05 % — half of 10 bps RT estimate
FEE_METAMASK = 0.0005  # 0.05 % per Uniswap swap

DEFAULT_PAPER_INVENTORY = {
    "ETH": 0.02085589,
    "SOL": 0.241308,
    "metamask_arbitrum": {"ETH": 0.0387},
}


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def load_json(path: Path) -> dict:
    return json.loads(path.read_text())


def save_json(path: Path, data: dict) -> None:
    """Atomic write (tmp + replace). Callers writing STATE_PATH hold state_summary.state_lock."""
    state_summary.atomic_write_json(path, data)


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


def deadline_iso(order: dict) -> str | None:
    """Normalized deadline (ISO with Brussels offset) or None. validate_order already refused invalid."""
    try:
        dl = parse_deadline(order_deadline_raw(order))
    except (TypeError, ValueError):
        return None
    return dl.isoformat() if dl else None


def load_order(args: argparse.Namespace) -> dict:
    if args.order:
        return load_json(Path(args.order))
    raw = sys.stdin.read()
    if not raw.strip():
        raise SystemExit("No order JSON on stdin and no --order path given")
    return json.loads(raw)


def run_validate(order: dict) -> tuple[dict, int]:
    env = os.environ.copy()
    proc = subprocess.run(
        [sys.executable, str(VALIDATE)],
        input=json.dumps(order),
        text=True,
        capture_output=True,
        env=env,
    )
    try:
        result = json.loads(proc.stdout.strip() or "{}")
    except json.JSONDecodeError:
        result = {
            "ok": False,
            "reasons": [f"validate_order bad stdout: {proc.stdout!r} {proc.stderr!r}"],
            "max_amount_eur": 0.0,
        }
    return result, proc.returncode


def base_asset(pair: str) -> str:
    return pair.split("-")[0].upper()


def resolve_idea_type(order: dict) -> str:
    raw = order.get("idea_type") or order.get("kind")
    if raw is None or str(raw).strip() == "":
        return "hausse"  # compat: missing → hausse (legacy behaviour)
    v = str(raw).strip().lower()
    if v in ("baisse", "short", "sell_first"):
        return "baisse"
    if v in ("hausse", "long"):
        return "hausse"
    return v


def ensure_paper_inventory(state: dict) -> dict:
    """Initialize paper_inventory once; never overwrite existing block."""
    if "paper_inventory" not in state or not isinstance(state.get("paper_inventory"), dict):
        state["paper_inventory"] = json.loads(json.dumps(DEFAULT_PAPER_INVENTORY))
    inv = state["paper_inventory"]
    # Ensure expected keys exist without wiping custom balances
    if "ETH" not in inv:
        inv["ETH"] = DEFAULT_PAPER_INVENTORY["ETH"]
    if "SOL" not in inv:
        inv["SOL"] = DEFAULT_PAPER_INVENTORY["SOL"]
    if "metamask_arbitrum" not in inv or not isinstance(inv.get("metamask_arbitrum"), dict):
        inv["metamask_arbitrum"] = dict(DEFAULT_PAPER_INVENTORY["metamask_arbitrum"])
    elif "ETH" not in inv["metamask_arbitrum"]:
        inv["metamask_arbitrum"]["ETH"] = DEFAULT_PAPER_INVENTORY["metamask_arbitrum"]["ETH"]
    return inv


def fee_rate_for_venue(venue: str) -> float:
    v = (venue or "revolut_x").lower()
    if v in ("metamask_uniswap", "metamask", "metamask_arbitrum", "uniswap"):
        return FEE_METAMASK
    return FEE_REVOLUT


def inventory_available(inv: dict, asset: str, venue: str) -> float:
    v = (venue or "revolut_x").lower()
    if v in ("metamask_uniswap", "metamask", "metamask_arbitrum", "uniswap"):
        mm = inv.get("metamask_arbitrum") or {}
        return float(mm.get(asset, 0) or 0)
    return float(inv.get(asset, 0) or 0)


def inventory_debit(inv: dict, asset: str, venue: str, qty: float) -> None:
    v = (venue or "revolut_x").lower()
    if v in ("metamask_uniswap", "metamask", "metamask_arbitrum", "uniswap"):
        mm = inv.setdefault("metamask_arbitrum", {})
        mm[asset] = float(mm.get(asset, 0) or 0) - qty
    else:
        inv[asset] = float(inv.get(asset, 0) or 0) - qty


def inventory_credit(inv: dict, asset: str, venue: str, qty: float) -> None:
    v = (venue or "revolut_x").lower()
    if v in ("metamask_uniswap", "metamask", "metamask_arbitrum", "uniswap"):
        mm = inv.setdefault("metamask_arbitrum", {})
        mm[asset] = float(mm.get(asset, 0) or 0) + qty
    else:
        inv[asset] = float(inv.get(asset, 0) or 0) + qty


def resolve_qty_amount(order: dict, price: float) -> tuple[float, float]:
    """Return (qty, amount_eur). Prefer explicit qty when present."""
    amount_eur = float(order["amount_eur"]) if order.get("amount_eur") is not None else None
    qty = float(order["qty"]) if order.get("qty") is not None else None
    if qty is not None and qty > 0:
        if amount_eur is None or amount_eur <= 0:
            amount_eur = qty * price
        return qty, float(amount_eur)
    if amount_eur is None or amount_eur <= 0 or price <= 0:
        raise ValueError("need positive amount_eur and price (or qty)")
    return amount_eur / price, float(amount_eur)


def recompute_equity(state: dict) -> None:
    """equity (cash ± mark, short = − rachat dû) + champs tableau (9 oct) after every fill/close:
    exposure_eur, exposure_pct, unrealized_pnl_eur, total_pnl_eur, drawdown_pct, summary_updated_at.
    A position opened here gets last_mid_eur = fill price and mark_ts (the watcher re-marks it each loop)."""
    ts = state_summary.now_local_iso()
    for p in state.get("positions") or []:
        if p.get("status", "open") == "open" and not p.get("mark_ts"):
            qty = float(p.get("qty") or 0)
            if qty > 0:
                p["last_mid_eur"] = round(float(p.get("mark_eur", p.get("cost_eur", 0)) or 0) / qty, 8)
                p["mark_ts"] = ts
    state_summary.refresh_summary(state, ts=ts)


def _clean_id(v) -> str | None:
    """decision_id / position id as a stripped string, None if empty."""
    if v is None:
        return None
    v = str(v).strip()
    return v or None


def order_risk_level(order: dict) -> str | None:
    """Niveau de risque de la décision (prudente / equilibree / risquee), stocké tel quel (9 oct)."""
    return _clean_id(order.get("risk_level"))


def _is_short_pos(p: dict) -> bool:
    return str(p.get("side", "")).lower() in ("short", "sell") or p.get("idea_type") == "baisse"


def find_close_target(positions: list, pair: str, order: dict, *, want_short: bool) -> dict | None:
    """Position ouverte à fermer (9 oct : une décision = une position).

    Ordre de priorité : linked_position_id / position_id / cycle_id (doit exister et être ouverte),
    puis decision_id (doit correspondre à une seule position ouverte de la paire), puis la seule
    position ouverte du bon sens sur la paire. Plusieurs candidates sans identifiant → refus
    (jamais « la » position de la paire au hasard).
    """
    opens = [
        p for p in positions
        if p.get("status", "open") == "open"
        and str(p.get("pair", "")).upper() == pair
        and _is_short_pos(p) == want_short
    ]
    kind = "short (baisse)" if want_short else "long (hausse)"
    pid = _clean_id(order.get("linked_position_id") or order.get("position_id") or order.get("cycle_id"))
    if pid:
        for p in opens:
            if str(p.get("id")) == pid:
                return p
        raise ValueError(f"position {pid} introuvable ou déjà fermée ({kind} {pair})")
    did = _clean_id(order.get("decision_id"))
    if did:
        hits = [p for p in opens if _clean_id(p.get("decision_id")) == did]
        if len(hits) == 1:
            return hits[0]
        if len(hits) > 1:
            raise ValueError(
                f"{len(hits)} positions {kind} {pair} ouvertes pour {did} — préciser linked_position_id"
            )
        raise ValueError(f"aucune position {kind} {pair} ouverte pour la décision {did}")
    if len(opens) == 1:
        return opens[0]
    if not opens:
        return None
    ids = ", ".join(f"{p.get('id')} ({p.get('decision_id') or '-'})" for p in opens)
    raise ValueError(
        f"{len(opens)} positions {kind} {pair} ouvertes — préciser linked_position_id ou decision_id : {ids}"
    )


def apply_fill(state: dict, order: dict) -> dict:
    pair = str(order["pair"]).strip().upper()
    side = str(order["side"]).strip().lower()
    price = float(order["price"])
    qty, amount_eur = resolve_qty_amount(order, price)
    ts = now_iso()
    trade_id = f"rx-paper-{ts.replace(':', '')}-{uuid.uuid4().hex[:8]}"
    idea_type = resolve_idea_type(order)
    venue = str(order.get("venue") or "revolut_x").strip().lower()
    if venue in ("metamask", "metamask_arbitrum", "uniswap"):
        venue = "metamask_uniswap"
    if venue not in ("revolut_x", "metamask_uniswap"):
        venue = "revolut_x"
    fee_pct = fee_rate_for_venue(venue)
    fee_eur = round(amount_eur * fee_pct, 6)
    mode = MODE_PATH.read_text().strip() if MODE_PATH.exists() else "paper"
    asset = base_asset(pair)
    risk_level = order_risk_level(order)

    positions = list(state.get("positions") or [])
    cash = float(state.get("cash_eur", 0) or 0)
    inv = ensure_paper_inventory(state)

    # --- Idée à la baisse: OPEN short (sell) ---
    if side == "sell" and idea_type == "baisse":
        decision_id = order.get("decision_id")
        if decision_id is None or str(decision_id).strip() == "":
            raise ValueError("decision_id obligatoire pour ouvrir une idée à la baisse")
        avail = inventory_available(inv, asset, venue)
        if qty > avail + 1e-12:
            raise ValueError(
                f"inventaire insuffisant: besoin {qty} {asset} ({venue}), dispo {avail}"
            )
        stop_price = order.get("stop_price")
        if stop_price is None:
            stop_price = order.get("safety_price") or order.get("stop_price_eur")
        if stop_price is None:
            raise ValueError("stop_price (prix de rachat de sécurité) obligatoire pour baisse")
        stop_price = float(stop_price)
        target_price = order.get("target_price")
        target_price = float(target_price) if target_price is not None else None
        if stop_price <= price:
            raise ValueError(
                f"stop_price {stop_price} doit être AU-DESSUS du prix de vente {price}"
            )
        if target_price is not None and target_price >= price:
            raise ValueError(
                f"target_price {target_price} doit être EN DESSOUS du prix de vente {price}"
            )

        inventory_debit(inv, asset, venue, qty)
        cash += amount_eur - fee_eur

        positions.append(
            {
                "id": trade_id,
                "pair": pair,
                "side": "short",
                "idea_type": "baisse",
                "kind": "baisse",
                "qty": qty,
                "avg_price": price,
                "cost_eur": amount_eur,
                "mark_eur": amount_eur,
                "stop_price": stop_price,
                "stop_price_eur": stop_price,
                "safety_price": stop_price,
                "target_price": target_price,
                "decision_id": str(decision_id).strip(),
                "venue": venue,
                "fee_eur": fee_eur,
                "deadline": deadline_iso(order),
                "status": "open",
                "opened_at": ts,
                "updated_at": ts,
            }
        )
        if risk_level:
            positions[-1]["risk_level"] = risk_level
        state["cash_eur"] = round(cash, 6)
        state["positions"] = positions
        state["updated_at"] = ts
        recompute_equity(state)

        return {
            "id": trade_id,
            "ts": ts,
            "venue": venue,
            "mode": mode,
            "pair": pair,
            "side": "sell",
            "idea_type": "baisse",
            "kind": "baisse",
            "decision_id": str(decision_id).strip(),
            "type": str(order.get("type", "limit")).lower(),
            "price": price,
            "amount_eur": amount_eur,
            "qty": qty,
            "fee_eur": fee_eur,
            "stop_price": stop_price,
            "safety_price": stop_price,
            "target_price": target_price,
            "deadline": deadline_iso(order),
            "status": "paper_filled",
            "source": "guardian/paper_fill",
            **({"risk_level": risk_level} if risk_level else {}),
        }

    # --- Idée à la baisse: CLOSE short (rebuy / buy) ---
    if side == "buy" and (
        idea_type == "baisse"
        or order.get("linked_position_id")
        or order.get("cycle_id")
        or order.get("rebuy_reason")
    ):
        # Only treat as rebuy if linked to a short / explicit rebuy_reason / idea baisse
        linked = order.get("linked_position_id") or order.get("cycle_id")
        rebuy_reason = str(order.get("rebuy_reason") or "").strip().lower() or None
        # 9 oct : rachat du short désigné (id, puis decision_id, puis seul short de la paire) ;
        # un id donné mais introuvable/fermé → refus (plus de repli sur un autre short de la paire)
        if linked or idea_type == "baisse":
            short_pos = find_close_target(positions, pair, order, want_short=True)
        else:
            short_pos = None
        if short_pos is None:
            # Not a rebuy — if idea_type baisse without open short, error;
            # if linked fields absent and idea was defaulted via rebuy_reason only, error
            if idea_type == "baisse" or rebuy_reason or linked:
                raise ValueError(
                    f"aucun short ouvert à racheter pour {pair}"
                    + (f" (linked={linked})" if linked else "")
                )
            # else fall through to hausse buy — unreachable if we entered on rebuy hints
        else:
            sell_price = float(short_pos.get("avg_price") or 0)
            sell_qty = float(short_pos.get("qty") or 0)
            sell_fee = float(short_pos.get("fee_eur") or 0)
            close_qty = qty if qty > 0 else sell_qty
            if close_qty > sell_qty + 1e-12:
                close_qty = sell_qty
            close_amount = close_qty * price
            close_fee = round(close_amount * fee_rate_for_venue(
                str(short_pos.get("venue") or venue)
            ), 6)
            pos_venue = str(short_pos.get("venue") or venue)

            # Spend cash to buy back
            cash -= close_amount + close_fee
            inventory_credit(inv, asset, pos_venue, close_qty)

            realized = round(
                (sell_price - price) * close_qty - sell_fee * (close_qty / sell_qty if sell_qty else 1)
                - close_fee,
                6,
            )
            cost_basis = sell_price * close_qty
            realized_pct = round(100.0 * realized / cost_basis, 4) if cost_basis else 0.0
            # Same qty back → coins_gained 0; fees were in EUR
            coins_gained = round(close_qty - close_qty, 8)  # 0.0; reserved for fee-in-coins

            if rebuy_reason not in ("target", "safety", "time"):
                if order.get("close_reason") in ("stop_hit", "safety", "safety_hit"):
                    rebuy_reason = "safety"
                elif order.get("close_reason") in ("target_hit", "target"):
                    rebuy_reason = "target"
                else:
                    rebuy_reason = rebuy_reason or "safety"
            close_reason = str(
                order.get("close_reason")
                or (
                    "target_hit"
                    if rebuy_reason == "target"
                    else "stop_hit"
                    if rebuy_reason == "safety"
                    else "time_exit"
                )
            )

            short_pos["qty"] = sell_qty - close_qty
            short_pos["cost_eur"] = float(short_pos.get("cost_eur") or 0) * (
                (sell_qty - close_qty) / sell_qty if sell_qty else 0
            )
            short_pos["mark_eur"] = short_pos["cost_eur"]
            short_pos["updated_at"] = ts
            if short_pos["qty"] <= 1e-12:
                short_pos["qty"] = 0.0
                short_pos["cost_eur"] = 0.0
                short_pos["mark_eur"] = 0.0
                short_pos["status"] = "closed"
                short_pos["closed_at"] = ts
                short_pos["close_reason"] = close_reason
                short_pos["close_price_eur"] = price
                short_pos["realized_pnl_eur"] = realized
                short_pos["realized_pnl_pct"] = realized_pct
                short_pos["rebuy_reason"] = rebuy_reason

            cycle_id = str(short_pos.get("id"))
            state["cash_eur"] = round(cash, 6)
            state["positions"] = positions
            state["updated_at"] = ts
            recompute_equity(state)

            return {
                "id": trade_id,
                "ts": ts,
                "venue": pos_venue,
                "mode": mode,
                "pair": pair,
                "side": "buy",
                "idea_type": "baisse",
                "kind": "baisse",
                "type": str(order.get("type", "limit")).lower(),
                "price": price,
                "amount_eur": close_amount,
                "qty": close_qty,
                "fee_eur": close_fee,
                "cycle_id": cycle_id,
                "linked_position_id": cycle_id,
                "rebuy_reason": rebuy_reason,
                "realized_pnl_eur": realized,
                "realized_pnl_pct": realized_pct,
                "coins_gained": coins_gained,
                "close_reason": close_reason,
                "decision_id": short_pos.get("decision_id"),
                **({"risk_level": short_pos["risk_level"]} if short_pos.get("risk_level") else {}),
                "status": "paper_filled",
                "source": "guardian/paper_fill",
            }

    # --- Idée à la hausse / legacy ---
    if side == "buy":
        # Objectif (target_price) d'une idée à la hausse : doit être AU-DESSUS du prix d'achat (9 oct)
        long_target = order.get("target_price")
        long_target = float(long_target) if long_target is not None else None
        if long_target is not None and long_target <= price:
            raise ValueError(f"target_price {long_target} doit être AU-DESSUS du prix d'achat {price}")
        long_stop = order.get("stop_price")
        if long_stop is None:
            long_stop = order.get("stop_price_eur") if order.get("stop_price_eur") is not None else order.get("safety_price")
        long_stop = float(long_stop) if long_stop is not None else None
        # Frais d'achat 0,05 % comme les ventes d'une idée à la baisse (9 oct) : sortis du cash, gardés dans fee_eur
        buy_fee = round(amount_eur * FEE_REVOLUT, 6)
        cash -= amount_eur + buy_fee
        merged = False
        order_did = _clean_id(order.get("decision_id"))
        for p in positions:
            # 9 oct : une décision = une position. Fusion seulement avec un long ouvert de la MÊME
            # décision (même decision_id) ; sinon (autre décision, ou sans decision_id) → nouvelle position.
            if (
                order_did is not None
                and _clean_id(p.get("decision_id")) == order_did
                and p.get("status", "open") == "open"
                and str(p.get("pair", "")).upper() == pair
                and str(p.get("side", "long")).lower() in ("long", "buy")
                and p.get("idea_type", "hausse") != "baisse"
            ):
                old_cost = float(p.get("cost_eur", 0) or 0)
                old_qty = float(p.get("qty", 0) or 0)
                new_qty = old_qty + qty
                new_cost = old_cost + amount_eur
                p["qty"] = new_qty
                p["cost_eur"] = new_cost
                p["avg_price"] = (new_cost / new_qty) if new_qty else price
                p["mark_eur"] = new_cost
                p["fee_eur"] = round(float(p.get("fee_eur") or 0) + buy_fee, 6)
                p["updated_at"] = ts
                if order.get("stop_pct") is not None:
                    p["stop_pct"] = float(order["stop_pct"])
                if long_stop is not None:
                    p["stop_price_eur"] = long_stop
                    p["stop_price"] = long_stop
                if long_target is not None:
                    p["target_price"] = long_target  # latest decision's target applies
                if deadline_iso(order):
                    p["deadline"] = deadline_iso(order)  # latest decision's deadline applies
                if risk_level:
                    p["risk_level"] = risk_level
                p["idea_type"] = "hausse"
                merged = True
                merged_id = p.get("id")
                break
        if not merged:
            pos = {
                "id": trade_id,
                "pair": pair,
                "side": "long",
                "idea_type": "hausse",
                "qty": qty,
                "avg_price": price,
                "cost_eur": amount_eur,
                "mark_eur": amount_eur,
                "stop_pct": order.get("stop_pct"),
                "fee_eur": buy_fee,
                "venue": "revolut_x",
                "status": "open",
                "opened_at": ts,
                "updated_at": ts,
            }
            if long_stop is not None:
                pos["stop_price_eur"] = long_stop
                pos["stop_price"] = long_stop
            if long_target is not None:
                pos["target_price"] = long_target
            if order.get("decision_id"):
                pos["decision_id"] = order["decision_id"]
            if risk_level:
                pos["risk_level"] = risk_level
            if deadline_iso(order):
                pos["deadline"] = deadline_iso(order)
            positions.append(pos)
            merged_id = trade_id
        record = {
            "id": trade_id,
            "ts": ts,
            "venue": "revolut_x",
            "mode": mode,
            "pair": pair,
            "side": side,
            "idea_type": "hausse",
            "type": str(order.get("type", "limit")).lower(),
            "price": price,
            "amount_eur": amount_eur,
            "qty": qty,
            "stop_pct": order.get("stop_pct"),
            "fee_eur": buy_fee,
            "status": "paper_filled",
            "source": "guardian/paper_fill",
        }
        if order.get("decision_id"):
            record["decision_id"] = order["decision_id"]
        record["position_id"] = merged_id
        record["merged"] = merged
        if risk_level:
            record["risk_level"] = risk_level
        if long_stop is not None:
            record["stop_price"] = long_stop
        if long_target is not None:
            record["target_price"] = long_target
        if deadline_iso(order):
            record["deadline"] = deadline_iso(order)
    else:  # sell → close ONE existing long (hausse) — 9 oct : la position désignée seulement
        target_pos = find_close_target(positions, pair, order, want_short=False)
        if target_pos is None:
            raise ValueError(f"aucune position long (hausse) {pair} ouverte à vendre")
        remaining = amount_eur
        linked_ids: list[str] = []
        closed_cost = 0.0
        closed_qty = 0.0
        closed_entry_fee = 0.0
        entry_price = None
        for p in [target_pos]:
            cost = float(p.get("cost_eur", 0) or 0)
            pqty = float(p.get("qty", 0) or 0)
            take = min(remaining, cost)
            frac = take / cost if cost else 1.0
            take_qty = pqty * frac
            pfee = float(p.get("fee_eur") or 0)
            closed_entry_fee += pfee * frac
            if pfee and frac < 1.0 - 1e-12:
                p["fee_eur"] = round(pfee * (1.0 - frac), 6)  # partial: entry fee left on the open rest
            p["cost_eur"] = cost - take
            p["qty"] = pqty * (1.0 - frac)
            p["mark_eur"] = p["cost_eur"]
            p["updated_at"] = ts
            linked_ids.append(str(p.get("id")))
            closed_cost += take
            closed_qty += take_qty
            if entry_price is None:
                entry_price = float(p.get("avg_price") or 0) or None
            if p["cost_eur"] <= 1e-9 or p["qty"] <= 1e-12:
                p["status"] = "closed"
                p["closed_at"] = ts
                p["cost_eur"] = 0.0
                p["qty"] = 0.0
                p["mark_eur"] = 0.0
                if order.get("close_reason"):
                    p["close_reason"] = order["close_reason"]
            remaining -= take
        # cash reçoit le coût réellement fermé (jamais plus que la position désignée)
        cash += closed_cost
        record = {
            "id": trade_id,
            "ts": ts,
            "venue": "revolut_x",
            "mode": mode,
            "pair": pair,
            "side": side,
            "idea_type": "hausse",
            "type": str(order.get("type", "limit")).lower(),
            "price": price,
            "amount_eur": amount_eur,
            "qty": qty,
            "stop_pct": order.get("stop_pct"),
            "status": "paper_filled",
            "source": "guardian/paper_fill",
        }
        if linked_ids:
            record["linked_position_id"] = linked_ids[0]
            record["position_id"] = linked_ids[0]
        if target_pos.get("decision_id"):
            record["decision_id"] = target_pos.get("decision_id")
        if target_pos.get("risk_level"):
            record["risk_level"] = target_pos.get("risk_level")
        if closed_cost < amount_eur - 1e-6:
            record["amount_eur_requested"] = amount_eur
            record["amount_eur"] = round(closed_cost, 6)
            record["qty"] = round(closed_qty, 12)
        if order.get("close_reason"):
            record["close_reason"] = order["close_reason"]
        # Frais de vente 0,05 % (9 oct) sortis du cash ; realized_pnl_eur = net (frais achat + vente),
        # realized_pnl_gross_eur = brut (watch_stops ajoute le brut au cash, comme avant).
        sell_fee = round(price * closed_qty * FEE_REVOLUT, 6) if closed_qty > 0 else 0.0
        cash -= sell_fee
        record["fee_eur"] = sell_fee
        if entry_price and closed_qty > 0:
            gross = round(price * closed_qty - closed_cost, 6)
            realized = round(gross - closed_entry_fee - sell_fee, 6)
            record["realized_pnl_gross_eur"] = gross
            record["fees_eur"] = round(closed_entry_fee + sell_fee, 6)
            record["realized_pnl_eur"] = realized
            if closed_cost > 0:
                record["realized_pnl_pct"] = round(100.0 * realized / closed_cost, 4)

    state["cash_eur"] = round(cash, 6)
    state["positions"] = positions
    state["updated_at"] = ts
    recompute_equity(state)
    return record


def order_opens_position(order: dict) -> bool:
    """True for an opening order: hausse buy (not a rebuy) or baisse sell."""
    side = str(order.get("side") or "").strip().lower()
    idea = resolve_idea_type(order)
    if side == "sell":
        return idea == "baisse"
    if side == "buy":
        if idea == "baisse":
            return False
        return not (order.get("linked_position_id") or order.get("cycle_id") or order.get("rebuy_reason"))
    return False


def record_opened_position(record: dict) -> bool:
    side = str(record.get("side") or "").lower()
    idea = str(record.get("idea_type") or "hausse").lower()
    return (side == "buy" and idea == "hausse") or (side == "sell" and idea == "baisse")


def _watch(reason: str) -> dict:
    if watcher_launch is None:
        return {"watcher_started": False, "watcher_already_running": False, "watcher_error": "launcher import failed"}
    try:
        return watcher_launch.ensure_watcher(reason=reason)
    except Exception as e:  # noqa: BLE001
        return {"watcher_started": False, "watcher_already_running": False, "watcher_error": str(e)}


def preopen_watch_check() -> dict | None:
    """Before an open: open paper positions but no live watcher → start it."""
    if watcher_launch is None or watcher_launch.autostart_disabled():
        return None
    try:
        st = load_json(STATE_PATH) if STATE_PATH.exists() else {}
    except (OSError, json.JSONDecodeError):
        return None
    n_open = sum(1 for p in st.get("positions") or [] if str(p.get("status", "open")).lower() == "open")
    if n_open == 0:
        return None
    if watcher_launch.running_pid():
        return None
    res = _watch(f"pre_open_unwatched_positions={n_open}")
    res["open_positions_before"] = n_open
    return res


def main() -> int:
    parser = argparse.ArgumentParser(description="Paper-fill a validated Revolut X order")
    parser.add_argument("--order", type=str, help="Path to order JSON file")
    args = parser.parse_args()

    try:
        order = load_order(args)
    except (json.JSONDecodeError, OSError) as e:
        print(json.dumps({"ok": False, "reasons": [f"order load error: {e}"]}))
        return 1

    preopen = preopen_watch_check() if order_opens_position(order) else None

    result, _rc = run_validate(order)
    if not result.get("ok"):
        out = {"ok": False, "reasons": result.get("reasons", []), "fill": None}
        if preopen is not None:
            out["watcher_preopen"] = preopen
        print(json.dumps(out))
        return 1

    # Read-modify-write of guardian state under the shared lock (watch_stops marks use it too)
    with state_summary.state_lock(STATE_PATH):
        state = (
            load_json(STATE_PATH)
            if STATE_PATH.exists()
            else {
                "bankroll_eur": 0,
                "cash_eur": 0,
                "positions": [],
                "daily_pnl_eur": 0,
                "peak_equity_eur": 0,
                "halted": False,
            }
        )
        # Always ensure inventory block exists (idempotent)
        ensure_paper_inventory(state)

        try:
            record = apply_fill(state, order)
        except ValueError as e:
            out = {"ok": False, "reasons": [str(e)], "fill": None}
            if preopen is not None:
                out["watcher_preopen"] = preopen
            print(json.dumps(out))
            return 1

        TRADES_PATH.parent.mkdir(parents=True, exist_ok=True)
        with TRADES_PATH.open("a") as f:
            f.write(json.dumps(record) + "\n")
        save_json(STATE_PATH, state)

    # Start the stop watcher after a successful open (state already saved)
    if record_opened_position(record):
        watcher = _watch(f"paper_open {record.get('pair')} {record.get('side')} {record.get('id')}")
    else:
        watcher = {"watcher_started": False, "watcher_already_running": False, "watcher_skipped": "not_an_open"}
    if preopen is not None:
        watcher["watcher_preopen"] = preopen

    print(
        json.dumps(
            {
                "ok": True,
                "reasons": [],
                "warnings": result.get("warnings") or [],
                **watcher,
                "fill": record,
                "state_summary": {
                    "cash_eur": state["cash_eur"],
                    "bankroll_eur": state.get("bankroll_eur"),
                    "open_positions": sum(
                        1
                        for p in state.get("positions") or []
                        if p.get("status", "open") == "open"
                    ),
                    "peak_equity_eur": state.get("peak_equity_eur"),
                    "equity_eur": state.get("equity_eur"),
                    "exposure_eur": state.get("exposure_eur"),
                    "exposure_pct": state.get("exposure_pct"),
                    "unrealized_pnl_eur": state.get("unrealized_pnl_eur"),
                    "total_pnl_eur": state.get("total_pnl_eur"),
                    "paper_inventory": state.get("paper_inventory"),
                },
            }
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
