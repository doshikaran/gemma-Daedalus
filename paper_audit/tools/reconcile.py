"""Reconcile the 72 records with the frozen plan, analysis, graders, controls, budgets and amendments.

Read-only over main_runs/, results/, pilots/, restoration_*/ and the freezes. Recomputes the
declared analysis with the frozen analyze.summarize and compares it with results/main_analysis.json.
Host power history comes from a saved `pmset -g log` extract (paper_audit/environment/).

Usage: python3 -I paper_audit/tools/reconcile.py
"""
import datetime as dt
import hashlib
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
AUDIT = ROOT / 'paper_audit'


def _t(x):
    return dt.datetime.fromisoformat(x).timestamp()


# Orchestrator-observed host power windows (UTC). Sources: launcher AC checks, watcher outputs and
# pmset readings recorded in the session; amendments 1.4-1.6. Gaps are 'not_observed'.
POWER_WINDOWS = [
    (_t('2026-11-03T18:00:00+00:00'), _t('2026-11-03T19:27:00+00:00'), 'AC_at_launch_unmonitored'),
    (_t('2026-11-04T16:21:00+00:00'), _t('2026-11-04T18:45:00+00:00'), 'AC_observed'),
    (_t('2026-11-04T18:45:00+00:00'), _t('2026-11-05T11:46:05+00:00'), 'BATTERY_observed'),
    (_t('2026-11-05T12:29:00+00:00'), _t('2026-11-05T13:06:00+00:00'), 'AC_guarded_amendment_1_4'),
    (_t('2026-11-05T18:00:00+00:00'), _t('2026-11-05T18:50:00+00:00'), 'BATTERY_observed_amendment_1_6'),
    (_t('2026-11-06T17:57:00+00:00'), _t('2026-11-06T21:42:00+00:00'), 'AC_observed_at_checks'),
]


def sha(p):
    return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()


