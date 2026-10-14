import json,urllib.request,csv,datetime as dt,sys
def kl(sym):
    st=int(dt.datetime(2025,9,15,tzinfo=dt.timezone.utc).timestamp()*1000); out=[]
    while True:
        b=json.load(urllib.request.urlopen(f'https://api.binance.com/api/v3/klines?symbol={sym}&interval=1h&startTime={st}&limit=1000',timeout=30))
        out+=b
        if len(b)<1000: break
        st=b[-1][0]+3600000
    return {dt.datetime.fromtimestamp(x[0]/1000,dt.timezone.utc).strftime('%Y-%m-%d %H:%M:%S'):float(x[4]) for x in out}
cache={}
for name,f in [('reb_ETH_full_touch','ETHEUR'),('reb_ETH_full_taker','ETHEUR'),('reb_SOL_full_touch','SOLEUR'),('reb_SOL_full_taker','SOLEUR'),('reb_ETH_full_all','ETHEUR'),('reb_SOL_full_all','SOLEUR')]:
    if f not in cache: cache[f]=kl(f)
    c=cache[f]; keys=sorted(c); idx={k:i for i,k in enumerate(keys)}; closes=[c[k] for k in keys]
    rd=json.load(open(f'out/{name}.json'))['run_dir']
    import os
    tf=f'{rd}/artifacts/fill_touch_trades.csv' if os.path.exists(f'{rd}/artifacts/fill_touch_trades.csv') else f'{rd}/artifacts/trades.csv'
    rows=list(csv.DictReader(open(tf)))
    if 'net_pct' not in rows[0]:
        print(name,'cols',list(rows[0].keys())); continue
    keep=[]
    for r in rows:
        e=r['entry'][:19]
        i=idx.get(e)
        if i is None or i<201: print(' missing',e); continue
        sig=i-1; sma=sum(closes[sig-199:sig+1])/200
        if closes[sig]>sma: keep.append(r)
    eq=1;pk=1;dd=0
    for r in keep:
        eq*=1+float(r['net_pct'])/100; pk=max(pk,eq); dd=min(dd,eq/pk-1)
    print(f"{name}: all {len(rows)} trades -> above SMA200: {len(keep)} trades, ret {(eq-1)*100:.2f}%, dd {dd*100:.2f}%, wins {sum(float(r['net_pct'])>0 for r in keep)}")
