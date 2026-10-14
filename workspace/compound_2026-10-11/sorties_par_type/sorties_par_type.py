#!/usr/bin/env python3
"""PM-Compound — sorties par type (simulation, fermées depuis 2026-10-08).
Lecture seule : guardian/state.json, state/trades_log.jsonl, state/price_ticks/*.jsonl,
bougies publiques 5 min Coinbase (Kraken en secours). Aucun ordre, aucun secret.
Contrefactuel « idée morte » : laissé ouvert jusqu'au 1er de (arrêt, cible) touché après la fermeture réelle,
côté sortie (bid pour revendre un achat, ask pour racheter une vente ; mid en secours) ;
trous > 90 s comblés par bougies 5 min (haut/bas ; arrêt d'abord si les deux dans la même bougie).
Remplissage au prix du niveau ; frais 0,05 % par côté (FEE_REVOLUT, guardian/scripts/paper_fill.py)."""
import json, glob, csv, sys, time, urllib.request
from datetime import datetime, timezone, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path('/workspace/predict-market-bot')
OUT = Path(__file__).resolve().parent
TZ = ZoneInfo('Europe/Brussels')
sys.path.insert(0, str(ROOT / 'guardian/scripts'))
FEE = 0.0005
try:
    import re
    m = re.search(r'FEE_REVOLUT\s*=\s*([0-9.]+)', (ROOT/'guardian/scripts/paper_fill.py').read_text())
    FEE = float(m.group(1))
except Exception:
    pass
GAP = 90
NOW = datetime.now(timezone.utc)

def p(ts): return datetime.fromisoformat(ts.replace('Z', '+00:00')).astimezone(timezone.utc)
def loc(dt): return dt.astimezone(TZ).strftime('%d/%m %Hh%M')

state = json.loads((ROOT/'guardian/state.json').read_text())
trades = [json.loads(l) for l in open(ROOT/'state/trades_log.jsonl')]
pos_by_dec = {x.get('decision_id'): x for x in state['positions'] if x.get('decision_id')}

# --- fermetures depuis 2026-10-08 (résultats = trades_log, D-021 corrigé inclus) ---
closes = {}
for t in trades:
    cr = t.get('close_reason'); d = t.get('decision_id')
    if not cr or not d or p(t['ts']) < datetime(2026,10,8,tzinfo=timezone.utc): continue
    c = closes.setdefault(d, {'dec': d, 'pair': t['pair'], 'pnl': 0.0, 'reasons': [], 'close_ts': None, 'close_price': None, 'label': t.get('label')})
    c['pnl'] += float(t.get('realized_pnl_eur') or 0)
    c['reasons'].append(cr)
    if cr != 'idee_morte_reste':
        c['close_ts'] = p(t['ts']); c['close_price'] = float(t['price'])
rows = []
for d, c in closes.items():
    pos = pos_by_dec[d]
    side = 'hausse' if pos['side'] == 'long' else 'baisse'
    opn = next(t for t in trades if t.get('decision_id') == d and t.get('id') == pos['id'])
    reason = c['reasons'][0]
    grp = {'stop_hit': '1 arrêt', 'target_hit': '2 cible', 'idee_morte': '3 idée morte'}[reason]
    rows.append(dict(dec=d, pair=c['pair'], side=side, size_eur=round(float(opn['amount_eur']), 2),
        qty=float(opn['qty']), entry=float(opn['price']), entry_fee=float(opn.get('fee_eur') or 0),
        open_ts=p(opn['ts']), close_ts=c['close_ts'], close_price=c['close_price'],
        stop=float(pos.get('stop_price') or pos.get('stop_price_eur')), target=float(pos['target_price']),
        actual=round(c['pnl'], 4), group=grp, retro=(c['label'] == 'retro')))

# --- prix ---
ticks = {}
for f in sorted(glob.glob(str(ROOT/'state/price_ticks/2026-*.jsonl'))):
    for l in open(f):
        try: x = json.loads(l)
        except Exception: continue
        ticks.setdefault(x['pair'], []).append(x)
