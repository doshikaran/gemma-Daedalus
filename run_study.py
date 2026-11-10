"""Frozen episode runner. No historical model episodes are executed on import.

Use --plan for the randomized grid; --execute explicitly starts the main study.
Shell access is instruction-bounded, not an OS security sandbox.
"""
import argparse
import hashlib
import json
import os
import pathlib
import random
import re
import shutil
import signal
import subprocess
import sys
import time
import urllib.request
import urllib.error
import uuid

from replay import ROOT, _replay, build, cmd
import replay_pytesthtml


def sha(path):
    return hashlib.sha256(pathlib.Path(path).read_bytes()).hexdigest()


def tree_digest(base):
    h = hashlib.sha256()
    base = pathlib.Path(base)
    for path in sorted(base.rglob('*')):
        if '.git' in path.relative_to(base).parts:
            continue
        if path.is_symlink():
            value = 'symlink:' + os.readlink(path)
        elif path.is_file():
            value = 'file:' + sha(path)
        else:
            continue
        h.update((path.relative_to(base).as_posix() + '\0' + value + '\n').encode())
    return h.hexdigest()


def verify_freeze():
    manifest = json.loads((ROOT / 'FREEZE.json').read_text())
    for name, digest in manifest['files'].items():
        if sha(ROOT / name) != digest:
            raise RuntimeError('Frozen input changed: ' + name)
    return manifest


def grid(protocol, tasks):
    rows = [{'task': task['id'], 'condition': condition, 'seed': seed}
            for task in tasks for condition in ['A', 'B']
            for seed in protocol['attempt_seeds']]
    random.Random(protocol['ordering_seed']).shuffle(rows)
    for i, row in enumerate(rows):
        row['order'] = i
        row['episode_id'] = f"{i:02d}-{row['task']}-{row['condition']}-{row['seed']}"
    return rows


def parse_command(content):
    if re.match(r'^COMPLETE(?:\s|$)', content.strip()):
        return None
    matches = re.findall(r'```(?:bash|sh)\s*\n(.*?)```', content, re.S)
    if len(matches) != 1:
        raise ValueError('Return exactly one bash code block, or COMPLETE after testing.')
    return matches[0].strip()


def shell(command, cwd, env, timeout):
    # Timeout includes child processes. The blocklist is an operational guard,
    # not a claim that arbitrary shell commands are securely contained.
    if any(s in command for s in ['../', 'http://', 'https://', 'curl ', 'wget ', 'rm -rf /']):
        return {'rejected': True, 'reason': 'Work inside the repository; no network services.'}
    start = time.monotonic()
    with (cwd / '.agent-command-output').open('w+b') as out:
        process = subprocess.Popen(command, shell=True, cwd=cwd, env=env,
                                   stdout=out, stderr=subprocess.STDOUT,
                                   start_new_session=True, executable='/bin/bash')
        timed_out = False
        try:
            process.wait(timeout=max(.1, timeout))
        except subprocess.TimeoutExpired:
            timed_out = True
            os.killpg(process.pid, signal.SIGKILL)
            process.wait()
        out.flush()
        out.seek(max(0, out.tell() - 4000))
        text = out.read().decode('utf-8', errors='replace')
    (cwd / '.agent-command-output').unlink(missing_ok=True)
    return {'returncode': process.returncode, 'output': text,
            'timeout': timed_out, 'seconds': time.monotonic() - start}


def request(messages, seed, remaining_tokens, remaining_seconds, protocol):
    payload = {'messages': messages,
               'temperature': protocol['temperature'], 'seed': seed,
               'max_tokens': min(protocol['response_tokens'], remaining_tokens),
               'chat_template_kwargs': {'enable_thinking': True}}
    started = time.monotonic()
    req = urllib.request.Request(protocol['endpoint'] + '/v1/chat/completions',
          data=json.dumps(payload).encode(), headers={'Content-Type': 'application/json'})
    with urllib.request.urlopen(req, timeout=min(240, remaining_seconds)) as response:
        raw = json.load(response)
    choice = raw['choices'][0]
    if not raw.get('usage', {}).get('completion_tokens'):
        raise RuntimeError('Missing completion-token accounting')
    return {'content': re.sub(r'<think>.*?</think>', '', choice['message'].get('content') or '', flags=re.S),
            'finish_reason': choice['finish_reason'], 'usage': raw['usage'],
            'seconds': time.monotonic() - started}


