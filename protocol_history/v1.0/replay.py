"""Build actual historical packages and execute the same public behavior in each artifact."""
import concurrent.futures,hashlib,json,os,pathlib,shutil,subprocess,tarfile,time,sys,fcntl,uuid
ROOT=pathlib.Path(__file__).resolve().parent
DEPS=ROOT/'runtime/probe-deps'
PROBES={
'rtl-data':'''from CocoTBFramework.components.dfi.jedec_timings import builtin_timings
out={name:builtin_timings(name).tCK_ns for name in ['ddr2-650-mt47h64m16hr','ddr3-1600']}
assert out=={'ddr2-650-mt47h64m16hr':3.077,'ddr3-1600':1.25},out
print(json.dumps(out))''',
'l0-module-actual':'''import runpy
sys.argv=['l0p4map','--help']
if stage=='source':runpy.run_path(str(base/'main.py'),run_name='__main__')
else:
 from importlib.metadata import distribution
 entry=next(x for x in distribution('l0p4map').entry_points if x.name=='l0p4map')
 entry.load()()''',
'apotrope-template':'''from apotrope.models import AuditReport
from apotrope.reporter import Reporter
from datetime import datetime
p=pathlib.Path('report.html')
if p.exists():p.unlink()
r=AuditReport(hostname='audit-host-482',os_version='offline-fixture',scan_timestamp=datetime(2026,1,2),scan_duration=0,score=75)
Reporter().generate_html_report(r,str(p))
text=p.read_text();assert 'audit-host-482' in text and '<html' in text.lower()
print(json.dumps({'html_written':True,'host_present':True}))''',
'pyfiglet-154':'''import pyfiglet
out={name:pyfiglet.figlet_format('AB',font=name) for name in ['circle','future']}
assert all(out.values())
print(json.dumps({'rendered':sorted(out)}))''',
'pynecore-data':'''import pynecore
from pynecore.types import Series
assert callable(Series)
print(json.dumps({'imported':True,'series_available':True}))''',
'pixcull-sdist':'''from pixcull.i18n import load_locale,t
a=load_locale('en_US');b=load_locale('zh_CN')
assert len(a)>10 and len(b)>10
key=next(k for k in a if k in b and a[k]!=b[k]);assert t(key,lang='en_US')==a[key]
print(json.dumps({'english_keys':len(a),'chinese_keys':len(b),'translation_lookup':True}))''',
'stellium-locales':'''from stellium.i18n import t,get_available_locales
assert 'zh_CN' in get_available_locales()
assert t('Chart Overview',locale='zh_CN')=='星盘概览'
assert t('audit-untranslated-key',locale='zh_CN')=='audit-untranslated-key'
print(json.dumps({'chinese_translation':True,'unknown_key_preserved':True}))''',
's3-template':'''from s3_security_scanner.html_reporter import HTMLReporter
p=pathlib.Path('s3-report.html')
if p.exists():p.unlink()
item={'bucket_name':'bucket-audit-482','region':'us-east-1','security_score':85,'is_public':False,'issues':[],'compliance_status':{}}
HTMLReporter().generate_report([item],{'total_buckets':1,'scan_time':'2026-01-02T00:00:00','average_security_score':85,'error_buckets':0,'high_severity_buckets':0,'medium_severity_buckets':0,'public_buckets':0,'region':'us-east-1','account_id':'audit-account'},str(p))
text=p.read_text();assert '<html' in text.lower() and 'bucket-audit-482'in text and len(text)>100
print(json.dumps({'report_written':True,'html':True}))''',
'stellium-glyphs':'''from stellium.visualization.core import get_glyph
from xml.etree import ElementTree as ET
for name in ['Pholus','Eris']:
 g=get_glyph(name);assert g['type']=='svg',(name,g['type'])
 assert ET.fromstring(g['value']).tag.endswith('svg')
print(json.dumps({'svg_glyphs':['Pholus','Eris']}))''',
'stellium-cache':'''from geopy.geocoders import Nominatim
def forbidden(*args,**kwargs):raise AssertionError('Unexpected network geocoding for a bundled location')
Nominatim.geocode=forbidden
from stellium import Native
n=Native(datetime_input='2000-01-01 12:00',location_input='Alexandria, Egypt')
assert abs(n.location.latitude-31.2)<0.001 and abs(n.location.longitude-29.9)<0.001
print(json.dumps({'cached_location_resolved':True,'network_geocoding':False}))''',
'tox-sdist':'''from tox.run import run
sys.argv=['tox','--help']
run()'''
}
def cmd(args,cwd,env=None,timeout=120):
    if env is None:
        env=os.environ.copy();env['SETUPTOOLS_SCM_PRETEND_VERSION']='0.0.0+audit';env['npm_config_cache']=str(ROOT/'.npm-cache');env['NPM_CONFIG_CACHE']=str(ROOT/'.npm-cache')
    start=time.monotonic();r=subprocess.run(args,cwd=cwd,env=env,text=True,capture_output=True,timeout=timeout)
    return {'args':[str(x)for x in args],'returncode':r.returncode,'stdout':r.stdout[-5000:],'stderr':r.stderr[-5000:],'seconds':time.monotonic()-start}
