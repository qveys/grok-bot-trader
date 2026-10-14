# Migration inventory — box → own server (13 Oct 2026, 10:10 Brussels time)

Files in /workspace/export/:
- `migration-20261013.tar.gz`: main archive with no secrets. Paths are relative to `/` (`workspace/…`, `home/box/…`). It also holds `MIGRATION_DOCS/` (this file, the guide, inventory/).
- `secrets.tar.gz.gpg`: secrets only (GPG symmetric, AES256). Passphrase is in `PASSPHRASE.txt` (chmod 600).
- `SHA256SUMS`: checksums.
- `inventory/`: versions.txt, pip-freeze-*.txt (system and each venv), npm-global.txt, apt-manual.txt, processes.txt, ports.txt, env-var-names.txt (names only), routines-observed.txt, secret-files.txt (list of paths only).

## Included in the main archive
| Path | Contents |
|---|---|
| /workspace/predict-market-bot | config.json, MODE, env (paths only), scripts/, guardian/ (validate_order, paper_fill, live_place, watch_stops…), state/ (incl. price_ticks, routine_runs.jsonl), knowledge/, references/, tmp/ |
| /workspace/guardian | Python guardian (`python -m guardian`), data/ (state.json, journal.log), deploy/ (run.sh, grok-bot.service, Dockerfile, env.example), tests, requirements.txt. `secrets/private.pem` is a symlink to predict-market-bot/secrets/… |
| /workspace/bot | Ca$her bot: INSTRUCTIONS.md, regles-jeu.md, wake.sh, decide.sh, decision*.json |
| /workspace/tools/sonnette | sonnette daemon (sonnette.py, config.json, start/stop/status.sh, state/, backups/) |
| /workspace/tools/veilleur | battement.py, pousse_etat.py, worker/ (Cloudflare Worker pm-veilleur), sonnette-cf/ (worker pm-sonnette-cf, prototype), deploy scripts, state/, logs/ |
| /workspace/tools/vibe-trading | backtest tool (vt_*.py, backtest.sh, ai.sh, checks/, home/sessions*, swarm, imports) |
| /workspace/tools/wrangler, tools/codex-cli | package.json only (+ lockfiles if present) |
| /workspace/tools/predict_lock, tools/routine_log | small helpers |
| /workspace/dashboard | build.py, src/, site/, cloudflare/ (Pages Functions, D1 scripts), *_loop.sh, start/stop.sh, cache, logs, screenshots (103 MB), backups |
| /workspace/dashboard-work, dashboard-staging, backups/, compound_2026-10-0x/, guardian (above), setup/, tests_watcher/, *.md briefs, avatars | everything else in /workspace |
| /home/box/agent-data/workflows | 6 user skills (SKILL.md): predict-market-scan, prediction-market-{scan,research,predict,risk,compound} |
| /home/box/agent-data/agents/* | 14 bots/groups: profile.json (instructions/persona), settings.json, group.json, assets, attachments, automations/, memory/, audit.jsonl. **Excluded: store.db\* and conversation-blobs.db** (the app's internal chat history, which could contain secrets) |
| /home/box/agent-data/plugins | plugin cache (revolut-x, finance, google-drive) |
| ~/.config/revolut-x | **nothing outside the secrets archive** (config.json, private.pem, public.pem are all in there) |
| ~/.config/.wrangler | metrics.json, registry/ (logs excluded). No OAuth login: wrangler uses CLOUDFLARE_API_TOKEN |
| ~/.local/bin | revx wrappers (revx, revx.real, revx-proxy-preload.cjs). ~/.local/lib (revx npm package) is not copied: reinstall it with npm |

Size: ~141 MB compressed, ~219 MB extracted, ~10,600 files.

## Excluded (bulk that can be regenerated)
| Excluded | Size | How to regenerate |
|---|---|---|
| tools/vibe-trading/home/runs (4,148 backtest runs) | 5.8 GB | re-run backtest.sh (results only, not needed to run anything) |
| tools/vibe-trading/home/cache (ccxt) | 7 MB | rebuilt automatically |
| tools/vibe-trading/.venv | 1.0 GB | `python3 -m venv .venv && .venv/bin/pip install -r inventory/pip-freeze-vibe-trading-venv.txt` |
| guardian/.venv | 32 MB | `pip install -r guardian/requirements.txt` (requests, cryptography) |
| dashboard/.venv-shot | 155 MB | playwright (screenshots only): see pip-freeze-dashboard-venv-shot.txt, then `playwright install chromium` |
| tools/wrangler/node_modules | 240 MB | `cd tools/wrangler && npm install` (wrangler ^4.148.0, Node ≥ 22) |
| tools/codex-cli/node_modules | 430 MB | `npm install` (@openai/codex ^0.161.0) |
| tools/node22 | 205 MB | install Node 22 (v22.20.0 here) |
| tools/cloudflared | 39 MB | download from Cloudflare |
| */__pycache__, */.wrangler (local wrangler caches), .playwright-mcp | small | automatic |
| agents/*/store.db*, conversation-blobs.db | — | app-internal |

## Secrets (secrets.tar.gz.gpg only, 14 files)
tools/sonnette/secrets.env, tools/veilleur/secrets.env, tools/veilleur/{worker,sonnette-cf}/.dev.vars, tools/vibe-trading/home/auth/openai-codex.json, bot/env (GUARDIAN_URL/TOKEN), predict-market-bot/secrets/{revolut_x_api_key, revolut_x_ed25519_private.pem, kalshi_private.pem}, predict-market-bot/guardian/.env, guardian/.env, ~/.config/revolut-x/{config.json, private.pem, public.pem}.
Checks run on the main archive: rg found no matches for private keys, tokens (sk-, ghp_, xox, Telegram, Bearer) or KEY=value patterns, and none of the real secret values appear in it. The only match was a file path in config.json.
Not on disk (re-enter them in Cloudflare): Worker/Pages secrets set with `wrangler secret` / set_secret.py (DASHBOARD_PASSWORD, VEILLEUR_SECRET, TELEGRAM_*, etc.). Their names are in env-var-names.txt.

## Processes running at export time (none were touched)
| Process | Started by | Working dir |
|---|---|---|
| `python -m guardian` (guardian/.venv) + bash supervise loop (restarts unless rc 0/42/43) | ad-hoc nohup loop (equivalent: guardian/deploy/run.sh start, or the systemd unit grok-bot.service) | /workspace/guardian |
| `python3 tools/sonnette/sonnette.py` | tools/sonnette/start.sh (also starts the veilleur battement) | tools/sonnette |
| `python3 tools/veilleur/battement.py` | tools/veilleur/start_battement.sh | |
| `python3 predict-market-bot/guardian/scripts/watch_stops.py --interval 30` | guardian/scripts/start_stop_watch.sh, or started automatically by paper_fill/live_place after an open | predict-market-bot |
| `python3 predict-market-bot/scripts/collect_price_ticks.py` | scripts/start_price_ticks.sh (supervise loop) | predict-market-bot |
| dashboard: refresh_loop.sh (5 min), prices_loop.sh (30 s), deploy_loop.sh (15 min → Pages), cloudflare/push_live_loop.sh (→ D1), `http.server 8080` (127.0.0.1) | dashboard/start.sh (needs CLOUDFLARE_API_TOKEN in the env) | /workspace/dashboard |

Listening ports owned by the setup: 127.0.0.1:8750 (guardian API), 127.0.0.1:8080 (local dashboard). All other ports (VNC, 13xx/14xx node, 8790/8791 egress proxy, 22, 6080/6081) belong to the box/app.
Note: scripts set HTTPS_PROXY=http://127.0.0.1:8791 by default. That is the box's egress proxy and must be removed (or unset) on your own server. The same goes for ~/.local/bin/revx.
No crontab, no systemd/user units: everything is nohup + pidfile.

## Versions
Debian 13 (trixie) x86_64, Python 3.13.5, Node 20.19.2 system / 22.20.0 (tools/node22), npm 9.2.0, wrangler 4.148.0, @revolut/revolut-x-cli 1.0.50 (npm prefix ~/.local), gpg 2.4.7. Details are in inventory/.

## Cloudflare resources (names/ids from config files)
- Pages project **pm-pipeline-tableau** (https://pm-pipeline-tableau.pages.dev), Functions in dashboard/cloudflare/functions, binding LIVE_DB.
- D1 **pm-pipeline-live**: 47c59ccf-6194-4899-adda-12a43a9f30b9 (dashboard/cloudflare/d1/live.json, schema.sql).
- D1 **pm-veilleur**: ddf64285-8b63-46aa-b96f-c9f26af726fd.
- Worker **pm-veilleur** (cron */5, D1 pm-veilleur); Worker **pm-sonnette-cf** (prototype, cron every minute, same D1).
- Other UUIDs seen in dashboard code/logs (e.g. 205eb6ad-…) are deployment/account ids, not resources to recreate.
These resources stay in the Cloudflare account. Nothing needs to move: only the token (CLOUDFLARE_API_TOKEN / CLOUDFLARE_ACCOUNT_ID, in secrets.env) is needed.

