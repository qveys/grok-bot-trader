#!/usr/bin/env python3
"""Pousse vers Cloudflare le paquet commun du mode « quasi direct » : site/data/{prices,summary,trades,
performance,research,news}.json (prix du collecteur 30 s + données des bots), seulement s'il a changé.
- D1 (prévu) : une ligne par fichier modifié, à chaque changement (≈ toutes les 30 s pour les prix).
- KV (provisoire, si le jeton n'a pas D1) : UN seul blob, au plus toutes les 2 min (KV gratuit = 1 000 écritures/jour).
Garde-fou : rien n'est poussé si check_secrets.py trouve quelque chose. Le jeton n'est jamais affiché."""
import datetime, hashlib, json, os, subprocess, sys, time, urllib.request, urllib.error
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from cf_api import call, errs, ACC, _OP
DASH = os.path.abspath(os.path.join(HERE, "..", ".."))
DATA = os.path.join(DASH, "site", "data")
FILES = ["prices", "summary", "trades", "performance", "research", "news"]
STATE = os.path.join(HERE, ".push_state.json")
SQL = ("INSERT INTO live_files(name, pushed_at, sha, body) VALUES(?1, ?2, ?3, ?4) "
       "ON CONFLICT(name) DO UPDATE SET pushed_at=excluded.pushed_at, sha=excluded.sha, body=excluded.body")
DAY_CAP = {"d1": 90000, "kv": 950}

def kv_put(ns, key, body):
    tok = os.environ.get("CLOUDFLARE_D1_API_TOKEN") or os.environ["CLOUDFLARE_API_TOKEN"]
    req = urllib.request.Request(f"https://api.cloudflare.com/client/v4/accounts/{ACC}/storage/kv/namespaces/{ns}/values/{key}",
                                 data=body.encode(), method="PUT", headers={"Authorization": "Bearer " + tok, "Content-Type": "text/plain; charset=utf-8"})
    try:
        r = _OP.open(req, timeout=40); return r.status, json.load(r)
    except urllib.error.HTTPError as e:
        return e.code, {}

def main():
    try:
        conf = json.load(open(os.path.join(HERE, "live.json")))
    except OSError:
        return print("mode direct pas configuré (cloudflare/d1/setup.py ou setup_kv.py)")
    prov = conf.get("provider")
    try:
        state = json.load(open(STATE))
    except Exception:
        state = {}
    today = datetime.date.today().isoformat()
    if state.get("_day") != today:
        state.update({"_day": today, "_writes": 0})
    if state.get("_provider") != prov:  # changement KV → D1 : tout repousser
        state = {"_day": today, "_writes": 0, "_provider": prov}
    if time.time() - state.get("_last", 0) < conf.get("min_interval_s", 0):
        return
    files, todo = {}, []
    for n in FILES:
        try:
            body = json.dumps(json.load(open(os.path.join(DATA, n + ".json"), encoding="utf-8")), ensure_ascii=False, separators=(",", ":"))
        except Exception:
            body = state.get("_body_" + n)  # fichier en cours d'écriture : on garde l'ancien (KV)
            if body is None: continue
        sha = hashlib.sha256(body.encode()).hexdigest()
        files[n] = (sha, body)
        if state.get(n) != sha:
            todo.append(n)
    if not todo:
        return
    if subprocess.run([sys.executable, os.path.join(DASH, "cloudflare", "check_secrets.py"), DATA]).returncode != 0:
        return print("REFUS : check_secrets.py a trouvé quelque chose de sensible, rien n'est poussé", file=sys.stderr)
    if state["_writes"] >= DAY_CAP.get(prov, 0):
        return print(f"limite de sécurité atteinte ({state['_writes']} écritures aujourd'hui), pause jusqu'à demain")
    now = datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")
    done = []
    if prov == "d1":
        for n in todo:
            sha, body = files[n]
            st, j = call("POST", f"/accounts/{ACC}/d1/database/{conf['database_id']}/query", {"sql": SQL, "params": [n, now, sha, body]}, timeout=40)
            if st == 200 and j.get("success"):
                state[n] = sha; state["_writes"] += 1; done.append(n)
            else:
                print(f"{now} échec {n}: {st} {errs(j)}", file=sys.stderr)
    elif prov == "kv":
        blob = '{"pushed_at":' + json.dumps(now) + ',"files":{' + ",".join(json.dumps(n) + ":" + files[n][1] for n in files) + "}}"
        st, j = kv_put(conf["namespace_id"], "live", blob)
        if st == 200 and j.get("success"):
            for n in files: state[n] = files[n][0]
            state["_writes"] += 1; done = todo
        else:
            print(f"{now} échec KV: {st} {errs(j)}", file=sys.stderr)
    if done:
        state["_last"] = time.time()
        print(f"{now} [{prov}] poussé: {','.join(done)} (écritures du jour: {state['_writes']})")
    json.dump(state, open(STATE, "w"))

if __name__ == "__main__":
    main()
