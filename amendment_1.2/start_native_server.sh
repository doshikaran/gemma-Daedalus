#!/bin/bash
# Amendment 1.2: native macOS arm64 llama.cpp b12020 built from the tag source with GGML_METAL/BLAS/ACCELERATE OFF (pure ggml CPU).
# Same model file and frozen server arguments as agent_calibration.start_server, plus
# --device none / -ngl 0 to forbid GPU offload. Bound to host loopback only.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
BIN="$ROOT/runtime/llama-b12020-src/build-cpu/bin"
LOG="$(cd "$(dirname "${1:-$ROOT/restoration_1.2/native/llama-server.log}")" && pwd)/$(basename "${1:-llama-server.log}")"
cd "$BIN"
exec caffeinate -i -s ./llama-server -m "$ROOT/runtime/gemma-4-E4B_q4_0-it.gguf" -c 32768 -t 4 -tb 4 --parallel 1 \
  --reasoning-budget 128 --host 127.0.0.1 --port 18090 --no-ui --device none -ngl 0 >"$LOG" 2>&1
