"""Build the compact paper-audit handoff ZIP with an embedded SHA-256 manifest, then verify it.

Contents: paper_audit/ (excluding regrade work trees), all 72 result/patch/trace records,
protocols, freezes, amendments, prompts, graders, frozen controls, incidents and the frozen
analysis. Final-source tarballs, release artifacts, weights and dependencies are omitted.

Usage: python3 -I paper_audit/tools/build_handoff.py
"""
import hashlib
import json
import pathlib
import zipfile

ROOT = pathlib.Path(__file__).resolve().parents[2]
OUT = ROOT.parent / 'Daedalus_Paper_Audit_Handoff.zip'
PREFIX = 'Daedalus_Paper_Audit/'


def collect():
    files = set()
    for p in (ROOT / 'paper_audit').rglob('*'):
        rel = p.relative_to(ROOT / 'paper_audit')
        if p.is_file() and not (rel.parts[0] == 'regrade' and len(rel.parts) > 3) and '__pycache__' not in rel.parts:
            files.add(p)
    for ep in (ROOT / 'main_runs').iterdir():
        for name in ['result.json', 'final.patch', 'calls.json', 'trajectory.json', 'prompt.txt', 'tool_environment.json', 'retention.json']:
            if (ep / name).exists():
                files.add(ep / name)
    for pattern in ['*.md', 'protocol.json', 'FREEZE.json', 'PROTOCOL_AMENDMENT_*.json', 'task_manifest.json', 'episode_plan.json',
                    'task_validation.csv', 'execution_manifest.json', 'experiment_status.json', 'run_study.py', 'run_batch.py',
                    'replay.py', 'replay_pytesthtml.py', 'analyze.py', 'agent_environment_preflight.py', 'preflight.py',
                    'build-constraints*.txt', 'CONTENTS_SHA256.json']:
        files.update(ROOT.glob(pattern))
    for folder, pattern in [('prompts', '*'), ('protocol_history', '*'), ('results', '*.json'), ('sources', '*-provenance.json'),
                            ('amendment_1.2', '*'), ('amendment_1.3', '*'), ('amendment_1.4', '*'), ('amendment_1.5', '*'),
                            ('amendment_1.6', '*'), ('pilots', '*.INCIDENT.json'), ('restoration_1.2/controls', 'summary.json'),
                            ('restoration_1.2/controls', 'ABORTED.txt'), ('logs/paper_audit', '*.log'), ('logs/amendment_1.5', 'load_gate.log')]:
        files.update(p for p in (ROOT / folder).rglob(pattern) if p.is_file() and '__pycache__' not in p.parts)
    return sorted(files)


def main():
    files = collect()
    digests = {}
    tmp = OUT.with_suffix('.tmp.zip')
    with zipfile.ZipFile(tmp, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for p in files:
            rel = str(p.relative_to(ROOT))
            data = p.read_bytes()
            z.writestr(PREFIX + rel, data)
            digests[rel] = hashlib.sha256(data).hexdigest()
        z.writestr(PREFIX + 'HANDOFF_SHA256.json', json.dumps(digests, indent=2) + '\n')
    with zipfile.ZipFile(tmp) as z:
        assert z.testzip() is None
        names = z.namelist()
        assert len(names) == len(set(names)), 'duplicate member names'
        manifest = json.loads(z.read(PREFIX + 'HANDOFF_SHA256.json'))
        bad = [k for k, v in manifest.items() if hashlib.sha256(z.read(PREFIX + k)).hexdigest() != v]
        assert not bad, bad
        assert len(manifest) == len(names) - 1
        records = sum(1 for k in manifest if k.startswith('main_runs/') and k.endswith('/result.json'))
        patches = sum(1 for k in manifest if k.startswith('main_runs/') and k.endswith('/final.patch'))
        traces = sum(1 for k in manifest if k.startswith('main_runs/') and k.endswith('/calls.json'))
    tmp.replace(OUT)
    digest = hashlib.sha256(OUT.read_bytes()).hexdigest()
    OUT.with_suffix('.zip.sha256').write_text(f'{digest}  {OUT.name}\n')
    print(json.dumps({'path': str(OUT), 'sha256': digest, 'bytes': OUT.stat().st_size, 'members': len(names),
                      'manifest_entries': len(manifest), 'mismatches': 0, 'result_records': records, 'patches': patches,
                      'traces': traces}, indent=1))


if __name__ == '__main__':
    main()
