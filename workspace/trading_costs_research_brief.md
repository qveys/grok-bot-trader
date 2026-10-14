# Research brief: Do transaction costs kill “many small winning trades”?
**For:** Quentin Veys (Belgium; crypto spot; MetaMask small live + Revolut paper)  
**Date:** 7 Oct 2026 (Europe/Brussels)  
**Scope:** Reputable academic / institutional sources only (no invented citations)

---

## Bottom line (clear yes/no)

**YES — the literature generally finds that trading costs (and related timing/adverse-selection costs) dominate small edges for frequent, small, retail-style trades.**  
Gross “many small wins” often look fine; **net of spreads, fees, slippage/gas, performance typically collapses**, especially for high turnover. Short-horizon scalping *can* work only under narrow conditions (proven structural edge + very low costs / maker rebates / institutional execution) — **not** typical retail MetaMask / high-turnover spot trading.

---

## Sources & findings (concrete numbers)

### 1) Trading costs erode returns — especially frequent small trades

- **Barber & Odean (2000), *Journal of Finance*** — “Trading Is Hazardous to Your Wealth”  
  - 66,465 US discount-broker households, 1991–1996.  
  - Average household turnover **~75%/year**; round-trip cost ≈ **3% commissions + 1% bid–ask** (~**4%** per round trip on average trade >$1k).  
  - Gross returns ≈ market; **net**: average household **16.4%** vs market **17.9%**; **most active traders 11.4%** vs **infrequent traders 18.5%**.  
  - Own-benchmark: trading itself cost ~**2%/year** vs buy-and-hold.  
  - Message: *frequency × cost*, not stock picking, drives underperformance.

- **Odean (1999), *American Economic Review*** — “Do Investors Trade Too Much?”  
  - Securities investors buy **underperform** those they sell — so trading fails to cover costs *even before* commissions/spreads.

- **Carhart (1997), *Journal of Finance*** — mutual funds  
  - Higher turnover hurts net returns; roughly **~0.95% lower return per 100% annual turnover** (implied round-trip trading cost ≈ **95 bp** per full turnover).

- **Novy-Marx & Velikov (2016), *Review of Financial Studies*** (NBER WP 20721) — “A Taxonomy of Anomalies and Their Trading Costs”  
  - Mid-turnover strategies: costs often **20–57 bp/month** (can exceed half of gross alpha).  
  - **Few strategies with >50% one-sided monthly turnover** remain significantly profitable after costs.  
  - “Transaction costs always reduce strategy profitability.”

### 2) Retail / high-turnover strategies underperform after costs

- **Barber, Lee, Liu & Odean** (Taiwan complete-market studies; e.g. “Just How Much Do Individual Investors Lose by Trading?” / “Who Gains from Trade?”)  
  - Aggregate individual portfolio penalty ≈ **3.8%/year**; trading of individuals subtracts **>3 percentage points/year** after costs.  
  - Virtually all individual losses linked to **aggressive** (liquidity-taking) orders; institutions profit ~**+1.5%/year** after commissions/taxes (before other costs).  
  - Implies: “many small aggressive round-trips” is exactly the losing profile.

- **NBER WP 26911** (Liu, Peng, Xiong, Xiong; survey + Chinese brokerage data) — “Taming the Bias Zoo” / excessive-trading puzzle  
  - Retail turnover high; more trading → worse net performance; investors **underestimate** round-trip costs (~70% estimate below true fee band).  
  - Reinforces: cost neglect + overtrading is widespread among retail.

### 3) Crypto-specific (on-chain gas + DEX fees, CEX fees)

- **Barbon & Ranaldo (2024)** — “On the Quality of Cryptocurrency Markets: CEX vs DEX” (SFI / Uni Basel; comprehensive CEX+DEX sample ~Mar 2021–Feb 2023)  
  - DEX cost = spread + protocol fee + **fixed gas** → **gas dominates small trades**.  
  - Example magnitudes (Uniswap v2 averages): gas alone ≈ **~205 bp on a $1,000** trade vs **~20 bp on $10,000**; total TCs for $1k often **~160–235+ bp**.  
  - **CEXs cheaper for small/medium sizes; DEXs competitive mainly for large trades** (roughly **>$10k–$100k**, depending on pair).  
  - Causal IV evidence: higher gas → worse DEX price efficiency (arbitrage deviations rise).

- **Adams et al. (2023)** — Uniswap Labs / “The Costs of Swapping on the Uniswap Protocol”  
  - On Ethereum mainnet, for swaps **<$1k**, **gas can be up to ~98% of total trading cost**; median Uniswap v3 mainnet swap gas cited in related L2 work ~**~$10** vs L2 ~**$0.28**.

