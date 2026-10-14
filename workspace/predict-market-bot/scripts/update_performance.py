#!/usr/bin/env python3
"""PM-Compound — reconstruit state/performance.json depuis les vraies sources (idempotent, aucun ordre, aucune IA).

Sources (lecture seule, sauf la sortie) :
  guardian/state.json        positions simulées (PM-Risk) : fermées (realized_pnl_eur) + ouvertes, capital
  guardian/config.json       plafonds (bankroll, max_exposure_pct)
  state/trades_log.jsonl     lignes d'ouverture / fermeture (heures, prix, frais, raison)
  state/retro_sims.jsonl     étiquette « rétro »
  state/live_orders.jsonl    ordres réels du pipeline (si présent)
  state/predictions_log.jsonl  nombre de prévisions / score de Brier
  knowledge/trading_journal.md  entrées « ### AAAA-MM-JJ | PAIRE | essai|live | D-xxx »
  knowledge/decision_log.md     sorte de trade (rebond, cassure, D-018, baisse sur prévision…)

Usage : python3 scripts/update_performance.py [--dry-run] [--quiet]
Les clés historiques lues par le site (win_rate, profit_factor, max_drawdown_pct, n_trades, n_closed,
total_realized_pnl_eur, updated_at, …) sont gardées (= simulation) ; tout le reste est ajouté.
"""
from __future__ import annotations

import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent.parent
TZ = ZoneInfo("Europe/Brussels")
F = {
    "guardian_state": ROOT / "guardian" / "state.json",
    "guardian_config": ROOT / "guardian" / "config.json",
    "trades_log": ROOT / "state" / "trades_log.jsonl",
    "retro_sims": ROOT / "state" / "retro_sims.jsonl",
    "live_orders": ROOT / "state" / "live_orders.jsonl",
    "predictions_log": ROOT / "state" / "predictions_log.jsonl",
    "trading_journal": ROOT / "knowledge" / "trading_journal.md",
    "decision_log": ROOT / "knowledge" / "decision_log.md",
}
OUT = ROOT / "state" / "performance.json"
TARGET_TRIALS = 20

# Historique du plafond simulation (total ouvert). 25 € = 5 % de 500 € (guardian/config.json max_exposure_pct).
# 9 oct 14h03 : consigne équipe → 50 € au total ouvert. À ajouter ici à chaque changement.
CAP_HISTORY = [
    {"depuis": "2026-10-08T00:00:00+02:00", "plafond_eur": 25.0, "source": "guardian/config.json max_exposure_pct 0.05 × bankroll 500 €"},
    {"depuis": "2026-10-09T14:03:00+02:00", "plafond_eur": 50.0, "source": "consigne équipe 9 oct 14h03 (simulation : 50 € au total ouvert, avant 25 €)"},
]

# Sorte de trade (pour compter les essais vers ~20). Clé = D-xxx. Repli : lecture du decision_log.
KINDS = {
    "rebond": "Rebond (D-013)",
    "cassure": "Cassure (D-014)",
    "vendre_haut_racheter_bas": "Vendre haut / racheter plus bas (D-018)",
    "baisse_sur_prevision": "Idée à la baisse sur prévision du jour (D-019, D-020, D-021…)",
    "hausse_sur_prevision": "Idée à la hausse sur prévision du jour",
    "essai_stop": "Essai technique du stop (sans décision écrite)",
    "autre": "Autre / non classé",
}
KIND_BY_DECISION = {"D-013": "rebond", "D-014": "cassure", "D-018": "vendre_haut_racheter_bas"}


def read_json(p, default=None):
    try:
        return json.loads(Path(p).read_text(encoding="utf-8"))
    except Exception:
        return default


def read_jsonl(p):
    out = []
    p = Path(p)
    if not p.exists():
        return out
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                pass
    return out


def ts(v):
    if not v:
        return None
    try:
        d = datetime.fromisoformat(str(v).replace("Z", "+00:00"))
    except ValueError:
        return None
    return d if d.tzinfo else d.replace(tzinfo=timezone.utc)


