#!/usr/bin/env python3
"""Verdict « test du passé » de l'équipe (PM-Compound), écrit DANS le fichier du test. Aucun ordre, aucune IA.

Règle de l'équipe (toutes doivent être vraies pour « oui ») :
  1. gain après frais > 0 (pour sell_rebuy : pièces gagnées vs garder, frais compris) ;
  2. au moins 20 trades (ventes pour sell_rebuy) ;
  3. gain positif sur LES DEUX moitiés de la période (coupure au milieu exact de la période ;
     trades classés par heure d'entrée, gains composés) ;
  4. pire baisse sur NOTRE capital < 8 % : pire baisse de l'outil × 5 % (l'outil met 100 % du capital
     dans chaque trade, nous ~5 %) ;
  5. encore positif en achat immédiat + frais (Revolut X 0,09 % + 0,05 % d'écart) quand ce test existe
     (même réglage, coûts `revolutx`, tout rempli). Pour sell_rebuy : profil `revolutx` (frais réels Revolut X).

Écrit : engine → run_card.json ; sell_rebuy → summary.json ; robust (checks/*.json) → le fichier lui-même.
Clés : verdict_equipe{test_du_passe_reussi "oui"|"non", raisons[], date_verdict, par, criteres{}, moitie_1_pct,
moitie_2_pct, pire_baisse_outil_pct, pire_baisse_capital_pct, achat_immediat, resultat_juge, …} + au premier
niveau moitie_1_pct, moitie_2_pct, pire_baisse_outil_pct, pire_baisse_capital_pct.
date_verdict ne change que si le verdict ou ses chiffres changent (idempotent).

Usage : .venv/bin/python vt_verdict.py --all            (tous les dossiers home/runs + checks/*.json)
        .venv/bin/python vt_verdict.py <dossier|fichier.json> [...]   [--dry-run] [--quiet]
"""
from __future__ import annotations

import csv
import glob
import hashlib
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent
RUNS = ROOT / "home" / "runs"
CHECKS = ROOT / "checks"
TZ = ZoneInfo("Europe/Brussels")
STAKE = 0.05          # mise réelle ≈ 5 % du capital
MAX_DD_CAPITAL = 8.0  # %
MIN_TRADES = 20
MIN_DAYS = 360        # « les deux moitiés de l'année » : il faut au moins ~1 an de prix
TAKER_FEE, TAKER_SLIP = 0.0009, 0.0005
VERSION = "regle-equipe-2026-10-09"


def _now():
    return datetime.now(TZ).isoformat(timespec="seconds")


def _read(p, default=None):
    try:
        return json.loads(Path(p).read_text(encoding="utf-8"))
    except Exception:
        return default


def _ts(x):
    """'2025-10-07 00:00:00' / '2025-10-07T00:00:00' / '2025-10-12 21:00' → datetime naïf (UTC)."""
    s = str(x).replace("T", " ").replace("Z", "").split("+")[0].strip()
    for f in ("%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d"):
        try:
            return datetime.strptime(s, f)
        except ValueError:
            pass
    raise ValueError(f"date illisible: {x}")


def _comp(pcts):
    f = 1.0
    for p in pcts:
        f *= 1 + p / 100.0
    return round((f - 1) * 100, 3)


def _halves(trades, start, end):
    """trades = [(heure_entree, gain_pct_net)] → (moitie_1_pct, moitie_2_pct, n1, n2, milieu)."""
    mid = start + (end - start) / 2
    h1 = [p for t, p in trades if t < mid]
    h2 = [p for t, p in trades if t >= mid]
    return _comp(h1), _comp(h2), len(h1), len(h2), mid


# ───────────────────────── engine runs (team_rebound, team_breakout, sma_cross…) ─────────────────────────
def _engine_trades_from_fills(rd: Path):
    rows, op = [], None
    p = rd / "artifacts" / "fills.jsonl"
    if not p.exists():
        return []
    for line in p.read_text().splitlines():
        if not line.strip():
            continue
        f = json.loads(line)
        if f["action"] == "open":
            op = f
        elif f["action"] == "close" and op is not None:
            gross = float(f["notional"]) - float(op["notional"])
            fees = float(op.get("fee") or 0) + float(f.get("fee") or 0)
            rows.append((_ts(op["timestamp"]), (gross - fees) / float(op["notional"]) * 100))
            op = None
    return rows


def _fill_summary(rd: Path):
    for name in ("fill_touch_summary.json", "fill_rate_summary.json"):
        if (rd / name).exists():
            return name, _read(rd / name, {})
    return None, None


