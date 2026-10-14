#!/usr/bin/env python3
"""Risk validation CLI — rejects trades that breach config limits or kill switch."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = ROOT / "config.json"
MODE_PATH = ROOT / "MODE"

# Import sibling kelly_size without requiring package install
sys.path.insert(0, str(ROOT / "scripts"))
from kelly_size import kelly_fraction, size_from_kelly  # noqa: E402


def load_config() -> dict:
    return json.loads(CONFIG_PATH.read_text())


def load_trade(args: argparse.Namespace) -> dict:
    if args.trade:
        return json.loads(Path(args.trade).read_text())
    raw = sys.stdin.read()
    if not raw.strip():
        raise SystemExit("No trade JSON on stdin and no --trade path given")
    return json.loads(raw)


def validate(trade: dict, cfg: dict) -> dict:
    reasons: list[str] = []
    risk = cfg.get("risk", {})
    predict = cfg.get("predict", {})
    min_edge = float(predict.get("min_edge", 0.04))
    kelly_frac = float(risk.get("kelly_fraction", 0.25))
    max_pos_pct = float(risk.get("max_position_pct", 0.05))
    max_exposure_pct = float(risk.get("max_total_exposure_pct", 0.25))
    max_dd = float(risk.get("max_drawdown_pct", 0.08))
    max_daily_loss = float(risk.get("max_daily_loss_pct", 0.15))
    max_concurrent = int(risk.get("max_concurrent_positions", 15))

    p_model = float(trade["p_model"])
    p_market = float(trade["p_market"])
    bankroll = float(trade["bankroll"])
    proposed = float(trade["proposed_size_eur"])
    existing_exposure = float(trade.get("existing_exposure_eur", 0))
    current_dd = float(trade.get("current_drawdown_pct", 0))
    daily_loss = float(trade.get("daily_loss_pct", 0))
    open_count = int(trade.get("open_positions_count", 0))

    # Kill switch
    stop_path = Path(cfg.get("kill_switch_path", str(ROOT / "STOP")))
    if stop_path.exists():
        reasons.append(f"kill switch STOP present at {stop_path}")

    # MODE gate
    mode = MODE_PATH.read_text().strip() if MODE_PATH.exists() else ""
    if mode not in ("paper", "live"):
        reasons.append(f"MODE must be paper or live, got {mode!r}")

    # Edge
    edge = p_model - p_market
    # 9 oct 14h26 (Quentin) : min_edge vaut pour le réel seulement, pas en simu.
    edge_live_only = predict.get("applies_to") == "live_only"
    if edge <= min_edge and not (edge_live_only and mode == "paper"):
        reasons.append(f"edge {edge:.4f} <= min_edge {min_edge}")

    # Kelly quarter-Kelly max size
    # For binary markets priced at p_market, net odds b ≈ (1 - p_market) / p_market
    # when buying YES at price p_market (stake p_market, win 1 => net b = (1-p)/p).
    p_mkt = max(min(p_market, 0.9999), 0.0001)
    b = (1.0 - p_mkt) / p_mkt
    kelly_result = size_from_kelly(p_model, b, bankroll, kelly_frac)
    kelly_max = kelly_result["size_eur"]

    pos_cap = max_pos_pct * bankroll
    exposure_room = max(0.0, max_exposure_pct * bankroll - existing_exposure)
    max_size = min(kelly_max, pos_cap, exposure_room)

    if proposed > kelly_max + 1e-9:
        reasons.append(
            f"proposed_size_eur {proposed} > kelly max {kelly_max:.4f} "
            f"(fraction={kelly_frac})"
        )
    if proposed > pos_cap + 1e-9:
        reasons.append(
            f"proposed_size_eur {proposed} > max_position_pct*bankroll {pos_cap:.4f}"
        )
    if existing_exposure + proposed > max_exposure_pct * bankroll + 1e-9:
        reasons.append(
            f"exposure+size {existing_exposure + proposed:.4f} > "
            f"max_total_exposure {max_exposure_pct * bankroll:.4f}"
        )
    if current_dd >= max_dd:
        reasons.append(f"drawdown {current_dd:.4f} >= max_drawdown_pct {max_dd}")
    if daily_loss >= max_daily_loss:
        reasons.append(
            f"daily_loss_pct {daily_loss:.4f} >= max_daily_loss_pct {max_daily_loss}"
        )
    if open_count >= max_concurrent:
        reasons.append(
            f"open_positions_count {open_count} >= max_concurrent {max_concurrent}"
        )

    ok = len(reasons) == 0
    return {
        "ok": ok,
        "reasons": reasons,
        "max_size_eur": round(max(0.0, max_size), 4),
        "edge": round(edge, 6),
        "kelly": kelly_result,
        "mode": mode,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate trade against risk rules")
    parser.add_argument("--trade", type=str, help="Path to trade JSON file")
    args = parser.parse_args()

    try:
        cfg = load_config()
        trade = load_trade(args)
        result = validate(trade, cfg)
    except (KeyError, ValueError, json.JSONDecodeError, OSError) as e:
        out = {"ok": False, "reasons": [f"validation error: {e}"], "max_size_eur": 0.0}
        print(json.dumps(out))
        return 1

    # Print only the required fields for the contract, plus helpful extras
    print(
        json.dumps(
            {
                "ok": result["ok"],
                "reasons": result["reasons"],
                "max_size_eur": result["max_size_eur"],
            }
        )
    )
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
