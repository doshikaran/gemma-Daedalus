"""Read-only evidence extraction for the RQ1/RQ2 paper audit.

For every main_runs/<episode>/ it reads result.json, final.patch and calls.json
(never writes there) and emits paper_audit/evidence/<episode>.json with:
  - frozen grade outcome per stage (source / wheel / sdist-wheel) incl. build/install returncodes
  - patch file inventory, split into preparation-common, build debris and agent edits
  - every agent command with a heuristic first-pass route/action tag (to be reviewed)
  - the final model message, verbatim
Heuristic tags are a first pass only; final labels are assigned in audit_table.csv
after review, with rationale.

Usage: python3 paper_audit/tools/extract_evidence.py
"""
import collections
import json
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parents[2]
OUT = ROOT / 'paper_audit' / 'evidence'
DEBRIS = re.compile(r'(^|/)(dist|build|__pycache__|\.pytest_cache|node_modules|\.venv[^/]*|venv[^/]*|\.tox|'
                    r'[^/]*\.egg-info|\.uv-cache)(/|$)|\.(whl|pyc)$|\.tar\.gz$')
TEST = re.compile(r'(^|/)(tests?|testing)/|(^|/)test_[^/]*\.py$|_test\.py$|(^|/)conftest\.py$')


def parse_patch(data):
    files = []
    for chunk in re.split(rb'(?m)^(?=diff --git )', data):
        if not chunk.startswith(b'diff --git '):
            continue
        head = chunk.split(b'\n', 1)[0].decode('utf-8', 'replace')
        m = re.match(r'diff --git a/(.*) b/(.*)$', head)
        path = m.group(2) if m else head
        status = 'new' if b'\nnew file mode' in chunk[:400] else 'deleted' if b'\ndeleted file mode' in chunk[:400] else 'modified'
        idx = re.search(rb'(?m)^index ([0-9a-f]+)\.\.([0-9a-f]+)', chunk)
        binary = b'GIT binary patch' in chunk or b'Binary files' in chunk
        added = removed = 0
        added_lines = []
        if not binary:
            for line in chunk.split(b'\n'):
                if line.startswith(b'+') and not line.startswith(b'+++'):
                    added += 1
                    if len(added_lines) < 400:
                        added_lines.append(line[1:].decode('utf-8', 'replace'))
                elif line.startswith(b'-') and not line.startswith(b'---'):
                    removed += 1
        files.append({'path': path, 'status': status, 'post_blob': idx.group(2).decode() if idx else None,
                      'binary': binary, 'added': added, 'removed': removed, 'bytes': len(chunk),
                      'debris': bool(DEBRIS.search(path)), 'test_file': bool(TEST.search(path)),
                      '_added_lines': added_lines})
    return files


def tag_command(cmd):
    c = cmd
    tags = []
    if re.search(r'\buv build\b|python3? -m build\b|pip3? wheel\b|setup\.py (sdist|bdist_wheel)|hatch build|poetry build', c):
        if re.search(r'--sdist\b|setup\.py sdist', c) and not re.search(r'--wheel\b', c):
            tags.append('build:sdist')
        elif re.search(r'\.tar\.gz\b', c) or re.search(r'--wheel\b', c) and re.search(r'sdist|extract|tmp', c):
            tags.append('build:wheel-from-sdist?')
        elif re.search(r'--wheel\b|bdist_wheel|pip3? wheel', c):
            tags.append('build:wheel')
        else:
            tags.append('build:sdist+wheel')
    if re.search(r'\b(uv )?pip3? install\b', c):
        if re.search(r'\.whl\b', c):
            tags.append('install:wheel')
        elif re.search(r'\.tar\.gz\b', c):
            tags.append('install:sdist')
        elif re.search(r'install\s+(-e\s+|--editable\s+)', c):
            tags.append('install:editable')
        elif re.search(r'install[^|;&]*\s\.(\s|$)', c):
            tags.append('install:source-dir')
        else:
            tags.append('install:other')
    if re.search(r'\btar\b.*-x|\bunzip\b|zipfile|tarfile', c):
        tags.append('inspect-or-extract-archive')
    if re.search(r'python3?\s+(-I\s+)?-c\b|python3?\s+-m\s+(?!build|pip|pytest|venv)\w|python3? [\w./-]+\.py', c):
        tags.append('run:python')
    if re.search(r'\bpytest\b|-m unittest|\btox\b(?! -)', c):
        tags.append('run:tests')
    if re.search(r'__file__|importlib\.util\.find_spec|\.origin\b|site-packages|files\(', c):
        tags.append('origin-check?')
    if re.search(r'\bcd\s+/(tmp|var|opt|root|home)|--target\s+/|/tmp/', c):
        tags.append('outside-checkout?')
    if re.search(r'\bsed\s+-i|cat\s*>|>\s*[\w./-]+\.(py|toml|cfg|in|json|txt|md)|apply_patch|python3? - <<|tee\s', c):
        tags.append('edit?')
    if not tags:
        tags.append('inspect/other')
    return tags


