#!/usr/bin/env python3
"""Sonnette (doorbell) — free price watcher that wakes a Grok Bot routine by webhook.

No AI, stdlib only. Reads prices ONLY from the team collector files:
  /workspace/predict-market-bot/state/price_ticks/YYYY-MM-DD.jsonl

Three bells:
  * predict  : manual zones in state/zones_reveil.json (bot="predict"),
               only inside a time window (default 15:00-17:00 Brussels, weekdays),
               max 3 rings/day total, each zone at most once/day.
  * risk     : ONLY while a REAL (live) position is open:
               stop_hit (price <= stop, any hour, repeat >= 10 min, max 6/day/position),
               stop_near (price within 1% above stop, once/position/day),
               daily_loss (12% then 15%) / drawdown (6% then 8%) from live_equity.json (real capital),
               only if a real buy is open OR one was made today,
               stale_price (newest tick > 10 min old: once, then every 30 min),
               manual zones with bot="risk" (once/zone/day, only while a real position is open).
               Health (sim OR live position open, Risk bell only, never Quentin directly):
               watcher_down (watch_stops_heartbeat.json > 3 min old or pid dead,
                            or ABSENT > 3 min while a position is open),
               revolut_down (revolut_heartbeat.json ok=false x>=2 or > 12 min old);
               max 1 ring per kind per 30 min, reset (« rétabli ») when healthy.
               Sim/paper positions never ring (watch_stops.py handles them).
  * compound : « trade fermé » — wakes PM-Compound ONCE per closed trade (sim or live).
               Sources (read-only): guardian/state.json (status=closed), trades_log.jsonl
               (close_reason), state/live_orders.jsonl (kind=auto_exit).
               Max 5 rings/day (Brussels); beyond → log « reporté au bilan 20h32 », no ring.
               Dedupe state survives restarts; first start seeds already-closed trades as rung.
  * predict, extra rings (same 6/day Predict limit, all in rings.jsonl):
               sans_decision : no new D-xxx header in knowledge/decision_log.md for 4 h AND room under the
                 simulation cap (guardian/state.json exposure_eur vs paper_max_exposure_pct × bankroll_eur) →
                 « pas de décision depuis 4 h… ». Max 1 per 4 h, max 2 per night (22h–09h). config → idle.
               heure_limite : the watcher wrote a deadline reminder (state/deadline_reminders.jsonl /
                 deadline_reminder.json) for a still-open trade → ring once per trade (id + current price);
                 Predict decides, Risk closes or keeps within 5 min. Reminders present at first start = seeded.
               status.json : zones_distance (nearest Predict zone below/above each price, flag if > 1 %),
               mouvement : a pair moves > 0.5 % from its price at Predict's latest D-xxx → ring Predict (no daily cap,
               min 30 min after the later of the last movement ring and the latest D-xxx),
                 night_sans_decision (no D-xxx between 22h and 09h last night) — the first Predict ring
                 after 09h then starts with « Nuit sans décision ».
  * resume  : a gap between two cycles (both wall clock and monotonic, > health.resume_gap_s) = machine
               pause/resume → heartbeat AGE checks (watcher_down, revolut_down « trop vieux » / absent) wait
               a grace period (watcher 90 s, Revolut 600 s = 2 tests of 5 min) before ringing Risk.
  * départs : « alertes de départ » (breakout hausse/baisse + accumulation) — OBSERVATION ONLY,
               never rings. Every ~10 min, 1 batch of read-only `revx market candles` (15m) for the
               3 pairs → state/departs.jsonl; outcomes at +1h/+4h/+24h → state/departs_resultats.jsonl.
               Thresholds in config.json → departs (see departs.py). `--departs` prints the summary.

Secrets come ONLY from env or the secrets file (never logged):
  SONNETTE_PREDICT_URL,  SONNETTE_PREDICT_AUTH  (full header value) or SONNETTE_PREDICT_KEY
  SONNETTE_RISK_URL,     SONNETTE_RISK_AUTH     (full header value) or SONNETTE_RISK_KEY
  SONNETTE_COMPOUND_URL, SONNETTE_COMPOUND_AUTH (full header value) or SONNETTE_COMPOUND_KEY
Missing URL/key => dry mode (log + state, no POST).

Usage:
  python3 sonnette.py                 # run loop (every 30 s)
  python3 sonnette.py --once          # one cycle
  python3 sonnette.py --status        # human status
  python3 sonnette.py --test risk     # one test ring (test=true); dry if no secrets
  python3 sonnette.py --test compound
  python3 sonnette.py --simulate      # self-tests with fake ticks in /tmp (never touches real state)
  python3 sonnette.py --departs       # summary of the « alertes de départ » (observation)
"""
from __future__ import annotations

import argparse
import copy
import json
import os
import re
import shutil
import signal
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import departs
import live_equity

TZ = ZoneInfo("Europe/Brussels")
HERE = Path(__file__).resolve().parent
TEAM = Path("/workspace/predict-market-bot")
ALLOWED_PAIRS = ("BTC-EUR", "ETH-EUR", "SOL-EUR")
BOTS = ("predict", "risk", "compound")
ZONE_BOTS = ("predict", "risk")  # only these may appear in zones_reveil.json

DEFAULT_CFG: dict = {
    "ticks_dir": str(TEAM / "state" / "price_ticks"),
    "zones_file": str(TEAM / "state" / "zones_reveil.json"),
    "live_orders": str(TEAM / "state" / "live_orders.jsonl"),
    "live_exits": str(TEAM / "state" / "live_exits.json"),
    "trades_log": str(TEAM / "state" / "trades_log.jsonl"),
    "watch_heartbeat": str(TEAM / "state" / "watch_stops_heartbeat.json"),
    "revolut_heartbeat": str(TEAM / "state" / "revolut_heartbeat.json"),
    "guardian_state": str(TEAM / "guardian" / "state.json"),
    "positions_file": str(TEAM / "state" / "positions.json"),
    "collector_pid": str(TEAM / "state" / "price_ticks" / "collector.pid"),
    # read-only team files for the extra Predict rings / night flag
    "decision_log": str(TEAM / "knowledge" / "decision_log.md"),
    "guardian_config": str(TEAM / "guardian" / "config.json"),
    "team_config": str(TEAM / "config.json"),
    "deadline_reminders": str(TEAM / "state" / "deadline_reminders.jsonl"),
    "deadline_reminder": str(TEAM / "state" / "deadline_reminder.json"),
    "state_dir": str(HERE / "state"),
    "secrets_file": str(HERE / "secrets.env"),
    "loop_seconds": 30,
    "stale_seconds": 180,          # older than this: no price rings at all (flag + log)
    "proxy": "http://127.0.0.1:8791",
    "http_timeout_s": 10,
    "http_retries": 3,             # retries after the first try
    "http_backoff_s": [2, 5, 10],
    "allow_http": False,           # only https webhooks (tests may set true)
    "revx_bin": "/home/box/.local/bin/revx",
    "revx_enabled": True,
    "revx_every_s": 300,           # read-only `revx order open` at most every 5 min
    "live_equity_file": str(TEAM / "state" / "live_equity.json"),
    "equity_every_s": 300,         # refresh capital réel at most every 5 min
    # MetaMask (Arbitrum One) : solde ETH lu en lecture seule (eth_getBalance) pour live_equity.json → total réel
    "metamask_address": "0xb88D4A78e960F04E8c9a5da2B91Bf74c49c271e8",
    "arbitrum_rpc": "https://arb1.arbitrum.io/rpc",
    "predict": {
        "window_start": "15:00",
        "window_end": "17:00",     # end excluded
        "days": [0, 1, 2, 3, 4],   # 0=Monday ... 6=Sunday
        "max_per_day": 3,
        "retry_after_fail_min": 5,
        "max_attempts_per_zone_per_day": 3,
    },
    "risk": {
        "stop_hit_repeat_min": 10,
        "stop_hit_max_per_day": 6,     # per position
        "retry_after_fail_min": 2,
        "max_attempts_per_day": 12,    # per alert key (anti-spam incl. failures)
        "stop_near_pct": 1.0,
        "daily_loss_levels": [0.12, 0.15],
        "drawdown_levels": [0.06, 0.08],
        "stale_ring_after_s": 600,
        "stale_repeat_min": 30,
        "manual_zone_max_per_day": 6,
    },
    "health": {
        "watcher_stale_s": 180,        # watch_stops heartbeat older than 3 min → watcher_down
        "revolut_stale_s": 720,        # revolut heartbeat older than 12 min → revolut_down
        "revolut_min_failures": 2,     # ok=false AND consecutive_failures >= 2 → revolut_down
        # Heartbeat file ABSENT while a position is open (guardian/state.json / live_orders.jsonl):
        "watcher_missing_grace_s": 180,  # watch_stops_heartbeat.json absent > 3 min → watcher_down
        "revolut_missing_grace_s": 720,  # revolut_heartbeat.json absent > 12 min (watcher alive) → revolut_down
        "repeat_min": 30,              # max 1 ring per kind per 30 min
        "retry_after_fail_min": 2,
        # machine pause / resume: a gap > resume_gap_s between two cycles (wall AND monotonic) = resume.
        # Then heartbeat AGE problems only count once the grace is over (the writers need time to run again).
        "resume_gap_s": 120,
        "resume_grace_watcher_s": 90,   # ~3 watcher loops of 30 s
        "resume_grace_revolut_s": 600,  # 2 Revolut tests of 5 min
    },
    # Night window (Brussels) used by idle « max par nuit » and the night_sans_decision flag.
    "nuit": {"debut": "22:00", "fin": "09:00"},
    # Predict « sans décision » ring (counts in predict.max_per_day).
    "idle": {
        "actif": True,
        "heures_sans_decision": 4.0,   # no new D-xxx for this long
        "intervalle_min_h": 4.0,       # max 1 idle ring per 4 h
        "max_par_nuit": 2,             # max 2 idle rings per night (nuit.debut → nuit.fin)
        "marge_min_eur": 5.0,          # « room under the cap » = at least this many € left
        "retry_after_fail_min": 5,
    },
    # Predict « heure limite » ring (once per trade, counts in predict.max_per_day).
    "heure_limite": {"actif": True, "delai_risk_min": 5, "retry_after_fail_min": 5, "max_essais": 3},
    # status.json → zones_distance : flag a pair whose nearest Predict zone (below or above) is > max_pct away.
    "zones_distance": {"max_pct": 1.0},
    # « mouvement » : reference = collector mid at the time of Predict's latest D-xxx; if a pair moves more than
    # seuil_pct from it → ring Predict (all crossed pairs in one ring). No daily cap and NOT in the zone 6/day:
    # only a gap of intervalle_min_min after the later of (last movement ring, latest D-xxx).
    "mouvement": {"actif": True, "seuil_pct": 0.5, "intervalle_min_min": 30,
                  "attente_decision_min": 20, "retry_after_fail_min": 5, "max_essais": 3,
                  "prix_max_age_s": 180, "paires": ["BTC-EUR", "ETH-EUR", "SOL-EUR"]},
    "compound": {
        "max_per_day": 5,              # Europe/Brussels day
        "bilan_note": "reporté au bilan 20h32",
    },
    # « alertes de départ » (breakout / accumulation) — OBSERVATION ONLY, never rings (see departs.py)
    "departs": copy.deepcopy(departs.DEFAULTS),
}

TEST_MESSAGE = "Essai de la sonnette, rien à faire."


# ----------------------------------------------------------------- helpers
def deep_merge(base: dict, over: dict) -> dict:
    out = copy.deepcopy(base)
    for k, v in (over or {}).items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = deep_merge(out[k], v)
        else:
            out[k] = v
    return out


def load_cfg(path: str | None) -> dict:
    p = Path(path) if path else HERE / "config.json"
    if p.exists():
        try:
            return deep_merge(DEFAULT_CFG, json.loads(p.read_text()))
        except Exception as e:  # noqa: BLE001
            print(f"[sonnette] config.json illisible ({e}); valeurs par défaut", file=sys.stderr)
    return copy.deepcopy(DEFAULT_CFG)


def parse_ts(s) -> datetime | None:
    if not isinstance(s, str) or not s.strip():
        return None
    try:
        dt = datetime.fromisoformat(s.strip().replace("Z", "+00:00"))
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=TZ)
    return dt


def to_float(x) -> float | None:
    if isinstance(x, bool) or x is None:
        return None
    if isinstance(x, (int, float)):
        return float(x)
    if isinstance(x, str):
        try:
            return float(x.strip().replace(",", ".").replace(" ", "").replace("€", ""))
        except ValueError:
            return None
    return None


def load_json(path: Path, default=None):
    try:
        return json.loads(Path(path).read_text())
    except Exception:  # noqa: BLE001
        return default


def save_json(path: Path, data) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")
    os.replace(tmp, path)


def fmt_eur(x: float, decimals: int | None = None) -> str:
    """98 -> '98', 97.854 -> '97,85', 73243.1 -> '73 243,10' (French style)."""
    if decimals is None:
        decimals = 0 if abs(x - round(x)) < 1e-9 else 2
    s = f"{x:,.{decimals}f}"
    return s.replace(",", " ").replace(".", ",")


def asset(pair: str) -> str:
    return pair.split("-")[0]


def hhmm(dt: datetime) -> str:
    return dt.astimezone(TZ).strftime("%Hh%M")


def pid_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def collector_status(cfg: dict) -> dict:
    """Watchdog only: report whether the team price collector is running (never start it)."""
    pid = None
    try:
        pid = int(Path(cfg["collector_pid"]).read_text().strip().split()[0])
    except Exception:  # noqa: BLE001
        pid = None
    if pid and pid_alive(pid):
        return {"running": True, "pid": pid, "via": "pidfile"}
    try:
        out = subprocess.run(["pgrep", "-f", "collect_price_ticks.py"], capture_output=True,
                             text=True, timeout=5).stdout.split()
        pids = [int(p) for p in out if p.strip().isdigit() and int(p) != os.getpid()]
        if pids:
            return {"running": True, "pid": pids[0], "via": "pgrep"}
    except Exception:  # noqa: BLE001
        pass
    return {"running": False, "pid": pid, "via": "none"}


# ----------------------------------------------------------------- secrets
def read_secrets_file(path: Path) -> dict:
    out: dict = {}
    try:
        text = Path(path).read_text()
    except OSError:
        return out
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        if line.startswith("export "):
            line = line[7:].strip()
        k, v = line.split("=", 1)
        k, v = k.strip(), v.strip()
        if len(v) >= 2 and v[0] == v[-1] and v[0] in "'\"":
            v = v[1:-1]
        if k.startswith("SONNETTE_"):
            out[k] = v
    return out


class Secrets:
    """Env first, then secrets file. Values are never printed."""

    def __init__(self, cfg: dict, env: dict | None = None):
        self.cfg = cfg
        self.env = dict(os.environ if env is None else env)

    def values(self) -> dict:
        merged = read_secrets_file(Path(self.cfg["secrets_file"]))
        for k, v in self.env.items():
            if k.startswith("SONNETTE_") and v != "":
                merged[k] = v
        return merged

    def all_secret_strings(self) -> list[str]:
        v = self.values()
        return [val for k, val in v.items()
                if any(k.endswith(s) for s in ("_URL", "_KEY", "_AUTH")) and len(val) >= 4]

    def channel(self, bot: str) -> dict:
        """Return {'real': bool, 'reason': str, ...private fields...} for a bot."""
        v = self.values()
        B = bot.upper()

        def g(name: str, default=None):
            return v.get(f"SONNETTE_{B}_{name}") or v.get(f"SONNETTE_{name}") or default

        if str(v.get("SONNETTE_DRY", "")).strip().lower() in ("1", "true", "yes", "oui"):
            return {"real": False, "reason": "SONNETTE_DRY=1 (forcé)"}
        url = v.get(f"SONNETTE_{B}_URL", "").strip()
        auth = v.get(f"SONNETTE_{B}_AUTH", "").strip()
        if auth.lower().startswith("authorization:"):
            auth = auth.split(":", 1)[1].strip()
        key = v.get(f"SONNETTE_{B}_KEY", "").strip()
        mode = str(g("KEY_MODE", "header")).strip().lower()
        if not url:
            return {"real": False, "reason": f"SONNETTE_{B}_URL absent"}
        if not (url.startswith("https://") or (self.cfg.get("allow_http") and url.startswith("http://"))):
            return {"real": False, "reason": f"SONNETTE_{B}_URL doit commencer par https://"}
        if mode not in ("header", "query", "body", "none"):
            return {"real": False, "reason": f"KEY_MODE inconnu ({mode}); header|query|body|none"}
        if mode != "none" and not (auth or key):
            return {"real": False, "reason": f"SONNETTE_{B}_AUTH ou SONNETTE_{B}_KEY absent"}
        # Header name + template. SONNETTE_KEY_HEADER may be "X-Key" or "Authorization: Bearer <key>"
        hspec = str(g("KEY_HEADER", "Authorization")).strip()
        template = None
        if ":" in hspec:
            hname, template = hspec.split(":", 1)
            hname, template = hname.strip(), template.strip()
            if "<key>" not in template:
                template = (template + " <key>").strip() if template else "<key>"
        else:
            hname = hspec or "Authorization"
        if auth:
            value = auth  # full value as copied from the routine panel, sent verbatim
        elif mode in ("query", "body"):
            value = key  # raw key in the URL parameter / JSON field
        else:
            prefix_env = v.get(f"SONNETTE_{B}_KEY_PREFIX") or v.get("SONNETTE_KEY_PREFIX")
            if template is not None:
                value = template.replace("<key>", key)
            elif prefix_env is not None:
                value = ("" if prefix_env.lower() == "none" else prefix_env) + key
            else:
                value = ("Bearer " + key) if hname.lower() == "authorization" else key
        return {
            "real": True,
            "reason": "URL + clé présentes",
            "_url": url,
            "_mode": mode,
            "_hname": hname,
            "_value": value,
            "_param": str(g("KEY_PARAM", "key")),
            "auth_style": ("header " + hname) if mode == "header" else mode,
        }


# ----------------------------------------------------------------- HTTP
def post_json(channel: dict, payload: dict, cfg: dict, redact: list[str], log) -> dict:
    """POST with proxy + retries. Returns {'ok', 'status', 'error', 'tries'}; never leaks URL/key."""
    url = channel["_url"]
    body = dict(payload)
    headers = {"Content-Type": "application/json; charset=utf-8", "User-Agent": "sonnette/1.0"}
    if channel["_mode"] == "header":
        headers[channel["_hname"]] = channel["_value"]
    elif channel["_mode"] == "query":
        sep = "&" if "?" in url else "?"
        url = url + sep + urllib.parse.urlencode({channel["_param"]: channel["_value"]})
    elif channel["_mode"] == "body":
        body[channel["_param"]] = channel["_value"]
    data = json.dumps(body, ensure_ascii=False).encode("utf-8")
    proxy = cfg.get("proxy") or ""
    handler = urllib.request.ProxyHandler({"http": proxy, "https": proxy} if proxy else {})
    opener = urllib.request.build_opener(handler)
    secrets = [s for s in redact + [url, channel["_url"], channel["_value"]] if s]

    def clean(msg: str) -> str:
        for s in sorted(secrets, key=len, reverse=True):
            msg = msg.replace(s, "***")
        return msg[:300]

    retries = int(cfg.get("http_retries", 3))
    backoff = list(cfg.get("http_backoff_s") or [2, 5, 10])
    last = {"ok": False, "status": None, "error": None, "tries": 0}
    for attempt in range(retries + 1):
        last["tries"] = attempt + 1
        try:
            req = urllib.request.Request(url, data=data, headers=headers, method="POST")
            with opener.open(req, timeout=float(cfg.get("http_timeout_s", 10))) as resp:
                code = resp.getcode()
                if 200 <= code < 300:
                    return {"ok": True, "status": code, "error": None, "tries": attempt + 1}
                last.update(status=code, error=f"HTTP {code}")
        except urllib.error.HTTPError as e:
            last.update(status=e.code, error=clean(f"HTTP {e.code} {e.reason}"))
            if 400 <= e.code < 500 and e.code not in (408, 425, 429):
                log("WARN", f"envoi refusé ({last['error']}) — pas de nouvel essai (vérifier la clé)")
                return last
        except Exception as e:  # noqa: BLE001
            last.update(status=None, error=clean(f"{type(e).__name__}: {e}"))
        if attempt < retries:
            wait = backoff[min(attempt, len(backoff) - 1)]
            log("WARN", f"envoi échoué (essai {attempt + 1}/{retries + 1}: {last['error']}); nouvel essai dans {wait}s")
            time.sleep(wait)
    return last


# ----------------------------------------------------------------- ticks
def tail_lines(path: Path, max_bytes: int = 65536) -> list[str]:
    try:
        with open(path, "rb") as f:
            f.seek(0, 2)
            size = f.tell()
            f.seek(max(0, size - max_bytes))
            raw = f.read().decode("utf-8", errors="replace")
    except OSError:
        return []
    lines = raw.splitlines()
    if size > max_bytes and lines:
        lines = lines[1:]  # first line may be partial
    return lines


def latest_ticks(ticks_dir: Path, now: datetime) -> dict:
    """{pair: {'mid': float, 'ts': datetime}} from today's (then yesterday's) file."""
    out: dict = {}
    for d in (now.date(), now.date() - timedelta(days=1)):
        path = Path(ticks_dir) / f"{d.isoformat()}.jsonl"
        for line in tail_lines(path):
            try:
                row = json.loads(line)
            except (json.JSONDecodeError, ValueError):
                continue
            if not isinstance(row, dict):
                continue
            pair = str(row.get("pair") or "").upper()
            mid = to_float(row.get("mid"))
            ts = parse_ts(row.get("ts"))
            if pair not in ALLOWED_PAIRS or mid is None or mid <= 0 or ts is None:
                continue
            if ts > now + timedelta(minutes=2):
                continue  # timestamp from the future: ignore
            prev = out.get(pair)
            if prev is None or ts >= prev["ts"]:
                out[pair] = {"mid": mid, "ts": ts}
        if all(p in out for p in ALLOWED_PAIRS):
            break
    return out


# ----------------------------------------------------------------- zones
SENS_ALIASES = {"sous": "sous", "en-dessous": "sous", "en dessous": "sous",
                "au-dessus": "au-dessus", "au dessus": "au-dessus", "dessus": "au-dessus"}


def load_zones(path: Path, now: datetime) -> tuple[list[dict], list[str], str | None]:
    """Return (valid_zones, problems, file_error). Never raises."""
    p = Path(path)
    if not p.exists():
        return [], [], None
    try:
        data = json.loads(p.read_text(encoding="utf-8") or "{}")
    except Exception as e:  # noqa: BLE001
        return [], [], f"fichier zones illisible (JSON cassé): {e}"
    rows = data.get("zones") if isinstance(data, dict) else data if isinstance(data, list) else None
    if not isinstance(rows, list):
        return [], [], "fichier zones: il faut {\"zones\": [ ... ]}"
    valid, problems, seen = [], [], set()
    for i, z in enumerate(rows):
        label = f"zone n°{i + 1}"
        if not isinstance(z, dict):
            problems.append(f"{label}: ce n'est pas un objet {{...}}")
            continue
        zid = str(z.get("id") or "").strip()
        label = f"zone {zid or 'n°' + str(i + 1)}"
        errs = []
        if not zid:
            errs.append("id manquant")
        elif zid in seen:
            errs.append("id en double")
        pair = str(z.get("paire") or z.get("pair") or "").strip().upper()
        if pair not in ALLOWED_PAIRS:
            errs.append(f"paire '{pair}' non autorisée (BTC-EUR, ETH-EUR, SOL-EUR)")
        sens = SENS_ALIASES.get(str(z.get("sens") or "").strip().lower())
        if not sens:
            errs.append("sens doit être 'sous' ou 'au-dessus'")
        prix = to_float(z.get("prix"))
        if prix is None or prix <= 0:
            errs.append("prix doit être un nombre > 0")
        bot = str(z.get("bot") or "").strip().lower()
        if bot not in ZONE_BOTS:
            errs.append("bot doit être 'predict' ou 'risk'")
        exp_raw = z.get("expire")
        exp = None
        if exp_raw not in (None, ""):
            exp = parse_ts(str(exp_raw))
            if exp is None:
                errs.append("expire illisible (ex: 2026-10-09T17:00:00+02:00)")
        actif = z.get("actif", True)
        if not isinstance(actif, bool):
            errs.append("actif doit être true ou false")
        if errs:
            problems.append(f"{label}: " + "; ".join(errs))
            if zid:
                seen.add(zid)
            continue
        seen.add(zid)
        if actif is False:
            continue
        if exp is not None and now >= exp:
            problems.append(f"{label}: expirée ({exp_raw}) — ignorée")
            continue
        valid.append({"id": zid, "paire": pair, "sens": sens, "prix": prix, "bot": bot,
                      "raison": str(z.get("raison") or "")[:300], "expire": exp_raw})
    return valid, problems, None


# ----------------------------------------------------------------- real positions
def derive_stop(pos: dict) -> float | None:
    """Same as watch_stops.derive_stop: stop_price_eur, else entry * (1 - |stop_pct|/100)."""
    s = to_float(pos.get("stop_price_eur"))
    if s is None:
        for k in ("stop_price", "stop", "trigger_price", "triggerPrice", "stopPrice"):
            s = to_float(pos.get(k))
            if s is not None:
                break
    if s is not None and s > 0:
        return s
    sp = to_float(pos.get("stop_pct"))
    avg = to_float(pos.get("avg_price") or pos.get("entry_price") or pos.get("price"))
    if sp is None or avg is None or avg <= 0:
        return None
    if sp > 0:
        sp = -sp
    return avg * (1.0 + sp / 100.0)


def is_explicit_live(pos: dict) -> bool:
    """Same tagging as watch_stops.classify_mode, but default = NOT live (sim never rings)."""
    for key in ("mode", "execution_mode"):
        m = str(pos.get(key) or "").strip().lower()
        if m in ("live", "real", "reel", "réel"):
            return True
        if m in ("paper", "sim", "simulation"):
            return False
    src = str(pos.get("source") or "").lower()
    if "live" in src and "paper" not in src:
        return True
    pid = str(pos.get("id") or "").lower()
    if "paper" in pid:
        return False
    return pid.startswith("rx-live") or pid.startswith("live-") or "-live-" in pid


def norm_pair(raw) -> str:
    return str(raw or "").strip().upper().replace("/", "-")


def live_from_orders_log(path: Path, exits_path: Path | None = None) -> list[dict]:
    """Same idea as watch_stops.load_live_orders_open: longs + idée à la baisse shorts.

    Longs = buys − plain sells (EUR). kind=auto_exit closes via exit lock / linked id.
    Idée à la baisse = sell with idea_type/kind=baisse (no cycle_id) → short; closed by
    a linked rebuy (cycle_id / linked_position_id) or auto_exit. Never « vendre d'abord ».
    """
    try:
        lines = Path(path).read_text().splitlines()
    except OSError:
        return []
    closed_by_exit: set[str] = set()
    if exits_path:
        ex = load_json(Path(exits_path), {}) or {}
        if isinstance(ex, dict):
            for k, v in ex.items():
                if isinstance(v, dict) and str(v.get("status") or "") in (
                        "done", "no_fill", "closed_by_target", "partial"):
                    closed_by_exit.add(str(k))
    buys: dict[str, dict] = {}
    sells: dict[str, float] = {}
    shorts: dict[str, dict] = {}
    closed_shorts: set[str] = set()
    for line in lines:
        try:
            row = json.loads(line)
        except (json.JSONDecodeError, ValueError):
            continue
        if not isinstance(row, dict) or not row.get("ok") or row.get("dry_run"):
            continue
        if row.get("kind") == "auto_exit":
            order = row.get("order") if isinstance(row.get("order"), dict) else row
            linked = str(order.get("exit_for") or order.get("linked_position_id")
                         or order.get("cycle_id") or "")
            if linked:
                closed_by_exit.add(linked)
                closed_shorts.add(linked)
            continue
        order = row.get("order") if isinstance(row.get("order"), dict) else row
        pair = norm_pair(order.get("pair"))
        side = str(order.get("side") or "").lower()
        amount = to_float(order.get("amount_eur")) or 0.0
        idea = str(order.get("idea_type") or order.get("kind") or "").lower()
        linked = order.get("linked_position_id") or order.get("cycle_id")
        if not pair:
            continue
        if side == "sell" and idea == "baisse" and not linked:
            oid = str(order.get("id") or row.get("client_order_id") or "")
            if not oid:
                oid = f"rx-live-{pair}-{row.get('at') or 'unknown'}"
            elif not (oid.startswith("rx-live") or oid.startswith("live-")):
                oid = f"rx-live-{oid}"
            stop_v = order.get("stop_price_eur")
            if stop_v is None:
                stop_v = order.get("stop_price") if order.get("stop_price") is not None else order.get("safety_price")
            shorts[oid] = {
                "id": oid, "pair": pair, "side": "short", "idea_type": "baisse", "kind": "baisse",
                "price": order.get("price"), "avg_price": order.get("price"), "cost_eur": amount,
                "stop_price_eur": stop_v, "target_price": order.get("target_price"),
                "decision_id": order.get("decision_id") or row.get("decision_id"),
                "source": "live_orders", "opened_at": row.get("at"), "mode": "live",
            }
            continue
        if side == "buy" and linked and (idea == "baisse" or order.get("rebuy_reason")):
            closed_shorts.add(str(linked))
            continue
        if side == "buy" and amount > 0:
            oid = str(order.get("id") or row.get("client_order_id") or "")
            if not oid:
                oid = f"rx-live-{pair}-{row.get('at') or 'unknown'}"
            elif not (oid.startswith("rx-live") or oid.startswith("live-")):
                oid = f"rx-live-{oid}"
            buys[oid] = {"id": oid, "pair": pair, "side": "long", "idea_type": idea or "hausse",
                         "price": order.get("price"), "avg_price": order.get("price"), "cost_eur": amount,
                         "stop_pct": order.get("stop_pct"),
                         "stop_price_eur": (order.get("stop_price_eur") if order.get("stop_price_eur") is not None
                                            else order.get("stop_price") if order.get("stop_price") is not None
                                            else order.get("safety_price")),
                         "decision_id": order.get("decision_id") or row.get("decision_id"),
                         "source": "live_orders", "opened_at": row.get("at"), "mode": "live"}
        elif side == "sell" and amount > 0:
            if order.get("target_for") or str(order.get("purpose") or "").lower() in ("target", "objectif"):
                continue
            sells[pair] = sells.get(pair, 0.0) + amount
    out = []
    for oid, b in buys.items():
        if oid in closed_by_exit:
            continue
        left = sells.get(b["pair"], 0.0)
        if left >= b["cost_eur"] - 1e-9:
            sells[b["pair"]] = left - b["cost_eur"]
            continue
        if left > 0:
            b = dict(b, cost_eur=round(b["cost_eur"] - left, 6))
            sells[b["pair"]] = 0.0
        out.append(b)
    for sid, sh in shorts.items():
        if sid not in closed_shorts and sid not in closed_by_exit:
            out.append(sh)
    return out


