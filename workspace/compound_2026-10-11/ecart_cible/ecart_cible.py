#!/usr/bin/env python3
"""PM-Compound — écart à la cible et meilleur mouvement favorable (simu fermées depuis 8 oct.).
Lecture seule. Ticks 30 s côté sortie (bid pour hausse, ask pour baisse, mid en secours) ;
trous > 90 s comblés par bougies 5 min Coinbase (haut pour hausse, bas pour baisse), étiquetées.
Contexte : mouvement favorable max dans 6 h / 24 h après chaque entrée sur une grille 5 min (8–11 oct.),
série 5 min mid (ticks) + bougies Coinbase dans les trous."""
import json, glob, csv, time, statistics as st, urllib.request
from datetime import datetime, timezone, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo
ROOT = Path('/workspace/predict-market-bot'); OUT = Path(__file__).resolve().parent
TZ = ZoneInfo('Europe/Brussels'); GAP = 90; NOW = datetime.now(timezone.utc)
def p(ts): return datetime.fromisoformat(ts.replace('Z', '+00:00')).astimezone(timezone.utc)
def loc(dt): return dt.astimezone(TZ).strftime('%d/%m %Hh%M')

state = json.loads((ROOT/'guardian/state.json').read_text())
trades = [json.loads(l) for l in open(ROOT/'state/trades_log.jsonl')]
pos_by_dec = {x.get('decision_id'): x for x in state['positions'] if x.get('decision_id')}
closes = {}
for t in trades:
    cr, d = t.get('close_reason'), t.get('decision_id')
    if cr and d and cr != 'idee_morte_reste' and p(t['ts']) >= datetime(2026,10,8,tzinfo=timezone.utc):
        closes[d] = t
rows = []
for d, c in closes.items():
    pos = pos_by_dec[d]; opn = next(t for t in trades if t.get('id') == pos['id'])
    side = 'hausse' if pos['side'] == 'long' else 'baisse'
    rows.append(dict(dec=d, pair=c['pair'], side=side, retro=c.get('label') == 'retro',
        exit_type={'stop_hit':'arrêt','target_hit':'cible','idee_morte':'idée morte'}[c['close_reason']],
        entry=float(opn['price']), target=float(pos['target_price']), stop=float(pos['stop_price']),
        open_ts=p(opn['ts']), close_ts=p(c['ts']), actual=round(float(c.get('realized_pnl_eur') or 0)
            + (sum(float(t.get('realized_pnl_eur') or 0) for t in trades if t.get('decision_id')==d and t.get('close_reason')=='idee_morte_reste')), 4)))

ticks = {}
for f in sorted(glob.glob(str(ROOT/'state/price_ticks/2026-*.jsonl'))):
    for l in open(f):
        try: x = json.loads(l); ticks.setdefault(x['pair'], []).append(x)
        except Exception: pass
for k in ticks: ticks[k].sort(key=lambda x: x['ts'])

