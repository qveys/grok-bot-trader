#!/usr/bin/env python3
"""Detect Predict BUY decisions awaiting Risk validation (buy-side wake).

Sources (Predict / decision handoff only — Scan price moves do NOT count):
  - state/last_predict.json  (signals / tradeable with BUY|YES|ACHETER|…)
  - knowledge/decision_log.md  (Décision : **ACHETER**)
  - state/handoff_*.json      if they carry a Predict buy / decision_id

A signal is pending when Risk has not yet recorded a matching paper/live fill
or an explicit refuse for that decision_id (trades_log, refuse files, Risk
handoffs). Writes state/buy_wake.json. Always exits 0. No orders, no secrets.

Run alongside check_alerts.py in Risk’s weekday routine / handoff.
"""
from __future__ import annotations

import json
import re
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

GUARDIAN = Path(__file__).resolve().parent.parent
ROOT = GUARDIAN.parent
STATE_DIR = ROOT / "state"
OUT_PATH = STATE_DIR / "buy_wake.json"
LAST_PREDICT = STATE_DIR / "last_predict.json"
DECISION_LOG = ROOT / "knowledge" / "decision_log.md"
TRADES_PATH = STATE_DIR / "trades_log.jsonl"
TZ = ZoneInfo("Europe/Brussels")

WHITELIST = {"BTC-EUR", "ETH-EUR", "SOL-EUR"}
BUY_DECISIONS = {
    "BUY",
    "YES",
    "ACHETER",
    "TRADE",
    "LONG",
    "BUY_YES",
    "OUI",
}
# Explicit non-buys (normalize strips accents / spaces)
NO_BUY = {
    "NO_TRADE",
    "NO",
    "PAS_ACHETER",
    "HOLD",
    "NONE",
    "SKIP",
    "REFUSE",
    "REFUSED",
}


def now_iso() -> str:
    return datetime.now(TZ).isoformat()


def load_json(path: Path):
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text())
    except (OSError, json.JSONDecodeError):
        return None


def norm_decision(raw) -> str:
    s = str(raw or "").strip().upper()
    s = (
        s.replace("É", "E")
        .replace("È", "E")
        .replace("Ê", "E")
        .replace("À", "A")
        .replace("’", "'")
    )
    s = re.sub(r"[\s\-]+", "_", s)
    s = s.strip("*_ ")
    return s


def is_buy_decision(raw) -> bool:
    d = norm_decision(raw)
    if not d or d in NO_BUY:
        return False
    if d in BUY_DECISIONS:
        return True
    # e.g. ACHETER_PAPER, BUY_LIMIT
    if d.startswith("ACHETER") or d.startswith("BUY") or d.startswith("YES"):
        return True
    return False


def norm_pair(raw) -> str:
    return str(raw or "").strip().upper()


def collect_from_predict(predict: dict) -> list[dict]:
    out: list[dict] = []
    if not predict:
        return out
    decided_at = (
        predict.get("predicted_at")
        or predict.get("ts")
        or predict.get("decided_at")
        or predict.get("updated_at")
    )
    # tradeable list first (explicit handoff to Risk)
    for row in predict.get("tradeable") or []:
        if isinstance(row, str):
            pair = norm_pair(row)
            if pair in WHITELIST:
                out.append(
                    {
                        "pair": pair,
                        "decision_id": None,
                        "side": "buy",
                        "amount_hint": None,
                        "decided_at": decided_at,
                        "source": "last_predict.tradeable",
                        "decision": "BUY",
                    }
                )
            continue
        if not isinstance(row, dict):
            continue
        pair = norm_pair(row.get("pair") or row.get("market") or row.get("symbol"))
        if pair not in WHITELIST:
            continue
        dec = row.get("decision") or row.get("side") or "BUY"
        if not is_buy_decision(dec) and norm_decision(dec) not in ("", "BUY"):
            # tradeable implies buy unless explicit no
            if norm_decision(dec) in NO_BUY:
                continue
        out.append(
            {
                "pair": pair,
                "decision_id": row.get("decision_id") or row.get("id"),
                "side": "buy",
                "amount_hint": _amount_hint(row),
                "decided_at": row.get("decided_at") or row.get("ts") or decided_at,
                "source": "last_predict.tradeable",
                "decision": str(dec),
            }
        )
    for row in predict.get("signals") or []:
        if not isinstance(row, dict):
            continue
        pair = norm_pair(row.get("pair"))
        if pair not in WHITELIST:
            continue
        if not is_buy_decision(row.get("decision") or row.get("side")):
            continue
        out.append(
            {
                "pair": pair,
                "decision_id": row.get("decision_id") or row.get("id"),
                "side": "buy",
                "amount_hint": _amount_hint(row),
                "decided_at": row.get("decided_at") or row.get("ts") or decided_at,
                "source": "last_predict.signals",
                "decision": str(row.get("decision") or row.get("side")),
            }
        )
    return out