def build(repo,out,sdist=False):
    out.mkdir(parents=True,exist_ok=True)
    constraints=ROOT/('build-constraints-tox.txt'if 'tox-sdist'in repo.parts else'build-constraints.txt')
    return cmd(['uv','build','--python',sys.executable,'--sdist'if sdist else'--wheel','--out-dir',str(out),'--build-constraints',str(constraints),'--cache-dir',str(ROOT/'.uv-cache')],repo)
def probe(task,base,stage,cwd):
    paths=[str(base/'src'if(base/'src').exists()else base)]if stage=='source'else[str(base)]
    extras=[str(ROOT/'runtime/pixcull-deps')]if task=='pixcull-sdist'else[str(ROOT/'runtime/tox-deps')]if task=='tox-sdist'else[]
    prelude='import sys,json,pathlib\nbase=pathlib.Path('+repr(str(base))+')\nstage='+repr(stage)+'\nsys.path[:0]='+repr(paths+extras+[str(DEPS)])+'\n'
    code='try:\n'+''.join(' '+line+'\n'for line in PROBES[task].splitlines())+'finally:\n origins={name:getattr(mod,"__file__",None)for name,mod in sys.modules.items()if name in ["CocoTBFramework","main","apotrope","pyfiglet","pynecore","pixcull","stellium","s3_security_scanner","tox"]}\n print(json.dumps({"import_origins":origins}))\n for name,path in origins.items():\n  if path:assert pathlib.Path(path).resolve().is_relative_to(base.resolve()),(name,path,str(base))\n'
    return cmd(['python3','-I','-c',prelude+code],cwd,timeout=40)
def replay(task):
    locks=ROOT/'locks';locks.mkdir(exist_ok=True)
    with (locks/(task+'.lock')).open('w')as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        return _replay(task)
