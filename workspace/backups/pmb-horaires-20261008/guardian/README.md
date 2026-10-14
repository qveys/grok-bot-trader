# Guardian — Revolut X risk gate / Couche risque

**EN** — Independent, deterministic risk gate for Revolut X spot under `predict-market-bot`.
Does **not** restore the deleted `/workspace/guardian` secrets or HTTP API. Old Ca$her
files under `/workspace/bot/` are left untouched; this path is separate.

- `config.json` — hard limits (whitelist, size, exposure, drawdown, daily loss).
- `state.json` — bankroll/cash/positions/PnL + `paper_inventory` (no secrets).
- `scripts/validate_order.py` — validate an order JSON (stdin or `--order` file).
- `scripts/paper_fill.py` — if validate OK, simulate fill into `state.json` + `../state/trades_log.jsonl`.
- `scripts/status.py` — print a status summary (no secrets).
- `scripts/watch_stops.py` — while **any** open position is tracked (guardian `state.json`,
  `state/positions.json` crypto rows, `live_orders.jsonl`, revx open orders best-effort),
  poll every **30 s**. On stop/target breach: **paper/sim** → close via `paper_fill` + wake;
  **live** (8 oct, décision Quentin, `config.json` `allow_live_auto_sell: true`) → **sortie
  automatique** via `live_place.py --exit` pour les positions du pipeline (`live_orders.jsonl`) ;
  urgent wake only if the exit fails (or for live rows not from `live_orders.jsonl`).
  After a close it **keeps watching** if other positions remain; exit **10** only when nothing is left.
  **Prix** : dernier tick de la paire dans `state/price_ticks/YYYY-MM-DD.jsonl` (collecteur commun,
  lecture de la fin du fichier) s’il a ≤ 2 min ; sinon Revolut (`revx market ticker`), sinon dernier
  scan, sinon tick périmé. Chaque cycle logue `prices[pair] = {mid, source, age_s}`.
- **Démarrage auto** (`scripts/watcher_launch.py`) — `paper_fill.py` (après chaque ouverture : achat
  hausse / vente baisse ; et avant une ouverture si des positions sont ouvertes sans surveillant) et
  `live_place.py` (après un ordre live réussi) lancent `watch_stops.py` détaché (`start_new_session`,
  log en ajout `state/watch_stops.log`) s’il ne tourne pas (pid `state/watch_stops.pid`). Sortie JSON :
  `watcher_started` / `watcher_already_running` (+ `watcher_preopen`). Désactiver : `PAPER_FILL_NO_WATCH=1`
  ou `WATCH_STOPS_NO_AUTOSTART=1`.
- `scripts/check_alerts.py` — stop / daily-loss / drawdown → `state/alerts_last.json`.
- `scripts/check_buy_wake.py` — Predict BUY awaiting Risk → `state/buy_wake.json`.
- `scripts/start_stop_watch.sh` — foreground wrapper for `watch_stops.py --interval 30` (`WATCH_STOPS_INTERVAL`).
- Kill switch: if `../STOP` or `guardian/HALTED` exists → reject all.
- Mode: `../MODE` must be `paper` or `live`.

## Deux types d’idée (validé Quentin, 8 oct)

| Type | `idea_type` | Ouverture | Fermeture |
|------|-------------|-----------|-----------|
| **Idée à la hausse** | `"hausse"` (défaut si absent) | Achat (`side=buy`) | Vente plus haut |
| **Idée à la baisse** | `"baisse"` (ou `kind=baisse`) | Vente de pièces déjà détenues (`side=sell`) | Rachat plus bas (`side=buy`) |

Chaque ligne de journal a `side` `buy` / `sell` (affiché Achat / Vente). Ne plus dire « vendre d’abord ».

**Idée à la baisse** — inventaire simulé dans `state.json` → `paper_inventory` (ETH/SOL Revolut + `metamask_arbitrum.ETH`). Refus si qty > inventaire. `decision_id` obligatoire. Prix d’arrêt = rachat de sécurité **au-dessus** (`stop_price` / `safety_price`) ; cible = rachat **en dessous** (`target_price`). Venue MetaMask Uniswap : frais 0,05 % / échange.

## Simulation ≠ live

**Simulation (`MODE=paper`)** — seulement :
- taille ≤ `max_position_pct` × bankroll (25 € si bankroll 500 €) ;
- prix d’arrêt obligatoire ;
- exposition totale (longs + baisses) ≤ `max_exposure_pct` (5 %) ;
- paires whitelist ; ordre limité post-only.
- **Pas** d’exigence gain ≥ 3× coûts.

