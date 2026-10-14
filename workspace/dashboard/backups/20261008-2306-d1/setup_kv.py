#!/usr/bin/env python3
"""Solution provisoire tant que le jeton n'a pas « D1: Edit » : Workers KV (binding LIVE).
Crée/retrouve le namespace KV, le relie au projet Pages (production + aperçus), écrit d1/live.json.
KV gratuit = 1 000 écritures/jour → la box pousse au plus toutes les 2 min (≤ 720/jour)."""
import json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from cf_api import call, errs, ACC
TITLE, PROJECT, BINDING = "pm-pipeline-live", "pm-pipeline-tableau", "LIVE"
st, j = call("GET", f"/accounts/{ACC}/storage/kv/namespaces?per_page=100")
if st != 200: sys.exit(f"KV refusé ({st} {errs(j)})")
ns = next((n for n in j.get("result") or [] if n.get("title") == TITLE), None)
if not ns:
    st, j = call("POST", f"/accounts/{ACC}/storage/kv/namespaces", {"title": TITLE})
    if st != 200: sys.exit(f"création KV refusée ({st} {errs(j)})")
    ns = j["result"]; print("namespace KV créé :", TITLE)
else: print("namespace KV déjà là :", TITLE)
dc = {"kv_namespaces": {BINDING: {"namespace_id": ns["id"]}}}
st, j = call("PATCH", f"/accounts/{ACC}/pages/projects/{PROJECT}", {"deployment_configs": {"production": dc, "preview": dc}})
cfg = (j.get("result") or {}).get("deployment_configs") or {}
ok = st == 200 and all(cfg.get(e, {}).get("kv_namespaces", {}).get(BINDING) for e in ("production", "preview"))
print("binding LIVE sur Pages (production + aperçus) :", "ok" if ok else f"ERREUR {st} {errs(j)}")
path = os.path.join(HERE, "live.json")
cur = json.load(open(path)) if os.path.exists(path) else {}
if cur.get("provider") != "d1":
    json.dump({"provider": "kv", "namespace_id": ns["id"], "binding": BINDING, "project": PROJECT, "min_interval_s": 120}, open(path, "w"), indent=1)
print("config :", path, "— redéployer pour activer le binding.")
