import json,glob,datetime as dt,csv,urllib.request,time,os
B='/workspace/predict-market-bot/'
FEE=0.0005  # guardian/scripts/paper_fill.py FEE_REVOLUT, par côté
TZ=dt.timezone(dt.timedelta(hours=2))
pos={p.get('decision_id'):p for p in json.load(open(B+'guardian/state.json'))['positions']}
trades=[json.loads(l) for l in open(B+'state/trades_log.jsonl') if l.strip()]
ticks=[]
for f in sorted(glob.glob(B+'state/price_ticks/*.jsonl')):
    for l in open(f):
        try: r=json.loads(l)
        except: continue
        r['t']=dt.datetime.fromisoformat(r['ts']); ticks.append(r)
scans=[]
for l in open(B+'state/scan_history.jsonl'):
    try: r=json.loads(l)
    except: continue
    scans.append((dt.datetime.fromisoformat(r['scanned_at']),r.get('prices',{})))
CC='candles_cache_5m'; os.makedirs(CC,exist_ok=True)
def candles(pair,a,b):
    res=[]; st=int(a.timestamp())//300*300
    while st<b.timestamp():
        en=min(st+300*300,int(b.timestamp())//300*300+300)
        fn=f'{CC}/{pair}_{st}_{en}.json'
        if not os.path.exists(fn):
            u=f'https://api.exchange.coinbase.com/products/{pair}/candles?granularity=300&start={dt.datetime.fromtimestamp(st,dt.timezone.utc):%Y-%m-%dT%H:%M:%SZ}&end={dt.datetime.fromtimestamp(en,dt.timezone.utc):%Y-%m-%dT%H:%M:%SZ}'
            req=urllib.request.Request(u,headers={'User-Agent':'pm-compound'})
            open(fn,'w').write(urllib.request.urlopen(req,timeout=20).read().decode()); time.sleep(0.4)
        for c in json.load(open(fn)):
            t=dt.datetime.fromtimestamp(c[0],dt.timezone.utc)
            if t+dt.timedelta(seconds=300)>a and t<b: res.append(dict(t=t,low=c[1],high=c[2]))
        st=en
    return sorted({c['t']:c for c in res}.values(),key=lambda c:c['t'])
KR={}
for kp,pp in [('SOLEUR','SOL-EUR'),('ETHEUR','ETH-EUR')]:
    try:
        d=json.load(open(f'kraken_{kp}_5m.json'))['result']
        for kk,v in d.items():
            if kk!='last':
                for c in v: KR[(pp,int(c[0]))]=(float(c[3]),float(c[2]))
    except Exception: pass
IDS=['D-021','D-026','D-031b','D-036a','D-024b','D-028a']
def p(x): return x.astimezone(TZ)
def hm(x): return p(x).strftime('%d/%m %Hh%M:%S')
def dur(s): s=int(s); return f"{s//3600}h{(s%3600)//60:02d}"
out=[]
for d in IDS:
    P=pos[d]; sell=[t for t in trades if t.get('decision_id')==d and t['side']=='sell'][0]
    buy=[t for t in trades if t.get('linked_position_id')==P['id'] and t['side']=='buy'][0]
    t0=dt.datetime.fromisoformat(sell['ts'].replace('Z','+00:00')); t1=dt.datetime.fromisoformat(buy['ts'].replace('Z','+00:00'))
    sp=sell['price']; q=sell['qty']; sfee=sell['fee_eur']; amt=sell['amount_eur']
    w=[r for r in ticks if r['pair']==P['pair'] and t0<=r['t']<=t1]
    def side(r): return r['ask'] if r.get('ask') is not None else r['mid']
    lo=min(w,key=side); lo_mid=min(w,key=lambda r:r['mid'])
    hi=max(w,key=side)
    # tick at close
    near=min([r for r in ticks if r['pair']==P['pair']],key=lambda r:abs((r['t']-t1).total_seconds()))
    best=side(lo)
    def net(px): return (sp-px)*q - sfee - px*q*FEE
    g=net(best); gm=net(lo_mid['mid'])
    tgt=P['target_price']; stp=P['stop_price']
    frac=(sp-best)/(sp-tgt)*100
    def first(th):
        for r in w:
            if side(r)<=sp*(1-th): return r
    f05=first(0.005); f1=first(0.01)
    be=sp*(1-FEE)/(1+FEE)  # prix de rachat où gain net = 0
    fpos=next((r for r in w if side(r)<be),None)
    gaps=[]; ts=[r['t'] for r in w]
    for a,b in zip([t0]+ts,ts+[t1]):
        if (b-a).total_seconds()>90: gaps.append((a,b))
    gapsec=sum((b-a).total_seconds() for a,b in gaps)
    # scan_history low during gaps (binance spot, autre source)
    sl=[pr[P['pair']]['price_eur'] for ts_,pr in scans for a,b in gaps if a<ts_<b and P['pair'] in pr]
    cs=[c for a,b in gaps for c in candles(P['pair'],a,b)]
    manq=[];kfill=[]
    for a,b in gaps:
        have={c['t'] for c in cs}; t=dt.datetime.fromtimestamp(int(a.timestamp())//300*300,dt.timezone.utc)
        while t<b:
            if t not in have:
                kc=KR.get((P['pair'],int(t.timestamp())))
                if kc: cs.append(dict(t=t,low=kc[0],high=kc[1],src='kraken')); kfill.append(t)
                else: manq.append(t)
            t+=dt.timedelta(seconds=300)
    if cs:
        cl=min(cs,key=lambda c:c['low']); ch=max(cs,key=lambda c:c['high'])
        est_best=min(best,cl['low']); est_t=lo['t'] if best<=cl['low'] else cl['t']
        eg=net(est_best)
        c05=min([c['t'] for c in cs if c['low']<=sp*0.995],default=None); c1=min([c['t'] for c in cs if c['low']<=sp*0.99],default=None)
        est=dict(trous_bougies_5min=len(cs),trous_bas=cl['low'],trous_bas_heure=hm(cl['t']),trous_haut=ch['high'],trous_haut_heure=hm(ch['t']),
          trous_cible_touchee=cl['low']<=tgt,trous_arret_touche=ch['high']>=stp,
          est_meilleur_prix=est_best,est_meilleur_heure=hm(est_t),est_gain_max_net_eur=round(eg,4),est_gain_max_net_pct=round(100*eg/amt,3),
          est_chemin_vers_cible_pct=round((sp-est_best)/(sp-tgt)*100,1),
          trous_fav_0_5pct=hm(c05) if c05 else '',trous_fav_1pct=hm(c1) if c1 else '')
    else: est={}
    out.append(dict(decision=d,paire=P['pair'],montant_eur=round(amt,2),qty=q,
      vente_prix=sp,vente_heure=hm(t0),rachat_prix=buy['price'],rachat_heure=hm(t1),
      rachat_tick_ask=side(near),rachat_tick_mid=near['mid'],
      resultat_eur=P['realized_pnl_eur'],resultat_pct=P['realized_pnl_pct'],raison=P['close_reason'],
      cible=tgt,arret=stp,
      meilleur_ask=best,meilleur_ask_heure=hm(lo['t']),meilleur_ask_apres=dur((lo['t']-t0).total_seconds()),
      meilleur_mid=lo_mid['mid'],meilleur_mid_heure=hm(lo_mid['t']),
      gain_max_net_eur=round(g,4),gain_max_net_pct=round(100*g/amt,3),
      gain_max_net_eur_mid=round(gm,4),gain_max_net_pct_mid=round(100*gm/amt,3),
      chemin_vers_cible_pct=round(frac,1),
      plus_haut_ask=side(hi),plus_haut_heure=hm(hi['t']),
      seuil_zero_frais=round(be,4),
      en_gain_net_apres=dur((fpos['t']-t0).total_seconds()) if fpos else '',
      fav_0_5pct=bool(f05),fav_0_5pct_apres=dur((f05['t']-t0).total_seconds()) if f05 else '',
      fav_1pct=bool(f1),fav_1pct_apres=dur((f1['t']-t0).total_seconds()) if f1 else '',
      ticks=len(w),trous_sans_ticks=dur(gapsec),trous=' ; '.join(f"{p(a):%d/%m %Hh%M}-{p(b):%Hh%M}" for a,b in gaps),
      scan_min_dans_trous=min(sl) if sl else '',statut_meilleur=('incomplet' if manq else ('complet (trous comblés bougies 5 min Coinbase + Kraken)' if kfill else 'complet (trous comblés bougies 5 min Coinbase)') if gaps else 'complet'),creneaux_5min_kraken=' '.join(f'{p(t):%d/%m %Hh%M}' for t in kfill),creneaux_5min_sans_prix=' '.join(f'{p(t):%d/%m %Hh%M}' for t in manq),**est))
k=[];[k.append(x) for o in out for x in o if x not in k]
with open('/workspace/compound_2026-10-10/meilleur_gain_ventes/meilleur_gain_ventes.csv','w',newline='') as f:
    wr=csv.DictWriter(f,k,delimiter=';',restval=''); wr.writeheader(); wr.writerows(out)
for o in out: print(json.dumps(o,ensure_ascii=False))
