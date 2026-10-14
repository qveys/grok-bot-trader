#!/usr/bin/env python3
"""PM-Risk verdict (8 oct 21:32) into backtest result JSON files.
 A) files WITHOUT verdict_equipe (compound_2026-10-08/*, knowledge/nightly_2026-10-08/*): add the literal object
    verdict_equipe = {autorise_en_reel: "non", par: "PM-Risk", date, raison} by text insertion (other bytes unchanged).
 B) files whose verdict_equipe is PM-Compound's (vt_verdict.py: home/runs/*/run_card.json|summary.json, checks/*.json):
    keep Compound's object, add only verdict_equipe.autorise_en_reel = {ok:false, valeur:"non", par, date, raison, pourquoi}
    (vt_verdict._merge keeps this key; dashboard team_gates reads the dict). Same serialisation as vt_verdict (indent=1).
"""
import glob, json, os, re, sys, collections
APPLY = "--apply" in sys.argv
REFUS = {("team_rebound", "ETH-EUR"), ("team_rebound", "SOL-EUR"), ("team_breakout", "ETH-EUR"),
         ("sell_rebuy", "ETH-EUR"), ("sell_rebuy", "SOL-EUR")}
R_TEAM = "Refusé en live (Risk 8 oct 21:32) : perte sur une moitié d'année et/ou en achat immédiat. Reste permis en simulation."
R_SR = ("Refusé en live (Risk 8 oct 21:32) : gain < 3× frais (vendre haut/racheter bas) et/ou perte sur une moitié "
        "d'année. Reste permis en simulation.")
R_MM = ("Refusé en live (Risk 8 oct 21:32) : MetaMask/Uniswap, gain < 3× frais (vendre haut/racheter bas), "
        "perte nette. Reste permis en simulation.")
R_NONE = "pas encore validé par Risk"
DATE = "2026-10-08 21:32"


def reason(strat, pair, profile):
    strat = re.sub(r"_(robust_base|robust|grid)$", "", str(strat or ""))
    if (strat, pair) in REFUS:
        return R_TEAM if strat.startswith("team_") else (R_MM if profile == "uniswap" else R_SR)
    return R_NONE


def meta(p, d):
    costs = d.get("costs") if isinstance(d.get("costs"), dict) else {}
    strat, pair = d.get("strategy"), d.get("pair")
    if os.path.basename(p) == "run_card.json":
        m = re.match(r"\d{8}_\d{6}_(?:\d+_)?([A-Z]+-[A-Z]+)_[0-9]+[A-Za-z]+_(.+)$", os.path.basename(os.path.dirname(p)))
        if m:
            pair, strat = m.group(1), m.group(2)
        cfgp = os.path.join(os.path.dirname(p), "config.json")
        try:
            prof = (json.load(open(cfgp)).get("costs") or {})
            costs = prof if isinstance(prof, dict) else costs
        except Exception:
            pass
    return strat, pair, costs.get("profile")


out = []
# A) literal object
for p in json.load(open("/tmp/bt_files.json")):
    if "/tools/vibe-trading/" in p:
        continue
    raw = open(p, encoding="utf-8").read(); d = json.loads(raw)
    strat, pair, prof = meta(p, d)
    v = {"autorise_en_reel": "non", "par": "PM-Risk", "date": DATE, "raison": reason(strat, pair, prof)}
    if "verdict_equipe" in d:
        out.append(("A-skip-existing", p, strat, pair, None)); continue
    body = raw.rstrip(); trail = raw[len(body):]
    assert body.endswith("}"), p
    inner = body[:-1].rstrip()
    if "\n" in body.strip():
        first = next(l for l in body.splitlines()[1:] if l.strip())
        ind = len(first) - len(first.lstrip())
        frag = json.dumps({"verdict_equipe": v}, ensure_ascii=False, indent=ind or 2)
        new = inner + ",\n" + "\n".join(frag.splitlines()[1:-1]) + "\n}" + trail
    else:
        new = inner + ', "verdict_equipe": ' + json.dumps(v, ensure_ascii=False) + "}" + trail
    d2 = json.loads(new); got = d2.pop("verdict_equipe")
    assert d2 == d and got == v and list(d2) == list(d), p
    if APPLY:
        with open(p, "w", encoding="utf-8") as fh:
            fh.write(new)
    out.append(("A", p, strat, pair, v["raison"]))
# B) nested in PM-Compound's verdict
for p in [l.strip() for l in open("/workspace/backups/pmb-dashboard-20261009/compound_verdict_files.txt") if l.strip()]:
    try:
        raw = open(p, encoding="utf-8").read(); d = json.loads(raw)
    except Exception as e:
        out.append(("B-unreadable", p, None, None, str(e))); continue
    ve = d.get("verdict_equipe")
    if not isinstance(ve, dict) or json.dumps(d, indent=1, ensure_ascii=False, default=str) != raw:
        out.append(("B-skip-format", p, None, None, None)); continue
    strat, pair, prof = meta(p, d)
    r = reason(strat, pair, prof)
    ar = {"ok": False, "valeur": "non", "par": "PM-Risk", "date": DATE, "raison": r, "pourquoi": r}
    if ve.get("autorise_en_reel") == ar:
        out.append(("B-already", p, strat, pair, r)); continue
    if "autorise_en_reel" in ve:
        out.append(("B-skip-other-ar", p, strat, pair, json.dumps(ve["autorise_en_reel"])[:80])); continue
    ve["autorise_en_reel"] = ar
    if APPLY:
        tmp = p + ".risk.tmp"
        with open(tmp, "w", encoding="utf-8") as fh:
            fh.write(json.dumps(d, indent=1, default=str, ensure_ascii=False))
        json.load(open(tmp, encoding="utf-8"))
        os.replace(tmp, p)
    out.append(("B", p, strat, pair, r))
c = collections.Counter((k, re.sub(r"_(robust_base|robust)$", "", str(s)), pa, (r or "")[:22]) for k, _, s, pa, r in out)
for k, v in sorted(c.items(), key=str):
    print(v, k)
print(len(out), "APPLIED" if APPLY else "dry-run")
if APPLY:
    json.dump(out, open("/workspace/backups/pmb-dashboard-20261009/verdict_files.json", "w"), ensure_ascii=False, indent=1)
