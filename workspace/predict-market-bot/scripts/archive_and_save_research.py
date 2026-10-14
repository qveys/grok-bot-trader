#!/usr/bin/env python3
"""Archive state/last_research.json with dated name, then write the new brief."""
from __future__ import annotations
import json
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path("/workspace/predict-market-bot")
LAST = ROOT / "state" / "last_research.json"
BRIEFS = ROOT / "state" / "research_briefs"
TZ = ZoneInfo("Europe/Brussels")

def stamp_from_payload(data: dict) -> str:
    t = data.get("briefed_at") or ""
    if "T" in t:
        date, rest = t.split("T", 1)
        hhmm = rest[:5].replace(":", "")
        return f"{date}_{hhmm}"
    now = datetime.now(TZ)
    return now.strftime("%Y-%m-%d_%H%M")

def archive_previous() -> Path | None:
    if not LAST.exists() or LAST.stat().st_size == 0:
        return None
    old = json.loads(LAST.read_text())
    stamp = stamp_from_payload(old)
    BRIEFS.mkdir(parents=True, exist_ok=True)
    dest = BRIEFS / f"{stamp}_last_research.json"
    # avoid overwrite if same stamp already archived
    if dest.exists():
        n = 2
        while True:
            alt = BRIEFS / f"{stamp}_last_research_v{n}.json"
            if not alt.exists():
                dest = alt
                break
            n += 1
    dest.write_text(json.dumps(old, ensure_ascii=False, indent=2) + "\n")
    return dest

def save_new(payload: dict) -> Path:
    BRIEFS.mkdir(parents=True, exist_ok=True)
    archived = archive_previous()
    LAST.parent.mkdir(parents=True, exist_ok=True)
    LAST.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
    stamp = stamp_from_payload(payload)
    dated = BRIEFS / f"{stamp}_last_research.json"
    dated.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
    print(f"archived_previous={archived}")
    print(f"last={LAST}")
    print(f"dated_copy={dated}")
    return LAST

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("usage: archive_and_save_research.py <new.json|->", file=sys.stderr)
        sys.exit(2)
    src = sys.argv[1]
    raw = sys.stdin.read() if src == "-" else Path(src).read_text()
    save_new(json.loads(raw))