def _engine_key(rd: Path, cfg: dict):
    try:
        code = hashlib.sha1((rd / "code" / "signal_engine.py").read_bytes()).hexdigest()
    except OSError:
        return None
    return json.dumps([cfg.get("codes"), cfg.get("interval"), cfg.get("source"), code, cfg.get("spot_stop_loss"),
                       cfg.get("spot_take_profit"), cfg.get("spot_trailing_stop"), cfg.get("evaluation_start_date"),
                       cfg.get("end_date"), cfg.get("initial_cash")]
                      + ([cfg.get("spot_trail_start"), cfg.get("spot_hold_until_exit")]
                         if cfg.get("spot_trail_start") or cfg.get("spot_hold_until_exit") else []))


def _is_taker(cfg):
    return abs(float(cfg.get("maker_rate") or 0) - TAKER_FEE) < 1e-12 and abs(float(cfg.get("slippage") or 0) - TAKER_SLIP) < 1e-12


_ENGINE_INDEX = None


def _engine_index():
    """clé de réglage → résultats en achat immédiat (coûts revolutx, moteur = tout rempli)."""
    global _ENGINE_INDEX
    if _ENGINE_INDEX is None:
        _ENGINE_INDEX = {}
        for d in sorted(glob.glob(str(RUNS / "*"))):
            rd = Path(d)
            cfg = _read(rd / "config.json", {})
            if not isinstance(cfg, dict) or "codes" not in cfg or not (rd / "artifacts" / "metrics.csv").exists():
                continue
            if not _is_taker(cfg):
                continue
            k = _engine_key(rd, cfg)
            if k:
                _ENGINE_INDEX.setdefault(k, []).append(rd)
    return _ENGINE_INDEX


def _metrics(rd: Path):
    with open(rd / "artifacts" / "metrics.csv", encoding="utf-8") as f:
        return next(csv.DictReader(f))


def engine_verdict(rd: Path, twin: bool = True):
    rd = Path(rd)
    cfg = _read(rd / "config.json", {})
    m = _metrics(rd)
    eq_first = eq_last = None
    with open(rd / "artifacts" / "equity.csv", encoding="utf-8") as f:
        rdr = csv.reader(f)
        next(rdr)
        for row in rdr:
            if eq_first is None:
                eq_first = row[0]
            eq_last = row[0]
    start, end = _ts(eq_first), _ts(eq_last)
    fname, fb = _fill_summary(rd)
    if fb and fb.get("result"):
        mode = fb.get("mode")
        tr_csv = rd / "artifacts" / f"fill_{mode}_trades.csv"
        trades = []
        if tr_csv.exists():
            with open(tr_csv, encoding="utf-8") as f:
                trades = [(_ts(x["entry"]), float(x["net_pct"])) for x in csv.DictReader(f)]
        res = fb["result"]
        total, n, dd = float(res["total_return_pct"]), int(res["trades"]), float(res["max_drawdown_pct"])
        juge = ("modèle d'ordres « touch » (ordres à prix fixé remplis seulement si le prix passe au-delà)" if mode == "touch"
                else f"modèle d'ordres remplis au hasard {fb.get('fill_rate_pct')} % (tirage {fb.get('seed')})")
        extra = {"fichier_resultat": fname}
        if fb.get("seed_spread"):
            sp = fb["seed_spread"]
            extra["tirages"] = {"n": sp.get("n"), "milieu_pct": sp.get("return_pct_median"), "pire_pct": sp.get("return_pct_min")}
    else:
        trades = _engine_trades_from_fills(rd)
        total, n, dd = float(m["total_return"]) * 100, int(float(m["trade_count"] or 0)), float(m["max_drawdown"]) * 100
        juge = "moteur, tous les ordres remplis (artifacts/metrics.csv)"
        extra = {"fichier_resultat": "artifacts/metrics.csv"}
    taker_self = _is_taker(cfg)
    if taker_self:
        imm = {"dossier": rd.name, "total_pct": round(float(m["total_return"]) * 100, 2), "trades": int(float(m["trade_count"] or 0)),
               "note": "ce test est lui-même en achat immédiat + frais (moteur, tout rempli)"}
    else:
        cands = [c for c in _engine_index().get(_engine_key(rd, cfg) or "", []) if c != rd]
        imm = None
        if cands:
            c = cands[-1]
            mc = _metrics(c)
            imm = {"dossier": c.name, "total_pct": round(float(mc["total_return"]) * 100, 2), "trades": int(float(mc["trade_count"] or 0)),
                   "note": "même réglage, coûts revolutx (0,09 % + 0,05 %), tout rempli"}
            if twin:
                tv = engine_verdict(c, twin=False)
                imm.update({"moitie_1_pct": tv["moitie_1_pct"], "moitie_2_pct": tv["moitie_2_pct"], "son_verdict": tv["test_du_passe_reussi"]})
    prud = []
    if not fb and not taker_self and float(cfg.get("maker_rate") or 0) == 0 and float(cfg.get("slippage") or 0) == 0:
        prud.append("frais 0 % partout, sorties au stop" + ("" if cfg.get("spot_hold_until_exit") else " et à 22h") + " comprises : cas le plus favorable")
    return _judge(total, n, dd, trades, start, end, imm, juge, extra, unit="%", prudence=prud)


