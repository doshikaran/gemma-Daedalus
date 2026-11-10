"""Exercise real agent build tools on every known fixed reference, without LLMs."""
import concurrent.futures
import json
import os
import pathlib
import shutil
import uuid
from run_study import ROOT, agent_environment, prepare
from replay import cmd


def check(task):
    name=task['id'];source=json.loads((ROOT/'sources'/f'{name}-provenance.json').read_text())
    work=ROOT/'agent_environment_audit'/'corrected'/name/uuid.uuid4().hex[:8]
    repo=work/'repo';shutil.copytree(source['reference']['directory'],repo,symlinks=True)
    prepare(repo,name)
    env=agent_environment(name)
    result=cmd(['uv','build','--wheel','--sdist','--out-dir',str(work/'dist')],repo,env,timeout=180)
    record={'task':name,'revision':source['reference']['sha'],'command':result,
            'UV_PYTHON':env['UV_PYTHON'],'UV_BUILD_CONSTRAINT':env['UV_BUILD_CONSTRAINT'],
            'pass':result['returncode']==0,'model_calls':0}
    print(json.dumps({'task':name,'pass':record['pass']}),flush=True)
    return record


def main():
    os.environ.update(UV_OFFLINE='1',npm_config_offline='true',
      npm_config_cache=str(ROOT/'.npm-cache'),NPM_CONFIG_CACHE=str(ROOT/'.npm-cache'))
    tasks=json.loads((ROOT/'task_manifest.json').read_text())['tasks']
    with concurrent.futures.ThreadPoolExecutor(max_workers=3)as pool:
        records=list(pool.map(check,tasks))
    result={'purpose':'Every fixed reference must build with the actual agent tool environment, without extra interpreter/constraint command flags.',
            'model_calls':0,'cases':records,'pass':all(x['pass']for x in records)}
    (ROOT/'results/agent_tool_environment_preflight.json').write_text(json.dumps(result,indent=2)+'\n')
    if not result['pass']:raise SystemExit('Agent tool environment is not ready')


if __name__=='__main__':main()
