#!/usr/bin/env bash
cd /workspace/compound_2026-10-11/filtre_calme
while IFS=$'\t' read -r out cmd; do
  [ -s tool_json/$out ] && continue
  echo "$out"$'\t'"$cmd"
done < scripts/cmds.tsv | xargs -P 7 -d '\n' -I{} bash -c 'line="{}"; out="${line%%$'"'"'\t'"'"'*}"; cmd="${line#*$'"'"'\t'"'"'}"; $cmd > tool_json/$out 2> tool_json/$out.err; echo done $out'
