#!/usr/bin/env python3
"""Alertes de départ (breakout / accumulation) — OBSERVATION SEULEMENT.

Stdlib only. Never rings anybody, never places orders.

Every `verif_toutes_s` (default 10 min) the sonnette calls Departs.maybe_check():
  * ONE batch fetch: read-only `revx market candles <PAIR> --interval 15m --since <24h>` for
    BTC-EUR, ETH-EUR, SOL-EUR (the candles endpoint takes one symbol, so 1 batch = 3 calls,
    no ticker call). Tests inject `_fetch_candles` (no network).
  * analyse() on CLOSED 15m bars:
      - variation_pct = close of last closed bar vs close `fenetre_min` earlier
      - ratio_volume  = mean volume of the window bars / mean volume of the
                        `volume_moyenne_barres` bars before the window
      - haut_24h / bas_24h from the 24h of bars (incl. the bar in progress), prix = latest close
    hausse       : variation > +mouvement_min_pct, prix within proche_extreme_24h_pct of haut_24h,
                   ratio_volume > volume_ratio_min, >= barres_meme_sens_min green bars in the
                   window AND the last closed 15m bar green (confirmation)
    baisse       : mirror (red bars, near bas_24h)
    accumulation : ratio_volume >= accumulation_volume_ratio_min and |variation| < accumulation_mouvement_max_pct
  * Each detection → state/departs.jsonl (anti-spam: 1 per pair+type per `anti_spam_heures`).
  * Outcomes at +1h/+4h/+24h → state/departs_resultats.jsonl (price from the team collector
    ticks, read-only; fallback = the 15m candles already fetched). reussi = moved >= reussite_min_pct
    in the predicted direction (accumulation: either direction).
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

TZ = ZoneInfo("Europe/Brussels")
PAIRS = ("BTC-EUR", "ETH-EUR", "SOL-EUR")
TYPES = ("hausse", "baisse", "accumulation")
INTERVAL_MS = {"1m": 60_000, "5m": 300_000, "15m": 900_000, "30m": 1_800_000, "1h": 3_600_000}

DEFAULTS: dict = {
    "actif": True,
    "mode": "observe",                  # "observe" (now) | "ring" (future: not wired yet → still observe)
    "verif_toutes_s": 600,              # one batch fetch every 10 min (not every 30 s)
    "intervalle": "15m",                # candle size (15m confirmation)
    "fenetre_min": 60,                  # recent window for the move / recent volume
    "mouvement_min_pct": 0.5,           # hausse: > +0.5 % ; baisse: < -0.5 %
    "proche_extreme_24h_pct": 3.0,      # within 3 % of the 24h high (hausse) / low (baisse)
    "volume_ratio_min": 1.2,            # recent volume > 1.2 × average
    "barres_meme_sens_min": 3,          # of the window bars (4 × 15m) in the same direction, last one included
    "accumulation_volume_ratio_min": 1.5,
    "accumulation_mouvement_max_pct": 0.3,
    "volume_moyenne_barres": 20,        # average volume = 20 bars (5 h) before the window
    "anti_spam_heures": 2,              # 1 detection per pair and type per 2 h
    "horizons_h": [1, 4, 24],
    "reussite_min_pct": 1.0,            # « ça a marché » = >= 1 % in the predicted direction
    "resultat_tolerance_min": 10,       # collector tick must be within 10 min after the target time
    "resultat_abandon_h": 3,            # no price found 3 h after the target → statut « manquant »
    "reessai_pause_s": 2,               # a failed pair is retried ONCE after 2 s (no extra call otherwise)
}


# ----------------------------------------------------------------- helpers
def _f(x) -> float | None:
    if isinstance(x, bool) or x is None:
        return None
    try:
        v = float(x)
    except (TypeError, ValueError):
        return None
    return v if v == v else None  # NaN guard


def _parse_ts(s) -> datetime | None:
    if not isinstance(s, str) or not s.strip():
        return None
    try:
        dt = datetime.fromisoformat(s.strip().replace("Z", "+00:00"))
    except ValueError:
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=TZ)


def _iso(dt: datetime) -> str:
    return dt.astimezone(TZ).isoformat(timespec="seconds")


def _ms(dt: datetime) -> int:
    return int(dt.timestamp() * 1000)


def _from_ms(ms: int) -> datetime:
    return datetime.fromtimestamp(ms / 1000, tz=timezone.utc).astimezone(TZ)


def fr_num(x: float, d: int = 2) -> str:
    return f"{x:.{d}f}".replace(".", ",")


def read_jsonl(path: Path) -> list[dict]:
    out = []
    try:
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    row = json.loads(line)
                except (json.JSONDecodeError, ValueError):
                    continue
                if isinstance(row, dict):
                    out.append(row)
    except OSError:
        pass
    return out


def append_jsonl(path: Path, row: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")


def parse_candles(raw) -> list[dict]:
    """revx JSON ({"data": [...]}) or a list → sorted [{start(ms), open, high, low, close, volume}]."""
    rows = raw.get("data") if isinstance(raw, dict) else raw
    out = {}
    for c in rows if isinstance(rows, list) else []:
        if not isinstance(c, dict):
            continue
        try:
            start = int(c.get("start") if c.get("start") is not None else c.get("timestamp"))
        except (TypeError, ValueError):
            continue
        vals = {k: _f(c.get(k)) for k in ("open", "high", "low", "close", "volume")}
        if any(v is None for v in vals.values()) or vals["close"] <= 0:
            continue
        out[start] = dict(vals, start=start)
    return [out[k] for k in sorted(out)]


def fetch_candles_revx(pair: str, since_ms: int, interval: str, revx_bin: str, proxy: str,
                       timeout_s: float = 25) -> list[dict]:
    """READ-ONLY market data (`revx market candles`). Raises RuntimeError on failure."""
    binp = revx_bin or "revx"
    if not Path(binp).exists() and not shutil.which(binp):
        raise RuntimeError("revx introuvable")
    env = dict(os.environ, HTTPS_PROXY=proxy, HTTP_PROXY=proxy, ALL_PROXY=proxy,
               PATH="/home/box/.local/bin:" + os.environ.get("PATH", ""))
    cmd = [binp, "market", "candles", pair, "--interval", interval, "--since", str(since_ms), "--json"]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout_s, env=env)
    except Exception as e:  # noqa: BLE001
        raise RuntimeError(f"revx candles {pair}: {type(e).__name__}") from None
    if proc.returncode != 0:
        err = " ".join((proc.stderr or proc.stdout or "").split())[:120]
        raise RuntimeError(f"revx candles {pair}: code {proc.returncode}" + (f" ({err})" if err else ""))
    raw = (proc.stdout or "").strip()
    starts = [i for i in (raw.find("{"), raw.find("[")) if i >= 0]
    try:
        data = json.loads(raw[min(starts):]) if starts else None
    except (json.JSONDecodeError, ValueError):
        data = None
    if data is None:
        raise RuntimeError(f"revx candles {pair}: réponse illisible")
    return parse_candles(data)


# ----------------------------------------------------------------- analysis
def analyse(candles: list[dict], now: datetime, dc: dict) -> dict:
    """Metrics + detected types for one pair. Pure function (no I/O)."""
    iv = INTERVAL_MS.get(str(dc.get("intervalle", "15m")), 900_000)
    now_ms = _ms(now)
    day = [c for c in candles if c["start"] + iv > now_ms - 24 * 3_600_000 and c["start"] <= now_ms]
    closed = [c for c in day if c["start"] + iv <= now_ms]
    w = max(1, int(round(float(dc["fenetre_min"]) * 60_000 / iv)))
    nb = max(1, int(dc["volume_moyenne_barres"]))
    if len(closed) < w + 1 + min(nb, 4):
        return {"erreur": f"pas assez de bougies ({len(closed)} fermées)", "types": []}
    window = closed[-w:]
    ref_close = closed[-w - 1]["close"]
    base = closed[-w - nb:-w] if len(closed) >= w + nb else closed[:-w]
    last = closed[-1]
    prix = day[-1]["close"]
    variation = (last["close"] / ref_close - 1.0) * 100.0
    vol_recent = sum(c["volume"] for c in window) / len(window)
    vol_avg = sum(c["volume"] for c in base) / len(base) if base else 0.0
    ratio = vol_recent / vol_avg if vol_avg > 0 else None
    haut = max(c["high"] for c in day)
    bas = min(c["low"] for c in day)
    dist_haut = (haut - prix) / haut * 100.0
    dist_bas = (prix - bas) / bas * 100.0
    verts = sum(1 for c in window if c["close"] > c["open"])
    rouges = sum(1 for c in window if c["close"] < c["open"])
    m = {
        "prix": prix,
        "prix_cloture_15m": last["close"],
        "barre_15m_fermee": _iso(_from_ms(last["start"])),
        "variation_pct": round(variation, 3),
        "ratio_volume": None if ratio is None else round(ratio, 3),
        "haut_24h": haut, "bas_24h": bas,
        "distance_haut_24h_pct": round(dist_haut, 3),
        "distance_bas_24h_pct": round(dist_bas, 3),
        "barres_vertes": verts, "barres_rouges": rouges, "barres_fenetre": w,
        "bougies_24h": len(day), "types": [],
    }
    if ratio is None:
        m["erreur"] = "volume moyen nul"
        return m
    mv, prox, vr = float(dc["mouvement_min_pct"]), float(dc["proche_extreme_24h_pct"]), float(dc["volume_ratio_min"])
    need = min(int(dc["barres_meme_sens_min"]), w)
    if (variation > mv and dist_haut <= prox and ratio > vr
            and verts >= need and last["close"] > last["open"]):
        m["types"].append("hausse")
    if (variation < -mv and dist_bas <= prox and ratio > vr
            and rouges >= need and last["close"] < last["open"]):
        m["types"].append("baisse")
    if ratio >= float(dc["accumulation_volume_ratio_min"]) and abs(variation) < float(dc["accumulation_mouvement_max_pct"]):
        m["types"].append("accumulation")
    return m


def reussi_for(kind: str, variation_pct: float, seuil: float) -> bool:
    if kind == "hausse":
        return variation_pct >= seuil
    if kind == "baisse":
        return variation_pct <= -seuil
    return abs(variation_pct) >= seuil  # accumulation: a 1 % exit, either direction


# ----------------------------------------------------------------- outcome prices
class TickReader:
    """Read-only collector ticks (price_ticks/YYYY-MM-DD.jsonl, Brussels date). Cached per check."""

    def __init__(self, ticks_dir: Path | None):
        self.dir = Path(ticks_dir) if ticks_dir else None
        self._cache: dict[str, dict[str, list]] = {}

    def _day(self, d) -> dict[str, list]:
        key = d.isoformat()
        if key not in self._cache:
            per: dict[str, list] = {}
            if self.dir is not None:
                for row in read_jsonl(self.dir / f"{key}.jsonl"):
                    pair = str(row.get("pair") or "").upper()
                    mid, ts = _f(row.get("mid")), _parse_ts(row.get("ts"))
                    if pair in PAIRS and mid and mid > 0 and ts:
                        per.setdefault(pair, []).append((ts, mid))
                for v in per.values():
                    v.sort(key=lambda x: x[0])
            self._cache[key] = per
        return self._cache[key]

    def price_at(self, pair: str, target: datetime, tol: timedelta) -> tuple[float | None, datetime | None]:
        t = target.astimezone(TZ)
        for d in sorted({t.date(), (t + tol).date()}):
            for ts, mid in self._day(d).get(pair, []):
                if target <= ts <= target + tol:
                    return mid, ts
        return None, None


def price_from_candles(candles: list[dict], target: datetime, iv_ms: int, now: datetime):
    """Open of the first bar starting at/after target (within one bar)."""
    t = _ms(target)
    for c in candles:
        if t <= c["start"] < t + iv_ms and c["start"] <= _ms(now):
            return c["open"], _from_ms(c["start"])
    return None, None


# ----------------------------------------------------------------- watcher
class Departs:
    def __init__(self, cfg: dict, state_dir: Path, log, ticks_dir: Path | None = None):
        self.cfg = cfg
        self.dc = dict(DEFAULTS, **(cfg.get("departs") or {}))
        self.sd = Path(state_dir)
        self.f_det = self.sd / "departs.jsonl"
        self.f_res = self.sd / "departs_resultats.jsonl"
        self.f_etat = self.sd / "departs_etat.json"
        self.log = log
        self.ticks_dir = ticks_dir
        self._last_check: datetime | None = None
        self._first_done = False
        self._fail_logged: dict[str, datetime] = {}
        self._mode_warned = False
        self.fetch_count = 0  # batch fetches (tests)
        inj = cfg.get("_fetch_candles")
        if inj is not None:
            self.fetch = inj
        elif cfg.get("revx_enabled"):
            revx_bin = cfg.get("revx_bin") or "/home/box/.local/bin/revx"
            proxy = cfg.get("proxy") or "http://127.0.0.1:8791"
            self.fetch = lambda pair, since_ms, interval: fetch_candles_revx(pair, since_ms, interval, revx_bin, proxy)
        else:
            self.fetch = None

    # ---- scheduling
    def due(self, now: datetime) -> bool:
        if self._last_check is None:
            return True
        el = (now - self._last_check).total_seconds()
        return el >= float(self.dc["verif_toutes_s"]) or el < 0

    def maybe_check(self, now: datetime, collector_prices: dict | None = None) -> dict:
        if not self.dc.get("actif", True):
            return {"actif": False}
        if self.fetch is None:
            return {"actif": True, "etat": "inactif (revx désactivé, pas de source de bougies)"}
        if not self.due(now):
            etat = self._read_etat()
            return {"actif": True, "mode": "observe", "derniere_verif": etat.get("derniere_verif"),
                    "prochaine_dans_s": round(float(self.dc["verif_toutes_s"]) - (now - self._last_check).total_seconds())}
        return self.check(now, collector_prices or {})

    # ---- one check = one batch fetch
    def check(self, now: datetime, collector_prices: dict) -> dict:
        now = now.astimezone(TZ)
        self._last_check = now
        dc = self.dc
        mode = str(dc.get("mode") or "observe").lower()
        if mode != "observe" and not self._mode_warned:
            self._mode_warned = True
            self.log("WARN", f"départs: mode « {mode} » pas encore branché — observation seulement (aucune sonnerie)", now)
        interval = str(dc.get("intervalle", "15m"))
        iv = INTERVAL_MS.get(interval, 900_000)
        since_ms = _ms(now) - 24 * 3_600_000 - iv
        self.fetch_count += 1
        candles: dict[str, list] = {}
        errors: dict[str, str] = {}
        for pair in PAIRS:
            try:
                try:
                    candles[pair] = parse_candles(self.fetch(pair, since_ms, interval))
                except Exception:  # noqa: BLE001 — one retry only (transient revx/proxy hiccup)
                    time.sleep(float(dc.get("reessai_pause_s", 2)))
                    candles[pair] = parse_candles(self.fetch(pair, since_ms, interval))
            except Exception as e:  # noqa: BLE001
                errors[pair] = str(e)[:160] or type(e).__name__
                last = self._fail_logged.get(pair)
                if last is None or (now - last).total_seconds() >= 3600:
                    self._fail_logged[pair] = now
                    self.log("WARN", f"départs: bougies {pair} illisibles ({errors[pair]}) — paire ignorée ce tour", now)
        metrics: dict[str, dict] = {}
        detections: list[dict] = []
        skipped: list[str] = []
        existing = read_jsonl(self.f_det)
        last_by: dict[str, datetime] = {}
        for d in existing:
            ts = _parse_ts(d.get("ts"))
            k = f"{d.get('paire')}:{d.get('type')}"
            if ts and (k not in last_by or ts > last_by[k]):
                last_by[k] = ts
        spam = timedelta(hours=float(dc["anti_spam_heures"]))
        for pair, cs in candles.items():
            m = analyse(cs, now, dc)
            metrics[pair] = m
            for kind in m.get("types") or []:
                k = f"{pair}:{kind}"
                if k in last_by and now - last_by[k] < spam:
                    skipped.append(k)
                    continue
                row = {
                    "id": f"DEP-{now:%Y%m%d-%H%M}-{pair.split('-')[0]}-{kind}",
                    "ts": _iso(now), "paire": pair, "type": kind, "mode": "observe",
                    "prix": m["prix"], "prix_cloture_15m": m["prix_cloture_15m"],
                    "prix_collecteur": collector_prices.get(pair),
                    "variation_pct": m["variation_pct"], "fenetre_min": int(dc["fenetre_min"]),
                    "ratio_volume": m["ratio_volume"],
                    "haut_24h": m["haut_24h"], "bas_24h": m["bas_24h"],
                    "distance_haut_24h_pct": m["distance_haut_24h_pct"],
                    "distance_bas_24h_pct": m["distance_bas_24h_pct"],
                    "barres_vertes": m["barres_vertes"], "barres_rouges": m["barres_rouges"],
                    "barre_15m_fermee": m["barre_15m_fermee"],
                    "source": f"revx market candles {interval}",
                    "sonnerie": False,
                }
                append_jsonl(self.f_det, row)
                last_by[k] = now
                detections.append(row)
                self.log("INFO", f"départ observé (pas de sonnerie): {pair} {kind} — variation "
                                 f"{fr_num(m['variation_pct'])} % en {int(dc['fenetre_min'])} min, volume "
                                 f"x{fr_num(m['ratio_volume'])}, à {fr_num(m['distance_haut_24h_pct'])} % du plus-haut 24h / "
                                 f"{fr_num(m['distance_bas_24h_pct'])} % du plus-bas 24h, prix {m['prix']}", now)
        resultats = self.record_outcomes(now, candles, iv)
        compact = {p: {k: m.get(k) for k in ("prix", "variation_pct", "ratio_volume", "distance_haut_24h_pct",
                                             "distance_bas_24h_pct", "types", "erreur") if m.get(k) is not None}
                   for p, m in metrics.items()}
        parts = []
        for p, m in metrics.items():
            if m.get("erreur") and m.get("ratio_volume") is None:
                parts.append(f"{p} {m['erreur']}")
                continue
            parts.append(f"{p} {m['prix']} var {fr_num(m['variation_pct'])} % vol x{fr_num(m['ratio_volume'] or 0)} "
                         f"haut-{fr_num(m['distance_haut_24h_pct'], 1)} % bas+{fr_num(m['distance_bas_24h_pct'], 1)} %"
                         + (f" → {','.join(m['types'])}" if m.get("types") else ""))
        lvl = "INFO"
        prefix = "départs: 1re vérif (données réelles) — " if not self._first_done else "départs: vérif — "
        self._first_done = True
        self.log(lvl, prefix + " | ".join(parts or ["aucune donnée"])
                 + (f" | {len(detections)} détection(s)" if detections else "")
                 + (f" | {len(resultats)} résultat(s) noté(s)" if resultats else "")
                 + (f" | erreurs: {', '.join(errors)}" if errors else ""), now)
        info = {"actif": True, "mode": "observe", "mode_config": mode, "derniere_verif": _iso(now),
                "appels_revx": len(PAIRS), "paires": compact, "detections": [d["id"] for d in detections],
                "anti_spam_ignores": skipped, "resultats_notes": len(resultats), "erreurs": errors}
        try:
            tmp = self.f_etat.with_suffix(".json.tmp")
            tmp.write_text(json.dumps(info, ensure_ascii=False, indent=2) + "\n")
            os.replace(tmp, self.f_etat)
        except OSError:
            pass
        return info

    def _read_etat(self) -> dict:
        try:
            return json.loads(self.f_etat.read_text())
        except Exception:  # noqa: BLE001
            return {}

    # ---- outcomes (+1h / +4h / +24h)
    def record_outcomes(self, now: datetime, candles: dict, iv_ms: int) -> list[dict]:
        dc = self.dc
        dets = read_jsonl(self.f_det)
        if not dets:
            return []
        done = {(r.get("id"), r.get("horizon")) for r in read_jsonl(self.f_res)}
        tol = timedelta(minutes=float(dc["resultat_tolerance_min"]))
        give_up = timedelta(hours=float(dc["resultat_abandon_h"]))
        seuil = float(dc["reussite_min_pct"])
        ticks = TickReader(self.ticks_dir)
        out = []
        for d in dets:
            t0 = _parse_ts(d.get("ts"))
            if t0 is None or not d.get("id"):
                continue
            for h in dc["horizons_h"]:
                hz = f"{int(h)}h" if float(h) == int(h) else f"{h}h"
                if (d["id"], hz) in done:
                    continue
                target = t0 + timedelta(hours=float(h))
                if now < target + timedelta(minutes=1):
                    continue
                price, pts = ticks.price_at(d.get("paire"), target, tol)
                ref = _f(d.get("prix_collecteur")) if price is not None else None
                src = "collecteur"
                if price is None:
                    price, pts = price_from_candles(candles.get(d.get("paire")) or [], target, iv_ms, now)
                    src = "revx bougies"
                if ref is None:
                    ref = _f(d.get("prix"))
                row = {"id": d["id"], "paire": d.get("paire"), "type": d.get("type"),
                       "ts_depart": d.get("ts"), "prix_depart": ref, "horizon": hz,
                       "ts_cible": _iso(target), "note_a": _iso(now)}
                if price is None or not ref:
                    if now - target < give_up:
                        continue  # wait for data
                    row.update(prix=None, variation_pct=None, reussi=None, statut="manquant", source=None)
                else:
                    var = (price / ref - 1.0) * 100.0
                    row.update(prix=price, ts_prix=_iso(pts), variation_pct=round(var, 3),
                               reussi=reussi_for(str(d.get("type")), var, seuil),
                               sens_reel="hausse" if var > 0 else ("baisse" if var < 0 else "plat"),
                               statut="ok", source=src)
                append_jsonl(self.f_res, row)
                done.add((d["id"], hz))
                out.append(row)
        return out


# ----------------------------------------------------------------- summary
def summary(state_dir: Path) -> dict:
    sd = Path(state_dir)
    dets = read_jsonl(sd / "departs.jsonl")
    res = read_jsonl(sd / "departs_resultats.jsonl")
    out: dict = {"total": len(dets), "par_type": {}}
    for t in TYPES:
        n = sum(1 for d in dets if d.get("type") == t)
        hz: dict = {}
        for h in ("1h", "4h", "24h"):
            rows = [r for r in res if r.get("type") == t and r.get("horizon") == h and r.get("statut") == "ok"]
            ok = sum(1 for r in rows if r.get("reussi"))
            hz[h] = {"evalues": len(rows), "reussis": ok,
                     "pct": None if not rows else round(100.0 * ok / len(rows), 1)}
        out["par_type"][t] = {"detections": n, **hz}
    out["derniere"] = dets[-1] if dets else None
    return out


def summary_line(state_dir: Path) -> str:
    s = summary(state_dir)
    parts = []
    for t in TYPES:
        p = s["par_type"][t]
        h4 = p["4h"]
        pct = "—" if h4["pct"] is None else f"{fr_num(h4['pct'], 0)} %"
        parts.append(f"{t} {p['detections']} (à +4h: {h4['reussis']}/{h4['evalues']} = {pct})")
    return "; ".join(parts)


def print_summary(state_dir: Path) -> int:
    s = summary(state_dir)
    print("=== Alertes de départ (observation seulement, aucune sonnerie) ===")
    print(f"Détections au total : {s['total']}")
    for t in TYPES:
        p = s["par_type"][t]
        cells = []
        for h in ("1h", "4h", "24h"):
            x = p[h]
            pct = "—" if x["pct"] is None else f"{fr_num(x['pct'], 0)} %"
            cells.append(f"+{h}: {x['reussis']}/{x['evalues']} ({pct})")
        print(f"  {t:<13}: {p['detections']:>3} détection(s) — ça a marché " + ", ".join(cells))
    d = s.get("derniere")
    if d:
        print(f"Dernière : {d.get('ts')} {d.get('paire')} {d.get('type')} prix {d.get('prix')} "
              f"volume x{d.get('ratio_volume')} (haut 24h -{d.get('distance_haut_24h_pct')} %, "
              f"bas 24h +{d.get('distance_bas_24h_pct')} %)")
    print("« Ça a marché » = le prix a bougé d'au moins 1 % dans le sens prévu "
          "(accumulation : 1 % dans un sens ou l'autre).")
    return 0


if __name__ == "__main__":
    import sys
    raise SystemExit(print_summary(Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parent / "state"))