def loc(v):
    d = ts(v)
    return d.astimezone(TZ).isoformat(timespec="seconds") if d else None


def r(x, n=6):
    return None if x is None else round(float(x), n)


# ---------------------------------------------------------------- decision_log → sorte
def decision_kinds():
    txt = Path(F["decision_log"]).read_text(encoding="utf-8") if Path(F["decision_log"]).exists() else ""
    blocks = re.split(r"\n(?=### )", txt)
    out = {}
    for b in blocks:
        m = re.match(r"### [^\n]*?\|\s*(D-\d+)", b)
        if not m:
            continue
        did, head = m.group(1), b.split("\n", 1)[0].lower()
        body = b.lower()
        if did in KIND_BY_DECISION:
            k = KIND_BY_DECISION[did]
        elif "rebond" in head or "team_rebound" in body[:400]:
            k = "rebond"
        elif "cassure" in head:
            k = "cassure"
        elif re.search(r"\bd-018\b", head) or "vendre haut" in head:
            k = "vendre_haut_racheter_bas"
        elif "à la baisse" in body or "a la baisse" in body:
            k = "baisse_sur_prevision"
        elif "à la hausse" in body:
            k = "hausse_sur_prevision"
        else:
            k = "autre"
        out.setdefault(did, k)
    return out


# ---------------------------------------------------------------- journal
def journal_entries():
    p = Path(F["trading_journal"])
    if not p.exists():
        return []
    txt = p.read_text(encoding="utf-8")
    txt = txt.split("## Entrées", 1)[1] if "## Entrées" in txt else txt
    out = []
    for b in re.split(r"\n(?=### )", txt):
        m = re.match(r"### (\d{4}-\d{2}-\d{2}) \| ([A-Z]+-[A-Z]+) \| (essai|live)[^|]*\| ([^\n]*)", b.strip())
        if not m:
            continue
        link = m.group(4).strip()
        d = re.search(r"D-\d+[a-z]?", link)
        fields = {}
        for line in b.splitlines():
            mm = re.match(r"- ([^:]+?) ?: (.*)", line.strip())
            if mm:
                fields[mm.group(1).strip()] = mm.group(2).strip()
        out.append({"date": m.group(1), "pair": m.group(2), "mode": "simulation" if m.group(3) == "essai" else "live",
                    "decision_id": d.group(0) if d else None, "link": link, "fields": fields})
    return out


