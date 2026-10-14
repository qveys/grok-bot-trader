import json, glob, os, re, pandas as pd
R = []
for f in sorted(glob.glob('tool_json/*.json')):
    d = json.load(open(f)); n = os.path.basename(f)[:-5]
    m = re.match(r'(BTC|ETH|SOL)_(team_rebound|team_breakout|sell_rebuy_tm200|sell_rebuy_tm0)_tp([\d.]+)_r([\d.]+)_(.+)', n)
    p, s, tp, r, c = m.groups(); tp, r = float(tp), float(r); sl = round(tp/r, 4)
    sell = s.startswith('sell')
    if sell:
        net, n_tr = d['coin_gain_vs_hold_pct'], d['cycles']
    else:
        fm = d.get('fill_model') or {}
        res = fm.get('result') if fm else None
        net = res['total_return_pct'] if res else d['total_return_pct']; n_tr = res['trades'] if res else d['trades']
    ve = d['verdict_equipe']
    # frais par issue : cible / arrêt (aller-retour, %)
    if c in ('revolutx', 'alltaker'): fw, fl = 0.28, 0.28
    else: fw, fl = 0.0, 0.14          # maker-touch (achat & cible à prix fixé 0 %, arrêt au marché 0,14 %) ; sell_rebuy revolutx : vente+rachat visé 0 %, sécurité 0,14 %
    if sell and c == 'revolutx': fw, fl = 0.0, 0.14
    be = (sl + fl) / (tp - fw + sl + fl) * 100
    R.append(dict(pair=p, sens='baisse' if sell else 'hausse', regle=s, frais=c, tp=tp, rapport=r, sl=sl,
        niveau={1: 'prudente', 1.5: 'équilibrée', 2: 'risquée'}[r], trades=n_tr, net_pct=round(net, 2),
        win_pct=d.get('win_rate_pct'), win_seuil_pct=round(be, 1), h1=ve.get('moitie_1_pct'), h2=ve.get('moitie_2_pct'),
        dd_cap=ve.get('pire_baisse_capital_pct'), verdict_outil=ve.get('test_du_passe_reussi'), raisons='; '.join(ve.get('raisons') or [])))
df = pd.DataFrame(R)
# critère achat immédiat recalculé : maker-touch jugé aussi avec le run revolutx du même réglage
imm = df[df.frais == 'revolutx'].set_index(['pair', 'regle', 'tp', 'rapport']).net_pct
def ok(x):
    i = imm.get((x.pair, x.regle, x.tp, x.rapport), x.net_pct)
    return 'oui' if (x.net_pct > 0 and x.trades >= 20 and x.h1 > 0 and x.h2 > 0 and abs(x.dd_cap) < 8 and i > 0) else 'non'
df['passe_test'] = df.apply(ok, axis=1)
df['deux_moities_pos'] = (df.h1 > 0) & (df.h2 > 0)
df.to_csv('../backtest_grille.csv', index=False)
print(len(df), 'runs ; passe:', (df.passe_test == 'oui').sum(), '; outil oui:', (df.verdict_outil == 'oui').sum())
pos = df[(df.net_pct > 0) & df.deux_moities_pos]
print('net>0 et 2 moitiés >0 :', len(pos)); print(pos.sort_values('tp').to_string())
# plus petite cible gagnante dans les deux moitiés, par paire × sens × frais
print(pos.groupby(['pair', 'sens', 'frais']).tp.min())
# vue par cible : combien de cases positives / 2 moitiés
g = df.groupby(['tp']).apply(lambda x: pd.Series(dict(cases=len(x), net_pos=(x.net_pct > 0).sum(), deux_moities=((x.net_pct > 0) & x.deux_moities_pos).sum(), passe=(x.passe_test == 'oui').sum(), net_median=x.net_pct.median(), trades_med=x.trades.median())))
print(g)
g.to_csv('../backtest_par_cible.csv')
