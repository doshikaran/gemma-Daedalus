"""Synthetic-only multi-turn check of the frozen runner against the amendment 1.2 server.

Uses the unmodified run_study.interact/request/agent_environment with the frozen system
prompt, common prompt template and protocol budgets, on a synthetic packaging repo (no
historical task text, not a main-study episode). Also verifies prefix caching with a
raw-timings probe (llama.cpp reports cached vs newly evaluated prompt tokens).

Usage (inside the container, from ROOT): python3 amendment_1.2/synthetic_runner_check.py
"""
import json
import pathlib
import subprocess
import sys
import time
import urllib.request
import uuid

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from run_study import agent_environment, git, interact, request  # noqa: E402

CONTRACT = ('Synthetic calibration package `calmsg`: `calmsg.message()` must return the text of the '
            'bundled `message.txt` when the package is installed from a built wheel or from an sdist-built '
            'wheel, as well as from source. Fix the packaging so that holds.')
FILES = {
    'pyproject.toml': '[build-system]\nrequires=["setuptools>=68","wheel"]\nbuild-backend="setuptools.build_meta"\n'
                      '[project]\nname="calibration-message"\nversion="0.0.1"\n[tool.setuptools.packages.find]\nwhere=["src"]\n',
    'src/calmsg/__init__.py': 'from importlib.resources import files\ndef message():\n'
                              '    return files(__package__).joinpath("message.txt").read_text().strip()\n',
    'src/calmsg/message.txt': 'runner-calibration-482\n',
}


def raw(messages, max_tokens):
    payload = {'messages': messages, 'temperature': 0.2, 'seed': 19, 'max_tokens': max_tokens,
               'chat_template_kwargs': {'enable_thinking': True}}
    req = urllib.request.Request('http://127.0.0.1:18090/v1/chat/completions', data=json.dumps(payload).encode(),
                                 headers={'Content-Type': 'application/json'})
    start = time.monotonic()
    with urllib.request.urlopen(req, timeout=600) as response:
        data = json.load(response)
    return {'seconds': time.monotonic() - start, 'usage': data.get('usage'), 'timings': data.get('timings')}


def main():
    protocol = json.loads((ROOT / 'protocol.json').read_text())
    out = ROOT / 'restoration_1.2' / 'synthetic_runner' / uuid.uuid4().hex[:8]
    repo = out / 'repo'
    for rel, body in FILES.items():
        (repo / rel).parent.mkdir(parents=True, exist_ok=True)
        (repo / rel).write_text(body)
    git(repo, 'init', '-q'); git(repo, 'add', '.'); git(repo, 'commit', '-qm', 'synthetic baseline')
    system = (ROOT / 'prompts/system.txt').read_text()
    prompt = (ROOT / 'prompts/common.txt').read_text().replace('{{TASK}}', CONTRACT)
    messages = [{'role': 'system', 'content': system}, {'role': 'user', 'content': prompt}]
    env = agent_environment('synthetic-calibration')
    started = time.monotonic()
    calls, stop, tokens = interact(repo, messages, 19, protocol, env, request, out / 'calls.json')
    elapsed = time.monotonic() - started
    per_call = [{'step': c['step'], 'prompt_tokens': c['response']['usage'].get('prompt_tokens'),
                 'completion_tokens': c['response']['usage'].get('completion_tokens'),
                 'cached_tokens': (c['response']['usage'].get('prompt_tokens_details') or {}).get('cached_tokens'),
                 'seconds': round(c['response']['seconds'], 2), 'finish': c['response'].get('finish_reason'),
                 'format_error': bool(c.get('format_error')), 'command': (c.get('command') or '')[:120]}
                for c in calls]
    # Prefix-cache probe: same long prefix twice, then the prefix extended by one turn.
    filler = '\n'.join(f'Synthetic log line {i}: build step {i % 13} finished.' for i in range(300))
    base = [{'role': 'system', 'content': system}, {'role': 'user', 'content': filler + '\nReply with COMPLETE.'}]
    cold = raw(base, 64)
    warm = raw(base, 64)
    extended = raw(base + [{'role': 'assistant', 'content': 'COMPLETE'},
                           {'role': 'user', 'content': 'Tool result: {"returncode": 0}'}], 64)
    probe = {'cold': cold, 'repeat_same_prefix': warm, 'extended_by_one_turn': extended,
             'cache_effective': (warm['timings'] or {}).get('prompt_n', 1e9) < (cold['timings'] or {}).get('prompt_n', 0)
                                and (extended['timings'] or {}).get('prompt_n', 1e9) < (cold['timings'] or {}).get('prompt_n', 0)}
    result = {'synthetic_only': True, 'historical_task_text': False, 'main_study': False,
              'stop': stop, 'generated_tokens': tokens, 'calls': len(calls), 'interaction_seconds': elapsed,
              'per_call': per_call, 'prefix_cache_probe': probe,
              'patch': subprocess.run(['git', 'diff', 'HEAD'], cwd=repo, capture_output=True, text=True).stdout[-3000:]}
    (out / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({k: result[k] for k in ['stop', 'generated_tokens', 'calls', 'interaction_seconds']}))
    for row in per_call:
        print(json.dumps(row))
    print(json.dumps({'prefix_cache': {k: (v['timings'] or {}).get('prompt_n') if isinstance(v, dict) else v
                                       for k, v in probe.items()},
                      'cache_n': {k: (v['timings'] or {}).get('cache_n') for k, v in probe.items() if isinstance(v, dict)}}))
    print('output:', out)


if __name__ == '__main__':
    main()