# ───────────────────────── sell_rebuy (idée à la baisse) ─────────────────────────
def _sr_core(s):
    b = s.get("base_full") if isinstance(s.get("base_full"), dict) else {}
    return {**s, **{k: v for k, v in b.items() if v is not None}} if b else s


def _sr_key(s):
    prm = {k: v for k, v in (s.get("params") or {}).items() if k not in ("fill", "fill_ticks")}
    return json.dumps([s.get("pair"), s.get("timeframe"), s.get("source"), prm, s.get("entries"), s.get("period"),
                       round(float(s.get("coins_start") or 0), 12)], sort_keys=True, default=str)


_SR_INDEX = None


def _sr_index():
    global _SR_INDEX
    if _SR_INDEX is None:
        _SR_INDEX = {}
        for d in sorted(glob.glob(str(RUNS / "*_sell_rebuy*"))):
            s = _read(Path(d) / "summary.json")
            if not isinstance(s, dict) or s.get("strategy") != "sell_rebuy":
                continue
            s = _sr_core(s)
            if (s.get("costs") or {}).get("profile") == "revolutx" and s.get("coin_gain_vs_hold_pct") is not None:
                _SR_INDEX.setdefault(_sr_key(s), []).append((Path(d), s))
    return _SR_INDEX


def sellrebuy_verdict(rd: Path, twin: bool = True):
    rd = Path(rd)
    s = _sr_core(_read(rd / "summary.json", {}))
    per = s.get("period") or []
    start, end = _ts(per[0]), _ts(per[1])
    trades = []
    cyc = rd / "artifacts" / "cycles.csv"
    chunk = float((s.get("params") or {}).get("chunk") or 100.0) / 100.0
    if cyc.exists():
        with open(cyc, encoding="utf-8") as f:
            for x in csv.DictReader(f):
                sold = float(x["coins_sold"])
                before = sold / chunk if chunk > 0 else sold
                trades.append((_ts(x["sell_time_utc"]), float(x["coin_gain"]) / before * 100 if before else 0.0))
    total = float(s.get("coin_gain_vs_hold_pct") or 0)
    n = int(s.get("cycles") or 0)
    dd = float(s.get("max_drawdown_coins_pct") or 0)
    prof = (s.get("costs") or {}).get("profile")
    if prof != "revolutx-maker":
        imm = {"dossier": rd.name, "total_pct": round(total, 3), "trades": n,
               "note": f"ce test compte déjà les frais réels (profil {prof})"}
    else:
        c = [x for x in _sr_index().get(_sr_key(s), []) if x[0] != rd]
        imm = None
        if c:
            d2, s2 = c[-1]
            imm = {"dossier": d2.name, "total_pct": round(float(s2["coin_gain_vs_hold_pct"]), 3), "trades": int(s2.get("cycles") or 0),
                   "note": "même réglage, frais Revolut X (rachat de sécurité au marché 0,09 % + 0,05 %)"}
            if twin:
                tv = sellrebuy_verdict(d2, twin=False)
                imm.update({"moitie_1_pct": tv["moitie_1_pct"], "moitie_2_pct": tv["moitie_2_pct"], "son_verdict": tv["test_du_passe_reussi"]})
    prud = ["rachats de sécurité (ordres au marché) comptés à 0 % : cas le plus favorable ; le cas réaliste est le profil revolutx"] if prof == "revolutx-maker" else []
    juge = f"pièces gagnées vs garder, frais compris (profil {prof})"
    return _judge(total, n, dd, trades, start, end, imm, juge, {"fichier_resultat": "summary.json", "unite": "% de pièces"}, unit="% pièces", prudence=prud)


