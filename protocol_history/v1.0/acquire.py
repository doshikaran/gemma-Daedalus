"""Fetch public historical sources and record their exact identities."""
import concurrent.futures,hashlib,json,pathlib,tarfile,time,urllib.request
ROOT=pathlib.Path(__file__).resolve().parent
def fetch(url,timeout=45):
    with urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'Daedalus-Research','Accept':'application/vnd.github+json'}),timeout=timeout)as r:return r.read()
def api(path):
    name=path.replace('/','__').replace('?','_').replace('&','_')+'.json';dest=ROOT/'sources'/name
    if dest.exists():return json.loads(dest.read_text())
    raw=fetch('https://api.github.com/'+path);dest.write_bytes(raw);return json.loads(raw)
def checkout(repo,sha):
    base=repo.replace('/','__')+'-'+sha
    archive=ROOT/'sources'/(base+'.tar.gz');dest=ROOT/'sources'/base
    if not archive.exists():archive.write_bytes(fetch('https://codeload.github.com/'+repo+'/tar.gz/'+sha,90))
    if not dest.exists():
        dest.mkdir()
        with tarfile.open(archive)as t:
            members=t.getmembers();prefix=members[0].name.split('/')[0]+'/'
            for m in members:
                if not m.name.startswith(prefix):continue
                m.name=m.name[len(prefix):]
                if m.name:t.extract(m,dest,filter='data')
    return {'repository':repo,'sha':sha,'directory':str(dest),'archive_sha256':hashlib.sha256(archive.read_bytes()).hexdigest(),'archive_bytes':archive.stat().st_size}
def commit_pair(repo,fix):
    d=api('repos/'+repo+'/commits/'+fix)
    return d['parents'][0]['sha'],d['sha']
def job(name,repo,fix=None,pair=None):
    try:
        affected,fixed=pair or commit_pair(repo,fix)
        rows=[checkout(repo,sha)for sha in [affected,fixed]]
        result={'id':name,'repository':repo,'affected':rows[0],'reference':rows[1]}
    except Exception as e:result={'id':name,'repository':repo,'error':repr(e)}
    (ROOT/'sources'/(name+'-provenance.json')).write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result),flush=True);return result
if __name__=='__main__':
    jobs=[('rtl-data','sean-galloway/RTLDesignSherpa-DV',None,('d77b364fc2f739d4dc4edd1fe6ee73ea832ad20d','81f6a103149e891ad5ef3b832630aa8275dbfc0f')),('l0-module','HaxL0p4/L0p4Map','1971dac',None),('l0-entry','HaxL0p4/L0p4Map','71e66e6',None),('apotrope-template','hexorcist404/apotrope','v0.1.4',None)]
    with concurrent.futures.ThreadPoolExecutor(max_workers=4)as pool:rows=list(pool.map(lambda x:job(*x),jobs))
    (ROOT/'results/acquisition.json').write_text(json.dumps(rows,indent=2)+'\n')
