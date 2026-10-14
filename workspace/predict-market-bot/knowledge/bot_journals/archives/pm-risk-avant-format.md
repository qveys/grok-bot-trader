# Journal de bord — PM-Risk

## 2026-10-07

- Rôle : accepter / refuser les trades (surtout simulation), surveiller les limites de perte, placer un live seulement si l’équipe l’arme (max 1 / jour).
- Règles notées : gain espéré ≥ 3× le coût ; décision écrite obligatoire ; simulation large / live rare ; 15h–17h aujourd’hui = simulation seulement ; live éventuel réservé à la Fed ~20h.
- Position simulée ETH : achetée à 2500 € (test), stop à 2300 €. Vers 15h17, ETH ~2293 € → **stop touché**, position fermée. Perte simulée ≈ **0,83 €** sur 10 €. Plus de position ouverte.
- Remis à Compound pour le journal de vente.
- Aucun live aujourd’hui (après-midi).

- Routine créée : dry-run live + alertes (stop / perte jour 15 % / chute 8 %) les jours de semaine ~14h24 ; avant tout live → croiser l’historique Revolut du jour.

- Auto-stop : watch_stops (~15s) ferme le simulé au stop + réveil Risk. Alerte achat : check_buy_wake si Predict dit acheter et Risk n’a pas encore tranché (pas Scan).

- 7 oct soir Fed ~20h40 : D-010/011/012 pas d’achat ; refus (pas de prix frais depuis ~17h25). 0 live aujourd’hui. 0 position, pas d’alerte.
- 2026-10-08 13:1x: BTC/ETH/SOL comptés comme un seul risque; total ouvert sur les 3 paires ≤ 5 % (max_exposure_pct 0.25→0.05).
- 2026-10-08 14:3x: ligne rx-live-test-1 (7 oct) = test du watcher, pas une vraie position. Revolut vérifié: 0 ordre ouvert, dernier ordre bot 19 sept; ETH/SOL détenus = avoirs existants de Quentin. Ligne archivée dans state/auto_stop_events.test-2026-10-07.jsonl.
- 2026-10-08 15:4x: Pas de live tant que l’alerte stop LIVE ne réveille pas vraiment Risk + Quentin (règle ajoutée au live-playbook).

- 2026-10-08 15:57: Essai sonnette (webhook test=true, zone TEST). Sonnette OK — rien à faire.
- 2026-10-08 15:58: Sonnette (script Grok Bot) branchée sur ma routine webhook « Sonnette stop (Risk) », essai reçu 15h57. Perte du jour en simulation remise à zéro chaque jour (daily_pnl_date, heure de Bruxelles). Source argent réel (state/live_equity.json) demandée à Grok Bot.
- 2026-10-08 16:09: MetaMask (adresse publique) = 0,0397 ETH sur Arbitrum, aucun jeton. Vendable ≈0,0387 ETH (garder ~0,001 pour frais). Bouton Échanger MetaMask ≈0,875 %/échange → refusé pour D-018; Uniswap direct 0,05 % → OK. Plafond 5 % commun Revolut+MetaMask. Revolut vendable: 0,0209 ETH, 0,241 SOL.
- 2026-10-08 17:30: D-019/D-020 rétro enregistrés dans state/retro_sims.jsonl (pas state.json). Vérif ticks OK. Plafond 25 € dépassé ensemble (49 €) → noté.
- 2026-10-08 18:16: Surveillant auto-démarré (paper+live), prix = relevé commun 30 s (repli Revolut >2 min). Sortie live auto sur stop (live_place --exit, allow_live_auto_sell true, décision Quentin). À surveiller : 1re vraie sortie live (formats Revolut non vérifiés en réel) ; sonnette Grok Bot ne voit pas bien l'idée à la baisse live (signalé à Grok Bot).
