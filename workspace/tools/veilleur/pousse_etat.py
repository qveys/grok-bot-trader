#!/usr/bin/env python3
"""Résumé compact (lecture seule) des positions ouvertes et zones actives pour pm-sonnette-cf (observation)."""
import hashlib, json
from pathlib import Path

GUARD = Path("/workspace/predict-market-bot/guardian/state.json")
ZONES = Path("/workspace/predict-market-bot/state/zones_reveil.json")


def construire():
    try:
        st = json.loads(GUARD.read_text())
    except Exception:
        st = {}
    pos = []
    for p in st.get("positions") or []:
        if str(p.get("status")) != "open":
            continue
        pos.append({"id": p.get("id"), "pair": p.get("pair"), "side": p.get("side"), "idea_type": p.get("idea_type") or p.get("kind"),
                    "stop": p.get("stop_price_eur") or p.get("stop_price") or p.get("safety_price"),
                    "target": p.get("target_price"), "deadline": p.get("deadline") or p.get("deadline_at"),
                    "decision_id": p.get("decision_id"), "mode": "simulation" if "paper" in str(p.get("id")) else "reel"})
    try:
        zs = json.loads(ZONES.read_text()).get("zones") or []
    except Exception:
        zs = []
    zones = [{k: z.get(k) for k in ("id", "paire", "sens", "prix", "bot", "expire", "actif")} for z in zs if z.get("actif", True)]
    etat = {"positions": pos, "zones": zones}
    h = hashlib.sha256(json.dumps(etat, sort_keys=True).encode()).hexdigest()[:16]
    return etat, h


if __name__ == "__main__":
    e, h = construire()
    print(h, json.dumps(e, ensure_ascii=False))
