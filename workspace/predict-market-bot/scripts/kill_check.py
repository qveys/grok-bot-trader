#!/usr/bin/env python3
"""Kill-switch check: exit 0 if trading allowed, exit 2 if STOP present."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = ROOT / "config.json"
DEFAULT_STOP = ROOT / "STOP"


def stop_path() -> Path:
    try:
        cfg = json.loads(CONFIG_PATH.read_text())
        return Path(cfg.get("kill_switch_path", str(DEFAULT_STOP)))
    except (OSError, json.JSONDecodeError):
        return DEFAULT_STOP


def main() -> int:
    path = stop_path()
    if path.exists():
        print(f"KILL: STOP present at {path} — trading blocked")
        return 2
    mode_file = ROOT / "MODE"
    mode = mode_file.read_text().strip() if mode_file.exists() else "unknown"
    print(f"OK: trading allowed (no STOP); MODE={mode}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
