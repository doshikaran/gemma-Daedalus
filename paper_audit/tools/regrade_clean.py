"""Sensitivity regrade: the frozen grader on every retained final source, in a given container.

Audit-only. Extracts main_runs/<ep>/final-source.tar.gz to paper_audit/regrade/<label>/<ep>/
and calls the unmodified run_study.evaluate (replay._replay / replay_pytesthtml.main) with the
same offline environment run_batch sets. Compares the source/wheel/sdist-wheel pattern with
the recorded result.json. Never writes to main_runs/ or results/; no model calls.

Usage (inside a container, from ROOT): python3 paper_audit/tools/regrade_clean.py LABEL [EPISODE ...]
"""
import datetime
import json
import os
import pathlib
import sys
import tarfile

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

import run_study  # noqa: E402


def main():
    label, only = sys.argv[1], set(sys.argv[2:])
    protocol = json.loads((ROOT / 'protocol.json').read_text())
    os.environ.update(UV_OFFLINE='1', npm_config_offline='true', npm_config_cache=str(ROOT / '.npm-cache'),
                      NPM_CONFIG_CACHE=str(ROOT / '.npm-cache'), UV_CACHE_DIR=str(ROOT / '.uv-cache'), CC='gcc', CXX='g++',
                      CALIBRATION_MODEL=protocol['model']['filename'])
    run_study.verify_freeze()
    out = ROOT / 'paper_audit' / 'regrade' / label
    out.mkdir(parents=True, exist_ok=True)
    rows = []
    for ep in sorted(p for p in (ROOT / 'main_runs').iterdir() if (p / 'result.json').exists()):
        if only and ep.name not in only:
            continue
        record = json.loads((ep / 'result.json').read_text())
        recorded = ''.join('P' if r['pass'] else 'F' for r in record['grade']['rows'])
        work = out / ep.name
        work.mkdir()
        with tarfile.open(ep / 'final-source.tar.gz') as archive:
            archive.extractall(work, filter='tar')
        started = datetime.datetime.now(datetime.timezone.utc).isoformat()
        try:
            grade = run_study.evaluate(record['task'], work / 'final-source', work / 'grading')
            observed = ''.join('P' if r['pass'] else 'F' for r in grade['rows'])
            error = None
            (work / 'grade.json').write_text(json.dumps(grade, indent=2) + '\n')
        except Exception as exc:
            observed, error = None, repr(exc)
        run_study.verify_freeze()
        row = {'episode_id': ep.name, 'task': record['task'], 'recorded': recorded, 'observed': observed,
               'match': observed == recorded, 'error': error, 'started_utc': started}
        rows.append(row)
        print(json.dumps(row), flush=True)
    summary = {'label': label, 'model_calls': 0, 'episodes': len(rows), 'matches': sum(r['match'] for r in rows),
               'finished_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'rows': rows}
    (out / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n')
    print('MATCH', summary['matches'], '/', summary['episodes'])


if __name__ == '__main__':
    main()