## Bots (Grok Bot AI agents) and routines
Routines run on the app server and are not stored on disk. Only one was found on disk: **Ca$her / "Cycle trader"**, cron `*/30 * * * *`, **disabled**, prompt in agents/33148aab…/automations/cycle-trader/automation.json.
Routines seen in predict-market-bot/state/routine_runs.jsonl (inventory/routines-observed.txt): PM-Scan "PM Scan paper"; PM-Research "Point du jour 14h44", "Bilan séance 17h42"; PM-Predict "Passage du matin 9h", "Prédiction avant session", "Sonnette Predict"; PM-Risk "Risk dry-run + alertes", "Sonnette stop (Risk)"; PM-Compound "Sonnette Compound (trade fermé)", "Score prévisions Predict", "perf et verdicts". The exact times and prompts are only in the app (to copy by hand).
Groups (no instructions of their own): PM Pipeline, PM Compound, Dashboard, Évaluation, Équipe trading.

## Not captured
- The bots' routines (schedules/prompts) and conversation histories (app server; store.db excluded).
- Secret values stored only in Cloudflare (Worker/Pages secrets).
- Full apt list: inventory/apt-manual.txt is a best-effort list (not a diff against a base image).
- Live files (state/, logs, guardian/data) are a hot snapshot from 10:09. They may change slightly before you migrate.

## GitHub repo (qveys/grok-bot-trader, private), 14 Oct 2026
The browsable tree has the same scope as the archive.
- **Chat databases:** `agents/*/store.db` are included (nearly empty, scanned clean). Ca$her's `conversation-blobs.db` contained secret values, so it is only in `MIGRATION_DOCS/encrypted/chat-dbs.tar.gz.gpg` (same passphrase).
- **Not in the repo:**
  - `PASSPHRASE.txt`
  - the plaintext secret files listed above
  - `~/.config/gh/hosts.yml`
  - the migration-*.tar.gz archives and their parts (same content as the tree)
  - the regenerable bulk listed above
  - the nested `.git` folder of the revolut-x plugin cache
- **Secret scan:** gitleaks 8.28 plus a check of every secret value. Remaining hits are dummy test values only (`abcdefgh12345678`, `abcd…efgh`, local wrangler ports).
