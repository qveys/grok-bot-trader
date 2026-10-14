# Pair selection for US equity open window (Revolut X spot PAPER)

**Trader:** Quentin Veys (Belgium)  
**Venue:** Revolut X · EUR quote · spot PAPER  
**Window:** weekdays ~15:00–17:00 Europe/Brussels (US cash open overlap)  
**Current whitelist:** ETH-EUR + SOL-EUR  
**Question:** Add BTC-EUR? Keep / drop / replace?  
**Brief date:** 2026-10-07 (Europe/Brussels)

---

## Bottom line (ranked, max 3)

| Rank | Pair | Action | Why |
|------|------|--------|-----|
| **1** | **BTC-EUR** | **ADD (primary)** | Highest spot volume & deepest books; US-open hour is the documented volume/volatility peak; tightest spreads → best chance that a 2h move survives fees |
| **2** | **ETH-EUR** | **KEEP** | Mid vol + still major liquidity; US-hours variance share rose like BTC; good second name without SOL’s thinner book |
| **3** | **SOL-EUR** | **KEEP only as optional 3rd / DROP if capped at 2** | Highest short-horizon vol (clears fee hurdle most often) but ~1/10 BTC spot turnover and thinning depth → spread/slippage risk on retail CLOB |

**If only 2 pairs:** **BTC-EUR + ETH-EUR** (add BTC, drop SOL).  
**If 3 pairs allowed:** BTC-EUR + ETH-EUR + SOL-EUR, with attention/capital priority BTC → ETH → SOL.  
**Do not** expand into memecoins / thin alts for this sparse routine. Gold/XAU not a Revolut X spot product; PAXG availability for EU/BE is uncertain — skip.

---

## 1) Volume & useful vol in the US open window

### Time mapping (critical)

- US cash open: **09:30 ET**.
- Under **CEST (UTC+2)** (Belgium now): 09:30 ET ≈ **15:30 Brussels**; Quentin’s **15:00–17:00** ≈ **13:00–15:00 UTC**.
- Under **CET (UTC+1)** winter: 15:00–17:00 Brussels ≈ **14:00–16:00 UTC**.

Both map onto the London/NY overlap / US-open cluster.

### BTC hourly volume & moves (exchange aggregate)

Maketo (Binance + Bitstamp + Coinbase + Kraken + OKX, **9 Jul 2026 – 7 Oct 2026**, last 91 days):

| Hour UTC | Share of day | vs avg hour | Avg hourly move |
|----------|--------------|-------------|-----------------|
| 13:00 | 7.4% | 1.8× | 0.328% |
| **14:00** | **8.4%** | **2.0×** | **0.441%** |
| 15:00 | 7.3% | 1.8× | 0.364% |
| 16:00 | 5.2% | 1.3× | 0.204% |

→ Busiest BTC hour = **14:00 UTC**; Quentin’s Brussels window covers the top volume/move hours in both DST regimes. Weekends ~41% quieter than weekdays (same source, long history).

### US-hours volatility concentration (BTC + peers)

Leap Digital summary of Kraken hourly study (2016–2025):

- **13:00–21:59 UTC** = **50.6%** of BTC daily realized variance in 2022–2025 (vs 38.4% in 2016–2018), despite being only 37.5% of the clock.
- Peak vol hour **moves with US DST** (14:00 UTC in DST → 15:00 UTC in standard time) and **falls on NYSE holidays**.
- Same US-hours concentration trend in **ETH, SOL, XRP**, etc. (ETH US-hours share 41.8% → 48.2% across sample periods).

GrandAlgo volume commentary (aligned): London/NY overlap **UTC 13:00–17:00** is the high-liquidity band; US equity open called out as the largest daily crypto volume spike for BTC/ETH.

### Cross-asset: who has volume vs who has range

**Spot turnover (illustrative live snapshot, CoinClass):** BTC ~$26.7B · ETH ~$11.0B · SOL ~$2.4B (24h) — order **BTC ≫ ETH ≫ SOL**.

**Intraday usefulness (Investisseur 2.0 observatory, CoinGecko OHLCV, 9 May–5 Oct 2026, 150 days):**

| Asset | Avg daily |move| | Avg intraday range |
|-------|------------------|--------------------|
| BTC | 1.40% | 2.81% |
| ETH | 1.83% | 3.67% |
| SOL | 2.20% | 4.39% |

→ SOL ≈ **1.6×** BTC daily move; ETH in between.

**Options/IV snapshot (Derivasys, 6 Oct 2026):** 1W ATM IV SOL 50.08% · ETH 39.26% · BTC 31.64%; 30d ATM IV similar ranking (SOL 51.6% · ETH 46.6% · BTC 34.3%).

**Liquidity depth caveat (KuCoin citing CoinGecko, Q3 2026):** ETH median market depth only **~35–45% of BTC** (was ≥60% YoY earlier); SOL depth also contracted (e.g. ~$28M → ~$20M within 2% of mid).

**Correlations (same 150d observatory):** BTC/ETH 0.88 · BTC/SOL 0.84 · ETH/SOL 0.83 — three names ≈ one risk bet for a 2h session. Morgan Stanley / E*TRADE (as of Apr 2026): longer-sample BTC–ETH corr ~0.78, BTC–SOL ~0.72; SOL ~86% more volatile than BTC since end-2019, ETH ~33% more.

### Answer to Q1

