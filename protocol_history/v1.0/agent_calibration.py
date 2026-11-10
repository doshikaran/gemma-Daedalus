"""Two declared synthetic runner checks; no historical main-study tasks are sent."""
import hashlib,json,os,pathlib,re,subprocess,time,urllib.request,uuid
ROOT=pathlib.Path(__file__).resolve().parent
SCHEMA={'type':'object','properties':{'action':{'type':'string','enum':['run','finish']},'command':{'type':'string'},'summary':{'type':'string'}},'required':['action','command','summary'],'additionalProperties':False}
SYSTEM='You are a coding agent working inside the current repository. Respond with exactly one bash code block containing the next shell command to execute. You can inspect files and use Python or shell to edit them. After successful testing, respond COMPLETE with a short summary and no code block. All paths are relative to the current directory. Do not access parent directories or network services. Never modify check.py. You must actually repair the files, not just describe a repair.'
def start_server():
    binary=ROOT/'runtime/llama-b12020';env=os.environ.copy();env['LD_LIBRARY_PATH']=str(binary)
    log=(ROOT/'logs/calibration-model.log').open('w')
    model=os.environ.get('CALIBRATION_MODEL','gemma-4-E2B_q4_0-it.gguf')
    args=[str(binary/'llama-server'),'-m',str(ROOT/'runtime'/model),'-c','32768','-t','4','-tb','4','--parallel','1','--reasoning-budget','128','--host','127.0.0.1','--port','18090','--no-ui']
    p=subprocess.Popen(args,cwd=binary,env=env,stdout=log,stderr=log)
    for _ in range(150):
        try:
            with urllib.request.urlopen('http://127.0.0.1:18090/health',timeout=1):return p,log,args
        except Exception:
            if p.poll()is not None:raise RuntimeError('Model server exited; inspect logs/calibration-model.log')
            time.sleep(.2)
    raise RuntimeError('Model server not ready')
def request(messages,seed):
    payload={'messages':messages,'temperature':0.2,'seed':seed,'max_tokens':1024,'chat_template_kwargs':{'enable_thinking':True}}
    start=time.monotonic()
    with urllib.request.urlopen(urllib.request.Request('http://127.0.0.1:18090/v1/chat/completions',data=json.dumps(payload).encode(),headers={'Content-Type':'application/json'}),timeout=240)as response:raw=json.load(response)
    c=raw['choices'][0];content=re.sub(r'<think>.*?</think>','',c['message'].get('content',''),flags=re.S);return {'content':content,'finish_reason':c['finish_reason'],'usage':raw.get('usage'),'seconds':time.monotonic()-start}