def _replay(task, candidate=None, output_root=None):
    source=json.loads((ROOT/'sources'/(task+'-provenance.json')).read_text());records=[];run_id=uuid.uuid4().hex[:12]
    if candidate is not None:
        source['candidate']={'directory':str(candidate),'sha':'candidate-final-state'}
    for arm in (['candidate'] if candidate is not None else ['affected','reference']):
        work=(pathlib.Path(output_root) if output_root else ROOT/'tasks')/task/run_id/arm
        repo=work/'repo';shutil.copytree(source[arm]['directory'],repo,symlinks=True)
        cwd=work/'consumer';cwd.mkdir()
        # pyfiglet's documented build copies its chosen font set. Include contrib
        # via the upstream makefile's release preparation, without editing code.
        if task=='pyfiglet-154':
            dest=repo/'pyfiglet/fonts';dest.mkdir(exist_ok=True)
            for folder in ['fonts-standard','fonts-contrib']:
                shutil.copytree(repo/'pyfiglet'/folder,dest,dirs_exist_ok=True)
        rows=[];source_preparation=None
        if task=='tox-sdist':source_preparation=build(repo,work/'source-preparation')
        source_consumer=cwd/'source';source_consumer.mkdir()
        rows.append({'stage':'source','preparation':source_preparation,'probe':probe(task,repo,'source',repo if task=='stellium-glyphs'else source_consumer)})
        direct_repo=work/'direct-repo';shutil.copytree(source[arm]['directory'],direct_repo,symlinks=True)
        if task=='pyfiglet-154':
            dest=direct_repo/'pyfiglet/fonts';dest.mkdir(exist_ok=True)
            for folder in ['fonts-standard','fonts-contrib']:shutil.copytree(direct_repo/'pyfiglet'/folder,dest,dirs_exist_ok=True)
        direct=work/'direct-dist';b=build(direct_repo,direct);row={'stage':'wheel','build':b}
        if b['returncode']==0:
            wheel=next(direct.glob('*.whl'));target=work/'wheel-installed'
            row['artifact_sha256']=hashlib.sha256(wheel.read_bytes()).hexdigest()
            row['install']=cmd(['uv','pip','install','--target',str(target),'--no-deps',str(wheel)],work)
            consumer=cwd/'wheel';consumer.mkdir();row['probe']=probe(task,target,'wheel',consumer)
        rows.append(row)
        # Build a fresh copy for the release route, so direct-build outputs cannot
        # repair the sdist by leaking generated files across evaluation states.
        release_repo=work/'release-repo';shutil.copytree(source[arm]['directory'],release_repo,symlinks=True)
        if task=='pyfiglet-154':
            dest=release_repo/'pyfiglet/fonts';dest.mkdir(exist_ok=True)
            for folder in ['fonts-standard','fonts-contrib']:shutil.copytree(release_repo/'pyfiglet'/folder,dest,dirs_exist_ok=True)
        sd=work/'sdist';b=build(release_repo,sd,True);row={'stage':'sdist-wheel','sdist_build':b}
        if b['returncode']==0:
            archive=next(sd.glob('*.tar.gz'));row['sdist_sha256']=hashlib.sha256(archive.read_bytes()).hexdigest()
            extracted=work/'extracted';extracted.mkdir()
            with tarfile.open(archive)as t:t.extractall(extracted,filter='data')
            eroot=next(extracted.iterdir());out=work/'from-sdist';row['wheel_build']=build(eroot,out)
            if row['wheel_build']['returncode']==0:
                wheel=next(out.glob('*.whl'));row['artifact_sha256']=hashlib.sha256(wheel.read_bytes()).hexdigest();target=work/'sdist-installed'
                row['install']=cmd(['uv','pip','install','--target',str(target),'--no-deps',str(wheel)],work);consumer=cwd/'sdist';consumer.mkdir();row['probe']=probe(task,target,'sdist-wheel',consumer)
        rows.append(row)
        for row in rows:
            row['pass']=row.get('probe',{}).get('returncode')==0 and all(value.get('returncode')==0 for key,value in row.items() if key in ['build','install','sdist_build','wheel_build','preparation'] and isinstance(value,dict))
        record={'id':task,'arm':arm,'run_id':run_id,'source_sha':source[arm]['sha'],'rows':rows};records.append(record)
        result_path=(pathlib.Path(output_root)/('result-'+task+'.json') if output_root else ROOT/'results'/(task+'-'+arm+'.json'))
        result_path.parent.mkdir(parents=True,exist_ok=True);result_path.write_text(json.dumps(record,indent=2)+'\n')
        print(json.dumps({'id':task,'arm':arm,'stages':{x['stage']:x['pass']for x in rows}}),flush=True)
    return records
if __name__=='__main__':
    with concurrent.futures.ThreadPoolExecutor(max_workers=3)as pool:
        results=list(pool.map(replay,['rtl-data','l0-module-actual','apotrope-template','pyfiglet-154']))
    (ROOT/'results/replay_initial.json').write_text(json.dumps(results,indent=2)+'\n')