def _amount_hint(row: dict):
    for key in (
        "amount_hint",
        "amount_eur",
        "size_eur",
        "taille_eur",
        "notional_eur",
        "suggested_amount_eur",
    ):
        if row.get(key) is not None:
            try:
                return float(row[key])
            except (TypeError, ValueError):
                return row[key]
    return None


def collect_from_decision_log(text: str) -> list[dict]:
    """Parse ### date | PAIR | D-xxx blocks with Décision : **ACHETER**."""
    out: list[dict] = []
    if not text:
        return out
    # Split on ### headings
    blocks = re.split(r"(?m)^###\s+", text)
    header_re = re.compile(
        r"^(?P<when>\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2})\s*\|\s*"
        r"(?P<pair>[A-Za-z0-9\-]+)\s*\|\s*(?P<did>[A-Za-z0-9\-_.]+)",
    )
    for block in blocks:
        m = header_re.match(block.strip())
        if not m:
            continue
        pair = norm_pair(m.group("pair"))
        if pair not in WHITELIST:
            continue
        # Decision line: must be ACHETER, not PAS ACHETER
        dec_m = re.search(
            r"Décision\s*:\s*\*?\*?(?P<dec>[^*\n]+)",
            block,
            re.IGNORECASE,
        )
        if not dec_m:
            continue
        dec_raw = dec_m.group("dec").strip()
        # Guard: "PAS ACHETER" / "PAS D'ACHETER"
        if re.search(r"\bPAS\b", dec_raw, re.IGNORECASE):
            continue
        if not is_buy_decision(dec_raw):
            continue
        amount_hint = None
        size_m = re.search(
            r"Si ACHETER\s*→\s*taille\s*€?\s*/?\s*%?\s*capital\s*:\s*"
            r"(?P<sz>[^\n]+)",
            block,
            re.IGNORECASE,
        )
        if size_m:
            sz = size_m.group("sz").strip()
            if sz and sz not in ("—", "-", "n/a", "N/A"):
                num = re.search(r"(\d+(?:[.,]\d+)?)\s*€?", sz)
                if num:
                    try:
                        amount_hint = float(num.group(1).replace(",", "."))
                    except ValueError:
                        amount_hint = sz
                else:
                    amount_hint = sz
        when = m.group("when")
        # Local Brussels wall time → ISO with offset
        try:
            dt = datetime.strptime(when, "%Y-%m-%d %H:%M").replace(tzinfo=TZ)
            decided_at = dt.isoformat()
        except ValueError:
            decided_at = when
        out.append(
            {
                "pair": pair,
                "decision_id": m.group("did"),
                "side": "buy",
                "amount_hint": amount_hint,
                "decided_at": decided_at,
                "source": "decision_log",
                "decision": "ACHETER",
            }
        )
    return out