def main():
    p,log,args=start_server();results=[];run_id=uuid.uuid4().hex[:12]
    try:
        cases=[('function','Fix add_one so it returns n+1 for any integer. Run python3 check.py before finishing.',{'app.py':'def add_one(n):\n    return n\n','check.py':'from app import add_one\nassert [add_one(n)for n in [-2,0,8]]==[-1,1,9]\nprint("PASS")\n'}),('resource','Fix the package so its bundled message.txt is included in the built wheel. Run python3 check.py before finishing.',{'pyproject.toml':'[build-system]\nrequires=["setuptools>=68","wheel"]\nbuild-backend="setuptools.build_meta"\n[project]\nname="calibration-message"\nversion="0.0.1"\n[tool.setuptools.packages.find]\nwhere=["src"]\n','src/calmsg/__init__.py':'from importlib.resources import files\ndef message():\n    return files(__package__).joinpath("message.txt").read_text().strip()\n','src/calmsg/message.txt':'runner-calibration-482\n','check.py':'import pathlib,subprocess,sys,tempfile,zipfile\nr=pathlib.Path(__file__).resolve().parent\nenvdir=r.parents[2]/"runtime/build-env"\nwith tempfile.TemporaryDirectory(dir=r) as t:\n p=subprocess.run([sys.executable,"-c","import sys;sys.path.insert(0,sys.argv[1]);from build.__main__ import main;main()",str(envdir),"--wheel","--no-isolation","--outdir",t],cwd=r,capture_output=True,text=True)\n assert p.returncode==0,p.stderr\n w=next(pathlib.Path(t).glob("*.whl"))\n with zipfile.ZipFile(w)as z:assert z.read("calmsg/message.txt").decode().strip()=="runner-calibration-482"\nprint("PASS")\n'})]
        for index,(name,instruction,files)in enumerate(cases):
            cwd=ROOT/'calibration'/run_id/name/'repo';cwd.mkdir(parents=True,exist_ok=False)
            for relative,body in files.items():
                target=cwd/relative;target.parent.mkdir(parents=True,exist_ok=True);target.write_text(body)
            if name=='resource':
                (cwd/'setup.py').unlink(missing_ok=True)
                path=cwd/'check.py';path.write_text('import os,pathlib,subprocess,sys,tempfile,zipfile\nr=pathlib.Path(__file__).resolve().parent\nenv={**os.environ,"PYTHONPATH":'+repr(str(ROOT/'runtime/build-env'))+'}\nwith tempfile.TemporaryDirectory(dir=r) as t:\n p=subprocess.run([sys.executable,"-m","build","--wheel","--no-isolation","--outdir",t],cwd=r,env=env,capture_output=True,text=True)\n assert p.returncode==0,p.stderr\n w=next(pathlib.Path(t).glob("*.whl"))\n with zipfile.ZipFile(w)as z:assert z.read("calmsg/message.txt").decode().strip()=="runner-calibration-482"\nprint("PASS")\n')
                baseline=subprocess.run(['python3','check.py'],cwd=cwd,capture_output=True,text=True)
                original=(cwd/'pyproject.toml').read_text();(cwd/'pyproject.toml').write_text(original+'\n[tool.setuptools.package-data]\ncalmsg=["message.txt"]\n')
                reference=subprocess.run(['python3','check.py'],cwd=cwd,capture_output=True,text=True)
                assert baseline.returncode!=0 and reference.returncode==0,{'baseline':baseline.stderr,'reference':reference.stderr}
                (cwd/'pyproject.toml').write_text(original)
                for folder in ['build','src/calibration_message.egg-info']:
                    import shutil
                    shutil.rmtree(cwd/folder,ignore_errors=True)
                (ROOT/'results/resource_oracle_controls.json').write_text(json.dumps({'affected_returncode':baseline.returncode,'reference_returncode':reference.returncode,'reference_stdout':reference.stdout},indent=2)+'\n')
            check_hash=hashlib.sha256((cwd/'check.py').read_bytes()).hexdigest()
            messages=[{'role':'system','content':SYSTEM},{'role':'user','content':instruction+' Files present: '+', '.join(files)+'.'}];calls=[]
            for step in range(12):
                response=request(messages,19+index);row={'step':step,'response':response};calls.append(row)
                messages.append({'role':'assistant','content':response['content']})
                if response['content'].strip().startswith('COMPLETE'):break
                match=re.search(r'```(?:bash|sh)\s*\n(.*?)```',response['content'],re.S)
                if not match:
                    row['format_error']='No shell code block';messages.append({'role':'user','content':'Return exactly one bash code block with a command, or COMPLETE after testing.'});continue
                command=match.group(1).strip()
                if any(s in command for s in ['../','https://','http://','curl ','wget ','rm -rf /']):output='Command rejected: work only inside the repository.';row['command_rejected']=True
                else:
                    try:
                        done=subprocess.run(command,shell=True,cwd=cwd,capture_output=True,text=True,timeout=90)
                        output=json.dumps({'returncode':done.returncode,'stdout':done.stdout[-4000:],'stderr':done.stderr[-4000:]});row['command_result']=json.loads(output)
                    except subprocess.TimeoutExpired:output='Command timed out';row['command_timeout']=True
                messages.append({'role':'user','content':'Tool result: '+output})
            check=subprocess.run(['python3','check.py'],cwd=cwd,capture_output=True,text=True,timeout=90)
            result={'case':name,'run_id':run_id,'workspace':str(cwd),'synthetic_calibration_only':True,'calls':calls,'check_unchanged':hashlib.sha256((cwd/'check.py').read_bytes()).hexdigest()==check_hash,'final_check':{'returncode':check.returncode,'stdout':check.stdout,'stderr':check.stderr},'pass':check.returncode==0 and hashlib.sha256((cwd/'check.py').read_bytes()).hexdigest()==check_hash}
            results.append(result);(ROOT/'results'/('calibration-'+name+'.json')).write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({'case':name,'pass':result['pass'],'model_calls':len(calls)}),flush=True)
    finally:
        p.terminate()
        try:p.wait(timeout=10)
        except subprocess.TimeoutExpired:p.kill();p.wait()
        log.close()
    (ROOT/'results/runner_calibration.json').write_text(json.dumps({'run_id':run_id,'server_args':args,'response_format':'bash-fence','system_prompt':SYSTEM,'cases':results},indent=2)+'\n')
if __name__=='__main__':main()
