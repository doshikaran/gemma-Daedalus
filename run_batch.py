"""Sequential frozen study with live status, post-grade retention and final analysis.

No changes to model/condition budgets. One server, one inference slot, four threads.
Completed episode trees are compressed only after their independent grade is saved.
"""
import argparse
import datetime
import fcntl
import gzip
import hashlib
import json
import os
import pathlib
import shutil
import tarfile
import threading
import time
import zipfile

from run_study import ROOT, episode, grid, sha, tree_digest, verify_freeze
from agent_calibration import start_server
from analyze import summarize


def now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def atomic_json(path, value):
    temp=path.with_suffix(path.suffix+'.tmp')
    temp.write_text(json.dumps(value,indent=2)+'\n');temp.replace(path)


def retain(work):
    """Keep patch, final source archive, actual release artifacts and all logs."""
    source=work/'final-source';target=work/'final-source.tar.gz'
    identity=tree_digest(source)
    with tarfile.open(target,'w:gz',compresslevel=3,dereference=False)as archive:
        archive.add(source,arcname='final-source')
    # Read through the gzip CRC before removing the expanded source.
    with gzip.open(target,'rb')as stream:
        while stream.read(1024*1024):pass
    retained=work/'release-artifacts';retained.mkdir(exist_ok=True)
    files=[]
    for p in sorted((work/'grading').rglob('*')):
        if not p.is_file()or not(p.name.endswith('.whl')or p.name.endswith('.tar.gz')):continue
        digest=sha(p);out=retained/(digest+'-'+p.name)
        if not out.exists():shutil.copy2(p,out)
        if sha(out)!=digest:raise RuntimeError('Retained artifact hash mismatch')
        files.append({'original':str(p),'retained':str(out),'sha256':digest,'bytes':p.stat().st_size})
    atomic_json(work/'retention.json',{'timestamp':now(),'source_tree_sha256':identity,
      'source_archive_sha256':sha(target),'release_artifacts':files,
      'reason':'Post-grade compression of generated work directories; frozen inputs, final patch, final source, actual release artifacts and all result/trajectory records retained.'})
    for name in ['repo','final-source','grading']:
        shutil.rmtree(work/name)


def checkpoint():
    """Small evidence package; weights and upstream code/artifact binaries omitted."""
    path=ROOT.parent/'Daedalus_Experiment_Checkpoint.zip';temp=path.with_suffix('.tmp.zip')
    files=set(ROOT.glob('*.md'))|set(ROOT.glob('*.json'))|set(ROOT.glob('*.csv'))|set(ROOT.glob('*.py'))|set(ROOT.glob('build-constraints*.txt'))
    for folder,patterns in [('prompts',['*.txt']),('locks',['*.txt']),('results',['*.json']),
                            ('protocol_history',['*.json','*.py','*.md','*.txt','*.csv'])]:
        for pattern in patterns:files.update((ROOT/folder).rglob(pattern))
    for work in (ROOT/'main_runs').glob('*'):
        for pattern in ['*.json','*.patch','prompt.txt']:files.update(work.glob(pattern))
    for work in (ROOT/'pilots').rglob('calls.json'):
        files.add(work)
        for name in ['prompt.txt','trajectory.json','controller.log']: 
            p=work.parent/name
            if p.exists():files.add(p)
    files.update((ROOT/'sources').glob('*-provenance.json'))
    files.update((ROOT/'logs').glob('*.log'))
    files.update((ROOT/'logs').glob('*audit.json'))
    digests={}
    with zipfile.ZipFile(temp,'w',zipfile.ZIP_DEFLATED,compresslevel=6)as z:
        for p in sorted(files):
            if p.is_file():
                name=str(p.relative_to(ROOT));data=p.read_bytes()
                z.writestr('Daedalus_Experiment/'+name,data);digests[name]=hashlib.sha256(data).hexdigest()
        z.writestr('Daedalus_Experiment/CONTENTS_SHA256.json',json.dumps(digests,indent=2)+'\n')
    with zipfile.ZipFile(temp)as z:
        if z.testzip()is not None:raise RuntimeError('Checkpoint archive integrity failure')
    temp.replace(path)