def summarize_grade(grade):
    out = {}
    for row in grade.get('rows', []):
        steps = {}
        for k in ['preparation', 'build', 'install', 'sdist_build', 'wheel_build', 'probe']:
            v = row.get(k)
            if isinstance(v, dict):
                steps[k] = {'returncode': v.get('returncode'), 'tail': (v.get('stderr') or v.get('stdout') or '')[-400:]}
        out[row['stage']] = {'pass': row['pass'], 'steps': steps}
    return out


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    episodes = sorted(p for p in (ROOT / 'main_runs').iterdir() if (p / 'result.json').exists())
    patches = {e.name: parse_patch((e / 'final.patch').read_bytes()) for e in episodes}
    by_task = collections.defaultdict(list)
    results = {}
    for e in episodes:
        r = json.loads((e / 'result.json').read_text())
        results[e.name] = r
        by_task[r['task']].append(e.name)
    # A (path, post-blob) present in every episode of a task is release preparation (e.g. pyfiglet fonts copy).
    common = {}
    for task, names in by_task.items():
        sets = [{(f['path'], f['post_blob']) for f in patches[n]} for n in names]
        common[task] = set.intersection(*sets)
    for e in episodes:
        r = results[e.name]
        files = patches[e.name]
        for f in files:
            f['preparation_common'] = (f['path'], f['post_blob']) in common[r['task']]
        agent_files = [f for f in files if not f['preparation_common'] and not f['debris']]
        calls = r['calls']
        commands = []
        for c in calls:
            res = c.get('result') or {}
            if 'command' in c:
                commands.append({'step': c['step'], 'command': c['command'], 'tags': tag_command(c['command']),
                                 'returncode': res.get('returncode'), 'timeout': res.get('timeout'),
                                 'rejected': res.get('rejected'), 'output_tail': (res.get('output') or res.get('reason') or '')[-700:]})
        final = calls[-1]['response'].get('content', '') if calls else ''
        ev = {'episode_id': e.name, 'task': r['task'], 'condition': r['condition'], 'seed': r['seed'], 'order': r['order'],
              'scope': r['scope'], 'stop': r['stop'], 'calls': len(calls), 'commands': len(commands),
              'format_errors': sum(1 for c in calls if c.get('format_error')),
              'generated_tokens': r['generated_tokens'], 'generated_token_accounting': r.get('generated_token_accounting'),
              'interaction_wall_seconds': r['interaction_wall_seconds'], 'patch_sha256': r['patch_sha256'],
              'artifact_contract_pass': r.get('artifact_contract_pass'),
              'pattern': ''.join('P' if row['pass'] else 'F' for row in r['grade']['rows']),
              'grade': summarize_grade(r['grade']),
              'patch': {'files_total': len(files), 'preparation_common': sum(f['preparation_common'] for f in files),
                        'debris': sum(f['debris'] and not f['preparation_common'] for f in files),
                        'agent_files': [{k: v for k, v in f.items() if k != '_added_lines'} for f in agent_files],
                        'agent_added_lines': {f['path']: f['_added_lines'][:120] for f in agent_files if not f['binary']},
                        'test_files_touched': [f['path'] for f in agent_files if f['test_file']],
                        'test_files_deleted': [f['path'] for f in agent_files if f['test_file'] and f['status'] == 'deleted']},
              'commands_detail': commands,
              'final_message': final,
              'final_message_is_complete': bool(re.match(r'^COMPLETE(?:\s|$)', final.strip())) if final else False,
              'sources': {k: f'main_runs/{e.name}/{k}' for k in ['result.json', 'final.patch', 'calls.json', 'trajectory.json', 'prompt.txt', 'final-source.tar.gz']}}
        (OUT / f'{e.name}.json').write_text(json.dumps(ev, indent=2) + '\n')
    print(len(episodes), 'episodes extracted')


if __name__ == '__main__':
    main()
