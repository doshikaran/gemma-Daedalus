#!/bin/bash
# Amendment 1.6 host power watcher: power source, battery percent and Low Power Mode every
# 20 s for the controller's battery-aware guard (amendment_1.6/run_batch_native_1_6.py).
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
OUT="$ROOT/logs/amendment_1.6/power_state.json"
while true; do
  b=$(pmset -g batt)
  if echo "$b" | grep -q "AC Power"; then src=AC; else src=BATTERY; fi
  pct=$(echo "$b" | grep -oE '[0-9]+%' | head -1 | tr -d '%')
  lpm=$(pmset -g | awk '/lowpowermode/ {print $2}')
  printf '{"source": "%s", "percent": %s, "lowpowermode": %s, "epoch": %s, "utc": "%s"}\n' "$src" "${pct:-null}" "${lpm:-null}" "$(date +%s)" "$(date -u +%FT%TZ)" > "$OUT.tmp"
  mv "$OUT.tmp" "$OUT"
  sleep 20
done