def interact(repo, messages, seed, protocol, env, requester=request, trace_path=None):
    start = time.monotonic()
    calls, generated = [], 0
    for step in range(protocol['max_actions']):
        remaining_time = protocol['wall_seconds'] - (time.monotonic() - start)
        remaining_tokens = protocol['episode_generated_tokens'] - generated
        if remaining_time <= 0 or remaining_tokens <= 0:
            return calls, 'budget', generated
        try:
            response = requester(messages, seed, remaining_tokens, remaining_time, protocol)
        except (TimeoutError, urllib.error.URLError) as exc:
            # An enforced episode deadline is a budget outcome, not an API
            # infrastructure failure. Partial generation has unknown token cost.
            if time.monotonic()-start >= protocol['wall_seconds']:
                calls.append({'step':step,'episode_deadline':True,'partial_response_tokens_unknown':True,
                  'response':{'content':'','usage':{'completion_tokens':0},'finish_reason':'episode_deadline'}})
                if trace_path:trace_path.write_text(json.dumps(calls,indent=2)+'\n')
                return calls,'budget',generated
            raise
        generated += response['usage']['completion_tokens']
        row = {'step': step, 'response': response}
        calls.append(row)
        if trace_path:
            trace_path.write_text(json.dumps(calls, indent=2) + '\n')
        messages.append({'role': 'assistant', 'content': response['content']})
        try:
            command = parse_command(response['content'])
        except ValueError as exc:
            row['format_error'] = str(exc)
            if trace_path:
                trace_path.write_text(json.dumps(calls, indent=2) + '\n')
            messages.append({'role': 'user', 'content': str(exc)})
            continue
        if command is None:
            return calls, 'completion_claim', generated
        remaining_time = protocol['wall_seconds'] - (time.monotonic() - start)
        if remaining_time <= 0:
            return calls, 'budget', generated
        row['command'] = command
        row['result'] = shell(command, repo, env, min(protocol['command_seconds'], remaining_time))
        if trace_path:
            trace_path.write_text(json.dumps(calls, indent=2) + '\n')
        messages.append({'role': 'user', 'content': 'Tool result: ' + json.dumps(row['result'])})
    return calls, 'action_limit', generated


def git(repo, *args):
    done = subprocess.run(['git', '-c', 'user.name=Research runner', '-c',
                           'user.email=runner@example.invalid', *args], cwd=repo,
                          capture_output=True, check=True)
    return done.stdout


def prepare(repo, task):
    if task == 'pyfiglet-154':
        for folder in ['fonts-standard', 'fonts-contrib']:
            shutil.copytree(repo / 'pyfiglet' / folder, repo / 'pyfiglet/fonts', dirs_exist_ok=True)
    elif task == 'tox-sdist':
        result = build(repo, repo / '.agent-source-preparation')
        if result['returncode']:
            raise RuntimeError('tox version preparation failed: ' + json.dumps(result))
    elif task == 'pytest-html-npm':
        env = os.environ.copy()
        env['npm_config_cache'] = str(ROOT / '.npm-cache')
        env['NPM_CONFIG_CACHE'] = str(ROOT / '.npm-cache')
        for args in [['npm', 'ci', '--ignore-scripts', '--no-audit', '--no-fund'], ['npm', 'run', 'build']]:
            result = cmd(args, repo, env, timeout=180)
            if result['returncode']:
                raise RuntimeError('JavaScript preparation failed: ' + json.dumps(result))


def agent_environment(task):
    extras = ['pixcull-deps'] if task == 'pixcull-sdist' else ['tox-deps'] if task == 'tox-sdist' else ['pytesthtml-deps'] if task == 'pytest-html-npm' else []
    env = {key: os.environ[key] for key in ['PATH', 'HOME', 'TMPDIR', 'LANG', 'LC_ALL'] if key in os.environ}
    constraints = ROOT / ('build-constraints-tox.txt' if task == 'tox-sdist' else 'build-constraints.txt')
    env.update(UV_OFFLINE='1', UV_CACHE_DIR=str(ROOT / '.uv-cache'),
               UV_PYTHON=sys.executable, UV_BUILD_CONSTRAINT=str(constraints),
               npm_config_offline='true', npm_config_cache=str(ROOT / '.npm-cache'), NPM_CONFIG_CACHE=str(ROOT / '.npm-cache'),
               SETUPTOOLS_SCM_PRETEND_VERSION='0.0.0+audit', CC='gcc', CXX='g++',
               PYTHONPATH=os.pathsep.join(str(ROOT / 'runtime' / x) for x in extras + ['probe-deps']))
    return env


def snapshot(repo, dest, baseline='HEAD'):
    # Export the final indexed source, excluding ignored build debris. The
    # grader then repeats declared release preparation in fresh source copies.
    git(repo, 'add', '-A')
    patch = git(repo, 'diff', '--cached', '--binary', baseline)
    dest.mkdir()
    git(repo, 'checkout-index', '--all', '--prefix=' + str(dest) + '/')
    return patch


def evaluate(task, candidate, output):
    if task == 'pytest-html-npm':
        return replay_pytesthtml.main(candidate=candidate, output_root=output)[0]
    return _replay(task, candidate=candidate, output_root=output)[0]


