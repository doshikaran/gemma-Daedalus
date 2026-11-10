"""Apply the audit codebook (paper_audit/CODEBOOK.md) to the extracted evidence.

First pass is rule-based over paper_audit/evidence/*.json. Reviewed labels from
paper_audit/reviewed_labels.json override or complete it; every override carries a
rationale. Writes paper_audit/audit_table.csv and paper_audit/audit_table.json.

Usage: python3 -I paper_audit/tools/code_episodes.py
"""
import csv
import json
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parents[2]
AUDIT = ROOT / 'paper_audit'

# Public operation per family: a command exercising it (not editing files) counts as a runtime attempt.
OPERATION = {
    'rtl-data': r'builtin_timings', 'l0-module-actual': r'main\.py\s+--help|l0p4map\s+--help|-m l0p4map',
    'pyfiglet-154': r'figlet_format|-m pyfiglet|test_pyfiglet\.py', 'apotrope-template': r'generate_html_report',
    'pynecore-data': r'import pynecore|pynecore\.types', 'pixcull-sdist': r'pixcull\.i18n|load_locale',
    'stellium-locales': r'stellium\.i18n', 'stellium-glyphs': r'get_glyph', 'stellium-cache': r'Native\(|Alexandria',
    'tox-sdist': r'\btox\b[^\n]*--help|-m tox', 'pytest-html-npm': r'--html|--self-contained-html',
    's3-template': r'generate_report|HTMLReporter',
}
EDIT_SCRIPT = re.compile(r'\.write\(|re\.sub\(|writelines|open\([^)]*[\'"]w[\'"]|sed\s+-i|cat\s*>|<<\s*EOF\s*>')
FAIL_OUT = re.compile(r'Traceback|Error:|error:|command not found|No module named|SyntaxError|not found')
ECHO_CLAIM = re.compile(r'echo\s+["\'][^"\'\n]*(success|verified|passed|complete|works)', re.I)
AFFECTED = {'pixcull-sdist': 'PPF', 'tox-sdist': 'PPF', 'pytest-html-npm': 'PPF', 's3-template': 'FFF'}


def route_first_pass(ev):
    op = re.compile(OPERATION[ev['task']])
    src = {'runtime_success': [], 'runtime_failed': []}
    build = {'wheel_built': [], 'sdist_built': [], 'wheel_from_sdist_built': [], 'build_failed': []}
    install = {'candidate_installed': [], 'install_failed': []}
    echo_steps = []
    for c in ev['commands_detail']:
        cmd, out, rc, s = c['command'], c['output_tail'], c['returncode'], c['step']
        if c.get('rejected'):
            continue
        if ECHO_CLAIM.search(cmd):
            echo_steps.append(s)
        runs = any(t in ('run:python', 'run:tests') for t in c['tags']) or re.search(r'(^|\n)\s*(l0p4map|tox|pytest)\b', cmd)
        if runs and op.search(cmd) and not EDIT_SCRIPT.search(cmd) and not re.match(r'\s*(grep|cat|find|ls|sed)\b', cmd):
            (src['runtime_success'] if rc == 0 and not FAIL_OUT.search(out) else src['runtime_failed']).append(s)
        if any(t.startswith('build:') for t in c['tags']):
            if 'Successfully built' in out:
                if re.search(r'Building wheel from (sdist|source distribution)', out):
                    build['wheel_from_sdist_built'].append(s)
                if re.search(r'\.tar\.gz', out.split('Successfully built', 1)[1]):
                    build['sdist_built'].append(s)
                if re.search(r'\.whl', out.split('Successfully built', 1)[1]) and s not in build['wheel_from_sdist_built']:
                    build['wheel_built'].append(s)
            else:
                build['build_failed'].append(s)
        if any(t.startswith('install:') for t in c['tags']):
            if re.search(r'Successfully installed [^\n]*(' + re.escape(ev['task'].split('-')[0]) + r'|l0p4map|stellium|pynecore|pixcull|pyfiglet|apotrope|tox-|pytest.html|s3)', out, re.I):
                install['candidate_installed'].append(s)
            else:
                install['install_failed'].append(s)
    return src, build, install, echo_steps


def main():
    reviewed = json.loads((AUDIT / 'reviewed_labels.json').read_text())
    rows = []
    for f in sorted((AUDIT / 'evidence').glob('*.json')):
        ev = json.loads(f.read_text())
        src, build, install, echo_steps = route_first_pass(ev)
        rv = reviewed[ev['episode_id']]
        pat = ev['pattern']
        affected = AFFECTED.get(ev['task'], 'PFF')
        agent_files = ev['patch']['agent_files']
        rank = lambda p: sum(c == 'P' for c in p)
        if not agent_files:
            change = 'no_change'
        elif pat == affected:
            change = 'edited_no_outcome_change'
        elif rank(pat) < rank(affected) or any(a == 'P' and b == 'F' for a, b in zip(affected, pat)):
            change = 'regression'
        else:
            change = 'partial_improvement'
        row = {
            'episode_id': ev['episode_id'], 'task': ev['task'], 'stratum': ev['scope'], 'condition': ev['condition'],
            'seed': ev['seed'], 'order': ev['order'], 'stop': ev['stop'], 'calls': ev['calls'], 'commands': ev['commands'],
            'format_errors': ev['format_errors'], 'generated_tokens': ev['generated_tokens'],
            'interaction_wall_seconds': round(ev['interaction_wall_seconds'], 1),
            'affected_pattern': affected, 'final_pattern': pat, 'source': pat[0], 'direct_wheel': pat[1], 'sdist_wheel': pat[2],
            'artifact_contract_pass': ev['artifact_contract_pass'],
            'source_pass_installed_fail': pat[0] == 'P' and 'F' in pat[1:],
            'first_failing_step': ';'.join(f"{k}:{next((s for s in ['preparation','build','sdist_build','wheel_build','install','probe'] if s in v['steps'] and v['steps'][s]['returncode'] not in (0, None)), 'probe')}"
                                           for k, v in ev['grade'].items() if not v['pass']),
            'agent_files_changed': len(agent_files), 'agent_lines_added': sum(a['added'] for a in agent_files),
            'agent_lines_removed': sum(a['removed'] for a in agent_files),
            'outcome_change_vs_affected': change,
            'auto_source_runtime_success_steps': src['runtime_success'], 'auto_source_runtime_failed_steps': src['runtime_failed'],
            'auto_wheel_built_steps': build['wheel_built'], 'auto_sdist_built_steps': build['sdist_built'],
            'auto_wheel_from_sdist_steps': build['wheel_from_sdist_built'], 'auto_build_failed_steps': build['build_failed'],
            'auto_candidate_installed_steps': install['candidate_installed'], 'auto_install_failed_steps': install['install_failed'],
            'echo_asserted_success_steps': echo_steps,
        }
        row.update(rv)  # reviewed labels and rationale (see CODEBOOK.md)
        rows.append(row)
    (AUDIT / 'audit_table.json').write_text(json.dumps(rows, indent=2, ensure_ascii=False) + '\n')
    keys = list(rows[0].keys())
    with open(AUDIT / 'audit_table.csv', 'w', newline='', encoding='utf-8') as out:
        w = csv.DictWriter(out, fieldnames=keys)
        w.writeheader()
        for r in rows:
            w.writerow({k: (json.dumps(v, ensure_ascii=False) if isinstance(v, (list, dict)) else v) for k, v in r.items()})
    print(len(rows), 'rows')


if __name__ == '__main__':
    main()
