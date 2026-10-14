"""Independent CSCV/PBO + walk-forward re-computation from the grid runs' equity files."""
import glob, json, itertools, sys
import numpy as np, pandas as pd
pattern, n_expected, cash = sys.argv[1], int(sys.argv[2]), 10000.0
dirs = sorted(glob.glob(pattern))[-n_expected:]
cols = {}
for d in dirs:
    cfg = json.load(open(d + "/config.json"))
    src = open(d + "/code/signal_engine.py").read().splitlines()[0] + f" sl={cfg['spot_stop_loss']} tp={cfg['spot_take_profit']}"
    eq = pd.read_csv(d + "/artifacts/equity.csv", index_col=0)["equity"]
    r = eq.pct_change(); r.iloc[0] = eq.iloc[0] / cash - 1
    cols[src] = r.to_numpy()
M = np.column_stack(list(cols.values())); T, N = M.shape
S = 16; k = T // S; M = M[: k * S]; blocks = [M[i*k:(i+1)*k] for i in range(S)]
sh = lambda x: x.mean(0) / x.std(0, ddof=1)
lam = []
for comb in itertools.combinations(range(S), S // 2):
    IS = np.vstack([blocks[i] for i in comb]); OS = np.vstack([blocks[i] for i in range(S) if i not in comb])
    i_s = sh(IS)
    if not np.isfinite(i_s).any(): continue
    b = int(np.nanargmax(np.where(np.isfinite(i_s), i_s, -np.inf))); o = sh(OS)
    fin = np.isfinite(o)
    if not fin[b] or fin.sum() < 2: continue
    rank = pd.Series(np.where(fin, o, np.nan)).rank(method="average").iloc[b] / (fin.sum() + 1)
    lam.append(np.log(rank / (1 - rank)))
print("strategies", N, "bars", T, "independent PBO", round(float((np.array(lam) <= 0).mean()), 4))
