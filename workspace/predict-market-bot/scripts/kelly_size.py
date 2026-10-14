#!/usr/bin/env python3
"""Kelly criterion position sizing CLI (stdlib only)."""

from __future__ import annotations

import argparse
import json
import sys


def kelly_fraction(p: float, b: float) -> float:
    """Full Kelly fraction f* = (p*b - (1-p)) / b. Clamp to >= 0."""
    if b <= 0:
        return 0.0
    f_star = (p * b - (1.0 - p)) / b
    return max(0.0, f_star)


def size_from_kelly(
    p: float, b: float, bankroll: float, fraction: float = 0.25
) -> dict:
    full_f = kelly_fraction(p, b)
    fractional_f = fraction * full_f
    size_eur = fractional_f * bankroll
    return {
        "full_kelly_f": round(full_f, 8),
        "fractional_f": round(fractional_f, 8),
        "size_eur": round(size_eur, 4),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Kelly position size calculator")
    parser.add_argument("--p", type=float, required=True, help="Model win probability")
    parser.add_argument(
        "--b",
        type=float,
        required=True,
        help="Net odds received on win (decimal net payout ratio)",
    )
    parser.add_argument("--bankroll", type=float, required=True, help="Bankroll in EUR")
    parser.add_argument(
        "--fraction",
        type=float,
        default=0.25,
        help="Fractional Kelly multiplier (default 0.25 = quarter-Kelly)",
    )
    args = parser.parse_args()

    if not (0.0 <= args.p <= 1.0):
        print(json.dumps({"error": "p must be in [0,1]"}), file=sys.stderr)
        return 1
    if args.b <= 0:
        print(json.dumps({"error": "b must be > 0"}), file=sys.stderr)
        return 1
    if args.bankroll < 0:
        print(json.dumps({"error": "bankroll must be >= 0"}), file=sys.stderr)
        return 1
    if args.fraction < 0:
        print(json.dumps({"error": "fraction must be >= 0"}), file=sys.stderr)
        return 1

    result = size_from_kelly(args.p, args.b, args.bankroll, args.fraction)
    print(json.dumps(result))
    return 0


if __name__ == "__main__":
    sys.exit(main())
