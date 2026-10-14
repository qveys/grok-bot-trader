---
name: Prediction market risk
description: >-
  Use when sizing, validating risk, and paper-executing Revolut X crypto spot
  (guardian validate_order + paper_fill only) or legacy paper_trade paths. Kill switch.
---
# Prediction market — Risk and execution

Use when sizing a trade, validating risk, paper-trading, or (only if explicitly live) placing an order.

## Goal
Deterministic risk gate, then execute only if all checks pass.

## Shared workspace
`/workspace/predict-market-bot/` (+ `guardian/` for Revolut X paper)

## Kill switch and mode
1. If `STOP` exists → reject all new orders.
2. Read `MODE` and `config.json`. Default is **paper**. Keep `platforms.revolut_x.trading=false` unless user explicitly flips live.
3. **Live** only when MODE=live, STOP absent, API secrets configured, and the user explicitly authorized live trading for this session/ask.

## Deux types d’idée
- **Idée à la hausse** (`idea_type: "hausse"`, défaut si absent) : achat puis revente plus haut.
- **Idée à la baisse** (`idea_type` / `kind: "baisse"`) : vente de pièces déjà détenues puis rachat plus bas. Pas l’expression « vendre d’abord ».
- Chaque ligne = `side` `buy` ou `sell` (Achat / Vente).

## Simulation ≠ live
- **Simulation** : taille ≤ 5 % bankroll (≤ 25 € par trade), stop obligatoire, exposition simulée totale ≤ 10 % = **50 €** (`paper_max_exposure_pct`, BTC+ETH+SOL + MetaMask sim, y compris baisses ; choix Quentin 9 oct), paires whitelist, limit post-only. **Pas** de règle gain ≥ 3× coûts.
- **Live** : inchangé (`live_place.py` / `LIVE_ONCE` / expectancy 3×) : ≤ 25 € par trade, exposition ≤ 25 € (`max_exposure_pct` 0.05, `validate_order.py --live`), `max_live_per_day` = 1 (config). Ne pas toucher le live depuis le chemin paper.

## Revolut X crypto paper (primary)
**MUST** call:
```bash
python3 guardian/scripts/validate_order.py ...
python3 guardian/scripts/paper_fill.py ...
```
- Never call Revolut live trading APIs from this skill while trading=false / MODE=paper.
- Prefer limit post-only; whitelist BTC-EUR, ETH-EUR, SOL-EUR.
- Inventaire simulé : `guardian/state.json` → `paper_inventory` (refus si qty > stock).
- `watch_stops.py` : long → stop en dessous ; baisse → stop (safety) au-dessus, cible en dessous → rachat auto. Démarre **tout seul** (détaché) après `paper_fill` / `live_place` réussis (`watcher_started` dans le JSON) ; prix = tick du collecteur ≤ 2 min, sinon Revolut, sinon scan ; 30 s.
- Live (8 oct, décision Quentin) : sortie **automatique** sur stop via `live_place.py --exit` (ne vend que la qty du pipeline, jamais les avoirs de Quentin ; 1 sortie/position ; ne touche pas LIVE_ONCE / live_day). Réveil `urgent` seulement si la sortie échoue — voir `references/live-playbook.md`.

- **Horaires live (8 oct)** : entrée live seulement 15:00–17:00 Bruxelles, pas dans les 15 min après une annonce (14:30, 15:30, `state/annonces_du_jour.json`) → `live_place.py` refuse (rc 12). Séance en plus seulement si Quentin donne le feu vert (`state/LIVE_EXTRA_SESSION.json`, date du jour). Fermeture 22h **retirée** (`force_close_enabled: false` ; code conservé). Simulation à toute heure. Battements : `state/watch_stops_heartbeat.json` (chaque tour) + `state/revolut_heartbeat.json` (~5 min, lecture seule Revolut tant qu'une position est ouverte) — lus par la sonnette Grok Bot.

- **Heure limite = rappel seulement (Quentin, 8 oct 23h)** : ordre d'ouverture avec `deadline` (ISO local Bruxelles, alias `deadline_at`) → stockée sur la position. Elle ne ferme **jamais** un trade : seuls le prix d'arrêt et le prix visé ferment. À l'heure, `watch_stops` écrit un rappel dans `state/deadline_reminder.json` (+ une ligne par position dans `state/deadline_reminders.jsonl`) ; Predict regarde le trade, Risk décide. `validate_order` : passée ou illisible → avertissement (pas de refus) ; absente en SIM → avertissement. Réglage : `guardian/config.json` → `deadline.close_enabled: false` (true = ancienne fermeture `heure_limite`).

### Exemple idée à la baisse
```bash
echo '{"pair":"SOL-EUR","side":"sell","type":"limit","price":110,"amount_eur":22,"qty":0.2,"idea_type":"baisse","decision_id":"D-018","stop_price":120,"target_price":100,"post_only":true}' \
  | python3 guardian/scripts/paper_fill.py
# puis rachat (ou watch_stops) avec linked_position_id / cycle_id + rebuy_reason
```

## Legacy / event-market paper path
```bash
python3 scripts/kelly_size.py --p ... --b ... --bankroll ... --fraction 0.25
python3 scripts/validate_risk.py
python3 scripts/paper_trade.py ...
```

## Position limits (guardian)
- Max 5 % bankroll / ticket (25 €) ; exposition totale : simulation ≤ 10 % (50 €), live ≤ 5 % (25 €) ; journal `trades_log.jsonl` avec les champs hausse/baisse ci-dessus.
- Slippage abort if price moved > max_slippage between signal and fill (live path).
- Max $50/day AI API cost budget.

## Hard rules
- Risk logic lives in Python scripts, not improvised chat math.
- Refusing a bad trade is success.
- Never bypass `validate_order.py` / `validate_risk.py`.

## Champs tableau (9 oct)
- `guardian/state.json` : par position ouverte `last_mid_eur`, `mark_eur`, `unrealized_pnl_eur`, `unrealized_pnl_pct`, `mark_ts` ; en haut `equity_eur`, `exposure_eur`, `exposure_pct`, `unrealized_pnl_eur`, `total_pnl_eur`, `drawdown_pct`, `summary_updated_at`. Écrits par watch_stops (chaque tour, ~30 s) et paper_fill (chaque trade) — ne pas les recalculer à la main ; écrire state.json seulement via les scripts (verrou `state.json.lock`).
- Sorties live : `realized_pnl_eur` net de frais dans la ligne `auto_exit` de `state/live_orders.jsonl`.
- Tests du passé : avis Risk dans `verdict_equipe.autorise_en_reel` (8 oct 21:32 : « non » pour tout).