def collect_from_handoffs() -> list[dict]:
    """Predict-oriented handoffs only (skip Scan price-flag files)."""
    out: list[dict] = []
    for path in sorted(STATE_DIR.glob("handoff_*.json")):
        name = path.name.lower()
        # Scan handoffs flag prices / anomalies — not a Predict buy
        if "scan" in name:
            continue
        data = load_json(path)
        if not data or not isinstance(data, dict):
            continue
        frm = str(data.get("from") or data.get("source") or "").lower()
        if "scan" in frm and "predict" not in frm:
            continue
        decided_at = (
            data.get("decided_at")
            or data.get("predicted_at")
            or data.get("ts")
            or data.get("updated_at")
        )
        # Nested signals / decisions / tradeable
        rows = []
        for key in ("signals", "decisions", "tradeable", "buys", "pending"):
            val = data.get(key)
            if isinstance(val, list):
                rows.extend(val)
        if data.get("pair") and (
            is_buy_decision(data.get("decision") or data.get("side") or data.get("action"))
            or data.get("awaiting_risk")
            or data.get("needs_risk")
        ):
            rows.append(data)
        for row in rows:
            if isinstance(row, str):
                pair = norm_pair(row)
                if pair in WHITELIST:
                    out.append(
                        {
                            "pair": pair,
                            "decision_id": data.get("decision_id"),
                            "side": "buy",
                            "amount_hint": _amount_hint(data),
                            "decided_at": decided_at,
                            "source": f"handoff:{path.name}",
                            "decision": "BUY",
                        }
                    )
                continue
            if not isinstance(row, dict):
                continue
            pair = norm_pair(row.get("pair"))
            if pair not in WHITELIST:
                continue
            dec = row.get("decision") or row.get("side") or row.get("action")
            if dec and not is_buy_decision(dec):
                continue
            if not dec and not (
                data.get("awaiting_risk")
                or data.get("needs_risk")
                or "predict" in frm
                or "risk" in name
            ):
                continue
            out.append(
                {
                    "pair": pair,
                    "decision_id": row.get("decision_id") or row.get("id") or data.get("decision_id"),
                    "side": "buy",
                    "amount_hint": _amount_hint(row) or _amount_hint(data),
                    "decided_at": row.get("decided_at") or row.get("ts") or decided_at,
                    "source": f"handoff:{path.name}",
                    "decision": str(dec or "BUY"),
                }
            )
    return out


def load_resolved_ids() -> set[str]:
    """decision_ids already filled or explicitly refused by Risk."""
    resolved: set[str] = set()

    def add_id(val):
        if val is None:
            return
        s = str(val).strip()
        if s:
            resolved.add(s)

    # trades_log: fills (or refuse status) carrying decision_id
    if TRADES_PATH.exists():
        try:
            for line in TRADES_PATH.read_text().splitlines():
                line = line.strip()
                if not line:
                    continue
                try:
                    row = json.loads(line)
                except json.JSONDecodeError:
                    continue
                did = row.get("decision_id") or row.get("linked_decision_id")
                status = str(row.get("status") or "").lower()
                side = str(row.get("side") or "").lower()
                if did and (
                    "fill" in status
                    or "filled" in status
                    or "refuse" in status
                    or side in ("buy", "yes", "long")
                ):
                    add_id(did)
                if did and row.get("refused") is True:
                    add_id(did)
        except OSError:
            pass

    # Explicit refuse / risk-decision files
    patterns = (
        "refuse*.json",
        "risk_refuse*.json",
        "risk_decision*.json",
        "risk_decisions.jsonl",
        "refuses.jsonl",
        "handoff_risk*.json",
    )
    paths: list[Path] = []
    for pat in patterns:
        paths.extend(STATE_DIR.glob(pat))
    # Also guardian-local refuse notes if any
    paths.extend(GUARDIAN.glob("refuse*.json"))
    paths.extend(GUARDIAN.glob("risk_refuse*.json"))

    for path in paths:
        if not path.exists():
            continue
        if path.suffix == ".jsonl":
            try:
                for line in path.read_text().splitlines():
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        row = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    _absorb_resolve_row(row, add_id)
            except OSError:
                continue
            continue
        data = load_json(path)
        if data is None:
            continue
        if isinstance(data, list):
            for row in data:
                if isinstance(row, dict):
                    _absorb_resolve_row(row, add_id)
        elif isinstance(data, dict):
            _absorb_resolve_row(data, add_id)
            for key in ("refuses", "decisions", "items", "entries"):
                for row in data.get(key) or []:
                    if isinstance(row, dict):
                        _absorb_resolve_row(row, add_id)

    return resolved