def episode(row, task, protocol):
    work = ROOT / 'main_runs' / row['episode_id']
    if work.exists():
        raise RuntimeError('Refusing to overwrite an episode: ' + row['episode_id'])
    work.mkdir(parents=True)
    repo = work / 'repo'
    provenance = json.loads((ROOT / 'sources' / (task['id'] + '-provenance.json')).read_text())
    if tree_digest(provenance['affected']['directory']) != task['affected']['tree_sha256']:
        raise RuntimeError('Affected source tree differs from frozen input')
    shutil.copytree(provenance['affected']['directory'], repo, symlinks=True)
    git(repo, 'init', '-q')
    git(repo, 'add', '--force', '.')
    git(repo, 'commit', '-qm', 'Pinned affected source; no upstream history')
    baseline_commit = git(repo, 'rev-parse', 'HEAD').decode().strip()
    (repo / '.git/info/exclude').write_text('.agent-source-preparation/\n.agent-command-output\n')
    prepare(repo, task['id'])
    prompt = (ROOT / 'prompts/common.txt').read_text().replace('{{TASK}}', task['contract'])
    if row['condition'] == 'B':
        prompt += '\n' + (ROOT / 'prompts/checklist.txt').read_text()
    (work / 'prompt.txt').write_text(prompt)
    system = (ROOT / 'prompts/system.txt').read_text()
    messages = [{'role': 'system', 'content': system}, {'role': 'user', 'content': prompt}]
    # Supply dependency libraries but do not expose reference patches or oracle code.
    env = agent_environment(task['id'])
    (work / 'tool_environment.json').write_text(json.dumps(env, indent=2)+'\n')
    record = {**row, 'run_uuid': uuid.uuid4().hex, 'scope': task['stratum'], 'main_study': True,
              'protocol_version': protocol['version'], 'baseline_commit':baseline_commit}
    interaction_start = time.monotonic()
    try:
        calls, stop, tokens = interact(repo, messages, row['seed'], protocol, env,
                                      trace_path=work / 'calls.json')
        record.update(calls=calls, stop=stop, generated_tokens=tokens)
        record['generated_token_accounting']='lower_bound_partial_timeout' if any(x.get('partial_response_tokens_unknown')for x in calls)else'complete'
    except Exception as exc:
        # Infrastructure errors are never silently regenerated or called model failures.
        record.update(infrastructure_error=repr(exc), stop='infrastructure_error')
        if (work/'calls.json').exists():
            record['calls']=json.loads((work/'calls.json').read_text())
            record['generated_tokens']=sum(x['response']['usage']['completion_tokens'] for x in record['calls'])
    finally:
        record['interaction_wall_seconds']=time.monotonic()-interaction_start
        (work / 'trajectory.json').write_text(json.dumps(record, indent=2) + '\n')
    exported = work / 'final-source'
    patch = snapshot(repo, exported, baseline_commit)
    (work / 'final.patch').write_bytes(patch)
    record['patch_sha256'] = hashlib.sha256(patch).hexdigest()
    # Recheck frozen external graders after the agent has finished.
    verify_freeze()
    try:
        grade = evaluate(task['id'], exported, work / 'grading')
        record['grade'] = grade
        record['artifact_contract_pass'] = all(x['pass'] for x in grade['rows'])
    except Exception as exc:
        record['grading_infrastructure_error'] = repr(exc)
    (work / 'result.json').write_text(json.dumps(record, indent=2) + '\n')
    return record


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--plan', action='store_true')
    parser.add_argument('--execute', action='store_true')
    parser.add_argument('--episode', help='Run only a declared episode ID, preserving its original order')
    args = parser.parse_args()
    verify_freeze()
    protocol = json.loads((ROOT / 'protocol.json').read_text())
    tasks = json.loads((ROOT / 'task_manifest.json').read_text())['tasks']
    rows = grid(protocol, tasks)
    if not args.execute:
        print(json.dumps(rows, indent=2))
        return
    if args.episode:
        rows = [r for r in rows if r['episode_id'] == args.episode]
        if not rows:
            raise SystemExit('Unknown episode ID')
    model = ROOT / 'runtime' / protocol['model']['filename']
    if sha(model) != protocol['model']['sha256']:
        raise RuntimeError('Model digest mismatch')
    os.environ.update(UV_OFFLINE='1', npm_config_offline='true', npm_config_cache=str(ROOT/'.npm-cache'), NPM_CONFIG_CACHE=str(ROOT/'.npm-cache'), UV_CACHE_DIR=str(ROOT/'.uv-cache'), CC='gcc', CXX='g++')
    from agent_calibration import start_server
    os.environ['CALIBRATION_MODEL'] = protocol['model']['filename']
    process, log, server_args = start_server()
    try:
        for row in rows:
            result = episode(row, next(t for t in tasks if t['id'] == row['task']), protocol)
            print(json.dumps({'episode': row['episode_id'], 'pass': result.get('artifact_contract_pass'),
                              'infrastructure_error': result.get('infrastructure_error')}), flush=True)
    finally:
        process.terminate()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()
        log.close()


if __name__ == '__main__':
    main()
