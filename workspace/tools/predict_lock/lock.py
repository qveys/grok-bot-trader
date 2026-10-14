#!/usr/bin/env python3
"""Verrou simple pour qu'une seule décision Predict se fasse à la fois.
  lock.py prendre <motif>  -> code 0 si pris ; code 1 + « déjà traité dans … » si un autre réveil est en cours (< 10 min)
  lock.py rendre <D-0xx>   -> libère et note le numéro de décision
  lock.py prochain         -> plus grand numéro D-xxx du carnet + 1
"""
import json, sys, time, pathlib
P = pathlib.Path("/workspace/tools/predict_lock/state.json")
def load():
    try: return json.loads(P.read_text())
    except Exception: return {}
cmd = sys.argv[1] if len(sys.argv) > 1 else ""
arg = " ".join(sys.argv[2:])
d = load(); now = time.time()
if cmd == "prendre":
    if d.get("actif") and now - d.get("depuis", 0) < 600:
        print(f"déjà en cours depuis {int(now-d['depuis'])} s (motif : {d.get('motif')}) — écrire « déjà traité dans {d.get('decision') or 'la décision en cours'} »"); sys.exit(1)
    if not d.get("actif") and now - d.get("fini", 0) < 300 and d.get("decision"):
        print(f"déjà traité dans {d['decision']} il y a {int(now-d['fini'])} s"); sys.exit(1)
    P.write_text(json.dumps({"actif": True, "depuis": now, "motif": arg})); print("ok"); sys.exit(0)
if cmd == "rendre":
    d.update({"actif": False, "fini": now, "decision": arg}); P.write_text(json.dumps(d)); print("ok"); sys.exit(0)
if cmd == "prochain":
    import re
    txt = pathlib.Path("/workspace/predict-market-bot/knowledge/decision_log.md").read_text()
    n = max(int(x) for x in re.findall(r"D-0*(\d{2,4})", txt))
    print(f"D-{n+1:03d}"); sys.exit(0)
print(__doc__); sys.exit(2)
