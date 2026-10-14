#!/usr/bin/env bash
# Print sonnette status (running, last tick, counters, dry/real).
set -euo pipefail
DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$DIR"
# secrets.env is read by sonnette.py itself (never echoed); ignore stale SONNETTE_* exports
if [[ "${SONNETTE_USE_ENV:-0}" != "1" ]]; then
  for v in $(compgen -e | grep '^SONNETTE_' || true); do unset "$v"; done
fi
exec python3 "$DIR/sonnette.py" --status
