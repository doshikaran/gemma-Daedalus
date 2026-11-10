"""Create a local pre-experiment hash freeze; never overwrite an existing freeze."""
import datetime
import hashlib
import json
from run_study import ROOT, grid, verify_freeze


def main():
    if (ROOT/'FREEZE.json').exists():raise RuntimeError('Preserve existing freeze; amend explicitly instead')
    assert not list((ROOT/'main_runs').glob('*/result.json'))
    protocol=json.loads((ROOT/'protocol.json').read_text())
    manifest=json.loads((ROOT/'task_manifest.json').read_text())
    assert manifest['families']==12 and manifest['repositories']==10
    assert json.loads((ROOT/'results/main_runner_preflight.json').read_text())['pass']
    tool_check=json.loads((ROOT/'results/agent_tool_environment_preflight.json').read_text())
    assert tool_check['pass'] and len(tool_check['cases'])==12
    for task in manifest['tasks']:
        for arm in ['affected','reference']:
            result=json.loads((ROOT/'results'/f"{task['id']}-{arm}.json").read_text())
            assert result['run_id']==task['validation_run_id']
            observed=''.join('P' if x['pass']else'F'for x in result['rows'])
            assert observed==task['states'][arm]
    plan=grid(protocol,manifest['tasks'])
    (ROOT/'episode_plan.json').write_text(json.dumps(plan,indent=2)+'\n')
    inputs=list(ROOT.glob('*.py'))+list(ROOT.glob('*.md'))+list(ROOT.glob('build-constraints*.txt'))
    inputs += [ROOT/'protocol.json',ROOT/'task_manifest.json',ROOT/'task_validation.csv',ROOT/'episode_plan.json']
    inputs += list(ROOT.glob('*.json'))
    inputs += list((ROOT/'prompts').glob('*.txt'))+list((ROOT/'locks').glob('*.txt'))
    inputs += list((ROOT/'results').rglob('*.json'))
    files={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest()for p in sorted(set(inputs))}
    record={'protocol_version':protocol['version'],'timestamp_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
            'type':'Local pre-experiment freeze, not external preregistration',
            'main_historical_model_episodes_completed':0,'planned_episodes':len(plan),'files':files}
    (ROOT/'FREEZE.json').write_text(json.dumps(record,indent=2)+'\n')
    verify_freeze()
    print(json.dumps({'frozen_inputs':len(files),'timestamp_utc':record['timestamp_utc'],'main_episodes':0}))


if __name__=='__main__':main()