In the US open window, **BTC typically shows the highest volume and cleanest liquidity**; **SOL typically shows the highest useful short-horizon volatility**; **ETH sits in the middle on both**. For *net* spot gains after fees/spreads, volume+tight spreads matter as much as raw range — so BTC and ETH edge SOL for a sparse retail CLOB routine, with SOL only if you explicitly want higher beta and size down.

---

## 2) Is ETH+SOL right, or should BTC replace/join?

**Join — do not stay on ETH+SOL alone.**

- Current set skips the deepest book and the best-documented US-open volume peak (**BTC**).
- ETH+SOL are highly correlated with each other and with BTC (~0.8+); dual-alt set does **not** diversify a 2h session.
- Relative to BTC, ETH is a fair “more vol, still liquid” complement; SOL is “most vol, least liquid of the three.”
- **Replace SOL with BTC if limited to 2 pairs.** Keep ETH. Only keep SOL as a third optional sleeve with smaller size.

---

## 3) Other Revolut-X-likely majors / warnings

**Revolut X facts (official / CMC):**

- Fees: **0% maker / 0.09% taker** (flat; round-trip taker ≈ **0.18%** before spread).
- Majors listed: **BTC, ETH, SOL, XRP** among 300+ tokens; API docs exemplify `ETH/EUR`, `BTC-USD`, etc. EUR pairs for majors are the natural fit for Quentin.
- Trading rules list min sizes for BTC, ETH, SOL, XRP, ADA, DOGE, etc.

**Worth considering (only if expanding beyond 2–3):**

- **XRP-EUR** — also shows US-hours variance concentration in the Kraken study; lower priority than BTC/ETH/SOL for this brief (less “equity-beta” narrative, still major liquidity vs alts). Not needed for a 2–3 pair sparse routine.

**Warn against:**

- **Memecoins / thin alts:** wider spreads, thin books, fee+slippage round-trips that routinely erase short-horizon edge (retail fee/spread literature; Schwab risk notes on memecoins). Bad fit for a ~2h after-cost mandate.
- **Native gold / XAU:** generally **not** on Revolut X (crypto CLOB).
- **PAXG (tokenized gold):** venue listings exist elsewhere; **EU/BE availability on Revolut X is uncertain** — do not plan the routine around it without a live pair check in-app.

**Fee hurdle reminder:** a taker round-trip needs roughly **>0.2–0.4%** favorable move (fees + typical major spread) before any “meaningful” net. That favors the US-open liquidity spike and majors over quiet hours / thin names.

---

## 4) Clear recommendation for sparse SuperGrok routine

1. **ADD BTC-EUR** as the primary pair for the 15:00–17:00 Brussels window.  
2. **KEEP ETH-EUR** as #2.  
3. **SOL-EUR:** keep only if allowing a 3rd pair and sizing smaller; **drop if the whitelist must stay at 2**.  
4. Cap at **2–3 pairs**; ignore memecoins/PAXG/XAU for this routine.  
5. Prefer limit/maker where practical (0% maker) to shrink the fee hurdle; still trade only in the documented high-volume hours.

**Ranked whitelist:** `BTC-EUR` > `ETH-EUR` > `SOL-EUR (optional)`.

---

## Sources (fetched / searched 2026-10-07)

1. Maketo — Bitcoin trading hours / hourly volume & moves (5 venues, 9 Jul–7 Oct 2026): https://maketo.com/bitcoin/market-hours  
2. Leap Digital — “Crypto never closes… Wall Street time” (Kraken hourly variance study summary, Sep 2026): https://leapdigitalinvestments.com.au/crypto-never-closes-but-bitcoin-ethereum-xrp-and-solana-now-move-on-wall-street-time/  
3. GrandAlgo — Crypto volume by hour / US open commentary: https://grandalgo.com/tools/crypto-volume  
4. Investisseur 2.0 crypto market observatory (BTC/ETH/SOL vol & corr, May–Oct 2026): https://investisseur2-0.com/en/resources/crypto-market-observatory  
5. Derivasys — BTC/ETH/SOL options vol report, 6 Oct 2026: https://www.derivasys.com/reports/major-coins/2026-10-06  
6. CoinClass — spot volume by coin snapshot: https://coinclass.com/volume  
7. KuCoin flash / CoinGecko depth — ETH depth ~35–45% of BTC (Q3 2026): https://www.kucoin.com/news/flash/eth-q3-price-surpasses-btc-but-liquidity-drops-to-40-of-bitcoin  
8. E*TRADE / Morgan Stanley Wealth — ETH vs BTC vs SOL vol & corr (Aug 2026): https://us.etrade.com/knowledge/library/cryptocurrency/portfolio-diversification  
9. Revolut X product page (0%/0.09% fees, 250–300+ tokens): https://www.revolut.com/revolut-x/  
10. Revolut X fees page: https://www.revolut.com/legal/crypto-exchange-fees/  
11. Revolut crypto exchange trading rules (min sizes BTC/ETH/SOL/XRP…): https://www.revolut.com/legal/crypto-exchange-trading-rules/  
12. CoinMarketCap — Revolut X exchange profile: https://coinmarketcap.com/exchanges/revolut-x/  
13. Revolut X API docs (pair examples BTC/USD, ETH/EUR): https://github.com/revolut-engineering/revolut-x-api  

*Educational research for PAPER trading pair selection — not investment advice.*