# ---------------------------------------------------------------- trades
def sim_trades(problems):
    st = read_json(F["guardian_state"], {}) or {}
    log = read_jsonl(F["trades_log"])
    retro_ids = {x.get("decision_id") for x in read_jsonl(F["retro_sims"])}
    by_id = {t.get("id"): t for t in log if t.get("id")}
    closes = {t.get("linked_position_id"): t for t in log if t.get("linked_position_id") and t.get("realized_pnl_eur") is not None}
    kinds = decision_kinds()
    closed, open_ = [], []
    seen = set()
    for p in st.get("positions", []):
        pid = p.get("id")
        seen.add(pid)
        op = by_id.get(pid, {})
        cl = closes.get(pid, {})
        idea = p.get("idea_type") or p.get("kind") or op.get("idea_type") or ("baisse" if p.get("side") == "short" else "hausse")
        did = p.get("decision_id") or op.get("decision_id")
        size = p.get("amount_eur") or op.get("amount_eur") or (p.get("cost_eur") if p.get("status") == "open" else None)
        if size is None and p.get("avg_price") and (p.get("orig_qty") or op.get("qty")):
            size = float(p["avg_price"]) * float(p.get("orig_qty") or op.get("qty"))
        kind = kinds.get(did) if did else ("essai_stop" if p.get("stop_pct") is not None and not did else "autre")
        row = {
            "id": pid, "pair": p.get("pair"), "mode": "simulation", "decision_id": did,
            "sens": idea, "sens_fr": "idée à la baisse (vente puis rachat)" if idea == "baisse" else "idée à la hausse (achat puis vente)",
            "sorte": kind or "autre", "retro": bool(p.get("label") == "retro" or did in retro_ids),
            "ouvert_le": loc(p.get("opened_at") or op.get("ts")), "taille_eur": r(size, 4),
            "prix_entree": p.get("avg_price") or op.get("price"),
        }
        if p.get("status") == "closed":
            pnl = p.get("realized_pnl_eur")
            if cl and cl.get("realized_pnl_eur") is not None and pnl is not None and abs(float(cl["realized_pnl_eur"]) - float(pnl)) > 1e-6:
                problems.append(f"{pid} : gain gardien {pnl} ≠ trades_log {cl['realized_pnl_eur']}")
            fees = sum(float(x.get("fee_eur") or 0) for x in (op, cl))
            row.update({
                "ferme_le": loc(p.get("closed_at") or cl.get("ts")), "prix_sortie": p.get("close_price_eur") or cl.get("price"),
                "gain_eur": r(pnl, 6), "gain_pct": r(p.get("realized_pnl_pct"), 4),
                "frais_eur": r(fees, 6) if (op.get("fee_eur") is not None or cl.get("fee_eur") is not None) else None,
                "frais_note": None if (op.get("fee_eur") is not None or cl.get("fee_eur") is not None) else "frais non isolés (inclus dans le gain simulé)",
                "raison_sortie": p.get("close_reason") or cl.get("close_reason"),
                "rachat": p.get("rebuy_reason") or cl.get("rebuy_reason"),
                "gagnant": (pnl or 0) > 0,
            })
            closed.append(row)
        elif p.get("status") == "open":
            row.update({"prix_arret": p.get("stop_price") or p.get("stop_price_eur"), "prix_vise": p.get("target_price"),
                        "heure_limite": p.get("deadline"), "frais_ouverture_eur": p.get("fee_eur"),
                        "latent_eur": p.get("unrealized_pnl_eur"), "latent_pct": p.get("unrealized_pnl_pct"),
                        "dernier_prix": p.get("last_mid_eur"), "prix_lu_le": p.get("mark_ts")})
            open_.append(row)
    # fermetures présentes dans trades_log mais plus dans guardian/state.json
    for pid, cl in closes.items():
        if pid in seen:
            continue
        op = by_id.get(pid, {})
        problems.append(f"{pid} : fermé dans trades_log mais absent de guardian/state.json (repris depuis trades_log)")
        did = cl.get("decision_id") or op.get("decision_id")
        idea = cl.get("idea_type") or op.get("idea_type") or ("baisse" if op.get("side") == "sell" else "hausse")
        closed.append({"id": pid, "pair": cl.get("pair"), "mode": "simulation", "decision_id": did, "sens": idea,
                       "sens_fr": "idée à la baisse (vente puis rachat)" if idea == "baisse" else "idée à la hausse (achat puis vente)",
                       "sorte": kinds.get(did, "autre") if did else "autre", "retro": cl.get("label") == "retro",
                       "ouvert_le": loc(op.get("ts")), "taille_eur": r(op.get("amount_eur"), 4), "prix_entree": op.get("price"),
                       "ferme_le": loc(cl.get("ts")), "prix_sortie": cl.get("price"), "gain_eur": r(cl.get("realized_pnl_eur")),
                       "gain_pct": r(cl.get("realized_pnl_pct"), 4), "frais_eur": r(float(op.get("fee_eur") or 0) + float(cl.get("fee_eur") or 0)),
                       "raison_sortie": cl.get("close_reason"), "rachat": cl.get("rebuy_reason"),
                       "gagnant": float(cl["realized_pnl_eur"]) > 0})
    closed.sort(key=lambda x: x["ferme_le"] or "")
    return closed, open_, st


