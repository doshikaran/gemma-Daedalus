"""Amendment 1.6 entry point: the amendment 1.5 controller with a battery-aware power guard.

Study owner instruction (PROTOCOL_AMENDMENT_1.6.json): allow running on battery. The
amendment 1.4 guard (AC required) is replaced by one that accepts AC, or battery at or
above MIN_BATTERY_PERCENT with Low Power Mode off, using the state written by
amendment_1.6/power_watch.sh. It is applied at the same points as before: at start,
before each episode (amendment 1.5 gate) and after each saved episode (amendment 1.4
checkpoint), pausing cleanly between episodes otherwise. Nothing inside an episode,
its budgets, grading or analysis changes.

Verifies FREEZE.json (1.1), FREEZE_1.2-1.5.json, FREEZE_1.6.json and the byte identity of
the 53 result records completed before this amendment.

Usage (inside the container, from ROOT): python3 amendment_1.6/run_batch_native_1_6.py --resume
"""
import json
import pathlib
import sys
import time

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'amendment_1.5'))

import run_batch_native_1_5 as amendment_1_5  # noqa: E402

amendment_1_4 = amendment_1_5.amendment_1_4
POWER_STATE = ROOT / 'logs/amendment_1.6/power_state.json'
STALE_SECONDS = 180
MIN_BATTERY_PERCENT = 35


def power_problem(state_file=POWER_STATE, now=None):
    """None when the host may run the next episode, else a reason string."""
    try:
        state = json.loads(state_file.read_text())
    except (OSError, ValueError) as exc:
        return 'host power state unreadable: ' + repr(exc)
    age = (now if now is not None else time.time()) - state.get('epoch', 0)
    if age > STALE_SECONDS:
        return f'host power state stale ({int(age)} s old)'
    if state.get('lowpowermode') != 0:
        return 'Low Power Mode on or unknown: ' + json.dumps(state)
    if state.get('source') == 'AC':
        return None
    if state.get('source') == 'BATTERY' and (state.get('percent') or 0) >= MIN_BATTERY_PERCENT:
        return None
    return f'battery below {MIN_BATTERY_PERCENT}% or unknown source: ' + json.dumps(state)


def verify():
    amendment_1_5.verify()
    freeze = json.loads((ROOT / 'amendment_1.6/FREEZE_1.6.json').read_text())
    for name, digest in freeze['files'].items():
        if amendment_1_4.amendment_1_3.sha(ROOT / name) != digest:
            raise RuntimeError('Amendment 1.6 frozen input changed: ' + name)
    for name, digest in freeze['completed_result_records_at_amendment'].items():
        if amendment_1_4.amendment_1_3.sha(ROOT / name) != digest:
            raise RuntimeError('Completed result record changed: ' + name)


def main():
    verify()
    amendment_1_4.power_problem = power_problem  # used by the 1.4 checkpoint and the 1.5 gate
    problem = power_problem()
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
    run_batch.episode = amendment_1_5.gated(run_batch.episode)
    run_batch.main()


if __name__ == '__main__':
    main()
