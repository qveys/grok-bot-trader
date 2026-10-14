| pair | strat | stop | net M | net T | net K | trades | win% | H1 (M) | H2 (M) | worst drop capital 5% (M) | biggest loss/trade % | avg loss % |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| ETH | rebound | fixed | +5.58 | +0.97 | +0.92 | 19 | 58 | +7.63 | -1.90 | 0.17 | -1.50 | -1.19 |
| ETH | rebound | trail1.5 | +2.72 | -0.18 | -1.92 | 19 | 47 | +5.92 | -3.02 | 0.17 | -1.50 | -1.06 |
| ETH | breakout | fixed | -6.43 | -9.34 | -15.13 | 40 | 40 | -6.01 | -0.45 | 0.37 | -1.50 | -1.15 |
| ETH | breakout | trail1.5 | -6.05 | -7.25 | -15.52 | 40 | 35 | -4.88 | -1.22 | 0.32 | -1.50 | -0.98 |
| ETH | sell_rebuy | fixed | +4.08 | +4.08 | +0.08 | 43 | 35 | +2.27 | +1.78 | 0.57 | -1.48 | -1.48 |
| ETH | sell_rebuy | trail1.5 | +14.24 | +14.24 | +4.75 | 72 | 47 | +13.50 | +0.66 | 0.34 | -1.48 | -0.89 |
| SOL | rebound | fixed | +8.23 | +6.39 | -0.63 | 23 | 65 | +2.91 | +5.17 | 0.15 | -1.50 | -1.39 |
| SOL | rebound | trail1.5 | -0.92 | +4.05 | -9.26 | 23 | 44 | -2.24 | +1.35 | 0.18 | -1.50 | -1.05 |
| SOL | breakout | fixed | +3.56 | +3.09 | -6.13 | 41 | 56 | +2.10 | +1.43 | 0.40 | -1.50 | -1.39 |
| SOL | breakout | trail1.5 | +0.05 | -0.69 | -9.74 | 41 | 44 | -0.88 | +0.93 | 0.38 | -1.50 | -1.04 |
| SOL | sell_rebuy | fixed | +16.23 | +16.23 | +10.05 | 63 | 38 | +24.87 | -6.92 | 0.62 | -1.48 | -1.48 |
| SOL | sell_rebuy | trail1.5 | +30.47 | +30.47 | +17.14 | 95 | 46 | +35.38 | -3.62 | 0.42 | -1.48 | -0.88 |
| BTC | rebound | fixed | +0.99 | -2.91 | -1.63 | 11 | 46 | +1.41 | -0.41 | 0.11 | -1.50 | -1.07 |
| BTC | rebound | trail1.5 | -0.57 | -4.54 | -3.35 | 11 | 36 | +0.36 | -0.93 | 0.12 | -1.50 | -0.93 |
| BTC | breakout | fixed | +1.14 | -2.94 | -8.95 | 42 | 50 | -5.18 | +6.67 | 0.37 | -1.50 | -1.10 |
| BTC | breakout | trail1.5 | +2.93 | -1.28 | -7.89 | 42 | 45 | -3.61 | +6.78 | 0.28 | -1.50 | -0.84 |
| BTC | sell_rebuy | fixed | +16.93 | +16.93 | +14.98 | 23 | 48 | +15.04 | +1.64 | 0.43 | -1.48 | -1.48 |
| BTC | sell_rebuy | trail1.5 | +6.71 | +6.71 | +2.61 | 33 | 42 | +8.02 | -1.22 | 0.30 | -1.48 | -0.71 |

### Who keeps more money, fixed vs trailing 1.5 (count of pair×strategy, 9 combos)
- maker_allfilled net year: trailing better 4, fixed better 5, tie 0; sum net fixed +50.31 vs trailing +49.58
- maker_allfilled H1: trailing better 4, fixed better 5, tie 0; sum net fixed +45.04 vs trailing +51.57
- maker_allfilled H2: trailing better 2, fixed better 7, tie 0; sum net fixed +7.01 vs trailing -0.29
- maker_allfilled worst drop: trailing smaller 6, fixed smaller 2; avg loss/losing trade fixed -1.30% vs trailing -0.93%
- maker_touch net year: trailing better 4, fixed better 5, tie 0; sum net fixed +32.50 vs trailing +41.53
- maker_touch H1: trailing better 4, fixed better 4, tie 1; sum net fixed +32.38 vs trailing +47.05
- maker_touch H2: trailing better 3, fixed better 6, tie 0; sum net fixed +1.68 vs trailing -3.97
- maker_touch worst drop: trailing smaller 6, fixed smaller 3; avg loss/losing trade fixed -1.37% vs trailing -1.09%
- taker_market net year: trailing better 3, fixed better 6, tie 0; sum net fixed -6.44 vs trailing -23.18
- taker_market H1: trailing better 4, fixed better 5, tie 0; sum net fixed +13.13 vs trailing +6.19
- taker_market H2: trailing better 2, fixed better 7, tie 0; sum net fixed -18.38 vs trailing -28.46
- taker_market worst drop: trailing smaller 4, fixed smaller 5; avg loss/losing trade fixed -1.47% vs trailing -1.12%