_cache = {}
def candles(pair, a, b):
    """[(t0, low, high, open)] 5 min Coinbase couvrant [a,b]."""
    out = []; s = a.replace(second=0, microsecond=0) - timedelta(minutes=a.minute % 5)
    while s < b:
        e = min(s + timedelta(minutes=5*290), b + timedelta(minutes=5)); key = (pair, s, e)
        if key not in _cache:
            url = f"https://api.exchange.coinbase.com/products/{pair}/candles?granularity=300&start={s:%Y-%m-%dT%H:%M:%SZ}&end={e:%Y-%m-%dT%H:%M:%SZ}"
            data = None
            for _ in range(3):
                try: data = json.loads(urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent':'pm-compound-readonly'}), timeout=20).read()); break
                except Exception: time.sleep(1)
            if not isinstance(data, list): raise SystemExit(f'Coinbase KO {pair} {s}')
            _cache[key] = [(datetime.fromtimestamp(r[0], timezone.utc), float(r[1]), float(r[2]), float(r[3])) for r in data]
            time.sleep(0.35)
        out += _cache[key]; s = e
    return sorted({c[0]: c for c in out}.values())

def series(pair, a, b, px):
    """[(t, lo, hi, src)] ticks (prix px, mid en secours) + bougies dans trous > 90 s."""
    ev, prev = [], a
    def fill(g0, g1):
        if (g1 - g0).total_seconds() <= GAP: return
        for c in candles(pair, g0, g1):
            if c[0] + timedelta(minutes=5) > g0 and c[0] < g1: ev.append((max(c[0], g0), c[1], c[2], 'bougie'))
    for x in ticks.get(pair, []):
        t = p(x['ts'])
        if t < a or t > b: continue
        fill(prev, t); v = float(x.get(px) or x['mid']); ev.append((t, v, v, 'tick')); prev = t
    fill(prev, b)
    return sorted(ev)

for r in rows:
    px = 'bid' if r['side'] == 'hausse' else 'ask'
    ev = series(r['pair'], r['open_ts'], r['close_ts'], px)
    if r['side'] == 'hausse':
        best = max(ev, key=lambda e: e[2]); bp = best[2]; mv = (bp - r['entry']) / r['entry'] * 100
    else:
        best = min(ev, key=lambda e: e[1]); bp = best[1]; mv = (r['entry'] - bp) / r['entry'] * 100
    tgt = abs(r['target'] - r['entry']) / r['entry'] * 100
    r.update(target_pct=round(tgt, 3), stop_pct=round(abs(r['stop'] - r['entry']) / r['entry'] * 100, 3),
             hours_open=round((r['close_ts'] - r['open_ts']).total_seconds() / 3600, 2),
             best_price=bp, best_move_pct=round(mv, 3), best_at=loc(best[0]), best_src=best[3],
             share_of_target_pct=round(mv / tgt * 100, 1))


# --- plage jour (haut-bas) par paire, jours Bruxelles 8–11 oct., mid ticks + bougies dans les trous ---
day_range = {}
for pair in ['BTC-EUR','ETH-EUR','SOL-EUR']:
    for d in range(8, 12):
        a = datetime(2026,10,d,0,0,tzinfo=TZ).astimezone(timezone.utc)
        b = min(datetime(2026,10,d+1,0,0,tzinfo=TZ).astimezone(timezone.utc), NOW)
        ev = series(pair, a, b, 'mid')
        hi = max(e[2] for e in ev); lo = min(e[1] for e in ev)
        day_range[(pair, d)] = dict(hi=hi, lo=lo, pct=round((hi-lo)/lo*100, 3), partiel=(b == NOW),
                                    part_bougie=round(100*sum(e[3]=='bougie' for e in ev)/len(ev),1))
for r in rows:
    dr = day_range[(r['pair'], r['open_ts'].astimezone(TZ).day)]
    r['day_range_pct'] = dr['pct']; r['target_share_of_day_range_pct'] = round(r['target_pct']/dr['pct']*100, 1)

# --- briefs Research (lignes chiffrées) ---
brief_rows = []
RB = ROOT/'state/research_briefs'
for f in sorted(RB.glob('2026-10-0[89]_*_last_research.json')):
    if f.name.endswith('_v2.json'): continue
    b = json.loads(f.read_text()); ideas = b.get('idees') or {}
    if not ideas:
        brief_rows.append(dict(brief=f.name, pair='—', note='aucune ligne chiffrée (pas de prix visé)')); continue
    t0 = p(b['prix'].get('releve_at') or b['briefed_at'])
    for pair, i in ideas.items():
        side = 'hausse' if 'hausse' in i['idee'] else 'baisse'
        entry, tgt, stp = float(i['prix_actuel']), float(i['prix_vise']), float(i['prix_arret'])
        dl = p(i['heure_limite'])
        ev = series(pair, t0, dl, 'bid' if side == 'hausse' else 'ask')
        if side == 'hausse':
            best = max(ev, key=lambda e: e[2]); bp = best[2]; mv = (bp-entry)/entry*100
            hit_t = next((e for e in ev if e[2] >= tgt), None); hit_s = next((e for e in ev if e[1] <= stp), None)
        else:
            best = min(ev, key=lambda e: e[1]); bp = best[1]; mv = (entry-bp)/entry*100
            hit_t = next((e for e in ev if e[1] <= tgt), None); hit_s = next((e for e in ev if e[2] >= stp), None)
        tp = abs(tgt-entry)/entry*100
        brief_rows.append(dict(brief=f.name, pair=pair, side=side, entry=entry, target=tgt, stop=stp,
            target_pct=round(tp,3), stop_pct=round(abs(stp-entry)/entry*100,3), start=loc(t0), deadline=loc(dl),
            best_price=bp, best_move_pct=round(mv,3), best_at=loc(best[0]), best_src=best[3],
            share_of_target_pct=round(mv/tp*100,1), target_reached=('oui '+loc(hit_t[0])) if hit_t else 'non',
            stop_touched=('oui '+loc(hit_s[0])) if hit_s else 'non',
            target_share_of_day_range_pct=round(tp/day_range[(pair, t0.astimezone(TZ).day)]['pct']*100,1)))
with open(OUT/'briefs_research.csv','w',newline='') as f:
    keys = list(dict.fromkeys(k for r in brief_rows for k in r))
    w = csv.DictWriter(f, fieldnames=keys); w.writeheader(); w.writerows(brief_rows)

# --- contexte : grille 5 min mid, 8 oct 00h (Bruxelles) → maintenant ---
G0 = datetime(2026,10,8,0,0,tzinfo=TZ).astimezone(timezone.utc)
ctx = {}
for pair in ['BTC-EUR','ETH-EUR','SOL-EUR']:
    cs = {c[0]: c for c in candles(pair, G0, NOW)}
    tk = [x for x in ticks.get(pair, []) if p(x['ts']) >= G0]
    buckets = {}
    for x in tk:
        t = p(x['ts']); b0 = t.replace(second=0, microsecond=0) - timedelta(minutes=t.minute % 5)
        buckets.setdefault(b0, []).append((t, float(x['mid'])))
    bars, t = [], G0
    while t + timedelta(minutes=5) <= NOW:
        b = buckets.get(t, [])
        times = [t] + [u for u, _ in b] + [t + timedelta(minutes=5)]
        covered = b and all((times[i+1] - times[i]).total_seconds() <= GAP for i in range(len(times)-1))
        if covered: bars.append((t, b[0][1], min(v for _, v in b), max(v for _, v in b), 'tick'))
        elif t in cs: c = cs[t]; bars.append((t, c[3], c[1], c[2], 'bougie'))
        t += timedelta(minutes=5)
    res = {'n_barres': len(bars), 'part_bougies_pct': round(100*sum(b[4]=='bougie' for b in bars)/len(bars), 1)}
    for H in (6, 24):
        up, dn = [], []
        for i, (t0, o, *_r) in enumerate(bars):
            if t0 + timedelta(hours=H) > bars[-1][0] + timedelta(minutes=5): break
            w = [b for b in bars[i:i+H*12] if b[0] < t0 + timedelta(hours=H)]
            up.append((max(b[3] for b in w) - o) / o * 100); dn.append((o - min(b[2] for b in w)) / o * 100)
        res[f'{H}h'] = {'n_entrees': len(up), 'mediane_hausse_pct': round(st.median(up), 3), 'mediane_baisse_pct': round(st.median(dn), 3)}
    ctx[pair] = res

rows.sort(key=lambda r: (r['retro'], r['close_ts']))
cols = ['dec','pair','side','exit_type','retro','entry','target','stop','target_pct','stop_pct','open_ts','close_ts','hours_open',
        'best_price','best_move_pct','best_at','best_src','share_of_target_pct','day_range_pct','target_share_of_day_range_pct','actual']
with open(OUT/'ecart_cible.csv', 'w', newline='') as f:
    w = csv.writer(f); w.writerow(cols)
    for r in rows: w.writerow([loc(r[c]) if isinstance(r[c], datetime) else r[c] for c in cols])
main = [r for r in rows if not r['retro']]
summ = {'n': len(main), 'moy_ecart_cible_pct': round(st.mean(r['target_pct'] for r in main), 3),
  'moy_ecart_arret_pct': round(st.mean(r['stop_pct'] for r in main), 3),
  'moy_meilleur_mouvement_pct': round(st.mean(r['best_move_pct'] for r in main), 3),
  'moy_part_cible_pct': round(st.mean(r['share_of_target_pct'] for r in main), 1),
  'n_50pct': sum(r['share_of_target_pct'] >= 50 for r in main), 'n_75pct': sum(r['share_of_target_pct'] >= 75 for r in main),
  'mediane_heures': round(st.median(r['hours_open'] for r in main), 2), 'moy_cible_sur_plage_jour_pct': round(st.mean(r['target_share_of_day_range_pct'] for r in main),1), 'plages_jour': {f'{k[0]} {k[1]}/10': v for k, v in day_range.items()}, 'briefs': brief_rows, 'contexte': ctx, 'calcul': loc(NOW)}
json.dump(summ, open(OUT/'totaux.json','w'), ensure_ascii=False, indent=1)
print(json.dumps(summ, ensure_ascii=False, indent=1))
