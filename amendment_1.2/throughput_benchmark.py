"""Synthetic-only inference throughput check for the restored runtime (no historical task text).

Starts llama-server with the frozen protocol arguments (same as agent_calibration.start_server)
but logs to restoration_1.2/, sends synthetic prompts of increasing length and records
llama.cpp's own prefill/decode timings. Compare with the original v1.0/v1.1 traces
(about 3-9 generated tokens/s end to end, including prefill).
"""
import json, os, pathlib, subprocess, sys, time, urllib.request
ROOT = pathlib.Path(__file__).resolve().parent.parent
protocol = json.loads((ROOT / 'protocol.json').read_text())
binary = ROOT / 'runtime/llama-b12020'
args = [str(binary / 'llama-server'), '-m', str(ROOT / 'runtime' / protocol['model']['filename']), '-c', '32768', '-t', '4', '-tb', '4',
        '--parallel', '1', '--reasoning-budget', '128', '--host', '127.0.0.1', '--port', '18090', '--no-ui']
out = ROOT / 'restoration_1.2' / 'throughput'; out.mkdir(parents=True, exist_ok=True)
log = (out / 'llama-server.log').open('w')
p = subprocess.Popen(args, cwd=binary, env={**os.environ, 'LD_LIBRARY_PATH': str(binary)}, stdout=log, stderr=log)
try:
    for _ in range(600):
        try:
            urllib.request.urlopen('http://127.0.0.1:18090/health', timeout=1); break
        except Exception:
            if p.poll() is not None: raise SystemExit('server exited')
            time.sleep(.5)
    filler = ' '.join(f'Line {i}: the quick brown fox jumps over the lazy dog near river {i % 17}.' for i in range(260))
    rows = []
    for label, text in [('short', 'Write a bash command that lists files, in one bash code block.'),
                        ('~3k', filler + '\nSummarise the pattern above in one bash comment inside one bash code block.'),
                        ('~6k', filler + filler + '\nCount the lines above with a bash one-liner in one bash code block.')]:
        payload = {'messages': [{'role': 'system', 'content': 'You are a synthetic benchmark.'}, {'role': 'user', 'content': text}],
                   'temperature': 0.2, 'seed': 7, 'max_tokens': 512, 'chat_template_kwargs': {'enable_thinking': True}}
        t = time.monotonic()
        raw = json.load(urllib.request.urlopen(urllib.request.Request('http://127.0.0.1:18090/v1/chat/completions',
              data=json.dumps(payload).encode(), headers={'Content-Type': 'application/json'}), timeout=900))
        sec = time.monotonic() - t; u = raw['usage']; tm = raw.get('timings', {})
        rows.append({'label': label, 'prompt_tokens': u['prompt_tokens'], 'completion_tokens': u['completion_tokens'], 'seconds': sec,
                     'end_to_end_generated_per_s': u['completion_tokens'] / sec,
                     'prefill_per_s': tm.get('prompt_per_second'), 'decode_per_s': tm.get('predicted_per_second')})
        print(json.dumps(rows[-1]), flush=True)
    (out / 'throughput.json').write_text(json.dumps({'args': args, 'rows': rows, 'historical_task_text': False}, indent=2) + '\n')
finally:
    p.terminate(); p.wait(timeout=20); log.close()
