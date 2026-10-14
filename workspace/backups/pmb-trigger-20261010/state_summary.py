#!/usr/bin/env python3
"""Champs « tableau » de guardian/state.json (9 oct) — écrits par les bots, jamais calculés par le tableau.

Convention (fixée 8 oct) :
  - idée à la baisse / short : le cash contient déjà la vente ; mark_eur = qty × mid = coût de rachat ;
    equity = cash − mark (short) + mark (long).
  - P&L ouvert : long = qty×mid − cost_eur − fee_eur ; short = (avg_price − mid)×qty − fee_eur.

Par position ouverte : last_mid_eur, mark_eur, unrealized_pnl_eur, unrealized_pnl_pct, mark_ts.
En haut : equity_eur, exposure_eur (Σ cost_eur ouverts), exposure_pct (exposure/bankroll),
unrealized_pnl_eur (Σ), total_pnl_eur (equity − bankroll), drawdown_pct, peak_equity_eur,
summary_updated_at (ISO local Bruxelles).

Écriture sûre : verrou fcntl `<state>.lock` (même méthode que state/live_exits.lock), relecture
sous verrou, écriture atomique (tmp + replace). paper_fill tient le même verrou pendant sa
lecture-modification-écriture → le gardien n'écrase jamais un trade.
"""
from __future__ import annotations

import fcntl
import json
import os
import tempfile
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

TZ = ZoneInfo("Europe/Brussels")
POSITION_FIELDS = ("last_mid_eur", "mark_eur", "unrealized_pnl_eur", "unrealized_pnl_pct", "mark_ts")
TOP_FIELDS = ("equity_eur", "exposure_eur", "exposure_pct", "unrealized_pnl_eur", "total_pnl_eur",
              "drawdown_pct", "peak_equity_eur")


def now_local_iso() -> str:
    return datetime.now(TZ).isoformat(timespec="seconds")


def _f(v, default: float = 0.0) -> float:
    try:
        return float(v) if v is not None else default
    except (TypeError, ValueError):
        return default


def is_open(p: dict) -> bool:
    return str(p.get("status", "open") or "open").lower() == "open"


def is_short(p: dict) -> bool:
    return (str(p.get("side") or "").lower() in ("short", "sell")
            or str(p.get("idea_type") or p.get("kind") or "").lower() == "baisse")


def position_mark(p: dict) -> float:
    return _f(p.get("mark_eur", p.get("cost_eur", 0)))


def position_unrealized(p: dict) -> tuple[float, float]:
    """(unrealized_pnl_eur, unrealized_pnl_pct) from mark_eur (= qty × mid)."""
    mark = position_mark(p)
    cost = _f(p.get("cost_eur", p.get("amount_eur", 0)))
    fee = _f(p.get("fee_eur"))
    if is_short(p):
        qty, avg = _f(p.get("qty")), _f(p.get("avg_price"))
        sold = avg * qty if (avg > 0 and qty > 0) else cost
        pnl = sold - mark - fee
        base = sold or cost
    else:
        pnl = mark - cost - fee
        base = cost
    return round(pnl, 4), (round(100.0 * pnl / base, 3) if base > 0 else 0.0)


def mark_position(p: dict, mid: float, ts: str | None = None) -> None:
    """Mark one open position at `mid` (qty × mid) and refresh its P&L fields."""
    qty = _f(p.get("qty"))
    p["last_mid_eur"] = float(mid)
    if qty > 0:
        p["mark_eur"] = round(qty * float(mid), 6)
    p["unrealized_pnl_eur"], p["unrealized_pnl_pct"] = position_unrealized(p)
    p["mark_ts"] = ts or now_local_iso()


def refresh_summary(state: dict, ts: str | None = None) -> dict:
    """Recompute top-level dashboard fields (and per-position P&L from current marks). In place."""
    opens = [p for p in state.get("positions") or [] if isinstance(p, dict) and is_open(p)]
    cash = _f(state.get("cash_eur"))
    bankroll = _f(state.get("bankroll_eur"))
    eq = cash
    exposure = 0.0
    unreal = 0.0
    for p in opens:
        eq += (-1.0 if is_short(p) else 1.0) * position_mark(p)
        exposure += _f(p.get("cost_eur", p.get("amount_eur", 0)))
        p["unrealized_pnl_eur"], p["unrealized_pnl_pct"] = position_unrealized(p)
        unreal += p["unrealized_pnl_eur"]
    peak = _f(state.get("peak_equity_eur"))
    if peak <= 0:
        peak = bankroll if bankroll > 0 else eq
    peak = max(peak, eq)
    state["equity_eur"] = round(eq, 6)
    state["peak_equity_eur"] = round(peak, 6)
    state["drawdown_pct"] = round(max(0.0, (peak - eq) / peak), 6) if peak > 0 else 0.0
    state["exposure_eur"] = round(exposure, 6)
    state["exposure_pct"] = round(exposure / bankroll, 4) if bankroll > 0 else 0.0
    state["unrealized_pnl_eur"] = round(unreal, 4)
    state["total_pnl_eur"] = round(eq - bankroll, 4)
    state["summary_updated_at"] = ts or now_local_iso()
    return state


def summary_signature(state: dict) -> tuple:
    """Dashboard values without timestamps (to skip no-op writes)."""
    top = tuple(state.get(k) for k in TOP_FIELDS)
    pos = tuple((p.get("id"), p.get("last_mid_eur"), p.get("mark_eur"), p.get("unrealized_pnl_eur"))
                for p in state.get("positions") or [] if isinstance(p, dict) and is_open(p))
    return top, pos


def lock_path(state_path: Path) -> Path:
    return state_path.with_name(state_path.name + ".lock")


@contextmanager
def state_lock(state_path: Path):
    """Exclusive fcntl lock on `<state>.lock` (blocking). Never hold it across a paper_fill subprocess."""
    lp = lock_path(Path(state_path))
    lp.parent.mkdir(parents=True, exist_ok=True)
    with lp.open("a+") as fh:
        fcntl.flock(fh, fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(fh, fcntl.LOCK_UN)


def atomic_write_json(path: Path, data: dict) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w") as fh:
            fh.write(json.dumps(data, indent=2, ensure_ascii=False) + "\n")
            fh.flush()
            os.fsync(fh.fileno())
        try:
            os.chmod(tmp, path.stat().st_mode & 0o777 if path.exists() else 0o644)
        except OSError:
            pass
        os.replace(tmp, path)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise
