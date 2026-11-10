#!/bin/bash
# Amendment 1.5 host load watcher: writes the macOS load averages every 15 s for the
# controller's pre-episode gate (amendment_1.5/run_batch_native_1_5.py).
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
OUT="$ROOT/logs/amendment_1.5/host_load.json"
while true; do
  read -r l1 l5 l15 <<< "$(sysctl -n vm.loadavg | tr -d '{}')"
  printf '{"load1": %s, "load5": %s, "load15": %s, "epoch": %s, "utc": "%s"}\n' "$l1" "$l5" "$l15" "$(date +%s)" "$(date -u +%FT%TZ)" > "$OUT.tmp"
  mv "$OUT.tmp" "$OUT"
  sleep 15
done