for k in ticks: ticks[k].sort(key=lambda x: x['ts'])

_cc = {}
def candles(pair, a, b):
    """bougies 5 min [t0, low, high] couvrant [a,b] ; Coinbase puis Kraken."""
    out = []
    s = a.replace(second=0, microsecond=0) - timedelta(minutes=a.minute % 5)
    while s < b:
        e = min(s + timedelta(minutes=5*290), b + timedelta(minutes=5))
        key = (pair, s, e)
        if key not in _cc:
            url = f"https://api.exchange.coinbase.com/products/{pair}/candles?granularity=300&start={s:%Y-%m-%dT%H:%M:%SZ}&end={e:%Y-%m-%dT%H:%M:%SZ}"
            data = None
            for _ in range(3):
                try:
                    req = urllib.request.Request(url, headers={'User-Agent': 'pm-compound-readonly'})
                    data = json.loads(urllib.request.urlopen(req, timeout=20).read()); break
                except Exception: time.sleep(1)
            if isinstance(data, list):
                _cc[key] = [(datetime.fromtimestamp(r[0], timezone.utc), float(r[1]), float(r[2]), 'coinbase') for r in data]
            else:
                kp = {'BTC-EUR': 'XBTEUR', 'ETH-EUR': 'ETHEUR', 'SOL-EUR': 'SOLEUR'}[pair]
                kd = json.loads(urllib.request.urlopen(f"https://api.kraken.com/0/public/OHLC?pair={kp}&interval=5&since={int(s.timestamp())-1}", timeout=20).read())
                res = next(v for k, v in kd['result'].items() if k != 'last')
                _cc[key] = [(datetime.fromtimestamp(r[0], timezone.utc), float(r[3]), float(r[2]), 'kraken') for r in res]
            time.sleep(0.35)
        out += _cc[key]
        s = e
    seen = {}
    for c in out: seen[c[0]] = c
    return sorted(seen.values())

gap_log = []
def events(pair, a, b, exit_px):
    """Suite chronologique (t, lo, hi, src) de a à b : ticks côté sortie + bougies dans les trous > 90 s."""
    tk = [x for x in ticks.get(pair, []) if a <= p(x['ts']) <= b]
    ev, prev = [], a
    def fill(g0, g1):
        if (g1 - g0).total_seconds() <= GAP: return
        cs = [c for c in candles(pair, g0, g1) if c[0] + timedelta(minutes=5) > g0 and c[0] < g1]
        gap_log.append((pair, g0, g1, len(cs), cs[0][3] if cs else 'aucune'))
        for c in cs: ev.append((max(c[0], g0), c[1], c[2], 'bougie5m-' + c[3]))
    for x in tk:
        t = p(x['ts']); fill(prev, t)
        v = x.get(exit_px) or x.get('mid')
        ev.append((t, v, v, 'tick-' + (exit_px if x.get(exit_px) else 'mid')))
        prev = t
    fill(prev, b)
    ev.sort(key=lambda e: e[0])
    return ev

def first_touch(r, a, b):
    exit_px = 'bid' if r['side'] == 'hausse' else 'ask'
    for t, lo, hi, src in events(r['pair'], a, b, exit_px):
        if r['side'] == 'hausse':
            s_hit, t_hit = lo <= r['stop'], hi >= r['target']
        else:
            s_hit, t_hit = hi >= r['stop'], lo <= r['target']
        if s_hit: return ('arrêt', t, src)          # arrêt d'abord si les deux
        if t_hit: return ('cible', t, src)
    return None

def pnl_at(r, px):
    sign = 1 if r['side'] == 'hausse' else -1
    return round(sign * r['qty'] * (px - r['entry']) - r['entry_fee'] - r['qty'] * px * FEE, 4)

