import json,glob,os
for f in sorted(glob.glob('out/*.json')):
    try: d=json.load(open(f))
    except Exception as e: print(f,'BAD',open(f).read()[:200]); continue
    if d.get('status')!='ok': print(f,'STATUS',str(d)[:300]); continue
    fm=d.get('fill_model') or {}
    r=fm.get('result') or {}
    ss=fm.get('seed_spread')
    t=r.get('trades',d['trades']); ret=r.get('total_return_pct',d['total_return_pct']); dd=r.get('max_drawdown_pct',d['max_drawdown_pct']); wr=r.get('win_rate_pct',d['win_rate_pct']); pf=r.get('profit_factor',d['profit_factor'])
    extra=''
    if fm.get('mode')=='touch': extra=f" filled {r.get('entry_orders_filled')}/{r.get('entry_orders_placed')} tpmaker {r.get('exits_maker_tp')}"
    if ss: extra+=' spread '+json.dumps({k:ss[k] for k in ss if k in ('worst','median','best','worst_return_pct','median_return_pct','best_return_pct')})[:200]
    print(f"{os.path.basename(f)[:-5]:28s} per {d['period'][0][:10]}..{d['period'][1][:10]} trades {t:3d} ret {ret:7.2f}% dd {dd:6.2f}% wr {wr} pf {pf} bh {d['buy_hold_return_pct']} costs {d['costs']['profile']} exit {d['entries']['exit_hour']}/{d['entries']['max_bars']}{extra}")
