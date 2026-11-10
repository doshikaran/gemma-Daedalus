#!/bin/bash
# Amendment 1.4 host power watcher: writes the macOS power source every 20 s for the
# controller's between-episode guard (amendment_1.4/run_batch_native_1_4.py).
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
OUT="$ROOT/logs/amendment_1.4/power_state.json"
while true; do
  b=$(pmset -g batt)
  if echo "$b" | grep -q "AC Power"; then src=AC; else src=BATTERY; fi
  pct=$(echo "$b" | grep -oE '[0-9]+%' | head -1 | tr -d '%')
  printf '{"source": "%s", "percent": %s, "epoch": %s, "utc": "%s"}\n' "$src" "${pct:-null}" "$(date +%s)" "$(date -u +%FT%TZ)" > "$OUT.tmp"
  mv "$OUT.tmp" "$OUT"
  sleep 20
done
