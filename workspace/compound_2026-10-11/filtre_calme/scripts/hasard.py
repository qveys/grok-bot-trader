"""Chance ou pas ? Pour chaque test achat (team_*, frais revolutx immédiat) où le filtre X retire des trades :
on tire 5000 fois au hasard le même nombre de trades parmi ceux du test sans filtre (X=0) et on compte
combien de tirages font au moins aussi bien (somme des % nets par trade). p petit = le filtre choisit mieux que le hasard."""
import json, glob, re, os, numpy as np, pandas as pd
rng = np.random.default_rng(1)
def rets(j):
    rd = json.load(open(j))['run_dir']; t = pd.read_csv(rd + '/artifacts/trades.csv')
    return t[t.side.str.lower() == 'sell'].return_pct.to_numpy(dtype=float)
out = []
for f in sorted(glob.glob('tool_json/x[1-9]*_team_*_revolutx.json')):
    n = os.path.basename(f); x = float(re.match(r'x([\d.]+)_', n).group(1)); b = 'tool_json/x0_' + n.split('_', 1)[1]
    a0, ax = rets(b), rets(f)
    if len(ax) == len(a0) or len(ax) == 0: continue
    s = ax.sum(); draws = np.array([rng.choice(a0, len(ax), replace=False).sum() for _ in range(5000)]) if len(ax) <= len(a0) else None
    p = float((draws >= s - 1e-12).mean()) if draws is not None else np.nan
    out.append(dict(x=x, test=n.split('_', 1)[1][:-5], n0=len(a0), nx=len(ax), somme_x0=round(a0.sum(), 2), somme_x=round(s, 2), p=round(p, 4)))
o = pd.DataFrame(out); o.to_csv('hasard_tirages.csv', index=False)
print(o.groupby('x').apply(lambda g: pd.Series(dict(tests=len(g), p_median=g.p.median(), p_sous_5pct=int((g.p < 0.05).sum()), attendu_par_chance=round(0.05 * len(g), 1)))).to_string())
print(o[o.p < 0.05].to_string())