def latest(pair, side):
    x = ticks[pair][-1]; k = 'bid' if side == 'hausse' else 'ask'
    return p(x['ts']), float(x.get(k) or x['mid'])

for r in rows:
    r.update(pre_touch='', cf_status='', cf_level='', cf_time='', cf_delay_h='', cf_result='', cf_src='')
    if r['group'] != '3 idée morte': continue
    pre = first_touch(r, r['open_ts'], r['close_ts'])
    r['pre_touch'] = 'non' if not pre else f"{pre[0]} {loc(pre[1])} ({pre[2]})"
    ft = first_touch(r, r['close_ts'] + timedelta(seconds=1), NOW)
    if ft:
        lvl, t, src = ft
        r.update(cf_status='tranché', cf_level=lvl, cf_time=loc(t), cf_src=src,
                 cf_delay_h=round((t - r['close_ts']).total_seconds()/3600, 2),
                 cf_result=pnl_at(r, r['stop'] if lvl == 'arrêt' else r['target']))
    else:
        t, px = latest(r['pair'], r['side'])
        r.update(cf_status='pas encore tranché', cf_level=f'valeur actuelle @ {px}', cf_time=loc(t),
                 cf_result=pnl_at(r, px), cf_src='dernier tick')

# --- sorties ---
rows.sort(key=lambda r: (r['retro'], r['group'], r['close_ts']))
cols = ['dec','pair','side','size_eur','entry','stop','target','group','retro','open_ts','close_ts','close_price','actual',
        'pre_touch','cf_status','cf_level','cf_time','cf_delay_h','cf_result','cf_src']
with open(OUT/'sorties_par_type.csv', 'w', newline='') as f:
    w = csv.writer(f); w.writerow(cols)
    for r in rows:
        w.writerow([loc(r[c]) if isinstance(r[c], datetime) else r[c] for c in cols])
json.dump({'now': loc(NOW), 'fee_one_way': FEE,
           'rows': [{k: (loc(v) if isinstance(v, datetime) else v) for k, v in r.items()} for r in rows],
           'gaps': [(g[0], loc(g[1]), loc(g[2]), g[3], g[4]) for g in gap_log]},
          open(OUT/'result.json', 'w'), ensure_ascii=False, indent=1)
print(json.dumps(json.load(open(OUT/'result.json')), ensure_ascii=False, indent=1))

# --- totaux ---
live = [r for r in rows if not r['retro']]
tot = {}
for r in live:
    g = tot.setdefault(r['group'], [0, 0.0]); g[0] += 1; g[1] += r['actual']
im = [r for r in live if r['group'] == '3 idée morte']
res = [r for r in im if r['cf_status'] == 'tranché']
pend = [r for r in im if r['cf_status'] != 'tranché']
summ = {
  'groupes': {k: [v[0], round(v[1], 4)] for k, v in sorted(tot.items())},
  'retro': [round(sum(r['actual'] for r in rows if r['retro']), 4), len([r for r in rows if r['retro']])],
  'im_tranches_reel': round(sum(r['actual'] for r in res), 4), 'im_tranches_cf': round(sum(r['cf_result'] for r in res), 4),
  'im_ouverts_reel': round(sum(r['actual'] for r in pend), 4), 'im_ouverts_marque': round(sum(r['cf_result'] for r in pend), 4),
  'im_total_reel': round(sum(r['actual'] for r in im), 4), 'im_total_cf_avec_marques': round(sum(r['cf_result'] for r in im), 4),
  'cible': sum(r['cf_level'] == 'cible' for r in res), 'arret': sum(r['cf_level'] == 'arrêt' for r in res),
  'gaps_uniques': sorted(set((g[0], loc(g[1]), loc(g[2]), g[3]) for g in gap_log)),
}
json.dump(summ, open(OUT/'totaux.json', 'w'), ensure_ascii=False, indent=1)
print(json.dumps(summ, ensure_ascii=False, indent=1))
