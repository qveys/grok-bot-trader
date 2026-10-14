#!/usr/bin/env python3
"""Envoie un battement au Worker pm-veilleur toutes les 60 s (lecture seule des fichiers des bots).
secrets.env (VEILLEUR_URL, VEILLEUR_SECRET) est relu à chaque tour ; rien n'est jamais affiché."""
import json, os, sys, time, urllib.request
from datetime import datetime, timezone
from pathlib import Path

DIR = Path(__file__).resolve().parent
SECRETS = DIR / "secrets.env"
SON = Path("/workspace/tools/sonnette/state")
RISK_HB = Path("/workspace/predict-market-bot/state/watch_stops_heartbeat.json")
INTERVAL = float(os.environ.get("VEILLEUR_INTERVAL", "60"))
LOG = DIR / "state" / "battement.log"


def log(msg):
    LOG.parent.mkdir(exist_ok=True)
    line = f"{datetime.now().astimezone().isoformat(timespec='seconds')} {msg}\n"
    try:
        if LOG.exists() and LOG.stat().st_size > 512_000:
            LOG.replace(LOG.with_suffix(".log.1"))
        with LOG.open("a") as f:
            f.write(line)
    except OSError:
        pass


def secrets():
    d = {}
    try:
        for l in SECRETS.read_text().splitlines():
            if "=" in l and not l.lstrip().startswith("#"):
                k, v = l.split("=", 1)
                d[k.strip()] = v.strip().strip('"').strip("'")
    except OSError:
        pass
    return d


def alive(pid):
    try:
        os.kill(int(pid), 0)
        return True
    except (OSError, ValueError, TypeError):
        return False


def age_s(ts):
    try:
        return round(time.time() - datetime.fromisoformat(ts).timestamp(), 1)
    except Exception:
        return None


def jload(p):
    try:
        return json.loads(Path(p).read_text())
    except Exception:
        return {}


def payload():
    shb = jload(SON / "sonnette_heartbeat.json")
    try:
        spid = (SON / "sonnette.pid").read_text().strip()
    except OSError:
        spid = shb.get("pid")
    rhb = jload(RISK_HB)
    return {
        "ts_box": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "sonnette_vivante": alive(spid),
        "sonnette_age_s": age_s(shb.get("ts")),
        "risk_vivant": alive(rhb.get("pid")) if rhb.get("pid") else False,
        "risk_age_s": age_s(rhb.get("ts")),
        "risk_ouvertes_live": rhb.get("open_live") or 0,
        "risk_ouvertes_paper": rhb.get("open_paper") or 0,
        "risk_action": rhb.get("action"),
    }


def send_once():
    s = secrets()
    url, sec = s.get("VEILLEUR_URL"), s.get("VEILLEUR_SECRET")
    if not url or not sec:
        return "URL ou secret absent (Worker pas encore déployé)"
    body = json.dumps(payload()).encode()
    req = urllib.request.Request(url.rstrip("/") + "/battement", data=body, method="POST",
                                 headers={"Authorization": f"Bearer {sec}", "Content-Type": "application/json",
                                          "User-Agent": "pm-veilleur-battement/1"})
    with urllib.request.urlopen(req, timeout=20) as r:
        return f"ok {r.status} {r.read(200).decode(errors='replace')}".replace("\n", " ")


_obs = {"hash": None, "t": 0.0}


def pousse_obs():
    """Prototype pm-sonnette-cf : envoie positions/zones si changées (ou toutes les 10 min). Optionnel."""
    s = secrets()
    url, sec = s.get("VEILLEUR_OBS_URL"), s.get("VEILLEUR_SECRET")
    if not url or not sec:
        return None
    import pousse_etat
    etat, h = pousse_etat.construire()
    if h == _obs["hash"] and time.time() - _obs["t"] < 600:
        return None
    req = urllib.request.Request(url.rstrip("/") + "/etat-bots", data=json.dumps(etat).encode(), method="POST",
                                 headers={"Authorization": f"Bearer {sec}", "Content-Type": "application/json",
                                          "User-Agent": "pm-veilleur-battement/1"})
    with urllib.request.urlopen(req, timeout=20) as r:
        r.read(200)
    _obs.update(hash=h, t=time.time())
    return f"obs ok {h}"


def main():
    once = "--once" in sys.argv
    last = None
    while True:
        try:
            res = send_once()
        except Exception as e:  # noqa: BLE001 — ne jamais s'arrêter
            res = f"erreur {type(e).__name__}: {str(e)[:150]}"
        # log seulement les changements d'état (+ 1 ligne/heure)
        try:
            o = pousse_obs()
            if o and once:
                print(o)
        except Exception as e:  # noqa: BLE001
            log(f"obs erreur {type(e).__name__}: {str(e)[:150]}")
        key = res.split(" ")[0] if res.startswith("ok") else res
        if once or key != last or int(time.time()) % 3600 < INTERVAL:
            log(res)
        last = key
        if once:
            print(res)
            return 0 if res.startswith("ok") else 1
        time.sleep(INTERVAL)


if __name__ == "__main__":
    sys.exit(main())