def main():
    from analyze import summarize
    from run_study import grid
    protocol = json.loads((ROOT / 'protocol.json').read_text())
    tasks = json.loads((ROOT / 'task_manifest.json').read_text())['tasks']
    plan = json.loads((ROOT / 'episode_plan.json').read_text())
    records = [json.loads(p.read_text()) for p in sorted((ROOT / 'main_runs').glob('*/result.json'))]
    issues, out = [], {}

    # 1. Plan reconciliation
    regenerated = grid(protocol, tasks)
    out['plan'] = {'plan_rows': len(plan), 'regenerated_plan_identical': regenerated == plan, 'records': len(records),
                   'record_ids_match_plan': sorted(r['episode_id'] for r in records) == sorted(p['episode_id'] for p in plan),
                   'record_fields_match_plan': all(all(r[k] == p[k] for k in p) for r, p in
                                                   zip(sorted(records, key=lambda x: x['order']), sorted(plan, key=lambda x: x['order']))),
                   'protocol_versions': sorted({r['protocol_version'] for r in records}),
                   'conditions': {c: sum(r['condition'] == c for r in records) for c in 'AB'},
                   'main_study_flag_all_true': all(r['main_study'] for r in records),
                   'infrastructure_records': sum('infrastructure_error' in r or 'grading_infrastructure_error' in r for r in records)}

    # 2. Analysis recomputation with the frozen code
    recomputed = summarize(records, tasks, protocol)
    frozen = json.loads((ROOT / 'results/main_analysis.json').read_text())
    out['analysis'] = {'recomputed_equals_frozen': recomputed == frozen,
                       'artifact_contract_passes': sum(bool(r.get('artifact_contract_pass')) for r in records),
                       'frozen_file_sha256': sha(ROOT / 'results/main_analysis.json')}
    if recomputed != frozen:
        issues.append('Recomputed analysis differs from results/main_analysis.json')

    # 3. Graders and controls
    freeze = json.loads((ROOT / 'FREEZE.json').read_text())
    graders = {k: v for k, v in freeze['files'].items() if re.search(r'replay|run_study|analyze|build-constraints|task_manifest', k)}
    out['graders'] = {'frozen_grader_files': {k: {'frozen': v, 'now': sha(ROOT / k), 'match': sha(ROOT / k) == v} for k, v in graders.items()},
                      'note': 'run_study.episode calls verify_freeze() after the agent finishes and before grading; a mismatch raises before any record is written. Records do not store per-episode grader hashes.'}
    manifest_states = {t['id']: t['states'] for t in tasks}
    frozen_controls = {}
    for t in tasks:
        for arm in ['affected', 'reference']:
            rec = json.loads((ROOT / 'results' / f"{t['id']}-{arm}.json").read_text())
            obs = ''.join('P' if r['pass'] else 'F' for r in rec['rows'])
            frozen_controls[f"{t['id']}/{arm}"] = {'expected': manifest_states[t['id']][arm], 'observed': obs, 'match': obs == manifest_states[t['id']][arm]}
    replays = {}
    for d in sorted((ROOT / 'restoration_1.2/controls').iterdir()):
        s = d / 'summary.json'
        if s.exists():
            rows = json.loads(s.read_text())['rows']
            replays[d.name] = {'rows': len(rows), 'matches': sum(r['match'] for r in rows)}
        else:
            replays[d.name] = {'rows': 0, 'matches': 0, 'note': (d / 'ABORTED.txt').read_text().strip() if (d / 'ABORTED.txt').exists() else 'no summary'}
    out['controls'] = {'frozen_v1_1_results': {'rows': len(frozen_controls), 'matches': sum(v['match'] for v in frozen_controls.values()), 'detail': frozen_controls},
                       'replays': replays}

    # 4. Budget accounting
    budget_rows = []
    for r in records:
        tok = sum(c['response']['usage'].get('completion_tokens', 0) for c in r['calls'])
        last = r['calls'][-1] if r['calls'] else {}
        row = {'episode_id': r['episode_id'], 'stop': r['stop'], 'calls': len(r['calls']), 'generated_tokens': r['generated_tokens'],
               'sum_completion_tokens': tok, 'wall': round(r['interaction_wall_seconds'], 1),
               'accounting': r.get('generated_token_accounting'), 'deadline_partial_call': bool(last.get('episode_deadline'))}
        problems = []
        if tok != r['generated_tokens']:
            problems.append('token sum differs from record')
        if len(r['calls']) > protocol['max_actions']:
            problems.append('more calls than max_actions')
        if r['generated_tokens'] > protocol['episode_generated_tokens']:
            problems.append('generated tokens exceed budget')
        if r['stop'] == 'action_limit' and len(r['calls']) != protocol['max_actions']:
            problems.append('action_limit without max_actions calls')
        if r['stop'] == 'budget' and not (r['generated_tokens'] >= protocol['episode_generated_tokens'] or
                                          r['interaction_wall_seconds'] >= protocol['wall_seconds'] - 1 or row['deadline_partial_call']):
            problems.append('budget stop without exhausted token or time budget')
        if r['stop'] == 'completion_claim' and not re.match(r'^COMPLETE(?:\s|$)', (last.get('response') or {}).get('content', '').strip()):
            problems.append('completion stop without COMPLETE message')
        if r['interaction_wall_seconds'] > protocol['wall_seconds'] + protocol['command_seconds'] + 5:
            problems.append('wall time exceeds budget plus one command')
        row['which_budget'] = ('tokens' if r['generated_tokens'] >= protocol['episode_generated_tokens'] else
                               'wall' if r['interaction_wall_seconds'] >= protocol['wall_seconds'] - 1 or row['deadline_partial_call'] else '') if r['stop'] == 'budget' else ''
        row['problems'] = problems
        budget_rows.append(row)
        issues += [f"{r['episode_id']}: {p}" for p in problems]
    out['budgets'] = {'rows': budget_rows,
                      'stops': {s: sum(r['stop'] == s for r in records) for s in ['completion_claim', 'budget', 'action_limit']},
                      'budget_by_kind': {k: sum(b['which_budget'] == k for b in budget_rows) for k in ['tokens', 'wall']},
                      'partial_deadline_calls': sum(b['deadline_partial_call'] for b in budget_rows),
                      'max_calls': max(b['calls'] for b in budget_rows), 'max_tokens': max(b['generated_tokens'] for b in budget_rows),
                      'max_wall': max(b['wall'] for b in budget_rows)}

    # 5. Infrastructure replacements and retained attempts
    incidents = []
    for inc in sorted((ROOT / 'pilots').glob('*/*.INCIDENT.json')):
        d = json.loads(inc.read_text())
        ep = d['episode']
        retained = inc.parent / ep
        rec = retained / 'result.json'
        incidents.append({'episode': ep, 'retained_at': str(retained.relative_to(ROOT)), 'retained_exists': retained.exists(),
                          'incident': d['incident'], 'model_calls': d.get('model_calls', d.get('model_calls_completed')),
                          'generated_tokens': d.get('generated_tokens'), 'replacement_record_exists': (ROOT / 'main_runs' / ep / 'result.json').exists(),
                          'retained_record_stop': json.loads(rec.read_text())['stop'] if rec.exists() else None})
    amendments = sorted(p.name for p in ROOT.glob('PROTOCOL_AMENDMENT_*.json'))
    out['infrastructure'] = {'incidents': incidents, 'amendments': amendments,
                             'setup_and_interrupted_attempts': [str(p.relative_to(ROOT)) for p in sorted((ROOT / 'pilots').glob('v1.[01]-*/*'))]}
    for i in incidents:
        if not (i['retained_exists'] and i['replacement_record_exists']):
            issues.append(f"Replacement bookkeeping incomplete for {i['episode']}")

    # 6. Host sleep and power per episode (pmset extract)
    pm = (AUDIT / 'environment' / 'pmset_log_2026-11-03_to_07.txt').read_text().splitlines()
    events = []
    for line in pm:
        m = re.match(r'(\d{4}-\d\d-\d\d \d\d:\d\d:\d\d [+-]\d{4}) (\S+)\s', line)
        if not m:
            continue
        t = dt.datetime.strptime(m.group(1), '%Y-%m-%d %H:%M:%S %z').timestamp()
        src = 'AC' if 'Using AC' in line else 'BATT' if 'Using Batt' in line or 'Using BATT' in line else None
        asleep = m.group(2) == 'Sleep' and 'Entering Sleep state' in line
        awake = m.group(2) in ('Wake', 'DarkWake') and re.search(r'\b(Dark)?Wake from ', line) is not None
        events.append((t, src, asleep, awake))
    sleeps, start = [], None
    for t, _, a, w in events:
        if a and start is None:
            start = t
        elif w and start is not None:
            sleeps.append((start, t))
            start = None
    power_rows = []
    for ep in sorted((ROOT / 'main_runs').iterdir()):
        s, e = (ep / 'prompt.txt').stat().st_mtime, (ep / 'result.json').stat().st_mtime
        overlap = sum(max(0, min(b, e) - max(a, s)) for a, b in sleeps)
        src_during = {x[1] for x in events if x[1] and s <= x[0] <= e}
        power = next((label for a, b, label in POWER_WINDOWS if a <= s < b), 'not_observed')
        power_rows.append({'episode_id': ep.name, 'start_utc': dt.datetime.fromtimestamp(s, dt.timezone.utc).isoformat(timespec='seconds'),
                           'end_utc': dt.datetime.fromtimestamp(e, dt.timezone.utc).isoformat(timespec='seconds'),
                           'host_asleep_seconds_in_window': int(overlap),
                           'power_at_start': power, 'power_sources_logged_at_sleep_wake_in_window': sorted(src_during)})
    out['host_power_sleep'] = {'rows': power_rows,
                               'episodes_overlapping_sleep': [r['episode_id'] for r in power_rows if r['host_asleep_seconds_in_window'] > 0],
                               'episodes_by_power_at_start': {k: [r['episode_id'] for r in power_rows if r['power_at_start'] == k] for k in sorted({r['power_at_start'] for r in power_rows})},
                               'note': 'Window = prompt.txt mtime to result.json mtime (includes preparation and grading). macOS logs the power source only at sleep/wake events, so power at start comes from the orchestrator-observed windows in POWER_WINDOWS (documented in the session and amendments), not from a continuous record.'}
    gate = ROOT / 'logs/amendment_1.5/load_gate.log'
    out['load_gate'] = [json.loads(l) for l in gate.read_text().splitlines()] if gate.exists() else []
    out['issues_detected_by_script'] = issues
    (AUDIT / 'reconciliation.json').write_text(json.dumps(out, indent=2) + '\n')
    print(json.dumps({k: v for k, v in out.items() if k in ('plan', 'analysis')}, indent=1))
    print('controls', out['controls']['frozen_v1_1_results']['matches'], {k: v['matches'] for k, v in replays.items()})
    print('budgets', out['budgets']['stops'], out['budgets']['budget_by_kind'], 'partial', out['budgets']['partial_deadline_calls'])
    print('sleep overlap', out['host_power_sleep']['episodes_overlapping_sleep'])
    print('power', {k: len(v) for k, v in out['host_power_sleep']['episodes_by_power_at_start'].items()})
    print('issues', issues)


if __name__ == '__main__':
    main()
