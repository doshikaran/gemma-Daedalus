"""Re-run the frozen affected/reference artifact controls without touching frozen evidence.

Calls the unmodified replay._replay / replay_pytesthtml.main graders, but directs
work trees and result records to restoration_1.2/controls/<label>/ instead of
results/<task>-<arm>.json (which FREEZE.json protects). Compares observed P/F
states with task_manifest.json. No model calls.

Usage (inside the container, from ROOT):
  python3 amendment_1.2/control_replay.py LABEL [--offline] [--task ID ...]
"""
import argparse
import concurrent.futures
import datetime
import fcntl
import json
import os
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from replay import _replay  # noqa: E402
import replay_pytesthtml  # noqa: E402


def run(task, out):
    if task == 'pytest-html-npm':
        # replay_pytesthtml.main takes its own per-task lock.
        records = replay_pytesthtml.main(output_root=out / 'work')
    else:
        with (ROOT / 'locks' / (task + '.lock')).open('w') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            records = _replay(task, output_root=out / 'work')
    for record in records:
        path = out / 'records' / f"{task}-{record['arm']}.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(record, indent=2) + '\n')
    return records


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('label')
    parser.add_argument('--offline', action='store_true')
    parser.add_argument('--task', action='append')
    args = parser.parse_args()
    if args.offline:
        # Same offline cache settings the main runner applies (run_batch.main).
        os.environ.update(UV_OFFLINE='1', npm_config_offline='true',
                          npm_config_cache=str(ROOT / '.npm-cache'), NPM_CONFIG_CACHE=str(ROOT / '.npm-cache'),
                          UV_CACHE_DIR=str(ROOT / '.uv-cache'), CC='gcc', CXX='g++')
    tasks = json.loads((ROOT / 'task_manifest.json').read_text())['tasks']
    if args.task:
        tasks = [t for t in tasks if t['id'] in args.task]
    out = ROOT / 'restoration_1.2' / 'controls' / args.label
    out.mkdir(parents=True, exist_ok=False)
    started = datetime.datetime.now(datetime.timezone.utc).isoformat()
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
        results = dict(zip([t['id'] for t in tasks], pool.map(lambda t: run(t['id'], out), tasks)))
    rows = []
    for task in tasks:
        for record in results[task['id']]:
            observed = ''.join('P' if x['pass'] else 'F' for x in record['rows'])
            expected = task['states'][record['arm']]
            rows.append({'task': task['id'], 'arm': record['arm'], 'run_id': record['run_id'],
                         'expected': expected, 'observed': observed, 'match': observed == expected})
    summary = {'label': args.label, 'offline': args.offline, 'started_utc': started,
               'finished_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
               'model_calls': 0, 'rows': rows, 'all_match': all(r['match'] for r in rows)}
    (out / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n')
    for r in rows:
        print(f"{r['task']:20} {r['arm']:9} expected {r['expected']} observed {r['observed']} {'OK' if r['match'] else 'MISMATCH'}")
    print('ALL MATCH' if summary['all_match'] else 'MISMATCHES PRESENT')


if __name__ == '__main__':
    main()