def live_trades():
    """Trades réels FERMÉS du pipeline : lignes de state/live_orders.jsonl avec realized_pnl_eur (aucune pour l'instant)."""
    rows = [x for x in read_jsonl(F["live_orders"]) if not x.get("dry_run")]
    closed = []
    for x in rows:
        o = x.get("order") or {}
        pnl = x.get("realized_pnl_eur", o.get("realized_pnl_eur"))
        if pnl is None:
            continue
        did = o.get("decision_id") or x.get("decision_id")
        idea = o.get("idea_type") or ("baisse" if o.get("kind") == "baisse" else "hausse")
        closed.append({"id": x.get("id") or o.get("client_order_id"), "pair": o.get("pair"), "mode": "live", "decision_id": did,
                       "sens": idea, "sorte": decision_kinds().get(did, "autre"), "retro": False, "ferme_le": loc(x.get("at")),
                       "taille_eur": r(o.get("amount_eur"), 4), "gain_eur": r(pnl), "raison_sortie": x.get("kind") or o.get("reason"),
                       "gagnant": float(pnl) > 0})
    return closed, len(rows)


# ---------------------------------------------------------------- stats
def stats(rows):
    g = [float(x["gain_eur"]) for x in rows if x.get("gain_eur") is not None]
    w = [x for x in g if x > 0]
    l = [x for x in g if x <= 0]
    pf = (sum(w) / abs(sum(l))) if l and sum(l) != 0 else None
    return {"trades": len(rows), "gagnants": len(w), "perdants": len(l), "net_eur": r(sum(g), 6),
            "taux_reussite": r(len(w) / len(g), 4) if g else None, "rapport_gains_pertes": r(pf, 4),
            "gain_moyen_eur": r(sum(g) / len(g), 6) if g else None,
            "taille_totale_eur": r(sum(float(x.get("taille_eur") or 0) for x in rows), 4)}


def by_side(rows):
    return {s: stats([x for x in rows if x["sens"] == s]) for s in ("hausse", "baisse")}


def brier(preds):
    sc = []
    for p in preds:
        if p.get("outcome") is None or p.get("p_model") is None:
            continue
        y = 1.0 if p["outcome"] in (1, True, "yes", "YES", "win") else 0.0
        sc.append((float(p["p_model"]) - y) ** 2)
    return r(sum(sc) / len(sc), 6) if sc else None


