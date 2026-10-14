#!/usr/bin/env python3
"""Place a validated Revolut X limit post-only order (live).

Arming (one of):
  - file LIVE_ONCE at repo root (preferred: one trade then auto-clears)
  - MODE file contents = live

Always: validate_order OK, no STOP/HALTED, limit + post-only only.
Mechanical gates (before place):
  - max 1 live/day via revx order history / trade (primary) + live_day.json (secondary)
  - expectancy: expected_gain_eur >= 3 * (costs_eur + expected_loss_eur)
  - min ticket MIN_LIVE_EUR

  python3 live_place.py --order order.json
  python3 live_place.py --order order.json --dry-run
  python3 live_place.py --order order.json --dry-run --skip-expectancy
  python3 live_place.py --exit --order exit_spec.json    # sortie auto sur stop (watch_stops)

After a successful placement (and after live_day.json / LIVE_ONCE handling) the stop
watcher watch_stops.py is started detached if not already running (watcher_launch.py);
it reads the order (with its stop) from state/live_orders.jsonl. Output JSON gains
watcher_started / watcher_already_running.

Horaires live (8 oct, validé Quentin) — NOUVELLES entrées seulement (pas --exit) :
  - créneau guardian/config.json `live_window` (défaut 15:00–17:00 Europe/Brussels) ;
  - refus pendant `post_announcement_block_min` (15) min après chaque heure de
    `live_window.announcement_times` (14:30, 15:30) et de state/annonces_du_jour.json
    ({"date": "YYYY-MM-DD", "times": ["20:00"]}, seulement si date == aujourd'hui) ;
  - séance en plus (feu vert de Quentin) : state/LIVE_EXTRA_SESSION.json
    {"date": "YYYY-MM-DD", "start": "HH:MM", "end": "HH:MM"} — date du jour seulement ;
    le blocage après annonce s'applique aussi ; jamais d'entrée à partir de force_close (22:00).
  - refus = rc 12 ; --dry-run rapporte gates.live_window (would_refuse + raison) sans changer le reste.
  - heure limite : `deadline` (alias `deadline_at`, ISO local) stockée sur l'ordre journalisé ;
    rappel seulement (watch_stops écrit state/deadline_reminder.json, ne ferme rien sauf si
    config deadline.close_enabled=true → --exit, raison heure_limite).
  - force_close (22:00) : RETIRÉE Quentin 8 oct (`force_close_enabled: false`) ; code conservé,
    remettre true pour réactiver (watch_stops → live_place --exit, raison fermeture_22h).
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

GUARDIAN = Path(__file__).resolve().parent.parent
ROOT = GUARDIAN.parent
MODE_PATH = ROOT / "MODE"
LIVE_ONCE = ROOT / "LIVE_ONCE"
STOP_PATH = ROOT / "STOP"
HALTED_PATH = GUARDIAN / "HALTED"
LOG_PATH = ROOT / "state" / "live_orders.jsonl"
LIVE_DAY_PATH = ROOT / "state" / "live_day.json"  # {"date": "YYYY-MM-DD", "count": 1}
VALIDATE = Path(__file__).resolve().parent / "validate_order.py"
MAX_LIVE_PER_DAY = 1
MIN_LIVE_EUR = 8  # aligned Risk 2026-10-07: ~5% of ~165€ cash.0
EXPECTANCY_MULTIPLE = 3.0
# Round-trip fee estimate when costs_eur omitted (10 bps of notional)
FEE_ESTIMATE_BPS = 10.0
WHITELIST_PAIRS = ("BTC-EUR", "ETH-EUR", "SOL-EUR")
SUCCESS_ORDER_STATES = frozenset(
    {"filled", "partially_filled", "partially-filled", "done", "closed", "completed"}
)
TZ = ZoneInfo("Europe/Brussels")
REVX_BIN = os.environ.get("REVX_BIN", "revx")
PROXY = "http://127.0.0.1:8791"

sys.path.insert(0, str(Path(__file__).resolve().parent))
try:
    import watcher_launch  # noqa: E402  (detached stop watcher; never blocks a live order)
except Exception:  # noqa: BLE001
    watcher_launch = None  # type: ignore[assignment]


def start_stop_watcher(pair: str) -> dict:
    if watcher_launch is None:
        return {"watcher_started": False, "watcher_already_running": False, "watcher_error": "launcher import failed"}
    try:
        return watcher_launch.ensure_watcher(reason=f"live_place {pair}")
    except Exception as e:  # noqa: BLE001
        return {"watcher_started": False, "watcher_already_running": False, "watcher_error": str(e)}


REAL_ROOT = Path("/workspace/predict-market-bot")
_PROC_START = time.time()


def _fake_now() -> datetime | None:
    """TEST ONLY: PMB_FAKE_NOW (ISO, Brussels if naive), advancing with real time since process start.
    Honoured only in a COPIED tree (never from the real repo) and only with TEST_MARKER set."""
    raw = os.environ.get("PMB_FAKE_NOW")
    if not raw or not os.environ.get("TEST_MARKER"):
        return None
    try:
        if ROOT.resolve() == REAL_ROOT.resolve():
            return None
    except OSError:
        return None
    try:
        dt = datetime.fromisoformat(raw)
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=TZ)
    from datetime import timedelta
    return dt.astimezone(TZ) + timedelta(seconds=time.time() - _PROC_START)


def now_brussels() -> datetime:
    return _fake_now() or datetime.now(TZ)


def today_local() -> str:
    return now_brussels().date().isoformat()


def revx_env() -> dict:
    env = os.environ.copy()
    env["HTTPS_PROXY"] = PROXY
    env["HTTP_PROXY"] = PROXY
    env["ALL_PROXY"] = PROXY
    # Prefer wrapper on PATH; ensure local bin is visible
    local_bin = "/home/box/.local/bin"
    path = env.get("PATH", "")
    if local_bin not in path.split(":"):
        env["PATH"] = f"{local_bin}:{path}" if path else local_bin
    return env


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


def load_order(path: str | None) -> dict:
    if path:
        return json.loads(Path(path).read_text())
    raw = sys.stdin.read()
    if not raw.strip():
        raise SystemExit("No order JSON")
    return json.loads(raw)


def live_count_today() -> int:
    if not LIVE_DAY_PATH.exists():
        return 0
    try:
        data = json.loads(LIVE_DAY_PATH.read_text())
    except Exception:
        return 0
    if data.get("date") != today_local():
        return 0
    return int(data.get("count") or 0)


def record_live_success() -> None:
    LIVE_DAY_PATH.parent.mkdir(parents=True, exist_ok=True)
    LIVE_DAY_PATH.write_text(
        json.dumps({"date": today_local(), "count": live_count_today() + 1}) + "\n"
    )


def armed() -> tuple[bool, str]:
    mode = MODE_PATH.read_text().strip() if MODE_PATH.exists() else ""
    if LIVE_ONCE.exists():
        return True, "LIVE_ONCE"
    if mode == "live":
        return True, "MODE=live"
    return False, f"not armed (MODE={mode!r}, no LIVE_ONCE)"


def _parse_json_stdout(stdout: str) -> object:
    text = (stdout or "").strip()
    if not text:
        return None
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # Some CLIs print banners before JSON
        start = text.find("{")
        start_arr = text.find("[")
        if start < 0 and start_arr < 0:
            return None
        if start < 0:
            start = start_arr
        elif start_arr >= 0:
            start = min(start, start_arr)
        try:
            return json.loads(text[start:])
        except json.JSONDecodeError:
            return None


def _as_list(payload: object) -> list:
    if payload is None:
        return []
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        for key in ("data", "orders", "trades", "results", "items"):
            val = payload.get(key)
            if isinstance(val, list):
                return val
        return [payload]
    return []


def _item_looks_success(item: dict) -> bool:
    state = str(
        item.get("order_state")
        or item.get("state")
        or item.get("status")
        or item.get("orderState")
        or ""
    ).lower().replace(" ", "_")
    if state in SUCCESS_ORDER_STATES:
        return True
    # Trades / fills without explicit state count as successful live activity
    if item.get("trade_id") or item.get("tradeId") or item.get("id"):
        if "order" in item or "price" in item or "qty" in item or "quantity" in item:
            if state in ("", "filled", "partially_filled", "executed", "completed"):
                return True
    filled = item.get("filled_qty") or item.get("filledQty") or item.get("executed_qty")
    try:
        if filled is not None and float(filled) > 0:
            return True
    except (TypeError, ValueError):
        pass
    return False


def _pair_of(item: dict) -> str:
    return str(
        item.get("symbol")
        or item.get("pair")
        or item.get("trading_pair")
        or item.get("market")
        or ""
    ).upper()


def query_revx_live_today() -> dict:
    """Primary max-1/day guard: any successful BTC/ETH/SOL live order or trade today."""
    env = revx_env()
    today = today_local()
    symbols = ",".join(WHITELIST_PAIRS)
    hits: list[dict] = []
    errors: list[str] = []

    # Order history for all whitelist pairs today
    cmd_hist = [
        REVX_BIN,
        "order",
        "history",
        "--symbols",
        symbols,
        "--start-date",
        "today",
        "--json",
        "--limit",
        "50",
    ]
    try:
        proc = subprocess.run(cmd_hist, capture_output=True, text=True, env=env, timeout=60)
        if proc.returncode != 0:
            errors.append(
                f"order history rc={proc.returncode}: {(proc.stderr or proc.stdout or '')[:300]}"
            )
        else:
            for item in _as_list(_parse_json_stdout(proc.stdout)):
                if not isinstance(item, dict):
                    continue
                pair = _pair_of(item)
                if pair and pair not in WHITELIST_PAIRS:
                    continue
                if _item_looks_success(item) or (
                    # With --order-states unset, include any non-cancelled/rejected row as caution
                    str(item.get("order_state") or item.get("state") or item.get("status") or "")
                    .lower()
                    .replace(" ", "_")
                    not in ("cancelled", "canceled", "rejected", "expired")
                    and pair in WHITELIST_PAIRS
                    and item
                ):
                    # Count only clearly successful fills; cancelled alone do not block
                    if _item_looks_success(item):
                        hits.append({"source": "order_history", "pair": pair or "?", "item": item})
    except (OSError, subprocess.TimeoutExpired) as e:
        errors.append(f"order history failed: {e}")

    # Also probe private trades per pair (covers wiped live_day.json)
    for pair in WHITELIST_PAIRS:
        cmd_tr = [
            REVX_BIN,
            "trade",
            "private",
            pair,
            "--start-date",
            "today",
            "--json",
            "--limit",
            "20",
        ]
        try:
            proc = subprocess.run(cmd_tr, capture_output=True, text=True, env=env, timeout=60)
            if proc.returncode != 0:
                errors.append(
                    f"trade {pair} rc={proc.returncode}: {(proc.stderr or proc.stdout or '')[:200]}"
                )
                continue
            for item in _as_list(_parse_json_stdout(proc.stdout)):
                if isinstance(item, dict):
                    # Any private trade row today is a successful live fill
                    hits.append({"source": "trade_private", "pair": pair, "item": item})
        except (OSError, subprocess.TimeoutExpired) as e:
            errors.append(f"trade {pair} failed: {e}")

    # Deduplicate by id if present
    seen: set[str] = set()
    unique: list[dict] = []
    for h in hits:
        item = h.get("item") or {}
        key = str(item.get("id") or item.get("order_id") or item.get("trade_id") or id(item))
        if key in seen:
            continue
        seen.add(key)
        unique.append(h)

    return {
        "date": today,
        "count": len(unique),
        "hits": unique[:10],  # cap payload
        "errors": errors or None,
        "queried_at": now_brussels().isoformat(),
    }


def estimate_costs_eur(amount_eur: float) -> float:
    return max(0.01, amount_eur * (FEE_ESTIMATE_BPS / 10_000.0))


def check_expectancy(order: dict, skip: bool) -> dict:
    """Return {ok, error?, details} for expectancy gate."""
    if skip:
        return {"ok": True, "skipped": True}

    missing = [
        k
        for k in ("expected_gain_eur", "expected_loss_eur")
        if order.get(k) is None
    ]
    if missing:
        return {
            "ok": False,
            "error": (
                f"expectancy fields missing: {missing}. "
                "Provide expected_gain_eur, expected_loss_eur, and optionally costs_eur "
                "(or rely on fee estimate). "
                "Gate: expected_gain_eur >= 3 * (costs_eur + expected_loss_eur). "
                "For dry-run tests only: pass --skip-expectancy with --dry-run."
            ),
        }

    try:
        expected_gain = float(order["expected_gain_eur"])
        expected_loss = float(order["expected_loss_eur"])
    except (TypeError, ValueError) as e:
        return {"ok": False, "error": f"invalid expectancy numbers: {e}"}

    if order.get("costs_eur") is not None:
        try:
            costs = float(order["costs_eur"])
            costs_source = "order.costs_eur"
        except (TypeError, ValueError) as e:
            return {"ok": False, "error": f"invalid costs_eur: {e}"}
    else:
        amount_eur = float(order.get("amount_eur") or 0)
        costs = estimate_costs_eur(amount_eur)
        costs_source = f"fee_estimate_{FEE_ESTIMATE_BPS}bps"

    threshold = EXPECTANCY_MULTIPLE * (costs + expected_loss)
    ok = expected_gain >= threshold
    details = {
        "expected_gain_eur": expected_gain,
        "expected_loss_eur": expected_loss,
        "costs_eur": costs,
        "costs_source": costs_source,
        "multiple": EXPECTANCY_MULTIPLE,
        "threshold": threshold,
        "formula": "expected_gain_eur >= 3 * (costs_eur + expected_loss_eur)",
    }
    if not ok:
        return {
            "ok": False,
            "error": (
                f"expectancy gate failed: gain {expected_gain} < "
                f"{EXPECTANCY_MULTIPLE}*(costs {costs} + loss {expected_loss}) = {threshold}"
            ),
            "details": details,
        }
    return {"ok": True, "details": details}


# ---------------------------------------------------------------------------
# Horaires live — 8 oct (validé Quentin). Nouvelles entrées live seulement.
# ---------------------------------------------------------------------------
LIVE_WINDOW_DEFAULTS = {
    "start": "15:00",
    "end": "17:00",
    "force_close": "22:00",
    "post_announcement_block_min": 15,
    "announcement_times": ["14:30", "15:30"],
}
ANNONCES_PATH = ROOT / "state" / "annonces_du_jour.json"
EXTRA_SESSION_PATH = ROOT / "state" / "LIVE_EXTRA_SESSION.json"


def _hhmm(v) -> int | None:
    """'HH:MM' -> minutes since midnight (None if invalid)."""
    try:
        h, m = str(v).strip().split(":")[:2]
        h, m = int(h), int(m)
    except (ValueError, AttributeError):
        return None
    if not (0 <= h <= 24 and 0 <= m < 60) or h * 60 + m > 24 * 60:
        return None
    return h * 60 + m


def _fmt(mins: int) -> str:
    return f"{mins // 60:02d}:{mins % 60:02d}"


def load_live_window_cfg() -> dict:
    try:
        cfg = json.loads((GUARDIAN / "config.json").read_text())
    except (OSError, json.JSONDecodeError):
        cfg = {}
    lw = dict(LIVE_WINDOW_DEFAULTS)
    lw.update(cfg.get("live_window") or {})
    times = list(lw.get("announcement_times") or [])
    for t in cfg.get("announcement_times") or []:  # optional top-level list too
        if t not in times:
            times.append(t)
    lw["announcement_times"] = times
    return lw


def _read_json_file(path: Path) -> dict | None:
    try:
        d = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError):
        return None
    return d if isinstance(d, dict) else None


def extra_session_today(today: str) -> dict | None:
    """state/LIVE_EXTRA_SESSION.json (feu vert de Quentin) valid for today only."""
    d = _read_json_file(EXTRA_SESSION_PATH)
    if not d or str(d.get("date")) != today:
        return None
    w = d.get("window")
    start, end = d.get("start"), d.get("end")
    if isinstance(w, dict):
        start, end = w.get("start", start), w.get("end", end)
    elif isinstance(w, str) and "-" in w:
        start, end = (x.strip() for x in w.split("-", 1))
    s, e = _hhmm(start), _hhmm(end)
    if s is None or e is None or e <= s:
        return None
    return {"start": s, "end": e, "note": d.get("note") or d.get("by")}


def check_live_window(now: datetime | None = None) -> dict:
    """Return {ok, reason_fr?, ...} for a NEW live entry at `now` (Brussels)."""
    now = (now or now_brussels()).astimezone(TZ)
    today = now.date().isoformat()
    lw = load_live_window_cfg()
    cur = now.hour * 60 + now.minute
    def _m(key: str, default: int) -> int:
        v = _hhmm(lw.get(key))
        return default if v is None else v

    start, end, force = _m("start", 15 * 60), _m("end", 17 * 60), _m("force_close", 22 * 60)
    try:
        block = int(lw.get("post_announcement_block_min", 15))
    except (TypeError, ValueError):
        block = 15
    ann = [(str(t), "config") for t in lw.get("announcement_times") or []]
    ad = _read_json_file(ANNONCES_PATH)
    if ad and str(ad.get("date")) == today:
        ann += [(str(t), "annonces_du_jour") for t in ad.get("times") or []]
    extra = extra_session_today(today)
    info = {
        "now": now.isoformat(timespec="seconds"),
        "window": f"{_fmt(start)}–{_fmt(end)}",
        "force_close": _fmt(force),
        "announcements": [t for t, _ in ann],
        "post_announcement_block_min": block,
        "extra_session": f"{_fmt(extra['start'])}–{_fmt(extra['end'])}" if extra else None,
    }
    hm = now.strftime("%H:%M")
    if cur >= force:
        return {**info, "ok": False, "reason": "after_force_close",
                "reason_fr": f"Live refusé : il est {hm} (Bruxelles), après l'heure de fermeture "
                             f"{_fmt(force)}. Pas de live le soir ni la nuit."}
    in_main = start <= cur < end
    in_extra = bool(extra) and extra["start"] <= cur < min(extra["end"], force)
    if not (in_main or in_extra):
        extra_txt = (f" (séance en plus aujourd'hui : {info['extra_session']})" if extra else "")
        return {**info, "ok": False, "reason": "outside_window",
                "reason_fr": f"Live refusé : il est {hm} (Bruxelles), hors du créneau live "
                             f"{info['window']}{extra_txt}. Une séance en plus demande le feu vert de "
                             f"Quentin (state/LIVE_EXTRA_SESSION.json)."}
    for t, src in ann:
        a = _hhmm(t)
        if a is None:
            continue
        if a <= cur < a + block:
            return {**info, "ok": False, "reason": "post_announcement", "announcement": t,
                    "announcement_source": src,
                    "reason_fr": f"Live refusé : il est {hm} (Bruxelles), moins de {block} min après "
                                 f"l'annonce de {t}. Live de nouveau possible à {_fmt(a + block)}."}
    return {**info, "ok": True, "session": "main" if in_main else "extra"}


# ---------------------------------------------------------------------------
# Sortie automatique sur stop (LIVE) — 8 oct, décision Quentin
#   python3 live_place.py --exit --order exit_spec.json     (appelé par watch_stops)
# spec: {position_id, pair, side: long|short, stop, trigger_price, close_reason,
#        qty_hint?, cost_eur?, avg_price?}
# - n'exige PAS LIVE_ONCE / MODE=live, ne le consomme pas, n'écrit PAS live_day.json
# - autorisée même si STOP / HALTED existe (réduit le risque)
# - verrou par position dans state/live_exits.json (une seule sortie, jamais de doublon)
# - relit chez Revolut: ordre d'entrée, ordres ouverts, solde ; annule l'ordre objectif
#   du bot lié à la position ; vend min(qty position, solde dispo − avoirs Quentin)
# - limite exécutable (pas post-only) au meilleur acheteur −0,3 % (rachat: vendeur +0,3 %),
#   attente ~60 s, sinon annule + replace à −0,5 %, 3 essais max → sinon alerte urgente
# ---------------------------------------------------------------------------
CONFIG_PATH = GUARDIAN / "config.json"
EXITS_PATH = ROOT / "state" / "live_exits.json"
EXITS_LOCK = ROOT / "state" / "live_exits.lock"
LIVE_EQUITY_PATH = ROOT / "state" / "live_equity.json"
EXIT_DEFAULTS = {
    "first_margin_pct": 0.3,
    "retry_margin_pct": 0.5,
    "fill_wait_s": 60.0,
    "poll_s": 5.0,
    "max_attempts": 3,
    "dust_eur": 0.5,
    "quentin_holdings": {"BTC": 0.0000066, "ETH": 0.0309, "SOL": 0.342},
    "pair_steps": {
        "BTC-EUR": {"base_step": 1e-8, "quote_step": 0.01, "min_quote": 0.1},
        "ETH-EUR": {"base_step": 1e-8, "quote_step": 0.01, "min_quote": 0.1},
        "SOL-EUR": {"base_step": 1e-6, "quote_step": 0.001, "min_quote": 0.1},
    },
}
OPEN_ORDER_STATES = frozenset({"new", "pending_new", "partially_filled", "partially-filled", "open", "active"})


def _fnum(v, default=None):
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


def load_exit_cfg() -> dict:
    try:
        cfg = json.loads(CONFIG_PATH.read_text())
    except (OSError, json.JSONDecodeError):
        cfg = {}
    ex = dict(EXIT_DEFAULTS)
    ex.update(cfg.get("live_exit") or {})
    ex["allow"] = bool(cfg.get("allow_live_auto_sell", False))
    # Test hooks (only shorten waits)
    for env_key, key in (("LIVE_EXIT_FILL_WAIT_S", "fill_wait_s"), ("LIVE_EXIT_POLL_S", "poll_s")):
        if os.environ.get(env_key):
            ex[key] = float(os.environ[env_key])
    return ex


def revx_json(args: list[str], timeout: float = 40.0) -> tuple[object, str | None, int]:
    try:
        proc = subprocess.run([REVX_BIN, *args], capture_output=True, text=True, env=revx_env(), timeout=timeout)
    except (OSError, subprocess.TimeoutExpired) as e:
        return None, str(e), -1
    if proc.returncode != 0:
        return None, (proc.stderr or proc.stdout or "")[:300], proc.returncode
    return _parse_json_stdout(proc.stdout), None, 0


def _unwrap_one(payload: object) -> dict:
    if isinstance(payload, dict) and "data" in payload:
        payload = payload["data"]
    if isinstance(payload, list):
        payload = payload[0] if payload else {}
    return payload if isinstance(payload, dict) else {}


def exit_get_ticker(pair: str) -> tuple[float | None, float | None]:
    data, _err, _rc = revx_json(["market", "ticker", pair, "--json"])
    d = _unwrap_one(data)
    return _fnum(d.get("bid") or d.get("bestBid")), _fnum(d.get("ask") or d.get("bestAsk"))


def exit_get_balance(currency: str) -> tuple[float, float] | None:
    """(available, total) from `revx account balances` (read-only). None if unreadable."""
    data, err, _rc = revx_json(["account", "balances", "--currencies", currency, "--json"])
    if err is not None:
        return None
    for b in _as_list(data):
        if isinstance(b, dict) and str(b.get("currency") or "").upper() == currency.upper():
            total = _fnum(b.get("total"))
            avail = _fnum(b.get("available"))
            if avail is None:
                avail = (total or 0.0) - (_fnum(b.get("reserved"), 0.0) or 0.0)
            if total is None:
                total = avail + (_fnum(b.get("reserved"), 0.0) or 0.0)
            return max(0.0, avail), max(0.0, total)
    return 0.0, 0.0  # currency absent = zero balance


def exit_get_available(currency: str) -> float | None:
    b = exit_get_balance(currency)
    return None if b is None else b[0]


def exit_open_orders(pair: str) -> list[dict] | None:
    data, err, _rc = revx_json(["order", "open", "--symbols", pair, "--json", "--limit", "50"])
    if err is not None:
        return None
    return [o for o in _as_list(data) if isinstance(o, dict)]


def exit_get_order(order_id: str) -> dict | None:
    data, err, _rc = revx_json(["order", "get", order_id, "--json"])
    if err is not None:
        return None
    return _unwrap_one(data)


def exit_cancel(order_id: str) -> bool:
    try:
        proc = subprocess.run([REVX_BIN, "order", "cancel", order_id], capture_output=True, text=True,
                              env=revx_env(), timeout=40)
    except (OSError, subprocess.TimeoutExpired):
        return False
    return proc.returncode == 0


def _order_state(o: dict) -> str:
    return str(o.get("status") or o.get("state") or o.get("order_state") or "").lower().replace(" ", "_")


def _order_filled(o: dict) -> tuple[float, float | None]:
    q = _fnum(o.get("filled_quantity") or o.get("filled_qty") or o.get("filledQty") or o.get("executed_qty"), 0.0) or 0.0
    a = _fnum(o.get("filled_amount") or o.get("filled_quote") or o.get("filledAmount"))
    return q, a


def _order_ids(o: dict) -> set[str]:
    return {str(x) for x in (o.get("id"), o.get("venue_order_id"), o.get("order_id"), o.get("client_order_id")) if x}


def _row_ids(row: dict) -> tuple[str | None, str | None]:
    """(venue order id from stdout, client order id from cmd) of a live_orders row."""
    cmd = row.get("cmd") or []
    coid = None
    if "--client-order-id" in cmd:
        i = cmd.index("--client-order-id")
        if i + 1 < len(cmd):
            coid = str(cmd[i + 1])
    d = _unwrap_one(_parse_json_stdout(row.get("stdout") or ""))
    oid = d.get("id") or d.get("venue_order_id") or d.get("order_id")
    return (str(oid) if oid else None), (str(d.get("client_order_id") or coid) if (d.get("client_order_id") or coid) else None)


def live_row_position_id(row: dict) -> str | None:
    """Same id formula as watch_stops.load_live_orders_open."""
    order = row.get("order") if isinstance(row.get("order"), dict) else row
    pair = str(order.get("pair") or "").upper()
    if not pair:
        return None
    oid = str(order.get("id") or row.get("client_order_id") or f"live-{pair}-{row.get('at')}")
    return oid if oid.startswith("rx-live") or oid.startswith("live-") else f"rx-live-{oid}"


def _read_live_rows() -> list[dict]:
    if not LOG_PATH.exists():
        return []
    rows = []
    for line in LOG_PATH.read_text().splitlines():
        try:
            r = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(r, dict):
            rows.append(r)
    return rows


def _floor_step(x: float, step: float) -> float:
    if step <= 0:
        return x
    n = int((x + 1e-15) / step)
    return round(n * step, 12)


def _ceil_step(x: float, step: float) -> float:
    if step <= 0:
        return x
    n = int(x / step)
    if n * step < x - 1e-12:
        n += 1
    return round(n * step, 12)


def quentin_reserve(asset: str, ex: dict) -> float:
    """Coins held by Quentin outside the bot: max(config, live_equity hors_bot)."""
    r = _fnum((ex.get("quentin_holdings") or {}).get(asset), 0.0) or 0.0
    try:
        eq = json.loads(LIVE_EQUITY_PATH.read_text())
        hb = (eq.get("hors_bot") or {}).get(asset) or {}
        r = max(r, _fnum(hb.get("qty"), 0.0) or 0.0)
    except (OSError, json.JSONDecodeError, AttributeError):
        pass
    return r


class _ExitLock:
    def __enter__(self):
        import fcntl

        EXITS_LOCK.parent.mkdir(parents=True, exist_ok=True)
        self.f = EXITS_LOCK.open("a+")
        fcntl.flock(self.f, fcntl.LOCK_EX)
        return self

    def __exit__(self, *exc):
        import fcntl

        fcntl.flock(self.f, fcntl.LOCK_UN)
        self.f.close()


def _load_exits() -> dict:
    try:
        return json.loads(EXITS_PATH.read_text())
    except (OSError, json.JSONDecodeError):
        return {}


def _save_exits(d: dict) -> None:
    EXITS_PATH.parent.mkdir(parents=True, exist_ok=True)
    tmp = EXITS_PATH.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(d, indent=2, ensure_ascii=False) + "\n")
    tmp.replace(EXITS_PATH)


def _update_exit(pid: str, **fields) -> dict:
    with _ExitLock():
        d = _load_exits()
        e = d.get(pid) or {}
        e.update(fields)
        d[pid] = e
        _save_exits(d)
        return e


def place_exit(spec: dict) -> dict:
    """Automatic live exit for ONE pipeline position (see block comment above)."""
    ex = load_exit_cfg()
    pid = str(spec.get("position_id") or "").strip()
    pair = str(spec.get("pair") or "").upper()
    side = "short" if str(spec.get("side") or "long").lower() in ("short", "sell") else "long"
    base = pair.split("-")[0]
    out: dict = {"position_id": pid, "pair": pair, "side": side, "at": now_brussels().isoformat()}
    if not ex["allow"]:
        return {**out, "ok": False, "status": "disabled", "error": "allow_live_auto_sell is false in config"}
    if not pid or pair not in WHITELIST_PAIRS:
        return {**out, "ok": False, "status": "bad_spec", "error": "position_id / whitelist pair required"}

    # 1) Lock: one exit per position, never a duplicate (even after failure)
    with _ExitLock():
        d = _load_exits()
        if pid in d:
            return {**out, "ok": False, "status": "already_handled", "existing": d[pid], "duplicate_blocked": True}
        d[pid] = {"status": "in_progress", "pid": os.getpid(), "started_at": out["at"], "pair": pair,
                  "side": side, "spec": spec}
        _save_exits(d)

    steps = ex.get("pair_steps", {}).get(pair) or EXIT_DEFAULTS["pair_steps"].get(pair) or {}
    base_step = float(steps.get("base_step", 1e-8))
    quote_step = float(steps.get("quote_step", 0.01))
    min_quote = float(steps.get("min_quote", 0.1))
    dust = float(ex.get("dust_eur", 0.5))
    exit_side = "sell" if side == "long" else "buy"
    entry_side = "buy" if side == "long" else "sell"
    log: list[dict] = []
    try:
        # 2) Entry row + entry order status (cancel any unfilled remainder of OUR entry)
        rows = _read_live_rows()
        entry_row = next((r for r in rows if r.get("ok") and not r.get("dry_run") and r.get("kind") != "auto_exit"
                          and live_row_position_id(r) == pid), None)
        entry_oid, entry_coid = _row_ids(entry_row) if entry_row else (None, None)
        pos_qty = None
        entry_info: dict = {"order_id": entry_oid, "client_order_id": entry_coid}
        if entry_oid:
            eo = exit_get_order(entry_oid)
            if eo:
                st = _order_state(eo)
                if st in OPEN_ORDER_STATES:
                    entry_info["cancelled_remainder"] = exit_cancel(entry_oid)
                    eo = exit_get_order(entry_oid) or eo
                    st = _order_state(eo)
                fq, _fa = _order_filled(eo)
                entry_info.update({"status": st, "filled_qty": fq})
                pos_qty = fq
        if pos_qty is None:
            q = _fnum(spec.get("qty_hint"))
            if not q:
                cost, avg = _fnum(spec.get("cost_eur")), _fnum(spec.get("avg_price"))
                q = (cost / avg) if cost and avg else None
            pos_qty = q or 0.0
            entry_info["qty_source"] = "spec_estimate"
        out["entry"] = entry_info
        out["position_qty"] = pos_qty
        cost_eur = _fnum(spec.get("cost_eur"), 0.0) or 0.0
        avg_entry = _fnum(spec.get("avg_price")) or (cost_eur / pos_qty if pos_qty else None)

        if pos_qty <= 0:
            status = "no_fill" if entry_oid else "failed"
            res = {**out, "ok": status == "no_fill", "status": status, "sold_qty": 0.0,
                   "note": "entrée jamais remplie (reste annulé) — rien à vendre" if status == "no_fill"
                   else "quantité de la position inconnue — rien vendu"}
            _finish_exit(pid, res, spec, cost_eur, exit_side)
            return res

        # 3) Cancel OUR target/objective order(s) linked to this position (never Quentin's orders)
        target_ids: set[str] = set()
        for r in rows:
            if not r.get("ok") or r.get("dry_run") or r is entry_row:
                continue
            o = r.get("order") if isinstance(r.get("order"), dict) else r
            if str(o.get("pair") or "").upper() != pair or str(o.get("side") or "").lower() != exit_side:
                continue
            linked = {str(o.get(k)) for k in ("linked_position_id", "cycle_id", "target_for", "exit_for") if o.get(k)}
            if pid in linked or str(o.get("purpose") or "").lower() in ("target", "objectif"):
                target_ids |= {x for x in _row_ids(r) if x}
        opens = exit_open_orders(pair)
        if opens is None:
            raise RuntimeError("lecture des ordres ouverts Revolut impossible")
        cancelled = []
        target_filled = 0.0
        seen_target: set[str] = set()
        for o in opens:
            if str(o.get("side") or "").lower() == exit_side and _order_ids(o) & target_ids:
                oid = str(o.get("id") or o.get("venue_order_id") or o.get("order_id"))
                ok_c = exit_cancel(oid)
                after = exit_get_order(oid) or o
                fq, _ = _order_filled(after)
                target_filled += fq
                seen_target |= _order_ids(o)
                cancelled.append({"order_id": oid, "ok": ok_c, "filled_before_cancel": fq})
        # Target orders no longer open: already filled part of the position?
        for r in rows:
            o = r.get("order") if isinstance(r.get("order"), dict) else r
            vid, _c = _row_ids(r)
            if vid and vid in target_ids and vid not in seen_target:
                to = exit_get_order(vid)
                if to:
                    target_filled += _order_filled(to)[0]
        out["cancelled_target_orders"] = cancelled
        out["target_filled_qty"] = target_filled
        out["other_open_orders_untouched"] = sum(1 for o in opens if not (_order_ids(o) & target_ids))
        if target_filled > 0:
            pos_qty = max(0.0, pos_qty - target_filled)
            out["position_qty"] = pos_qty
            ref = _fnum(spec.get("trigger_price")) or 0.0
            if pos_qty * ref < dust:
                res = {**out, "ok": True, "status": "closed_by_target", "sold_qty": 0.0,
                       "note": "position déjà vendue par l'ordre objectif — rien à vendre"}
                _finish_exit(pid, res, spec, cost_eur, exit_side)
                return res
        if cancelled:
            time.sleep(min(2.0, float(ex.get("poll_s", 5))))

        # 4) Real balance, Quentin's coins protected
        if side == "long":
            bal = exit_get_balance(base)
            if bal is None:
                raise RuntimeError(f"lecture du solde {base} Revolut impossible")
            avail, total = bal
            reserve = quentin_reserve(base, ex)
            # bot coins = total − Quentin's holdings; also limited by what is available now
            sellable = max(0.0, min(avail, total - reserve))
            target_qty = _floor_step(min(pos_qty, sellable), base_step)
            out["balance"] = {"available": avail, "total": total, "quentin_reserve": reserve,
                              "sellable_bot": sellable}
        else:
            avail_eur = exit_get_available("EUR")
            if avail_eur is None:
                raise RuntimeError("lecture du solde EUR Revolut impossible")
            target_qty = _floor_step(pos_qty, base_step)
            out["balance"] = {"available_eur": avail_eur}
        out["target_qty"] = target_qty

        # 5) Executable limit orders, up to max_attempts
        sold = 0.0
        quote_total = 0.0
        remaining = target_qty
        attempts = int(ex.get("max_attempts", 3))
        for i in range(1, attempts + 1):
            if remaining <= 0:
                break
            bid, ask = exit_get_ticker(pair)
            ref_px = (bid if side == "long" else ask) or _fnum(spec.get("trigger_price"))
            if not ref_px:
                log.append({"attempt": i, "error": "pas de prix acheteur/vendeur"})
                continue
            margin = float(ex["first_margin_pct"] if i == 1 else ex["retry_margin_pct"]) / 100.0
            if side == "long":
                px = _floor_step(ref_px * (1 - margin), quote_step)
                qty = _floor_step(remaining, base_step)
            else:
                px = _ceil_step(ref_px * (1 + margin), quote_step)
                eur_now = exit_get_available("EUR")
                cap = _floor_step((eur_now or 0.0) / px, base_step) if px else 0.0
                qty = _floor_step(min(remaining, cap), base_step)
            if qty * px < min_quote:
                log.append({"attempt": i, "skip": "quantité sous le minimum", "qty": qty, "price": px})
                break
            coid = str(uuid.uuid4())
            cmd = ["order", "place", pair, exit_side, "--qty", f"{qty:.8f}".rstrip("0").rstrip("."),
                   "--limit", f"{px:.8f}".rstrip("0").rstrip("."), "--json", "--client-order-id", coid]
            data, err, rc = revx_json(cmd, timeout=60)
            entry = {"attempt": i, "side": exit_side, "qty": qty, "limit": px, "ref_price": ref_px,
                     "margin_pct": margin * 100, "client_order_id": coid}
            if err is not None:
                entry["error"] = err
                log.append(entry)
                time.sleep(1.0)
                continue
            od = _unwrap_one(data)
            oid = str(od.get("id") or od.get("venue_order_id") or od.get("order_id") or coid)
            entry["order_id"] = oid
            deadline = time.monotonic() + float(ex["fill_wait_s"])
            o = od
            while True:
                o = exit_get_order(oid) or o
                fq, _ = _order_filled(o)
                if fq >= qty - base_step / 2 or _order_state(o) in ("filled", "done", "completed"):
                    break
                if time.monotonic() >= deadline:
                    break
                time.sleep(float(ex["poll_s"]))
            fq, fa = _order_filled(o)
            if fq < qty - base_step / 2 and _order_state(o) not in ("filled", "done", "completed"):
                entry["cancelled"] = exit_cancel(oid)
                o = exit_get_order(oid) or o  # final fill after cancel
                fq, fa = _order_filled(o)
            fq = min(fq, qty)
            entry.update({"filled_qty": fq, "filled_amount": fa if fa is not None else round(fq * px, 8),
                          "state": _order_state(o)})
            log.append(entry)
            sold += fq
            quote_total += fa if fa is not None else fq * px
            remaining = _floor_step(target_qty - sold, base_step)
            if remaining * (ref_px or px) < max(min_quote, dust):
                remaining = 0.0
        out["attempts"] = log
        avg_px = (quote_total / sold) if sold > 0 else None
        unsold_vs_pos = max(0.0, pos_qty - sold)
        ref = avg_px or _fnum(spec.get("trigger_price")) or 0.0
        if sold > 0 and unsold_vs_pos * ref < dust:
            status = "done"
        elif sold > 0:
            status = "partial"
        else:
            status = "failed"
        frac = 1.0 if status == "done" else (min(1.0, sold / pos_qty) if pos_qty else 0.0)  # done = dust ignored
        cost_closed = round(cost_eur * frac, 6)
        if side == "long":
            pnl = round(quote_total - cost_closed, 6) if sold > 0 else None
        else:
            pnl = round(cost_closed - quote_total, 6) if sold > 0 else None
        res = {**out, "ok": status == "done", "status": status, "sold_qty": round(sold, 12),
               "avg_price": avg_px, "quote_eur": round(quote_total, 6), "cost_closed_eur": cost_closed,
               "realized_pnl_eur": pnl, "unsold_qty": round(unsold_vs_pos, 12), "urgent": status != "done",
               "avg_entry": avg_entry}
        _finish_exit(pid, res, spec, cost_closed, exit_side)
        return res
    except Exception as e:  # noqa: BLE001
        res = {**out, "ok": False, "status": "error", "error": str(e), "attempts": log, "urgent": True}
        _finish_exit(pid, res, spec, 0.0, exit_side)
        return res


def _finish_exit(pid: str, res: dict, spec: dict, cost_closed: float, exit_side: str) -> None:
    """Persist final lock status + journal row (kind=auto_exit) in live_orders.jsonl."""
    _update_exit(pid, status=res.get("status"), finished_at=now_brussels().isoformat(),
                 result={k: v for k, v in res.items() if k != "attempts"}, attempts=res.get("attempts"))
    sold = float(res.get("sold_qty") or 0.0)
    if sold <= 0 and res.get("status") not in ("no_fill", "closed_by_target"):
        return
    row = {
        "ok": True,
        "kind": "auto_exit",
        "at": now_brussels().isoformat(),
        "order": {
            "pair": res.get("pair"),
            "side": exit_side,
            # amount_eur = cost basis closed (so buys − sells netting closes the position)
            "amount_eur": round(cost_closed if res.get("status") not in ("no_fill", "closed_by_target")
                                else float(spec.get("cost_eur") or 0), 6),
            "qty": sold,
            "price": res.get("avg_price"),
            "quote_eur": res.get("quote_eur"),
            "exit_for": pid,
            "linked_position_id": pid,
            "idea_type": "baisse" if res.get("side") == "short" else "hausse",
            "close_reason": spec.get("close_reason") or "stop_hit",
            "realized_pnl_eur": res.get("realized_pnl_eur"),
        },
        "status": res.get("status"),
        "attempts": res.get("attempts"),
        "note": ({"fermeture_22h": "fermeture auto 22h (horaires live 8 oct)",
                  "heure_limite": "sortie auto à l'heure limite (Predict)"}.get(
                      str(spec.get("close_reason")), "sortie auto sur stop (8 oct, décision Quentin)")
                 + " — ne compte pas comme trade live du jour"),
    }
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with LOG_PATH.open("a") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")



def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--order", help="order JSON path")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument(
        "--skip-expectancy",
        action="store_true",
        help="Skip expectancy gate (only allowed with --dry-run, for tests)",
    )
    ap.add_argument(
        "--exit",
        action="store_true",
        help="Automatic stop exit of ONE pipeline position (spec JSON via --order/stdin); "
        "no LIVE_ONCE, no live_day.json, allowed under STOP",
    )
    args = ap.parse_args()

    if args.exit:
        # Exit path: reduces risk → bypasses entry gates (STOP/HALTED, LIVE_ONCE, max 1/day,
        # expectancy, validate_order). Never touches LIVE_ONCE or live_day.json.
        spec = load_order(args.order)
        res = place_exit(spec)
        print(json.dumps(res, ensure_ascii=False))
        return 0 if res.get("ok") else 11

    if args.skip_expectancy and not args.dry_run:
        print(
            json.dumps(
                {
                    "ok": False,
                    "error": "--skip-expectancy only allowed with --dry-run",
                }
            )
        )
        return 2

    # Horaires live (8 oct) — nouvelles entrées seulement ; --dry-run rapporte sans refuser
    window = check_live_window()
    if not window.get("ok") and not args.dry_run:
        print(json.dumps({"ok": False, "error": window.get("reason_fr"), "live_window": window},
                         ensure_ascii=False))
        return 12

    if STOP_PATH.exists() or HALTED_PATH.exists():
        print(json.dumps({"ok": False, "error": "STOP or HALTED present"}))
        return 2

    # Primary: Revolut today (survives wiped live_day.json)
    revx_today = query_revx_live_today()
    file_count = live_count_today()
    effective_count = max(int(revx_today.get("count") or 0), file_count)

    if effective_count >= MAX_LIVE_PER_DAY and not args.dry_run:
        print(
            json.dumps(
                {
                    "ok": False,
                    "error": (
                        f"mechanical guard: already {effective_count} live today "
                        f"(max {MAX_LIVE_PER_DAY}); revx={revx_today.get('count')} "
                        f"live_day.json={file_count}"
                    ),
                    "date": today_local(),
                    "revx_today": {
                        "count": revx_today.get("count"),
                        "errors": revx_today.get("errors"),
                        "queried_at": revx_today.get("queried_at"),
                    },
                    "live_day_count": file_count,
                },
                ensure_ascii=False,
            )
        )
        return 7

    ok_arm, arm_reason = armed()
    if not ok_arm and not args.dry_run:
        print(
            json.dumps(
                {"ok": False, "error": arm_reason, "hint": "touch LIVE_ONCE or set MODE=live"}
            )
        )
        return 3

    order = load_order(args.order)

    # Min ticket
    try:
        amount_eur = float(order.get("amount_eur"))
    except (TypeError, ValueError):
        print(json.dumps({"ok": False, "error": "invalid or missing amount_eur"}))
        return 5
    if amount_eur < MIN_LIVE_EUR:
        print(
            json.dumps(
                {
                    "ok": False,
                    "error": (
                        f"min ticket gate: amount_eur {amount_eur} < MIN_LIVE_EUR {MIN_LIVE_EUR}"
                    ),
                    "MIN_LIVE_EUR": MIN_LIVE_EUR,
                }
            )
        )
        return 8

    # Expectancy gate
    exp = check_expectancy(order, skip=bool(args.skip_expectancy))
    if not exp.get("ok"):
        print(
            json.dumps(
                {
                    "ok": False,
                    "error": exp.get("error"),
                    "expectancy": exp.get("details"),
                },
                ensure_ascii=False,
            )
        )
        return 9

    if args.order:
        proc = subprocess.run(
            [sys.executable, str(VALIDATE), "--order", args.order], capture_output=True
        )
    else:
        proc = subprocess.run(
            [sys.executable, str(VALIDATE)],
            input=json.dumps(order).encode(),
            capture_output=True,
        )
    out = (proc.stdout or b"").decode()
    err = (proc.stderr or b"").decode()
    try:
        val = json.loads(out) if out.strip() else {"raw": err, "returncode": proc.returncode}
    except json.JSONDecodeError:
        val = {"raw": out + err, "returncode": proc.returncode}
    if proc.returncode != 0 or (isinstance(val, dict) and val.get("ok") is False):
        payload = {"ok": False, "error": "validate failed", "validate": val}
        if args.dry_run:
            payload["gates"] = {
                "live_window": {**window, "would_refuse": not window.get("ok")},
                "min_ticket": {"amount_eur": amount_eur, "MIN_LIVE_EUR": MIN_LIVE_EUR},
                "expectancy": exp,
                "max_live_per_day": {
                    "max": MAX_LIVE_PER_DAY,
                    "revx_count": revx_today.get("count"),
                    "live_day_count": file_count,
                    "effective_count": effective_count,
                    "would_refuse": effective_count >= MAX_LIVE_PER_DAY,
                    "revx_errors": revx_today.get("errors"),
                    "queried_at": revx_today.get("queried_at"),
                },
            }
            payload["at"] = now_brussels().isoformat()
        print(json.dumps(payload, ensure_ascii=False))
        return 4

    # Heure limite (Predict): normalize `deadline` / alias `deadline_at` on the journaled order
    try:
        _dl = parse_deadline(order_deadline_raw(order))
    except (TypeError, ValueError):
        _dl = None
    if _dl is not None:
        order["deadline"] = _dl.isoformat()

    pair = str(order["pair"]).upper()
    side = str(order["side"]).lower()
    price = float(order["price"])
    if str(order.get("type", "limit")).lower() != "limit":
        print(json.dumps({"ok": False, "error": "only limit orders allowed"}))
        return 5

    env = revx_env()

    cmd = [
        REVX_BIN,
        "order",
        "place",
        pair,
        side,
        "--quote",
        f"{amount_eur}",
        "--limit",
        f"{price}",
        "--post-only",
        "--json",
        "--client-order-id",
        str(uuid.uuid4()),
    ]
    if args.dry_run:
        print(
            json.dumps(
                {
                    "ok": True,
                    "dry_run": True,
                    "armed": arm_reason,
                    "cmd": cmd,
                    "validate": val,
                    "gates": {
                        "live_window": {**window, "would_refuse": not window.get("ok")},
                        "min_ticket": {"amount_eur": amount_eur, "MIN_LIVE_EUR": MIN_LIVE_EUR},
                        "expectancy": exp,
                        "max_live_per_day": {
                            "max": MAX_LIVE_PER_DAY,
                            "revx_count": revx_today.get("count"),
                            "live_day_count": file_count,
                            "effective_count": effective_count,
                            "would_refuse": effective_count >= MAX_LIVE_PER_DAY,
                            "revx_errors": revx_today.get("errors"),
                            "queried_at": revx_today.get("queried_at"),
                        },
                    },
                    "at": now_brussels().isoformat(),
                },
                ensure_ascii=False,
            )
        )
        return 0

    # Final refuse if revx already has a live today (belt after validate)
    if effective_count >= MAX_LIVE_PER_DAY:
        print(
            json.dumps(
                {
                    "ok": False,
                    "error": f"mechanical guard: already {effective_count} live today",
                    "revx_today": revx_today,
                },
                ensure_ascii=False,
            )
        )
        return 7

    window = check_live_window()  # re-check just before placing (gates above may take time)
    if not window.get("ok"):
        print(json.dumps({"ok": False, "error": window.get("reason_fr"), "live_window": window},
                         ensure_ascii=False))
        return 12

    placed = subprocess.run(cmd, capture_output=True, text=True, env=env)
    result = {
        "ok": placed.returncode == 0,
        "armed": arm_reason,
        "at": now_brussels().isoformat(),
        "cmd": cmd,
        "stdout": placed.stdout,
        "stderr": placed.stderr,
        "returncode": placed.returncode,
        "order": order,
        "gates": {
            "live_window": window,
            "expectancy": exp,
            "min_ticket": {"amount_eur": amount_eur, "MIN_LIVE_EUR": MIN_LIVE_EUR},
            "revx_today_count": revx_today.get("count"),
            "live_day_count": file_count,
        },
    }
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with LOG_PATH.open("a") as f:
        f.write(json.dumps(result, ensure_ascii=False) + "\n")

    if placed.returncode == 0:
        record_live_success()
        if LIVE_ONCE.exists():
            LIVE_ONCE.unlink(missing_ok=True)
        # After the gates above (unchanged): start the stop watcher (urgent wake only on stop)
        result.update(start_stop_watcher(pair))
    else:
        result.update({"watcher_started": False, "watcher_already_running": False})

    print(json.dumps(result, ensure_ascii=False))
    return 0 if placed.returncode == 0 else 6


if __name__ == "__main__":
    raise SystemExit(main())
