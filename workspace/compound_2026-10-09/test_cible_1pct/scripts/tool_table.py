import json, glob, os, re, pandas as pd
rows=[]
for f in sorted(glob.glob('tool_json/*.json')):
    d=json.load(open(f)); b=os.path.basename(f)[:-5]
    v=d.get('verdict_equipe') or {}
    rd=d['run_dir']
    for fn in ('run_card.json','summary.json'):
        try:
            vv=json.load(open(os.path.join(rd,fn))).get('verdict_equipe')
            if vv: v=vv; break
        except Exception: pass
    if 'sell_rebuy' in b:
        m=re.match(r'(\w+)_sell_rebuy_tm(\d+)_dip([\d.]+)_stop([\d.]+)_(\w+)',b)
        p,tm,tp,sl,c=m.groups(); rule=f'sell_rebuy_ma{tm}'; cost={'revolutx':'mixte(cible 0%)','alltaker':'immediat0.14'}[c]
        rows.append(dict(pair=p,rule=rule,dir='baisse',set=f'{float(tp):g}/{float(sl):g}',cost=cost,net=d['coin_gain_vs_hold_pct'],n=d['cycles'],win=d['win_rate_pct'],
             h1=v.get('moitie_1_pct'),h2=v.get('moitie_2_pct'),dd_cap=v.get('pire_baisse_capital_pct'),verdict=v.get('test_du_passe_reussi'),run=d['run_dir'].split('/')[-1]))
    else:
        m=re.match(r'(\w+?)_(team_\w+?)_tp([\d.]+)_sl([\d.]+)_([\w-]+)_fill(\w+)',b)
        p,rule,tp,sl,c,fl=m.groups()
        if fl=='touch':
            r=d['fill_model']['result']; net,n,win=r['total_return_pct'],r['trades'],r['win_rate_pct']; cost='maker+touch'
        else:
            net,n,win=d['total_return_pct'],d['trades'],d['win_rate_pct']; cost={'revolutx-maker':'maker0','revolutx':'immediat0.14'}[c]
        rows.append(dict(pair=p,rule=rule,dir='hausse',set=f'{float(tp):g}/{float(sl):g}',cost=cost,net=net,n=n,win=win,h1=v.get('moitie_1_pct'),h2=v.get('moitie_2_pct'),
             dd_cap=v.get('pire_baisse_capital_pct'),verdict=v.get('test_du_passe_reussi'),run=d['run_dir'].split('/')[-1]))
df=pd.DataFrame(rows); df.to_csv('tool_results.csv',index=False)
pd.set_option('display.width',250); pd.set_option('display.max_rows',1000)
w=df.pivot_table(index=['rule','pair','set'],columns='cost',values='net',aggfunc='first')
x=df[df.cost.isin(['immediat0.14'])].set_index(['rule','pair','set'])[['n','win','h1','h2','dd_cap','verdict']].add_prefix('imm_')
print(w.join(x).round(2).to_string())
print('any verdict oui:', df[df.verdict=='oui'][['pair','rule','set','cost','net','n']].to_string())
