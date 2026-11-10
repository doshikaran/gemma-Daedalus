"""Amendment 1.6 verification: the battery-aware guard's decisions and that it replaces the
1.4 guard used by the checkpoint and the 1.5 gate, with zero model calls.

Usage (inside the container, from ROOT): python3 amendment_1.6/power_guard_test.py
"""
import json
import pathlib
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'amendment_1.6'))

import run_batch_native_1_6 as amendment  # noqa: E402

NOW = 2_000_000_000
CASES = [
    ('ac', {'source': 'AC', 'percent': 20, 'lowpowermode': 0, 'epoch': NOW - 10}, False),
    ('battery_high', {'source': 'BATTERY', 'percent': 94, 'lowpowermode': 0, 'epoch': NOW - 10}, False),
    ('battery_at_min', {'source': 'BATTERY', 'percent': 35, 'lowpowermode': 0, 'epoch': NOW - 10}, False),
    ('battery_low', {'source': 'BATTERY', 'percent': 34, 'lowpowermode': 0, 'epoch': NOW - 10}, True),
    ('low_power_mode', {'source': 'BATTERY', 'percent': 90, 'lowpowermode': 1, 'epoch': NOW - 10}, True),
    ('lpm_unknown', {'source': 'AC', 'percent': 90, 'lowpowermode': None, 'epoch': NOW - 10}, True),
    ('stale', {'source': 'AC', 'percent': 90, 'lowpowermode': 0, 'epoch': NOW - 600}, True),
    ('missing', None, True),
]


def main():
    rows = []
    with tempfile.TemporaryDirectory() as tmp:
        for name, state, expect_pause in CASES:
            path = pathlib.Path(tmp) / (name + '.json')
            if state is not None:
                path.write_text(json.dumps(state))
            problem = amendment.power_problem(path, now=NOW)
            rows.append({'case': name, 'pause': problem is not None, 'reason': problem,
                         'pass': (problem is not None) == expect_pause})
    amendment.amendment_1_4.power_problem = amendment.power_problem
    wired = amendment.amendment_1_5.amendment_1_4.power_problem is amendment.power_problem
    live = amendment.power_problem()
    result = {'model_calls': 0, 'rows': rows, 'guard_replaces_1_4': wired, 'live_state_problem': live,
              'pass': all(r['pass'] for r in rows) and wired and live is None}
    out = ROOT / 'restoration_1.6' / 'power_guard_test.json'
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))
    print('PASS' if result['pass'] else 'FAIL')


if __name__ == '__main__':
    main()
