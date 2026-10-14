#!/usr/bin/env python3
"""Rapprochement Revolut (9 oct) → guardian/state.json `rapprochement_revolut`.

    {gain_equipe_eur, gain_revolut_eur, ecart_eur, controle_at, mode, note, ...}

- gain_equipe_eur : résultat réalisé LIVE (net) d'après state/live_orders.jsonl (lignes avec
  realized_pnl_eur, en pratique les sorties `kind: auto_exit`) ; 0 s'il n'y en a pas.
- Simulation (aucun ordre réel réussi dans live_orders.jsonl) : gain_revolut_eur / ecart_eur =
  "sans objet", note "simulation : pas d'ordre réel". Aucun appel Revolut.
- Live : gain_revolut_eur recalculé depuis les ordres remplis chez Revolut X pour chaque cycle
  fermé (entrée + ordres de sortie), via `revx order history` puis `revx order get` pour les
  manquants — lecture seule, JAMAIS d'ordre (liste blanche de commandes ci-dessous).
  Frais : ceux donnés par Revolut sur l'ordre, sinon estimation 0,05 %/côté (signalé dans la note).
  ecart_eur = gain_equipe_eur − gain_revolut_eur.

Usage : python3 reconcile_revolut.py [--no-network] [--dry-run]   (JSON sur stdout)
Appelé par watch_stops (battement Revolut ~5 min si position live / trade live aujourd'hui,
1×/jour sinon ; bloc simulation ajouté au rafraîchissement du tableau s'il manque).
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parent))
import state_summary  # noqa: E402

GUARDIAN = Path(__file__).resolve().parent.parent
ROOT = Path(os.environ.get("PREDICT_BOT_ROOT", str(GUARDIAN.parent)))
STATE_PATH = Path(os.environ.get("GUARDIAN_STATE", str(GUARDIAN / "state.json")))
LIVE_ORDERS_PATH = Path(os.environ.get("LIVE_ORDERS", str(ROOT / "state" / "live_orders.jsonl")))
REVX_BIN = (os.environ.get("WATCH_STOPS_REVX_BIN") or os.environ.get("REVX_BIN")
            or os.path.expanduser("~/.local/bin/revx"))
PROXY = "http://127.0.0.1:8791"
TZ = ZoneInfo("Europe/Brussels")
FEE_RATE = 0.0005  # estimation 0,05 %/côté si Revolut ne donne pas les frais
WHITELIST_PAIRS = ("BTC-EUR", "ETH-EUR", "SOL-EUR")
FIELD = "rapprochement_revolut"
SANS_OBJET = "sans objet"
NOTE_SIM = "simulation : pas d'ordre réel"
READ_ONLY = {("order", "history"), ("order", "get")}  # seules commandes revx autorisées ici


# ---------- live_orders.jsonl ----------
def load_live_rows() -> list[dict]:
    if not LIVE_ORDERS_PATH.exists():
        return []
    rows = []
    for line in LIVE_ORDERS_PATH.read_text().splitlines():
        try:
            r = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(r, dict):
            rows.append(r)
    return rows


def real_rows(rows: list[dict]) -> list[dict]:
    """Rows of real (non dry-run) successful live orders / exits."""
    return [r for r in rows if r.get("ok") and not r.get("dry_run")]


def _order(row: dict) -> dict:
    return row["order"] if isinstance(row.get("order"), dict) else row


def _fnum(v, default=None):
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


def row_realized(row: dict) -> float | None:
    v = row.get("realized_pnl_eur")
    if v is None:
        v = _order(row).get("realized_pnl_eur")
    return _fnum(v)


def row_local_date(row: dict) -> str | None:
    at = row.get("at") or row.get("ts")
    if not at:
        return None
    try:
        dt = datetime.fromisoformat(str(at).replace("Z", "+00:00"))
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=TZ)
    return dt.astimezone(TZ).date().isoformat()


def live_trade_today(rows: list[dict] | None = None) -> bool:
    today = datetime.now(TZ).date().isoformat()
    return any(row_local_date(r) == today for r in real_rows(load_live_rows() if rows is None else rows))


def gain_equipe(rows: list[dict]) -> float:
    return round(sum(v for v in (row_realized(r) for r in real_rows(rows)) if v is not None), 6)


def sim_block(rows: list[dict] | None = None, now: str | None = None) -> dict:
    rows = load_live_rows() if rows is None else rows
    return {"gain_equipe_eur": gain_equipe(rows), "gain_revolut_eur": SANS_OBJET, "ecart_eur": SANS_OBJET,
            "controle_at": now or state_summary.now_local_iso(), "mode": "simulation", "note": NOTE_SIM}


def local_block_if_sim(rows: list[dict] | None = None) -> dict | None:
    """Simulation block without any network call; None when real live orders exist."""
    rows = load_live_rows() if rows is None else rows
    return None if real_rows(rows) else sim_block(rows)


# ---------- Revolut (lecture seule) ----------
def _revx_env() -> dict:
    env = os.environ.copy()
    env.update({"HTTPS_PROXY": env.get("HTTPS_PROXY", PROXY), "HTTP_PROXY": env.get("HTTP_PROXY", PROXY),
                "ALL_PROXY": env.get("ALL_PROXY", PROXY)})
    local_bin = os.path.expanduser("~/.local/bin")
    if local_bin not in env.get("PATH", "").split(":"):
        env["PATH"] = f"{local_bin}:{env.get('PATH', '')}"
    return env


def _parse(stdout: str):
    text = (stdout or "").strip()
    if not text:
        return None
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        starts = [i for i in (text.find("{"), text.find("[")) if i >= 0]
        if not starts:
            return None
        try:
            return json.loads(text[min(starts):])
        except json.JSONDecodeError:
            return None


def revx_read(args: list[str], timeout: float = 40.0):
    if tuple(args[:2]) not in READ_ONLY:
        raise RuntimeError(f"commande revx refusée (lecture seule) : {args[:2]}")
    try:
        p = subprocess.run([REVX_BIN, *args], capture_output=True, text=True, env=_revx_env(), timeout=timeout)
    except (OSError, subprocess.TimeoutExpired) as e:
        return None, str(e)
    if p.returncode != 0:
        return None, (p.stderr or p.stdout or f"rc={p.returncode}")[:200]
    return _parse(p.stdout), None


def _as_list(payload) -> list:
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        for k in ("data", "orders", "items", "results"):
            if isinstance(payload.get(k), list):
                return payload[k]
        if isinstance(payload.get("data"), dict):
            return [payload["data"]]
        return [payload]
    return []


def _ids(o: dict) -> set[str]:
    return {str(x) for x in (o.get("id"), o.get("venue_order_id"), o.get("order_id"), o.get("client_order_id")) if x}


def _filled(o: dict) -> tuple[float, float | None]:
    q = _fnum(o.get("filled_quantity") or o.get("filled_qty") or o.get("filledQty") or o.get("executed_qty"), 0.0) or 0.0
    a = _fnum(o.get("filled_amount") or o.get("filled_quote") or o.get("filledAmount"))
    if a is None and q:
        px = _fnum(o.get("average_fill_price") or o.get("avg_price") or o.get("price"))
        a = q * px if px else None
    return q, a


def _fee(o: dict) -> float | None:
    for k in ("fee", "fees", "total_fee", "fee_amount", "commission", "cumulative_fee"):
        v = o.get(k)
        if isinstance(v, dict):
            v = v.get("amount") or v.get("value")
        f = _fnum(v)
        if f is not None:
            return abs(f)
    return None


def _row_ids(row: dict) -> set[str]:
    out: set[str] = set()
    cmd = row.get("cmd") or []
    if "--client-order-id" in cmd:
        i = cmd.index("--client-order-id")
        if i + 1 < len(cmd):
            out.add(str(cmd[i + 1]))
    d = _parse(row.get("stdout") or "")
    for o in _as_list(d)[:1]:
        if isinstance(o, dict):
            out |= _ids(o)
    if isinstance(row.get("fill"), dict):
        out |= _ids(row["fill"])
    return out


def _position_id(row: dict) -> str | None:
    """Same id formula as watch_stops.load_live_orders_open / live_place.live_row_position_id."""
    o = _order(row)
    pair = str(o.get("pair") or "").upper()
    if not pair:
        return None
    oid = str(o.get("id") or row.get("client_order_id") or f"live-{pair}-{row.get('at')}")
    return oid if oid.startswith("rx-live") or oid.startswith("live-") else f"rx-live-{oid}"


def closed_cycles(rows: list[dict]) -> list[dict]:
    """Closed live cycles: auto_exit row + its entry row (order ids for Revolut)."""
    rr = real_rows(rows)
    entries = {(_position_id(r)): r for r in rr if r.get("kind") != "auto_exit"}
    cycles = []
    for r in rr:
        if r.get("kind") != "auto_exit":
            continue
        o = _order(r)
        pid = str(o.get("exit_for") or o.get("linked_position_id") or "")
        sold = _fnum(o.get("qty"), 0.0) or 0.0
        if sold <= 0:
            continue
        exit_ids = [str(a.get("order_id")) for a in (r.get("attempts") or [])
                    if isinstance(a, dict) and a.get("order_id") and (_fnum(a.get("filled_qty"), 0.0) or 0.0) > 0]
        entry = entries.get(pid)
        cycles.append({"position_id": pid, "pair": o.get("pair"), "side": "short" if o.get("idea_type") == "baisse" else "long",
                       "sold_qty": sold, "exit_ids": exit_ids, "entry_ids": sorted(_row_ids(entry)) if entry else [],
                       "gain_equipe_eur": row_realized(r), "date": row_local_date(r)})
    return cycles


def revolut_gain(cycles: list[dict]) -> tuple[float | None, dict]:
    """Σ over closed cycles of Revolut fills: sorties − entrée (au prorata de la qté sortie) − frais."""
    info: dict = {"cycles": [], "frais_estimes": False, "erreurs": []}
    if not cycles:
        return 0.0, info
    start = min(c["date"] for c in cycles if c.get("date")) if any(c.get("date") for c in cycles) else "7d"
    hist, err = revx_read(["order", "history", "--symbols", ",".join(WHITELIST_PAIRS), "--start-date", start,
                           "--json", "--limit", "200"])
    if err:
        info["erreurs"].append(f"order history: {err}")
    by_id: dict[str, dict] = {}
    for o in _as_list(hist):
        if isinstance(o, dict):
            for k in _ids(o):
                by_id[k] = o

    def get(oid: str) -> dict | None:
        if oid in by_id:
            return by_id[oid]
        d, e = revx_read(["order", "get", oid, "--json"])
        if e:
            info["erreurs"].append(f"order get {oid}: {e}")
            return None
        lst = _as_list(d)
        o = lst[0] if lst and isinstance(lst[0], dict) else None
        if o:
            for k in _ids(o) | {oid}:
                by_id[k] = o
        return o

    total = 0.0
    for c in cycles:
        entry = next((o for o in (get(i) for i in c["entry_ids"]) if o), None)
        exits = [o for o in (get(i) for i in c["exit_ids"]) if o]
        if entry is None or len(exits) != len(c["exit_ids"]) or not exits:
            info["erreurs"].append(f"{c['position_id']}: ordres Revolut introuvables")
            return None, info
        eq, ea = _filled(entry)
        xq = sum(_filled(o)[0] for o in exits)
        xa = sum((_filled(o)[1] or 0.0) for o in exits)
        if not eq or ea is None:
            info["erreurs"].append(f"{c['position_id']}: entrée non remplie chez Revolut")
            return None, info
        frac = min(1.0, xq / eq) if eq else 1.0
        entry_part = ea * frac
        fe = _fee(entry)
        fx = [_fee(o) for o in exits]
        if fe is None or any(f is None for f in fx):
            info["frais_estimes"] = True
        fees = (fe * frac if fe is not None else entry_part * FEE_RATE) + sum(
            (f if f is not None else (_filled(o)[1] or 0.0) * FEE_RATE) for f, o in zip(fx, exits))
        gross = (xa - entry_part) if c["side"] == "long" else (entry_part - xa)
        g = round(gross - fees, 6)
        total += g
        info["cycles"].append({"position_id": c["position_id"], "gain_revolut_eur": g,
                               "gain_equipe_eur": c.get("gain_equipe_eur")})
    return round(total, 6), info


def build_block(network: bool = True) -> dict:
    rows = load_live_rows()
    if not real_rows(rows):
        return sim_block(rows)
    now = state_summary.now_local_iso()
    eq = gain_equipe(rows)
    cycles = closed_cycles(rows)
    block = {"gain_equipe_eur": eq, "controle_at": now, "mode": "live", "cycles_controles": len(cycles)}
    if not network:
        block.update({"gain_revolut_eur": "non contrôlé", "ecart_eur": "non contrôlé",
                      "note": "live : contrôle Revolut au prochain battement (~5 min)"})
        return block
    rev, info = revolut_gain(cycles)
    if rev is None:
        block.update({"gain_revolut_eur": "indisponible", "ecart_eur": "indisponible",
                      "note": "live : lecture Revolut impossible — " + "; ".join(info["erreurs"])[:300]})
        return block
    notes = [f"live : {len(cycles)} cycle(s) fermé(s) recalculé(s) depuis les ordres remplis Revolut X (lecture seule)"]
    if info["frais_estimes"]:
        notes.append("frais non fournis par Revolut → estimation 0,05 %/côté")
    if not cycles:
        notes.append("aucun cycle live fermé")
    block.update({"gain_revolut_eur": rev, "ecart_eur": round(eq - rev, 6), "note": " ; ".join(notes)})
    if info["cycles"]:
        block["detail"] = info["cycles"][-10:]
    return block


def write_block(block: dict) -> dict:
    with state_summary.state_lock(STATE_PATH):
        try:
            state = json.loads(STATE_PATH.read_text())
        except (OSError, json.JSONDecodeError):
            raise RuntimeError("guardian/state.json illisible — rien écrit")
        if not isinstance(state, dict):
            raise RuntimeError("guardian/state.json invalide — rien écrit")
        state[FIELD] = block
        state_summary.atomic_write_json(STATE_PATH, state)
    return block


def run(network: bool = True, dry_run: bool = False) -> dict:
    block = build_block(network=network)
    if not dry_run:
        write_block(block)
    return block


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--no-network", action="store_true", help="pas d'appel Revolut")
    ap.add_argument("--dry-run", action="store_true", help="calcule sans écrire")
    a = ap.parse_args()
    try:
        block = run(network=not a.no_network, dry_run=a.dry_run)
    except Exception as e:  # noqa: BLE001
        print(json.dumps({"ok": False, "error": str(e)}, ensure_ascii=False))
        return 1
    print(json.dumps({"ok": True, FIELD: block}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
