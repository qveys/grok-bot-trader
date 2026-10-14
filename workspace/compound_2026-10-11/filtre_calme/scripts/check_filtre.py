"""Vérif indépendante du filtre --min-range24 (achats team_*) à partir de fills.jsonl (bar_idx) :
plage des 24 bougies 1 h fermées jusqu'à la bougie du signal (barre avant l'achat) / clôture du signal > X %.
Usage : check_filtre.py X fichier_X.json fichier_X0.json"""
import json, sys, glob, pandas as pd
def load(j):
    d = json.load(open(j)); rd = d['run_dir']
    o = pd.read_csv(glob.glob(rd + '/artifacts/ohlcv_*.csv')[0]); o['t'] = pd.to_datetime(o.trade_date)
    start = o.index[o.t == pd.Timestamp(d['period'][0])][0]
    rng = ((o.high.rolling(24).max() - o.low.rolling(24).min()) / o.close).to_numpy()
    F = [json.loads(l) for l in open(rd + '/artifacts/fills.jsonl')]
    buys = [start + f['bar_idx'] for f in F if f['action'] == 'open']
    return [(o.t[i], rng[i - 1], o.t[i].tz_localize('UTC').tz_convert('Europe/Brussels').hour) for i in buys]
x = float(sys.argv[1]); X = load(sys.argv[2]); Z = load(sys.argv[3])
bad = [b for b in X if not b[1] > x / 100]
exp = {b[0] for b in Z if b[1] > x / 100}; got = {b[0] for b in X}
print(f'X={x}: {len(X)} achats, heures locales {sorted(set(b[2] for b in X))}, sous le seuil : {len(bad)} {[(str(b[0]), round(b[1]*100,2)) for b in bad][:5]} ; '
      f'X=0 au-dessus du seuil : {len(exp)}, retrouvés : {len(exp & got)}, nouveaux dans X : {len(got - {b[0] for b in Z})}')
