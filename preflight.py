"""Meaningful runner controls, excluded from all main-study measurements."""
import json
import os
import pathlib
import tempfile
import uuid
import time

from run_study import ROOT, grid, interact, parse_command, evaluate, git, snapshot
from analyze import summarize


def main():
    protocol = json.loads((ROOT/'protocol.json').read_text())
    tasks = json.loads((ROOT/'task_manifest.json').read_text())['tasks']
    checks = []
    rows = grid(protocol,tasks)
    assert len(rows)==72 and len({r['episode_id'] for r in rows})==72
    for task in tasks:
        for condition in ['A','B']:
            assert {r['seed'] for r in rows if r['task']==task['id'] and r['condition']==condition}=={19,23,41}
    checks.append('72 unique episodes; balanced seeds and conditions')
    assert rows==grid(protocol,tasks)
    checks.append('Deterministic randomized ordering')
    synthetic=[{**row,'artifact_contract_pass':row['condition']=='B'}for row in rows]
    analysis=summarize(synthetic,tasks,protocol)
    assert analysis['primary_family_mean_difference']==1
    assert analysis['repository_cluster_percentile_95_interval']==[1,1]
    try:summarize(synthetic[:-1],tasks,protocol)
    except ValueError:pass
    else:raise AssertionError('Incomplete analysis accepted')
    checks.append('Declared analysis recovers a known paired contrast and rejects incomplete data')
    assert parse_command('```bash\npython3 -V\n```')=='python3 -V'
    assert parse_command('COMPLETE\nTested.') is None
    for bad in ['I would edit a file.','```bash\npwd\n```\n```bash\nls\n```']:
        try:parse_command(bad)
        except ValueError:pass
        else:raise AssertionError('Malformed or multiple commands accepted')
    checks.append('Action parsing rejects malformed and multiple tool blocks')
    with tempfile.TemporaryDirectory(prefix='preflight-',dir=ROOT/'calibration') as tmp:
        repo=pathlib.Path(tmp)/'repo';repo.mkdir()
        (repo/'app.py').write_text('def add_one(n):\n return n\n')
        responses=iter(['Read first.', '```bash\ncat app.py\n```',
            '```bash\npython3 - <<\'PY\'\nfrom pathlib import Path\np=Path("app.py");p.write_text(p.read_text().replace("return n", "return n+1"))\nPY\n```',
            '```bash\npython3 -c "from app import add_one; assert add_one(-2)==-1; print(\'PASS\')"\n```',
            'COMPLETE\nFunction tested.'])
        def fake(*_):
            return {'content':next(responses),'usage':{'completion_tokens':10},'finish_reason':'stop','seconds':0}
        trace=pathlib.Path(tmp)/'calls.json'
        calls,stop,tokens=interact(repo,[],19,protocol,os.environ.copy(),fake,trace)
        assert stop=='completion_claim' and tokens==50 and calls[0]['format_error']
        assert calls[-2]['result']['returncode']==0 and 'PASS' in calls[-2]['result']['output']
        assert len(json.loads(trace.read_text()))==5
        checks.append('Scripted read/edit/execute/format-error recovery/completion, with persisted trajectory')
        short={**protocol,'episode_generated_tokens':10}
        def consuming(*_):return {'content':'No shell block.','usage':{'completion_tokens':10},'seconds':0}
        calls,stop,tokens=interact(repo,[],19,short,os.environ.copy(),consuming)
        assert stop=='budget' and len(calls)==1
        checks.append('Generated-token exhaustion stops the episode')
        def deadline(*_):
            time.sleep(.02);raise TimeoutError('Controlled episode deadline')
        calls,stop,tokens=interact(repo,[],19,{**protocol,'wall_seconds':.01},os.environ.copy(),deadline)
        assert stop=='budget' and calls[0]['partial_response_tokens_unknown']
        checks.append('An inference response interrupted by the wall budget is scored as budget exhaustion, with token uncertainty retained')
        git(repo,'init','-q');git(repo,'add','.');git(repo,'commit','-qm','fixture')
        baseline=git(repo,'rev-parse','HEAD').decode().strip()
        (repo/'.git/info/exclude').write_text('ignored-build/\n')
        (repo/'ignored-build').mkdir();(repo/'ignored-build/debris').write_text('omit')
        (repo/'new-file').write_text('retain')
        exported=pathlib.Path(tmp)/'exported';patch=snapshot(repo,exported)
        assert (exported/'new-file').exists() and not (exported/'ignored-build').exists() and patch
        checks.append('Final patch export retains new source and excludes ignored build debris')
        git(repo,'commit','-qm','Simulate agent committing its edit')
        exported2=pathlib.Path(tmp)/'exported-after-commit'
        assert snapshot(repo,exported2,baseline)
        checks.append('Patch remains relative to original baseline even if the agent commits')
    controls=[]
    for arm,expected in [('affected',False),('reference',True)]:
        provenance=json.loads((ROOT/'sources/rtl-data-provenance.json').read_text())
        output=ROOT/'preflight_runs'/uuid.uuid4().hex
        grade=evaluate('rtl-data',pathlib.Path(provenance[arm]['directory']),output)
        passed=all(x['pass'] for x in grade['rows'])
        assert passed==expected
        controls.append({'arm':arm,'pass':passed,'states':{x['stage']:x['pass']for x in grade['rows']},'output':str(output)})
    checks.append('Main runner candidate-grading path rejects historical no-op and accepts upstream fix')
    result={'synthetic_or_gold_control_only':True,'main_model_calls':0,'checks':checks,
            'candidate_grading_controls':controls,'pass':True}
    (ROOT/'results/main_runner_preflight.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))


if __name__=='__main__':main()