def status(state, tasks, protocol):
    records=[]
    for p in sorted((ROOT/'main_runs').glob('*/result.json')):
        records.append(json.loads(p.read_text()))
    current=state.get('current');active_calls=0;active_tokens=0
    if current:
        p=ROOT/'main_runs'/current/'calls.json'
        if p.exists():
            try:
                calls=json.loads(p.read_text());active_calls=len(calls)
                active_tokens=sum(x['response']['usage']['completion_tokens']for x in calls)
            except json.JSONDecodeError:pass
    errors=sum('infrastructure_error'in x or 'grading_infrastructure_error'in x for x in records)
    value={'timestamp_utc':now(),'protocol_version':protocol['version'],'phase':state['phase'],
      'planned':72,'completed':len(records),'current_episode':current,'current_completed_responses':active_calls,
      'current_generated_tokens':active_tokens,'artifact_contract_passes':sum(x.get('artifact_contract_pass',False)for x in records),
      'infrastructure_outcomes':errors,'frozen_model':'Gemma 4 E4B QAT Q4_0; one CPU server, one slot, four threads',
      'final_analysis_ready':(ROOT/'results/main_analysis.json').exists(),
      'manual_patch_and_verification_audit':'pending; automated contract pass is not a claim of unrestricted valid repair',
      'error':state.get('error')}
    atomic_json(ROOT/'experiment_status.json',value)
    text='# Experiment status\n\n'+f"Updated: {value['timestamp_utc']} (UTC).\n\n"
    text+=f"**{state['phase']}: {len(records)}/72 episodes have final records.**\n\n"
    text+=f"Current episode: `{current or 'none'}`; {active_calls} completed responses, {active_tokens} generated tokens.\n\n"
    text+=f"Automated artifact-contract passes so far: {value['artifact_contract_passes']}; infrastructure outcomes: {errors}. These are provisional counts, not a final treatment comparison.\n\n"
    text+='All 72 planned episodes use the fixed model, prompts, seeds, tools and budgets. The twelve historical families include eleven artifact-gap cases and one separately analyzed source-failing control. No best-of-attempt selection or silent retries.\n\n'
    text+='One initial v1.0 setup attempt was interrupted after eleven responses before a final outcome. Its trace and the original freeze are retained. Protocol 1.1 aligns agent interpreter/backend selection with the grader; conditions, tasks, model, seeds, budgets and scoring remain fixed.\n\n'
    text+='The controller advances through the entire queue and writes the declared analysis after all 72 valid records. Manual patch and verification-trace audits remain separate. `Daedalus_Experiment_Checkpoint.zip` contains completed trajectories, patches, protocol history and interim evidence.\n'
    if state.get('error'):text+='\nExecution issue: '+state['error']+'\n'
    temp=ROOT/'Experiment_Status.tmp';temp.write_text(text);temp.replace(ROOT/'Experiment_Status.md')