# ───────────────────────── jugement commun ─────────────────────────
def _fr(x, nd=2):
    return f"{x:+.{nd}f}".replace(".", ",")


def _judge(total, n, dd_tool, trades, start, end, imm, juge, extra, unit="%", prudence=None):
    h1, h2, n1, n2, mid = _halves(trades, start, end)
    days = round((end - start).total_seconds() / 86400, 1)
    dd_tool = -abs(dd_tool)
    dd_cap = round(dd_tool * STAKE, 3)
    crit = {
        "gain_apres_frais": {"ok": total > 0, "valeur_pct": round(total, 3), "seuil": "> 0"},
        "assez_de_trades": {"ok": n >= MIN_TRADES, "valeur": n, "seuil": f">= {MIN_TRADES}"},
        "deux_moities_positives": {"ok": h1 > 0 and h2 > 0 and days >= MIN_DAYS, "moitie_1_pct": h1, "moitie_2_pct": h2,
                                   "jours_testes": days, "jours_min": MIN_DAYS},
        "pire_baisse_capital_sous_8": {"ok": abs(dd_cap) < MAX_DD_CAPITAL, "pire_baisse_outil_pct": round(dd_tool, 3),
                                       "pire_baisse_capital_pct": dd_cap, "seuil": f"< {MAX_DD_CAPITAL:g} % (outil × {STAKE:g})"},
        "achat_immediat_positif": {"ok": None if imm is None else imm["total_pct"] > 0,
                                   "valeur_pct": None if imm is None else imm["total_pct"],
                                   "note": "pas de test en achat immédiat pour ce réglage : critère non compté" if imm is None else imm["note"]},
    }
    raisons = []
    if not crit["gain_apres_frais"]["ok"]:
        raisons.append(f"perte après frais ({_fr(total)} {unit})")
    if not crit["assez_de_trades"]["ok"]:
        raisons.append(f"trop peu de trades ({n} < {MIN_TRADES})")
    if days < MIN_DAYS:
        raisons.append(f"période trop courte ({days:g} jours < 1 an) : les deux moitiés de l'année ne sont pas testées")
    if h1 <= 0:
        raisons.append(f"1re moitié pas gagnante ({_fr(h1)} {unit})")
    if h2 <= 0:
        raisons.append(f"2e moitié pas gagnante ({_fr(h2)} {unit})")
    if not crit["pire_baisse_capital_sous_8"]["ok"]:
        raisons.append(f"pire baisse sur notre capital trop forte ({_fr(dd_cap)} %)")
    if crit["achat_immediat_positif"]["ok"] is False:
        raisons.append(f"perte en achat immédiat + frais ({_fr(imm['total_pct'])} {unit})")
    ok = not raisons
    prudence = list(prudence or [])
    if imm and imm.get("son_verdict") == "non" and (imm.get("moitie_1_pct", 1) <= 0 or imm.get("moitie_2_pct", 1) <= 0):
        prudence.append(f"le même réglage en achat immédiat / frais réels a une moitié perdante "
                        f"({_fr(imm['moitie_1_pct'])} / {_fr(imm['moitie_2_pct'])} {unit})")
    return {
        "test_du_passe_reussi": "oui" if ok else "non",
        "raisons": raisons,
        "par": "PM-Compound",
        "regle": "gain après frais > 0 ; >= 20 trades ; 2 moitiés gagnantes ; pire baisse outil × 5 % < 8 % ; achat immédiat + frais > 0 (si testé)",
        "resultat_juge": juge,
        "gain_pct": round(total, 3), "trades": n,
        "moitie_1_pct": h1, "moitie_2_pct": h2, "moitie_1_trades": n1, "moitie_2_trades": n2,
        "coupure_moities": str(mid)[:16] + " UTC", "periode": [str(start)[:16], str(end)[:16]], "jours_testes": days,
        "methode_moities": "trades classés par heure d'entrée (vente pour sell_rebuy), gains nets composés",
        "pire_baisse_outil_pct": round(dd_tool, 3), "pire_baisse_capital_pct": dd_cap,
        "achat_immediat": imm,
        "prudence": prudence,
        "criteres": crit,
        **extra,
        "version_regle": VERSION,
    }


# ───────────────────────── écriture ─────────────────────────
TOP = ("moitie_1_pct", "moitie_2_pct", "pire_baisse_outil_pct", "pire_baisse_capital_pct")


