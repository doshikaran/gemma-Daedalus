#!/bin/bash
# Amendment 1.4 host-side orchestration: power watcher, fresh native server + forwarder,
# then the amendment 1.4 controller (detached). Use --resume to retain completed episodes.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"; cd "$ROOT"
pmset -g batt | grep -q "AC Power" || { echo "Refusing to start: not on AC power"; exit 1; }
mkdir -p logs/amendment_1.4
pkill -f "amendment_1.4/power_watch.sh" || true
(nohup amendment_1.4/power_watch.sh >/dev/null 2>&1 &)
pkill -f "gemma-4-E4B_q4_0-it.gguf" || true; sleep 2
STAMP=$(date -u +%Y%m%dT%H%M%SZ)
(nohup amendment_1.2/start_native_server.sh "$ROOT/logs/amendment_1.4/native-server-main-$STAMP.log" >/dev/null 2>&1 &)
for i in $(seq 120); do curl -s 127.0.0.1:18090/health | grep -q ok && break; sleep 1; done
limactl start daedalus --tty=false >/dev/null 2>&1 || true
limactl shell daedalus -- sudo docker start daedalus >/dev/null
limactl shell daedalus -- sudo docker exec daedalus pgrep -f endpoint_forwarder.py >/dev/null || \
  limactl shell daedalus -- sudo docker exec -d daedalus bash -c 'cd /workspace/scratch/93af20bbcd93/packaging_study && exec python3 amendment_1.2/endpoint_forwarder.py >> logs/amendment_1.2/endpoint-forwarder.log 2>&1'
sleep 5
limactl shell daedalus -- sudo docker exec -d daedalus bash -c "cd /workspace/scratch/93af20bbcd93/packaging_study && exec python3 amendment_1.4/run_batch_native_1_4.py $* >> logs/amendment_1.4/main-batch-$STAMP.log 2>&1"
echo "started; controller log: logs/amendment_1.4/main-batch-$STAMP.log; status: Experiment_Status.md"
