"""Aggregate tables for the paper audit from paper_audit/audit_table.json and reconciliation.json.

Writes paper_audit/summary_tables.json and paper_audit/summary_tables.md. Counts only;
no inferential statistics beyond the frozen analysis.

Usage: python3 -I paper_audit/tools/summarize_audit.py
"""
import collections
import json
import pathlib

AUDIT = pathlib.Path(__file__).resolve().parents[1]
FAMILY_ORDER = ['rtl-data', 'l0-module-actual', 'pyfiglet-154', 'apotrope-template', 'pynecore-data', 'pixcull-sdist',
                'stellium-locales', 'stellium-glyphs', 'stellium-cache', 'tox-sdist', 'pytest-html-npm', 's3-template']


def md_table(header, rows):
    out = ['| ' + ' | '.join(header) + ' |', '|' + '|'.join([' :-- '] + [' --: '] * (len(header) - 1)) + '|']
    out += ['| ' + ' | '.join(str(c) for c in r) + ' |' for r in rows]
    return '\n'.join(out)


def main():
    rows = json.loads((AUDIT / 'audit_table.json').read_text())
    rec = json.loads((AUDIT / 'reconciliation.json').read_text())
    gap = [r for r in rows if r['stratum'] == 'gap']
    ctrl = [r for r in rows if r['stratum'] != 'gap']
    T = {}

    # RQ1: exact patterns by family and condition
    pat = {}
    for fam in FAMILY_ORDER:
        for cond in 'AB':
            sel = sorted((r for r in rows if r['task'] == fam and r['condition'] == cond), key=lambda r: r['seed'])
            pat[f'{fam}/{cond}'] = [f"{r['seed']}:{r['final_pattern']}" for r in sel]
    T['patterns_by_family_condition'] = pat
    T['pattern_counts'] = {
        'gap_all': dict(collections.Counter(r['final_pattern'] for r in gap)),
        'gap_A': dict(collections.Counter(r['final_pattern'] for r in gap if r['condition'] == 'A')),
        'gap_B': dict(collections.Counter(r['final_pattern'] for r in gap if r['condition'] == 'B')),
        'control_all': dict(collections.Counter(r['final_pattern'] for r in ctrl)),
    }
    spif = [r for r in gap if r['source_pass_installed_fail']]
    T['source_pass_installed_fail'] = {
        'gap_total': len(spif), 'gap_A': sum(r['condition'] == 'A' for r in spif), 'gap_B': sum(r['condition'] == 'B' for r in spif),
        'gap_source_pass': sum(r['source'] == 'P' for r in gap),
        'by_pattern': dict(collections.Counter(r['final_pattern'] for r in spif)),
        'control': sum(r['source_pass_installed_fail'] for r in ctrl),
        'direct_vs_sdist_disagreement_gap': sum(r['direct_wheel'] != r['sdist_wheel'] for r in gap),
    }
    T['outcome_change_vs_affected'] = {s: dict(collections.Counter(r['outcome_change_vs_affected'] for r in rows if (r['stratum'] == 'gap') == (s == 'gap')))
                                       for s in ['gap', 'control']}
    T['regressions'] = [f"{r['episode_id']} {r['affected_pattern']}->{r['final_pattern']}" for r in rows if r['outcome_change_vs_affected'] == 'regression']
    T['first_failing_step'] = dict(collections.Counter(x for r in rows for x in r['first_failing_step'].split(';') if x))

    # Patch validity
    T['patch_validity'] = {c: dict(collections.Counter(r['patch_validity'] for r in rows if r['condition'] == c)) for c in 'AB'}
    T['patch_flags'] = dict(collections.Counter(f for r in rows for f in r['patch_flags']))
    T['patch_flags_episodes'] = {f: [r['episode_id'] for r in rows if f in r['patch_flags']] for f in sorted({f for r in rows for f in r['patch_flags']})}

    # RQ2: routes actually exercised
    for key in ['review_source_route', 'review_direct_wheel_route', 'review_sdist_wheel_route']:
        T[key] = {c: dict(collections.Counter(r[key] for r in rows if r['condition'] == c)) for c in 'AB'}
    T['any_artifact_built'] = [r['episode_id'] for r in rows if r['review_direct_wheel_route'] in ('built_not_installed', 'installed_exercised_failed')
                               or r['review_sdist_wheel_route'] in ('built_not_installed', 'sdist_built_not_rebuilt')]
    T['any_candidate_installed'] = [r['episode_id'] for r in rows if r['review_direct_wheel_route'] in ('installed_exercised_failed', 'exercised_origin_unknown', 'verified_installed')]
    T['verified_installed_operation'] = [r['episode_id'] for r in rows if 'verified_installed' in (r['review_direct_wheel_route'], r['review_sdist_wheel_route'])]
    T['origin_check_performed'] = sum(r['origin_check_performed'] for r in rows)
    T['outside_checkout_consumer'] = sum(r['outside_checkout_consumer'] for r in rows)
    T['echo_asserted_success'] = [r['episode_id'] for r in rows if r['echo_asserted_success_steps']]

    # Claims
    comp = [r for r in rows if r['stop'] == 'completion_claim']
    T['final_message_class_completion_stops'] = {c: dict(collections.Counter(r['final_message_class'] for r in comp if r['condition'] == c)) for c in 'AB'}
    succ = [r for r in comp if r['final_message_class'] in ('unhedged_success_claim', 'hedged_claim')]
    T['claims'] = {
        'completion_stops': len(comp),
        'bare_complete': sum(r['final_message_class'] == 'bare_complete' for r in comp),
        'explicit_non_repair': sum(r['final_message_class'] == 'explicit_non_repair' for r in comp),
        'unhedged_success_claims': sum(r['final_message_class'] == 'unhedged_success_claim' for r in comp),
        'hedged_claims': sum(r['final_message_class'] == 'hedged_claim' for r in comp),
        'unhedged_success_claims_contradicted_by_grade': sum(r['final_message_class'] == 'unhedged_success_claim' and not r['artifact_contract_pass'] for r in comp),
        'claims_asserting_an_installed_route': [r['episode_id'] for r in succ if set(filter(None, r['claimed_verified_routes'].split(','))) & {'D', 'W'}],
        'claims_asserting_installed_route_with_installed_operation_in_trace': [r['episode_id'] for r in succ if set(filter(None, r['claimed_verified_routes'].split(','))) & {'D', 'W'}
                                                                               and r['review_direct_wheel_route'] in ('exercised_origin_unknown', 'verified_installed')],
        'claim_basis': dict(collections.Counter(r['claim_basis'] for r in succ)),
        'edit_claims_not_in_patch': [r['episode_id'] for r in comp if r['edit_claim_vs_patch'] == 'claims_edit_not_in_patch'],
        'fabricated_or_echo_basis': [r['episode_id'] for r in succ if r['claim_basis'] == 'echo_or_fabricated'],
    }
    T['environment_flags'] = {f: [r['episode_id'] for r in rows if f in r['environment_flags']] for f in sorted({f for r in rows for f in r['environment_flags']})}
    T['stops_by_condition'] = {c: dict(collections.Counter(r['stop'] for r in rows if r['condition'] == c)) for c in 'AB'}
    T['format_errors_total'] = sum(r['format_errors'] for r in rows)
    T['episodes_with_zero_commands'] = [r['episode_id'] for r in rows if r['commands'] == 0]
    T['budgets'] = {k: rec['budgets'][k] for k in ['stops', 'budget_by_kind', 'partial_deadline_calls', 'max_calls', 'max_tokens', 'max_wall']}
    T['host'] = {'sleep_overlap': rec['host_power_sleep']['episodes_overlapping_sleep'],
                 'power_at_start_counts': {k: len(v) for k, v in rec['host_power_sleep']['episodes_by_power_at_start'].items()}}
    (AUDIT / 'summary_tables.json').write_text(json.dumps(T, indent=2, ensure_ascii=False) + '\n')

    md = ['# Audit summary tables (generated)', '', 'Generated by `paper_audit/tools/summarize_audit.py` from `audit_table.json` and `reconciliation.json`.', '',
          '## Final-state outcome patterns (source / direct wheel / sdist-wheel), seeds 19, 23, 41', '']
    md.append(md_table(['Family', 'Stratum', 'Affected', 'A (19, 23, 41)', 'B (19, 23, 41)'],
                       [[f, 'control' if f == 's3-template' else 'gap', next(r['affected_pattern'] for r in rows if r['task'] == f),
                         ' '.join(x.split(':')[1] for x in pat[f'{f}/A']), ' '.join(x.split(':')[1] for x in pat[f'{f}/B'])] for f in FAMILY_ORDER]))
    md += ['', '## Pattern counts', '', md_table(['Set', 'Counts'], [[k, json.dumps(v)] for k, v in T['pattern_counts'].items()]), '',
           '## Source-pass / installed-route failure (gap stratum)', '', md_table(['Measure', 'Value'], [[k, json.dumps(v)] for k, v in T['source_pass_installed_fail'].items()]), '',
           '## Routes exercised (reviewed labels)', '']
    for key in ['review_source_route', 'review_direct_wheel_route', 'review_sdist_wheel_route']:
        md += [f'**{key}**', '', md_table(['Label', 'A', 'B'], [[lab, T[key]['A'].get(lab, 0), T[key]['B'].get(lab, 0)]
                                                               for lab in sorted(set(T[key]['A']) | set(T[key]['B']))]), '']
    md += ['## Completion messages', '', md_table(['Measure', 'Value'], [[k, json.dumps(v, ensure_ascii=False)] for k, v in T['claims'].items()]), '',
           '## Patch validity', '', md_table(['Label', 'A', 'B'], [[lab, T['patch_validity']['A'].get(lab, 0), T['patch_validity']['B'].get(lab, 0)]
                                                                    for lab in sorted(set(T['patch_validity']['A']) | set(T['patch_validity']['B']))]), '',
           md_table(['Flag', 'Episodes'], [[f, ', '.join(e)] for f, e in T['patch_flags_episodes'].items()]), '',
           '## Environment flags', '', md_table(['Flag', 'Episodes'], [[f, ', '.join(e)] for f, e in T['environment_flags'].items()]), '']
    (AUDIT / 'summary_tables.md').write_text('\n'.join(md) + '\n')
    print(json.dumps({k: T[k] for k in ['pattern_counts', 'source_pass_installed_fail', 'claims']}, indent=1, ensure_ascii=False))


if __name__ == '__main__':
    main()
