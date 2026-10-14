"""Analyse du filtre plage 24 h. Net = % après frais du test (achats : % du capital outil ; ventes : % de pièces vs garder)."""
import json, glob, os, re, pandas as pd, numpy as np
R = []
for f in sorted(glob.glob('tool_json/x*.json')):
    n = os.path.basename(f)[:-5]
    try: d = json.load(open(f))
    except Exception: print('illisible', n); continue
    m = re.match(r'x([\d.]+)_(BTC|ETH|SOL)_(team_rebound|team_breakout|sell_rebuy_tm200|sell_rebuy_tm0)_tp([\d.]+)_r([\d.]+)_(.+)', n)
    x, p, s, tp, r, c = m.groups(); sell = s.startswith('sell')
    if sell: net, nt = d['coin_gain_vs_hold_pct'], d['cycles']
    else:
        res = (d.get('fill_model') or {}).get('result')
        net, nt = (res['total_return_pct'], res['trades']) if res else (d['total_return_pct'], d['trades'])
    ve = d['verdict_equipe']
    R.append(dict(x=float(x), pair=p, sens='baisse' if sell else 'hausse', regle=s, frais=c, tp=float(tp), rapport=float(r),
                  trades=nt, net=net, h1=ve.get('moitie_1_pct'), h2=ve.get('moitie_2_pct'), dd_cap=ve.get('pire_baisse_capital_pct')))
df = pd.DataFrame(R)
df['h1'] = df.h1.fillna(0.0); df['h2'] = df.h2.fillna(0.0)
key = ['pair', 'regle', 'frais', 'tp', 'rapport']
imm = df[df.frais == 'revolutx'].set_index(['x', 'pair', 'regle', 'tp', 'rapport']).net
df['passe'] = [ (r.net > 0 and r.trades >= 20 and r.h1 > 0 and r.h2 > 0 and abs(r.dd_cap or 0) < 8
                 and imm.get((r.x, r.pair, r.regle, r.tp, r.rapport), r.net) > 0) for r in df.itertuples()]
base = df[df.x == 0].set_index(key)
df = df.join(base[['net', 'h1', 'h2', 'trades']].rename(columns=lambda c: c + '_x0'), on=key)
df['gain_vs_x0'] = df.net - df.net_x0
df['mieux_2_moities'] = (df.h1 > df.h1_x0 + 1e-9) & (df.h2 > df.h2_x0 + 1e-9)
df['pire_2_moities'] = (df.h1 < df.h1_x0 - 1e-9) & (df.h2 < df.h2_x0 - 1e-9)
df['filtre_mord'] = df.trades != df.trades_x0
df.to_csv('filtre_grille.csv', index=False)

def agg(x):
    b = x[x.filtre_mord]
    return pd.Series(dict(configs=len(x), net_somme=round(x.net.sum(), 1), net_mediane=round(x.net.median(), 2),
        trades_par_an_moy=round(x.trades.mean(), 1), trades_total=int(x.trades.sum()), passent=int(x.passe.sum()),
        h1_somme=round(x.h1.sum(), 1), h2_somme=round(x.h2.sum(), 1),
        configs_ou_filtre_mord=len(b), mieux_2_moities=int(b.mieux_2_moities.sum()), pire_2_moities=int(b.pire_2_moities.sum())))
parX = df.groupby('x').apply(agg); parX.to_csv('par_X.csv'); print(parX.to_string())
pg = df.groupby(['pair', 'sens', 'x']).apply(agg); pg.to_csv('par_paire_sens_X.csv')
best = []
for (p, s), g in pg.groupby(level=[0, 1]):
    g = g.droplevel([0, 1]); bx = g.net_somme.idxmax()
    best.append(dict(paire=p, sens=s, meilleur_X=bx, net_somme=g.loc[bx, 'net_somme'], net_somme_X0=g.loc[0.0, 'net_somme'],
        h1=g.loc[bx, 'h1_somme'], h2=g.loc[bx, 'h2_somme'], h1_X0=g.loc[0.0, 'h1_somme'], h2_X0=g.loc[0.0, 'h2_somme'],
        trades_an_moy=g.loc[bx, 'trades_par_an_moy'], trades_an_moy_X0=g.loc[0.0, 'trades_par_an_moy'],
        passent=g.loc[bx, 'passent'], passent_X0=g.loc[0.0, 'passent'], configs=g.loc[bx, 'configs']))
best = pd.DataFrame(best); best.to_csv('meilleur_X_par_paire_sens.csv', index=False); print(best.to_string())
pr = df.groupby(['regle', 'x']).apply(agg); pr.to_csv('par_regle_X.csv'); print(pr[['net_somme', 'trades_par_an_moy', 'passent', 'h1_somme', 'h2_somme', 'configs_ou_filtre_mord', 'mieux_2_moities', 'pire_2_moities']].to_string())
print(df[df.passe].sort_values(['x', 'pair']).groupby('x').apply(lambda g: '; '.join(f"{r.pair} {r.regle} {r.frais} {r.tp:g}/r{r.rapport:g} ({r.trades} tr, {r.net:+.1f})" for r in g.itertuples())).to_string())
