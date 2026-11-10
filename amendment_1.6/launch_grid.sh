#!/bin/bash
# Amendment 1.6 host-side orchestration: battery-aware power and load watchers, fresh native
# server + forwarder, then the amendment 1.6 controller (detached). Use --resume to retain
# completed episodes. Runs on AC, or on battery >= 35% with Low Power Mode off.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"; cd "$ROOT"
pmset -g | awk '/lowpowermode/ {exit $2}' || { echo "Refusing to start: Low Power Mode on"; exit 1; }
pct=$(pmset -g batt | grep -oE '[0-9]+%' | head -1 | tr -d '%')
pmset -g batt | grep -q "AC Power" || [ "${pct:-0}" -ge 35 ] || { echo "Refusing to start: battery below 35%"; exit 1; }
mkdir -p logs/amendment_1.5 logs/amendment_1.6
pkill -f "amendment_1.4/power_watch.sh" || true; pkill -f "amendment_1.6/power_watch.sh" || true
(nohup amendment_1.6/power_watch.sh >/dev/null 2>&1 &)
pkill -f "amendment_1.5/load_watch.sh" || true
(nohup amendment_1.5/load_watch.sh >/dev/null 2>&1 &)
pkill -f "gemma-4-E4B_q4_0-it.gguf" || true; sleep 2
STAMP=$(date -u +%Y%m%dT%H%M%SZ)
(nohup amendment_1.2/start_native_server.sh "$ROOT/logs/amendment_1.6/native-server-main-$STAMP.log" >/dev/null 2>&1 &)
for i in $(seq 120); do curl -s 127.0.0.1:18090/health | grep -q ok && break; sleep 1; done
limactl start daedalus --tty=false >/dev/null 2>&1 || true
limactl shell daedalus -- sudo docker start daedalus >/dev/null
limactl shell daedalus -- sudo docker exec daedalus pgrep -f endpoint_forwarder.py >/dev/null || \
  limactl shell daedalus -- sudo docker exec -d daedalus bash -c 'cd /workspace/scratch/93af20bbcd93/packaging_study && exec python3 amendment_1.2/endpoint_forwarder.py >> logs/amendment_1.2/endpoint-forwarder.log 2>&1'
sleep 25
limactl shell daedalus -- sudo docker exec -d daedalus bash -c "cd /workspace/scratch/93af20bbcd93/packaging_study && exec python3 amendment_1.6/run_batch_native_1_6.py $* >> logs/amendment_1.6/main-batch-$STAMP.log 2>&1"
echo "started; controller log: logs/amendment_1.6/main-batch-$STAMP.log; status: Experiment_Status.md"
