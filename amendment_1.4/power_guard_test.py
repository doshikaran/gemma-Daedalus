"""Amendment 1.4 verification: the power guard's decisions, with zero model calls.

Usage (inside the container, from ROOT): python3 amendment_1.4/power_guard_test.py
"""
import json
import pathlib
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'amendment_1.4'))

import run_batch_native_1_4 as amendment  # noqa: E402

NOW = 2_000_000_000
CASES = [
    ('ac_fresh', {'source': 'AC', 'percent': 50, 'epoch': NOW - 10}, False),
    ('battery_fresh', {'source': 'BATTERY', 'percent': 90, 'epoch': NOW - 10}, True),
    ('ac_stale', {'source': 'AC', 'percent': 50, 'epoch': NOW - 600}, True),
    ('missing', None, True),
    ('corrupt', '{not json', True),
]


def main():
    rows = []
    with tempfile.TemporaryDirectory() as tmp:
        for name, state, expect_pause in CASES:
            path = pathlib.Path(tmp) / (name + '.json')
            if isinstance(state, dict):
                path.write_text(json.dumps(state))
            elif isinstance(state, str):
                path.write_text(state)
            problem = amendment.power_problem(path, now=NOW)
            rows.append({'case': name, 'pause': problem is not None, 'reason': problem,
                         'pass': (problem is not None) == expect_pause})
    live = amendment.power_problem()
    result = {'model_calls': 0, 'rows': rows, 'live_state_problem': live,
              'pass': all(r['pass'] for r in rows) and live is None}
    out = ROOT / 'restoration_1.4' / 'power_guard_test.json'
    out.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))
    print('PASS' if result['pass'] else 'FAIL')


if __name__ == '__main__':
    main()
