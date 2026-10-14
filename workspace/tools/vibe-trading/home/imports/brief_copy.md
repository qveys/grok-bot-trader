# Brief — décisions chart / chandeliers : ce que dit la littérature

*Note FR-friendly. Sources vérifiées (pas de papiers inventés). Focus : process pro vs retail, checklists, TA après coûts, framework setup→confirm→risque.*

---

## Findings (bullets)

- **Pros ≠ lecture de bougies seule.** Les surveys sur professionnels (FX, gérants) montrent que la TA est **très utilisée**, surtout à **horizon court** (jours/semaines), mais presque toujours **combinée** aux fondamentaux / flux et à un cadre de risque — pas comme oracle isolé (Taylor & Allen 1992 ; Menkhoff & Taylor 2007 ; Menkhoff 2010).
- **Retail vs pro = process, pas “meilleur œil”.** Chez les pros/praticiens disciplinés : régime (trend/range) → zone de décision → modèle (continuation vs fade) → **invalidation écrite avant l’ordre** → taille calculée depuis un budget de risque → revue d’adhésion aux règles. Le retail typique : entrée d’abord, justification après, stop déplacé, taille émotionnelle (synthèse praticienne cohérente avec la lit. sur discipline / risk-first).
- **Chandeliers purs : peu de valeur démontrée.** Marshall, Young & Rose (2006) — premier test robuste (bootstrap OHLC) sur titres DJIA — concluent que les stratégies candlestick **ne créent pas de valeur** vs buy-and-hold ; compatible avec l’efficience informationnelle sur ce marché.
- **TA “règles techniques” après coûts : souvent fragile.** Park & Irwin (2007) : revue large — résultats mixtes/positifs historiques, mais **data snooping**, sélection ex post, et **coûts/risque** mal traités. Bajgrowicz & Scaillet (2012) : après FDR + coûts de transaction réalistes, les profits apparents des règles techniques (univers type STW) **disparaissent** ; pas de persistance ex ante fiable.
- **Crypto : plus favorable *en apparence*, mais coûts + OOS comptent.** Hudson & Urquhart (2019) : ~15k règles sur BTC/ETH/LTC/XRP — prédictibilité/profitabilité significative in-sample, break-even costs souvent > coûts typiques (~50 bps BTC cité), **mais BTC sans prédictibilité out-of-sample**. Anghel (2022) : après coûts, **moins** de règles rentables ; le quotidien tient mieux que l’intraday 1-min ; bulles/coûts modifient les odds.
- **Framework consensus (académique + praticien) pour “locker” une décision chart :**  
  **Setup** (contexte + niveau + pattern nommé) → **Confirmation** (close, break, retest, follow-through — bougie *fermée*) → **Risque défini avant le clic** (invalidation = stop, taille = risque$ / distance stop, R:R / coûts nets OK) → sinon **no-trade**. Les bougies = timing / hypothèse locale, pas le trade entier.

---

## Sources nommées (3–6+ vérifiées)

1. **Taylor, M. P. & Allen, H. (1992).** *The use of technical analysis in the foreign exchange market.* *Journal of International Money and Finance*, 11(3), 304–314.  
   https://doi.org/10.1016/0261-5606(92)90048-4

2. **Menkhoff, L. & Taylor, M. P. (2007).** *The Obstinate Passion of Foreign Exchange Professionals: Technical Analysis.* *Journal of Economic Literature*, 45(4), 936–972.  
   https://www.aeaweb.org/articles?id=10.1257/jel.45.4.936  
   (Working paper : https://warwick.ac.uk/fac/soc/economics/research/workingpapers/2006/twerp_769.pdf)

3. **Menkhoff, L. (2010).** *The use of technical analysis by fund managers: International evidence.* *Journal of Banking & Finance*, 34(11), 2573–2586.  
   https://doi.org/10.1016/j.jbankfin.2010.04.014  
   (PDF open : https://www.econstor.eu/bitstream/10419/38748/1/625491165.pdf)

4. **Park, C.-H. & Irwin, S. H. (2007).** *What Do We Know About The Profitability Of Technical Analysis?* *Journal of Economic Surveys*, 21(4), 786–826.  
   https://doi.org/10.1111/j.1467-6419.2007.00519.x

5. **Marshall, B. R., Young, M. R. & Rose, L. C. (2006).** *Candlestick technical trading strategies: Can they create value for investors?* *Journal of Banking & Finance*, 30(8), 2303–2323.  
   https://doi.org/10.1016/j.jbankfin.2005.08.001

6. **Bajgrowicz, P. & Scaillet, O. (2012).** *Technical trading revisited: False discoveries, persistence tests, and transaction costs.* *Journal of Financial Economics*, 106(3), 473–491.  
   https://doi.org/10.1016/j.jfineco.2012.06.001  
   (PDF course mirror : https://www.phd-finance.uzh.ch/static/Courses/Downloads/BBLS_spring08_Bajgrowicz.pdf)

7. **Hudson, R. & Urquhart, A. (2019/2021).** *Technical trading and cryptocurrencies.* *Annals of Operations Research*.  
   https://link.springer.com/article/10.1007/s10479-019-03357-1  
   https://doi.org/10.1007/s10479-019-03357-1

8. **Anghel, D.-G. (2022).** *Technical analysis in cryptocurrency markets: Do transaction costs and bubbles matter?* *Journal of International Financial Markets, Institutions and Money*, 79.  
   https://doi.org/10.1016/j.intfin.2022.101584  
   https://www.sciencedirect.com/science/article/abs/pii/S1042443122000816

*Praticien (pas peer-review, utile pour checklists) : protocoles pré-trade type “setup nommé / invalidation / size / no-trade” — ex. Execution Protocol checklists (traderssecondbrain.com), pre-trade risk checklists.*

---

## Takeaway pratique (5 lignes) — retail crypto spot, bots team : paper vs 1-live/jour

1. **Ne laissez pas un chandelier “décider”** : exigez un **setup nommé** (régime + niveau + pattern) + **confirmation sur bougie fermée** + **invalidation prix écrite** avant toute exposition live.  
2. **Risque avant le clic** : taille = budget de perte max / distance stop ; si R:R net (fees + slippage) < seuil écrit → skip.  
3. **Quota 1 live/jour** = garde-fou retail aligné lit. (coûts + data-snooping + OOS fragile sur BTC) : le live doit passer **toutes** les gates ; le surplus reste **paper** pour mesurer expectancy.  
4. **Bots** : coder les gates (setup ID, confirm, stop, size, max 1 live, daily loss kill-switch) — journaliser *adhésion process*, pas seulement PnL.  
5. **Calibration** : paper jusqu’à N trades avec expectancy/coûts mesurés ; promote 1 live seulement si règles stables hors sample (surtout BTC : liter. OOS faible).

---

*Fichier généré pour recherche interne. Citations tirées de WebSearch/WebFetch ; titres/années/DOI vérifiés sur résumés éditeurs.*