def live_from_state_file(path: Path, source: str) -> list[dict]:
    data = load_json(Path(path), {}) or {}
    out = []
    for p in (data.get("positions") or []) if isinstance(data, dict) else []:
        if not isinstance(p, dict):
            continue
        if str(p.get("status") or "open").lower() != "open":
            continue
        if not is_explicit_live(p):
            continue
        pair = norm_pair(p.get("pair") or p.get("symbol"))
        if pair not in ALLOWED_PAIRS:
            continue
        side = str(p.get("side") or "long").lower()
        out.append(dict(p, pair=pair, side="long" if side in ("long", "buy") else side, source=source))
    return out


def live_from_revx(cfg: dict, log) -> list[dict] | None:
    """READ-ONLY `revx order open` (never place/cancel/replace). None = could not read."""
    binp = cfg.get("revx_bin") or "revx"
    if not Path(binp).exists() and not shutil.which(binp):
        return None
    proxy = cfg.get("proxy") or "http://127.0.0.1:8791"
    env = dict(os.environ, HTTPS_PROXY=proxy, HTTP_PROXY=proxy, ALL_PROXY=proxy,
               PATH="/home/box/.local/bin:" + os.environ.get("PATH", ""))
    cmd = [binp, "order", "open", "--symbols", ",".join(ALLOWED_PAIRS), "--json", "--limit", "50"]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=30, env=env)
    except Exception as e:  # noqa: BLE001
        log("WARN", f"revx order open (lecture) impossible: {type(e).__name__}")
        return None
    if proc.returncode != 0:
        log("WARN", f"revx order open (lecture) code {proc.returncode}")
        return None
    raw = (proc.stdout or "").strip()
    try:
        starts = [i for i in (raw.find("{"), raw.find("[")) if i >= 0]
        data = json.loads(raw[min(starts):]) if raw and starts else []
    except (json.JSONDecodeError, ValueError):
        log("WARN", "revx order open: réponse illisible")
        return None
    if isinstance(data, dict):
        data = next((data[k] for k in ("data", "orders", "results", "items") if isinstance(data.get(k), list)),
                    [data] if data else [])
    out = []
    for o in data if isinstance(data, list) else []:
        if not isinstance(o, dict):
            continue
        pair = norm_pair(o.get("symbol") or o.get("pair") or o.get("trading_pair"))
        if pair not in ALLOWED_PAIRS:
            continue
        status = str(o.get("status") or o.get("state") or o.get("order_state") or "").lower()
        if status in ("cancelled", "canceled", "rejected", "expired", "filled", "closed"):
            continue
        oid = str(o.get("id") or o.get("order_id") or o.get("client_order_id") or f"revx-{pair}")
        # resting order: entry price is NOT a stop; only explicit stop/trigger fields count
        row = {"id": f"revx-{oid}", "pair": pair, "side": "long", "source": "revx_open",
               "order_side": str(o.get("side") or "").lower(), "order_type": o.get("type") or o.get("order_type")}
        for k in ("stop_price", "trigger_price", "triggerPrice", "stopPrice", "stop_price_eur"):
            if o.get(k) is not None:
                row["stop_price_eur"] = o.get(k)
                break
        out.append(row)
    return out



# ----------------------------------------------------------------- compound (trade fermé)
def _close_raison_fr(raw) -> str:
    s = str(raw or "").strip().lower()
    if s in ("manual", "manuel", "manual_close", "closed_manual"):
        return "manuel"
    if any(x in s for x in ("target", "cible", "closed_by_target")):
        return "cible"
    if any(x in s for x in ("stop", "arrêt", "arret", "safety")):
        return "arrêt"
    if s in ("cible", "arrêt", "arret", "manuel"):
        return "cible" if s == "cible" else ("manuel" if s == "manuel" else "arrêt")
    return "manuel" if not s else ("arrêt" if "stop" in s else s)


def _trade_side_fr(pos_or_row: dict) -> str:
    """Achat = idée à la hausse; Vente = idée à la baisse. Never « vendre d\'abord »."""
    idea = str(pos_or_row.get("idea_type") or pos_or_row.get("kind") or "").lower()
    side = str(pos_or_row.get("side") or "").lower()
    if idea == "baisse" or side in ("short", "sell"):
        return "Vente"
    if idea == "hausse" or side in ("long", "buy"):
        return "Achat"
    # closing auto_exit: idea_type on the exit row reflects the original idea
    return "Vente" if idea == "baisse" else "Achat"


def _trade_mode_fr(pos_or_row: dict) -> str:
    m = str(pos_or_row.get("mode") or pos_or_row.get("execution_mode") or "").strip().lower()
    if m in ("live", "real", "reel", "réel"):
        return "live"
    if m in ("paper", "sim", "simulation"):
        return "simulation"
    src = str(pos_or_row.get("source") or "").lower()
    pid = str(pos_or_row.get("id") or pos_or_row.get("position_id") or "").lower()
    if "live" in src or pid.startswith("rx-live") or pid.startswith("live-") or "-live-" in pid:
        return "live"
    return "simulation"


def discover_closed_trades(cfg: dict) -> list[dict]:
    """Closed trades from team files (read-only). One entry per trade, stable `key`.

    Sources: guardian/state.json (status=closed), trades_log.jsonl (close_reason),
    live_orders.jsonl (kind=auto_exit). Prefer decision_id as key when present.
    """
    found: dict[str, dict] = {}

    def add(key: str, row: dict) -> None:
        key = str(key or "").strip()
        if not key:
            return
        # Prefer richer rows (decision_id, pnl) over sparse ones
        prev = found.get(key)
        if prev is None:
            found[key] = row
            return
        score = (1 if row.get("decision_id") else 0) + (1 if row.get("gain_perte_eur") is not None else 0)
        pscore = (1 if prev.get("decision_id") else 0) + (1 if prev.get("gain_perte_eur") is not None else 0)
        if score >= pscore:
            found[key] = row

    # 1) guardian closed positions
    gs = load_json(Path(cfg["guardian_state"]), {}) or {}
    for pos in (gs.get("positions") or []) if isinstance(gs, dict) else []:
        if not isinstance(pos, dict):
            continue
        if str(pos.get("status") or "").lower() != "closed":
            continue
        did = str(pos.get("decision_id") or "").strip()
        pid = str(pos.get("id") or "").strip()
        key = did or pid
        add(key, {
            "key": key,
            "decision_id": did or None,
            "position_id": pid or None,
            "paire": norm_pair(pos.get("pair") or pos.get("symbol")),
            "sens": _trade_side_fr(pos),
            "mode": _trade_mode_fr(pos),
            "gain_perte_eur": to_float(pos.get("realized_pnl_eur")),
            "raison_fermeture": _close_raison_fr(pos.get("close_reason")),
            "closed_at": pos.get("closed_at") or pos.get("updated_at"),
            "source": "guardian_state",
        })

    # 2) trades_log closing legs
    try:
        lines = Path(cfg["trades_log"]).read_text().splitlines()
    except OSError:
        lines = []
    for line in lines:
        try:
            row = json.loads(line)
        except (json.JSONDecodeError, ValueError):
            continue
        if not isinstance(row, dict) or not row.get("close_reason"):
            continue
        did = str(row.get("decision_id") or "").strip()
        linked = str(row.get("linked_position_id") or row.get("cycle_id") or "").strip()
        rid = str(row.get("id") or "").strip()
        key = did or linked or rid
        idea = {"idea_type": row.get("idea_type") or row.get("kind"),
                "side": "short" if str(row.get("idea_type") or "").lower() == "baisse"
                else ("long" if str(row.get("side") or "").lower() == "buy"
                      and str(row.get("idea_type") or "").lower() != "baisse"
                      else row.get("side")),
                "mode": row.get("mode"), "source": row.get("source"), "id": linked or rid}
        # For baisse close the closing leg is a buy; idea_type still baisse → Vente
        if str(row.get("idea_type") or "").lower() == "baisse":
            idea["side"] = "short"
        add(key, {
            "key": key,
            "decision_id": did or None,
            "position_id": linked or rid or None,
            "paire": norm_pair(row.get("pair")),
            "sens": _trade_side_fr(idea),
            "mode": _trade_mode_fr(row if row.get("mode") else idea),
            "gain_perte_eur": to_float(row.get("realized_pnl_eur")),
            "raison_fermeture": _close_raison_fr(row.get("close_reason") or row.get("rebuy_reason")),
            "closed_at": row.get("ts_local") or row.get("ts") or row.get("at"),
            "source": "trades_log",
        })

    # 3) live auto exits
    try:
        lines = Path(cfg["live_orders"]).read_text().splitlines()
    except OSError:
        lines = []
    for line in lines:
        try:
            row = json.loads(line)
        except (json.JSONDecodeError, ValueError):
            continue
        if not isinstance(row, dict) or row.get("kind") != "auto_exit":
            continue
        if not row.get("ok") and str(row.get("status") or "") not in ("done", "closed_by_target", "partial"):
            # still record successful-ish closes; skip pure failures with no fill
            if str(row.get("status") or "") in ("failed", "error", "no_fill"):
                continue
        order = row.get("order") if isinstance(row.get("order"), dict) else row
        pid = str(order.get("exit_for") or order.get("linked_position_id") or order.get("cycle_id") or "").strip()
        did = str(order.get("decision_id") or row.get("decision_id") or "").strip()
        key = did or pid
        if not key:
            continue
        idea = {"idea_type": order.get("idea_type"), "side": "short" if str(order.get("idea_type") or "").lower() == "baisse" else "long",
                "mode": "live", "id": pid, "source": "live_orders"}
        add(key, {
            "key": key,
            "decision_id": did or None,
            "position_id": pid or None,
            "paire": norm_pair(order.get("pair")),
            "sens": _trade_side_fr(idea),
            "mode": "live",
            "gain_perte_eur": to_float(order.get("realized_pnl_eur")),
            "raison_fermeture": _close_raison_fr(order.get("close_reason")),
            "closed_at": row.get("at"),
            "source": "live_orders_auto_exit",
        })

    return list(found.values())



# ----------------------------------------------------------------- health (watcher / Revolut)
def open_positions_any(cfg: dict) -> list[dict]:
    """Open positions (sim AND live) from the sonnette's own sources: guardian/state.json + live_orders."""
    out: dict[str, dict] = {}
    gs = load_json(Path(cfg["guardian_state"]), {}) or {}
    for p in (gs.get("positions") or []) if isinstance(gs, dict) else []:
        if not isinstance(p, dict) or str(p.get("status") or "open").lower() != "open":
            continue
        pid = str(p.get("id") or "")
        if not pid:
            continue
        idea = str(p.get("idea_type") or p.get("kind") or "").lower()
        out[pid] = {"id": pid, "pair": norm_pair(p.get("pair") or p.get("symbol")),
                    "mode": _trade_mode_fr(p), "decision_id": p.get("decision_id"),
                    "cycle_id": p.get("cycle_id") or (pid if idea == "baisse" else None)}
    lx = Path(cfg["live_exits"]) if cfg.get("live_exits") else None
    for p in live_from_orders_log(Path(cfg["live_orders"]), lx):
        pid = str(p.get("id") or "")
        out.setdefault(pid, {"id": pid, "pair": p.get("pair"), "mode": "live",
                             "decision_id": p.get("decision_id"),
                             "cycle_id": pid if p.get("idea_type") == "baisse" else None})
    return list(out.values())


def read_heartbeat(path: Path, now: datetime) -> dict:
    """{'exists', 'error', 'data', 'age_s'} — age_s None if ts missing/unreadable."""
    p = Path(path)
    if not p.exists():
        return {"exists": False, "error": None, "data": None, "age_s": None}
    try:
        data = json.loads(p.read_text() or "{}")
        if not isinstance(data, dict):
            raise ValueError("pas un objet JSON")
    except Exception as e:  # noqa: BLE001
        return {"exists": True, "error": f"illisible: {type(e).__name__}", "data": None, "age_s": None}
    ts = parse_ts(data.get("ts"))
    age = None if ts is None else max(0.0, (now - ts).total_seconds())
    return {"exists": True, "error": None, "data": data, "age_s": age}


def _int0(x) -> int:
    try:
        return int(float(x))
    except (TypeError, ValueError):
        return 0


def trades_ouverts_fr(n_live: int, n_paper: int) -> str:
    parts = []
    if n_live:
        parts.append(f"{n_live} trade{'s' if n_live > 1 else ''} live")
    if n_paper:
        parts.append(f"{n_paper} trade{'s' if n_paper > 1 else ''} simulé{'s' if n_paper > 1 else ''}")
    total = n_live + n_paper
    if not parts:
        return "une position ouverte"
    return " et ".join(parts) + (" ouverts" if total > 1 else " ouvert")


