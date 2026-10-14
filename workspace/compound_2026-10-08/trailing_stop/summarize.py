import pandas as pd, numpy as np
d = pd.read_csv("results.csv")
S = {"maker_allfilled": "M", "maker_touch": "T", "taker_market": "K"}
out = []
# 1. headline: fixed vs trail1.5 per pair x strategy
rows = []
for (p, s), g in d.groupby(["pair", "strategy"], sort=False):
    for v in ["fixed", "trail1.5"]:
        r = {sc: g[(g.scenario == sc) & (g.variant == v)].iloc[0] for sc in S}
        m = r["maker_allfilled"]
        rows.append(f"| {p[:3]} | {s.replace('team_','')} | {v} | {m.net_pct:+.2f} | {r['maker_touch'].net_pct:+.2f} | {r['taker_market'].net_pct:+.2f} | "
                    f"{int(m.trades)} | {m.win_rate:.0f} | {m.h1_pct:+.2f} | {m.h2_pct:+.2f} | {m.maxdd_capital_5pct:.2f} | {m.worst_loss_pct:.2f} | {m.avg_loss_pct:.2f} |")
out.append("| pair | strat | stop | net M | net T | net K | trades | win% | H1 (M) | H2 (M) | worst drop capital 5% (M) | biggest loss/trade % | avg loss % |")
out.append("|" + "---|" * 13)
out += rows
# 2. win counts fixed vs trail1.5
out.append("\n### Who keeps more money, fixed vs trailing 1.5 (count of pair×strategy, 9 combos)")
for sc in S:
    f = d[(d.scenario == sc) & (d.variant == "fixed")].set_index(["pair", "strategy"])
    t = d[(d.scenario == sc) & (d.variant == "trail1.5")].set_index(["pair", "strategy"])
    for col, lab in [("net_pct", "net year"), ("h1_pct", "H1"), ("h2_pct", "H2")]:
        w = (t[col] > f[col] + 1e-9).sum(); l = (t[col] < f[col] - 1e-9).sum()
        out.append(f"- {sc} {lab}: trailing better {w}, fixed better {l}, tie {9-w-l}; sum net fixed {f[col].sum():+.2f} vs trailing {t[col].sum():+.2f}")
    dd_t = (t.maxdd_capital_5pct < f.maxdd_capital_5pct - 1e-9).sum(); dd_f = (t.maxdd_capital_5pct > f.maxdd_capital_5pct + 1e-9).sum()
    out.append(f"- {sc} worst drop: trailing smaller {dd_t}, fixed smaller {dd_f}; avg loss/losing trade fixed {f.avg_loss_pct.mean():.2f}% vs trailing {t.avg_loss_pct.mean():.2f}%")
# 3. flips
out.append("\n### Half-year flips (fixed vs trailing 1.5: winner in H1 differs from H2)")
for sc in S:
    f = d[(d.scenario == sc) & (d.variant == "fixed")].set_index(["pair", "strategy"])
    t = d[(d.scenario == sc) & (d.variant == "trail1.5")].set_index(["pair", "strategy"])
    for k in f.index:
        a1, a2 = np.sign(t.h1_pct[k] - f.h1_pct[k]), np.sign(t.h2_pct[k] - f.h2_pct[k])
        if a1 and a2 and a1 != a2:
            out.append(f"- {sc} {k[0]} {k[1]}: H1 {'trailing' if a1>0 else 'fixed'} ({f.h1_pct[k]:+.2f} fixed / {t.h1_pct[k]:+.2f} trail), "
                       f"H2 {'trailing' if a2>0 else 'fixed'} ({f.h2_pct[k]:+.2f} / {t.h2_pct[k]:+.2f})")
# 4. sensitivity: all variants net per scenario
out.append("\n### Sensitivity (net % for the year): fixed / trail 0.75 / trail 1.5 / trail 2.25 / trail 1.5 without take-profit")
out.append("| pair | strat | scen | fixed | t0.75 | t1.5 | t2.25 | t1.5 noTP | fixed noTP |")
out.append("|---|---|---|---|---|---|---|---|---|")
for (p, s, sc), g in d.groupby(["pair", "strategy", "scenario"], sort=False):
    g = g.set_index("variant").net_pct
    out.append(f"| {p[:3]} | {s.replace('team_','')} | {S[sc]} | {g['fixed']:+.2f} | {g['trail0.75']:+.2f} | {g['trail1.5']:+.2f} | {g['trail2.25']:+.2f} | "
               + (f"{g['trail1.5_noTP']:+.2f}" if "trail1.5_noTP" in g else "n/a") + " | " + (f"{g['fixed_noTP']:+.2f}" if "fixed_noTP" in g else "n/a") + " |")
out.append("\n### Sum over 9 combos per variant (net %, simple sum, just to rank)")
pv = d.pivot_table(index="scenario", columns="variant", values="net_pct", aggfunc="sum").round(2)
out.append(pv.to_string())
pt = d[d.strategy != "sell_rebuy"].pivot_table(index="scenario", columns="variant", values="net_pct", aggfunc="sum").round(2)
out.append("\nteam_* only (6 combos):\n" + pt.to_string())
ps = d[d.strategy == "sell_rebuy"].pivot_table(index="scenario", columns="variant", values="net_pct", aggfunc="sum").round(2)
out.append("\nsell_rebuy only (3 combos):\n" + ps.to_string())
dd = d.pivot_table(index="scenario", columns="variant", values="maxdd_capital_5pct", aggfunc="mean").round(3)
out.append("\nMean worst drop on our capital (5% stakes), %:\n" + dd.to_string())
Path = __import__("pathlib").Path
Path("tables.md").write_text("\n".join(out) + "\n")
print("\n".join(out))
