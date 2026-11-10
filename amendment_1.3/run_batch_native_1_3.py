"""Amendment 1.3 entry point: the amendment 1.2 controller plus two corrections.

1. Experimental-setup correction (PROTOCOL_AMENDMENT_1.3.json): the tox-sdist branch
   of run_study.prepare selects build-constraints-tox.txt by task ID. The frozen code
   reached replay.build, which chooses the tox constraints only when a path component
   equals 'tox-sdist'; episode trees are main_runs/<NN>-tox-sdist-<C>-<seed>/repo, so
   the generic constraints were used and preparation failed before any model call.
   The command is otherwise identical to replay.build. All other tasks use the frozen
   prepare unchanged.
2. Evidence-packaging correction (not scoring): run_batch.checkpoint wrote the root
   CONTENTS_SHA256.json as a member and then a second member with the same name. The
   replacement writes one generated manifest, adds the amendment directories, incident
   records and amendment logs, and verifies every member against the manifest.

Model server attach/verify is amendment 1.2's start_server. Verifies FREEZE.json (1.1),
amendment_1.2/FREEZE_1.2.json, amendment_1.3/FREEZE_1.3.json and the byte identity of
the result records completed before this amendment.

Usage (inside the container, from ROOT): python3 amendment_1.3/run_batch_native_1_3.py --resume
"""
import hashlib
import json
import pathlib
import sys
import zipfile

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'amendment_1.2'))

import run_batch_native as amendment_1_2  # noqa: E402
import run_study  # noqa: E402
from replay import cmd  # noqa: E402

frozen_prepare = run_study.prepare


def sha(path):
    return amendment_1_2.sha(path)


def tox_preparation_command(repo):
    return ['uv', 'build', '--python', sys.executable, '--wheel', '--out-dir', str(repo / '.agent-source-preparation'),
            '--build-constraints', str(ROOT / 'build-constraints-tox.txt'), '--cache-dir', str(ROOT / '.uv-cache')]


def prepare(repo, task):
    if task == 'tox-sdist':
        result = cmd(tox_preparation_command(repo), repo)
        if result['returncode']:
            raise RuntimeError('tox version preparation failed: ' + json.dumps(result))
        return
    frozen_prepare(repo, task)


def verify():
    run_study.verify_freeze()
    amendment_1_2.verify_amendment_freeze()
    freeze = json.loads((ROOT / 'amendment_1.3/FREEZE_1.3.json').read_text())
    for name, digest in freeze['files'].items():
        if sha(ROOT / name) != digest:
            raise RuntimeError('Amendment 1.3 frozen input changed: ' + name)
    for name, digest in freeze['completed_result_records_at_amendment'].items():
        if sha(ROOT / name) != digest:
            raise RuntimeError('Completed result record changed: ' + name)


def checkpoint():
    """Duplicate-free evidence package; weights and upstream code/artifact binaries omitted."""
    path = ROOT.parent / 'Daedalus_Experiment_Checkpoint.zip'
    temp = path.with_suffix('.tmp.zip')
    files = set(ROOT.glob('*.md')) | set(ROOT.glob('*.json')) | set(ROOT.glob('*.csv')) | set(ROOT.glob('*.py')) | set(ROOT.glob('build-constraints*.txt'))
    files.discard(ROOT / 'CONTENTS_SHA256.json')  # regenerated below; the original stays on disk unchanged
    for folder, patterns in [('prompts', ['*.txt']), ('locks', ['*.txt']), ('results', ['*.json']),
                             ('protocol_history', ['*.json', '*.py', '*.md', '*.txt', '*.csv']),
                             ('amendment_1.2', ['*.py', '*.json', '*.sh', 'Dockerfile']),
                             ('amendment_1.3', ['*.py', '*.json', '*.sh'])]:
        for pattern in patterns:
            files.update((ROOT / folder).rglob(pattern))
    for work in (ROOT / 'main_runs').glob('*'):
        for pattern in ['*.json', '*.patch', 'prompt.txt']:
            files.update(work.glob(pattern))
    for calls in (ROOT / 'pilots').rglob('calls.json'):
        files.add(calls)
        for name in ['prompt.txt', 'trajectory.json', 'controller.log']:
            if (calls.parent / name).exists():
                files.add(calls.parent / name)
    files.update((ROOT / 'pilots').glob('*/*.INCIDENT.json'))
    files.update((ROOT / 'sources').glob('*-provenance.json'))
    files.update((ROOT / 'logs').glob('*.log'))
    files.update((ROOT / 'logs').glob('*audit.json'))
    files.update((ROOT / 'logs').glob('amendment_1.*/*.log'))
    digests = {}
    with zipfile.ZipFile(temp, 'w', zipfile.ZIP_DEFLATED, compresslevel=6) as z:
        for p in sorted(files):
            if p.is_file():
                name = str(p.relative_to(ROOT)); data = p.read_bytes()
                z.writestr('Daedalus_Experiment/' + name, data); digests[name] = hashlib.sha256(data).hexdigest()
        z.writestr('Daedalus_Experiment/CONTENTS_SHA256.json', json.dumps(digests, indent=2) + '\n')
    with zipfile.ZipFile(temp) as z:
        if z.testzip() is not None:
            raise RuntimeError('Checkpoint archive integrity failure')
        names = z.namelist()
        if len(names) != len(set(names)):
            raise RuntimeError('Checkpoint archive has duplicate member names')
        manifest = json.loads(z.read('Daedalus_Experiment/CONTENTS_SHA256.json'))
        for name, digest in manifest.items():
            if hashlib.sha256(z.read('Daedalus_Experiment/' + name)).hexdigest() != digest:
                raise RuntimeError('Checkpoint member hash mismatch: ' + name)
    temp.replace(path)


def main():
    verify()
    import agent_calibration
    agent_calibration.start_server = amendment_1_2.start_server
    run_study.prepare = prepare
    import run_batch
    run_batch.start_server = amendment_1_2.start_server
    run_batch.checkpoint = checkpoint
    run_batch.main()


if __name__ == '__main__':
    main()
