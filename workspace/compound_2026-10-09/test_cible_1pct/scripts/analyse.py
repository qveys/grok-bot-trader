import pandas as pd, numpy as np, warnings; warnings.filterwarnings('ignore')
SETS=['1/1','1.5/1.5','1.5/1','2/1','2.25/1.5','2.25/1','2/1.5','1/1.5']
def lvl(s):
    tp,sl=map(float,s.split('/')); r=tp/sl
    return '+'.join([n for n,t in (('P',1),('E',1.5),('R',2)) if r>=t-1e-9]) or '—'
def fmt(s): return s.replace('.0','') 
g=[]
for m in ('main','touch','tpfirst'):
    x=pd.read_csv(f'own_sim/grid_{m}.csv'); x['check']='own_'+m; g.append(x)
o=pd.concat(g); o['set']=(o.tp.map('{:g}'.format)+'/'+o.sl.map('{:g}'.format))
o['dd_cap']=o.dd_tool*0.05
t=pd.read_csv('tool_results.csv')
L=[]
def md(df): return df.to_markdown(index=False)
# A. baseline
for d in ('long','short'):
    a=o[(o.check=='own_main')&(o.rule=='daily15h')&(o.dir==d)&(o.cost=='taker014')&(o.set.isin(SETS[:5]))]
    a=a.assign(niveau=a.set.map(lvl))[['pair','set','niveau','n','net_pct','win','h1','h2','dd_cap']]
    mk=o[(o.check=='own_main')&(o.rule=='daily15h')&(o.dir==d)&(o.cost=='maker0')].set_index(['pair','set']).net_pct.rename('net_maker0')
    a=a.join(mk,on=['pair','set']); a['set']=pd.Categorical(a.set,SETS); a=a.sort_values(['pair','set'])
    L.append(f"### A{'1' if d=='long' else '2'}. Témoin neutre : entrée chaque jour 15h Bruxelles, {'hausse' if d=='long' else 'baisse'} — achat immédiat 0,14 %/côté (net_maker0 = 0 % frais)\n\n"+md(a.round(2)))
# B. team signals immediate (tool hausse + own mirrors baisse + tool sell_rebuy)
b=t[(t.cost=='immediat0.14')&(t.set.isin(SETS[:6]))].copy()
b['set']=pd.Categorical(b.set,SETS); b=b.sort_values(['rule','pair','set'])
mk=t[t.cost=='maker0'].set_index(['rule','pair','set']).net.rename('net_maker0')
tc=t[t.cost=='maker+touch'].set_index(['rule','pair','set']).net.rename('net_maker_touch')
mx=t[t.cost=='mixte(cible 0%)'].set_index(['rule','pair','set']).net.rename('net_mixte')
b['set']=b.set.astype(str); b=b.join(mk,on=['rule','pair','set']).join(tc,on=['rule','pair','set']).join(mx,on=['rule','pair','set'])
b['niveau']=b.set.map(lvl)
L.append("### B1. Signaux de l'équipe, outil backtest.sh (15–17h jours ouvrés, sans 22h, sécurité 48 h) — achat immédiat 0,14 %/côté\n(baisse = sell_rebuy, résultat en % de pièces vs garder ; net_mixte = vente/rachat visé à 0 %, rachat de sécurité 0,14 %)\n\n"+md(b[['rule','pair','set','niveau','n','net','win','h1','h2','dd_cap','verdict','net_maker0','net_maker_touch','net_mixte']].round(2)))
c=o[(o.check=='own_main')&(~o.rule.str.startswith('daily'))&(o.cost=='taker014')&(o.set.isin(SETS[:6]))].copy()
c['set']=pd.Categorical(c.set,SETS); c=c.sort_values(['rule','pair','set']); c['set']=c.set.astype(str); c['niveau']=c.set.map(lvl)
mk=o[(o.check=='own_main')&(o.cost=='maker0')].set_index(['rule','dir','pair','set']).net_pct.rename('net_maker0')
c=c.join(mk,on=['rule','dir','pair','set'])
L.append("### B2. Mêmes idées, recalcul indépendant (own_sim.py, ré-entrée permise dès la sortie) — achat immédiat 0,14 %/côté\n\n"+md(c[['rule','dir','pair','set','niveau','n','net_pct','win','h1','h2','dd_cap','net_maker0']].round(2)))
# C. 1/1 vs others: head-to-head counts across every (source, rule, pair, cost) cell
cells=[]
for (chk,rule,d,p,cost),x in o.groupby(['check','rule','dir','pair','cost']):
    v=x.set_index('set').net_pct; cells.append(dict(src=chk,rule=rule,pair=p,cost=cost,**{s:v.get(s) for s in SETS}))
