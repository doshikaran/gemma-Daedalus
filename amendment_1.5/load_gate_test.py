"""Amendment 1.5 verification: the host-load gate's decisions, with zero model calls.

Usage (inside the container, from ROOT): python3 amendment_1.5/load_gate_test.py
"""
import json
import pathlib
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'amendment_1.5'))

import run_batch_native_1_5 as amendment  # noqa: E402

NOW = 2_000_000_000
CASES = [
    ('quiet_fresh', {'load1': 2.1, 'epoch': NOW - 5}, True),
    ('busy_fresh', {'load1': 15.6, 'epoch': NOW - 5}, False),
    ('at_limit', {'load1': 6.0, 'epoch': NOW - 5}, False),
    ('quiet_stale', {'load1': 1.0, 'epoch': NOW - 600}, False),
    ('missing', None, False),
]


def main():
    rows = []
    with tempfile.TemporaryDirectory() as tmp:
        for name, state, expect_ok in CASES:
            path = pathlib.Path(tmp) / (name + '.json')
            if state is not None:
                path.write_text(json.dumps(state))
            ok, _ = amendment.load_ok(path, now=NOW)
            rows.append({'case': name, 'ok': ok, 'pass': ok == expect_ok})
    live_ok, live = amendment.load_ok()
    result = {'model_calls': 0, 'rows': rows, 'live_reading': live, 'live_ok': live_ok,
              'pass': all(r['pass'] for r in rows) and 'load1' in live}
    out = ROOT / 'restoration_1.5' / 'load_gate_test.json'
    out.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))
    print('PASS' if result['pass'] else 'FAIL')


if __name__ == '__main__':
    main()
