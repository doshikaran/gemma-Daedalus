"""Amendment 1.2 entry point: the frozen run_batch controller with the native model server.

Only agent_calibration.start_server is replaced. Instead of launching the Linux x86_64
llama-server (unusably slow under Rosetta), it attaches to the already-running native
macOS arm64 CPU-only b12020 server reached through the frozen endpoint 127.0.0.1:18090,
checks its identity, and returns a handle that leaves the host server running.
Everything else (plan, prompts, budgets, episode(), grading, retention, checkpoint,
analysis) is the unmodified frozen code. FREEZE.json (v1.1) and FREEZE_1.2.json are
both verified before anything starts.

Usage (inside the container, from ROOT): python3 amendment_1.2/run_batch_native.py [--resume]
"""
import hashlib
import json
import pathlib
import sys
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
FREEZE = json.loads((ROOT / 'amendment_1.2/FREEZE_1.2.json').read_text())


def sha(path):
    h = hashlib.sha256()
    with open(path, 'rb') as stream:
        while chunk := stream.read(8 * 1024 * 1024):
            h.update(chunk)
    return h.hexdigest()


def verify_amendment_freeze():
    for name, digest in FREEZE['files'].items():
        if sha(ROOT / name) != digest:
            raise RuntimeError('Amendment 1.2 frozen input changed: ' + name)


class HostServer:
    """Stands in for the subprocess handle; the native server is managed on the host."""
    def terminate(self):
        pass

    def wait(self, timeout=None):
        return 0

    def kill(self):
        pass

    def poll(self):
        return None


def start_server():
    protocol = json.loads((ROOT / 'protocol.json').read_text())
    with urllib.request.urlopen(protocol['endpoint'] + '/health', timeout=10) as response:
        if json.load(response).get('status') != 'ok':
            raise RuntimeError('Native model server not healthy')
    with urllib.request.urlopen(protocol['endpoint'] + '/props', timeout=10) as response:
        props = json.load(response)
    settings = props.get('default_generation_settings', {})
    if (not props['model_path'].endswith('/' + protocol['model']['filename']) or props['total_slots'] != 1
            or settings.get('n_ctx') != protocol['runtime']['context_tokens']):
        raise RuntimeError('Native model server differs from the frozen configuration: ' + json.dumps(props)[:500])
    log = (ROOT / 'logs/amendment_1.2/native-server-attach.log').open('a')
    log.write(json.dumps({'model_path': props['model_path'], 'total_slots': props['total_slots'],
                          'n_ctx': settings.get('n_ctx'), 'build_info': props.get('build_info')}) + '\n')
    log.flush()
    return HostServer(), log, FREEZE['native_server']['args']


def main():
    verify_amendment_freeze()
    import agent_calibration
    agent_calibration.start_server = start_server
    import run_batch
    run_batch.start_server = start_server
    run_batch.main()


if __name__ == '__main__':
    main()
