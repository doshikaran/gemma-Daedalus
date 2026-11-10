"""Amendment 1.5 entry point: the amendment 1.4 controller plus a pre-episode host-load gate.

Episode 53 hit the frozen 240 s per-request timeout while host contention cut native
decoding from ~20 to ~1.3 tok/s (PROTOCOL_AMENDMENT_1.5.json). Before each episode
starts, this waits until the host 1-minute load average (written by
amendment_1.5/load_watch.sh) is below LOAD_LIMIT for SETTLE_READS consecutive fresh
readings. It changes only when an episode starts; nothing inside an episode, its
budgets, grading or analysis changes. The amendment 1.4 power guard stays in force.

Verifies FREEZE.json (1.1), FREEZE_1.2-1.4.json, FREEZE_1.5.json and the byte identity of
the 53 result records completed before this amendment.

Usage (inside the container, from ROOT): python3 amendment_1.5/run_batch_native_1_5.py --resume
"""
import json
import pathlib
import sys
import time

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'amendment_1.4'))

import run_batch_native_1_4 as amendment_1_4  # noqa: E402

HOST_LOAD = ROOT / 'logs/amendment_1.5/host_load.json'
GATE_LOG = ROOT / 'logs/amendment_1.5/load_gate.log'
LOAD_LIMIT = 6.0
SETTLE_READS = 2
STALE_SECONDS = 120
POLL_SECONDS = 15


def load_ok(state_file=HOST_LOAD, now=None):
    """(ok, reading) for one host-load reading."""
    try:
        state = json.loads(state_file.read_text())
    except (OSError, ValueError) as exc:
        return False, {'error': repr(exc)}
    age = (now if now is not None else time.time()) - state.get('epoch', 0)
    return age <= STALE_SECONDS and state.get('load1', 1e9) < LOAD_LIMIT, state


def wait_for_quiet_host(episode_id, sleep=time.sleep):
    started, settled, last = time.time(), 0, None
    while settled < SETTLE_READS:
        problem = amendment_1_4.power_problem()
        if problem:
            raise RuntimeError('Paused cleanly before episode: ' + problem)
        ok, reading = load_ok()
        if reading.get('epoch') != last:
            settled = settled + 1 if ok else 0
            last = reading.get('epoch')
        if settled < SETTLE_READS:
            sleep(POLL_SECONDS)
    with GATE_LOG.open('a') as log:
        log.write(json.dumps({'episode': episode_id, 'waited_seconds': round(time.time() - started, 1),
                              'reading': reading}) + '\n')


def gated(episode):
    def run(row, task, protocol):
        wait_for_quiet_host(row['episode_id'])
        return episode(row, task, protocol)
    return run


def verify():
    amendment_1_4.verify()
    freeze = json.loads((ROOT / 'amendment_1.5/FREEZE_1.5.json').read_text())
    for name, digest in freeze['files'].items():
        if amendment_1_4.amendment_1_3.sha(ROOT / name) != digest:
            raise RuntimeError('Amendment 1.5 frozen input changed: ' + name)
    for name, digest in freeze['completed_result_records_at_amendment'].items():
        if amendment_1_4.amendment_1_3.sha(ROOT / name) != digest:
            raise RuntimeError('Completed result record changed: ' + name)


def main():
    verify()
    problem = amendment_1_4.power_problem()
    if problem:
        raise RuntimeError('Refusing to start: ' + problem)
    import agent_calibration
    import run_batch
    import run_study
    amendment_1_3 = amendment_1_4.amendment_1_3
    agent_calibration.start_server = amendment_1_3.amendment_1_2.start_server
    run_study.prepare = amendment_1_3.prepare
    run_batch.start_server = amendment_1_3.amendment_1_2.start_server
    run_batch.checkpoint = amendment_1_4.checkpoint
    run_batch.episode = gated(run_batch.episode)
    run_batch.main()


if __name__ == '__main__':
    main()
