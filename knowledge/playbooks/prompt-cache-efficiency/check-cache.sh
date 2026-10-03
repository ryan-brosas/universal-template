#!/usr/bin/env bash
# Print prompt-cache rates and the 98/99% miss budgets from OpenCode V2 stats.
set -euo pipefail

usage() { echo "usage: check-cache.sh [--days N | --all]" >&2; exit 2; }

window=(--all)
label="all time"
while [ "$#" -gt 0 ]; do
  case "$1" in
    --days)
      [ "$#" -ge 2 ] || usage
      case "$2" in ''|*[!0-9]*) usage ;; esac
      window=(--days "$2")
      if [ "$2" = 0 ]; then label="today"; else label="last $2 day(s)"; fi
      shift 2
      ;;
    --all)
      window=(--all)
      label="all time"
      shift
      ;;
    *) usage ;;
  esac
done

command -v opencode2 >/dev/null 2>&1 || { echo "opencode2 not found on PATH" >&2; exit 1; }
command -v jq >/dev/null 2>&1 || { echo "jq not found on PATH" >&2; exit 1; }

stats=$(opencode2 stats "${window[@]}" --cost --json)

jq -r --arg label "$label" '
  .tokens as $t
  | ($t.input + $t.cache.read + $t.cache.write) as $tot
  | ($t.cache.write + $t.input) as $miss
  | "\($label): \(.sessions) sessions, \(.steps) steps"
  + "\ncached input: "
  + (if $tot > 0 then ((10000 * $t.cache.read / $tot | round) / 100 | tostring) else "n/a" end)
  + "%"
  + "\nmiss budget: " + ($miss | tostring) + " current"
  + " vs " + (($t.cache.read * 2 / 98) | floor | tostring) + " at 98%"
  + ", " + (($t.cache.read / 99) | floor | tostring) + " at 99%"
' <<<"$stats"

jq -r '.models[]
  | [(.model | if type == "object" then (if .providerID then .providerID + "/" + .id else .id end) else . end),
     (.tokens.input // 0), (.tokens.cache.read // 0), (.tokens.cache.write // 0)] | @tsv' <<<"$stats" \
  | awk -F'\t' 'BEGIN{printf "%-52s %8s\n","model","cache%"} {t=$2+$3+$4; r=(t>0)?100*$3/t:0; printf "%-52s %7.1f%%\n",$1,r}'
