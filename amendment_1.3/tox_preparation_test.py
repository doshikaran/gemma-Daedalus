"""Amendment 1.3 verification: tox preparation under every actual tox episode-directory name.

For each of the six tox-sdist episode IDs in the frozen plan and each source arm
(affected, reference), builds an isolated tree restoration_1.3/tox_prep_tests/<label>/
<arm>/main_runs/<episode_id>/repo exactly as run_study.episode does before prepare
(copy, git init/add/commit, info/exclude), then runs:
  - the frozen run_study.prepare as a negative control (expected to fail), and
  - the amendment 1.3 prepare (expected to succeed and generate src/tox/version.py).
No model server is contacted; model_calls is 0 by construction.

Usage (inside the container, from ROOT): python3 amendment_1.3/tox_preparation_test.py LABEL
"""
import json
import pathlib
import shutil
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'amendment_1.3'))

import run_study  # noqa: E402
import run_batch_native_1_3 as amendment  # noqa: E402


def fresh_repo(source, base):
    repo = base / 'repo'
    shutil.copytree(source, repo, symlinks=True)
    run_study.git(repo, 'init', '-q')
    run_study.git(repo, 'add', '--force', '.')
    run_study.git(repo, 'commit', '-qm', 'Pinned affected source; no upstream history')
    (repo / '.git/info/exclude').write_text('.agent-source-preparation/\n.agent-command-output\n')
    return repo


def main():
    label = sys.argv[1]
    protocol = json.loads((ROOT / 'protocol.json').read_text())
    tasks = json.loads((ROOT / 'task_manifest.json').read_text())['tasks']
    episodes = [r['episode_id'] for r in run_study.grid(protocol, tasks) if r['task'] == 'tox-sdist']
    assert len(episodes) == 6, episodes
    provenance = json.loads((ROOT / 'sources/tox-sdist-provenance.json').read_text())
    out = ROOT / 'restoration_1.3' / 'tox_prep_tests' / label
    out.mkdir(parents=True, exist_ok=False)
    rows = []
    for arm in ['affected', 'reference']:
        for episode_id in episodes:
            row = {'arm': arm, 'episode_id': episode_id}
            for variant, function in [('frozen_prepare', amendment.frozen_prepare), ('amendment_1_3_prepare', amendment.prepare)]:
                repo = fresh_repo(provenance[arm]['directory'], out / variant / arm / 'main_runs' / episode_id)
                try:
                    function(repo, 'tox-sdist')
                    error = None
                except RuntimeError as exc:
                    error = str(exc)[:600]
                version = repo / 'src/tox/version.py'
                status = run_study.git(repo, 'status', '--porcelain').decode()
                row[variant] = {'ok': error is None, 'error': error, 'version_py': version.exists(),
                                'version_text': version.read_text()[:300] if version.exists() else None,
                                'wheel_built': sorted(p.name for p in (repo / '.agent-source-preparation').glob('*.whl')),
                                'git_status_after_prepare': status}
            row['pass'] = (not row['frozen_prepare']['ok'] and row['amendment_1_3_prepare']['ok']
                           and row['amendment_1_3_prepare']['version_py'])
            rows.append(row)
            print(json.dumps({'arm': arm, 'episode': episode_id, 'frozen_ok': row['frozen_prepare']['ok'],
                              'fixed_ok': row['amendment_1_3_prepare']['ok'],
                              'version_py': row['amendment_1_3_prepare']['version_py']}), flush=True)
    result = {'label': label, 'model_calls': 0, 'tox_episode_ids': episodes, 'rows': rows,
              'command': amendment.tox_preparation_command(pathlib.Path('<repo>')),
              'pass': all(r['pass'] for r in rows)}
    (out / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
    print('PASS' if result['pass'] else 'FAIL')


if __name__ == '__main__':
    main()