def build():
    problems = []
    closed, open_, st = sim_trades(problems)
    live_closed, n_live_orders = live_trades()
    cfg = read_json(F["guardian_config"], {}) or {}
    start = float(st.get("bankroll_eur") or 500.0)

    # capital simulé après chaque trade fermé : départ gardien + gains réalisés écrits par le gardien
    cap, peak, mdd, series = start, start, 0.0, [{"date": None, "evenement": "départ (guardian/state.json bankroll_eur)", "capital_eur": start}]
    for x in closed:
        cap += float(x["gain_eur"] or 0)
        peak = max(peak, cap)
        mdd = max(mdd, (peak - cap) / peak if peak else 0)
        series.append({"date": x["ferme_le"], "evenement": f"fermeture {x['decision_id'] or x['id']} {x['pair']}", "trade_id": x["id"],
                       "gain_eur": x["gain_eur"], "capital_eur": round(cap, 6)})
    # contrôle : départ + gains fermés + latent des ouvertes (frais compris ; à défaut − frais d'ouverture) = equity_eur du gardien
    open_adj = sum(float(x["latent_eur"]) if x.get("latent_eur") is not None else -float(x.get("frais_ouverture_eur") or 0) for x in open_)
    eq = st.get("equity_eur")
    if eq is not None and abs((cap + open_adj) - float(eq)) > 0.01:
        problems.append(f"capital recalculé {cap + open_adj:.4f} € (départ + gains fermés + latent ouvert) ≠ gardien equity_eur {eq}")

    s_all = stats(closed)
    s_live = stats(live_closed)
    sim_nr = [x for x in closed if not x["retro"]]

    # sortes de trade → essais vers ~20
    kinds = {}
    for k, label in KINDS.items():
        rows = [x for x in closed if x["sorte"] == k]
        lrows = [x for x in live_closed if x["sorte"] == k]
        kinds[k] = {"nom": label, "essais_simulation": len(rows), "essais_live": len(lrows), "objectif_essais": TARGET_TRIALS,
                    "reste": max(0, TARGET_TRIALS - len(rows) - len(lrows)), "ouverts": sum(1 for x in open_ if x["sorte"] == k),
                    "decisions": sorted({x["decision_id"] for x in rows + lrows if x["decision_id"]}),
                    "simulation": stats(rows), "live": stats(lrows)}

    # journal ↔ gardien
    jr = journal_entries()
    missing, matched = [], set()
    for x in closed + live_closed:
        day = (x["ferme_le"] or "")[:10]
        mode = x["mode"]
        cand = [i for i, e in enumerate(jr) if e["pair"] == x["pair"] and e["mode"] == mode and
                ((x["decision_id"] and e["decision_id"] == x["decision_id"]) or (not x["decision_id"] and not e["decision_id"] and e["date"] == day))]
        if cand:
            matched.update(cand)
            x["journal"] = {"date": jr[cand[0]]["date"], "lien": jr[cand[0]]["link"],
                            "pourquoi_vente": jr[cand[0]]["fields"].get("Pourquoi vente"),
                            "lecon": jr[cand[0]]["fields"].get("Leçon (1 ligne)")}
        else:
            x["journal"] = None
            missing.append({"id": x["id"], "decision_id": x["decision_id"], "pair": x["pair"], "ferme_le": x["ferme_le"], "gain_eur": x["gain_eur"]})
    extra = [{"date": e["date"], "pair": e["pair"], "mode": e["mode"], "lien": e["link"]} for i, e in enumerate(jr) if i not in matched]

    preds = read_jsonl(F["predictions_log"])
    cur_cap = CAP_HISTORY[-1]
    now = datetime.now(TZ).isoformat(timespec="seconds")
    perf = {
        # --- clés historiques lues par le site (= SIMULATION, rétro compris, comme le capital du gardien) ---
        "win_rate": s_all["taux_reussite"],
        "profit_factor": s_all["rapport_gains_pertes"],
        "profit_factor_infinite": bool(s_all["gagnants"] and not s_all["perdants"]),
        "max_drawdown_pct": round(mdd, 6),
        "brier_score": brier(preds),
        "n_trades": len(closed) + len(open_),
        "n_closed": len(closed),
        "n_open": len(open_),
        # Site « Ordres des bots » / « Ordres remplis (Revolut X) » (onglet Simulation) :
        # « sans objet » quand il n'y a pas d'ordres live (règle équipe 10 oct. 00h06). Le site recopie, il ne calcule pas.
        "ordres_des_bots": "sans objet" if n_live_orders == 0 else n_live_orders,
        "ordres_remplis": "sans objet" if n_live_orders == 0 else n_live_orders,
        "n_predictions": len(preds),
        "total_realized_pnl_eur": s_all["net_eur"],
        "updated_at": now,
        "updated_by": "PM-Compound (scripts/update_performance.py)",
        "fuseau": "Europe/Brussels",
        "notes_fr": [
            "Les clés du haut (win_rate, n_closed, total_realized_pnl_eur…) = simulation seulement, essais « rétro » compris (comptés dans le capital du gardien, accord Quentin 8 oct).",
            "Gain/perte = realized_pnl_eur écrit par le gardien (PM-Risk), frais déjà déduits.",
            "max_drawdown_pct = plus grosse baisse du capital simulé après chaque trade fermé (fraction, 0,01 = 1 %).",
            "Sens : « hausse » = achat puis vente plus haut ; « baisse » = vente de pièces déjà détenues puis rachat plus bas.",
        ],
        # --- nouveau ---
        "totaux": {
            "simulation": {**s_all, "par_sens": by_side(closed),
                           "hors_retro": {**stats(sim_nr), "par_sens": by_side(sim_nr)}},
            "live": {**s_live, "par_sens": by_side(live_closed), "ordres_live_journal": n_live_orders,
                     "note_fr": "Aucun trade réel du pipeline fermé (state/live_orders.jsonl absent ou sans résultat)." if not live_closed else None},
        },
        "par_sens": {"simulation": by_side(closed), "live": by_side(live_closed)},
        "par_sorte": kinds,
        "capital_simule": {
            "depart_eur": start,
            "depart_source": "guardian/state.json bankroll_eur",
            "historique": series,
            "apres_dernier_trade_ferme_eur": round(cap, 6),
            "actuel_eur": eq,
            "actuel_le": st.get("summary_updated_at") or loc(st.get("updated_at")),
            "actuel_source": "guardian/state.json equity_eur",
            "actuel_note_fr": "Valeur du gardien : départ + gains fermés + gain/perte latent des positions ouvertes (frais compris).",
            "latent_ouvert_eur": st.get("unrealized_pnl_eur"), "gain_total_gardien_eur": st.get("total_pnl_eur"),
            "liquidites_eur": st.get("cash_eur"), "sommet_eur": st.get("peak_equity_eur"), "baisse_depuis_sommet": st.get("drawdown_pct"),
            "plus_grosse_baisse": round(mdd, 6),
        },
        "plafond_simulation": {
            "actuel_eur": cur_cap["plafond_eur"], "depuis": cur_cap["depuis"], "historique": CAP_HISTORY,
            "config_gardien": {"max_exposure_pct": cfg.get("max_exposure_pct"), "max_position_pct": cfg.get("max_position_pct"),
                               "bankroll_eur": start,
                               "plafond_calcule_eur": r((cfg.get("max_exposure_pct") or 0) * start, 2)},
            "note_fr": (None if abs((cfg.get("max_exposure_pct") or 0) * start - cur_cap["plafond_eur"]) < 0.01 else
                        f"guardian/config.json donne encore {(cfg.get('max_exposure_pct') or 0) * start:.0f} € (max_exposure_pct {cfg.get('max_exposure_pct')}) : à mettre à jour par PM-Risk."),
        },
        "trades_fermes": closed + live_closed,
        "positions_ouvertes": open_,
        "rapprochement": {
            "journal_manquants": missing,
            "journal_sans_trade_gardien": extra,
            "incoherences": problems,
        },
        "exclus": [f"{t.get('id')} : ligne de test marché de prédiction (demo-selftest), pas un trade crypto"
                   for t in read_jsonl(F["trades_log"]) if t.get("market_id")],
        "sources": {k: str(v.relative_to(ROOT)) for k, v in F.items()},
    }
    return perf


def main(argv):
    perf = build()
    txt = json.dumps(perf, indent=2, ensure_ascii=False) + "\n"
    json.loads(txt)  # validation
    if "--dry-run" not in argv:
        tmp = OUT.with_suffix(".json.tmp")
        tmp.write_text(txt, encoding="utf-8")
        tmp.replace(OUT)
    if "--quiet" not in argv:
        t = perf["totaux"]
        print(f"simulation : {t['simulation']['trades']} fermés, net {t['simulation']['net_eur']} €, réussite {t['simulation']['taux_reussite']}")
        for s, v in perf["par_sens"]["simulation"].items():
            print(f"  {s}: {v['trades']} trades, {v['gagnants']} G / {v['perdants']} P, net {v['net_eur']} €")
        print(f"live : {t['live']['trades']} fermés, net {t['live']['net_eur']} €")
        print(f"capital simulé : {perf['capital_simule']['actuel_eur']} € (après dernier fermé {perf['capital_simule']['apres_dernier_trade_ferme_eur']})")
        rp = perf["rapprochement"]
        print(f"journal manquants : {rp['journal_manquants']}  incohérences : {rp['incoherences']}")
        print(("(dry-run) " if "--dry-run" in argv else "écrit ") + str(OUT))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
