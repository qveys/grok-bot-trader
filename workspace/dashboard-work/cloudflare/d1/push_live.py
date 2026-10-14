#!/usr/bin/env python3
"""Pousse vers Cloudflare le paquet commun du mode « quasi direct » : site/data/{prices,summary,trades,
performance,research,news}.json (prix du collecteur 30 s + données des bots), seulement s'il a changé.
- D1 (binding LIVE_DB) : une ligne par fichier modifié, à chaque changement (≈ toutes les 30 s pour les prix). Seule cible.
Garde-fou : rien n'est poussé si check_secrets.py trouve quelque chose. Le jeton n'est jamais affiché."""
import datetime, hashlib, json, os, subprocess, sys, time
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from cf_api import call, errs, ACC
DASH = os.path.abspath(os.path.join(HERE, "..", ".."))
DATA = os.path.join(DASH, "site", "data")
FILES = ["prices", "summary", "trades", "performance", "research", "news"]
STATE = os.path.join(HERE, ".push_state.json")
SQL = ("INSERT INTO live_files(name, pushed_at, sha, body) VALUES(?1, ?2, ?3, ?4) "
       "ON CONFLICT(name) DO UPDATE SET pushed_at=excluded.pushed_at, sha=excluded.sha, body=excluded.body")
DAY_CAP = {"d1": 90000}

def main():
    try:
        conf = json.load(open(os.path.join(HERE, "live.json")))
    except OSError:
        return print("mode direct pas configuré (cloudflare/d1/setup.py)")
    prov = conf.get("provider")
    if prov != "d1":
        return print(f"fournisseur {prov!r} non pris en charge : relancer cloudflare/d1/setup.py (D1 seulement)", file=sys.stderr)
    try:
        state = json.load(open(STATE))
    except Exception:
        state = {}
    today = datetime.date.today().isoformat()
    if state.get("_day") != today:
        state.update({"_day": today, "_writes": 0})
    if state.get("_provider") != prov:  # changement de fournisseur : tout repousser
        state = {"_day": today, "_writes": 0, "_provider": prov}
    if time.time() - state.get("_last", 0) < conf.get("min_interval_s", 0):
        return
    files, todo = {}, []
    for n in FILES:
        try:
            body = json.dumps(json.load(open(os.path.join(DATA, n + ".json"), encoding="utf-8")), ensure_ascii=False, separators=(",", ":"))
        except Exception:
            continue  # fichier en cours d'écriture : on réessaie au tour suivant (10 s)
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
    for n in todo:
        sha, body = files[n]
        st, j = call("POST", f"/accounts/{ACC}/d1/database/{conf['database_id']}/query", {"sql": SQL, "params": [n, now, sha, body]}, timeout=40)
        if st == 200 and j.get("success"):
            state[n] = sha; state["_writes"] += 1; done.append(n)
        else:
            print(f"{now} échec {n}: {st} {errs(j)}", file=sys.stderr)
    if done:
        state["_last"] = time.time()
        print(f"{now} [{prov}] poussé: {','.join(done)} (écritures du jour: {state['_writes']})")
    json.dump(state, open(STATE, "w"))

if __name__ == "__main__":
    main()