### Half-year flips (fixed vs trailing 1.5: winner in H1 differs from H2)
- maker_allfilled ETH-EUR team_breakout: H1 trailing (-6.01 fixed / -4.88 trail), H2 fixed (-0.45 / -1.22)
- maker_allfilled ETH-EUR sell_rebuy: H1 trailing (+2.27 fixed / +13.50 trail), H2 fixed (+1.78 / +0.66)
- maker_touch ETH-EUR sell_rebuy: H1 trailing (+2.27 fixed / +13.50 trail), H2 fixed (+1.78 / +0.66)
- taker_market ETH-EUR team_breakout: H1 trailing (-9.83 fixed / -9.19 trail), H2 fixed (-5.88 / -6.98)
- taker_market ETH-EUR sell_rebuy: H1 trailing (-0.70 fixed / +5.83 trail), H2 fixed (+0.79 / -1.02)

### Sensitivity (net % for the year): fixed / trail 0.75 / trail 1.5 / trail 2.25 / trail 1.5 without take-profit
| pair | strat | scen | fixed | t0.75 | t1.5 | t2.25 | t1.5 noTP | fixed noTP |
|---|---|---|---|---|---|---|---|---|
| ETH | rebound | M | +5.58 | -6.00 | +2.72 | +5.58 | +5.91 | +6.92 |
| ETH | rebound | T | +0.97 | -8.28 | -0.18 | +0.97 | +8.03 | +4.00 |
| ETH | rebound | K | +0.92 | -10.40 | -1.92 | +0.92 | +0.68 | +1.78 |
| ETH | breakout | M | -6.43 | -1.38 | -6.05 | -5.77 | +14.54 | +12.69 |
| ETH | breakout | T | -9.34 | -5.58 | -7.25 | -8.79 | +10.52 | +6.76 |
| ETH | breakout | K | -15.13 | -11.17 | -15.52 | -14.66 | +2.37 | +1.56 |
| ETH | sell_rebuy | M | +4.08 | +17.28 | +14.24 | -2.44 | n/a | n/a |
| ETH | sell_rebuy | T | +4.08 | +17.28 | +14.24 | -2.44 | n/a | n/a |
| ETH | sell_rebuy | K | +0.08 | +0.41 | +4.75 | -8.65 | n/a | n/a |
| SOL | rebound | M | +8.23 | -6.53 | -0.92 | +8.23 | +5.15 | +6.87 |
| SOL | rebound | T | +6.39 | -3.73 | +4.05 | +6.42 | +5.98 | +3.41 |
| SOL | rebound | K | -0.63 | -11.75 | -9.26 | -0.63 | -3.37 | -5.06 |
| SOL | breakout | M | +3.56 | +0.26 | +0.05 | +4.33 | +13.15 | +18.10 |
| SOL | breakout | T | +3.09 | -2.31 | -0.69 | +3.09 | +7.56 | +14.31 |
| SOL | breakout | K | -6.13 | -9.31 | -9.74 | -5.58 | +1.32 | +6.19 |
| SOL | sell_rebuy | M | +16.23 | +29.50 | +30.47 | +15.21 | n/a | n/a |
| SOL | sell_rebuy | T | +16.23 | +29.50 | +30.47 | +15.21 | n/a | n/a |
| SOL | sell_rebuy | K | +10.05 | +7.36 | +17.14 | +6.98 | n/a | n/a |
| BTC | rebound | M | +0.99 | -0.03 | -0.57 | +0.15 | +2.84 | +1.94 |
| BTC | rebound | T | -2.91 | -3.29 | -4.54 | -3.48 | -0.37 | +0.44 |
| BTC | rebound | K | -1.63 | -2.62 | -3.35 | -2.50 | -0.23 | -0.90 |
| BTC | breakout | M | +1.14 | +1.58 | +2.93 | +1.19 | +12.57 | +6.31 |
| BTC | breakout | T | -2.94 | +1.46 | -1.28 | -2.94 | +3.13 | -0.76 |
| BTC | breakout | K | -8.95 | -9.55 | -7.89 | -8.95 | +0.13 | -4.87 |
| BTC | sell_rebuy | M | +16.93 | +6.58 | +6.71 | +10.55 | n/a | n/a |
| BTC | sell_rebuy | T | +16.93 | +6.58 | +6.71 | +10.55 | n/a | n/a |
| BTC | sell_rebuy | K | +14.98 | +0.22 | +2.61 | +7.80 | n/a | n/a |

### Sum over 9 combos per variant (net %, simple sum, just to rank)
variant          fixed  fixed_noTP  trail0.75  trail1.5  trail1.5_noTP  trail2.25
scenario                                                                         
maker_allfilled  50.31       52.83      41.26     49.58          54.16      37.03
maker_touch      32.50       28.16      31.63     41.53          34.85      18.59
taker_market     -6.44       -1.30     -46.81    -23.18           0.90     -25.27

team_* only (6 combos):
variant          fixed  fixed_noTP  trail0.75  trail1.5  trail1.5_noTP  trail2.25
scenario                                                                         
maker_allfilled  13.07       52.83     -12.10     -1.84          54.16      13.71
maker_touch      -4.74       28.16     -21.73     -9.89          34.85      -4.73
taker_market    -31.55       -1.30     -54.80    -47.68           0.90     -31.40

sell_rebuy only (3 combos):
variant          fixed  trail0.75  trail1.5  trail2.25
scenario                                              
maker_allfilled  37.24      53.36     51.42      23.32
maker_touch      37.24      53.36     51.42      23.32
taker_market     25.11       7.99     24.50       6.13

Mean worst drop on our capital (5% stakes), %:
variant          fixed  fixed_noTP  trail0.75  trail1.5  trail1.5_noTP  trail2.25
scenario                                                                         
maker_allfilled  0.356       0.333      0.228     0.279          0.260      0.356
maker_touch      0.401       0.366      0.295     0.335          0.334      0.396
taker_market     0.467       0.438      0.462     0.465          0.383      0.489
