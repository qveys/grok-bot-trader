"""results.csv -> tables.md (all tables) ; prints compact ones."""
import pandas as pd, numpy as np
d = pd.read_csv("results.csv")
L = []
def md(df): return df.to_markdown()
def block(strat, sc, ref_tp="a_fixed_tp", ref_notp=None):
    x = d[(d.strategy == strat) & (d.scenario == sc)].copy()
    rows = []
    for v, g in x.groupby("variant"):
        g = g.set_index("pair")
        ref = ref_notp if ("noTP" in v and ref_notp) else ref_tp
        r = x[x.variant == ref].set_index("pair")
        both = [p for p in g.index if v != ref and g.at[p, "h1_pct"] > r.at[p, "h1_pct"] and g.at[p, "h2_pct"] > r.at[p, "h2_pct"]]
        rows.append({"variant": v, "ETH": g.at["ETH-EUR", "net_pct"], "SOL": g.at["SOL-EUR", "net_pct"], "BTC": g.at["BTC-EUR", "net_pct"],
                     "SUM": round(g.net_pct.sum(), 2), "H1": round(g.h1_pct.sum(), 2), "H2": round(g.h2_pct.sum(), 2),
                     "trades": int(g.trades.sum()), "win%": round(float((g.win_rate * g.trades).sum() / g.trades.sum()), 1),
                     "maxDD_cap%": g.maxdd_capital_5pct.max(), "worst%": g.worst_trade_pct.min(),
                     "oui": int((g.verdict == "oui").sum()), f"beats {ref} both halves": ",".join(p[:3] for p in both) or "-"})
    return pd.DataFrame(rows).set_index("variant")
for strat, scs, ref_notp in [("sell_rebuy", ["K_revolutx", "K2_all_0.14", "G_guardian_0.05", "M_maker_allfilled", "T_maker_touch"], None),
                             ("team_rebound", ["K_immediate_0.14", "T_maker_touch", "G_guardian_0.05", "M_maker_allfilled"], "b_fixed_noTP"),
                             ("team_breakout", ["K_immediate_0.14", "T_maker_touch", "G_guardian_0.05", "M_maker_allfilled"], "b_fixed_noTP")]:
    for sc in scs:
        L += [f"\n## {strat} — {sc}\n", md(block(strat, sc, ref_notp=ref_notp)), ""]
L += ["\n## Détail par essai (H1/H2 par paire)\n", md(d[["pair", "strategy", "scenario", "variant", "net_pct", "trades", "win_rate", "h1_pct", "h2_pct",
                                                        "maxdd_capital_5pct", "worst_trade_pct", "verdict", "verdict_reasons"]].set_index("pair"))]
open("tables.md", "w").write("# Tableaux — arrêt suiveur (10 oct. 2026)\nNet = % après frais (sell_rebuy : % de pièces vs garder). H1 = ventes/achats avant 2026-04-07 12:00 UTC, H2 après (sommes des 3 paires). maxDD_cap = pire baisse outil × 5 %. worst = pire trade. oui = verdict équipe (vt_verdict) sur 3 paires.\n" + "\n".join(L))
print(block("sell_rebuy", "K_revolutx").to_string())
print(block("sell_rebuy", "K2_all_0.14")[["SUM","H1","H2","trades","oui"]].to_string())
print(block("sell_rebuy", "G_guardian_0.05")[["SUM","H1","H2","trades","oui"]].to_string())
print(block("team_rebound", "K_immediate_0.14", ref_notp="b_fixed_noTP").to_string())
print(block("team_breakout", "K_immediate_0.14", ref_notp="b_fixed_noTP").to_string())
print(block("team_breakout", "T_maker_touch", ref_notp="b_fixed_noTP")[["SUM","H1","H2","oui"]].to_string())
print(block("team_rebound", "T_maker_touch", ref_notp="b_fixed_noTP")[["SUM","H1","H2","oui"]].to_string())
