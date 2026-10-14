# Platforms / Plateformes

## Polymarket

- **Discovery (no key):** Gamma API — `https://gamma-api.polymarket.com/markets` (used by `scan_markets.py`).
- **Trading CLOB:** `https://clob.polymarket.com` (see `config.json` → `platforms.polymarket.base_url`).
- **Auth (live only):** wallet signature (EIP-712) to derive L2 API credentials (`API_KEY`, `SECRET`, `PASSPHRASE`). Private key signs; never commit keys.
- **Orders:** signed CLOB orders; paper mode must never hit order endpoints.
- **Tooling mention:** community CLIs such as **pmxt** can help explore markets; treat them as optional research aids, not as this bot’s execution path.

## Kalshi

- **Demo REST:** `https://demo-api.kalshi.co/trade-api/v2` (`config` → `env: demo`).
- **Prod REST:** typically `https://api.elections.kalshi.com/trade-api/v2` (confirm current docs before live).
- **Auth:** API Key ID + RSA private key; requests signed with timestamped headers (no secrets in repo — use `KALSHI_API_KEY_ID` + `KALSHI_PRIVATE_KEY_PATH` from `.env`).
- Start on **demo**; flip `env` and base URL only after paper validation.

## Security hygiene

- Keep credentials in environment / secret store only (see `.env.example`).
- Never paste private keys, API secrets, or passphrases into chat.
- Live trading additionally requires `MODE=live` **and** absence of the `STOP` kill-switch file.

## Regulatory caution (Belgium / EU)

- The operator lives in the **EU (Belgium)**. Prediction-market access, geo-restrictions, and local gambling/financial rules may prohibit or limit retail trading on Polymarket, Kalshi, or similar venues.
- This workspace is built **paper-first**. Enabling live mode is an explicit, user-owned decision after legal/compliance review — not financial, legal, or tax advice.
- Prefer demo/paper endpoints until counsel confirms eligibility.
