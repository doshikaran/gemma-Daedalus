"""Historical pytest-html release-route probe with Node absent for sdist consumers."""
import fcntl,hashlib,json,os,pathlib,shutil,subprocess,sys,tarfile,uuid
from replay import ROOT,cmd,build
UV=shutil.which('uv')
PROBE='''import sys,pathlib,json
sys.path[:0]=[sys.argv[1],sys.argv[2]]
import pytest,pytest_html
assert pathlib.Path(pytest_html.__file__).resolve().is_relative_to(pathlib.Path(sys.argv[1]).resolve())
p=pathlib.Path('test_release_fixture.py');p.write_text('def test_audit_release_482():\\n    assert 2+2==4\\n')
code=pytest.main(['-p','pytest_metadata.plugin','-p','pytest_html.plugin','--html=report.html','--self-contained-html','test_release_fixture.py','-q'])
assert code==0
s=pathlib.Path('report.html').read_text();assert 'test_audit_release_482'in s and '<html'in s.lower()
print(json.dumps({'html_report':True,'module_origin':pytest_html.__file__}))
'''
def main(candidate=None, output_root=None):
    task='pytest-html-npm';data=json.loads((ROOT/'sources'/(task+'-provenance.json')).read_text());run_id=uuid.uuid4().hex[:12];records=[]
    locks=ROOT/'locks';locks.mkdir(exist_ok=True)
    with(locks/(task+'.lock')).open('w')as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        if candidate is not None:data['candidate']={'directory':str(candidate),'sha':'candidate-final-state'}
        for arm in (['candidate'] if candidate is not None else ['affected','reference']):
            work=(pathlib.Path(output_root) if output_root else ROOT/'tasks')/task/run_id/arm;repo=work/'repo';shutil.copytree(data[arm]['directory'],repo,symlinks=True)
            env=os.environ.copy();env.update(SETUPTOOLS_SCM_PRETEND_VERSION='0.0.0+audit',PYTEST_DISABLE_PLUGIN_AUTOLOAD='1',npm_config_cache=str(ROOT/'.npm-cache'),NPM_CONFIG_CACHE=str(ROOT/'.npm-cache'))
            prep=[]
            for command in [['npm','ci','--ignore-scripts','--no-audit','--no-fund'],['npm','run','build']]:
                out=cmd(command,repo,env,timeout=180);prep.append(out)
                if out['returncode']:raise RuntimeError(json.dumps(out)[-1800:])
            def check(base,stage):
                consumer=work/('consumer-'+stage);consumer.mkdir()
                return cmd(['python3','-I','-c',PROBE,str(base),str(ROOT/'runtime/pytesthtml-deps')],consumer,env,timeout=60)
            rows=[{'stage':'source','preparation':prep,'probe':check(repo/'src','source')}]
            direct_repo=work/'direct-repo';shutil.copytree(repo,direct_repo,symlinks=True)
            direct=work/'direct-dist';b=build(direct_repo,direct);row={'stage':'wheel','build':b}
            if b['returncode']==0:
                w=next(direct.glob('*.whl'));target=work/'wheel-installed';row['artifact_sha256']=hashlib.sha256(w.read_bytes()).hexdigest();row['install']=cmd([UV,'pip','install','--target',str(target),'--no-deps',str(w)],work,env);row['probe']=check(target,'wheel')
            rows.append(row)
            release_repo=work/'release-repo';shutil.copytree(repo,release_repo,symlinks=True)
            sd=work/'sdist';b=build(release_repo,sd,True);row={'stage':'sdist-wheel','sdist_build':b}
            if b['returncode']==0:
                archive=next(sd.glob('*.tar.gz'));row['sdist_sha256']=hashlib.sha256(archive.read_bytes()).hexdigest();unpack=work/'extracted';unpack.mkdir()
                with tarfile.open(archive)as t:t.extractall(unpack,filter='data')
                root=next(unpack.iterdir());out=work/'from-sdist';out.mkdir();no_node=env.copy();no_node['PATH']='/usr/bin:/bin'
                # No npm is supplied to the consumer's build environment.
                if shutil.which('npm',path=no_node['PATH']):raise RuntimeError('No-Node control unexpectedly finds npm')
                b=cmd([UV,'build','--python',sys.executable,'--wheel','--out-dir',str(out),'--build-constraints',str(ROOT/'build-constraints.txt'),'--cache-dir',str(ROOT/'.uv-cache')],root,no_node);row['wheel_build']=b
                if b['returncode']==0:
                    w=next(out.glob('*.whl'));target=work/'sdist-installed';row['artifact_sha256']=hashlib.sha256(w.read_bytes()).hexdigest();row['install']=cmd([UV,'pip','install','--target',str(target),'--no-deps',str(w)],work,env);row['probe']=check(target,'sdist-wheel')
            rows.append(row)
            for row in rows:
                row['pass']=row.get('probe',{}).get('returncode')==0 and all(value.get('returncode')==0 for key,value in row.items() if key in ['build','install','sdist_build','wheel_build'] and isinstance(value,dict))
            result={'id':task,'arm':arm,'run_id':run_id,'source_sha':data[arm]['sha'],'rows':rows};records.append(result)
            result_path=(pathlib.Path(output_root)/('result-'+task+'.json') if output_root else ROOT/'results'/(task+'-'+arm+'.json'))
            result_path.parent.mkdir(parents=True,exist_ok=True);result_path.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({'id':task,'arm':arm,'stages':{x['stage']:x['pass']for x in rows}}),flush=True)
    return records
if __name__=='__main__':main()