def _absorb_resolve_row(row: dict, add_id) -> None:
    did = row.get("decision_id") or row.get("linked_decision_id") or row.get("id")
    action = norm_decision(row.get("action") or row.get("status") or row.get("decision") or row.get("result"))
    refused = row.get("refused") is True or "REFUSE" in action
    filled = "FILL" in action or action in ("PAPER_FILLED", "FILLED", "LIVE_FILLED", "DONE")
    if did and (refused or filled or row.get("resolved") is True):
        add_id(did)


def dedupe_candidates(cands: list[dict]) -> list[dict]:
    """Prefer decision_id key; else pair+decided_at. Keep richest / latest."""
    by_key: dict[str, dict] = {}
    for c in cands:
        did = c.get("decision_id")
        key = f"id:{did}" if did else f"pair:{c.get('pair')}|{c.get('decided_at')}"
        prev = by_key.get(key)
        if prev is None:
            by_key[key] = c
            continue
        # Prefer entry with amount_hint / later decided_at
        if c.get("amount_hint") is not None and prev.get("amount_hint") is None:
            by_key[key] = c
        elif (c.get("decided_at") or "") > (prev.get("decided_at") or ""):
            by_key[key] = c
    return list(by_key.values())


def filter_pending(cands: list[dict], resolved: set[str]) -> list[dict]:
    pending = []
    for c in cands:
        did = c.get("decision_id")
        if did and str(did) in resolved:
            continue
        pending.append(c)
    return pending


def message_fr_for(c: dict) -> str:
    pair = c.get("pair") or "?"
    return f"Signal d’achat {pair} en attente — Risk doit valider"


def build_wake(pending: list[dict]) -> dict:
    checked = now_iso()
    if not pending:
        return {
            "checked_at": checked,
            "alerted": False,
            "pending_count": 0,
            "message_fr": None,
            "note": (
                "Idle — aucun achat Predict en attente de Risk "
                "(Scan ne déclenche pas cette alerte)."
            ),
        }
    # Primary = most recent decided_at, else first
    pending_sorted = sorted(
        pending,
        key=lambda x: str(x.get("decided_at") or ""),
        reverse=True,
    )
    primary = pending_sorted[0]
    wake = {
        "checked_at": checked,
        "alerted": True,
        "decided_at": primary.get("decided_at"),
        "pair": primary.get("pair"),
        "decision_id": primary.get("decision_id"),
        "side": primary.get("side") or "buy",
        "amount_hint": primary.get("amount_hint"),
        "message_fr": message_fr_for(primary),
        "source": primary.get("source"),
        "decision": primary.get("decision"),
        "pending_count": len(pending),
    }
    if len(pending) > 1:
        wake["others"] = [
            {
                "pair": p.get("pair"),
                "decision_id": p.get("decision_id"),
                "decided_at": p.get("decided_at"),
                "amount_hint": p.get("amount_hint"),
                "source": p.get("source"),
            }
            for p in pending_sorted[1:]
        ]
    return wake


def main() -> int:
    cands: list[dict] = []
    predict = load_json(LAST_PREDICT)
    if isinstance(predict, dict):
        cands.extend(collect_from_predict(predict))
    if DECISION_LOG.exists():
        try:
            cands.extend(collect_from_decision_log(DECISION_LOG.read_text()))
        except OSError:
            pass
    cands.extend(collect_from_handoffs())

    cands = dedupe_candidates(cands)
    resolved = load_resolved_ids()
    pending = filter_pending(cands, resolved)
    wake = build_wake(pending)

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(wake, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps(wake, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
