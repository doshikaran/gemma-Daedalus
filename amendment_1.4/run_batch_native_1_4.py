"""Amendment 1.4 entry point: the amendment 1.3 controller plus a host-power guard.

Episode 50 was interrupted when the host battery ran out and macOS hibernated mid-request
(PROTOCOL_AMENDMENT_1.4.json). The amendment 1.3 launcher checked AC power only at start.
Here the checkpoint step, which run_batch.main calls after each episode's record has been
saved and retained, additionally reads the host power state written by
amendment_1.4/power_watch.sh. If the host is not on AC power, or the state file is stale,
the controller pauses cleanly between episodes (frozen pause path: status 'paused',
checkpoint, exit). No episode, prompt, budget, grading or analysis code changes.

Verifies FREEZE.json (1.1), FREEZE_1.2.json, FREEZE_1.3.json, FREEZE_1.4.json and the byte
identity of the 50 result records completed before this amendment.

Usage (inside the container, from ROOT): python3 amendment_1.4/run_batch_native_1_4.py --resume
"""
import json
import pathlib
import sys
import time

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'amendment_1.3'))

import run_batch_native_1_3 as amendment_1_3  # noqa: E402

POWER_STATE = ROOT / 'logs/amendment_1.4/power_state.json'
STALE_SECONDS = 180
TOTAL_EPISODES = 72


def power_problem(state_file=POWER_STATE, now=None):
    """None when the host is on AC power with a fresh state file, else a reason string."""
    try:
        state = json.loads(state_file.read_text())
    except (OSError, ValueError) as exc:
        return 'host power state unreadable: ' + repr(exc)
    age = (now if now is not None else time.time()) - state.get('epoch', 0)
    if age > STALE_SECONDS:
        return f'host power state stale ({int(age)} s old)'
    if state.get('source') != 'AC':
        return 'host not on AC power: ' + json.dumps(state)
    return None


def checkpoint():
    amendment_1_3.checkpoint()
    if len(list((ROOT / 'main_runs').glob('*/result.json'))) >= TOTAL_EPISODES:
        return  # grid complete; analysis already written
    problem = power_problem()
    if problem:
        raise RuntimeError('Paused cleanly between episodes: ' + problem)


def verify():
    amendment_1_3.verify()
    freeze = json.loads((ROOT / 'amendment_1.4/FREEZE_1.4.json').read_text())
    for name, digest in freeze['files'].items():
        if amendment_1_3.sha(ROOT / name) != digest:
            raise RuntimeError('Amendment 1.4 frozen input changed: ' + name)
    for name, digest in freeze['completed_result_records_at_amendment'].items():
        if amendment_1_3.sha(ROOT / name) != digest:
            raise RuntimeError('Completed result record changed: ' + name)


def main():
    verify()
    problem = power_problem()
    if problem:
        raise RuntimeError('Refusing to start: ' + problem)
    import agent_calibration
    import run_batch
    import run_study
    agent_calibration.start_server = amendment_1_3.amendment_1_2.start_server
    run_study.prepare = amendment_1_3.prepare
    run_batch.start_server = amendment_1_3.amendment_1_2.start_server
    run_batch.checkpoint = checkpoint
    run_batch.main()


if __name__ == '__main__':
    main()
