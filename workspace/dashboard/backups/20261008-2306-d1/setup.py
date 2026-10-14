#!/usr/bin/env python3
"""Active le mode « quasi direct » : crée la base D1, la table, et la relie au projet Pages (binding LIVE_DB,
production + aperçus). Idempotent. Jeton : env CLOUDFLARE_API_TOKEN (droits Pages: Edit + D1: Edit), jamais affiché."""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cf_api import call, errs, ACC
NAME, PROJECT, BINDING = "pm-pipeline-live", "pm-pipeline-tableau", "LIVE_DB"
CONF = os.path.join(os.path.dirname(os.path.abspath(__file__)), "live.json")

st, j = call("GET", f"/accounts/{ACC}/d1/database?name={NAME}")
if st != 200:
    sys.exit(f"Lecture D1 refusée ({st} {errs(j)}) : le jeton n'a pas le droit « D1: Edit ».")
db = next((d for d in j.get("result") or [] if d.get("name") == NAME), None)
if not db:
    st, j = call("POST", f"/accounts/{ACC}/d1/database", {"name": NAME})
    if st != 200:
        sys.exit(f"Création D1 refusée ({st} {errs(j)})")
    db = j["result"]
    print("base D1 créée :", NAME)
else:
    print("base D1 déjà là :", NAME)
uuid = db["uuid"]
schema = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "schema.sql")).read().strip()
st, j = call("POST", f"/accounts/{ACC}/d1/database/{uuid}/query", {"sql": schema})
print("table live_files :", "ok" if st == 200 and j.get("success") else f"ERREUR {st} {errs(j)}")
dc = {"d1_databases": {BINDING: {"id": uuid}}}
st, j = call("PATCH", f"/accounts/{ACC}/pages/projects/{PROJECT}", {"deployment_configs": {"production": dc, "preview": dc}})
ok = st == 200 and all(((j.get("result") or {}).get("deployment_configs") or {}).get(e, {}).get("d1_databases", {}).get(BINDING) for e in ("production", "preview"))
print("binding LIVE_DB sur Pages (production + aperçus) :", "ok" if ok else f"ERREUR {st} {errs(j)}")
json.dump({"provider": "d1", "database_id": uuid, "name": NAME, "binding": BINDING, "project": PROJECT, "min_interval_s": 0}, open(CONF, "w"), indent=1)
print("config écrite :", CONF, "(identifiant de base, pas un secret). Il faut redéployer pour que le binding s'applique.")