- **BIS Working Paper 1227 (2024)** — “Decentralised dealers? Examining liquidity provision in decentralised exchanges”  
  - Retail LPs capture only **~10–25% of trading fees** and earn **substantially lower returns on capital** than sophisticated LPs.  
  - DEX takers also pay **gas** on top of pool fees; CEX fees are %-of-volume maker/taker.

- **Lehar, Parlour & Zoican** — liquidity fragmentation on DEXs  
  - Fixed gas creates **economies of scale**: small/retail LPs disproportionately hurt; they migrate to high-fee / low-turnover pools.

**Implication for Quentin’s setup:** MetaMask / on-chain “many small” spot trades face **fixed gas + spread + AMM fee** that can erase single-digit % wins; Revolut/CEX paper trading still faces spreads/fees/slippage and timing error, but without gas — still cost-sensitive at high turnover.

### 4) When short-horizon scalping *can* work (narrow conditions)

Literature does **not** say scalping never works; it says it works only when costs are structurally below the edge:

| Condition | Why it matters | Typical retail MetaMask? |
|-----------|----------------|--------------------------|
| **Proven, persistent edge** (not “felt” edge) | Gross alpha must exceed round-trip cost × turnover | Rare |
| **Very low effective costs** (maker rebates / passive limit orders, not taker) | Aggressive orders drive retail losses (Taiwan studies) | Usually taker |
| **Scale that dilutes fixed costs** (esp. gas) | Barbon–Ranaldo: DEX cheap only for large tickets | Small tickets |
| **Cost-aware design** (banding / lower turnover) | Novy-Marx–Velikov: buy/hold spread is best mitigator; high-turnover anomalies die | High turnover |
| **Institutional execution / HFT infrastructure** (latency, queue priority, maker-taker) | Micro-edges require tech + rebates; competition fierce | No |

**Frazzini, Israel & Moskowitz (AQR working paper)** — “Trading Costs of Asset Pricing Anomalies”: with live institutional execution, some anomalies survive, but **capacity is turnover-limited**; short-term reversal is among the **most cost-constrained**. Reinforces: short horizon + high turnover is the hardest regime.

---

## Plain summary bullets (parent → simple French)

1. **Yes — research consistently finds costs usually kill “many small winning trades” for retail / high-turnover strategies.** Gross wins ≠ net wealth.

2. **Classic JoF evidence (Barber & Odean 2000):** most active traders earned **11.4%/yr** vs **18.5%** for infrequent traders; round-trip costs historically ~**4%**; ~**75%** annual turnover was enough to destroy performance.

3. **High-turnover “alpha” often vanishes after costs (Novy-Marx & Velikov 2016 RFS):** strategies with **>50% monthly one-sided turnover** rarely stay profitable net; mid-turnover costs often **20–57 bp/month**.

4. **Retail aggressive trading loses systematically (Taiwan / Barber–Odean):** individuals lose ~**3–4%/yr** from trading; almost all losses from **aggressive** orders; institutions are the counterparties who gain.

5. **Crypto DEX/MetaMask is worse for small tickets:** gas is a **fixed $ cost** → can be **tens to hundreds of bp** (even ~**98%** of cost) on sub-$1k swaps (Barbon–Ranaldo; Adams et al.); CEX/Revolut avoids gas but still has fees/spreads/slippage.

6. **Scalping can work only with a real edge + maker/low costs + scale/tech** — not from “many small wins” on retail taker flow. Literature’s default answer for Quentin’s profile: **costs dominate**.

---

## Key citations (real; verify via links)

| Source | Year | Venue |
|--------|------|--------|
| Barber & Odean, “Trading Is Hazardous to Your Wealth” | 2000 | *Journal of Finance* |
| Odean, “Do Investors Trade Too Much?” | 1999 | *AER* |
| Carhart, “On Persistence in Mutual Fund Performance” | 1997 | *Journal of Finance* |
| Novy-Marx & Velikov, “A Taxonomy of Anomalies and Their Trading Costs” | 2016 | *RFS* / NBER WP 20721 |
| Barber, Lee, Liu, Odean (Taiwan trading gains/losses) | ~2007–2009 | various / RFS-related |
| Liu et al., NBER WP 26911 (“Bias Zoo” / excessive trading) | 2020+ | NBER |
| Barbon & Ranaldo, CEX vs DEX market quality | 2024 | working paper / arXiv 2112.07386 |
| Adams et al., Uniswap swap costs | 2023 | Uniswap / arXiv |
| BIS WP 1227, DEX liquidity provision | 2024 | Bank for International Settlements |
| Frazzini, Israel, Moskowitz, trading costs of anomalies | 2012+ | AQR WP |

*No advice on bypassing geo restrictions. No investment advice — research summary only.*