def _merge(doc: dict, v: dict):
    old = doc.get("verdict_equipe") if isinstance(doc.get("verdict_equipe"), dict) else {}
    same = {k: x for k, x in old.items() if k != "date_verdict"} == v
    v = dict(v, date_verdict=old.get("date_verdict") if same and old.get("date_verdict") else _now())
    # garde un éventuel avis PM-Risk déjà écrit dans le même objet
    if "autorise_en_reel" in old:
        v["autorise_en_reel"] = old["autorise_en_reel"]
    doc["verdict_equipe"] = v
    for k in TOP:
        doc[k] = v[k]
    return doc, not same


def _write(path: Path, doc: dict, dry):
    if dry:
        return
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(doc, indent=1, default=str, ensure_ascii=False), encoding="utf-8")
    json.loads(tmp.read_text(encoding="utf-8"))
    tmp.replace(path)


def _strip(path: Path, dry):
    """Retire un verdict écrit par erreur (variantes de grille)."""
    doc = _read(path, None)
    if isinstance(doc, dict) and "verdict_equipe" in doc and (doc["verdict_equipe"] or {}).get("par") == "PM-Compound":
        for k in ("verdict_equipe",) + TOP:
            doc.pop(k, None)
        _write(path, doc, dry)


def annotate(target, dry=False):
    """Calcule et écrit le verdict pour un dossier de test ou un fichier robust (checks/*.json). Renvoie (fichier, verdict) ou None.
    Les variantes de grille de `robust` (dossiers *_grid) ne reçoivent pas de verdict : ce ne sont pas des tests à elles seules
    (réglages balayés pour mesurer la chance) ; un « oui » y serait trompeur."""
    p = Path(target)
    if p.is_dir() and p.name.endswith("_grid"):
        _strip(p / "run_card.json", dry)
        return None
    if p.is_file() and p.suffix == ".json":
        doc = _read(p, None)
        if not isinstance(doc, dict) or "base_result" not in doc:
            return None
        base = doc.get("base_run_dir") or doc.get("run_dir")
        if not base or not Path(base).exists():
            return None
        v = engine_verdict(Path(base)) if (Path(base) / "artifacts" / "metrics.csv").exists() else sellrebuy_verdict(Path(base))
        v["dossier_base"] = Path(base).name
        doc, _ = _merge(doc, v)
        _write(p, doc, dry)
        return p, doc["verdict_equipe"]
    if (p / "summary.json").exists():
        s = _read(p / "summary.json", {})
        if isinstance(s, dict) and s.get("strategy") == "sell_rebuy" and s.get("status", "ok") == "ok":
            v = sellrebuy_verdict(p)
            s, _ = _merge(s, v)
            _write(p / "summary.json", s, dry)
            return p / "summary.json", s["verdict_equipe"]
        return None
    if (p / "artifacts" / "metrics.csv").exists() and (p / "artifacts" / "equity.csv").exists():
        v = engine_verdict(p)
        rc = _read(p / "run_card.json", {}) or {}
        rc, _ = _merge(rc, v)
        _write(p / "run_card.json", rc, dry)
        return p / "run_card.json", rc["verdict_equipe"]
    return None


def annotate_safe(target):
    """Pour l'outil : ne fait jamais échouer un test si le verdict ne peut pas être calculé."""
    try:
        r = annotate(target)
        return r[1] if r else None
    except Exception as exc:  # noqa: BLE001
        return {"erreur": f"verdict non calculé : {exc}"}


def main(argv):
    dry, quiet = "--dry-run" in argv, "--quiet" in argv
    targets = [a for a in argv if not a.startswith("--")]
    if "--all" in argv:
        targets = sorted(glob.glob(str(RUNS / "*"))) + sorted(glob.glob(str(CHECKS / "*.json")))
    n = 0
    for t in targets:
        try:
            r = annotate(t, dry)
        except Exception as exc:  # noqa: BLE001
            print(f"ERREUR {t}: {exc}", file=sys.stderr)
            continue
        if not r:
            continue
        n += 1
        if not quiet:
            v = r[1]
            print(f"{v['test_du_passe_reussi']:3} {Path(t).name:60} gain {v['gain_pct']:+8.2f} n {v['trades']:4} "
                  f"H1 {v['moitie_1_pct']:+7.2f} H2 {v['moitie_2_pct']:+7.2f} dd {v['pire_baisse_outil_pct']:+7.2f}/{v['pire_baisse_capital_pct']:+.2f} "
                  f"imm {None if not v['achat_immediat'] else v['achat_immediat']['total_pct']} | {'; '.join(v['raisons'])}")
    print(f"{n} fichier(s) {'vérifiés (dry-run)' if dry else 'écrits'}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