**Live** — inchangé (`live_place.py`, `LIVE_ONCE`, `live_day.json`) : espérance ≥ 3× coûts, etc. Ne pas modifier le chemin live depuis ces scripts paper.

## Champs du journal (`state/trades_log.jsonl`)

- Hausse (achat) : `id`, `ts`, `mode`, `pair`, `side`, `idea_type=hausse`, `price`, `amount_eur`, `qty`, `stop_pct` ; à la vente : `realized_pnl_eur` / `pct`, `close_reason`, `linked_position_id`.
- Baisse (vente d’ouverture) : + `idea_type`/`kind=baisse`, `decision_id`, `fee_eur`, `venue`, `stop_price`, `target_price`, `safety_price`.
- Baisse (rachat) : `side=buy`, `cycle_id` + `linked_position_id`, `rebuy_reason` (`target`|`safety`|`time`), `realized_pnl_eur`/`pct`, `coins_gained`, `close_reason`.

## Exemple — simuler une idée à la baisse puis son rachat

```bash
# 1) Vente (ouvre le cycle) — pièces déjà en paper_inventory
echo '{
  "pair":"SOL-EUR","side":"sell","type":"limit","price":110,
  "amount_eur":22,"qty":0.2,"idea_type":"baisse","kind":"baisse",
  "decision_id":"D-018","stop_price":120,"target_price":100,"post_only":true
}' | python3 guardian/scripts/paper_fill.py

# 2) Rachat (ferme) — ou laisser watch_stops le faire au stop/cible
echo '{
  "pair":"SOL-EUR","side":"buy","type":"limit","price":100,
  "amount_eur":20,"qty":0.2,"idea_type":"baisse",
  "linked_position_id":"ID_DE_LA_VENTE","cycle_id":"ID_DE_LA_VENTE",
  "rebuy_reason":"target","post_only":true
}' | python3 guardian/scripts/paper_fill.py

# Gardien (30 s, démarré automatiquement par paper_fill) : mid ≥ stop → rachat safety ; mid ≤ target → rachat target
./guardian/scripts/start_stop_watch.sh
```

**Le surveillant démarre tout seul** après une ouverture (paper_fill / live_place). Manuel si besoin :

```bash
python3 guardian/scripts/watch_stops.py --once          # un cycle
./guardian/scripts/start_stop_watch.sh                  # boucle (refuse un 2e exemplaire)
```

Exit codes: `0` idle/ok, `10` close done and nothing left to watch (or `--once` / `--exit-on-close`), `1` hard error (5 erreurs de suite).

## Sortie automatique LIVE sur stop — 8 oct (décision Quentin)

`live_place.py --exit` (appelé par `watch_stops`, spec JSON sur stdin) — détail dans `references/live-playbook.md` :
- ne vend **que** la quantité de la position du pipeline : `min(qty position, solde dispo, solde total − avoirs de Quentin)` ;
  avoirs de Quentin = max(`config.live_exit.quentin_holdings`, `state/live_equity.json` `hors_bot`) ;
- relit Revolut (ordre d’entrée, ordres ouverts, solde) ; annule d’abord l’ordre objectif **du bot** lié à la position
  (jamais les ordres de Quentin) et le reste non rempli de l’ordre d’entrée ;
- limite exécutable (pas post-only) au meilleur acheteur −0,3 % (rachat baisse : meilleur vendeur +0,3 %), attente 60 s,
  sinon annule et replace à ∓0,5 %, 3 essais max → alerte urgente ;
- verrou `state/live_exits.json` : une seule sortie par position, jamais de doublon ni de nouvel essai auto après échec ;
- ne consomme **pas** `LIVE_ONCE`, n’écrit **pas** `live_day.json` ; autorisée même si `STOP` existe ;
- journal : ligne `kind: auto_exit` dans `state/live_orders.jsonl` (`amount_eur` = coût fermé), événement
  `auto_stop_events.jsonl`, réveil `auto_stop_wake.json` (`urgent: false` si OK, `true` si échec).

**FR** — Couche risque déterministe pour le spot Revolut X. Pas de secrets chat, pas d’API live depuis ces scripts. Ordres limit post-only ; whitelist BTC-EUR / ETH-EUR / SOL-EUR ; pas de levier.