def final_report(analysis,records):
    rows=analysis['families'];diff=analysis['primary_family_mean_difference']
    report='# Automated experiment results\n\n'
    report+='All 72 declared episodes have result records. This report covers automated artifact-contract grading. Manual patch validity and verification-trace audits are still required before paper conclusions.\n\n'
    report+='| Family | Ordinary A | Checklist B | B − A |\n| :-- | --: | --: | --: |\n'
    for row in rows:report+=f"| {row['id']} | {row['A']:.3f} | {row['B']:.3f} | {row['B_minus_A']:+.3f} |\n"
    report+=f"\nPrimary mean family difference (eleven gap families): {diff:+.4f}. Descriptive repository-cluster 95% interval: {analysis['repository_cluster_percentile_95_interval']}.\n"
    report+='\nThe source-failing control is separate. Public historical fixes, repository clustering, scoped runtime checks and one small quantized CPU model limit interpretation. This selected cohort does not estimate failure prevalence.\n'
    (ROOT/'Automated_Experiment_Results.md').write_text(report)


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--resume',action='store_true');args=parser.parse_args()
    lock=(ROOT/'locks/main-batch.lock').open('w');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    lock.write(str(os.getpid())+'\n');lock.flush()
    verify_freeze();protocol=json.loads((ROOT/'protocol.json').read_text())
    tasks=json.loads((ROOT/'task_manifest.json').read_text())['tasks'];plan=grid(protocol,tasks)
    existing=list((ROOT/'main_runs').glob('*/result.json'))
    if existing and not args.resume:raise RuntimeError('Use --resume to retain completed declared episodes')
    state={'phase':'starting','current':None};stop=threading.Event()
    def tick():
        while not stop.wait(15):
            try:status(state,tasks,protocol)
            except Exception as exc:print('STATUS_ERROR',repr(exc),flush=True)
    thread=threading.Thread(target=tick,daemon=True);thread.start()
    process=None;log=None
    try:
        if sha(ROOT/'runtime'/protocol['model']['filename'])!=protocol['model']['sha256']:
            raise RuntimeError('Model digest mismatch')
        os.environ.update(UV_OFFLINE='1',npm_config_offline='true',npm_config_cache=str(ROOT/'.npm-cache'),
          NPM_CONFIG_CACHE=str(ROOT/'.npm-cache'),UV_CACHE_DIR=str(ROOT/'.uv-cache'),CC='gcc',CXX='g++',
          CALIBRATION_MODEL=protocol['model']['filename'])
        process,log,server_args=start_server()
        atomic_json(ROOT/'execution_manifest.json',{'started_at':now(),'pid':os.getpid(),'server_args':server_args,
          'protocol':protocol['version'],'freeze_sha256':sha(ROOT/'FREEZE.json'),'execution':'one sequential worker; original randomized plan order'})
        for row in plan:
            work=ROOT/'main_runs'/row['episode_id'];result_file=work/'result.json'
            if result_file.exists()and args.resume:
                result=json.loads(result_file.read_text())
                if result.get('protocol_version')!=protocol['version'] or any(result[k]!=row[k]for k in row):
                    raise RuntimeError('Existing record differs from frozen episode')
                if 'infrastructure_error'in result or 'grading_infrastructure_error'in result:
                    raise RuntimeError('Existing infrastructure outcome needs disclosed review, not automatic retry')
                continue
            state.update(phase='running',current=row['episode_id']);status(state,tasks,protocol)
            result=episode(row,next(t for t in tasks if t['id']==row['task']),protocol)
            print(json.dumps({'completed_episode':row['episode_id'],'contract_pass':result.get('artifact_contract_pass'),
                              'stop':result.get('stop'),'timestamp':now()}),flush=True)
            if 'infrastructure_error'in result or 'grading_infrastructure_error'in result:
                raise RuntimeError('Infrastructure outcome retained; review required before continuing')
            retain(work)
            state['current']=None;status(state,tasks,protocol);checkpoint()
        records=[json.loads(p.read_text())for p in (ROOT/'main_runs').glob('*/result.json')]
        analysis=summarize(records,tasks,protocol)
        atomic_json(ROOT/'results/main_analysis.json',analysis);final_report(analysis,records)
        state.update(phase='complete',current=None);status(state,tasks,protocol);checkpoint()
    except BaseException as exc:
        state.update(phase='paused',error=repr(exc));status(state,tasks,protocol)
        checkpoint();raise
    finally:
        stop.set();thread.join(timeout=2)
        if process is not None:
            process.terminate()
            try:process.wait(timeout=10)
            except Exception:process.kill();process.wait()
        if log is not None:log.close()


if __name__=='__main__':main()
