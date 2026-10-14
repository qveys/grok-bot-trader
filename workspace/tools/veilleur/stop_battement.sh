#!/usr/bin/env bash
DIR="$(cd "$(dirname "$0")" && pwd)"; PID_FILE="$DIR/state/battement.pid"
[[ -f "$PID_FILE" ]] && pid="$(cat "$PID_FILE")" && kill "$pid" 2>/dev/null && echo "battement arrêté (pid=$pid)"
rm -f "$PID_FILE"
