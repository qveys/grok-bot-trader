#!/usr/bin/env python3
"""Journal commun des passages de routines.
Usage : python3 /workspace/tools/routine_log/log.py <bot> "<routine>" <demarre|fini|arret> ["note courte"]
Écrit une ligne dans /workspace/predict-market-bot/state/routine_runs.jsonl
"""
import json, sys, datetime, os
from zoneinfo import ZoneInfo
PATH = "/workspace/predict-market-bot/state/routine_runs.jsonl"
if len(sys.argv) < 4 or sys.argv[3] not in ("demarre", "fini", "arret"):
    sys.exit(__doc__)
bot, routine, etape = sys.argv[1], sys.argv[2], sys.argv[3]
note = sys.argv[4] if len(sys.argv) > 4 else ""
line = {"ts": datetime.datetime.now(ZoneInfo("Europe/Brussels")).isoformat(timespec="seconds"),
        "bot": bot, "routine": routine, "etape": etape, "note": note}
os.makedirs(os.path.dirname(PATH), exist_ok=True)
with open(PATH, "a") as f:
    f.write(json.dumps(line, ensure_ascii=False) + "\n")
print("ok")
