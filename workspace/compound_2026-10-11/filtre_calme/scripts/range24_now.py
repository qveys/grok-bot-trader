"""Plage 24 h actuelle (contexte) : 24 dernières bougies 1 h fermées Coinbase, / dernier prix (relevé 30 s)."""
import json, urllib.request, glob
from datetime import datetime, timezone, timedelta
now = datetime.now(timezone.utc); end = now.replace(minute=0, second=0, microsecond=0)
out = {}
last = {}
for l in open(sorted(glob.glob('/workspace/predict-market-bot/state/price_ticks/2026-*.jsonl'))[-1]):
    d = json.loads(l); last[d['pair']] = (d['ts'], d['mid'])
for pair in ['BTC-EUR', 'ETH-EUR', 'SOL-EUR']:
    s = end - timedelta(hours=24)
    url = f"https://api.exchange.coinbase.com/products/{pair}/candles?granularity=3600&start={s:%Y-%m-%dT%H:%M:%SZ}&end={end:%Y-%m-%dT%H:%M:%SZ}"
    c = json.loads(urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent': 'pm-compound-readonly'}), timeout=20).read())
    c = [r for r in c if datetime.fromtimestamp(r[0], timezone.utc) < end][:24]
    hi, lo = max(r[2] for r in c), min(r[1] for r in c); px = last[pair][1]
    out[pair] = dict(n_bougies=len(c), haut=hi, bas=lo, prix=px, prix_ts=last[pair][0], plage_pct=round((hi - lo) / px * 100, 3),
                     de=(s.astimezone().strftime('%d/%m %Hh%M')), a=end.astimezone().strftime('%d/%m %Hh%M'))
json.dump(out, open('range24_now.json', 'w'), indent=1); print(json.dumps(out, indent=1))