for (rule,p,cost),x in t.groupby(['rule','pair','cost']):
    v=x.set_index('set').net; cells.append(dict(src='tool',rule=rule,pair=p,cost=cost,**{s:v.get(s) for s in SETS}))
C=pd.DataFrame(cells); C.to_csv('head_to_head_cells.csv',index=False)
rows=[]
for grp,sub in [('tous frais',C),('achat immédiat 0,14 %',C[C.cost.isin(['taker014','immediat0.14'])]),('0 % frais',C[C.cost.isin(['maker0'])])]:
    for s in SETS[1:6]:
        sub2=sub.dropna(subset=['1/1',s]); rows.append(dict(groupe=grp,contre=s,cases=len(sub2),**{'1/1 gagne':int((sub2['1/1']>sub2[s]).sum())},**{'1/1 >0':int((sub2['1/1']>0).sum())}))
L.append("### C. Duel 1/1 contre chaque réglage actuel (toutes les cases : paire × règle × source × vérif)\n\n"+md(pd.DataFrame(rows)))
# D. 1/1 team-rule verdict (immediate fees, both implementations)
rows=[]
for _,r in b[b.set=='1/1'].iterrows():
    ok=r.net>0 and r.n>=20 and (r.h1 or 0)>0 and (r.h2 or 0)>0 and r.dd_cap>-8
    rows.append(dict(source='outil',regle=r.rule,paire=r.pair,n=r.n,net=r.net,h1=r.h1,h2=r.h2,dd_cap=r.dd_cap,passe='oui' if ok else 'non'))
for _,r in o[(o.check=='own_main')&(o.set=='1/1')&(o.cost=='taker014')].iterrows():
    ok=r.net_pct>0 and r.n>=20 and r.h1>0 and r.h2>0 and r.dd_cap>-8
    rows.append(dict(source='own',regle=f'{r.rule}/{r.dir}',paire=r.pair,n=r.n,net=r.net_pct,h1=r.h1,h2=r.h2,dd_cap=round(r.dd_cap,2),passe='oui' if ok else 'non'))
D=pd.DataFrame(rows); L.append(f"### D. Règle d'équipe pour 1/1, achat immédiat 0,14 % : {int((D.passe=='oui').sum())} cas sur {len(D)} passent\n\n"+md(D.round(2)))
# E. stability of 1/1 vs best current per check (immediate)
rows=[]
for chk in ['own_main','own_touch','own_tpfirst']:
    x=o[(o.check==chk)&(o.cost=='taker014')]
    for s in ['1/1','1.5/1.5','1.5/1','2/1','2.25/1.5']:
        y=x[x.set==s]; rows.append(dict(verif=chk,reglage=s,niveau=lvl(s),cases=len(y),cases_gain=int((y.net_pct>0).sum()),moyenne_net=round(y.net_pct.mean(),2),
            cases_2_moities=int(((y.h1>0)&(y.h2>0)).sum()),trimestres_gagnants_moy=round(y.q_pos.mean(),2)))
for cst,lab in [('immediat0.14','outil_immediat'),('maker+touch','outil_maker_touch'),('maker0','outil_maker0')]:
    x=t[t.cost==cst]
    for s in ['1/1','1.5/1.5','1.5/1','2/1','2.25/1.5']:
        y=x[x.set==s]; rows.append(dict(verif=lab,reglage=s,niveau=lvl(s),cases=len(y),cases_gain=int((y.net>0).sum()),moyenne_net=round(y.net.mean(),2),
            cases_2_moities=int(((y.h1>0)&(y.h2>0)).sum()) if y.h1.notna().all() else None,trimestres_gagnants_moy=None))
L.append("### E. Vérifications répétées (moyenne sur paires × règles)\n\n"+md(pd.DataFrame(rows)))
open('tables.md','w').write('\n\n'.join(L)+'\n')
print('\n\n'.join(L))