def fmt_age_fr(age_s) -> str:
    if age_s is None:
        return "?"
    m = int(age_s // 60)
    return f"{m} min" if m >= 1 else f"{int(age_s)} s"


# ----------------------------------------------------------------- core
# ----------------------------------------------------------------- decisions / night / cap / zones distance
DECISION_RE = re.compile(r"^#{2,4}\s+(\d{4}-\d{2}-\d{2})[ T](\d{1,2})[:h](\d{2})\b.*?\|\s*(D-\d{2,})\b")


def read_decisions(path: Path) -> tuple[list[dict], str | None]:
    """D-xxx headers of knowledge/decision_log.md (« ### AAAA-MM-JJ HH:MM | PAIRE | D-xxx … »), read-only.
    Lines like « Test du passé (D-013, …) » (no « | D-xxx » after a pipe) are not decisions."""
    try:
        text = Path(path).read_text(encoding="utf-8", errors="replace")
    except OSError as e:
        return [], f"carnet des décisions illisible ({type(e).__name__})"
    out = []
    for line in text.splitlines():
        m = DECISION_RE.match(line.strip())
        if not m:
            continue
        try:
            ts = datetime.fromisoformat(f"{m.group(1)}T{int(m.group(2)):02d}:{m.group(3)}:00").replace(tzinfo=TZ)
        except ValueError:
            continue
        out.append({"id": m.group(4), "ts": ts})
    return out, None


def mids_at(ticks_dir: Path, when: datetime, pairs, before_s: float = 900, after_s: float = 900) -> dict:
    """Collector mid per pair at `when` (a D-xxx header time, minute precision): last tick up to the end of
    that minute and at most `before_s` earlier; else the first tick after, within `after_s`. {pair: {mid, ts}}."""
    end = when + timedelta(seconds=59)
    lo, hi = when - timedelta(seconds=before_s), end + timedelta(seconds=after_s)
    best_b: dict = {}
    best_a: dict = {}
    days = sorted({lo.date(), when.date(), hi.date()})
    for d in days:
        try:
            text = (Path(ticks_dir) / f"{d.isoformat()}.jsonl").read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for line in text.splitlines():
            try:
                row = json.loads(line)
            except (json.JSONDecodeError, ValueError):
                continue
            if not isinstance(row, dict):
                continue
            pair = str(row.get("pair") or "").upper()
            if pair not in pairs:
                continue
            mid, ts = to_float(row.get("mid")), parse_ts(row.get("ts"))
            if mid is None or mid <= 0 or ts is None or ts < lo or ts > hi:
                continue
            if ts <= end:
                if pair not in best_b or ts >= best_b[pair]["ts"]:
                    best_b[pair] = {"mid": mid, "ts": ts}
            elif pair not in best_a or ts < best_a[pair]["ts"]:
                best_a[pair] = {"mid": mid, "ts": ts}
    return {p: best_b.get(p) or best_a.get(p) for p in pairs if (best_b.get(p) or best_a.get(p))}


def fmt_pct_signed(x: float, decimals: int = 1) -> str:
    v = round(x, decimals)
    return ("+" if v >= 0 else "-") + f"{abs(v):.{decimals}f}".replace(".", ",") + " %"


def _hm(v, default: tuple[int, int]) -> tuple[int, int]:
    try:
        h, m = [int(x) for x in str(v).split(":")]
        return h, m
    except Exception:  # noqa: BLE001
        return default


def night_window(cfg: dict) -> tuple[tuple[int, int], tuple[int, int]]:
    n = cfg.get("nuit") or {}
    return _hm(n.get("debut"), (22, 0)), _hm(n.get("fin"), (9, 0))


def in_night(now: datetime, cfg: dict) -> str | None:
    """Night key (date the night started, AAAA-MM-JJ) if `now` is inside the night window, else None."""
    (dh, dm), (fh, fm) = night_window(cfg)
    cur, d0, f0 = now.hour * 60 + now.minute, dh * 60 + dm, fh * 60 + fm
    if d0 > f0:  # crosses midnight (22:00 → 09:00)
        if cur >= d0:
            return now.date().isoformat()
        if cur < f0:
            return (now.date() - timedelta(days=1)).isoformat()
        return None
    return now.date().isoformat() if d0 <= cur < f0 else None


def last_night(now: datetime, cfg: dict) -> tuple[datetime, datetime]:
    """Most recent COMPLETE night [start, end) — before 09:00 the current night is not over yet."""
    (dh, dm), (fh, fm) = night_window(cfg)
    end = now.replace(hour=fh, minute=fm, second=0, microsecond=0)
    if now < end:
        end -= timedelta(days=1)
    start = end.replace(hour=dh, minute=dm)
    if start >= end:
        start -= timedelta(days=1)
    return start, end


def sim_cap_room(cfg: dict) -> dict:
    """Room under the simulation cap, read as written: guardian/state.json exposure_eur (+ bankroll_eur) and
    guardian/config.json paper_max_exposure_pct. Bankroll fallback: team config.json bankroll_eur."""
    gs = load_json(Path(cfg["guardian_state"]), None)
    gc = load_json(Path(cfg["guardian_config"]), None)
    if not isinstance(gs, dict):
        return {"ok": False, "raison": "guardian/state.json illisible"}
    if not isinstance(gc, dict):
        return {"ok": False, "raison": "guardian/config.json illisible"}
    exp = to_float(gs.get("exposure_eur"))
    pct = to_float(gc.get("paper_max_exposure_pct"))
    bank = to_float(gs.get("bankroll_eur"))
    src_bank = "guardian/state.json bankroll_eur"
    if bank is None:
        tc = load_json(Path(cfg.get("team_config") or ""), None) if cfg.get("team_config") else None
        bank = to_float((tc or {}).get("bankroll_eur")) if isinstance(tc, dict) else None
        src_bank = "config.json bankroll_eur"
    if exp is None or pct is None or bank is None:
        manque = [n for n, v in (("exposure_eur", exp), ("paper_max_exposure_pct", pct), ("bankroll_eur", bank)) if v is None]
        return {"ok": False, "raison": "non écrit : " + ", ".join(manque)}
    cap = pct * bank
    return {"ok": True, "expose_eur": round(exp, 2), "plafond_eur": round(cap, 2), "place_eur": round(cap - exp, 2),
            "paper_max_exposure_pct": pct, "bankroll_eur": bank, "source_bankroll": src_bank}


def zones_distance(zones: list[dict], prices: dict, max_pct: float) -> dict:
    """Nearest Predict zone below and above each priced pair; ok=False if one side is missing or > max_pct away."""
    out: dict = {"max_pct": max_pct, "paires": {}, "ok": None, "a_signaler": []}
    for pair in ALLOWED_PAIRS:
        px = prices.get(pair)
        if px is None:
            continue
        zs = [z for z in zones if z["bot"] == "predict" and z["paire"] == pair]
        below = max((z for z in zs if z["prix"] <= px), key=lambda z: z["prix"], default=None)
        above = min((z for z in zs if z["prix"] >= px), key=lambda z: z["prix"], default=None)

        def side(z):
            if z is None:
                return None
            return {"id": z["id"], "prix": z["prix"], "ecart_pct": round(abs(px - z["prix"]) / px * 100, 3)}
        b, a = side(below), side(above)
        pb = []
        if b is None:
            pb.append("aucune zone en dessous")
        elif b["ecart_pct"] > max_pct:
            pb.append(f"zone du dessous à {b['ecart_pct']:.2f} %".replace(".", ","))
        if a is None:
            pb.append("aucune zone au-dessus")
        elif a["ecart_pct"] > max_pct:
            pb.append(f"zone du dessus à {a['ecart_pct']:.2f} %".replace(".", ","))
        out["paires"][pair] = {"prix": px, "dessous": b, "dessus": a, "ok": not pb, "probleme": " · ".join(pb) or None}
        if pb:
            out["a_signaler"].append(pair)
    if out["paires"]:
        out["ok"] = not out["a_signaler"]
    return out


class Sonnette:
    def __init__(self, cfg: dict, env: dict | None = None, sender=None, quiet: bool = False):
        self.cfg = cfg
        self.sd = Path(cfg["state_dir"])
        self.sd.mkdir(parents=True, exist_ok=True)
        self.secrets = Secrets(cfg, env)
        self.sender = sender  # tests may inject; default = real post_json
        self.quiet = quiet
        self._log_last: dict = {}
        self._revx_cache: list[dict] = []
        self._revx_at: float = -1e18
        self._revx_ok: bool | None = None
        self._last_modes: dict = {}
        self.f_state = self.sd / "state.json"
        self.f_status = self.sd / "status.json"
        self.f_rings = self.sd / "rings.jsonl"
        self.f_log = self.sd / "sonnette.log"
        self.f_stale = self.sd / "PRIX_PERIMES.flag"
        self.f_urgent = self.sd / "ALERTE_RISK_URGENTE.json"
        self.f_urgent_log = self.sd / "alertes_urgentes.jsonl"
        self.f_compound = self.sd / "compound_rung.json"  # persistent dedupe (survives day rollover)
        self.f_health = self.sd / "sante.json"  # watcher_down / revolut_down anti-repeat (persistent)
        self._hb_missing_logged: set[str] = set()
        self.f_extra = self.sd / "predict_extra.json"  # idle / heure limite / nuit annoncée (persistent)
        self._dec_cache: tuple | None = None  # (mtime, size, decisions, error)
        self._last_cycle: tuple | None = None  # (wall datetime, monotonic) of the previous cycle
        self._resume_at: datetime | None = None
        self._resume_gap_s: float | None = None
        self.equity = live_equity.LiveEquity(
            out_path=Path(cfg["live_equity_file"]),
            live_orders_path=Path(cfg["live_orders"]),
            revx_bin=cfg.get("revx_bin") or "/home/box/.local/bin/revx",
            proxy=cfg.get("proxy") or "http://127.0.0.1:8791",
            every_s=float(cfg.get("equity_every_s", 300)),
            fetch_balances=cfg.get("_fetch_balances"),  # tests only
            log=lambda lvl, msg: self.log(lvl, msg),
            metamask_address=cfg.get("metamask_address"),
            arbitrum_rpc=cfg.get("arbitrum_rpc") or "https://arb1.arbitrum.io/rpc",
            fetch_metamask=cfg.get("_fetch_metamask"),  # tests only
        )
        # alertes de départ: observation only (state/departs.jsonl), never rings anybody
        self.departs = departs.Departs(cfg, self.sd, log=lambda lvl, msg, now=None: self.log(lvl, msg, now),
                                       ticks_dir=Path(cfg["ticks_dir"]))

    # ---- logging (secrets redacted, rate-limited helper)
    def log(self, level: str, msg: str, now: datetime | None = None) -> None:
        for s in sorted(self.secrets.all_secret_strings(), key=len, reverse=True):
            msg = msg.replace(s, "***")
        ts = (now or datetime.now(TZ)).astimezone(TZ).strftime("%Y-%m-%d %H:%M:%S")
        line = f"{ts} [{level}] {msg}"
        try:
            if self.f_log.exists() and self.f_log.stat().st_size > 5_000_000:
                os.replace(self.f_log, self.f_log.with_suffix(".log.1"))
            with self.f_log.open("a", encoding="utf-8") as f:
                f.write(line + "\n")
        except OSError:
            pass
        if not self.quiet:
            print(line, flush=True)

    def log_every(self, key: str, every_s: float, level: str, msg: str, now: datetime) -> None:
        last = self._log_last.get(key)
        if last is None or (now - last).total_seconds() >= every_s or (now - last).total_seconds() < 0:
            self._log_last[key] = now
            self.log(level, msg, now)

    # ---- state
    def load_state(self, today: str) -> dict:
        st = load_json(self.f_state, {}) or {}
        if st.get("date") != today:
            st = {"date": today, "dry": {}, "real": {}}
        st.setdefault("dry", {})
        st.setdefault("real", {})
        return st

    @staticmethod
    def bucket(st: dict, delivery: str, bot: str) -> dict:
        b = st[delivery].setdefault(bot, {"delivered": 0, "keys": {}})
        b.setdefault("delivered", 0)
        b.setdefault("keys", {})
        return b

    @staticmethod
    def key_state(st: dict, delivery: str, bot: str, key: str) -> dict:
        b = st[delivery].get(bot) or {}
        return (b.get("keys") or {}).get(key) or {"delivered": 0, "attempts": 0, "last_try": None,
                                                    "last_ok": None, "last_result": None}

    @staticmethod
    def minutes_since(iso: str | None, now: datetime) -> float:
        t = parse_ts(iso) if iso else None
        return 1e9 if t is None else (now - t).total_seconds() / 60.0

    def can_retry(self, ks: dict, now: datetime, min_after_ok: float, min_after_fail: float,
                  max_attempts: int) -> bool:
        if ks["attempts"] >= max_attempts:
            return False
        if ks.get("last_result") == "failed":
            return self.minutes_since(ks.get("last_try"), now) >= min_after_fail
        return self.minutes_since(ks.get("last_ok"), now) >= min_after_ok

    # ---- real positions (revx cached, read-only, max every 5 min)
    def real_positions(self, now_mono: float) -> tuple[list[dict], dict]:
        cfg = self.cfg
        pos = []
        pos += live_from_state_file(Path(cfg["guardian_state"]), "guardian_state")
        pos += live_from_state_file(Path(cfg["positions_file"]), "root_positions")
        pos += live_from_orders_log(Path(cfg["live_orders"]),
                                    Path(cfg["live_exits"]) if cfg.get("live_exits") else None)
        info = {"revx": "désactivé"}
        if cfg.get("revx_enabled"):
            if now_mono - self._revx_at >= float(cfg.get("revx_every_s", 300)):
                self._revx_at = now_mono
                res = live_from_revx(cfg, lambda lvl, m: self.log(lvl, m))
                self._revx_ok = res is not None
                if res is not None:
                    self._revx_cache = res
            pos += self._revx_cache
            info = {"revx": "ok" if self._revx_ok else "lecture impossible (ignoré)",
                    "revx_open_orders": len(self._revx_cache)}
        merged: dict = {}
        for p in pos:
            merged.setdefault(str(p.get("id")), p)
        return list(merged.values()), info


    # ---- compound (trade fermé) dedupe — persistent across days/restarts
    def load_compound_state(self, today: str, closed: list[dict]) -> dict:
        st = load_json(self.f_compound, None)
        if not isinstance(st, dict):
            st = {"seeded": False, "rung": {}, "day": today, "day_count": 0}
        st.setdefault("rung", {})
        if not isinstance(st["rung"], dict):
            st["rung"] = {}
        if st.get("day") != today:
            st["day"] = today
            st["day_count"] = 0
        if not st.get("seeded"):
            # First start: mark every already-closed trade as rung so nothing old rings.
            now_iso = datetime.now(TZ).isoformat()
            for t in closed:
                k = str(t.get("key") or "")
                if k and k not in st["rung"]:
                    st["rung"][k] = {"at": now_iso, "result": "seed",
                                     "decision_id": t.get("decision_id")}
            st["seeded"] = True
            save_json(self.f_compound, st)
            self.log("INFO",
                     f"compound: amorçage — {len(st['rung'])} trade(s) déjà fermé(s) marqués "
                     f"(pas de sonnerie rétroactive)", datetime.now(TZ))
        return st

    def save_compound_state(self, st: dict) -> None:
        save_json(self.f_compound, st)

    def compound_payload(self, trade: dict, now: datetime, test: bool = False) -> dict:
        did = trade.get("decision_id") or trade.get("key")
        paire = trade.get("paire")
        sens = trade.get("sens") or "Achat"
        mode = trade.get("mode") or "simulation"
        pnl = trade.get("gain_perte_eur")
        raison = trade.get("raison_fermeture") or "manuel"
        if test:
            msg = "Essai de la sonnette Compound (trade fermé), rien à faire."
        else:
            pnl_txt = ("?" if pnl is None else f"{pnl:+.2f}".replace(".", ",") + " €")
            msg = (f"Trade fermé {did}: {paire}, {sens}, {mode}, "
                   f"gain/perte {pnl_txt}, raison {raison}.")
        return {
            "bot": "compound",
            "kind": "trade_ferme",
            "decision_id": did,
            "paire": paire,
            "sens": sens,          # Achat | Vente
            "mode": "test" if test else mode,  # simulation | live | test
            "gain_perte_eur": pnl,
            "raison_fermeture": raison,  # cible | arrêt | manuel
            "message_fr": msg,
            "heure": now.isoformat(),
            "ts": now.isoformat(),
            "test": bool(test),
            "position_id": trade.get("position_id"),
        }

    # ---- health: watcher_down / revolut_down → Risk bell only
    def health_check(self, now: datetime, st: dict, rings: list) -> dict:
        cfg, hc = self.cfg, self.cfg["health"]
        hst = load_json(self.f_health, {}) or {}
        own = open_positions_any(cfg)
        wb = read_heartbeat(Path(cfg["watch_heartbeat"]), now)
        rb = read_heartbeat(Path(cfg["revolut_heartbeat"]), now)
        wd = wb["data"] or {}
        own_live = sum(1 for p in own if p["mode"] == "live")
        own_paper = len(own) - own_live
        n_live = max(_int0(wd.get("open_live")), own_live)
        n_paper = max(_int0(wd.get("open_paper")), own_paper)
        pos_open = (n_live + n_paper) > 0
        common = {"positions": own, "position_ids": [p["id"] for p in own],
                  "cycle_ids": [p["cycle_id"] for p in own if p.get("cycle_id")],
                  "open_live": n_live, "open_paper": n_paper}
        info: dict = {"positions_ouvertes": n_live + n_paper, "open_live": n_live, "open_paper": n_paper}

        # Persistent "file absent while a position is open" timers (survive restarts).
        absent = hst.get("_absent") if isinstance(hst.get("_absent"), dict) else {}
        hst["_absent"] = absent

        def absent_for(name: str, hb: dict, watching: bool) -> float | None:
            """Seconds the heartbeat file has been absent while `watching` (position open…); None otherwise."""
            if hb["exists"] or not watching:
                absent.pop(name, None)
                return None
            since = parse_ts(absent.get(name))
            if since is None or since > now:
                since = now
                absent[name] = now.isoformat()
            return (now - since).total_seconds()

        def missing(name: str, hb: dict) -> bool:
            """Absent (no open position) or unreadable → no check. Logged once / rate-limited."""
            if not hb["exists"]:
                if name not in self._hb_missing_logged:
                    self._hb_missing_logged.add(name)
                    self.log("INFO", f"santé: {Path(cfg[name]).name} absent — pas de contrôle {name} (pas de sonnerie)", now)
                return True
            self._hb_missing_logged.discard(name)
            if hb["error"]:
                self.log_every("hb-err-" + name, 1800, "WARN", f"santé: {Path(cfg[name]).name} {hb['error']} — ignoré", now)
                return True
            return False

        def absent_open_log(name: str, grace: float) -> None:
            tag = name + ":ouvert"
            if tag not in self._hb_missing_logged:
                self._hb_missing_logged.add(tag)
                self.log("WARN", f"santé: {Path(cfg[name]).name} absent alors qu'une position est ouverte "
                                 f"({trades_ouverts_fr(n_live, n_paper)}) — alerte si toujours absent après "
                                 f"{fmt_age_fr(grace)}", now)

        def handle(kind: str, problem: bool, payload_fn) -> str:
            k = hst.setdefault(kind, {"actif": False, "depuis": None, "last_ok": None,
                                      "last_try": None, "last_result": None})
            if not problem:
                if k.get("actif"):
                    self.log("INFO", f"santé: {kind} rétabli (depuis {k.get('depuis')})", now)
                hst[kind] = {"actif": False, "depuis": None, "last_ok": None, "last_try": None,
                             "last_result": None, "retabli": now.isoformat() if k.get("actif") else k.get("retabli")}
                return "ok"
            if not k.get("actif"):
                k.update(actif=True, depuis=now.isoformat())
            if k.get("last_result") == "failed":
                if self.minutes_since(k.get("last_try"), now) < float(hc["retry_after_fail_min"]):
                    return "alerte (attente nouvel essai)"
            elif self.minutes_since(k.get("last_ok"), now) < float(hc["repeat_min"]):
                return "alerte (déjà sonné < 30 min)"
            r = self.ring("risk", kind, payload_fn(), st, now, kind_for_log=kind)
            rings.append({"bot": "risk", "key": kind, "result": r})
            k["last_try"] = now.isoformat()
            k["last_result"] = r
            if r in ("delivered", "dry"):
                k["last_ok"] = now.isoformat()
            return "alerte (" + r + ")"

        def active(kind: str) -> bool:
            return bool((hst.get(kind) or {}).get("actif"))

        mode = "live" if n_live else "paper"
        watcher_ok = False  # fresh heartbeat + pid alive (used by the revolut "absent" rule)
        # Machine pause → resume: heartbeat writers need a moment to run again. During the grace,
        # an AGE problem (too old / file absent) does not ring; real failures (ok=false ×2, pid dead) still do.
        since_resume = None if self._resume_at is None else (now - self._resume_at).total_seconds()

        def in_grace(key: str, default: float) -> bool:
            return since_resume is not None and 0 <= since_resume < float(hc.get(key, default))
        g_w, g_r = in_grace("resume_grace_watcher_s", 90), in_grace("resume_grace_revolut_s", 600)
        if since_resume is not None and (g_w or g_r):
            info["reprise"] = {"detectee_a": self._resume_at.isoformat(), "trou_s": self._resume_gap_s,
                               "grace_surveillant": g_w, "grace_revolut": g_r}
        # 1) watcher_down
        w_abs = absent_for("watch_heartbeat", wb, pos_open)
        if w_abs is not None:
            # Position open (guardian/state.json / live_orders.jsonl / …) but NO heartbeat file at all.
            self._hb_missing_logged.discard("watch_heartbeat")
            grace = float(hc.get("watcher_missing_grace_s", hc["watcher_stale_s"]))
            absent_open_log("watch_heartbeat", grace)
            problem = (w_abs >= grace and not g_w) or active("watcher_down")
            hb_name = Path(cfg["watch_heartbeat"]).name

            def wpay_absent():
                quoi = trades_ouverts_fr(n_live, n_paper)
                msg = (f"Le surveillant ne donne aucun signe de vie (fichier {hb_name} absent "
                       f"depuis {fmt_age_fr(w_abs)}), {quoi}.")
                return self.risk_payload("watcher_down", now, msg, mode=mode, heartbeat_age_s=None,
                                         heartbeat_pid=None, pid_vivant=None, heartbeat_absent=True,
                                         absent_depuis_s=round(w_abs), **common)
            info["watcher"] = (handle("watcher_down", True, wpay_absent) if problem
                               else f"fichier absent, position ouverte (alerte après {fmt_age_fr(grace)})")
            info["watcher_absent_s"] = round(w_abs)
        elif missing("watch_heartbeat", wb):
            self._hb_missing_logged.discard("watch_heartbeat:ouvert")
            if not wb["exists"]:
                handle("watcher_down", False, None)  # no position open → quiet (logs « rétabli » if it was active)
            info["watcher"] = "fichier absent" if not wb["exists"] else "illisible"
        else:
            self._hb_missing_logged.discard("watch_heartbeat:ouvert")
            age = wb["age_s"]
            pid = _int0(wd.get("pid"))
            dead = bool(pid) and not pid_alive(pid)
            too_old = age is None or age > float(hc["watcher_stale_s"])
            watcher_ok = not (too_old or dead)
            if too_old and g_w and not active("watcher_down"):
                self.log_every("resume-w", 60, "INFO", "santé: surveillant pas encore revu après la reprise — délai de grâce", now)
                too_old = False
            problem = pos_open and (too_old or dead)

            def wpay():
                quoi = trades_ouverts_fr(n_live, n_paper)
                if dead and not too_old:
                    msg = f"Le surveillant est arrêté (processus {pid} absent), {quoi}."
                else:
                    msg = (f"Le surveillant ne donne plus signe de vie depuis {fmt_age_fr(age)}, {quoi}."
                           + (f" Processus {pid} absent." if dead else ""))
                return self.risk_payload("watcher_down", now, msg, mode=mode,
                                         heartbeat_age_s=None if age is None else round(age),
                                         heartbeat_pid=pid or None, pid_vivant=not dead,
                                         heartbeat_absent=False, **common)
            info["watcher"] = handle("watcher_down", problem, wpay)
            info["watcher_age_s"] = None if age is None else round(age)
            info["watcher_pid_vivant"] = None if not pid else not dead
        # 2) revolut_down
        # Absent file only counts while the watcher itself is alive (it writes revolut_heartbeat.json
        # on its first loop with a position open); a dead watcher is already watcher_down.
        r_abs = absent_for("revolut_heartbeat", rb, pos_open and watcher_ok)
        if r_abs is not None:
            self._hb_missing_logged.discard("revolut_heartbeat")
            grace = float(hc.get("revolut_missing_grace_s", hc["revolut_stale_s"]))
            absent_open_log("revolut_heartbeat", grace)
            problem = (r_abs >= grace and not g_r) or active("revolut_down")
            rb_name = Path(cfg["revolut_heartbeat"]).name

            def rpay_absent():
                quoi = trades_ouverts_fr(n_live, n_paper)
                msg = (f"Pas de test Revolut (fichier {rb_name} absent depuis {fmt_age_fr(r_abs)}) "
                       f"alors que le surveillant tourne, {quoi}.")
                return self.risk_payload("revolut_down", now, msg, mode=mode, heartbeat_age_s=None,
                                         consecutive_failures=None, error=None, heartbeat_absent=True,
                                         absent_depuis_s=round(r_abs), **common)
            info["revolut"] = (handle("revolut_down", True, rpay_absent) if problem
                               else f"fichier absent, position ouverte (alerte après {fmt_age_fr(grace)})")
            info["revolut_absent_s"] = round(r_abs)
        elif missing("revolut_heartbeat", rb):
            self._hb_missing_logged.discard("revolut_heartbeat:ouvert")
            if not rb["exists"] and not pos_open:
                handle("revolut_down", False, None)
            info["revolut"] = "fichier absent" if not rb["exists"] else "illisible"
        else:
            self._hb_missing_logged.discard("revolut_heartbeat:ouvert")
            rd = rb["data"] or {}
            age = rb["age_s"]
            fails = _int0(rd.get("consecutive_failures"))
            bad = rd.get("ok") is False and fails >= int(hc["revolut_min_failures"])
            too_old = age is None or age > float(hc["revolut_stale_s"])
            if too_old and g_r and not active("revolut_down"):
                self.log_every("resume-r", 120, "INFO",
                               f"santé: test Revolut vieux de {fmt_age_fr(age)} juste après une reprise de la machine — "
                               f"délai de grâce ({fmt_age_fr(float(hc.get('resume_grace_revolut_s', 600)))}), pas de sonnerie", now)
                too_old = False
            problem = pos_open and (bad or too_old)
            err = str(rd.get("error") or "")[:200]

            def rpay():
                quoi = trades_ouverts_fr(n_live, n_paper)
                if bad:
                    msg = (f"Revolut ne répond plus ({fails} échecs de suite"
                           + (f" : {err[:80]}" if err else "") + f"), {quoi}.")
                else:
                    msg = f"Pas de nouvelle du test Revolut depuis {fmt_age_fr(age)}, {quoi}."
                return self.risk_payload("revolut_down", now, msg, mode=mode,
                                         heartbeat_age_s=None if age is None else round(age),
                                         consecutive_failures=fails, error=err or None,
                                         heartbeat_absent=False, **common)
            info["revolut"] = handle("revolut_down", problem, rpay)
            info["revolut_age_s"] = None if age is None else round(age)
            info["revolut_ok"] = rd.get("ok")
        save_json(self.f_health, hst)
        return info

    # ---- decisions (cached by mtime/size), extra persistent state
    def decisions(self) -> tuple[list[dict], str | None]:
        path = Path(self.cfg["decision_log"])
        try:
            stt = path.stat()
            sig = (stt.st_mtime_ns, stt.st_size)
        except OSError as e:
            return [], f"carnet des décisions illisible ({type(e).__name__})"
        if self._dec_cache and self._dec_cache[0] == sig:
            return self._dec_cache[1], self._dec_cache[2]
        dec, err = read_decisions(path)
        self._dec_cache = (sig, dec, err)
        return dec, err

    def load_extra(self) -> dict:
        ex = load_json(self.f_extra, None)
        if not isinstance(ex, dict):
            ex = {}
        ex.setdefault("idle", {})
        ex["idle"].setdefault("nuits", {})
        ex.setdefault("heure_limite", {"seeded": False, "rung": {}})
        ex.setdefault("mouvement", {})
        ex["heure_limite"].setdefault("rung", {})
        return ex

    def save_extra(self, ex: dict) -> None:
        # keep the file small: only the last 10 nights / 200 trades
        nu = ex["idle"]["nuits"]
        for k in sorted(nu)[:-10]:
            nu.pop(k, None)
        rg = ex["heure_limite"]["rung"]
        if len(rg) > 200:
            for k in sorted(rg, key=lambda k: str((rg[k] or {}).get("at")))[:-200]:
                rg.pop(k, None)
        save_json(self.f_extra, ex)

    def night_flag(self, now: datetime, decs: list[dict], derr: str | None) -> dict:
        start, end = last_night(now, self.cfg)
        d = {"nuit": start.date().isoformat(), "debut": start.isoformat(), "fin": end.isoformat()}
        if derr:
            return dict(d, sans_decision=None, raison=derr)
        ids = [x["id"] for x in decs if start <= x["ts"] < end]
        return dict(d, sans_decision=not ids, decisions=ids, source="knowledge/decision_log.md (titres D-xxx)")

    def predict_text(self, msg: str, now: datetime, night: dict, ex: dict) -> tuple[str, bool]:
        """First Predict ring after the end of a night without decision → « Nuit sans décision » in front."""
        if not night.get("sans_decision"):
            return msg, False
        end = parse_ts(night.get("fin"))
        if end is None or now < end or now.date() != end.date() or ex.get("nuit_annoncee") == night.get("nuit"):
            return msg, False
        return "Nuit sans décision (aucune décision D-xxx entre 22h et 9h). " + msg, True

    def predict_ring(self, key: str, payload: dict, st: dict, now: datetime, kind: str,
                     night: dict, ex: dict, count_daily: bool = True) -> str:
        msg, flagged = self.predict_text(payload["message_fr"], now, night, ex)
        if flagged:
            payload = dict(payload, message_fr=msg, nuit_sans_decision=True, nuit=night.get("nuit"))
        r = self.ring("predict", key, payload, st, now, count_daily=count_daily, kind_for_log=kind)
        if flagged and r in ("delivered", "dry"):
            ex["nuit_annoncee"] = night.get("nuit")
        return r

    # ---- idle: no new D-xxx for N hours + room under the simulation cap → ring Predict
    def idle_check(self, now: datetime, st: dict, dlv: str, win: bool, stale: bool, rings: list,
                   decs: list[dict], derr: str | None, night: dict, ex: dict) -> dict:
        ic, pc = self.cfg.get("idle") or {}, self.cfg["predict"]
        info: dict = {"actif": bool(ic.get("actif"))}
        if not ic.get("actif"):
            return info
        hours = float(ic.get("heures_sans_decision", 4))
        gap_h = float(ic.get("intervalle_min_h", 4))
        idl = ex["idle"]
        past = [x for x in decs if x["ts"] <= now]
        last = max(past, key=lambda x: x["ts"]) if past else None
        info.update({"derniere_decision": last["id"] if last else None,
                     "derniere_decision_a": last["ts"].isoformat() if last else None,
                     "heures_sans_decision": None if not last else round((now - last["ts"]).total_seconds() / 3600, 2),
                     "dernier_reveil": idl.get("last_ring")})
        nk = in_night(now, self.cfg)
        info["nuit_en_cours"] = nk
        if nk:
            info["reveils_cette_nuit"] = int(idl["nuits"].get(nk, 0))
        cap = sim_cap_room(self.cfg)
        info["plafond"] = cap

        def no(reason: str) -> dict:
            info["sonne"] = False
            info["raison"] = reason
            return info
        if derr:
            return no(derr)
        if last and (now - last["ts"]).total_seconds() < hours * 3600:
            return no(f"décision récente ({last['id']})")
        if not cap.get("ok"):
            return no("plafond simulation inconnu : " + str(cap.get("raison")))
        if cap["place_eur"] < float(ic.get("marge_min_eur", 5)):
            return no(f"plafond simulation plein ({fmt_eur(cap['expose_eur'], 2)} € sur {fmt_eur(cap['plafond_eur'], 2)} €)")
        lr = parse_ts(idl.get("last_ring"))
        if lr is not None and lr <= now and (now - lr).total_seconds() < gap_h * 3600:
            return no(f"déjà réveillé à {hhmm(lr)} (max 1 par {fmt_eur(gap_h)} h)")
        if nk and int(idl["nuits"].get(nk, 0)) >= int(ic.get("max_par_nuit", 2)):
            return no(f"max {int(ic.get('max_par_nuit', 2))} réveils cette nuit")
        lf = parse_ts(idl.get("last_fail"))
        if lf is not None and lf <= now and (now - lf).total_seconds() < float(ic.get("retry_after_fail_min", 5)) * 60:
            return no("échec d'envoi récent, nouvel essai bientôt")
        if not win:
            return no("fenêtre Predict fermée")
        if stale:
            return no("prix pas à jour")
        if any(r["bot"] == "predict" for r in rings):
            return no("Predict déjà réveillé à ce tour")
        if self.bucket(st, dlv, "predict")["delivered"] >= int(pc["max_per_day"]):
            self.log_every("p-cap-idle", 3600, "INFO",
                           f"sans décision depuis {fmt_eur(hours)} h mais max {pc['max_per_day']} sonneries Predict/jour atteint", now)
            return no(f"max {pc['max_per_day']} sonneries Predict/jour atteint")
        last_txt = (f"Dernière décision : {last['id']} le {last['ts'].strftime('%d/%m')} à {hhmm(last['ts'])}."
                    if last else "Aucune décision dans le carnet.")
        msg = (f"Predict : pas de décision depuis {fmt_eur(hours)} h, propose une simulation ou donne un prix d'entrée "
               f"avec une nouvelle zone. {last_txt} Place en simulation : {fmt_eur(cap['place_eur'], 2)} € "
               f"sur {fmt_eur(cap['plafond_eur'])} €.")
        payload = {"bot": "predict", "kind": "sans_decision", "raison_type": "sans_decision", "zone_id": None,
                   "derniere_decision": info["derniere_decision"], "derniere_decision_a": info["derniere_decision_a"],
                   "heures_sans_decision": info["heures_sans_decision"], "seuil_heures": hours,
                   "place_simulation_eur": cap["place_eur"], "plafond_simulation_eur": cap["plafond_eur"],
                   "expose_simulation_eur": cap["expose_eur"], "nuit": nk, "heure": now.isoformat(),
                   "message_fr": msg, "test": False}
        key = "idle:" + now.isoformat(timespec="minutes")
        r = self.predict_ring(key, payload, st, now, "sans_decision", night, ex)
        rings.append({"bot": "predict", "key": key, "result": r})
        if r in ("delivered", "dry"):
            idl["last_ring"] = now.isoformat()
            idl.pop("last_fail", None)
            if nk:
                idl["nuits"][nk] = int(idl["nuits"].get(nk, 0)) + 1
        else:
            idl["last_fail"] = now.isoformat()
        info["sonne"] = r
        return info

    # ---- heure limite: the watcher wrote a deadline reminder → ring Predict once per trade
    # ---- mouvement: a pair moved > seuil_pct from its price at Predict's latest D-xxx → ring Predict
    def note(self, now: datetime, kind: str, message: str, **extra) -> None:
        """A line in rings.jsonl that is NOT a ring (bot « sonnette », result « note »): not counted anywhere."""
        rec = {"at": now.isoformat(), "bot": "sonnette", "key": f"{kind}:{now.strftime('%Y%m%dT%H%M')}",
               "result": "note", "http_status": None, "error": None, "tries": 0,
               "payload": dict({"bot": "sonnette", "pour": "predict", "kind": kind, "raison_type": kind,
                                "message_fr": message, "test": False}, **extra)}
        try:
            with self.f_rings.open("a", encoding="utf-8") as f:
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        except OSError:
            pass
        self.log("INFO", f"note {kind}: {message}", now)

    def mouvement_set_ref(self, mv: dict, now: datetime, prices: dict, pairs, source: str,
                          dec: dict | None = None) -> None:
        ref = {"source": source, "pose_a": now.isoformat(),
               "decision_id": (dec or {}).get("id") or (mv.get("ref") or {}).get("decision_id"),
               "decision_ts": (dec["ts"].isoformat() if dec else (mv.get("ref") or {}).get("decision_ts")),
               "prix": {}, "prix_ts": {}, "origine": {}}
        at = mids_at(Path(self.cfg["ticks_dir"]), dec["ts"], pairs) if dec else {}
        for p in pairs:
            if p in at:
                ref["prix"][p] = at[p]["mid"]; ref["prix_ts"][p] = at[p]["ts"].isoformat()
                ref["origine"][p] = "prix à l'heure de la décision"
            elif p in prices:
                ref["prix"][p] = prices[p]; ref["prix_ts"][p] = now.isoformat()
                ref["origine"][p] = "prix actuel" + (" (pas de prix à l'heure de la décision)" if dec else "")
        mv["ref"] = ref
        mv["attente"] = None
        mv["echec"] = None

    def mouvement_check(self, now: datetime, st: dict, prices: dict, ticks: dict, stale: bool, rings: list,
                        decs: list, derr: str | None, night: dict, ex: dict) -> dict:
        mc = self.cfg.get("mouvement") or {}
        info: dict = {"actif": bool(mc.get("actif"))}
        if not mc.get("actif"):
            return info
        pairs = [p for p in (mc.get("paires") or ALLOWED_PAIRS) if p in ALLOWED_PAIRS]
        seuil = float(mc.get("seuil_pct", 0.5))
        mv = ex["mouvement"]
        today = now.date().isoformat()
        if (mv.get("jour") or {}).get("date") != today:
            mv["jour"] = {"date": today, "n": 0}
        gap = float(mc.get("intervalle_min_min", 30))
        info.update(seuil_pct=seuil, aujourd_hui=mv["jour"]["n"],
                    intervalle_min_min=float(mc.get("intervalle_min_min", 30)),
                    attente_decision_min=float(mc.get("attente_decision_min", 20)))

        def finish(raison: str | None = None, sonne=False) -> dict:
            ref = mv.get("ref") or {}
            info.update(reference=ref or None, aujourd_hui=mv["jour"]["n"], attente_decision=mv.get("attente"),
                        echec=mv.get("echec"), dernier_reveil=mv.get("dernier_reveil"), sonne=sonne)
            bases = [b for b in (parse_ts(mv.get("dernier_reveil")) if mv.get("dernier_reveil") else None,
                                 max(d["ts"] for d in decs) if decs else None) if b]
            nxt = max(bases) + timedelta(minutes=gap) if bases else None
            info["prochain_reveil_possible"] = nxt.isoformat() if nxt else None
            info["prochain_reveil_possible_fr"] = (hhmm(nxt) if nxt and nxt > now else "maintenant") if bases else None
            info["mouvement_pct"] = {p: (round((prices[p] / r - 1) * 100, 3) if p in prices and r else None)
                                     for p, r in (ref.get("prix") or {}).items()}
            if raison:
                info["raison"] = raison
            return info

        if derr:
            return finish(derr)
        if not decs:
            return finish("aucune décision D-xxx dans le carnet — pas de référence")
        last = max(enumerate(decs), key=lambda iv: (iv[1]["ts"], iv[0]))[1]
        ref = mv.get("ref") or {}
        if not ref:
            self.mouvement_set_ref(mv, now, prices, pairs, "décision (démarrage)", last)
            self.log("INFO", f"mouvement: amorçage — références = prix à {last['id']} "
                     f"({last['ts'].strftime('%d/%m %H:%M')}) : {mv['ref']['prix']} (pas de sonnerie)", now)
            return finish("amorçage (pas de sonnerie)")
        if last["id"] != ref.get("decision_id") or last["ts"].isoformat() != ref.get("decision_ts"):
            after_ring = bool(mv.get("attente") or mv.get("echec"))
            self.mouvement_set_ref(mv, now, prices, pairs, "décision", last)
            self.log("INFO", f"mouvement: nouvelle décision {last['id']}" + (" après réveil" if after_ring else "")
                     + f" — références remises : {mv['ref']['prix']}", now)
            return finish(f"références remises à {last['id']}")
        if any(p not in (mv["ref"].get("prix") or {}) for p in pairs):
            for p in pairs:  # a pair without any price yet (collector down at the decision): take it when it comes
                if p not in mv["ref"]["prix"] and p in prices:
                    mv["ref"]["prix"][p] = prices[p]; mv["ref"]["prix_ts"][p] = now.isoformat()
                    mv["ref"]["origine"][p] = "prix actuel (pas de prix à l'heure de la décision)"
        att = mv.get("attente")
        if att:
            if self.minutes_since(att.get("at"), now) < float(mc.get("attente_decision_min", 20)):
                return finish(f"réveil envoyé à {hhmm(parse_ts(att['at']))}, attente d'une nouvelle D-xxx")
            self.mouvement_set_ref(mv, now, prices, pairs, "pas de nouvelle décision après réveil")
            self.note(now, "mouvement_sans_decision",
                      f"pas de nouvelle décision après réveil (réveil mouvement de {hhmm(parse_ts(att['at']))}, "
                      f"rien depuis {att.get('decision_id')}) — références remises aux prix actuels",
                      decision_id=att.get("decision_id"), reveil_at=att.get("at"), references=mv["ref"]["prix"])
            return finish("pas de nouvelle décision après réveil — références remises aux prix actuels")
        ech = mv.get("echec")
        if ech:
            if int(ech.get("essais") or 0) >= int(mc.get("max_essais", 3)):
                self.mouvement_set_ref(mv, now, prices, pairs, "abandon après échecs d'envoi")
                self.log("ERROR", f"mouvement: {ech.get('essais')} échecs d'envoi — abandon, références remises aux prix actuels", now)
                return finish("abandon après échecs d'envoi")
            if self.minutes_since(ech.get("at"), now) < float(mc.get("retry_after_fail_min", 5)):
                return finish("échec d'envoi, nouvel essai après "
                              f"{fmt_eur(float(mc.get('retry_after_fail_min', 5)))} min")
        # moves (fresh prices only)
        max_age = float(mc.get("prix_max_age_s", 180))
        fresh = {p: prices[p] for p in pairs if p in prices and p in ticks
                 and (now - ticks[p]["ts"]).total_seconds() <= max_age}
        crossed = []
        for p in pairs:
            r = (mv["ref"].get("prix") or {}).get(p)
            if r and p in fresh:
                pct = (fresh[p] / r - 1) * 100
                if abs(pct) > seuil:
                    crossed.append((p, r, fresh[p], pct))
        if not crossed:
            if ech:
                mv["echec"] = None
                self.log("INFO", "mouvement: plus aucun franchissement — nouvel essai annulé", now)
            if stale or len(fresh) < len(pairs):
                return finish("prix pas à jour (> " + fmt_eur(max_age) + " s)")
            return finish(None)
        if stale or len(fresh) < len(pairs):
            self.log_every("mv-stale", 600, "INFO", "mouvement: prix pas à jour — pas de sonnerie", now)
            return finish("prix pas à jour (> " + fmt_eur(max_age) + " s)")
        if not ech:
            lr = parse_ts(mv.get("dernier_reveil")) if mv.get("dernier_reveil") else None
            base, quoi = last["ts"], f"la dernière décision {last['id']}"
            if lr and lr > base:
                base, quoi = lr, "le dernier réveil mouvement"
            if now < base + timedelta(minutes=gap):
                self.log_every("mv-gap", 600, "INFO", f"mouvement: franchissement mais trop tôt — prochain réveil possible à "
                               f"{hhmm(base + timedelta(minutes=gap))} ({fmt_eur(gap)} min après {quoi})", now)
                return finish(f"prochain réveil possible à {hhmm(base + timedelta(minutes=gap))} "
                              f"({fmt_eur(gap)} min après {quoi})")
        did = mv["ref"].get("decision_id") or "?"
        parts = ", ".join(f"{asset(p)} {fmt_eur(r, 2)} € → {fmt_eur(px, 2)} € ({fmt_pct_signed(pct)})"
                          for p, r, px, pct in crossed)
        msg = (f"mouvement > {f'{seuil:g}'.replace('.', ',')} % : {parts} depuis {did}. Refais tes 3 propositions (risquée, prudente, "
               f"équilibrée) dans une nouvelle D-xxx ; si rien à proposer, écris une D-xxx « pas de proposition » "
               f"avec tes raisons.")
        key = f"mouvement:{did}:{now.strftime('%Y%m%dT%H%M')}"
        payload = {"bot": "predict", "kind": "mouvement", "raison_type": "mouvement", "decision_id": did,
                   "seuil_pct": seuil, "heure": now.isoformat(), "test": False, "message_fr": msg,
                   "paires": [{"paire": p, "reference": round(r, 6), "prix": round(px, 6), "mouvement_pct": round(pct, 3)}
                              for p, r, px, pct in crossed],
                   "reveil_mouvement_du_jour": mv["jour"]["n"] + 1}
        r = self.predict_ring(key, payload, st, now, "mouvement", night, ex, count_daily=False)
        rings.append({"bot": "predict", "key": key, "result": r})
        if r in ("delivered", "dry"):
            mv["jour"]["n"] += 1
            mv["dernier_reveil"] = now.isoformat()
            mv["attente"] = {"at": now.isoformat(), "decision_id": did, "paires": [c[0] for c in crossed]}
            mv["echec"] = None
            return finish(None, sonne=r)
        mv["echec"] = {"at": now.isoformat(), "essais": int((ech or {}).get("essais") or 0) + 1}
        return finish("échec d'envoi", sonne=r)

    def read_reminders(self) -> dict:
        out: dict = {}
        for ln in tail_lines(Path(self.cfg["deadline_reminders"]), 262144):
            try:
                r = json.loads(ln)
            except ValueError:
                continue
            if isinstance(r, dict) and r.get("position_id"):
                out.setdefault(str(r["position_id"]), r)
        one = load_json(Path(self.cfg["deadline_reminder"]), None)
        if isinstance(one, dict) and one.get("position_id"):
            out.setdefault(str(one["position_id"]), one)
        return out

    def deadline_check(self, now: datetime, st: dict, dlv: str, win: bool, stale: bool, prices: dict,
                       rings: list, night: dict, ex: dict) -> dict:
        hc, pc = self.cfg.get("heure_limite") or {}, self.cfg["predict"]
        info: dict = {"actif": bool(hc.get("actif")), "en_attente": []}
        if not hc.get("actif"):
            return info
        hl = ex["heure_limite"]
        rems = self.read_reminders()
        if not hl.get("seeded"):
            for pid, r in rems.items():
                hl["rung"].setdefault(pid, {"at": now.isoformat(), "result": "seed", "decision_id": r.get("decision_id")})
            hl["seeded"] = True
            if rems:
                self.log("INFO", f"heure limite: amorçage — {len(rems)} rappel(s) déjà écrit(s) marqués (pas de sonnerie rétroactive)", now)
            return info
        todo = {pid: r for pid, r in rems.items()
                if pid not in hl["rung"] or (hl["rung"][pid] or {}).get("result") == "failed"}
        if not todo:
            return info
        gs = load_json(Path(self.cfg["guardian_state"]), None)
        if not isinstance(gs, dict):
            self.log_every("hl-gs", 600, "WARN", "heure limite: guardian/state.json illisible — on attend", now)
            info["en_attente"] = list(todo)
            return info
        pos = {str(p.get("id")): p for p in (gs.get("positions") or []) if isinstance(p, dict)}
        for pid, r in todo.items():
            ks = hl["rung"].get(pid) or {}
            p = pos.get(pid)
            if p is None or str(p.get("status") or "open").lower() != "open":
                hl["rung"][pid] = {"at": now.isoformat(), "result": "deja_ferme", "decision_id": r.get("decision_id")}
                self.log("INFO", f"heure limite: {r.get('decision_id') or pid} déjà fermé — pas de sonnerie", now)
                continue
            if ks.get("result") == "failed":
                if int(ks.get("essais") or 0) >= int(hc.get("max_essais", 3)):
                    continue
                if self.minutes_since(ks.get("at"), now) < float(hc.get("retry_after_fail_min", 5)):
                    continue
            pair = norm_pair(p.get("pair") or r.get("pair"))
            px = prices.get(pair)
            if not win or stale or px is None:
                info["en_attente"].append(pid)
                self.log_every("hl-wait-" + pid, 600, "INFO",
                               f"heure limite {r.get('decision_id') or pid}: en attente ({'fenêtre fermée' if not win else 'prix pas à jour'})", now)
                continue
            if self.bucket(st, dlv, "predict")["delivered"] >= int(pc["max_per_day"]):
                info["en_attente"].append(pid)
                self.log_every("p-cap-hl", 3600, "INFO",
                               f"heure limite {r.get('decision_id') or pid}: max {pc['max_per_day']} sonneries Predict/jour atteint", now)
                continue
            did = p.get("decision_id") or r.get("decision_id") or pid
            idea = str(p.get("idea_type") or p.get("kind") or r.get("idea_type") or "").lower()
            idee = "idée à la baisse" if idea == "baisse" or p.get("side") == "short" else "idée à la hausse"
            stop = to_float(p.get("stop_price") or p.get("stop_price_eur") or p.get("safety_price"))
            tgt = to_float(p.get("target_price"))
            dl = parse_ts(r.get("deadline") or p.get("deadline"))
            delai = int(hc.get("delai_risk_min", 5))
            msg = (f"Heure limite passée pour {did} ({asset(pair)}, {idee}, trade {pid}"
                   + (f", heure limite {hhmm(dl.astimezone(TZ))}" if dl else "") + f") : prix actuel {fmt_eur(px, 2)} €"
                   + (f", arrêt {fmt_eur(stop, 2)} €" if stop is not None else "")
                   + (f", visé {fmt_eur(tgt, 2)} €" if tgt is not None else "")
                   + f". Predict, décide maintenant (garder ou fermer) et passe la main à @PM-Risk, "
                     f"qui ferme ou garde le trade dans les {delai} minutes.")
            payload = {"bot": "predict", "kind": "heure_limite", "raison_type": "heure_limite", "zone_id": None,
                       "decision_id": did, "position_id": pid, "paire": pair, "prix": round(px, 6),
                       "stop": stop, "cible": tgt, "heure_limite": dl.isoformat() if dl else None,
                       "delai_risk_min": delai, "heure": now.isoformat(), "message_fr": msg, "test": False}
            key = "heure_limite:" + pid
            res = self.predict_ring(key, payload, st, now, "heure_limite", night, ex)
            rings.append({"bot": "predict", "key": key, "result": res})
            hl["rung"][pid] = {"at": now.isoformat(), "result": res, "decision_id": did,
                               "essais": int(ks.get("essais") or 0) + 1}
        return info

    # ---- one ring
    def ring(self, bot: str, key: str, payload: dict, st: dict | None, now: datetime,
             count_daily: bool = True, kind_for_log: str = "") -> str:
        """Send (or dry-log) one ring. Returns 'delivered' | 'dry' | 'failed'."""
        ch = self.secrets.channel(bot)
        delivery = "real" if ch["real"] else "dry"
        payload = dict(payload, envoi="reel" if ch["real"] else "dry")
        if ch["real"]:
            sender = self.sender or post_json
            res = sender(ch, payload, self.cfg, self.secrets.all_secret_strings(),
                         lambda lvl, m: self.log(lvl, m))
            result = "delivered" if res.get("ok") else "failed"
        else:
            res = {"ok": None, "status": None, "error": None, "tries": 0}
            result = "dry"
        if st is not None and key:
            b = self.bucket(st, delivery, bot)
            k = b["keys"].setdefault(key, {"delivered": 0, "attempts": 0, "last_try": None,
                                           "last_ok": None, "last_result": None})
            k["attempts"] += 1
            k["last_try"] = now.isoformat()
            k["last_result"] = result
            if result in ("delivered", "dry"):
                k["delivered"] += 1
                k["last_ok"] = now.isoformat()
                if count_daily:
                    b["delivered"] += 1
        rec = {"at": now.isoformat(), "bot": bot, "key": key, "result": result,
               "http_status": res.get("status"), "error": res.get("error"), "tries": res.get("tries"),
               "payload": payload}
        try:
            with self.f_rings.open("a", encoding="utf-8") as f:
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        except OSError:
            pass
        self.write_totals()  # status.json totals.* à jour à chaque sonnerie
        word = {"delivered": "SONNÉ (livré)", "dry": "AURAIT SONNÉ (mode dry)", "failed": "ÉCHEC d'envoi"}[result]
        extra = f" — {res.get('error')}" if result == "failed" else ""
        self.log("RING" if result != "failed" else "ERROR",
                 f"{word} bot={bot} {kind_for_log} {key}: {payload.get('message_fr')}{extra}", now)
        return result

    # ---- totaux depuis le journal des sonneries (rings.jsonl), écrits dans status.json → totals
    @staticmethod
    def ring_is_test(rec: dict) -> bool:
        pl = rec.get("payload") if isinstance(rec.get("payload"), dict) else {}
        return bool(pl.get("test") or pl.get("mode") == "test" or str(pl.get("zone_id") or "").upper() == "TEST"
                    or str(pl.get("decision_id") or "").upper().startswith("D-ESSAI"))

    def ring_totals(self) -> dict:
        """Par sonnette : vrais réveils (pas un essai) et essais, tous résultats (livré / dry / échec) détaillés,
        + le dernier vrai réveil. Source unique : state/rings.jsonl (une ligne par sonnerie)."""
        tot = {b: {"vrais": 0, "essais": 0,
                   "vrais_par_resultat": {"delivered": 0, "dry": 0, "failed": 0},
                   "essais_par_resultat": {"delivered": 0, "dry": 0, "failed": 0},
                   "dernier_vrai": None, "dernier_essai": None} for b in BOTS}
        first = None
        try:
            lines = self.f_rings.read_text(encoding="utf-8").splitlines()
        except OSError:
            lines = []
        for ln in lines:
            try:
                r = json.loads(ln)
            except ValueError:
                continue
            pl = r.get("payload") if isinstance(r.get("payload"), dict) else {}
            b = r.get("bot") or pl.get("bot")
            if b not in tot:
                continue
            first = first or r.get("at")
            t = tot[b]
            kind = "essais" if self.ring_is_test(r) else "vrais"
            t[kind] += 1
            res = r.get("result")
            t[kind + "_par_resultat"][res] = t[kind + "_par_resultat"].get(res, 0) + 1
            info = {"at": r.get("at"), "result": res, "kind": pl.get("kind"), "envoi": pl.get("envoi"),
                    "zone_id": pl.get("zone_id"), "decision_id": pl.get("decision_id"),
                    "paire": pl.get("paire") or pl.get("pair"), "message_fr": pl.get("message_fr")}
            t["dernier_vrai" if kind == "vrais" else "dernier_essai"] = info
        return dict(tot, depuis=first, lignes=len(lines), source="state/rings.jsonl",
                    regle_essai="payload.test, mode=test, zone_id=TEST ou decision_id D-ESSAI…")

    def write_totals(self) -> None:
        try:
            st = load_json(self.f_status, {}) or {}
            st["totals"] = self.ring_totals()
            st["totals_at"] = datetime.now(TZ).isoformat()
            save_json(self.f_status, st)
        except Exception as e:  # noqa: BLE001
            self.log("WARN", f"totaux sonneries: {type(e).__name__}")

    # ---- predict window
    def predict_window_open(self, now: datetime) -> bool:
        pc = self.cfg["predict"]
        if now.weekday() not in [int(d) for d in pc.get("days", [0, 1, 2, 3, 4])]:
            return False
        try:
            h1, m1 = [int(x) for x in str(pc["window_start"]).split(":")]
            h2, m2 = [int(x) for x in str(pc["window_end"]).split(":")]
        except Exception:  # noqa: BLE001
            h1, m1, h2, m2 = 15, 0, 17, 0
        cur = now.hour * 60 + now.minute
        return h1 * 60 + m1 <= cur < h2 * 60 + m2

    @staticmethod
    def risk_payload(kind: str, now: datetime, message: str, pair=None, price=None, stop=None,
                     position_id=None, test=False, **extra) -> dict:
        p = {"mode": "test" if test else "live", "kind": kind, "pair": pair, "price": price,
             "stop": stop, "position_id": position_id, "message_fr": message,
             "ts": now.isoformat(), "test": bool(test), "bot": "risk"}
        p.update(extra)
        return p

    # ---- cycle
    def cycle(self, now: datetime | None = None, now_mono: float | None = None) -> dict:
        now = (now or datetime.now(TZ)).astimezone(TZ)
        now_mono = time.monotonic() if now_mono is None else now_mono
        cfg, rc, pc = self.cfg, self.cfg["risk"], self.cfg["predict"]
        today = now.date().isoformat()
        # machine pause / resume: both wall clock and monotonic jumped since the previous cycle
        if self._last_cycle is not None:
            gw = (now - self._last_cycle[0]).total_seconds()
            gm = now_mono - self._last_cycle[1]
            lim = float((cfg.get("health") or {}).get("resume_gap_s", 120))
            if gw > lim and gm > lim:
                self._resume_at, self._resume_gap_s = now, round(min(gw, gm))
                self.log("WARN", f"reprise détectée : {fmt_age_fr(min(gw, gm))} sans tour (pause de la machine ?) — "
                                 f"santé en délai de grâce avant de sonner Risk", now)
        self._last_cycle = (now, now_mono)
        st = self.load_state(today)
        rings: list[dict] = []
        eq: dict = {}
        daily_loss = dd = None

        modes = {b: self.secrets.channel(b) for b in BOTS}
        for b in BOTS:
            m = "réel" if modes[b]["real"] else "dry"
            if self._last_modes.get(b) != m:
                self.log("INFO", f"bot {b}: mode {m} ({modes[b]['reason']})", now)
                self._last_modes[b] = m

        # 1) prices (collector files only)
        ticks = latest_ticks(Path(cfg["ticks_dir"]), now)
        newest = max((t["ts"] for t in ticks.values()), default=None)
        age = (now - newest).total_seconds() if newest else None
        stale = age is None or age > float(cfg["stale_seconds"])
        prices = {}
        for pair, t in ticks.items():
            a = (now - t["ts"]).total_seconds()
            if a <= float(cfg["stale_seconds"]):
                prices[pair] = t["mid"]
            elif not stale:
                self.log_every(f"stale-{pair}", 600, "WARN", f"prix {pair} trop vieux ({int(a)} s) — ignoré", now)
        if stale:
            self.log_every("stale", 600, "WARN",
                           f"PRIX PÉRIMÉS: dernier tick il y a {int(age) if age is not None else '?'} s "
                           f"(> {cfg['stale_seconds']} s) — aucune sonnette sur les prix", now)
            try:
                self.f_stale.write_text(json.dumps({"checked_at": now.isoformat(), "last_tick_age_s": age}) + "\n")
            except OSError:
                pass
        else:
            if self.f_stale.exists():
                self.f_stale.unlink(missing_ok=True)
                self.log("INFO", "prix de nouveau frais", now)
            self._log_last.pop("stale", None)

        # 2) zones
        zones, problems, ferr = load_zones(Path(cfg["zones_file"]), now)
        if ferr:
            self.log_every("zones-file", 1800, "WARN", ferr, now)
        for pb in problems:
            self.log_every("zone:" + pb, 6 * 3600, "WARN", "zone ignorée → " + pb, now)

        def hit(sens: str, price: float, seuil: float) -> bool:
            return price <= seuil if sens == "sous" else price >= seuil

        # 3) predict bell
        win = self.predict_window_open(now)
        dlv_p = "real" if modes["predict"]["real"] else "dry"
        decs, derr = self.decisions()
        night = self.night_flag(now, decs, derr)
        ex = self.load_extra()
        if not stale and win:
            for z in [z for z in zones if z["bot"] == "predict"]:
                px = prices.get(z["paire"])
                if px is None or not hit(z["sens"], px, z["prix"]):
                    continue
                key = "zone:" + z["id"]
                ks = self.key_state(st, dlv_p, "predict", key)
                if ks["delivered"] >= 1:
                    continue
                if self.bucket(st, dlv_p, "predict")["delivered"] >= int(pc["max_per_day"]):
                    self.log_every("p-cap", 3600, "INFO",
                                   f"zone {z['id']} touchée mais max {pc['max_per_day']} sonneries Predict/jour atteint", now)
                    continue
                if not self.can_retry(ks, now, 0, float(pc["retry_after_fail_min"]),
                                      int(pc["max_attempts_per_zone_per_day"])):
                    continue
                sens_txt = "sous" if z["sens"] == "sous" else "au-dessus de"
                msg = (f"{asset(z['paire'])} est passé {sens_txt} {fmt_eur(z['prix'])} € "
                       f"({fmt_eur(px, 2)} €) à {hhmm(now)}. Predict, à toi de juger.")
                payload = {"bot": "predict", "zone_id": z["id"], "paire": z["paire"], "prix": round(px, 6),
                           "seuil": z["prix"], "sens": z["sens"], "heure": now.isoformat(),
                           "message_fr": msg, "raison": z["raison"], "kind": "zone", "test": False}
                r = self.predict_ring(key, payload, st, now, "zone", night, ex)
                rings.append({"bot": "predict", "key": key, "result": r})
        # 3b) heure limite (once per trade), then 3c) « sans décision » (idle)
        try:
            hl_info = self.deadline_check(now, st, dlv_p, win, stale, prices, rings, night, ex)
        except Exception as e:  # noqa: BLE001
            self.log("ERROR", f"heure limite: {type(e).__name__}: {e}", now)
            hl_info = {"erreur": type(e).__name__}
        try:
            idle_info = self.idle_check(now, st, dlv_p, win, stale, rings, decs, derr, night, ex)
        except Exception as e:  # noqa: BLE001
            self.log("ERROR", f"sans décision: {type(e).__name__}: {e}", now)
            idle_info = {"erreur": type(e).__name__}
        try:
            mv_info = self.mouvement_check(now, st, prices, ticks, stale, rings, decs, derr, night, ex)
        except Exception as e:  # noqa: BLE001
            self.log("ERROR", f"mouvement: {type(e).__name__}: {e}", now)
            mv_info = {"erreur": type(e).__name__}
        self.save_extra(ex)
        zd = zones_distance(zones, prices, float((cfg.get("zones_distance") or {}).get("max_pct", 1.0)))

        # 4) risk bell — only while a REAL position is open
        positions, pinfo = self.real_positions(now_mono)
        dlv_r = "real" if modes["risk"]["real"] else "dry"
        no_stop, breaches = [], []

        def risk_try(key, payload, after_ok_min, after_fail_min, max_ok, kind):
            ks = self.key_state(st, dlv_r, "risk", key)
            if ks["delivered"] >= max_ok:
                return None
            if not self.can_retry(ks, now, after_ok_min, after_fail_min, int(rc["max_attempts_per_day"])):
                return None
            r = self.ring("risk", key, payload, st, now, kind_for_log=kind)
            rings.append({"bot": "risk", "key": key, "result": r})
            return r

        if positions:
            # stale_price (rings even though prices are stale — that's the point)
            if age is None or age > float(rc["stale_ring_after_s"]):
                mins = "?" if age is None else str(int(age // 60))
                msg = (f"Attention : je ne reçois plus de prix depuis {mins} min alors qu'une position "
                       f"en argent réel est ouverte. Je suis aveugle. Risk, vérifie le collecteur de prix et la position.")
                risk_try("stale_price", self.risk_payload("stale_price", now, msg,
                                                          last_tick_age_s=None if age is None else round(age)),
                         float(rc["stale_repeat_min"]), float(rc["retry_after_fail_min"]), 10 ** 6, "stale_price")

            if not stale:
                for p in positions:
                    stop = derive_stop(p)
                    px = prices.get(p["pair"])
                    if p.get("side") != "long":
                        continue
                    pid = str(p.get("id"))
                    if stop is None:
                        no_stop.append(pid)
                        self.log_every("nostop-" + pid, 3600, "WARN",
                                       f"position/ordre réel {pid} ({p['pair']}, source {p.get('source')}) "
                                       f"SANS prix d'arrêt — pas de surveillance stop", now)
                        continue
                    if px is None:
                        continue
                    if px <= stop:
                        breaches.append({"position_id": pid, "pair": p["pair"], "price": px, "stop": stop})
                        n = self.key_state(st, dlv_r, "risk", "stop_hit:" + pid)["delivered"] + 1
                        msg = (f"URGENT argent réel : {asset(p['pair'])} est passé sous ton prix d'arrêt "
                               f"{fmt_eur(stop)} € ({fmt_eur(px, 2)} €) à {hhmm(now)}. Position {pid}. "
                               f"Risk, vérifie et agis maintenant (aucune vente automatique)."
                               + (f" Rappel n°{n}." if n > 1 else ""))
                        payload = self.risk_payload("stop_hit", now, msg, p["pair"], round(px, 6), round(stop, 6), pid,
                                                    zone_id="STOP-REEL-" + pid, paire=p["pair"], prix=round(px, 6),
                                                    seuil=round(stop, 6), sens="sous", heure=now.isoformat(),
                                                    rappel=n, source=p.get("source"))
                        risk_try("stop_hit:" + pid, payload, float(rc["stop_hit_repeat_min"]),
                                 float(rc["retry_after_fail_min"]), int(rc["stop_hit_max_per_day"]), "stop_hit")
                    elif px <= stop * (1 + float(rc["stop_near_pct"]) / 100.0):
                        msg = (f"{asset(p['pair'])} est tout près de ton prix d'arrêt : {fmt_eur(px, 2)} € "
                               f"pour un arrêt à {fmt_eur(stop)} € (à {hhmm(now)}). Argent réel, position {pid}. "
                               f"Risk, prépare-toi.")
                        payload = self.risk_payload("stop_near", now, msg, p["pair"], round(px, 6), round(stop, 6), pid,
                                                    source=p.get("source"))
                        risk_try("stop_near:" + pid, payload, 0, float(rc["retry_after_fail_min"]), 1, "stop_near")

            # manual risk zones (only while a real position is open)
            if not stale:
                for z in [z for z in zones if z["bot"] == "risk"]:
                    px = prices.get(z["paire"])
                    if px is None or not hit(z["sens"], px, z["prix"]):
                        continue
                    done = sum(1 for k, v in self.bucket(st, dlv_r, "risk")["keys"].items()
                               if k.startswith("zone:") and v.get("delivered"))
                    if done >= int(rc["manual_zone_max_per_day"]):
                        continue
                    sens_txt = "sous" if z["sens"] == "sous" else "au-dessus de"
                    msg = (f"{asset(z['paire'])} est passé {sens_txt} {fmt_eur(z['prix'])} € "
                           f"({fmt_eur(px, 2)} €) à {hhmm(now)}. Risk, à toi de juger.")
                    payload = self.risk_payload("manual_zone", now, msg, z["paire"], round(px, 6), z["prix"], None,
                                                zone_id=z["id"], paire=z["paire"], prix=round(px, 6), seuil=z["prix"],
                                                sens=z["sens"], heure=now.isoformat(), raison=z["raison"])
                    risk_try("zone:" + z["id"], payload, 0, float(rc["retry_after_fail_min"]), 1, "zone")

        # 5) capital réel (live_equity.json) — every ~5 min; rings 12/15 & 6/8 if eligible
        daily_loss, dd = None, None
        try:
            eq = self.equity.maybe_update(now, prices, now_mono=now_mono)
        except Exception as e:  # noqa: BLE001
            self.log("ERROR", f"live_equity: {type(e).__name__}: {e}", now)
            eq = self.equity.read() or {}
        if eq.get("stale"):
            self.log_every("eq-stale", 1800, "WARN",
                           "capital réel périmé (revx n'a pas répondu) — pas de sonnerie perte/baisse", now)
        elif self.equity.ring_eligible(positions, today):
            try:
                daily_loss = float(eq.get("perte_jour_pct") or 0) / 100.0
            except (TypeError, ValueError):
                daily_loss = 0.0
            raw_dd = eq.get("baisse_depuis_plus_haut_pct")
            try:
                dd = None if raw_dd is None else float(raw_dd) / 100.0
            except (TypeError, ValueError):
                dd = None
            for kind, val, levels, label in (
                ("daily_loss", daily_loss, rc["daily_loss_levels"], "perte du jour"),
                ("drawdown", dd, rc["drawdown_levels"], "baisse depuis le plus haut"),
            ):
                if val is None:
                    continue
                crossed = [float(lv) for lv in levels if val >= float(lv)]
                if not crossed:
                    continue
                lvl = max(crossed)
                if any(self.key_state(st, dlv_r, "risk", f"{kind}:{float(h)}")["delivered"]
                       for h in levels if float(h) >= lvl):
                    continue
                limit = max(float(lv) for lv in levels)
                msg = (f"Alerte argent réel : {label} = {val * 100:.1f} % (seuil {lvl * 100:.0f} %"
                       + (", c'est la LIMITE" if lvl >= limit else "")
                       + f") à {hhmm(now)}. Capital réel {eq.get('capital_reel')} €. Risk, regarde maintenant.")
                payload = self.risk_payload(kind, now, msg, value_pct=round(val * 100, 2),
                                            level_pct=round(lvl * 100, 2),
                                            capital_reel=eq.get("capital_reel"))
                risk_try(f"{kind}:{lvl}", payload, 0, float(rc["retry_after_fail_min"]), 1, kind)
        else:
            # still surface metrics for status, but do not ring
            try:
                daily_loss = float(eq.get("perte_jour_pct") or 0) / 100.0 if eq else None
                raw_dd = (eq or {}).get("baisse_depuis_plus_haut_pct")
                dd = None if raw_dd is None else float(raw_dd) / 100.0
            except (TypeError, ValueError):
                pass

        # 6) compound bell — trade fermé (sim or live), once per trade, max N/day
        closed_trades = discover_closed_trades(cfg)
        cst = self.load_compound_state(today, closed_trades)
        cc = self.cfg.get("compound") or {}
        max_c = int(cc.get("max_per_day", 5))
        bilan = str(cc.get("bilan_note") or "reporté au bilan 20h32")
        dlv_c = "real" if modes["compound"]["real"] else "dry"
        for trade in closed_trades:
            key = str(trade.get("key") or "")
            if not key or key in cst["rung"]:
                continue
            if int(cst.get("day_count") or 0) >= max_c:
                self.log("INFO",
                         f"compound: trade {trade.get('decision_id') or key} fermé mais "
                         f"max {max_c}/jour atteint — {bilan}", now)
                cst["rung"][key] = {"at": now.isoformat(), "result": "deferred_bilan",
                                    "decision_id": trade.get("decision_id")}
                self.save_compound_state(cst)
                continue
            payload = self.compound_payload(trade, now)
            r = self.ring("compound", "trade:" + key, payload, st, now, kind_for_log="trade_ferme")
            rings.append({"bot": "compound", "key": "trade:" + key, "result": r})
            if r in ("delivered", "dry"):
                cst["rung"][key] = {"at": now.isoformat(), "result": r,
                                    "decision_id": trade.get("decision_id")}
                cst["day_count"] = int(cst.get("day_count") or 0) + 1
                self.save_compound_state(cst)
            # failed: leave unrung so we retry later (same as other bells)

        # 7) health checks (watcher / Revolut) — Risk bell only
        try:
            health = self.health_check(now, st, rings)
        except Exception as e:  # noqa: BLE001
            self.log("ERROR", f"santé: {type(e).__name__}: {e}", now)
            health = {"erreur": type(e).__name__}

        # 8) alertes de départ — OBSERVATION ONLY (1 batch fetch every ~10 min, never rings)
        try:
            departs_info = self.departs.maybe_check(now, prices if not stale else {})
        except Exception as e:  # noqa: BLE001
            self.log("ERROR", f"départs: {type(e).__name__}: {e}", now)
            departs_info = {"erreur": type(e).__name__}

        # urgent alert file for real stop breaches
        prev = load_json(self.f_urgent, None)
        if breaches:
            data = {"actif": True, "mis_a_jour": now.isoformat(), "breches": breaches,
                    "message_fr": "Prix d'arrêt touché sur une position en ARGENT RÉEL. Risk doit agir (pas de vente auto)."}
            if not (prev or {}).get("actif"):
                data["depuis"] = now.isoformat()
                try:
                    with self.f_urgent_log.open("a", encoding="utf-8") as f:
                        f.write(json.dumps(data, ensure_ascii=False) + "\n")
                except OSError:
                    pass
            else:
                data["depuis"] = prev.get("depuis") or now.isoformat()
            save_json(self.f_urgent, data)
        elif (prev or {}).get("actif") and not stale:
            prev.update(actif=False, fin=now.isoformat(),
                        message_fr="Le prix est repassé au-dessus du prix d'arrêt (ou la position est fermée).")
            save_json(self.f_urgent, prev)

        save_json(self.f_state, st)
        status = {
            "heartbeat": now.isoformat(),
            "pid": os.getpid(),
            "mode": {b: ("réel" if modes[b]["real"] else "dry") for b in BOTS},
            "mode_reason": {b: modes[b]["reason"] for b in BOTS},
            "auth_style": {b: modes[b].get("auth_style") for b in BOTS},
            "last_tick_ts": newest.isoformat() if newest else None,
            "last_tick_age_s": None if age is None else round(age, 1),
            "stale": stale,
            "prices": prices,
            "predict_window_open": win,
            "zones_valid": len(zones),
            "zones_problems": problems,
            "zones_file_error": ferr,
            "zones_distance": zd,
            "night_sans_decision": night.get("sans_decision"),
            "night_sans_decision_detail": night,
            "predict_sans_decision": idle_info,
            "predict_heure_limite": hl_info,
            "predict_mouvement": mv_info,
            "real_positions": [{"id": p.get("id"), "pair": p.get("pair"), "stop": derive_stop(p),
                                "source": p.get("source")} for p in positions],
            "real_positions_without_stop": no_stop,
            "real_sources": pinfo,
            "risk_metrics": {"daily_loss_pct": None if daily_loss is None else round(daily_loss * 100, 2),
                             "drawdown_pct": None if dd is None else round(dd * 100, 2)},
            "live_equity": ({k: eq.get(k) for k in ("capital_reel", "eur_available", "eur_reserved",
                                                    "bot_positions_value", "perte_jour_pct",
                                                    "baisse_depuis_plus_haut_pct", "stale", "plus_haut", "ref_jour")}
                            if eq else None),
            "urgent_active": bool(breaches),
            "sante": health,
            "rings_this_cycle": rings,
            "today": {"date": today,
                      "predict_delivered": {d: (st[d].get("predict") or {}).get("delivered", 0) for d in ("dry", "real")},
                      "risk_delivered": {d: (st[d].get("risk") or {}).get("delivered", 0) for d in ("dry", "real")},
                      "compound_delivered": {d: (st[d].get("compound") or {}).get("delivered", 0) for d in ("dry", "real")},
                      "compound_day_count": int((load_json(self.f_compound, {}) or {}).get("day_count") or 0),
                      "compound_rung_total": len((load_json(self.f_compound, {}) or {}).get("rung") or {})},
            "collector": collector_status(cfg),
            "departs": departs_info,
            "totals": self.ring_totals(),
            "totals_at": now.isoformat(),
        }
        if not status["collector"]["running"]:
            self.log_every("collector", 1800, "WARN",
                           "le collecteur de prix (collect_price_ticks.py) ne tourne pas — à relancer par l'équipe "
                           "(scripts/start_price_ticks.sh); la sonnette ne le démarre pas", now)
        save_json(self.f_status, status)
        return status

    # ---- manual test ring (not counted, no price needed)
    def test_ring(self, bot: str) -> str:
        now = datetime.now(TZ)
        if bot == "risk":
            payload = self.risk_payload("stop_hit", now, TEST_MESSAGE, test=True, zone_id="TEST")
        elif bot == "compound":
            payload = self.compound_payload({
                "key": "TEST", "decision_id": "D-ESSAI", "paire": "SOL-EUR",
                "sens": "Achat", "mode": "simulation", "gain_perte_eur": 0.0,
                "raison_fermeture": "manuel", "position_id": "TEST",
            }, now, test=True)
            # force the word « essai » into the payload (identical spirit to other --test modes)
            payload["message_fr"] = "Essai de la sonnette Compound (trade fermé), rien à faire."
        else:
            payload = {"bot": "predict", "zone_id": "TEST", "paire": None, "prix": None, "seuil": None,
                       "sens": None, "heure": now.isoformat(), "ts": now.isoformat(), "kind": "stop_hit",
                       "mode": "test", "test": True, "message_fr": TEST_MESSAGE}
        return self.ring(bot, "", payload, None, now, count_daily=False, kind_for_log="TEST")


# ----------------------------------------------------------------- status
def print_status(cfg: dict) -> int:
    sd = Path(cfg["state_dir"])
    pid = None
    try:
        pid = int((sd / "sonnette.pid").read_text().strip())
    except Exception:  # noqa: BLE001
        pass
    running = bool(pid and pid_alive(pid))
    s = load_json(sd / "status.json", {}) or {}
    now = datetime.now(TZ)
    print("=== Sonnette — état ===")
    print(f"Processus       : {'EN MARCHE' if running else 'ARRÊTÉ'} (pid {pid if pid else '-'})")
    hb = parse_ts(s.get("heartbeat"))
    if hb:
        ago = int((now - hb).total_seconds())
        print(f"Dernier tour    : {hb.strftime('%H:%M:%S')} (il y a {ago} s)"
              + ("  ⚠ pas de tour récent" if ago > 3 * int(cfg["loop_seconds"]) else ""))
    sec = Secrets(cfg)
    for b in BOTS:
        ch = sec.channel(b)
        print(f"Mode {b:<8}   : {'RÉEL (envoie vraiment)' if ch['real'] else 'DRY (rien n est envoyé)'} — {ch['reason']}")
    lt = parse_ts(s.get("last_tick_ts"))
    if lt:
        age = int((now - lt).total_seconds())
        print(f"Dernier prix    : {lt.strftime('%H:%M:%S')} (il y a {age} s)"
              + (f"  ⚠ PÉRIMÉ (> {cfg['stale_seconds']} s)" if age > cfg["stale_seconds"] else "  OK"))
    else:
        print("Dernier prix    : aucun")
    if s.get("prices"):
        print("Prix            : " + ", ".join(f"{k} {fmt_eur(v, 2)} €" for k, v in s["prices"].items()))
    pc = cfg["predict"]
    print(f"Fenêtre Predict : {'OUVERTE' if s.get('predict_window_open') else 'fermée'} "
          f"({pc['window_start']}-{pc['window_end']}, jours {pc['days']} 0=lundi)")
    print(f"Zones valides   : {s.get('zones_valid', 0)}; ignorées: {len(s.get('zones_problems') or [])}"
          + (f"; FICHIER: {s['zones_file_error']}" if s.get("zones_file_error") else ""))
    for pb in (s.get("zones_problems") or [])[:5]:
        print(f"   - {pb}")
    rp = s.get("real_positions") or []
    src = s.get("real_sources") or {}
    print(f"Positions RÉELLES: {len(rp)}" + (f" → {rp}" if rp else "") + f"  (revx lecture: {src.get('revx', '?')})")
    if s.get("real_positions_without_stop"):
        print(f"   ⚠ sans prix d'arrêt: {s['real_positions_without_stop']}")
    le = load_json(Path(cfg["live_equity_file"]), None)
    if isinstance(le, dict) and le.get("ts"):
        lt2 = parse_ts(le.get("ts"))
        ago2 = int((now - lt2).total_seconds()) if lt2 else -1
        hb_ = le.get("hors_bot") or {}
        hb_txt = ", ".join(f"{a} {v.get('qty')}" for a, v in hb_.items() if isinstance(v, dict))
        print(f"Capital réel    : {le.get('capital_reel')} € (EUR dispo {le.get('eur_available')} + réservé "
              f"{le.get('eur_reserved')} + bot {le.get('bot_positions_value')}) — il y a {ago2} s"
              + ("  ⚠ PÉRIMÉ" if le.get("stale") else ""))
        print(f"   réf. jour {(le.get('ref_jour') or {}).get('valeur')} € → perte {le.get('perte_jour_pct')} %; "
              f"plus-haut {le.get('plus_haut')} → baisse {le.get('baisse_depuis_plus_haut_pct')} %; "
              f"ajustements {len(le.get('ajustements') or [])}")
        print(f"   hors_bot (perso, exclu): {hb_txt}")
    else:
        print("Capital réel    : pas encore calculé")
    t = s.get("today") or {}
    cc = cfg.get("compound") or {}
    print(f"Aujourd'hui     : {t.get('date')} — Predict: {t.get('predict_delivered')} / max {pc['max_per_day']}; "
          f"Risk: {t.get('risk_delivered')}; "
          f"Compound: {t.get('compound_delivered')} / max {cc.get('max_per_day', 5)} "
          f"(jour {t.get('compound_day_count', 0)}, déjà vus {t.get('compound_rung_total', 0)})")
    c = collector_status(cfg)
    print(f"Collecteur prix : {'tourne (pid ' + str(c.get('pid')) + ')' if c.get('running') else '⚠ NE TOURNE PAS (à relancer par l équipe: scripts/start_price_ticks.sh)'}")
    print(f"Alerte urgente  : {'⚠ ACTIVE — voir state/ALERTE_RISK_URGENTE.json' if s.get('urgent_active') else 'non'}")
    zd = s.get("zones_distance") or {}
    for pr, z in sorted((zd.get("paires") or {}).items()):
        d1, d2 = z.get("dessous") or {}, z.get("dessus") or {}
        print(f"Zones à ≤ {zd.get('max_pct')} % : {pr} {'OK' if z.get('ok') else '⚠ ' + str(z.get('probleme'))} "
              f"(dessous {d1.get('ecart_pct', '-')} %, dessus {d2.get('ecart_pct', '-')} %)")
    nd = s.get("night_sans_decision_detail") or {}
    print(f"Nuit dernière   : {nd.get('nuit', '?')} → "
          + ({True: '⚠ NUIT SANS DÉCISION', False: f"{nd.get('decisions')} décision(s)", None: 'inconnu'}
             .get(s.get('night_sans_decision'), 'inconnu')))
    ps = s.get("predict_sans_decision") or {}
    if ps:
        print(f"Sans décision   : {'SONNÉ' if ps.get('sonne') else 'pas de réveil'} — {ps.get('raison', '')}"
              f" (réveils cette nuit: {ps.get('reveils_cette_nuit', 0)})")
    ph = s.get("predict_heure_limite") or {}
    if ph:
        print(f"Heures limites  : {'actif' if ph.get('actif') else 'désactivé'}; en attente: {ph.get('en_attente') or 'aucun'}")
    pm = s.get("predict_mouvement") or {}
    if pm:
        rf = pm.get("reference") or {}
        print(f"Mouvement       : {'actif' if pm.get('actif') else 'désactivé'} — seuil {pm.get('seuil_pct')} %, "
              f"aujourd'hui {pm.get('aujourd_hui', 0)} réveil(s), pas de plafond (à part des zones) ; "
              f"prochain réveil possible à {pm.get('prochain_reveil_possible_fr') or '-'}"
              + (f" — {pm['raison']}" if pm.get("raison") else ""))
        print(f"   référence {rf.get('decision_id', '-')} ({rf.get('source', '-')}) : "
              + ", ".join(f"{asset(p)} {fmt_eur(v, 2)} € → {('%+.2f' % pm['mouvement_pct'][p]).replace('.', ',') + ' %' if (pm.get('mouvement_pct') or {}).get(p) is not None else '?'}"
                          for p, v in (rf.get("prix") or {}).items()))
    rep_ = (s.get("sante") or {}).get("reprise") if isinstance(s.get("sante"), dict) else None
    if rep_:
        print(f"Reprise machine : {rep_}")
    hc = cfg["health"]
    hs = load_json(sd / "sante.json", {}) or {}
    wb = read_heartbeat(Path(cfg["watch_heartbeat"]), now)
    try:
        own_open = open_positions_any(cfg)
    except Exception:  # noqa: BLE001
        own_open = []
    absent_since = parse_ts(((hs.get("_absent") or {}) if isinstance(hs.get("_absent"), dict) else {}).get("watch_heartbeat"))
    if not wb["exists"] and own_open:
        depuis = f" depuis {fmt_age_fr((now - absent_since).total_seconds())}" if absent_since else ""
        print(f"Surveillant     : ⚠ fichier absent{depuis} avec {len(own_open)} position(s) ouverte(s) "
              f"→ watcher_down après {fmt_age_fr(hc.get('watcher_missing_grace_s', hc['watcher_stale_s']))}"
              + ("  (alerte watcher_down active)" if (hs.get('watcher_down') or {}).get('actif') else ""))
    elif not wb["exists"] or wb["error"]:
        print(f"Surveillant     : {'fichier absent, aucune position ouverte' if not wb['exists'] else wb['error']} (pas de contrôle)")
    else:
        d = wb["data"]
        pid = _int0(d.get("pid"))
        alive = (not pid) or pid_alive(pid)
        ok = alive and wb["age_s"] is not None and wb["age_s"] <= hc["watcher_stale_s"]
        print(f"Surveillant     : dernier signe il y a {fmt_age_fr(wb['age_s'])}, pid {pid or '-'} "
              f"{'vivant' if alive else 'ABSENT'}, live {d.get('open_live')} / sim {d.get('open_paper')} — "
              f"{'OK' if ok else '⚠ en panne'}" + ("  (alerte watcher_down active)" if (hs.get('watcher_down') or {}).get('actif') else ""))
    rb = read_heartbeat(Path(cfg["revolut_heartbeat"]), now)
    if not rb["exists"] or rb["error"]:
        print(f"Revolut (test)  : {'fichier absent' if not rb['exists'] else rb['error']} (pas de contrôle)")
    else:
        d = rb["data"]
        ok = (d.get("ok") is not False or _int0(d.get("consecutive_failures")) < hc["revolut_min_failures"]) \
            and rb["age_s"] is not None and rb["age_s"] <= hc["revolut_stale_s"]
        print(f"Revolut (test)  : dernier test il y a {fmt_age_fr(rb['age_s'])}, ok={d.get('ok')}, "
              f"échecs de suite {d.get('consecutive_failures')} — {'OK' if ok else '⚠ en panne'}"
              + ("  (alerte revolut_down active)" if (hs.get('revolut_down') or {}).get('actif') else ""))
    dc = cfg.get("departs") or {}
    di = s.get("departs") or {}
    if dc.get("actif", True):
        lv = parse_ts(di.get("derniere_verif"))
        print(f"Départs (obs.)  : mode {dc.get('mode', 'observe')} (aucune sonnerie), vérif toutes les "
              f"{int(float(dc.get('verif_toutes_s', 600)) // 60)} min"
              + (f", dernière {lv.strftime('%H:%M')}" if lv else "")
              + (f"  ⚠ {di['etat']}" if di.get("etat") else ""))
        try:
            print(f"   {departs.summary_line(sd)}   (détail: python3 sonnette.py --departs)")
        except Exception as e:  # noqa: BLE001
            print(f"   résumé illisible: {type(e).__name__}")
    else:
        print("Départs (obs.)  : désactivé (departs.actif=false)")
    if (sd / "PRIX_PERIMES.flag").exists():
        print("Drapeau         : ⚠ PRIX_PERIMES.flag présent")
    rings = tail_lines(sd / "rings.jsonl", 20000)[-5:]
    print("Dernières sonneries:" if rings else "Dernières sonneries: aucune")
    for line in rings:
        try:
            r = json.loads(line)
            print(f"   {r['at'][:19]} {r['bot']:<7} {r['result']:<9} {r['payload'].get('message_fr')}")
        except Exception:  # noqa: BLE001
            pass
    return 0


# ----------------------------------------------------------------- main
_STOP = False


def main() -> int:
    ap = argparse.ArgumentParser(description="Sonnette — price-zone doorbell (no AI)")
    ap.add_argument("--config", default=None)
    ap.add_argument("--once", action="store_true", help="one cycle then exit")
    ap.add_argument("--status", action="store_true", help="print human status")
    ap.add_argument("--simulate", action="store_true", help="run self-tests with fake ticks in /tmp")
    ap.add_argument("--test", choices=BOTS, help="send one test ring (test=true)")
    ap.add_argument("--departs", action="store_true", help="summary of the « alertes de départ » (observation)")
    args = ap.parse_args()

    if args.simulate:
        return simulate()
    cfg = load_cfg(args.config)
    if args.status:
        return print_status(cfg)
    if args.departs:
        return departs.print_summary(Path(cfg["state_dir"]))
    s = Sonnette(cfg, quiet=bool(args.test))
    if args.test:
        r = s.test_ring(args.test)
        print({"delivered": f"Test {args.test} livré (HTTP OK).",
               "dry": f"Mode dry ({s.secrets.channel(args.test)['reason']}): rien envoyé — voir state/rings.jsonl.",
               "failed": "Échec d'envoi — voir state/sonnette.log."}[r])
        return 0 if r != "failed" else 1
    if args.once:
        st = s.cycle()
        print(json.dumps({k: st[k] for k in ("mode", "last_tick_age_s", "stale", "rings_this_cycle")}, ensure_ascii=False))
        return 0

    def stop(_sig, _frm):
        global _STOP
        _STOP = True

    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    sf = Path(cfg["secrets_file"])
    if sf.exists() and (sf.stat().st_mode & 0o077):
        s.log("WARN", f"{sf.name} lisible par d'autres — faire: chmod 600 {sf}")
    s.log("INFO", f"démarrage sonnette pid={os.getpid()} (boucle {cfg['loop_seconds']} s)")
    while not _STOP:
        t0 = time.monotonic()
        try:
            s.cycle()
        except Exception as e:  # noqa: BLE001 — never crash the loop
            s.log("ERROR", f"tour en erreur: {type(e).__name__}: {e}")
        while not _STOP and time.monotonic() - t0 < float(cfg["loop_seconds"]):
            time.sleep(0.5)
    s.log("INFO", "arrêt sonnette")
    return 0


# ----------------------------------------------------------------- simulate (self-tests)
def simulate() -> int:
    """Self-tests in /tmp/sonnette_sim with fake ticks/positions. Never touches the real state."""
    import http.server
    import threading

    base = Path("/tmp/sonnette_sim")
    if base.exists():
        shutil.rmtree(base)
    base.mkdir(parents=True)
    results: list[tuple[str, bool]] = []

    def check(name: str, cond, detail: str = "") -> None:
        results.append((name, bool(cond)))
        print(f"  [{'OK ' if cond else 'FAIL'}] {name}" + (f" — {detail}" if detail and not cond else ""))

    def make(sub: str, extra_cfg: dict | None = None, env: dict | None = None,
             balances: dict | None = None) -> Sonnette:
        d = base / sub
        d.mkdir(parents=True)
        (d / "ticks").mkdir()
        # Default fake balances: EUR only (no hors_bot crypto) — never call real revx in tests.
        bal_box = {"b": balances if balances is not None else {
            "EUR": {"available": 100.0, "reserved": 0.0, "staked": 0.0, "total": 100.0}}}
        def _fb():
            if isinstance(bal_box["b"], Exception):
                raise bal_box["b"]
            return bal_box["b"]
        cfg = deep_merge(DEFAULT_CFG, {
            "ticks_dir": str(d / "ticks"), "zones_file": str(d / "zones.json"),
            "live_orders": str(d / "live_orders.jsonl"), "guardian_state": str(d / "gstate.json"),
            "positions_file": str(d / "positions.json"), "collector_pid": str(d / "none.pid"),
            "state_dir": str(d / "state"), "secrets_file": str(d / "secrets.env"),
            "live_equity_file": str(d / "live_equity.json"),
            "live_exits": str(d / "live_exits.json"), "trades_log": str(d / "trades_log.jsonl"),
            "watch_heartbeat": str(d / "watch_hb.json"), "revolut_heartbeat": str(d / "revolut_hb.json"),
            # extra Predict rings: never the real team files in tests (absent → feature quiet)
            "decision_log": str(d / "decision_log.md"), "guardian_config": str(d / "gconfig.json"),
            "team_config": str(d / "team_config.json"),
            "deadline_reminders": str(d / "deadline_reminders.jsonl"),
            "deadline_reminder": str(d / "deadline_reminder.json"),
            "equity_every_s": 0,  # refresh every cycle in tests
            "revx_enabled": False, "http_backoff_s": [0, 0, 0], "proxy": "", "allow_http": True,
            "_fetch_balances": _fb, "_fetch_metamask": lambda: 0.05,  # never a real network read in tests
        })
        if not sub.startswith(("sante", "absent")):
            # Non-health sections (stop_hit, stale_price, …) have open positions without any
            # heartbeat file: neutralise the « fichier absent » rule there so their ring counts stay exact.
            cfg["health"] = dict(cfg["health"], watcher_missing_grace_s=1e12, revolut_missing_grace_s=1e12)
        s = Sonnette(deep_merge(cfg, extra_cfg or {}), env=env or {}, quiet=True)
        s._bal_box = bal_box  # tests mutate balances via s._bal_box["b"] = ...
        return s

    def tick(s: Sonnette, ts: datetime, prices: dict) -> None:
        p = Path(s.cfg["ticks_dir"]) / f"{ts.date().isoformat()}.jsonl"
        with p.open("a") as f:
            for pair, mid in prices.items():
                f.write(json.dumps({"ts": ts.isoformat(), "pair": pair, "mid": mid, "source": "fake"}) + "\n")

    def zones(s: Sonnette, zs: list) -> None:
        Path(s.cfg["zones_file"]).write_text(json.dumps({"zones": zs}, ensure_ascii=False))

    def Z(zid, pair="SOL-EUR", sens="sous", prix=98.0, bot="predict", **kw):
        return dict({"id": zid, "paire": pair, "sens": sens, "prix": prix, "bot": bot, "raison": "test",
                     "expire": "2030-01-01T00:00:00+01:00", "actif": True}, **kw)

    def n(st: dict, bot: str | None = None, result: str | None = None) -> int:
        return sum(1 for r in st["rings_this_cycle"] if (bot is None or r["bot"] == bot)
                   and (result is None or r["result"] == result))

    def keys(st: dict) -> list:
        return sorted(r["key"] for r in st["rings_this_cycle"])

    def last_payload(s: Sonnette) -> dict:
        return json.loads(tail_lines(s.f_rings)[-1])["payload"]

    ALL = {"SOL-EUR": 97.85, "BTC-EUR": 70000, "ETH-EUR": 2200}
    THU = datetime(2026, 10, 8, 14, 30, tzinfo=TZ)  # Thursday
    print("== Predict ==")
    s = make("predict")
    zones(s, [Z("Z-SOL-98")])
    tick(s, THU, ALL)
    check("predict: zone touchée à 14:30 (hors fenêtre) → pas de sonnerie", n(s.cycle(THU, 0)) == 0)
    t = THU.replace(hour=15, minute=41)
    tick(s, t, {"SOL-EUR": 97.85})
    st = s.cycle(t, 1)
    check("predict: 15:41 dans la fenêtre → 1 sonnerie (dry)", n(st, "predict", "dry") == 1)
    p = last_payload(s)
    check("predict: message FR exact", p["message_fr"] == "SOL est passé sous 98 € (97,85 €) à 15h41. Predict, à toi de juger.",
          p["message_fr"])
    check("predict: champs payload bot/zone_id/paire/prix/seuil/sens/heure/message_fr",
          all(k in p for k in ("bot", "zone_id", "paire", "prix", "seuil", "sens", "heure", "message_fr")))
    t2 = t + timedelta(minutes=5)
    tick(s, t2, {"SOL-EUR": 97.0})
    check("predict: même zone 5 min plus tard → pas de 2e sonnerie (1 fois/zone/jour)", n(s.cycle(t2, 2)) == 0)
    zones(s, [Z("Z-SOL-98"), Z("Z-BTC", "BTC-EUR", "au-dessus", 69000), Z("Z-ETH", "ETH-EUR", "sous", 2300),
              Z("Z-SOL-99", prix=99)])
    t3 = t + timedelta(minutes=10)
    tick(s, t3, ALL)
    st = s.cycle(t3, 3)
    check("predict: 3 nouvelles zones touchées → seulement 2 sonnent (max 3/jour au total)", n(st, "predict") == 2, keys(st))
    t4 = t + timedelta(minutes=20)
    tick(s, t4, ALL)
    st = s.cycle(t4, 4)
    check("predict: après 3 sonneries → plus rien ce jour", n(st) == 0 and st["today"]["predict_delivered"]["dry"] == 3)
    fri = t + timedelta(days=1)
    tick(s, fri, ALL)
    check("predict: lendemain (vendredi 15:41) → compteurs remis à zéro, 3 sonneries", n(s.cycle(fri, 5), "predict") == 3)
    btc = [json.loads(x)["payload"]["message_fr"] for x in tail_lines(s.f_rings) if "Z-BTC" in x][-1]
    check("predict: message 'au-dessus de' + format 70 000,00 €", "BTC est passé au-dessus de 69 000 € (70 000,00 €)" in btc, btc)
    sat = t + timedelta(days=2)
    s2 = make("predict_sat")
    zones(s2, [Z("Z-SOL-98")])
    tick(s2, sat, ALL)
    check("predict: samedi 15:41 → pas de sonnerie (jours de semaine)", n(s2.cycle(sat, 0)) == 0)
    s3 = make("predict_sat_cfg", {"predict": {"days": [0, 1, 2, 3, 4, 5, 6]}})
    zones(s3, [Z("Z-SOL-98")])
    tick(s3, sat, ALL)
    check("predict: samedi autorisé par config → sonne", n(s3.cycle(sat, 0), "predict") == 1)
    t5 = THU.replace(hour=17, minute=0)
    s4 = make("predict_17h")
    zones(s4, [Z("Z-SOL-98")])
    tick(s4, t5, ALL)
    check("predict: 17:00 pile → fenêtre fermée", n(s4.cycle(t5, 0)) == 0)

    print("== Prix périmés ==")
    s = make("stale")
    zones(s, [Z("Z-SOL-98")])
    tick(s, t - timedelta(minutes=4), ALL)
    st = s.cycle(t, 0)
    check("stale: dernier tick il y a 4 min → pas de sonnerie", n(st) == 0)
    check("stale: status.stale=true + fichier PRIX_PERIMES.flag", st["stale"] and s.f_stale.exists())
    check("stale: ligne de log 'PRIX PÉRIMÉS'", "PRIX PÉRIMÉS" in s.f_log.read_text())
    tick(s, t + timedelta(seconds=30), ALL)
    st = s.cycle(t + timedelta(seconds=30), 1)
    check("stale: tick frais revient → drapeau retiré + sonne", (not s.f_stale.exists()) and n(st) == 1)
    s = make("noticks")
    st = s.cycle(t, 0)
    check("stale: aucun fichier de prix → pas de crash, stale", st["stale"] and n(st) == 0)

    print("== Validation des zones ==")
    s = make("validation")
    zones(s, [Z("OK-1"), Z(""), Z("BAD-PAIR", "DOGE-EUR"), Z("BAD-SENS", sens="dessous-ish"),
              Z("BAD-PRIX", prix=-5), Z("BAD-BOT", bot="scan"), Z("OK-1"), "pas un objet",
              Z("EXPIRED", expire="2020-01-01T00:00:00+01:00"), Z("OFF", actif=False),
              Z("BAD-EXP", expire="demain"), Z("COMMA", prix="98,5")])
    tick(s, t, ALL)
    st = s.cycle(t, 0)
    check("validation: seules OK-1 et COMMA ('98,5') valides", st["zones_valid"] == 2, str(st["zones_problems"]))
    check("validation: 9 entrées ignorées avec raison", len(st["zones_problems"]) == 9, str(st["zones_problems"]))
    check("validation: lignes 'zone ignorée' dans le log", s.f_log.read_text().count("zone ignorée") == 9)
    Path(s.cfg["zones_file"]).write_text("{ ceci n'est pas du json")
    st = s.cycle(t + timedelta(seconds=30), 1)
    check("validation: JSON cassé → pas de crash, 0 zone, erreur notée", st["zones_valid"] == 0 and st["zones_file_error"])

    print("== Risk (argent réel) ==")
    SUN = datetime(2026, 10, 11, 3, 0, tzinfo=TZ)  # Sunday 03:00
    s = make("risk")
    Path(s.cfg["live_orders"]).write_text("\n".join(json.dumps(r) for r in [
        {"ok": True, "at": "2026-10-10T10:00:00+02:00",
         "order": {"pair": "SOL-EUR", "side": "buy", "price": 100.0, "amount_eur": 10, "stop_price_eur": 95.0}},
        {"ok": True, "dry_run": True, "order": {"pair": "BTC-EUR", "side": "buy", "price": 70000, "amount_eur": 10, "stop_pct": -1}},
        {"ok": False, "order": {"pair": "ETH-EUR", "side": "buy", "price": 2300, "amount_eur": 10, "stop_pct": -1}},
    ]) + "\n")
    save_json(Path(s.cfg["guardian_state"]), {"bankroll_eur": 500, "daily_pnl_eur": 0, "positions": [
        {"id": "rx-paper-1", "pair": "ETH-EUR", "side": "long", "avg_price": 2500, "stop_price_eur": 2400, "status": "open"}]})
    tick(s, SUN, {"SOL-EUR": 96.5, "BTC-EUR": 60000, "ETH-EUR": 2000})
    st = s.cycle(SUN, 0)
    check("risk: 1 position réelle (lignes dry_run / ok=false / paper ignorées)",
          [p["pair"] for p in st["real_positions"]] == ["SOL-EUR"], str(st["real_positions"]))
    check("risk: SOL 96,5 (1,6 % au-dessus du stop) + ETH SIM sous son stop → aucune sonnerie", n(st) == 0)
    tt = SUN + timedelta(minutes=1)
    tick(s, tt, {"SOL-EUR": 95.5})
    st = s.cycle(tt, 1)
    check("risk: SOL 95,5 (0,5 % au-dessus du stop 95) → stop_near",
          len(st["rings_this_cycle"]) == 1 and keys(st)[0].startswith("stop_near:"), keys(st))
    tt = SUN + timedelta(minutes=2)
    tick(s, tt, {"SOL-EUR": 95.4})
    check("risk: stop_near pas répété", n(s.cycle(tt, 2)) == 0)
    tt = SUN + timedelta(minutes=3)
    tick(s, tt, {"SOL-EUR": 94.8})
    st = s.cycle(tt, 3)
    check("risk: dimanche 03:03 SOL 94,8 ≤ stop 95 → sonne tout de suite", n(st, "risk") == 1 and keys(st)[0].startswith("stop_hit:"))
    p = last_payload(s)
    check("risk: payload Risk (mode, pair, price, stop, position_id, kind, message_fr, ts, test)",
          all(k in p for k in ("mode", "pair", "price", "stop", "position_id", "kind", "message_fr", "ts", "test"))
          and p["kind"] == "stop_hit" and p["mode"] == "live" and p["test"] is False and p["stop"] == 95.0, str(p))
    check("risk: fichier ALERTE_RISK_URGENTE.json actif", (load_json(s.f_urgent, {}) or {}).get("actif") is True)
    sent = 1
    for i, mins in enumerate([5, 9, 13, 14, 23, 33, 43, 53, 63, 73, 83]):
        tt = SUN + timedelta(minutes=3 + mins)
        tick(s, tt, {"SOL-EUR": 94.0})
        sent += n(s.cycle(tt, 10 + i), "risk")
        if mins == 9:
            check("risk: pas de rappel avant 10 min", sent == 1)
        if mins == 13:
            check("risk: rappel après 10 min", sent == 2)
    check("risk: max 6 sonneries stop_hit/jour", sent == 6, f"sent={sent}")
    tt = SUN + timedelta(minutes=100)
    tick(s, tt, {"SOL-EUR": 99.0})
    s.cycle(tt, 100)
    check("risk: prix remonte → alerte urgente passée à actif=false", (load_json(s.f_urgent, {}) or {}).get("actif") is False)

    s = make("risk_closed")
    Path(s.cfg["live_orders"]).write_text("\n".join(json.dumps(r) for r in [
        {"ok": True, "order": {"pair": "SOL-EUR", "side": "buy", "price": 100, "amount_eur": 10, "stop_pct": -5}},
        {"ok": True, "order": {"pair": "SOL-EUR", "side": "sell", "price": 101, "amount_eur": 10}}]) + "\n")
    tick(s, SUN, {"SOL-EUR": 90.0})
    st = s.cycle(SUN, 0)
    check("risk: achat puis vente (position fermée) → aucune sonnerie", n(st) == 0 and not st["real_positions"])

    s = make("risk_sim_only")
    save_json(Path(s.cfg["guardian_state"]), {"bankroll_eur": 100, "daily_pnl_eur": -20, "positions": [
        {"id": "x1", "pair": "SOL-EUR", "side": "long", "stop_price_eur": 95, "status": "open", "mode": "sim"}]})
    zones(s, [Z("R-1", bot="risk")])
    tick(s, SUN, {"SOL-EUR": 90.0})
    check("risk: seulement position SIM (sous stop, perte 20 %, zone risk) → aucune sonnerie", n(s.cycle(SUN, 0)) == 0)

    s = make("risk_levels", balances={
        "EUR": {"available": 90.0, "reserved": 0.0, "staked": 0.0, "total": 90.0},
        "BTC": {"available": 0.001, "reserved": 0.0, "staked": 0.0, "total": 0.001},
        "ETH": {"available": 0.0, "reserved": 0.0, "staked": 0.0, "total": 0.0},
        "SOL": {"available": 0.0, "reserved": 0.0, "staked": 0.0, "total": 0.0},
    })
    Path(s.cfg["live_orders"]).write_text(json.dumps({
        "ok": True, "at": SUN.isoformat(),
        "order": {"id": "abc", "pair": "BTC-EUR", "side": "buy", "price": 10000,
                  "amount_eur": 10, "qty": 0.001, "stop_price_eur": 2000}}) + "\n")
    save_json(Path(s.cfg["live_equity_file"]), {
        "hors_bot": {"BTC": {"qty": 0.0}, "ETH": {"qty": 0.0}, "SOL": {"qty": 0.0}},
        "_track": {"hors_bot_locked": True, "first_real_buy_at": SUN.isoformat(),
                   "eur_prev": 90.0, "bot_orders_sig": "bootstrap",
                   "bot_qty": {"BTC": 0.001, "ETH": 0.0, "SOL": 0.0}},
        "ref_jour": {"date": SUN.date().isoformat(), "valeur": 100.0},
        "plus_haut": 100.0, "ajustements": [], "stale": False,
    })
    zones(s, [Z("R-ETH", "ETH-EUR", "sous", 2100, bot="risk")])
    # EUR 90→80 (with bot sig change → no deposit adj); BTC @ 7500 → capital 87.5 = −12.5%
    s._bal_box["b"]["EUR"]["available"] = s._bal_box["b"]["EUR"]["total"] = 80.0
    tick(s, SUN, {"BTC-EUR": 7500.0, "ETH-EUR": 2000.0})
    st = s.cycle(SUN, 0)
    check("risk: perte 12,5 % + drawdown (saut direct au seuil 8 %) + zone manuelle → 3 sonneries",
          keys(st) == ["daily_loss:0.12", "drawdown:0.08", "zone:R-ETH"], keys(st))
    tt = SUN + timedelta(minutes=1)
    tick(s, tt, {"BTC-EUR": 7500.0, "ETH-EUR": 2000.0})
    check("risk: niveaux pas répétés", n(s.cycle(tt, 1)) == 0)
    # BTC @ 5000 → capital 85 = −15% / −15% dd
    tt = SUN + timedelta(minutes=2)
    tick(s, tt, {"BTC-EUR": 5000.0, "ETH-EUR": 2000.0})
    st = s.cycle(tt, 2)
    check("risk: perte 15 % → re-sonne daily_loss 15 (drawdown 8 % déjà sonné)",
          keys(st) == ["daily_loss:0.15"], keys(st))
    tt = SUN + timedelta(minutes=3)
    tick(s, tt, {"BTC-EUR": 1500.0, "ETH-EUR": 2000.0})
    st = s.cycle(tt, 3)
    check("risk: prix ≤ stop_price_eur 2000 → stop_hit",
          any(k.startswith("stop_hit:") for k in keys(st)), keys(st))

    s = make("risk_stale")
    save_json(Path(s.cfg["guardian_state"]), {"positions": [
        {"id": "rx-live-1", "pair": "SOL-EUR", "side": "long", "stop_price_eur": 95, "status": "open"}]})
    tick(s, SUN, {"SOL-EUR": 90.0})
    check("risk: tick vieux de 5 min, prix sous stop → rien (périmé, et < 10 min)", n(s.cycle(SUN + timedelta(minutes=5), 0)) == 0)
    check("risk: tick vieux de 11 min → stale_price", keys(s.cycle(SUN + timedelta(minutes=11), 1)) == ["stale_price"])
    check("risk: stale_price pas répété avant 30 min", n(s.cycle(SUN + timedelta(minutes=30), 2)) == 0)
    check("risk: stale_price répété après 30 min", n(s.cycle(SUN + timedelta(minutes=42), 3)) == 1)
    s = make("risk_stale_nopos")
    tick(s, SUN, {"SOL-EUR": 90.0})
    check("risk: prix périmés sans position réelle → aucune sonnerie", n(s.cycle(SUN + timedelta(hours=1), 0)) == 0)

    print("== Capital réel (live_equity) ==")
    def B(eur, btc=0.0, eth=0.0, sol=0.0, reserved=0.0):
        return {"EUR": {"available": eur, "reserved": reserved, "staked": 0.0, "total": eur + reserved},
                "BTC": {"available": btc, "reserved": 0.0, "staked": 0.0, "total": btc},
                "ETH": {"available": eth, "reserved": 0.0, "staked": 0.0, "total": eth},
                "SOL": {"available": sol, "reserved": 0.0, "staked": 0.0, "total": sol}}
    PX = {"BTC-EUR": 70000.0, "ETH-EUR": 2200.0, "SOL-EUR": 100.0}
    MON = datetime(2026, 10, 12, 10, 0, tzinfo=TZ)

    # baseline hors_bot + no real buy → no drawdown/peak, no ring even on big loss
    s = make("eq_baseline", balances=B(165.71, btc=0.0000066, eth=0.0309, sol=0.342))
    tick(s, MON, PX)
    s.cycle(MON, 0)
    eq = load_json(Path(s.cfg["live_equity_file"]), {})
    check("equity: hors_bot = crypto déjà détenu (ETH 0,0309 / SOL 0,342 / BTC 0,0000066)",
          abs(eq["hors_bot"]["ETH"]["qty"] - 0.0309) < 1e-9 and abs(eq["hors_bot"]["SOL"]["qty"] - 0.342) < 1e-9
          and abs(eq["hors_bot"]["BTC"]["qty"] - 0.0000066) < 1e-12, str(eq.get("hors_bot")))
    check("equity: capital_reel = EUR seulement (crypto perso exclu), plus_haut=null sans achat bot",
          abs(eq["capital_reel"] - 165.71) < 1e-6 and eq["bot_positions_value"] == 0 and eq["plus_haut"] is None,
          str({k: eq.get(k) for k in ("capital_reel", "bot_positions_value", "plus_haut")}))
    check("equity: champs requis présents",
          all(k in eq for k in ("ts", "eur_available", "eur_reserved", "bot_positions_value", "capital_reel",
                                "hors_bot", "ref_jour", "plus_haut", "perte_jour_pct",
                                "baisse_depuis_plus_haut_pct", "ajustements", "stale", "notes_fr")))
    # personal crypto price crash doesn't change capital
    t1 = MON + timedelta(minutes=5)
    tick(s, t1, {"BTC-EUR": 35000.0, "ETH-EUR": 1100.0, "SOL-EUR": 50.0})
    s.cycle(t1, 1)
    eq = load_json(Path(s.cfg["live_equity_file"]), {})
    check("equity: chute du crypto perso → capital inchangé, perte 0 %", eq["perte_jour_pct"] == 0.0, str(eq["perte_jour_pct"]))

    # deposit shift: EUR +50 without bot order → ref & peak shifted, logged, no gain/loss
    s = make("eq_deposit", balances=B(100.0))
    Path(s.cfg["live_orders"]).write_text(json.dumps({"ok": True, "at": (MON - timedelta(days=2)).isoformat(),
        "order": {"pair": "SOL-EUR", "side": "buy", "price": 100, "amount_eur": 10, "stop_price_eur": 50}}) + "\n")
    tick(s, MON, PX)
    s.cycle(MON, 0)
    eq0 = load_json(Path(s.cfg["live_equity_file"]), {})
    s._bal_box["b"] = B(150.0)
    t1 = MON + timedelta(minutes=5)
    tick(s, t1, PX)
    s.cycle(t1, 1)
    eq = load_json(Path(s.cfg["live_equity_file"]), {})
    check("equity: dépôt +50 € → ref_jour et plus_haut décalés de +50",
          abs(eq["ref_jour"]["valeur"] - (eq0["ref_jour"]["valeur"] + 50)) < 1e-6
          and abs(eq["plus_haut"] - (eq0["plus_haut"] + 50)) < 1e-6, f"{eq0['ref_jour']} → {eq['ref_jour']}, {eq0['plus_haut']}→{eq['plus_haut']}")
    check("equity: dépôt pas compté comme gain/perte (perte 0, baisse 0)",
          eq["perte_jour_pct"] == 0.0 and eq["baisse_depuis_plus_haut_pct"] == 0.0)
    check("equity: ajustement journalisé (fichier + log)",
          len(eq["ajustements"]) == 1 and abs(eq["ajustements"][0]["delta_eur"] - 50) < 1e-6
          and "ajustement +50.00" in s.f_log.read_text())
    # withdrawal −30 → shift down, still no loss
    s._bal_box["b"] = B(120.0)
    t2 = MON + timedelta(minutes=10)
    tick(s, t2, PX)
    s.cycle(t2, 2)
    eq = load_json(Path(s.cfg["live_equity_file"]), {})
    check("equity: retrait −30 € → pas de perte comptée", eq["perte_jour_pct"] == 0.0 and len(eq["ajustements"]) == 2)
    # bot buy fill: EUR −10, SOL +0.1 (bot) → no adjustment
    Path(s.cfg["live_orders"]).write_text(Path(s.cfg["live_orders"]).read_text() + json.dumps({"ok": True,
        "at": t2.isoformat(), "order": {"pair": "SOL-EUR", "side": "buy", "price": 100, "amount_eur": 10}}) + "\n")
    s._bal_box["b"] = B(110.0, sol=0.1)
    t3 = MON + timedelta(minutes=15)
    tick(s, t3, PX)
    s.cycle(t3, 3)
    eq = load_json(Path(s.cfg["live_equity_file"]), {})
    check("equity: achat bot (EUR −10, SOL +0,1) → pas d'ajustement, capital stable",
          len(eq["ajustements"]) == 2 and abs(eq["capital_reel"] - 120.0) < 1e-6, str(eq["capital_reel"]))

    # midnight reset
    s = make("eq_midnight", balances=B(100.0))
    tn = MON.replace(hour=23, minute=30)
    tick(s, tn, PX)
    s.cycle(tn, 0)  # lock hors_bot = 0 crypto, capital=100
    Path(s.cfg["live_orders"]).write_text(json.dumps({"ok": True, "at": tn.isoformat(),
        "order": {"pair": "BTC-EUR", "side": "buy", "price": 70000, "amount_eur": 10, "stop_price_eur": 1}}) + "\n")
    s._bal_box["b"] = B(90.0, btc=10 / 70000)
    tick(s, tn + timedelta(minutes=5), PX)
    s.cycle(tn + timedelta(minutes=5), 1)  # capital still ~100
    tick(s, tn + timedelta(minutes=10), {"BTC-EUR": 35000.0, "ETH-EUR": 2200.0, "SOL-EUR": 100.0})
    s.cycle(tn + timedelta(minutes=10), 2)  # capital ~95, perte 5%
    eq_before = load_json(Path(s.cfg["live_equity_file"]), {})
    tm = MON.replace(hour=0, minute=1) + timedelta(days=1)
    tick(s, tm, {"BTC-EUR": 35000.0, "ETH-EUR": 2200.0, "SOL-EUR": 100.0})
    s.cycle(tm, 3)
    eq = load_json(Path(s.cfg["live_equity_file"]), {})
    check("equity: avant minuit perte > 0", eq_before["perte_jour_pct"] > 0, str(eq_before["perte_jour_pct"]))
    check("equity: après minuit nouvelle ref_jour (date du jour, perte 0 %)",
          eq["ref_jour"]["date"] == tm.date().isoformat() and eq["perte_jour_pct"] == 0.0, str(eq["ref_jour"]))
    check("equity: plus_haut conservé à travers minuit (baisse > 0)", (eq["baisse_depuis_plus_haut_pct"] or 0) > 0)

    # no ring when no real buy open/today, even with a big loss; ring 12 then 15 when buy today (closed)
    s = make("eq_noring", balances=B(100.0))
    Path(s.cfg["live_orders"]).write_text("\n".join(json.dumps(r) for r in [
        {"ok": True, "at": (MON - timedelta(days=3)).isoformat(), "order": {"pair": "SOL-EUR", "side": "buy", "price": 100, "amount_eur": 10}},
        {"ok": True, "at": (MON - timedelta(days=2)).isoformat(), "order": {"pair": "SOL-EUR", "side": "sell", "price": 100, "amount_eur": 10}},
    ]) + "\n")
    tick(s, MON, PX)
    s.cycle(MON, 0)
    # simulate a loss not explained as deposit: change sig so it's "bot activity" (e.g. an old sell recorded late)
    eqf = Path(s.cfg["live_equity_file"])
    d = load_json(eqf, {}); d["_track"]["bot_orders_sig"] = "x"; save_json(eqf, d)
    s._bal_box["b"] = B(85.0)
    t1 = MON + timedelta(minutes=5)
    tick(s, t1, PX)
    st = s.cycle(t1, 1)
    eq = load_json(eqf, {})
    check("equity: perte 15 % mais aucun achat réel ouvert ni aujourd'hui → aucune sonnerie",
          eq["perte_jour_pct"] >= 15 - 1e-6 and not any(k.startswith(("daily_loss", "drawdown")) for k in keys(st)),
          f"{eq['perte_jour_pct']} {keys(st)}")
    s = make("eq_ring_today", balances=B(100.0))
    lo = Path(s.cfg["live_orders"])
    lo.write_text("\n".join(json.dumps(r) for r in [
        {"ok": True, "at": (MON - timedelta(hours=1)).isoformat(), "order": {"pair": "SOL-EUR", "side": "buy", "price": 100, "amount_eur": 10}},
        {"ok": True, "at": (MON - timedelta(minutes=30)).isoformat(), "order": {"pair": "SOL-EUR", "side": "sell", "price": 100, "amount_eur": 10}},
    ]) + "\n")
    tick(s, MON, PX)
    s.cycle(MON, 0)
    eqf = Path(s.cfg["live_equity_file"])
    def lose(new_eur, tt, mono):
        d = load_json(eqf, {}); d["_track"]["bot_orders_sig"] = "x" + str(mono); save_json(eqf, d)
        s._bal_box["b"] = B(new_eur)
        tick(s, tt, PX)
        return s.cycle(tt, mono)
    st = lose(88.0, MON + timedelta(minutes=5), 1)
    check("equity: achat réel fait aujourd'hui (fermé) + perte 12 % → sonne daily_loss 12",
          "daily_loss:0.12" in keys(st), keys(st))
    st = lose(87.0, MON + timedelta(minutes=10), 2)
    check("equity: perte 13 % → pas de re-sonnerie", not any(k.startswith("daily_loss") for k in keys(st)), keys(st))
    st = lose(85.0, MON + timedelta(minutes=15), 3)
    check("equity: perte 15 % → re-sonne daily_loss 15 (limite)", "daily_loss:0.15" in keys(st), keys(st))
    p_ = last_payload(s)
    check("equity: payload Risk kind=daily_loss avec capital_reel", p_.get("kind") in ("daily_loss", "drawdown")
          and "capital_reel" in p_, str(p_))

    # revx failure → keep last values, stale, no equity ring, log
    s = make("eq_revx_fail", balances=B(100.0))
    Path(s.cfg["live_orders"]).write_text(json.dumps({"ok": True, "at": MON.isoformat(),
        "order": {"pair": "SOL-EUR", "side": "buy", "price": 100, "amount_eur": 10, "stop_price_eur": 1}}) + "\n")
    tick(s, MON, PX)
    s.cycle(MON, 0)
    eqf = Path(s.cfg["live_equity_file"])
    good = load_json(eqf, {})
    s._bal_box["b"] = RuntimeError("revx down")
    d = load_json(eqf, {}); d["perte_jour_pct"] = 20.0; d["baisse_depuis_plus_haut_pct"] = 20.0; save_json(eqf, d)
    t1 = MON + timedelta(minutes=5)
    tick(s, t1, PX)
    st = s.cycle(t1, 1)
    eq = load_json(eqf, {})
    check("equity: revx en panne → stale=true, dernières valeurs gardées",
          eq["stale"] is True and eq["capital_reel"] == good["capital_reel"])
    check("equity: revx en panne → aucune sonnerie perte/baisse (même si 20 % dans le fichier)",
          not any(k.startswith(("daily_loss", "drawdown")) for k in keys(st)), keys(st))
    check("equity: revx en panne → loggé", "lecture revx échouée" in s.f_log.read_text())
    s._bal_box["b"] = B(100.0)
    t2 = MON + timedelta(minutes=10)
    tick(s, t2, PX)
    s.cycle(t2, 2)
    check("equity: revx revient → stale=false", load_json(eqf, {})["stale"] is False)
    s = make("eq_first_fail", balances=RuntimeError("down"))
    tick(s, MON, PX)
    st = s.cycle(MON, 0)
    eq = load_json(Path(s.cfg["live_equity_file"]), {})
    check("equity: revx en panne dès le départ → fichier stale sans valeurs, pas de crash",
          eq.get("stale") is True and eq.get("capital_reel") is None)

    print("== Vue complète de l'argent réel (soldes détaillés, MetaMask, total) ==")
    bal_v = B(165.71, btc=0.0000066, eth=0.0309, sol=0.342, reserved=4.0)
    bal_v["SOL"].update(available=0.142, staked=0.2, total=0.342)
    s = make("eq_vue", balances=bal_v)
    tick(s, MON, PX)
    s.cycle(MON, 0)
    eq = load_json(Path(s.cfg["live_equity_file"]), {})
    sx = eq.get("soldes_revolut_x") or {}
    check("vue: split disponible / staké / réservé écrit (SOL 0,142 + 0,2 staké ; EUR 4 réservé)",
          sx.get("SOL", {}).get("disponible") == 0.142 and sx["SOL"]["stake"] == 0.2 and sx["SOL"]["total"] == 0.342
          and sx.get("EUR", {}).get("reserve") == 4.0 and sx["EUR"]["eur"] == 169.71, str(sx))
    check("vue: MetaMask ETH + valeur € (prix du collecteur)",
          (eq.get("metamask") or {}).get("eth") == 0.05 and eq["metamask"]["eur"] == 110.0, str(eq.get("metamask")))
    want = round(169.71 + 0.0000066 * 70000 + 0.0309 * 2200 + 0.342 * 100 + 110.0, 4)
    check("vue: total réel = Revolut X (EUR + toutes pièces) + MetaMask, complet",
          abs(eq.get("total_reel_eur", 0) - want) < 1e-3 and eq.get("total_reel_complet") is True, f"{eq.get('total_reel_eur')} ≠ {want}")
    s2 = make("eq_vue_mmfail", balances=B(10.0), extra_cfg={"_fetch_metamask": lambda: (_ for _ in ()).throw(RuntimeError("rpc"))})
    tick(s2, MON, PX)
    s2.cycle(MON, 0)
    eq2 = load_json(Path(s2.cfg["live_equity_file"]), {})
    check("vue: MetaMask illisible sans valeur précédente → metamask=null, total = Revolut X seul",
          eq2.get("metamask") is None and eq2.get("total_reel_eur") == 10.0, str({k: eq2.get(k) for k in ("metamask", "total_reel_eur")}))

    print("== Totaux des sonneries (status.json → totals) ==")
    s = make("totaux")
    s.test_ring("predict"); s.test_ring("risk")
    st_t = load_json(s.f_status, {}) or {}
    tt = st_t.get("totals") or {}
    check("totaux: écrits à chaque sonnerie (2 essais dry, 0 vrai)",
          tt.get("predict", {}).get("essais") == 1 and tt.get("risk", {}).get("essais") == 1 and tt["predict"]["vrais"] == 0
          and tt["predict"]["essais_par_resultat"]["dry"] == 1 and tt["predict"]["dernier_vrai"] is None, str(tt.get("predict")))
    zones(s, [Z("zt1", prix=98.0)])
    tick(s, THU, ALL)
    s.cycle(THU, 0)
    tick(s, THU.replace(hour=15, minute=41), {"SOL-EUR": 97.85})
    s.cycle(THU.replace(hour=15, minute=41), 1)
    tt = (load_json(s.f_status, {}) or {}).get("totals") or {}
    check("totaux: un vrai réveil compté avec son dernier_vrai",
          tt.get("predict", {}).get("vrais") == 1 and (tt["predict"].get("dernier_vrai") or {}).get("zone_id") == "zt1"
          and tt["predict"]["essais"] == 1, str(tt.get("predict")))

    print("== Dry / réel / test ==")
    s = make("dry")
    check("dry: sans secrets → mode dry pour les 2 bots",
          not s.secrets.channel("predict")["real"] and not s.secrets.channel("risk")["real"])
    check("dry: --test risk → 'dry' (rien envoyé)", s.test_ring("risk") == "dry")
    p = last_payload(s)
    check("dry: payload test (test=true, kind=stop_hit, mode=test, message d'essai)",
          p["test"] is True and p["kind"] == "stop_hit" and p["mode"] == "test" and p["message_fr"] == TEST_MESSAGE)
    check("dry: --test predict → 'dry'", s.test_ring("predict") == "dry")
    check("dry: test non compté dans les compteurs du jour", not (load_json(s.f_state, None) or {}).get("dry"))

    received: list = []
    behaviour = {"fail": 0}

    class H(http.server.BaseHTTPRequestHandler):
        def do_POST(self):  # noqa: N802
            body = self.rfile.read(int(self.headers.get("Content-Length", 0)))
            received.append({"path": self.path, "headers": dict(self.headers), "body": json.loads(body)})
            code = 500 if behaviour["fail"] > 0 else 200
            behaviour["fail"] = max(0, behaviour["fail"] - 1)
            self.send_response(code)
            self.end_headers()
            self.wfile.write(b"{}")

        def log_message(self, *a):
            pass

    srv = http.server.HTTPServer(("127.0.0.1", 0), H)
    port = srv.server_address[1]
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    url = f"http://127.0.0.1:{port}/hook/SECRETPATH123"
    s = make("real", env={"SONNETTE_RISK_URL": url, "SONNETTE_RISK_AUTH": "Bearer sk-TESTSECRET-999",
                          "SONNETTE_PREDICT_URL": url, "SONNETTE_PREDICT_KEY": "pk-RAWKEY-777"})
    check("réel: URL + AUTH/KEY → mode réel", s.secrets.channel("risk")["real"] and s.secrets.channel("predict")["real"])
    check("réel: test risk livré (HTTP 200, test=true)", s.test_ring("risk") == "delivered" and received[-1]["body"]["test"] is True)
    check("réel: SONNETTE_RISK_AUTH envoyé tel quel dans Authorization",
          received[-1]["headers"].get("Authorization") == "Bearer sk-TESTSECRET-999")
    s.test_ring("predict")
    check("réel: KEY seule → 'Authorization: Bearer <key>' par défaut",
          received[-1]["headers"].get("Authorization") == "Bearer pk-RAWKEY-777")
    s5 = make("real_hdr", env={"SONNETTE_PREDICT_URL": url, "SONNETTE_PREDICT_KEY": "pk-RAWKEY-777",
                               "SONNETTE_KEY_HEADER": "X-Routine-Key"})
    s5.test_ring("predict")
    check("réel: SONNETTE_KEY_HEADER=X-Routine-Key → clé brute dans X-Routine-Key",
          received[-1]["headers"].get("X-Routine-Key") == "pk-RAWKEY-777")
    s6 = make("real_query", env={"SONNETTE_PREDICT_URL": url, "SONNETTE_PREDICT_KEY": "pk-RAWKEY-777",
                                 "SONNETTE_KEY_MODE": "query", "SONNETTE_KEY_PARAM": "token"})
    s6.test_ring("predict")
    check("réel: KEY_MODE=query → ?token=<key>", received[-1]["path"].endswith("token=pk-RAWKEY-777"))
    zones(s, [Z("Z-SOL-98")])
    t = THU.replace(hour=15, minute=10)
    tick(s, t, ALL)
    before = len(received)
    behaviour["fail"] = 10
    st = s.cycle(t, 0)
    check("réel: webhook en panne (HTTP 500) → 4 essais (1 + 3 retries), résultat failed",
          n(st, "predict", "failed") == 1 and len(received) - before == 4, str(len(received) - before))
    check("réel: échec non compté comme livré", st["today"]["predict_delivered"]["real"] == 0)
    behaviour["fail"] = 0
    tick(s, t + timedelta(minutes=2), ALL)
    check("réel: pas de ré-essai avant 5 min (anti-spam)", n(s.cycle(t + timedelta(minutes=2), 1)) == 0)
    tick(s, t + timedelta(minutes=6), ALL)
    st = s.cycle(t + timedelta(minutes=6), 2)
    check("réel: après 5 min → ré-essai livré et compté",
          n(st, "predict", "delivered") == 1 and st["today"]["predict_delivered"]["real"] == 1)
    srv.shutdown()
    leaks = []
    for sub in ("real", "real_hdr", "real_query"):
        for f in (base / sub / "state").glob("*"):
            txt = f.read_text(errors="ignore")
            if any(x in txt for x in ("SECRETPATH123", "sk-TESTSECRET-999", "pk-RAWKEY-777", f":{port}")):
                leaks.append(str(f))
    check("réel: aucun URL ni clé dans logs / état / status", not leaks, str(leaks))
    s7 = make("http_refused", env={"SONNETTE_RISK_URL": "http://example.com/x", "SONNETTE_RISK_KEY": "k123"},
              extra_cfg={"allow_http": False})
    check("réel: URL non-https refusée → dry", not s7.secrets.channel("risk")["real"])
    s8 = make("forced_dry", env={"SONNETTE_RISK_URL": url, "SONNETTE_RISK_KEY": "k123", "SONNETTE_DRY": "1"})
    check("réel: SONNETTE_DRY=1 force le mode dry", not s8.secrets.channel("risk")["real"])
    sf = base / "secfile"
    sf.mkdir()
    (sf / "secrets.env").write_text("# test\nexport SONNETTE_RISK_URL='https://x.example/hook'\nSONNETTE_RISK_AUTH=\"Bearer abc\"\n")
    sec = Secrets(deep_merge(DEFAULT_CFG, {"secrets_file": str(sf / "secrets.env")}), env={})
    check("secrets: lus depuis secrets.env (risk réel, predict dry)", sec.channel("risk")["real"] and not sec.channel("predict")["real"])

    print("== Santé (watcher_down / revolut_down) ==")
    s = make("sante")
    t0 = datetime(2026, 10, 9, 10, 0, tzinfo=TZ)
    wf, rf = Path(s.cfg["watch_heartbeat"]), Path(s.cfg["revolut_heartbeat"])
    hk = lambda st, k: [r for r in st["rings_this_cycle"] if r["key"] == k]
    tick(s, t0, ALL)
    st = s.cycle(t0, 0)
    check("santé: fichiers absents → aucune sonnerie + log INFO une fois",
          not hk(st, "watcher_down") and not hk(st, "revolut_down")
          and s.f_log.read_text().count("watch_stops_heartbeat") + s.f_log.read_text().count("watch_hb.json") == 1)
    s.cycle(t0 + timedelta(seconds=30), 1)
    check("santé: fichier absent → log pas répété", s.f_log.read_text().count("watch_hb.json") == 1)
    me = os.getpid()
    proc = subprocess.Popen(["true"]); proc.wait(); dead_pid = proc.pid
    wf.write_text(json.dumps({"ts": (t0 - timedelta(minutes=4)).isoformat(), "pid": me, "open_live": 0, "open_paper": 0}))
    st = s.cycle(t0, 2)
    check("santé: heartbeat vieux de 4 min mais aucune position → pas de sonnerie", not hk(st, "watcher_down"))
    wf.write_text(json.dumps({"ts": (t0 - timedelta(minutes=4)).isoformat(), "pid": me, "open_live": 1, "open_paper": 0}))
    st = s.cycle(t0, 3)
    p = last_payload(s)
    check("santé: heartbeat 4 min + 1 trade live → watcher_down (Risk, dry)",
          len(hk(st, "watcher_down")) == 1 and hk(st, "watcher_down")[0]["bot"] == "risk" and p["kind"] == "watcher_down")
    check("santé: message FR simple", p["message_fr"] == "Le surveillant ne donne plus signe de vie depuis 4 min, 1 trade live ouvert.",
          p["message_fr"])
    check("santé: payload open_live/open_paper/heartbeat_age_s/position_ids",
          p["open_live"] == 1 and p["open_paper"] == 0 and p["heartbeat_age_s"] == 240 and "position_ids" in p, str(p))
    st = s.cycle(t0 + timedelta(minutes=10), 4)
    check("santé: toujours en panne 10 min après → pas de 2e sonnerie (< 30 min)", not hk(st, "watcher_down"))
    st = s.cycle(t0 + timedelta(minutes=31), 5)
    check("santé: 31 min après → 2e sonnerie", len(hk(st, "watcher_down")) == 1)
    wf.write_text(json.dumps({"ts": (t0 + timedelta(minutes=32)).isoformat(), "pid": me, "open_live": 1, "open_paper": 0}))
    st = s.cycle(t0 + timedelta(minutes=32), 6)
    check("santé: heartbeat frais → rétabli (log) + pas de sonnerie",
          not hk(st, "watcher_down") and "watcher_down rétabli" in s.f_log.read_text())
    wf.write_text(json.dumps({"ts": (t0 + timedelta(minutes=33)).isoformat(), "pid": dead_pid, "open_live": 0, "open_paper": 2}))
    st = s.cycle(t0 + timedelta(minutes=33), 7)
    p = last_payload(s)
    check("santé: après rétabli, pid mort + 2 trades simulés → re-sonne tout de suite",
          len(hk(st, "watcher_down")) == 1 and "2 trades simulés ouverts" in p["message_fr"] and p["pid_vivant"] is False,
          p.get("message_fr"))
    # own sources: guardian open sim position, heartbeat says 0 → still counts
    Path(s.cfg["guardian_state"]).write_text(json.dumps({"positions": [
        {"id": "rx-paper-D-030-sell", "pair": "ETH-EUR", "status": "open", "mode": "paper",
         "idea_type": "baisse", "decision_id": "D-030"}]}))
    s2 = make("sante_own")
    Path(s2.cfg["guardian_state"]).write_text(Path(s.cfg["guardian_state"]).read_text())
    Path(s2.cfg["watch_heartbeat"]).write_text(json.dumps({"ts": (t0 - timedelta(minutes=5)).isoformat(), "pid": me,
                                                           "open_live": 0, "open_paper": 0}))
    tick(s2, t0, ALL)
    st = s2.cycle(t0, 0)
    p = last_payload(s2)
    check("santé: position ouverte connue via guardian/state.json (heartbeat dit 0) → watcher_down avec id + cycle_id",
          len(hk(st, "watcher_down")) == 1 and p["position_ids"] == ["rx-paper-D-030-sell"]
          and p["cycle_ids"] == ["rx-paper-D-030-sell"], str(p.get("position_ids")))
    # revolut
    rf.write_text(json.dumps({"ts": (t0 + timedelta(minutes=34)).isoformat(), "ok": False, "error": "x" * 300,
                              "consecutive_failures": 1}))
    st = s.cycle(t0 + timedelta(minutes=34), 8)
    check("santé: Revolut 1 échec → pas de sonnerie", not hk(st, "revolut_down"))
    rf.write_text(json.dumps({"ts": (t0 + timedelta(minutes=35)).isoformat(), "ok": False, "error": "x" * 300,
                              "consecutive_failures": 2}))
    st = s.cycle(t0 + timedelta(minutes=35), 9)
    p = [json.loads(x)["payload"] for x in tail_lines(s.f_rings) if '"revolut_down"' in x][-1]
    check("santé: Revolut ok=false 2 échecs → revolut_down, erreur tronquée à 200",
          len(hk(st, "revolut_down")) == 1 and len(p["error"]) == 200 and p["consecutive_failures"] == 2)
    rf.write_text(json.dumps({"ts": (t0 + timedelta(minutes=36)).isoformat(), "ok": True, "error": None,
                              "consecutive_failures": 0}))
    st = s.cycle(t0 + timedelta(minutes=36), 10)
    check("santé: Revolut ok → rétabli", not hk(st, "revolut_down") and "revolut_down rétabli" in s.f_log.read_text())
    st = s.cycle(t0 + timedelta(minutes=49), 11)
    p = last_payload(s)
    check("santé: test Revolut vieux de 13 min → revolut_down",
          len(hk(st, "revolut_down")) == 1 and "13 min" in p["message_fr"], p.get("message_fr"))
    check("santé: jamais d'autre bot que Risk",
          all(json.loads(x)["bot"] == "risk" for x in tail_lines(s.f_rings) if "_down" in x))
    # delivery through a local mock (never the real Risk webhook)
    got: list = []

    class H2(http.server.BaseHTTPRequestHandler):
        def do_POST(self):  # noqa: N802
            got.append(json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0)))))
            self.send_response(200); self.end_headers(); self.wfile.write(b"{}")

        def log_message(self, *a):
            pass
    srv2 = http.server.HTTPServer(("127.0.0.1", 0), H2)
    threading.Thread(target=srv2.serve_forever, daemon=True).start()
    s3 = make("sante_mock", env={"SONNETTE_RISK_URL": f"http://127.0.0.1:{srv2.server_address[1]}/h",
                                 "SONNETTE_RISK_KEY": "k-MOCK-1"})
    Path(s3.cfg["watch_heartbeat"]).write_text(json.dumps({"ts": (t0 - timedelta(minutes=6)).isoformat(),
                                                           "pid": me, "open_live": 1, "open_paper": 0}))
    tick(s3, t0, ALL)
    st = s3.cycle(t0, 0)
    srv2.shutdown()
    check("santé: livré au webhook Risk (mock local) avec kind=watcher_down",
          n(st, "risk", "delivered") == 1 and got and got[-1]["kind"] == "watcher_down" and got[-1]["bot"] == "risk")

    print("== Santé: fichier heartbeat ABSENT + position ouverte ==")
    G1 = {"positions": [{"id": "rx-paper-D-040", "pair": "SOL-EUR", "status": "open", "mode": "paper",
                         "decision_id": "D-040"}]}
    s4 = make("absent_guardian")
    tick(s4, t0, ALL)
    st = s4.cycle(t0, 0)
    st2 = s4.cycle(t0 + timedelta(minutes=10), 1)
    check("absent: aucune position + fichiers absents → silence (pas de watcher_down / revolut_down)",
          not hk(st, "watcher_down") and not hk(st, "revolut_down") and not hk(st2, "watcher_down")
          and not hk(st2, "revolut_down") and not s4.f_rings.exists())
    Path(s4.cfg["guardian_state"]).write_text(json.dumps(G1))
    ta = t0 + timedelta(minutes=11)
    tick(s4, ta, ALL)
    st = s4.cycle(ta, 2)
    check("absent: position ouverte (guardian) + watch_stops_heartbeat absent → pas encore (délai 3 min) + WARN",
          not hk(st, "watcher_down") and "absent alors qu'une position est ouverte" in s4.f_log.read_text()
          and "fichier absent, position ouverte" in str(st.get("sante", {}).get("watcher", st)), str(st.get("sante")))
    st = s4.cycle(ta + timedelta(minutes=2), 3)
    check("absent: 2 min → toujours pas de sonnerie", not hk(st, "watcher_down"))
    st = s4.cycle(ta + timedelta(minutes=3), 4)
    p = last_payload(s4)
    check("absent: position ouverte + watch_stops_heartbeat.json absent 3 min → watcher_down (Risk, dry)",
          len(hk(st, "watcher_down")) == 1 and hk(st, "watcher_down")[0]["bot"] == "risk"
          and hk(st, "watcher_down")[0]["result"] == "dry" and p["kind"] == "watcher_down", str(st["rings_this_cycle"]))
    check("absent: payload heartbeat_absent=true, absent_depuis_s=180, position_ids, mode paper",
          p.get("heartbeat_absent") is True and p.get("absent_depuis_s") == 180
          and p["position_ids"] == ["rx-paper-D-040"] and p["mode"] == "paper" and p["open_paper"] == 1, str(p))
    check("absent: message FR", p["message_fr"] == "Le surveillant ne donne aucun signe de vie (fichier watch_hb.json "
          "absent depuis 3 min), 1 trade simulé ouvert.", p["message_fr"])
    check("absent: surveillant mort → pas de revolut_down en plus (déjà couvert)", not hk(st, "revolut_down"))
    st = s4.cycle(ta + timedelta(minutes=20), 5)
    check("absent: 20 min après → pas de 2e sonnerie (< 30 min)", not hk(st, "watcher_down"))
    st = s4.cycle(ta + timedelta(minutes=34), 6)
    check("absent: 34 min après → 2e sonnerie", len(hk(st, "watcher_down")) == 1)
    # restart: new instance, same state dir → alert memory kept (no immediate re-ring)
    s4b = Sonnette(s4.cfg, env={}, quiet=True)
    st = s4b.cycle(ta + timedelta(minutes=35), 7)
    check("absent: redémarrage sonnette → pas de re-sonnerie (mémoire sante.json)", not hk(st, "watcher_down"))
    Path(s4.cfg["watch_heartbeat"]).write_text(json.dumps({"ts": (ta + timedelta(minutes=36)).isoformat(), "pid": me,
                                                           "open_live": 0, "open_paper": 1}))
    st = s4b.cycle(ta + timedelta(minutes=36), 8)
    check("absent: heartbeat réapparaît (frais) → rétabli (log) + pas de sonnerie",
          not hk(st, "watcher_down") and "watcher_down rétabli" in s4.f_log.read_text())
    # revolut: watcher alive, position open, revolut_heartbeat.json never written
    for i, m in enumerate((37, 45)):
        Path(s4.cfg["watch_heartbeat"]).write_text(json.dumps({"ts": (ta + timedelta(minutes=m)).isoformat(), "pid": me,
                                                               "open_live": 0, "open_paper": 1}))
        st = s4b.cycle(ta + timedelta(minutes=m), 9 + i)
    check("absent: revolut_heartbeat absent 9 min (surveillant vivant) → pas encore", not hk(st, "revolut_down"))
    Path(s4.cfg["watch_heartbeat"]).write_text(json.dumps({"ts": (ta + timedelta(minutes=48)).isoformat(), "pid": me,
                                                           "open_live": 0, "open_paper": 1}))
    st = s4b.cycle(ta + timedelta(minutes=48), 11)
    p = last_payload(s4b)
    check("absent: revolut_heartbeat absent 12 min, surveillant vivant → revolut_down",
          len(hk(st, "revolut_down")) == 1 and p["kind"] == "revolut_down" and p.get("heartbeat_absent") is True
          and not hk(st, "watcher_down"), str(p.get("message_fr")))
    # position closes while files are absent → quiet + rétabli
    os.remove(s4.cfg["watch_heartbeat"])
    Path(s4.cfg["guardian_state"]).write_text(json.dumps({"positions": [dict(G1["positions"][0], status="closed")]}))
    st = s4b.cycle(ta + timedelta(minutes=50), 12)
    st = s4b.cycle(ta + timedelta(minutes=60), 13)
    check("absent: plus de position + fichier absent → silence + revolut_down rétabli",
          not hk(st, "watcher_down") and not hk(st, "revolut_down") and "revolut_down rétabli" in s4.f_log.read_text())

    # live position known only via live_orders.jsonl, heartbeat absent → watcher_down via local mock webhook
    got3: list = []

    class H3(http.server.BaseHTTPRequestHandler):
        def do_POST(self):  # noqa: N802
            got3.append(json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0)))))
            self.send_response(200); self.end_headers(); self.wfile.write(b"{}")

        def log_message(self, *a):
            pass
    srv3 = http.server.HTTPServer(("127.0.0.1", 0), H3)
    threading.Thread(target=srv3.serve_forever, daemon=True).start()
    s5 = make("absent_live_mock", env={"SONNETTE_RISK_URL": f"http://127.0.0.1:{srv3.server_address[1]}/h",
                                       "SONNETTE_RISK_KEY": "k-MOCK-2"})
    Path(s5.cfg["live_orders"]).write_text(json.dumps({"ok": True, "at": t0.isoformat(), "order": {
        "pair": "SOL-EUR", "side": "buy", "price": 100.0, "amount_eur": 10, "stop_price_eur": 90.0}}) + "\n")
    tick(s5, t0, ALL)
    s5.cycle(t0, 0)
    tb = t0 + timedelta(minutes=4)
    tick(s5, tb, ALL)
    st = s5.cycle(tb, 1)
    srv3.shutdown()
    wd3 = [g for g in got3 if g.get("kind") == "watcher_down"]
    check("absent: trade live (live_orders.jsonl) + heartbeat absent → watcher_down livré au mock Risk local",
          len(hk(st, "watcher_down")) == 1 and hk(st, "watcher_down")[0]["result"] == "delivered" and len(wd3) == 1
          and wd3[0]["mode"] == "live" and wd3[0]["open_live"] == 1 and wd3[0]["heartbeat_absent"] is True
          and "1 trade live ouvert" in wd3[0]["message_fr"], str(got3)[:300])

    # ------------------------------------------------------------ alertes de départ (observation)
    print("== Alertes de départ (observation seulement) ==")
    import contextlib
    import io
    IV = 900_000
    DC = dict(departs.DEFAULTS)

    def bars(now: datetime, window: list, base: float = 100.0, base_vol: float = 10.0,
             spike_high: float | None = None, spike_low: float | None = None) -> list:
        """Fake 15m candles: flat bars (neither green nor red), then `window` = [(open, close, vol)],
        then one bar in progress. `start` aligned on 15 min like revx."""
        cur = (int(now.timestamp() * 1000) // IV) * IV
        n_closed = 95
        out = []
        for i in range(n_closed - len(window)):
            st_ = cur - (n_closed - i) * IV
            out.append({"start": st_, "open": base, "close": base, "high": base * 1.0005,
                        "low": base * 0.9995, "volume": base_vol})
        if spike_high is not None:
            out[3]["high"] = spike_high
        if spike_low is not None:
            out[3]["low"] = spike_low
        for j, (o, c, v) in enumerate(window):
            st_ = cur - (len(window) - j) * IV
            out.append({"start": st_, "open": o, "close": c, "high": max(o, c) * 1.0002,
                        "low": min(o, c) * 0.9998, "volume": v})
        last = window[-1][1] if window else base
        out.append({"start": cur, "open": last, "close": last, "high": last, "low": last, "volume": 1.0})
        return [{k: (str(v) if k != "start" else v) for k, v in c.items()} for c in out]  # revx sends strings

    UP = [(100.0, 100.2, 15), (100.2, 100.4, 15), (100.4, 100.6, 15), (100.6, 100.8, 15)]
    DOWN = [(100.0, 99.8, 15), (99.8, 99.6, 15), (99.6, 99.4, 15), (99.4, 99.2, 15)]
    ACC = [(100.0, 100.05, 16), (100.05, 99.98, 16), (99.98, 100.1, 16), (100.1, 100.1, 16)]
    FLAT = [(100.0, 100.0, 10)] * 4
    T0 = datetime(2026, 10, 8, 14, 7, tzinfo=TZ)

    def A(window, **kw):
        return departs.analyse(departs.parse_candles(bars(T0, window, **kw)), T0, DC)["types"]

    m = departs.analyse(departs.parse_candles(bars(T0, UP)), T0, DC)
    check("départs: hausse détectée (+0,8 % en 1h, volume x1,5, près du plus-haut 24h, 4 barres 15m vertes)",
          m["types"] == ["hausse"] and abs(m["variation_pct"] - 0.8) < 1e-6 and abs(m["ratio_volume"] - 1.5) < 1e-6
          and m["distance_haut_24h_pct"] <= 3, str(m))
    check("départs: baisse détectée (miroir: -0,8 %, près du plus-bas 24h, volume x1,5)", A(DOWN) == ["baisse"], str(A(DOWN)))
    check("départs: accumulation détectée (volume x1,6, prix plat +0,1 %)", A(ACC) == ["accumulation"], str(A(ACC)))
    check("départs: pas de hausse si loin du plus-haut 24h (8 % sous 110)", A(UP, spike_high=110.0) == [])
    check("départs: pas de baisse si loin du plus-bas 24h", A(DOWN, spike_low=90.0) == [])
    check("départs: pas de hausse si volume x1,15 (< 1,2)",
          A([(o, c, 11.5) for o, c, _ in UP]) == [])
    check("départs: hausse si volume x1,3 (> 1,2)", A([(o, c, 13) for o, c, _ in UP]) == ["hausse"])
    check("départs: pas de hausse si +0,4 % seulement (≤ 0,5 %)",
          A([(100.0, 100.1, 15), (100.1, 100.2, 15), (100.2, 100.3, 15), (100.3, 100.4, 15)]) == [])
    check("départs: pas de hausse si dernière barre 15m rouge (pas de confirmation)",
          A([(100.0, 100.5, 15), (100.5, 100.7, 15), (100.7, 100.9, 15), (100.9, 100.8, 15)]) == [])
    check("départs: pas de hausse si seulement 2 barres vertes sur 4",
          A([(100.0, 100.5, 15), (100.5, 100.3, 15), (100.3, 100.2, 15), (100.2, 100.8, 15)]) == [])
    check("départs: pas d'accumulation si volume x1,4 (< 1,5)", A([(o, c, 14) for o, c, _ in ACC]) == [])
    check("départs: pas d'accumulation si le prix bouge de 0,35 % (≥ 0,3 %)",
          A([(100.0, 100.1, 16), (100.1, 100.2, 16), (100.2, 100.25, 16), (100.25, 100.35, 16)]) == [])
    check("départs: pas assez de bougies → pas de détection, pas d'erreur fatale",
          departs.analyse(departs.parse_candles(bars(T0, UP))[-6:], T0, DC).get("erreur", "").startswith("pas assez"))

    # --- full cycle with injected fetcher (no network), webhook senders armed to prove nothing rings
    scen = {"SOL-EUR": UP, "BTC-EUR": ACC, "ETH-EUR": FLAT}
    calls: list = []
    sent: list = []

    def fake_fetch(pair, since_ms, interval):
        calls.append((pair, interval, since_ms))
        return {"data": bars(clock["now"], scen[pair])}
    clock = {"now": T0}
    ARMED = {"SONNETTE_PREDICT_URL": "http://127.0.0.1:9/p", "SONNETTE_PREDICT_KEY": "k-dep-1",
             "SONNETTE_RISK_URL": "http://127.0.0.1:9/r", "SONNETTE_RISK_KEY": "k-dep-2",
             "SONNETTE_COMPOUND_URL": "http://127.0.0.1:9/c", "SONNETTE_COMPOUND_KEY": "k-dep-3"}
    sd_ = make("departs", {"_fetch_candles": fake_fetch}, env=ARMED)
    sd_.sender = lambda *a, **k: (sent.append(a[1]), {"ok": True, "status": 200, "error": None, "tries": 1})[1]

    def run(s_, t, prices_):
        clock["now"] = t
        tick(s_, t, prices_)
        return s_.cycle(t, t.timestamp())
    st = run(sd_, T0, {"SOL-EUR": 100.8, "BTC-EUR": 100.1, "ETH-EUR": 100.0})
    det = departs.read_jsonl(sd_.departs.f_det)
    check("départs: 1 vérif = 1 lot de 3 appels bougies (BTC, ETH, SOL en 15m)",
          len(calls) == 3 and sorted(c[0] for c in calls) == sorted(ALLOWED_PAIRS) and all(c[1] == "15m" for c in calls))
    check("départs: SOL hausse + BTC accumulation écrits dans state/departs.jsonl",
          sorted((d["paire"], d["type"]) for d in det) == [("BTC-EUR", "accumulation"), ("SOL-EUR", "hausse")], str(det))
    d0 = next(d for d in det if d["type"] == "hausse")
    check("départs: ligne = ts Bruxelles, paire, type, prix, ratio volume, distances plus-haut/plus-bas 24h",
          d0["ts"] == "2026-10-08T14:07:00+02:00" and d0["paire"] == "SOL-EUR" and d0["prix"] == 100.8
          and d0["ratio_volume"] == 1.5 and isinstance(d0["distance_haut_24h_pct"], float)
          and isinstance(d0["distance_bas_24h_pct"], float) and d0["prix_collecteur"] == 100.8
          and d0["mode"] == "observe" and d0["sonnerie"] is False, str(d0))
    check("départs: OBSERVATION — aucune sonnerie (webhooks armés, 0 envoi, pas de rings.jsonl)",
          not sent and not sd_.f_rings.exists() and n(st) == 0, str(sent)[:200])
    check("départs: statut contient le résumé de la vérif", len(st["departs"]["detections"]) == 2
          and st["departs"]["mode"] == "observe" and st["departs"]["appels_revx"] == 3, str(st.get("departs"))[:300])
    check("départs: log « 1re vérif (données réelles) » écrit", "départs: 1re vérif" in sd_.f_log.read_text())
    st = run(sd_, T0 + timedelta(seconds=30), {"SOL-EUR": 100.8, "BTC-EUR": 100.1, "ETH-EUR": 100.0})
    check("départs: pas de nouvel appel 30 s après (vérif toutes les 10 min, pas toutes les 30 s)", len(calls) == 3)
    st = run(sd_, T0 + timedelta(minutes=10), {"SOL-EUR": 100.8, "BTC-EUR": 100.1, "ETH-EUR": 100.0})
    check("départs: 10 min après → nouveau lot, mêmes signaux ignorés (anti-spam 2 h)",
          len(calls) == 6 and len(departs.read_jsonl(sd_.departs.f_det)) == 2
          and sorted(st["departs"]["anti_spam_ignores"]) == ["BTC-EUR:accumulation", "SOL-EUR:hausse"])
    scen.update({"SOL-EUR": FLAT, "BTC-EUR": FLAT})
    st = run(sd_, T0 + timedelta(minutes=65), {"SOL-EUR": 102.0, "BTC-EUR": 100.5, "ETH-EUR": 100.0})
    res = departs.read_jsonl(sd_.departs.f_res)
    r1 = {(r["paire"], r["horizon"]): r for r in res}
    check("départs: résultat +1h SOL hausse +1,19 % → ça a marché (≥ 1 %, prix collecteur)",
          r1[("SOL-EUR", "1h")]["reussi"] is True and r1[("SOL-EUR", "1h")]["source"] == "collecteur"
          and abs(r1[("SOL-EUR", "1h")]["variation_pct"] - 1.19) < 0.01, str(res))
    check("départs: résultat +1h BTC accumulation +0,4 % → pas marché", r1[("BTC-EUR", "1h")]["reussi"] is False)
    check("départs: pas de résultat +4h/+24h avant l'heure", len(res) == 2)
    st = run(sd_, T0 + timedelta(hours=4, minutes=5), {"SOL-EUR": 100.9, "BTC-EUR": 101.3, "ETH-EUR": 100.0})
    st = run(sd_, T0 + timedelta(hours=24, minutes=5), {"SOL-EUR": 99.0, "BTC-EUR": 98.9, "ETH-EUR": 100.0})
    st = run(sd_, T0 + timedelta(hours=24, minutes=20), {"SOL-EUR": 99.0, "BTC-EUR": 98.9, "ETH-EUR": 100.0})
    res = departs.read_jsonl(sd_.departs.f_res)
    r1 = {(r["paire"], r["horizon"]): r for r in res}
    check("départs: 6 résultats (2 détections × +1h/+4h/+24h), pas de doublon", len(res) == 6
          and len({(r["id"], r["horizon"]) for r in res}) == 6, str(len(res)))
    check("départs: +4h SOL +0,1 % → non ; BTC accumulation +1,2 % → oui",
          r1[("SOL-EUR", "4h")]["reussi"] is False and r1[("BTC-EUR", "4h")]["reussi"] is True)
    check("départs: +24h SOL hausse -1,8 % → non ; BTC accumulation -1,2 % (sortie à la baisse) → oui",
          r1[("SOL-EUR", "24h")]["reussi"] is False and r1[("BTC-EUR", "24h")]["reussi"] is True
          and r1[("BTC-EUR", "24h")]["sens_reel"] == "baisse")
    sm = departs.summary(sd_.sd)
    check("départs: résumé — hausse 1 (0 % à +4h), accumulation 1 (100 % à +4h)",
          sm["par_type"]["hausse"]["detections"] == 1 and sm["par_type"]["hausse"]["4h"]["pct"] == 0.0
          and sm["par_type"]["accumulation"]["4h"]["pct"] == 100.0 and sm["par_type"]["baisse"]["detections"] == 0, str(sm))
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        print_status(sd_.cfg)
    check("départs: ./status.sh affiche la ligne Départs (compte + % à +4h)",
          "Départs (obs.)" in buf.getvalue() and "hausse 1 (à +4h: 0/1 = 0 %)" in buf.getvalue()
          and "accumulation 1 (à +4h: 1/1 = 100 %)" in buf.getvalue(), buf.getvalue()[-600:])
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        departs.print_summary(sd_.sd)
    check("départs: --departs (résumé détaillé) fonctionne", "+4h: 0/1 (0 %)" in buf.getvalue(), buf.getvalue())
    check("départs: toujours aucune sonnerie après 24 h de suivi", not sent and not sd_.f_rings.exists())

    # --- anti-spam survives a restart; mode "ring" not wired → still observe-only
    calls.clear()
    scen.update({"SOL-EUR": UP, "BTC-EUR": FLAT, "ETH-EUR": FLAT})
    s2 = make("departs_spam", {"_fetch_candles": fake_fetch, "departs": {"mode": "ring"}}, env=ARMED)
    s2.sender = sd_.sender
    run(s2, T0, {"SOL-EUR": 100.8})
    s2b = Sonnette(s2.cfg, env=ARMED, quiet=True)
    s2b.sender = sd_.sender
    st = run(s2b, T0 + timedelta(minutes=30), {"SOL-EUR": 100.8})
    check("départs: redémarrage → anti-spam gardé (lu dans departs.jsonl), 1 seule ligne",
          len(departs.read_jsonl(s2.departs.f_det)) == 1 and st["departs"]["anti_spam_ignores"] == ["SOL-EUR:hausse"])
    st = run(s2b, T0 + timedelta(hours=2, minutes=1), {"SOL-EUR": 100.8})
    check("départs: 2 h après → nouvelle détection SOL hausse permise", len(departs.read_jsonl(s2.departs.f_det)) == 2)
    check("départs: mode « ring » → WARN « pas encore branché », toujours aucune sonnerie",
          "pas encore branché" in s2.f_log.read_text() and not sent and not s2.f_rings.exists())

    # --- fetch failure on one pair → WARN, others processed, no crash
    def flaky(pair, since_ms, interval):
        if pair == "ETH-EUR":
            raise RuntimeError("revx candles ETH-EUR: code 1")
        return {"data": bars(clock["now"], UP if pair == "SOL-EUR" else FLAT)}
    s3 = make("departs_flaky", {"_fetch_candles": flaky, "departs": {"reessai_pause_s": 0}})
    st = run(s3, T0, {"SOL-EUR": 100.8})
    check("départs: bougies ETH en erreur → WARN, SOL quand même analysé, pas de crash",
          "ETH-EUR" in st["departs"]["erreurs"] and "bougies ETH-EUR illisibles" in s3.f_log.read_text()
          and len(departs.read_jsonl(s3.departs.f_det)) == 1 and "ERROR" not in s3.f_log.read_text())
    calls.clear()
    fails = {"n": 0}

    def once_flaky(pair, since_ms, interval):
        calls.append(pair)
        if pair == "BTC-EUR" and fails["n"] == 0:
            fails["n"] += 1
            raise RuntimeError("revx candles BTC-EUR: code 1")
        return {"data": bars(clock["now"], FLAT)}
    s3b = make("departs_retry", {"_fetch_candles": once_flaky, "departs": {"reessai_pause_s": 0}})
    st = run(s3b, T0, {"SOL-EUR": 100.0})
    check("départs: un échec passager → 1 seul nouvel essai, puis OK (4 appels, pas d'erreur)",
          len(calls) == 4 and not st["departs"]["erreurs"] and "BTC-EUR" in st["departs"]["paires"], str(calls))

    # --- no candle source (revx disabled in tests) / disabled section
    s4d = make("departs_off")
    st = s4d.cycle(T0, 0)
    check("départs: sans source de bougies (revx désactivé) → inactif, aucun fichier",
          "inactif" in str(st["departs"].get("etat")) and not s4d.departs.f_det.exists())
    s5d = make("departs_disabled", {"_fetch_candles": fake_fetch, "departs": {"actif": False}})
    calls.clear()
    st = s5d.cycle(T0, 0)
    check("départs: departs.actif=false → rien (aucun appel)", st["departs"] == {"actif": False} and not calls)

    # --- outcome fallback on candles, and « manquant » when no price at all
    d6 = base / "departs_out" / "state"
    d6.mkdir(parents=True)
    dep6 = departs.Departs({"departs": {}, "revx_enabled": False}, d6, log=lambda *a, **k: None,
                           ticks_dir=base / "departs_out" / "no_ticks")
    departs.append_jsonl(dep6.f_det, {"id": "DEP-X", "ts": T0.isoformat(), "paire": "ETH-EUR", "type": "baisse",
                                      "prix": 100.0, "prix_collecteur": None})
    tgt = T0 + timedelta(hours=1)
    cs6 = [{"start": int(tgt.timestamp() * 1000) + 60_000, "open": 98.5, "high": 99, "low": 98, "close": 98.7, "volume": 1}]
    out6 = dep6.record_outcomes(T0 + timedelta(hours=1, minutes=20), {"ETH-EUR": cs6}, IV)
    check("départs: pas de tick collecteur → prix pris dans les bougies 15m (baisse -1,5 % → oui)",
          len(out6) == 1 and out6[0]["source"] == "revx bougies" and out6[0]["reussi"] is True, str(out6))
    out6 = dep6.record_outcomes(T0 + timedelta(hours=5), {}, IV)
    check("départs: +4h sans aucun prix, < 3 h après → on attend", out6 == [])
    out6 = dep6.record_outcomes(T0 + timedelta(hours=7, minutes=1), {}, IV)
    check("départs: +4h sans aucun prix, > 3 h après → statut « manquant » (non compté dans les %)",
          len(out6) == 1 and out6[0]["statut"] == "manquant" and out6[0]["reussi"] is None)

    # --- real config.json carries the requested defaults
    real_cfg = json.loads((HERE / "config.json").read_text()).get("departs") or {}
    check("départs: config.json section departs (mode observe, 0,5 % / 3 % / x1,2 / x1,5 / 0,3 %, 2 h)",
          real_cfg.get("mode") == "observe" and real_cfg.get("mouvement_min_pct") == 0.5
          and real_cfg.get("proche_extreme_24h_pct") == 3.0 and real_cfg.get("volume_ratio_min") == 1.2
          and real_cfg.get("accumulation_volume_ratio_min") == 1.5
          and real_cfg.get("accumulation_mouvement_max_pct") == 0.3 and real_cfg.get("anti_spam_heures") == 2,
          str(real_cfg))

    # ================================================================ extra Predict rings (9 oct)
    print("== Predict : sans décision (idle) ==")
    def declog(s_, entries):
        lines = ["# Carnet", "", "### YYYY-MM-DD HH:MM | PAIRE | id-décision (ex. D-001)", "## Entrées", ""]
        lines += [f"### {t.strftime('%Y-%m-%d %H:%M')} | SOL-EUR | {i} — essai" for i, t in entries]
        lines += ["### 2026-10-08 21:30 | ETH-EUR / SOL-EUR | Test du passé — Compound 8 oct (D-013, D-014, D-018)"]
        Path(s_.cfg["decision_log"]).write_text("\n".join(lines) + "\n")

    def gcap(s_, exposure, pct=0.10, bank=500, positions=None):
        Path(s_.cfg["guardian_state"]).write_text(json.dumps({"bankroll_eur": bank, "exposure_eur": exposure,
                                                             "positions": positions or []}))
        Path(s_.cfg["guardian_config"]).write_text(json.dumps({"paper_max_exposure_pct": pct}))

    def ik(st_, prefix):
        return [r for r in st_["rings_this_cycle"] if r["key"].startswith(prefix)]
    FRI = datetime(2026, 10, 9, 15, 0, tzinfo=TZ)
    s = make("idle", {"predict": {"window_start": "00:00", "window_end": "24:00", "days": list(range(7)), "max_per_day": 6}})
    declog(s, [("D-021", datetime(2026, 10, 8, 23, 0, tzinfo=TZ)), ("D-022", FRI - timedelta(hours=5))])
    gcap(s, 14.7)
    tick(s, FRI, ALL)
    st = s.cycle(FRI, 0)
    p = last_payload(s) if s.f_rings.exists() else {}
    check("idle: 5 h sans D-xxx + place sous le plafond → 1 sonnerie Predict (dry)",
          len(ik(st, "idle:")) == 1 and ik(st, "idle:")[0]["result"] == "dry", str(st["rings_this_cycle"]))
    check("idle: message FR demandé", p.get("message_fr", "").startswith(
        "Predict : pas de décision depuis 4 h, propose une simulation ou donne un prix d'entrée avec une nouvelle zone.")
          and "D-022" in p.get("message_fr", "") and "35,30 € sur 50 €" in p.get("message_fr", ""), p.get("message_fr"))
    rec = json.loads(tail_lines(s.f_rings)[-1])
    check("idle: rings.jsonl → kind/raison_type « sans_decision », place 35,30 €",
          rec["payload"]["kind"] == "sans_decision" and rec["payload"]["raison_type"] == "sans_decision"
          and rec["payload"]["place_simulation_eur"] == 35.3, str(rec["payload"]))
    check("idle: compté dans le max Predict du jour", st["today"]["predict_delivered"]["dry"] == 1, str(st["today"]))
    t = FRI + timedelta(minutes=30); tick(s, t, ALL); st = s.cycle(t, 1)
    check("idle: 30 min après → pas de 2e sonnerie (max 1 par 4 h)", not ik(st, "idle:")
          and "déjà réveillé" in str(st["predict_sans_decision"].get("raison")), str(st["predict_sans_decision"]))
    t = FRI + timedelta(hours=4, minutes=1); tick(s, t, ALL); st = s.cycle(t, 2)
    check("idle: 4 h après la 1re → nouvelle sonnerie", len(ik(st, "idle:")) == 1)
    declog(s, [("D-022", FRI - timedelta(hours=5)), ("D-023", t + timedelta(minutes=1))])
    t2 = t + timedelta(minutes=2); tick(s, t2, ALL)
    s._last_cycle = None
    st = s.cycle(t2, 3)
    check("idle: nouvelle décision D-023 → raison « décision récente »",
          not ik(st, "idle:") and "D-023" in str(st["predict_sans_decision"].get("raison")), str(st["predict_sans_decision"]))
    # recent decision / full cap / unreadable cap
    s = make("idle_recent"); declog(s, [("D-030", FRI - timedelta(hours=2))]); gcap(s, 0)
    tick(s, FRI, ALL); st = s.cycle(FRI, 0)
    check("idle: décision il y a 2 h → pas de sonnerie", not ik(st, "idle:"))
    s = make("idle_full"); declog(s, [("D-030", FRI - timedelta(hours=6))]); gcap(s, 47.0)
    tick(s, FRI, ALL); st = s.cycle(FRI, 0)
    check("idle: plafond presque plein (47 € / 50 €, < 5 € de place) → pas de sonnerie, raison « plafond »",
          not ik(st, "idle:") and "plafond" in str(st["predict_sans_decision"].get("raison")), str(st["predict_sans_decision"]))
    s = make("idle_nocfg"); declog(s, [("D-030", FRI - timedelta(hours=6))])
    Path(s.cfg["guardian_state"]).write_text(json.dumps({"bankroll_eur": 500, "exposure_eur": 0}))
    tick(s, FRI, ALL); st = s.cycle(FRI, 0)
    check("idle: guardian/config.json absent → pas de sonnerie (plafond inconnu)",
          not ik(st, "idle:") and "inconnu" in str(st["predict_sans_decision"].get("raison")))
    s = make("idle_nolog"); gcap(s, 0); tick(s, FRI, ALL); st = s.cycle(FRI, 0)
    check("idle: carnet des décisions absent → pas de sonnerie", not ik(st, "idle:"))
    s_p = make("idle_parse"); declog(s_p, [("D-099", FRI)])
    check("idle: carnet lu — seul « ### … | D-099 » compte (modèle et « Test du passé (D-013…) » ignorés)",
          [x["id"] for x in read_decisions(Path(s_p.cfg["decision_log"]))[0]] == ["D-099"])
    # night: max 2 per night, counts per night
    s = make("idle_night", {"predict": {"window_start": "00:00", "window_end": "24:00", "days": list(range(7))}})
    declog(s, [("D-040", datetime(2026, 10, 8, 18, 0, tzinfo=TZ))]); gcap(s, 14.7)
    got = []
    for i, (hh, dd) in enumerate([(22, 8), (23, 8), (2, 9), (3, 9), (6, 9), (8, 9), (9, 9)]):
        tt = datetime(2026, 10, dd, hh, 31, tzinfo=TZ); tick(s, tt, ALL)
        got.append(len(ik(s.cycle(tt, i), "idle:")))
    check("idle: nuit 22h–09h → 22h31 et 02h31 seulement (max 2 par nuit, 1 par 4 h), puis 09h31 de jour",
          got == [1, 0, 1, 0, 0, 0, 1], str(got))
    check("idle: compteur de nuit persistant (predict_extra.json)",
          (load_json(s.f_extra, {}) or {}).get("idle", {}).get("nuits", {}).get("2026-10-08") == 2)
    # daily cap shared with zones
    s = make("idle_cap", {"predict": {"window_start": "00:00", "window_end": "24:00", "days": list(range(7)), "max_per_day": 1}})
    declog(s, [("D-050", FRI - timedelta(hours=6))]); gcap(s, 0); zones(s, [Z("Z-SOL-98")])
    tick(s, FRI, ALL); st = s.cycle(FRI, 0)
    check("idle: zone sonnée au même tour → pas d'idle en plus", len(ik(st, "zone:")) == 1 and not ik(st, "idle:"))
    t = FRI + timedelta(minutes=1); tick(s, t, ALL); st = s.cycle(t, 1)
    check("idle: max Predict du jour atteint (1) → pas de sonnerie, raison « max »",
          not ik(st, "idle:") and "max 1" in str(st["predict_sans_decision"].get("raison")), str(st["predict_sans_decision"]))

    print("== Predict : heure limite ==")
    POS = {"id": "rx-paper-D-060", "pair": "SOL-EUR", "side": "short", "idea_type": "baisse", "status": "open",
           "stop_price": 99.47, "target_price": 96.53, "decision_id": "D-060", "deadline": "2026-10-09T10:00:00+02:00"}
    REM = {"ts": "2026-10-09T10:00:09+02:00", "position_id": "rx-paper-D-060", "pair": "SOL-EUR", "decision_id": "D-060",
           "deadline": "2026-10-09T10:00:00+02:00", "idea_type": "baisse", "action": "rappel_heure_limite"}
    s = make("hl", {"predict": {"window_start": "00:00", "window_end": "24:00", "days": list(range(7))}})
    gcap(s, 14.7, positions=[POS]); declog(s, [("D-060", FRI - timedelta(hours=1))])
    t0 = datetime(2026, 10, 9, 9, 59, tzinfo=TZ); tick(s, t0, {"SOL-EUR": 98.36})
    st = s.cycle(t0, 0)
    check("heure limite: aucun rappel → rien", not ik(st, "heure_limite:"))
    hr = Path(s.cfg["deadline_reminders"])
    hr.write_text(json.dumps(REM) + "\n"); Path(s.cfg["deadline_reminder"]).write_text(json.dumps(REM))
    t1 = datetime(2026, 10, 9, 10, 0, 30, tzinfo=TZ); tick(s, t1, {"SOL-EUR": 98.36})
    st = s.cycle(t1, 1)
    p = last_payload(s)
    check("heure limite: rappel écrit → 1 sonnerie Predict (dry)", len(ik(st, "heure_limite:")) == 1, str(st["rings_this_cycle"]))
    check("heure limite: message avec id du trade, prix actuel, @PM-Risk et 5 minutes",
          "D-060" in p["message_fr"] and "rx-paper-D-060" in p["message_fr"] and "prix actuel 98,36 €" in p["message_fr"]
          and "@PM-Risk" in p["message_fr"] and "dans les 5 minutes" in p["message_fr"] and "arrêt 99,47 €" in p["message_fr"],
          p["message_fr"])
    check("heure limite: payload kind/raison_type « heure_limite », position_id, prix",
          p["kind"] == "heure_limite" and p["raison_type"] == "heure_limite" and p["position_id"] == "rx-paper-D-060"
          and p["prix"] == 98.36, str(p))
    t2 = t1 + timedelta(minutes=1); tick(s, t2, {"SOL-EUR": 98.4}); st = s.cycle(t2, 2)
    check("heure limite: tour suivant → pas de doublon", not ik(st, "heure_limite:"))
    s_b = Sonnette(s.cfg, env={}, quiet=True); tick(s_b, t2 + timedelta(minutes=1), {"SOL-EUR": 98.4})
    st = s_b.cycle(t2 + timedelta(minutes=1), 3)
    check("heure limite: après redémarrage → toujours pas de doublon", not ik(st, "heure_limite:"))
    check("heure limite: compté dans le max Predict du jour", st["today"]["predict_delivered"]["dry"] >= 1)
    # seeding + closed + stale
    s = make("hl_seed", {"predict": {"window_start": "00:00", "window_end": "24:00", "days": list(range(7))}})
    gcap(s, 14.7, positions=[POS]); Path(s.cfg["deadline_reminders"]).write_text(json.dumps(REM) + "\n")
    tick(s, t1, {"SOL-EUR": 98.36}); st = s.cycle(t1, 0)
    t3 = t1 + timedelta(minutes=1); tick(s, t3, {"SOL-EUR": 98.36}); st2 = s.cycle(t3, 1)
    check("heure limite: rappel déjà écrit au 1er démarrage → amorcé, pas de sonnerie rétroactive",
          not ik(st, "heure_limite:") and not ik(st2, "heure_limite:") and "amorçage" in s.f_log.read_text())
    s = make("hl_closed", {"predict": {"window_start": "00:00", "window_end": "24:00", "days": list(range(7))}})
    gcap(s, 0, positions=[dict(POS, status="closed")]); tick(s, t0, ALL); s.cycle(t0, 0)
    Path(s.cfg["deadline_reminders"]).write_text(json.dumps(REM) + "\n")
    tick(s, t1, ALL); st = s.cycle(t1, 1)
    check("heure limite: trade déjà fermé → pas de sonnerie (noté « déjà fermé »)",
          not ik(st, "heure_limite:") and "déjà fermé" in s.f_log.read_text())
    s = make("hl_stale", {"predict": {"window_start": "00:00", "window_end": "24:00", "days": list(range(7))}})
    gcap(s, 14.7, positions=[POS]); tick(s, t0, ALL); s.cycle(t0, 0)
    Path(s.cfg["deadline_reminders"]).write_text(json.dumps(REM) + "\n")
    st = s.cycle(t0 + timedelta(minutes=10), 1)
    check("heure limite: prix pas à jour → en attente, pas de sonnerie",
          not ik(st, "heure_limite:") and st["predict_heure_limite"]["en_attente"] == ["rx-paper-D-060"])
    t4 = t0 + timedelta(minutes=11); tick(s, t4, {"SOL-EUR": 98.5}); st = s.cycle(t4, 2)
    check("heure limite: prix de nouveau frais → sonne", len(ik(st, "heure_limite:")) == 1)

    print("== Nuit sans décision ==")
    s = make("nuit", {"predict": {"window_start": "00:00", "window_end": "24:00", "days": list(range(7))}})
    declog(s, [("D-070", datetime(2026, 10, 8, 20, 0, tzinfo=TZ)), ("D-071", datetime(2026, 10, 9, 9, 30, tzinfo=TZ))])
    gcap(s, 50.0)  # cap full → no idle ring here
    t = datetime(2026, 10, 9, 10, 0, tzinfo=TZ); tick(s, t, ALL); st = s.cycle(t, 0)
    check("nuit: aucune D-xxx entre 22h et 9h → night_sans_decision = true (nuit du 8 oct.)",
          st["night_sans_decision"] is True and st["night_sans_decision_detail"]["nuit"] == "2026-10-08", str(st["night_sans_decision_detail"]))
    zones(s, [Z("Z-SOL-98")]); t = t + timedelta(minutes=1); tick(s, t, ALL); st = s.cycle(t, 1)
    p = last_payload(s)
    check("nuit: 1re sonnerie Predict après 9h commence par « Nuit sans décision »",
          p["message_fr"].startswith("Nuit sans décision") and p.get("nuit_sans_decision") is True, p["message_fr"])
    zones(s, [Z("Z-SOL-98b")]); t = t + timedelta(minutes=1); tick(s, t, ALL); s.cycle(t, 2)
    check("nuit: 2e sonnerie → texte normal", last_payload(s)["message_fr"].startswith("SOL est passé"), last_payload(s)["message_fr"])
    declog(s, [("D-072", datetime(2026, 10, 8, 23, 0, tzinfo=TZ))])
    st = s.cycle(t + timedelta(minutes=1), 3)
    check("nuit: D-072 à 23h → night_sans_decision = false", st["night_sans_decision"] is False
          and st["night_sans_decision_detail"]["decisions"] == ["D-072"])
    st = s.cycle(datetime(2026, 10, 10, 8, 0, tzinfo=TZ), 4)
    check("nuit: à 8h00 le 10 oct., la nuit en cours n'est pas finie → on regarde encore la nuit du 8",
          st["night_sans_decision_detail"]["nuit"] == "2026-10-08")
    check("nuit: last_night / in_night (22h–09h)",
          in_night(datetime(2026, 10, 9, 23, 0, tzinfo=TZ), s.cfg) == "2026-10-09"
          and in_night(datetime(2026, 10, 10, 8, 59, tzinfo=TZ), s.cfg) == "2026-10-09"
          and in_night(datetime(2026, 10, 10, 9, 0, tzinfo=TZ), s.cfg) is None)

    print("== Distance des zones ==")
    def zz(pair, prix, zid):
        return {"id": zid, "paire": pair, "sens": "sous", "prix": prix, "bot": "predict"}
    zd = zones_distance([zz("SOL-EUR", 99.5, "a"), zz("SOL-EUR", 100.8, "b"), zz("SOL-EUR", 97.0, "c")],
                        {"SOL-EUR": 100.0}, 1.0)
    check("zones: 0,5 % dessous / 0,8 % dessus → ok (vert)", zd["paires"]["SOL-EUR"]["ok"] is True and zd["ok"] is True
          and zd["paires"]["SOL-EUR"]["dessous"]["id"] == "a", str(zd))
    zd = zones_distance([zz("BTC-EUR", 72000, "x"), zz("BTC-EUR", 74000, "y")], {"BTC-EUR": 72950.0, "ETH-EUR": 2200.0}, 1.0)
    check("zones: BTC à 1,30 % / 1,44 % → signalé (rouge) ; ETH sans zone → signalé",
          zd["ok"] is False and set(zd["a_signaler"]) == {"BTC-EUR", "ETH-EUR"}
          and "aucune zone en dessous" in zd["paires"]["ETH-EUR"]["probleme"], str(zd))
    zd = zones_distance([zz("SOL-EUR", 99.5, "a"), {"id": "r", "paire": "SOL-EUR", "prix": 100.5, "bot": "risk"}],
                        {"SOL-EUR": 100.0}, 1.0)
    check("zones: zones de Risk ignorées → SOL sans zone Predict au-dessus = signalé", zd["paires"]["SOL-EUR"]["ok"] is False)
    s = make("zd"); zones(s, [Z("Z-SOL-97", prix=97.0)]); tick(s, FRI, ALL); st = s.cycle(FRI, 0)
    check("zones: status.json → zones_distance par paire", st["zones_distance"]["paires"]["SOL-EUR"]["ok"] is False
          and set(st["zones_distance"]["paires"]) == {"SOL-EUR", "BTC-EUR", "ETH-EUR"})

    print("== Reprise après pause de la machine ==")
    s = make("sante_reprise")
    me = os.getpid()
    T = datetime(2026, 10, 9, 13, 19, 0, tzinfo=TZ)
    gcap(s, 14.7, positions=[POS])
    wf, rf = Path(s.cfg["watch_heartbeat"]), Path(s.cfg["revolut_heartbeat"])
    wf.write_text(json.dumps({"ts": T.isoformat(), "pid": me, "open_live": 0, "open_paper": 1}))
    rf.write_text(json.dumps({"ts": (T - timedelta(minutes=4)).isoformat(), "ok": True, "consecutive_failures": 0}))
    tick(s, T, ALL); st = s.cycle(T, 1000.0)
    check("reprise: avant la pause tout va bien → aucune sonnerie Risk", not hk(st, "revolut_down") and not hk(st, "watcher_down"))
    R = T + timedelta(minutes=41)  # 13:19 → 14:00, the machine was paused (wall + monotonic jump)
    tick(s, R, ALL); st = s.cycle(R, 1000.0 + 41 * 60)
    check("reprise: 1er tour après 41 min de pause (Revolut 45 min, surveillant 41 min) → aucune sonnerie Risk",
          not hk(st, "revolut_down") and not hk(st, "watcher_down"), str(st["rings_this_cycle"]))
    check("reprise: status.json → sante.reprise + log « reprise détectée »",
          (st["sante"].get("reprise") or {}).get("trou_s") == 2460 and "reprise détectée" in s.f_log.read_text())
    wf.write_text(json.dumps({"ts": (R + timedelta(seconds=30)).isoformat(), "pid": me, "open_live": 0, "open_paper": 1}))
    tick(s, R + timedelta(seconds=30), ALL); st = s.cycle(R + timedelta(seconds=30), 1000.0 + 41 * 60 + 30)
    check("reprise: surveillant revenu, Revolut pas encore retesté (dans la grâce) → toujours rien",
          not hk(st, "revolut_down") and not hk(st, "watcher_down"))
    rf.write_text(json.dumps({"ts": (R + timedelta(minutes=1)).isoformat(), "ok": True, "consecutive_failures": 0}))
    for i in range(1, 12):
        tt = R + timedelta(minutes=1, seconds=30 * i)
        wf.write_text(json.dumps({"ts": tt.isoformat(), "pid": me, "open_live": 0, "open_paper": 1}))
        tick(s, tt, ALL); st = s.cycle(tt, 1000.0 + 41 * 60 + 60 + 30 * i)
        assert not hk(st, "revolut_down"), "unexpected"
    check("reprise: Revolut retesté → rien du tout (fausse alerte évitée)", "revolut_down" not in s.f_rings.read_text()
          if s.f_rings.exists() else True)
    # Real problem after resume: Revolut never comes back → rings once the grace (10 min) is over
    s = make("sante_reprise2")
    gcap(s, 14.7, positions=[POS])
    wf, rf = Path(s.cfg["watch_heartbeat"]), Path(s.cfg["revolut_heartbeat"])
    rf.write_text(json.dumps({"ts": (T - timedelta(minutes=4)).isoformat(), "ok": True, "consecutive_failures": 0}))
    wf.write_text(json.dumps({"ts": T.isoformat(), "pid": me, "open_live": 0, "open_paper": 1}))
    tick(s, T, ALL); s.cycle(T, 0.0)
    tick(s, R, ALL); wf.write_text(json.dumps({"ts": R.isoformat(), "pid": me, "open_live": 0, "open_paper": 1}))
    st = s.cycle(R, 41 * 60.0)
    check("reprise: Revolut muet → pas de sonnerie pendant la grâce", not hk(st, "revolut_down"))
    first_ring = None
    for k in range(1, 23):  # normal 30 s cycles after the resume, the watcher keeps writing, Revolut never does
        tt = R + timedelta(seconds=30 * k)
        wf.write_text(json.dumps({"ts": tt.isoformat(), "pid": me, "open_live": 0, "open_paper": 1}))
        tick(s, tt, ALL); st = s.cycle(tt, 41 * 60.0 + 30 * k)
        if hk(st, "revolut_down") and first_ring is None:
            first_ring = 30 * k
    check("reprise: Revolut muet → rien pendant la grâce, puis revolut_down sonne Risk à 10 min (vrai problème)",
          first_ring == 600, str(first_ring))
    # No pause: a 44-min-old Revolut heartbeat still rings at once (unchanged behaviour)
    s = make("sante_sans_reprise")
    gcap(s, 14.7, positions=[POS])
    Path(s.cfg["watch_heartbeat"]).write_text(json.dumps({"ts": R.isoformat(), "pid": me, "open_live": 0, "open_paper": 1}))
    Path(s.cfg["revolut_heartbeat"]).write_text(json.dumps({"ts": (R - timedelta(minutes=44)).isoformat(), "ok": True,
                                                            "consecutive_failures": 0}))
    tick(s, R - timedelta(seconds=30), ALL); st0 = s.cycle(R - timedelta(seconds=30), 0.0)
    tick(s, R, ALL); st = s.cycle(R, 30.0)
    check("reprise: sans pause, Revolut muet 44 min → sonne tout de suite (inchangé), une seule fois",
          len(hk(st0, "revolut_down")) == 1 and not hk(st, "revolut_down"))
    s = make("sante_reprise_pid")
    gcap(s, 14.7, positions=[POS])
    proc = subprocess.Popen(["true"]); proc.wait()
    Path(s.cfg["watch_heartbeat"]).write_text(json.dumps({"ts": T.isoformat(), "pid": me, "open_live": 0, "open_paper": 1}))
    Path(s.cfg["revolut_heartbeat"]).write_text(json.dumps({"ts": T.isoformat(), "ok": True, "consecutive_failures": 0}))
    tick(s, T, ALL); s.cycle(T, 0.0)
    Path(s.cfg["watch_heartbeat"]).write_text(json.dumps({"ts": R.isoformat(), "pid": proc.pid, "open_live": 0, "open_paper": 1}))
    tick(s, R, ALL); st = s.cycle(R, 41 * 60.0)
    check("reprise: pid du surveillant mort juste après une reprise → watcher_down sonne quand même (pas de grâce)",
          len(hk(st, "watcher_down")) == 1, str(st["rings_this_cycle"]))
    # ================================================================ mouvement (9 oct)
    print("== Predict : mouvement > 0,5 % ==")
    M0 = datetime(2026, 10, 10, 11, 0, tzinfo=TZ)  # Saturday: 24/7
    REF = {"BTC-EUR": 74000.0, "ETH-EUR": 2200.0, "SOL-EUR": 100.0}
    def mv_make(sub, extra=None, env=None):
        s_ = make(sub, extra, env)
        declog(s_, [("D-029", M0 - timedelta(hours=12)), ("D-030", M0)])  # D-029 at 23:00: not a night without decision
        tick(s_, M0 + timedelta(seconds=20), REF)           # collector price at the decision minute
        tick(s_, M0 + timedelta(minutes=3), {"BTC-EUR": 74100.0, "ETH-EUR": 2201.0, "SOL-EUR": 100.2})
        return s_
    def mk(st_):
        return [r for r in st_["rings_this_cycle"] if r["key"].startswith("mouvement:")]
    def run_at(s_, t_, px, mono=None):
        tick(s_, t_, px); return s_.cycle(t_, (t_ - M0).total_seconds() if mono is None else mono)
    s = mv_make("mv")
    t1 = M0 + timedelta(minutes=31)   # gap: 30 min after the decision before any movement ring
    st = run_at(s, t1, {"BTC-EUR": 74100.0, "ETH-EUR": 2201.0, "SOL-EUR": 100.2})
    pm = st["predict_mouvement"]
    check("mouvement: démarrage → références = prix à D-030 (pas le prix actuel), aucune sonnerie",
          not mk(st) and pm["reference"]["prix"] == REF and pm["reference"]["decision_id"] == "D-030"
          and "amorçage" in s.f_log.read_text(), str(pm))
    st = run_at(s, t1 + timedelta(seconds=30), {"BTC-EUR": 74350.0, "ETH-EUR": 2210.0, "SOL-EUR": 100.5})
    check("mouvement: 0,47 % / 0,45 % / 0,5 % pile → pas de sonnerie (il faut PLUS de 0,5 %)", not mk(st),
          str(st["predict_mouvement"].get("mouvement_pct")))
    t2 = t1 + timedelta(minutes=1)
    st = run_at(s, t2, {"BTC-EUR": 74400.0, "ETH-EUR": 2201.0, "SOL-EUR": 99.3})
    r_ = mk(st); pl = last_payload(s)
    want = ("mouvement > 0,5 % : BTC 74 000,00 € → 74 400,00 € (+0,5 %), SOL 100,00 € → 99,30 € (-0,7 %) depuis D-030. "
            "Refais tes 3 propositions (risquée, prudente, équilibrée) dans une nouvelle D-xxx ; si rien à proposer, "
            "écris une D-xxx « pas de proposition » avec tes raisons.")
    check("mouvement: BTC +0,54 % et SOL -0,7 % → UNE sonnerie Predict groupée (dry en test)",
          len(r_) == 1 and r_[0]["bot"] == "predict" and r_[0]["result"] == "dry", str(st["rings_this_cycle"]))
    check("mouvement: message exact demandé", pl.get("message_fr") == want, pl.get("message_fr"))
    check("mouvement: payload kind/raison_type « mouvement », 2 paires, D-030",
          pl.get("kind") == "mouvement" and pl.get("raison_type") == "mouvement" and pl.get("decision_id") == "D-030"
          and [x["paire"] for x in pl.get("paires", [])] == ["BTC-EUR", "SOL-EUR"])
    check("mouvement: compté à part — Predict zones/jour inchangé (0), 1 réveil mouvement, pas de plafond",
          s.bucket(s.load_state(t2.date().isoformat()), "dry", "predict")["delivered"] == 0
          and st["predict_mouvement"]["aujourd_hui"] == 1 and "max_par_jour" not in st["predict_mouvement"]
          and st["predict_mouvement"]["prochain_reveil_possible_fr"] == hhmm(t2 + timedelta(minutes=30)),
          str(st["predict_mouvement"].get("prochain_reveil_possible_fr")))
    st = run_at(s, t2 + timedelta(minutes=5), {"BTC-EUR": 74600.0, "ETH-EUR": 2201.0, "SOL-EUR": 99.0})
    check("mouvement: pendant l'attente de la D-xxx → pas de 2e sonnerie", not mk(st)
          and "attente" in str(st["predict_mouvement"].get("raison")))
    # new decision after the ring → references reset to the price at that decision
    Dn = t2 + timedelta(minutes=8)
    tick(s, Dn.replace(second=10), {"BTC-EUR": 74500.0, "ETH-EUR": 2205.0, "SOL-EUR": 99.1})
    declog(s, [("D-029", M0 - timedelta(hours=12)), ("D-030", M0), ("D-031", Dn.replace(second=0))])
    st = run_at(s, Dn + timedelta(minutes=2), {"BTC-EUR": 74550.0, "ETH-EUR": 2205.0, "SOL-EUR": 99.1})
    rf = st["predict_mouvement"]["reference"]
    check("mouvement: nouvelle D-031 → références = prix à D-031, attente terminée, pas de sonnerie",
          not mk(st) and rf["decision_id"] == "D-031" and rf["prix"]["BTC-EUR"] == 74500.0
          and st["predict_mouvement"]["attente_decision"] is None, str(rf))
    st = run_at(s, Dn + timedelta(minutes=29), {"BTC-EUR": 75000.0, "ETH-EUR": 2205.0, "SOL-EUR": 99.1})
    check("mouvement: +0,67 % 29 min après D-031 → bloqué (30 min après la dernière proposition)",
          not mk(st) and "après la dernière décision D-031" in str(st["predict_mouvement"].get("raison"))
          and st["predict_mouvement"]["prochain_reveil_possible_fr"] == hhmm(Dn.replace(second=0) + timedelta(minutes=30)),
          str(st["predict_mouvement"].get("raison")))
    st = run_at(s, Dn.replace(second=0) + timedelta(minutes=30), {"BTC-EUR": 75000.0, "ETH-EUR": 2205.0, "SOL-EUR": 99.1})
    check("mouvement: 30 min après D-031 → sonne", len(mk(st)) == 1 and "depuis D-031" in last_payload(s)["message_fr"])
    # no decision within 20 min → reset to current prices + note in rings.jsonl
    s = mv_make("mv_sans_dec")
    run_at(s, t1, {"BTC-EUR": 74100.0, "ETH-EUR": 2201.0, "SOL-EUR": 100.2})
    st = run_at(s, t2, {"BTC-EUR": 74500.0, "ETH-EUR": 2201.0, "SOL-EUR": 100.0})
    check("mouvement: (2e cas) BTC +0,68 % → sonne", len(mk(st)) == 1)
    st = run_at(s, t2 + timedelta(minutes=19), {"BTC-EUR": 74600.0, "ETH-EUR": 2201.0, "SOL-EUR": 100.0})
    check("mouvement: 19 min sans D-xxx → on attend encore", not mk(st) and st["predict_mouvement"]["attente_decision"])
    tot_before = s.ring_totals()["predict"]["vrais"]
    st = run_at(s, t2 + timedelta(minutes=20), {"BTC-EUR": 74650.0, "ETH-EUR": 2201.0, "SOL-EUR": 100.0})
    lastrec = json.loads(tail_lines(s.f_rings)[-1])
    check("mouvement: 20 min sans D-xxx → références = prix actuels, note « pas de nouvelle décision après réveil » dans rings.jsonl",
          not mk(st) and st["predict_mouvement"]["reference"]["prix"]["BTC-EUR"] == 74650.0
          and lastrec["result"] == "note" and lastrec["payload"]["kind"] == "mouvement_sans_decision"
          and "pas de nouvelle décision après réveil" in lastrec["payload"]["message_fr"], str(lastrec))
    check("mouvement: la note n'est pas comptée comme sonnerie (totaux inchangés)",
          s.ring_totals()["predict"]["vrais"] == tot_before)
    st = run_at(s, t2 + timedelta(minutes=21), {"BTC-EUR": 74650.0, "ETH-EUR": 2201.0, "SOL-EUR": 100.0})
    check("mouvement: même mouvement après remise à zéro → plus de sonnerie", not mk(st))
    st = run_at(s, t2 + timedelta(minutes=25), {"BTC-EUR": 75100.0, "ETH-EUR": 2201.0, "SOL-EUR": 100.0})
    check("mouvement: nouveau +0,6 % 25 min après le réveil → bloqué (30 min après le dernier réveil)", not mk(st)
          and "après le dernier réveil mouvement" in str(st["predict_mouvement"].get("raison")), str(st["predict_mouvement"].get("raison")))
    st = run_at(s, t2 + timedelta(minutes=30), {"BTC-EUR": 75100.0, "ETH-EUR": 2201.0, "SOL-EUR": 100.0})
    check("mouvement: à 30 min → sonne de nouveau (2e)", len(mk(st)) == 1 and st["predict_mouvement"]["aujourd_hui"] == 2)
    # no daily cap: 14 movement rings in one day (each 30 min apart, no D-xxx in between) all go through
    s = mv_make("mv_pas_de_plafond")
    run_at(s, t1, REF)
    cnt, px_, tt = 0, 74000.0, t2
    for _k in range(14):
        px_ *= 1.006
        st = run_at(s, tt, {"BTC-EUR": round(px_, 2), "ETH-EUR": 2200.0, "SOL-EUR": 100.0})
        cnt += len(mk(st))
        st = run_at(s, tt + timedelta(minutes=20), {"BTC-EUR": round(px_, 2), "ETH-EUR": 2200.0, "SOL-EUR": 100.0})
        cnt += len(mk(st))   # 20 min without D-xxx → references reset (no ring)
        tt += timedelta(minutes=30)
    check("mouvement: pas de plafond par jour — 14 mouvements espacés de 30 min → 14 sonneries",
          cnt == 14 and st["predict_mouvement"]["aujourd_hui"] == 14 and "plafond" not in s.f_log.read_text(), str(cnt))
    # stale prices
    s = mv_make("mv_stale")
    run_at(s, t1, REF)
    tick(s, t2, {"BTC-EUR": 75000.0, "ETH-EUR": 2200.0, "SOL-EUR": 100.0})
    st = s.cycle(t2 + timedelta(minutes=4), 600)
    check("mouvement: prix vieux de 4 min → pas de sonnerie", not mk(st)
          and "pas à jour" in str(st["predict_mouvement"].get("raison")), str(st["predict_mouvement"].get("raison")))
    tick(s, t2 + timedelta(minutes=4, seconds=30), {"BTC-EUR": 75000.0, "SOL-EUR": 100.0})
    st = s.cycle(t2 + timedelta(minutes=4, seconds=40), 640)
    check("mouvement: une paire sans prix frais (ETH) → pas de sonnerie", not mk(st))
    # zone cap full does not block movement; movement does not use it
    s = mv_make("mv_zonecap", {"predict": {"max_per_day": 0}})
    run_at(s, t1, REF)
    st = run_at(s, t2, {"BTC-EUR": 73500.0, "ETH-EUR": 2200.0, "SOL-EUR": 100.0})
    check("mouvement: max Predict zones/jour plein → la sonnerie mouvement passe quand même (compteur séparé)",
          len(mk(st)) == 1 and "(-0,7 %)" in last_payload(s)["message_fr"])
    # failed ring → retry after 5 min, max 3 tries, then give up and reset references
    ARM = {"SONNETTE_PREDICT_URL": "http://127.0.0.1:9/p", "SONNETTE_PREDICT_KEY": "k-mv-1"}
    s = mv_make("mv_fail", env=ARM)
    s.sender = lambda *a, **k: {"ok": False, "status": 500, "error": "HTTP 500", "tries": 1}
    run_at(s, t1, REF)
    BIG = {"BTC-EUR": 74600.0, "ETH-EUR": 2200.0, "SOL-EUR": 100.0}
    st = run_at(s, t2, BIG)
    check("mouvement: échec d'envoi → result failed, pas compté (0/10)",
          [r["result"] for r in mk(st)] == ["failed"] and st["predict_mouvement"]["aujourd_hui"] == 0)
    st = run_at(s, t2 + timedelta(minutes=4), BIG)
    check("mouvement: 4 min après l'échec → pas de nouvel essai", not mk(st))
    st = run_at(s, t2 + timedelta(minutes=5), BIG)
    check("mouvement: 5 min après → 2e essai", [r["result"] for r in mk(st)] == ["failed"])
    st = run_at(s, t2 + timedelta(minutes=10), BIG)
    check("mouvement: 3e essai", [r["result"] for r in mk(st)] == ["failed"] and st["predict_mouvement"]["echec"]["essais"] == 3)
    st = run_at(s, t2 + timedelta(minutes=15), BIG)
    check("mouvement: après 3 essais → abandon, références = prix actuels, pas de 4e essai",
          not mk(st) and st["predict_mouvement"]["reference"]["prix"]["BTC-EUR"] == 74600.0
          and st["predict_mouvement"]["echec"] is None)
    s2 = mv_make("mv_fail_ok", env=ARM)
    calls = []
    s2.sender = lambda *a, **k: (calls.append(1), {"ok": len(calls) > 1, "status": 200 if len(calls) > 1 else 500,
                                                    "error": None if len(calls) > 1 else "HTTP 500", "tries": 1})[1]
    run_at(s2, t1, REF); run_at(s2, t2, BIG)
    st = run_at(s2, t2 + timedelta(minutes=5), BIG)
    check("mouvement: 2e essai réussi → livré, 1 réveil, attente de la D-xxx",
          [r["result"] for r in mk(st)] == ["delivered"] and st["predict_mouvement"]["aujourd_hui"] == 1
          and st["predict_mouvement"]["attente_decision"])
    # no decision at all / no tick at decision time
    s = make("mv_vide")
    st = run_at(s, t1, BIG)
    check("mouvement: carnet absent → pas de référence, pas de sonnerie", not mk(st)
          and st["predict_mouvement"].get("reference") is None)
    s = make("mv_sans_tick"); declog(s, [("D-040", M0 - timedelta(hours=3))])
    st = run_at(s, t1, BIG)
    check("mouvement: pas de prix à l'heure de la décision → prix actuel en référence (noté), pas de sonnerie",
          not mk(st) and st["predict_mouvement"]["reference"]["prix"]["BTC-EUR"] == 74600.0
          and "pas de prix à l'heure" in st["predict_mouvement"]["reference"]["origine"]["BTC-EUR"])
    s = mv_make("mv_off", {"mouvement": {"actif": False}})
    run_at(s, t1, REF); st = run_at(s, t2, BIG)
    check("mouvement: actif=false → jamais de sonnerie", not mk(st))
    s = mv_make("mv_restart"); run_at(s, t1, REF)
    st = run_at(s, t2, BIG)
    s_b = Sonnette(s.cfg, env={}, quiet=True)
    tick(s_b, t2 + timedelta(minutes=1), BIG); st = s_b.cycle(t2 + timedelta(minutes=1), 0.0)
    check("mouvement: redémarrage après un réveil → état gardé (pas de 2e sonnerie, compteur 1)",
          not mk(st) and st["predict_mouvement"]["aujourd_hui"] == 1)
    s_c = mv_make("mv_down"); run_at(s_c, t1, REF)
    st = run_at(s_c, t2, {"BTC-EUR": 74000.0, "ETH-EUR": 2185.0, "SOL-EUR": 100.0})
    check("mouvement: baisse ETH -0,68 % → sonne avec « (-0,7 %) » et seulement ETH",
          len(mk(st)) == 1 and "ETH 2 200,00 € → 2 185,00 € (-0,7 %) depuis D-030" in last_payload(s_c)["message_fr"]
          and "BTC" not in last_payload(s_c)["message_fr"].split("depuis")[0], last_payload(s_c)["message_fr"])
    check("mouvement: status.json → predict_mouvement (référence, % par paire, réveils du jour, prochain réveil possible)",
          all(k in (load_json(s_c.f_status, {}) or {}).get("predict_mouvement", {})
              for k in ("reference", "mouvement_pct", "aujourd_hui", "prochain_reveil_possible", "prochain_reveil_possible_fr")))
    s_g = mv_make("mv_gap_decision")
    st = run_at(s_g, M0 + timedelta(minutes=10), REF)
    st = run_at(s_g, M0 + timedelta(minutes=20), BIG)
    check("mouvement: +0,8 % 20 min après la décision (jamais sonné) → bloqué jusqu'à 11h30",
          not mk(st) and st["predict_mouvement"]["prochain_reveil_possible_fr"] == "11h30", str(st["predict_mouvement"].get("raison")))

    real = json.loads((HERE / "config.json").read_text())
    check("config.json: mouvement 0,5 % / 30 min / pas de plafond / 20 min / 5 min ×3 / 180 s",
          "max_par_jour" not in real.get("mouvement", {}) and
          {k: real.get("mouvement", {}).get(k) for k in ("actif", "seuil_pct", "intervalle_min_min",
                                                          "attente_decision_min", "retry_after_fail_min", "max_essais", "prix_max_age_s")}
          == {"actif": True, "seuil_pct": 0.5, "intervalle_min_min": 30, "attente_decision_min": 20,
              "retry_after_fail_min": 5, "max_essais": 3, "prix_max_age_s": 180}, str(real.get("mouvement")))
    check("config.json: idle (4 h, 1 par 4 h, 2 par nuit), heure_limite, zones_distance 1 %, nuit 22h–09h, reprise",
          real.get("idle", {}).get("heures_sans_decision") == 4 and real["idle"].get("intervalle_min_h") == 4
          and real["idle"].get("max_par_nuit") == 2 and real.get("heure_limite", {}).get("actif") is True
          and real.get("zones_distance", {}).get("max_pct") == 1.0 and real.get("nuit") == {"debut": "22:00", "fin": "09:00"}
          and real.get("health", {}).get("resume_grace_revolut_s") == 600, str({k: real.get(k) for k in ("idle", "nuit")}))

    ok = sum(1 for _, c in results if c)
    print(f"\nRésultat: {ok}/{len(results)} tests OK")
    return 0 if ok == len(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
